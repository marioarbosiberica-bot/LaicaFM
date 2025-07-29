from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import aiofiles
import json
import asyncio
from mutagen import File as MutagenFile
import socketio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Socket.IO setup
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

# Create directories for audio files
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Radio state management
class RadioState:
    def __init__(self):
        self.current_song: Optional[Dict] = None
        self.playlist: List[Dict] = []
        self.is_playing: bool = False
        self.is_live: bool = False
        self.listeners: int = 0
        self.current_position: float = 0.0
        self.start_time: Optional[datetime] = None
        
radio_state = RadioState()

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        radio_state.listeners = len(self.active_connections)
        await self.broadcast_radio_state()
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        radio_state.listeners = len(self.active_connections)
        
    async def broadcast_radio_state(self):
        state_data = {
            "type": "radio_state",
            "current_song": radio_state.current_song,
            "is_playing": radio_state.is_playing,
            "is_live": radio_state.is_live,
            "listeners": radio_state.listeners,
            "current_position": radio_state.current_position
        }
        await self.broadcast(state_data)
        
    async def broadcast(self, data: dict):
        if self.active_connections:
            message = json.dumps(data)
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(conn)

manager = ConnectionManager()

# Models
class Song(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    artist: str = ""
    filename: str
    duration: float = 0.0
    file_size: int = 0
    upload_date: datetime = Field(default_factory=datetime.utcnow)

class Playlist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    songs: List[str] = []  # List of song IDs
    created_date: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = False

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RadioStats(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    listeners: int
    current_song_id: Optional[str] = None
    is_playing: bool
    is_live: bool

# Routes
@api_router.get("/")
async def root():
    return {"message": "LaicaFM API - ¡Tu estación de radio online!"}

# Song management endpoints
@api_router.post("/songs/upload")
async def upload_song(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de audio")
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Extract metadata
        try:
            audio_file = MutagenFile(str(file_path))
            title = str(audio_file.get('TIT2', [file.filename])[0]) if audio_file and audio_file.get('TIT2') else file.filename
            artist = str(audio_file.get('TPE1', ['Artista Desconocido'])[0]) if audio_file and audio_file.get('TPE1') else 'Artista Desconocido'
            duration = audio_file.info.length if audio_file and audio_file.info else 0.0
        except:
            title = file.filename
            artist = 'Artista Desconocido'
            duration = 0.0
        
        # Create song object
        song = Song(
            title=title,
            artist=artist,
            filename=unique_filename,
            duration=duration,
            file_size=len(content)
        )
        
        # Save to database
        await db.songs.insert_one(song.dict())
        
        return song
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {str(e)}")

@api_router.get("/songs", response_model=List[Song])
async def get_songs():
    songs = await db.songs.find().to_list(1000)
    return [Song(**song) for song in songs]

@api_router.delete("/songs/{song_id}")
async def delete_song(song_id: str):
    result = await db.songs.delete_one({"id": song_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    
    # Try to delete file
    try:
        songs = await db.songs.find({"id": song_id}).to_list(1)
        if songs:
            file_path = UPLOAD_DIR / songs[0]["filename"]
            if file_path.exists():
                file_path.unlink()
    except:
        pass
    
    return {"message": "Canción eliminada"}

# Playlist management
@api_router.post("/playlists", response_model=Playlist)
async def create_playlist(name: str):
    playlist = Playlist(name=name)
    await db.playlists.insert_one(playlist.dict())
    return playlist

@api_router.get("/playlists", response_model=List[Playlist])
async def get_playlists():
    playlists = await db.playlists.find().to_list(1000)
    return [Playlist(**playlist) for playlist in playlists]

@api_router.post("/playlists/{playlist_id}/songs/{song_id}")
async def add_song_to_playlist(playlist_id: str, song_id: str):
    result = await db.playlists.update_one(
        {"id": playlist_id},
        {"$addToSet": {"songs": song_id}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Playlist no encontrada")
    return {"message": "Canción agregada a la playlist"}

# Radio control endpoints
@api_router.post("/radio/play")
async def play_radio():
    if not radio_state.playlist:
        # Load active playlist
        active_playlist = await db.playlists.find_one({"is_active": True})
        if active_playlist:
            songs = await db.songs.find({"id": {"$in": active_playlist["songs"]}}).to_list(1000)
            radio_state.playlist = [Song(**song).dict() for song in songs]
    
    if radio_state.playlist and not radio_state.is_playing:
        if not radio_state.current_song:
            radio_state.current_song = radio_state.playlist[0]
        radio_state.is_playing = True
        radio_state.start_time = datetime.utcnow()
        await manager.broadcast_radio_state()
    
    return {"message": "Radio iniciada", "current_song": radio_state.current_song}

@api_router.post("/radio/pause")
async def pause_radio():
    radio_state.is_playing = False
    await manager.broadcast_radio_state()
    return {"message": "Radio pausada"}

@api_router.post("/radio/next")
async def next_song():
    if radio_state.playlist and radio_state.current_song:
        current_index = next((i for i, song in enumerate(radio_state.playlist) if song["id"] == radio_state.current_song["id"]), -1)
        if current_index != -1 and current_index < len(radio_state.playlist) - 1:
            radio_state.current_song = radio_state.playlist[current_index + 1]
            radio_state.start_time = datetime.utcnow()
            radio_state.current_position = 0.0
            await manager.broadcast_radio_state()
    return {"message": "Siguiente canción", "current_song": radio_state.current_song}

@api_router.get("/radio/status")
async def get_radio_status():
    return {
        "current_song": radio_state.current_song,
        "is_playing": radio_state.is_playing,
        "is_live": radio_state.is_live,
        "listeners": radio_state.listeners,
        "current_position": radio_state.current_position,
        "playlist_length": len(radio_state.playlist)
    }

# Chat endpoints
@api_router.get("/chat/messages")
async def get_chat_messages():
    messages = await db.chat_messages.find().sort("timestamp", -1).limit(50).to_list(50)
    return [ChatMessage(**msg) for msg in messages]

@api_router.post("/chat/message")
async def send_chat_message(username: str, message: str):
    chat_msg = ChatMessage(username=username, message=message)
    await db.chat_messages.insert_one(chat_msg.dict())
    
    # Broadcast to all connections
    await manager.broadcast({
        "type": "chat_message",
        "message": chat_msg.dict()
    })
    
    return chat_msg

# Statistics
@api_router.get("/stats/current")
async def get_current_stats():
    stats = RadioStats(
        listeners=radio_state.listeners,
        current_song_id=radio_state.current_song["id"] if radio_state.current_song else None,
        is_playing=radio_state.is_playing,
        is_live=radio_state.is_live
    )
    await db.radio_stats.insert_one(stats.dict())
    return stats

# WebSocket endpoint
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (like chat, position updates, etc.)
            try:
                message = json.loads(data)
                if message.get("type") == "position_update":
                    radio_state.current_position = message.get("position", 0.0)
                elif message.get("type") == "chat":
                    chat_msg = ChatMessage(
                        username=message.get("username", "Anónimo"),
                        message=message.get("message", "")
                    )
                    await db.chat_messages.insert_one(chat_msg.dict())
                    await manager.broadcast({
                        "type": "chat_message",
                        "message": chat_msg.dict()
                    })
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Include the router in the main app
app.include_router(api_router)

# Add Socket.IO to the app
app.mount("/socket.io", socketio.ASGIApp(sio))

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
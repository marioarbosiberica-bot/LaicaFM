import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { 
  Play, 
  Pause, 
  SkipForward, 
  Upload, 
  Users, 
  Music,
  MessageCircle,
  Radio,
  Volume2,
  Disc,
  Headphones
} from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  // Estado principal
  const [currentSong, setCurrentSong] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [listeners, setListeners] = useState(0);
  const [songs, setSongs] = useState([]);
  const [playlists, setPlaylists] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [username, setUsername] = useState('Usuario');
  const [activeTab, setActiveTab] = useState('player');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  
  // Referencias
  const wsRef = useRef(null);
  const audioRef = useRef(null);
  const chatEndRef = useRef(null);

  // Conectar WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = `${BACKEND_URL.replace('http', 'ws')}/api/ws`;
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket conectado a LaicaFM');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'radio_state') {
            setCurrentSong(data.current_song);
            setIsPlaying(data.is_playing);
            setIsLive(data.is_live);
            setListeners(data.listeners);
          } else if (data.type === 'chat_message') {
            setChatMessages(prev => [...prev, data.message]);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket desconectado, reintentando...');
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('Error WebSocket:', error);
      };
    };
    
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Cargar datos iniciales
  useEffect(() => {
    loadSongs();
    loadPlaylists();
    loadChatMessages();
    getRadioStatus();
  }, []);

  // Auto scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Funciones API
  const loadSongs = async () => {
    try {
      const response = await axios.get(`${API}/songs`);
      setSongs(response.data);
    } catch (error) {
      console.error('Error cargando canciones:', error);
    }
  };

  const loadPlaylists = async () => {
    try {
      const response = await axios.get(`${API}/playlists`);
      setPlaylists(response.data);
    } catch (error) {
      console.error('Error cargando playlists:', error);
    }
  };

  const loadChatMessages = async () => {
    try {
      const response = await axios.get(`${API}/chat/messages`);
      setChatMessages(response.data.reverse());
    } catch (error) {
      console.error('Error cargando mensajes:', error);
    }
  };

  const getRadioStatus = async () => {
    try {
      const response = await axios.get(`${API}/radio/status`);
      setCurrentSong(response.data.current_song);
      setIsPlaying(response.data.is_playing);
      setIsLive(response.data.is_live);
      setListeners(response.data.listeners);
    } catch (error) {
      console.error('Error obteniendo estado de radio:', error);
    }
  };

  // Controles de radio
  const playRadio = async () => {
    try {
      await axios.post(`${API}/radio/play`);
    } catch (error) {
      console.error('Error iniciando radio:', error);
    }
  };

  const pauseRadio = async () => {
    try {
      await axios.post(`${API}/radio/pause`);
    } catch (error) {
      console.error('Error pausando radio:', error);
    }
  };

  const nextSong = async () => {
    try {
      await axios.post(`${API}/radio/next`);
    } catch (error) {
      console.error('Error cambiando canción:', error);
    }
  };

  // Upload de archivos
  const handleFileUpload = async () => {
    if (!selectedFile) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
      await axios.post(`${API}/songs/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setSelectedFile(null);
      await loadSongs();
      alert('¡Canción subida exitosamente!');
    } catch (error) {
      console.error('Error subiendo archivo:', error);
      alert('Error subiendo archivo. Por favor intenta de nuevo.');
    } finally {
      setUploading(false);
    }
  };

  // Chat
  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    
    try {
      await axios.post(`${API}/chat/message?username=${username}&message=${newMessage}`);
      setNewMessage('');
    } catch (error) {
      console.error('Error enviando mensaje:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      {/* Header */}
      <header className="bg-black/20 backdrop-blur-md border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <Radio className="h-8 w-8 text-cyan-400" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">LaicaFM</h1>
                <p className="text-cyan-400 text-sm">Tu estación favorita 24/7</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-6 text-white">
              <div className="flex items-center space-x-2">
                <Users className="h-5 w-5 text-cyan-400" />
                <span className="font-semibold">{listeners}</span>
                <span className="text-sm text-gray-300">oyentes</span>
              </div>
              {isLive && (
                <div className="flex items-center space-x-2 px-3 py-1 bg-red-500 rounded-full">
                  <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                  <span className="text-sm font-semibold">EN VIVO</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          
          {/* Panel Principal */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Reproductor Principal */}
            <div className="bg-black/30 backdrop-blur-md rounded-xl p-6 border border-white/10">
              <div className="text-center">
                <div className="relative mx-auto w-48 h-48 mb-6">
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-full p-1">
                    <div className="w-full h-full bg-black rounded-full flex items-center justify-center">
                      {currentSong ? (
                        <div className={`text-white text-center ${isPlaying ? 'animate-spin' : ''}`}>
                          <Disc className="h-20 w-20 mx-auto mb-2" />
                          <div className="text-xs">
                            <div className="font-semibold truncate">{currentSong.title}</div>
                            <div className="text-gray-400 truncate">{currentSong.artist}</div>
                          </div>
                        </div>
                      ) : (
                        <div className="text-white text-center">
                          <Headphones className="h-20 w-20 mx-auto mb-2" />
                          <div className="text-sm text-gray-400">LaicaFM</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                {currentSong && (
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold text-white mb-2">{currentSong.title}</h2>
                    <p className="text-cyan-400 text-lg">{currentSong.artist}</p>
                  </div>
                )}
                
                {/* Controles */}
                <div className="flex justify-center items-center space-x-4">
                  <button
                    onClick={isPlaying ? pauseRadio : playRadio}
                    className="bg-gradient-to-r from-purple-500 to-cyan-500 hover:from-purple-600 hover:to-cyan-600 text-white p-4 rounded-full transition-all duration-200 transform hover:scale-105"
                  >
                    {isPlaying ? <Pause className="h-8 w-8" /> : <Play className="h-8 w-8" />}
                  </button>
                  
                  <button
                    onClick={nextSong}
                    className="bg-white/10 hover:bg-white/20 text-white p-3 rounded-full transition-all duration-200"
                  >
                    <SkipForward className="h-6 w-6" />
                  </button>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    <Volume2 className="h-5 w-5 text-white" />
                    <input
                      type="range"
                      min="0"
                      max="100"
                      className="w-20 accent-cyan-400"
                      defaultValue="75"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="bg-black/30 backdrop-blur-md rounded-xl border border-white/10">
              <div className="flex border-b border-white/10">
                {[
                  { id: 'player', label: 'Reproductor', icon: Music },
                  { id: 'upload', label: 'Subir Música', icon: Upload },
                  { id: 'playlist', label: 'Playlists', icon: Disc }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 px-6 py-4 font-semibold transition-all duration-200 ${
                      activeTab === tab.id
                        ? 'text-cyan-400 border-b-2 border-cyan-400 bg-white/5'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    <tab.icon className="h-5 w-5" />
                    <span>{tab.label}</span>
                  </button>
                ))}
              </div>

              <div className="p-6">
                {/* Tab: Player */}
                {activeTab === 'player' && (
                  <div>
                    <h3 className="text-xl font-bold text-white mb-4">Lista de Reproducción Actual</h3>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {songs.map((song, index) => (
                        <div 
                          key={song.id}
                          className={`flex items-center justify-between p-3 rounded-lg transition-all duration-200 ${
                            currentSong?.id === song.id 
                              ? 'bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border border-cyan-400/50' 
                              : 'bg-white/5 hover:bg-white/10'
                          }`}
                        >
                          <div className="flex items-center space-x-3">
                            <div className="text-gray-400 w-8 text-center">{index + 1}</div>
                            <div>
                              <div className="text-white font-semibold">{song.title}</div>
                              <div className="text-gray-400 text-sm">{song.artist}</div>
                            </div>
                          </div>
                          <div className="text-gray-400 text-sm">
                            {Math.floor(song.duration / 60)}:{String(Math.floor(song.duration % 60)).padStart(2, '0')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tab: Upload */}
                {activeTab === 'upload' && (
                  <div>
                    <h3 className="text-xl font-bold text-white mb-4">Subir Nueva Música</h3>
                    <div className="space-y-4">
                      <div className="border-2 border-dashed border-white/20 rounded-lg p-8 text-center">
                        <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                        <input
                          type="file"
                          accept="audio/*"
                          onChange={(e) => setSelectedFile(e.target.files[0])}
                          className="hidden"
                          id="audio-upload"
                        />
                        <label
                          htmlFor="audio-upload"
                          className="cursor-pointer text-white hover:text-cyan-400 transition-colors"
                        >
                          <div className="text-lg font-semibold mb-2">
                            {selectedFile ? selectedFile.name : 'Selecciona un archivo de audio'}
                          </div>
                          <div className="text-gray-400 text-sm">
                            Formatos soportados: MP3, WAV, OGG, M4A
                          </div>
                        </label>
                      </div>
                      
                      {selectedFile && (
                        <button
                          onClick={handleFileUpload}
                          disabled={uploading}
                          className="w-full bg-gradient-to-r from-purple-500 to-cyan-500 hover:from-purple-600 hover:to-cyan-600 disabled:opacity-50 text-white py-3 rounded-lg font-semibold transition-all duration-200"
                        >
                          {uploading ? 'Subiendo...' : 'Subir Archivo'}
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Tab: Playlists */}
                {activeTab === 'playlist' && (
                  <div>
                    <h3 className="text-xl font-bold text-white mb-4">Gestión de Playlists</h3>
                    <div className="text-white">
                      <p className="text-gray-400">Próximamente: Gestión avanzada de playlists</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Chat Sidebar */}
          <div className="bg-black/30 backdrop-blur-md rounded-xl border border-white/10 h-fit">
            <div className="p-4 border-b border-white/10">
              <div className="flex items-center space-x-2">
                <MessageCircle className="h-5 w-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-white">Chat en Vivo</h3>
              </div>
            </div>
            
            <div className="h-64 overflow-y-auto p-4 space-y-3">
              {chatMessages.map((msg) => (
                <div key={msg.id} className="text-sm">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-cyan-400">{msg.username}:</span>
                    <span className="text-white">{msg.message}</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            
            <div className="p-4 border-t border-white/10">
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Tu nombre"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-cyan-400"
                />
                <div className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Escribe un mensaje..."
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    className="flex-1 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-cyan-400"
                  />
                  <button
                    onClick={sendMessage}
                    className="px-4 py-2 bg-gradient-to-r from-purple-500 to-cyan-500 hover:from-purple-600 hover:to-cyan-600 text-white rounded-lg font-semibold transition-all duration-200"
                  >
                    Enviar
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
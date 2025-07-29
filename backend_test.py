#!/usr/bin/env python3
"""
LaicaFM Backend Testing Suite
Tests all critical backend functionality for the radio station
"""

import requests
import json
import asyncio
import websockets
import os
import time
from pathlib import Path
import tempfile
import wave
import struct

# Get backend URL from frontend .env
def get_backend_url():
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

print(f"Testing LaicaFM Backend at: {API_URL}")

class LaicaFMTester:
    def __init__(self):
        self.session = requests.Session()
        self.uploaded_songs = []
        self.created_playlists = []
        
    def create_test_audio_file(self):
        """Create a simple test audio file"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        
        # Create a simple 1-second sine wave
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0
        
        frames = []
        for i in range(int(duration * sample_rate)):
            value = int(32767 * 0.3 * (i % int(sample_rate / frequency)) / int(sample_rate / frequency))
            frames.append(struct.pack('<h', value))
        
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(frames))
        
        return temp_file.name
    
    def test_api_root(self):
        """Test API root endpoint"""
        print("\n=== Testing API Root ===")
        try:
            response = self.session.get(f"{API_URL}/")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def test_song_upload(self):
        """Test song upload functionality"""
        print("\n=== Testing Song Upload ===")
        try:
            # Create test audio file
            test_file_path = self.create_test_audio_file()
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_song.wav', f, 'audio/wav')}
                response = self.session.post(f"{API_URL}/songs/upload", files=files)
            
            print(f"Upload Status: {response.status_code}")
            
            if response.status_code == 200:
                song_data = response.json()
                print(f"Uploaded Song: {song_data}")
                self.uploaded_songs.append(song_data)
                
                # Verify metadata extraction
                assert 'id' in song_data
                assert 'title' in song_data
                assert 'artist' in song_data
                assert 'filename' in song_data
                assert 'duration' in song_data
                print("✅ Song upload successful with metadata")
                return True
            else:
                print(f"❌ Upload failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False
        finally:
            # Cleanup test file
            try:
                os.unlink(test_file_path)
            except:
                pass
    
    def test_get_songs(self):
        """Test getting list of songs"""
        print("\n=== Testing Get Songs ===")
        try:
            response = self.session.get(f"{API_URL}/songs")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                songs = response.json()
                print(f"Found {len(songs)} songs")
                if songs:
                    print(f"Sample song: {songs[0]}")
                print("✅ Get songs successful")
                return True
            else:
                print(f"❌ Get songs failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Get songs error: {e}")
            return False
    
    def test_playlist_management(self):
        """Test playlist creation and management"""
        print("\n=== Testing Playlist Management ===")
        try:
            # Create playlist
            playlist_name = "Test Playlist LaicaFM"
            response = self.session.post(f"{API_URL}/playlists", params={"name": playlist_name})
            print(f"Create Playlist Status: {response.status_code}")
            
            if response.status_code == 200:
                playlist = response.json()
                print(f"Created Playlist: {playlist}")
                self.created_playlists.append(playlist)
                
                # Get playlists
                response = self.session.get(f"{API_URL}/playlists")
                if response.status_code == 200:
                    playlists = response.json()
                    print(f"Found {len(playlists)} playlists")
                    
                    # Add song to playlist if we have songs
                    if self.uploaded_songs and playlists:
                        playlist_id = playlists[0]['id']
                        song_id = self.uploaded_songs[0]['id']
                        response = self.session.post(f"{API_URL}/playlists/{playlist_id}/songs/{song_id}")
                        print(f"Add song to playlist status: {response.status_code}")
                        if response.status_code == 200:
                            print("✅ Playlist management successful")
                            return True
                    else:
                        print("✅ Playlist creation successful (no songs to add)")
                        return True
                        
            print(f"❌ Playlist management failed")
            return False
            
        except Exception as e:
            print(f"❌ Playlist error: {e}")
            return False
    
    def test_radio_control(self):
        """Test radio control endpoints"""
        print("\n=== Testing Radio Control ===")
        try:
            # Test radio status
            response = self.session.get(f"{API_URL}/radio/status")
            print(f"Radio Status: {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"Initial Status: {status}")
            
            # Test play radio
            response = self.session.post(f"{API_URL}/radio/play")
            print(f"Play Radio Status: {response.status_code}")
            if response.status_code == 200:
                play_result = response.json()
                print(f"Play Result: {play_result}")
            
            # Test pause radio
            response = self.session.post(f"{API_URL}/radio/pause")
            print(f"Pause Radio Status: {response.status_code}")
            if response.status_code == 200:
                pause_result = response.json()
                print(f"Pause Result: {pause_result}")
            
            # Test next song
            response = self.session.post(f"{API_URL}/radio/next")
            print(f"Next Song Status: {response.status_code}")
            if response.status_code == 200:
                next_result = response.json()
                print(f"Next Result: {next_result}")
            
            # Test final status
            response = self.session.get(f"{API_URL}/radio/status")
            if response.status_code == 200:
                final_status = response.json()
                print(f"Final Status: {final_status}")
                print("✅ Radio control endpoints working")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Radio control error: {e}")
            return False
    
    def test_chat_system(self):
        """Test chat system"""
        print("\n=== Testing Chat System ===")
        try:
            # Send a chat message
            username = "DJ LaicaFM"
            message = "¡Bienvenidos a LaicaFM! La mejor música en vivo."
            
            response = self.session.post(f"{API_URL}/chat/message", 
                                       params={"username": username, "message": message})
            print(f"Send Message Status: {response.status_code}")
            
            if response.status_code == 200:
                sent_message = response.json()
                print(f"Sent Message: {sent_message}")
                
                # Get chat messages
                response = self.session.get(f"{API_URL}/chat/messages")
                print(f"Get Messages Status: {response.status_code}")
                
                if response.status_code == 200:
                    messages = response.json()
                    print(f"Found {len(messages)} messages")
                    if messages:
                        print(f"Latest message: {messages[0]}")
                    print("✅ Chat system working")
                    return True
            
            print("❌ Chat system failed")
            return False
            
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return False
    
    def test_statistics(self):
        """Test statistics endpoint"""
        print("\n=== Testing Statistics ===")
        try:
            response = self.session.get(f"{API_URL}/stats/current")
            print(f"Stats Status: {response.status_code}")
            
            if response.status_code == 200:
                stats = response.json()
                print(f"Current Stats: {stats}")
                print("✅ Statistics working")
                return True
            else:
                print(f"❌ Statistics failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Statistics error: {e}")
            return False
    
    async def test_websocket(self):
        """Test WebSocket connection"""
        print("\n=== Testing WebSocket ===")
        try:
            # Convert HTTP URL to WebSocket URL
            ws_url = API_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
            print(f"Connecting to WebSocket: {ws_url}")
            
            async with websockets.connect(ws_url, timeout=10) as websocket:
                print("✅ WebSocket connected successfully")
                
                # Send a test message
                test_message = {
                    "type": "chat",
                    "username": "Test User",
                    "message": "Testing WebSocket connection"
                }
                await websocket.send(json.dumps(test_message))
                print("✅ Message sent via WebSocket")
                
                # Try to receive a message (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"✅ Received WebSocket message: {response}")
                except asyncio.TimeoutError:
                    print("⚠️ No immediate WebSocket response (this is normal)")
                
                return True
                
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🎵 Starting LaicaFM Backend Tests 🎵")
        print("=" * 50)
        
        results = {}
        
        # Test API endpoints
        results['api_root'] = self.test_api_root()
        results['song_upload'] = self.test_song_upload()
        results['get_songs'] = self.test_get_songs()
        results['playlist_management'] = self.test_playlist_management()
        results['radio_control'] = self.test_radio_control()
        results['chat_system'] = self.test_chat_system()
        results['statistics'] = self.test_statistics()
        
        # Test WebSocket
        try:
            results['websocket'] = asyncio.run(self.test_websocket())
        except Exception as e:
            print(f"❌ WebSocket test failed: {e}")
            results['websocket'] = False
        
        # Summary
        print("\n" + "=" * 50)
        print("🎵 LaicaFM Backend Test Results 🎵")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All backend tests passed! LaicaFM is ready to rock! 🎉")
        else:
            print("⚠️ Some tests failed. Check the logs above for details.")
        
        return results

if __name__ == "__main__":
    tester = LaicaFMTester()
    results = tester.run_all_tests()
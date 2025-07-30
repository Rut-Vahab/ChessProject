import pygame
import pathlib
from typing import Dict, Any
import threading

class SoundManager:
    """מנהל הקולות - Observer Pattern לטיפול באירועי קול"""
    
    def __init__(self, music_folder: pathlib.Path):
        self.music_folder = music_folder
        self.sounds = {}
        
        # אתחול pygame mixer לשמע
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._load_sounds()
            print("SoundManager initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize sound system: {e}")
            self.sounds = {}  # ריק אם אין תמיכה בשמע
    
    def _load_sounds(self):
        """טוען את קבצי הקול"""
        try:
            # טעינת קול תנועה
            move_path = self.music_folder / "move.wav"
            if move_path.exists():
                self.sounds['move'] = pygame.mixer.Sound(str(move_path))
                print(f"Loaded move sound from {move_path}")
            
            # טעינת קול לכידה
            capture_path = self.music_folder / "capture.wav"
            if capture_path.exists():
                self.sounds['capture'] = pygame.mixer.Sound(str(capture_path))
                print(f"Loaded capture sound from {capture_path}")
                
        except Exception as e:
            print(f"Error loading sounds: {e}")
    
    def play_sound(self, sound_name: str, volume: float = 0.7):
        """מנגן קול בצורה אסינכרונית"""
        if sound_name in self.sounds:
            try:
                # השמעה ב-thread נפרד כדי לא לעכב את המשחק
                def play_async():
                    sound = self.sounds[sound_name]
                    sound.set_volume(volume)
                    sound.play()
                
                threading.Thread(target=play_async, daemon=True).start()
            except Exception as e:
                print(f"Error playing sound {sound_name}: {e}")
    
    def on_move_made(self, event_data: Dict[str, Any]):
        """מתבצע כשכלי זז - Observer callback"""
        piece_type = event_data.get('piece_type', '')
        print(f"SoundManager: Playing move sound for {piece_type}")
        self.play_sound('move', volume=0.5)
    
    def on_piece_captured(self, event_data: Dict[str, Any]):
        """מתבצע כשכלי נאכל - Observer callback"""
        captured_piece = event_data.get('captured_piece_id', '')
        captured_by = event_data.get('captured_by', '')
        print(f"SoundManager: Playing capture sound - {captured_by} captured {captured_piece}")
        self.play_sound('capture', volume=0.8)
    
    def cleanup(self):
        """ניקוי משאבי השמע"""
        try:
            pygame.mixer.quit()
        except:
            pass

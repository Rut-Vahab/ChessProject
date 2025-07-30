import cv2
import numpy as np
import time
from typing import Dict, Any, List, Tuple
import random

class GameMessagesManager:
    """מנהל הודעות המשחק - Observer Pattern לטיפול באירועי הודעות"""
    
    def __init__(self):
        self.active_messages: List[Dict] = []
        self.game_started = False
        self.game_ended = False
        
        # הודעות תחילת משחק
        self.start_messages = [
            " Welcome to Kung-Fu Chess! ",
            " Capture the enemy king to win!",
            " Real-time chess - no turns!",
            " May the fastest strategist win!",
            " Battle begins NOW! "
        ]
        
        # הודעות סוף משחק
        self.end_messages = [
            " Game Over! What an epic battle! ",
            " Victory achieved through skill and speed! ",
            " The battlefield falls silent... ",
            " A new chess master emerges! ",
            " The hunt for the king is complete! "
        ]
        
        # הודעות במהלך המשחק
        self.action_messages = [
            " Great capture!",
            " Lightning fast move!",
            " Perfect positioning!",
            " The battle intensifies!",
            " Strike and counter-strike!",
            " Swift as the wind!",
            " Defensive mastery!",
            " Protecting the royal line!"
        ]
    
    def on_game_start(self, event_data: Dict[str, Any]):
        """מתבצע בתחילת המשחק"""
        if not self.game_started:
            self.game_started = True
            print("GameMessages: Game start event received")
            
            # הוספת הודעות תחילת משחק
            for i, message in enumerate(self.start_messages):
                start_time = event_data.get('timestamp', 0) + (i * 1500)  # כל הודעה אחרי 1.5 שניות
                duration = 3000  # 3 שניות
                
                self.active_messages.append({
                    'text': message,
                    'start_time': start_time,
                    'end_time': start_time + duration,
                    'type': 'start',
                    'color': (0, 255, 255),  # צהוב
                    'fade_in': True,
                    'fade_out': True
                })
    
    def on_game_end(self, event_data: Dict[str, Any]):
        """מתבצע בסוף המשחק"""
        if not self.game_ended:
            self.game_ended = True
            print("GameMessages: Game end event received")
            
            # ניקוי הודעות קיימות
            self.active_messages.clear()
            
            # הוספת הודעות סוף משחק
            for i, message in enumerate(self.end_messages):
                start_time = event_data.get('timestamp', 0) + (i * 2000)  # כל הודעה אחרי 2 שניות
                duration = 4000  # 4 שניות
                
                self.active_messages.append({
                    'text': message,
                    'start_time': start_time,
                    'end_time': start_time + duration,
                    'type': 'end',
                    'color': (255, 215, 0),  # זהב
                    'fade_in': True,
                    'fade_out': True
                })
    
    def on_piece_captured(self, event_data: Dict[str, Any]):
        """מתבצע כשכלי נאכל - הוספת הודעות אקשן"""
        if self.game_started and not self.game_ended:
            message = random.choice(self.action_messages)
            start_time = event_data.get('timestamp', 0)
            duration = 2000  # 2 שניות
            
            self.active_messages.append({
                'text': message,
                'start_time': start_time,
                'end_time': start_time + duration,
                'type': 'action',
                'color': (0, 255, 0),  # ירוק
                'fade_in': True,
                'fade_out': True
            })
    
    def on_move_made(self, event_data: Dict[str, Any]):
        """מתבצע כשמהלך נעשה - לפעמים הוספת הודעות מעודדות"""
        if self.game_started and not self.game_ended:
            # רק לפעמים (10% מהמהלכים) נוסיף הודעה
            if random.random() < 0.1:
                message = random.choice(self.action_messages)
                start_time = event_data.get('timestamp', 0)
                duration = 1500  # 1.5 שניות
                
                self.active_messages.append({
                    'text': message,
                    'start_time': start_time,
                    'end_time': start_time + duration,
                    'type': 'move',
                    'color': (255, 165, 0),  # כתום
                    'fade_in': True,
                    'fade_out': True
                })
    
    def draw_messages(self, img, current_time_ms):
        """מציירת את כל הההודעות הפעילות"""
        height, width = img.shape[:2]
        
        # סינון הודעות פעילות
        active_now = []
        for msg in self.active_messages:
            if msg['start_time'] <= current_time_ms <= msg['end_time']:
                active_now.append(msg)
            elif current_time_ms > msg['end_time']:
                # הודעה פגה - נסיר אותה
                continue
            else:
                # הודעה עדיין לא התחילה
                active_now.append(msg)
        
        self.active_messages = active_now
        
        # ציור ההודעות
        y_offset = 50
        for msg in active_now:
            if msg['start_time'] <= current_time_ms <= msg['end_time']:
                alpha = self._calculate_alpha(msg, current_time_ms)
                if alpha > 0:
                    self._draw_message(img, msg, y_offset, alpha)
                    y_offset += 60
    
    def _calculate_alpha(self, msg, current_time):
        """חישוב שקיפות ההודעה בהתאם לזמן"""
        total_duration = msg['end_time'] - msg['start_time']
        elapsed = current_time - msg['start_time']
        
        fade_duration = total_duration * 0.2  # 20% מהזמן לכל fade
        
        if msg['fade_in'] and elapsed < fade_duration:
            # Fade in
            return elapsed / fade_duration
        elif msg['fade_out'] and elapsed > (total_duration - fade_duration):
            # Fade out
            remaining = msg['end_time'] - current_time
            return remaining / fade_duration
        else:
            # גלוי מלא
            return 1.0
    
    def _draw_message(self, img, msg, y_pos, alpha):
        """מציירת הודעה בודדת עם אפקטים"""
        height, width = img.shape[:2]
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        thickness = 2
        
        # חישוב גודל הטקסט
        (text_width, text_height), baseline = cv2.getTextSize(msg['text'], font, font_scale, thickness)
        
        # מיקום הטקסט (במרכז אופקית)
        text_x = (width - text_width) // 2
        text_y = y_pos
        
        # יצירת overlay לשקיפות
        overlay = img.copy()
        
        # רקע עמום לטקסט
        padding = 20
        cv2.rectangle(overlay, 
                     (text_x - padding, text_y - text_height - padding),
                     (text_x + text_width + padding, text_y + baseline + padding),
                     (0, 0, 0), -1)
        
        # צללית לטקסט
        shadow_offset = 3
        cv2.putText(overlay, msg['text'], 
                   (text_x + shadow_offset, text_y + shadow_offset),
                   font, font_scale, (0, 0, 0), thickness + 1)
        
        # הטקסט עצמו
        cv2.putText(overlay, msg['text'], (text_x, text_y),
                   font, font_scale, msg['color'], thickness)
        
        # שילוב עם התמונה המקורית
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    
    def clear_all_messages(self):
        """מנקה את כל ההודעות"""
        self.active_messages.clear()
    
    def has_active_messages(self) -> bool:
        """בודק אם יש הודעות פעילות"""
        return len(self.active_messages) > 0

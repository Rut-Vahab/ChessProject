import cv2
import numpy as np
from typing import Dict, Any

class VictoryManager:
    """מנהל הניצחון - Observer Pattern לטיפול באירועי ניצחון"""
    
    def __init__(self):
        self.victory_announced = False
        self.winner = None
        self.victory_message = ""
        self.victory_display_start = None
        
    def on_king_captured(self, event_data: Dict[str, Any]):
        """מתבצע כשכלי נאכל - בודק אם זה מלך - Observer callback"""
        captured_piece_id = event_data.get('captured_piece_id', '')
        captured_by_id = event_data.get('captured_by', '')
        
        print(f"VictoryManager: Received capture event for piece: {captured_piece_id}")
        
        # בדיקה אם הכלי שנאכל הוא מלך
        if captured_piece_id.lower().startswith('k'):
            captured_king_color = captured_piece_id[1]  # W או B
            self.winner = "BLACK" if captured_king_color == 'W' else "WHITE"
            self.victory_message = f"{self.winner} WINS!"
            self.victory_announced = True
            self.victory_display_start = event_data.get('timestamp', 0)
            
            print(f" VICTORY ANNOUNCED! {self.winner} has won by capturing the {captured_king_color} king!")
        else:
            print(f"VictoryManager: Not a king capture, piece was: {captured_piece_id}")
    
    def draw_victory_overlay(self, img, current_time_ms):
        """מציירת הודעת ניצחון על המסך"""
        if not self.victory_announced:
            return
            
        # יצירת overlay עם שקיפות
        overlay = img.copy()
        height, width = img.shape[:2]
        
        # רקע כהה עם שקיפות
        cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 0), -1)
        
        # טקסט הניצחון הראשי - גדול ובולט
        main_text = f" {self.victory_message} "
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 3.0
        thickness = 8
        
        # חישוב מיקום הטקסט (במרכז)
        (text_width, text_height), baseline = cv2.getTextSize(main_text, font, font_scale, thickness)
        text_x = (width - text_width) // 2
        text_y = (height + text_height) // 2 - 50
        
        # ציור הטקסט עם צללית
        shadow_offset = 5
        cv2.putText(overlay, main_text, (text_x + shadow_offset, text_y + shadow_offset), 
                   font, font_scale, (0, 0, 0), thickness + 2)  # צללית שחורה
        
        # צבע הטקסט לפי הזוכה
        text_color = (0, 255, 255) if self.winner == "WHITE" else (255, 255, 0)  # צהוב ללבן, כחול לשחור
        cv2.putText(overlay, main_text, (text_x, text_y), 
                   font, font_scale, text_color, thickness)
        
        # חישוב זמן שנשאר (10 שניות)
        elapsed_seconds = (current_time_ms - (self.victory_display_start or current_time_ms)) / 1000
        remaining_seconds = max(0, 10 - elapsed_seconds)
        
        # טקסט משני עם זמן
        sub_text = f"Game will close in {remaining_seconds:.1f} seconds - Press ESC to exit now"
        sub_font_scale = 1.5
        sub_thickness = 3
        
        (sub_width, sub_height), _ = cv2.getTextSize(sub_text, font, sub_font_scale, sub_thickness)
        sub_x = (width - sub_width) // 2
        sub_y = text_y + 100
        
        # צללית לטקסט המשני
        cv2.putText(overlay, sub_text, (sub_x + 3, sub_y + 3), 
                   font, sub_font_scale, (0, 0, 0), sub_thickness + 1)
        cv2.putText(overlay, sub_text, (sub_x, sub_y), 
                   font, sub_font_scale, (255, 255, 255), sub_thickness)
        
        # עיגול מהבהב סביב ההודעה
        pulse = abs(int((elapsed_seconds * 1000 / 200) % 2))  # מהבהב כל 200ms
        if pulse:
            circle_radius = max(text_width, text_height) // 2 + 50
            cv2.circle(overlay, (width // 2, height // 2 - 25), circle_radius, text_color, 10)
        
        # שילוב ה-overlay עם התמונה המקורית עם שקיפות
        alpha = 0.85  # שקיפות
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    
    def is_victory(self) -> bool:
        """בודק אם יש ניצחון"""
        return self.victory_announced
    
    def get_winner(self) -> str:
        """מחזיר את הזוכה"""
        return self.winner if self.victory_announced else ""

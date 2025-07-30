from typing import Dict, Any


class ScoreBoard:
    """
    מחלקה שעוקבת אחרי הניקוד על בסיס כלים שנאכלו
    """
    
    # ערכי הכלים
    PIECE_VALUES = {
        'P': 1,  # חייל (Pawn)
        'N': 3,  # פרש (Knight) 
        'B': 3,  # רץ (Bishop)
        'R': 5,  # צריח (Rook)
        'Q': 9,  # מלכה (Queen)
        'K': 0   # מלך (King) - בדרך כלל לא נופל אבל אם כן...
    }
    
    def __init__(self):
        # ניקוד לכל שחקן - W = לבן, B = שחור
        self.scores = {'W': 0, 'B': 0}
        self.captured_pieces = {'W': [], 'B': []}  # רשימת הכלים שנאכלו
    
    def on_piece_captured(self, capture_data: Dict[str, Any]):
        """
        פונקציה שתיקרא כשכלי נאכל
        
        Args:
            capture_data: מידע על הכלי שנאכל - {'captured_piece_id', 'captured_by', 'timestamp'}
        """
        print(f"ScoreBoard received capture event: {capture_data}")
        
        captured_piece_id = capture_data.get('captured_piece_id', '')
        captured_by = capture_data.get('captured_by', '')
        
        if not captured_piece_id or not captured_by:
            print("Invalid capture data received")
            return
        
        print(f"Processing capture: {captured_by} captured {captured_piece_id}")
        
        # פיצוח פורמט המזהה: 'RB_1' -> piece_type='R', color='B'
        if '_' in captured_piece_id and len(captured_piece_id.split('_')[0]) >= 2:
            piece_part = captured_piece_id.split('_')[0]  # 'RB'
            piece_type = piece_part[0]  # 'R'
            captured_color = piece_part[1]  # 'B'
        else:
            # פורמט חלופי: נסה לפרש ישירות
            piece_type = captured_piece_id[0] if captured_piece_id else ''
            captured_color = captured_piece_id[1] if len(captured_piece_id) > 1 else ''
        
        # פיצוח מזהה התוקף
        if '_' in captured_by and len(captured_by.split('_')[0]) >= 2:
            attacking_part = captured_by.split('_')[0]  # 'PB'
            capturing_color = attacking_part[1]  # 'B'
        else:
            # פורמט חלופי
            capturing_color = captured_by[1] if len(captured_by) > 1 else ''
        
        print(f"Piece type: {piece_type}, Captured color: {captured_color}, Capturing color: {capturing_color}")
        
        if piece_type in self.PIECE_VALUES and captured_color and capturing_color:
            # הוספת נקודות לשחקן שביצע את הלכידה
            points = self.PIECE_VALUES[piece_type]
            old_score = self.scores[capturing_color]
            self.scores[capturing_color] += points
            new_score = self.scores[capturing_color]
            
            print(f"Score update: {capturing_color} score {old_score} -> {new_score} (+{points} points)")
            
            # שמירת הכלי שנאכל ברשימה
            self.captured_pieces[capturing_color].append({
                'piece': captured_piece_id,
                'points': points,
                'timestamp': capture_data.get('timestamp', 0)
            })
            
            print(f"Capture! {captured_by} captured {captured_piece_id} (+{points} points)")
            self.print_current_score()
        else:
            print(f"Unknown piece type or invalid data: {captured_piece_id}")
    
    def get_score(self, player: str) -> int:
        """מחזיר את הניקוד של שחקן מסוים"""
        return self.scores.get(player, 0)
    
    def get_score_difference(self) -> int:
        """מחזיר את ההפרש בניקוד (חיובי = לבן מוביל, שלילי = שחור מוביל)"""
        return self.scores['W'] - self.scores['B']
    
    def print_current_score(self):
        """מדפיס את המצב הנוכחי של הניקוד"""
        white_score = self.scores['W']
        black_score = self.scores['B']
        diff = white_score - black_score
        
        print(f"Score: White {white_score} - {black_score} Black", end="")
        if diff > 0:
            print(f" (White +{diff})")
        elif diff < 0:
            print(f" (Black +{abs(diff)})")
        else:
            print(" (Tied)")
    
    def print_captured_pieces(self):
        """מדפיס את כל הכלים שנאכלו"""
        print("\n=== Captured Pieces ===")
        for color in ['W', 'B']:
            color_name = "White" if color == 'W' else "Black"
            print(f"{color_name} captured:")
            for capture in self.captured_pieces[color]:
                print(f"  - {capture['piece']} ({capture['points']} pts)")
        print("=====================\n")


# דוגמה לבדיקה
if __name__ == "__main__":
    scoreboard = ScoreBoard()
    
    # דוגמה ללכידות
    test_captures = [
        {'captured_piece_id': 'PB1', 'captured_by': 'PW1', 'timestamp': 5000},
        {'captured_piece_id': 'NW1', 'captured_by': 'BB1', 'timestamp': 8000},
        {'captured_piece_id': 'RB1', 'captured_by': 'QW1', 'timestamp': 12000}
    ]
    
    for capture in test_captures:
        scoreboard.on_piece_captured(capture)
    
    scoreboard.print_captured_pieces()

from typing import List, Dict, Any
from datetime import datetime


class MoveHistory:
    """
    מחלקה שעוקבת אחרי כל המהלכים במשחק
    """
    
    def __init__(self):
        self.moves: List[Dict[str, Any]] = []
    
    def on_move_made(self, move_data: Dict[str, Any]):
        """
        פונקציה שתיקרא כשמהלך מתבצע
        
        Args:
            move_data: מידע על המהלך - {'piece_id', 'from', 'to', 'timestamp'}
        """
        move_entry = {
            'move_number': len(self.moves) + 1,
            'piece_id': move_data.get('piece_id', 'Unknown'),
            'from': move_data.get('from', ''),
            'to': move_data.get('to', ''),
            'timestamp': move_data.get('timestamp', 0),
            'time': datetime.now().strftime("%H:%M:%S")
        }
        
        self.moves.append(move_entry)
        print(f"Move recorded: {move_entry['piece_id']} from {move_entry['from']} to {move_entry['to']}")
    
    def get_moves(self) -> List[Dict[str, Any]]:
        """מחזיר את רשימת כל המהלכים"""
        return self.moves.copy()
    
    def get_last_moves(self, count: int = 5) -> List[Dict[str, Any]]:
        """מחזיר את המהלכים האחרונים"""
        return self.moves[-count:] if len(self.moves) >= count else self.moves
    
    def print_history(self):
        """מדפיס את כל ההיסטוריה"""
        print("\n=== Move History ===")
        for move in self.moves:
            print(f"{move['move_number']:2d}. {move['time']} - {move['piece_id']}: {move['from']} → {move['to']}")
        print("==================\n")


# דוגמה לבדיקה
if __name__ == "__main__":
    move_history = MoveHistory()
    
    # דוגמה למהלכים
    test_moves = [
        {'piece_id': 'PW1', 'from': 'e2', 'to': 'e4', 'timestamp': 1000},
        {'piece_id': 'PB1', 'from': 'e7', 'to': 'e5', 'timestamp': 2000},
        {'piece_id': 'NW1', 'from': 'g1', 'to': 'f3', 'timestamp': 3000}
    ]
    
    for move in test_moves:
        move_history.on_move_made(move)
    
    move_history.print_history()

import asyncio
import websockets
import json
import time
import pathlib
from typing import Dict, List, Optional, Tuple, Any
from EventManager import EventManager
from MoveHistory import MoveHistory
from VictoryManager import VictoryManager
from ScoreBoard import ScoreBoard
from Moves import Moves
import os


class GameState:
    """מחלקה המנהלת את מצב המשחק המרכזי"""
    
    def __init__(self):
        # הלוח הפנימי - מיקום -> piece_id
        self.board_state = {
            "a8": "RB", "b8": "NB", "c8": "BB", "d8": "KB", "e8": "QB", "f8": "BB", "g8": "NB", "h8": "RB",
            "a7": "PB", "b7": "PB", "c7": "PB", "d7": "PB", "e7": "PB", "f7": "PB", "g7": "PB", "h7": "PB",
            "a2": "PW", "b2": "PW", "c2": "PW", "d2": "PW", "e2": "PW", "f2": "PW", "g2": "PW", "h2": "PW",
            "a1": "RW", "b1": "NW", "c1": "BW", "d1": "KW", "e1": "QW", "f1": "BW", "g1": "NW", "h1": "RW",
        }
        
        # מנהלי אירועים ומשחק
        self.event_manager = EventManager()
        self.move_history = MoveHistory()
        self.scoreboard = ScoreBoard()
        self.victory_manager = VictoryManager()
        
        # טעינת חוקי תזוזה בסיסיים - רק עבור הסוס להתחלה
        self.piece_moves = {}
        pieces_dir = pathlib.Path("../pieces")
        
        # נטען רק את הסוסים כדי לבדוק שזה עובד
        for piece_type in ["NW", "NB"]:
            moves_file = pieces_dir / piece_type / "moves.txt"
            if moves_file.exists():
                try:
                    self.piece_moves[piece_type] = Moves(moves_file, (8, 8))
                except Exception as e:
                    pass
        
    
        self.event_manager.subscribe("move_made", self.move_history.on_move_made)
        self.event_manager.subscribe("piece_captured", self.scoreboard.on_piece_captured)
        self.event_manager.subscribe("piece_captured", self.victory_manager.on_king_captured)
        
        # KungFu Chess - אין תורות!
        self.game_started = False
        self.start_time = time.time()

    def should_promote_pawn(self, piece_type: str, to_pos: str) -> bool:
        """בדיקה אם חייל צריך להיות מקודם למלכה"""
        if not piece_type.startswith('P'):  # לא חייל
            return False
            
        row = int(to_pos[1])  # מספר השורה
        
        # חייל לבן מגיע לשורה 8 (העליונה)
        if piece_type.endswith('W') and row == 8:
            return True
            
        # חייל שחור מגיע לשורה 1 (התחתונה)
        if piece_type.endswith('B') and row == 1:
            return True
            
        return False

    def promote_pawn_to_queen(self, piece_type: str) -> str:
        """המרת חייל למלכה"""
        if piece_type.endswith('W'):
            return piece_type.replace('PW', 'QW')
        else:
            return piece_type.replace('PB', 'QB')

    def is_valid_move(self, from_pos: str, to_pos: str, piece_id: str, player_color: str) -> Tuple[bool, str]:
        """בדיקת תקינות מהלך"""
        
        # בדיקות בסיסיות
        if not self.game_started:
            return False, "המשחק עדיין לא התחיל"
            
        if from_pos not in self.board_state or self.board_state[from_pos] is None:
            return False, f"אין כלי במיקום {from_pos}"
            
        piece_at_source = self.board_state[from_pos]
        piece_color = "white" if piece_at_source.endswith("W") else "black"
        
        if piece_color != player_color:
            return False, "לא ניתן להזיז כלי של השחקן השני"
            
        # מניעת מהלכים למקום עצמו - אסור לגמרי
        if from_pos == to_pos:
            return False, "לא ניתן להזיז כלי למקום עצמו"
            
        # בדיקת חוקי תזוזה - רק עבור סוסים כרגע (לשאר הכלים אפשר הכל)
        if piece_at_source in ["NW", "NB"]:  # סוס
            if not self.is_piece_move_valid(from_pos, to_pos, piece_at_source):
                return False, f"קפיצה לא חוקית עבור סוס {piece_at_source}"
        
        return True, "מהלך תקין"

    def convert_position_to_coords(self, pos: str) -> Tuple[int, int]:
        """המרת מיקום שחמט (a1, b2 וכו') לקואורדינטות מערך (0-7, 0-7)"""
        if len(pos) != 2:
            raise ValueError(f"מיקום לא תקין: {pos}")
        col = ord(pos[0]) - ord('a')  # a=0, b=1, ..., h=7
        row = int(pos[1]) - 1        # 1=0, 2=1, ..., 8=7
        return row, col

    def is_piece_move_valid(self, from_pos: str, to_pos: str, piece_type: str) -> bool:
        """בדיקה אם המהלך תקין עבור סוג הכלי הספציפי"""
        try:
            from_row, from_col = self.convert_position_to_coords(from_pos)
            to_row, to_col = self.convert_position_to_coords(to_pos)
            
            delta_row = to_row - from_row
            delta_col = to_col - from_col
            
            # אם אין כללים לכלי הזה, אפשר הכל
            if piece_type not in self.piece_moves:
                return True
                
            moves = self.piece_moves[piece_type]
            
            # בדיקה אם התזוזה תקינה עבור הכלי
            for allowed_delta in moves.rules:
                if (delta_row, delta_col) == allowed_delta:
                    return True
                    
            return False
            
        except Exception as e:
            # במקרה של שגיאה, לא לאפשר את המהלך
            return False

    def execute_move(self, from_pos: str, to_pos: str, piece_id: str, player_color: str) -> Tuple[bool, Dict[str, Any]]:
        """ביצוע מהלך ועדכון מצב המשחק"""
        
        is_valid, reason = self.is_valid_move(from_pos, to_pos, piece_id, player_color)
        
        if not is_valid:
            return False, {"error": reason}
            
        # שמירת הכלי שנלכד (אם יש)
        captured_piece = self.board_state.get(to_pos)
        
        # ביצוע המהלך
        piece = self.board_state[from_pos]
        self.board_state[from_pos] = None
        
        # בדיקה אם צריך לקדם חייל למלכה
        promoted = False
        if self.should_promote_pawn(piece, to_pos):
            piece = self.promote_pawn_to_queen(piece)
            promoted = True
            
        self.board_state[to_pos] = piece
        
        # יצירת מידע על המהלך
        move_data = {
            'piece_id': piece_id,
            'piece_type': piece,
            'from': from_pos,
            'to': to_pos,
            'timestamp': int((time.time() - self.start_time) * 1000),
            'player': player_color,
            'promoted': promoted
        }
        
        # פרסום אירוע מהלך
        self.event_manager.publish("move_made", move_data)
        
        # אם הייתה לכידה
        if captured_piece:
            capture_data = {
                'captured_piece': captured_piece,
                'by_piece': piece,
                'position': to_pos,
                'timestamp': move_data['timestamp']
            }
            self.event_manager.publish("piece_captured", capture_data)
            
        # הכנת תגובה ללקוחות
        response = {
            "type": "move_executed",
            "from": from_pos,
            "to": to_pos,
            "piece": piece,
            "captured": captured_piece,
            "promoted": promoted,
            "board_state": {k: v for k, v in self.board_state.items() if v is not None}
        }
        
        return True, response

    def get_full_state(self) -> Dict[str, Any]:
        """החזרת מצב מלא של המשחק"""
        return {
            "type": "full_state",
            "board": {k: v for k, v in self.board_state.items() if v is not None},
            "game_started": self.game_started,
            "move_history": self.move_history.get_last_moves(10),
            "score": self.scoreboard.get_scores() if hasattr(self.scoreboard, 'get_scores') else {}
        }

    def start_game(self):
        """התחלת המשחק"""
        self.game_started = True
        self.start_time = time.time()
        start_data = {
            'timestamp': 0,
            'message': 'Game Started!'
        }
        self.event_manager.publish("game_start", start_data)


class GameServer:
    """שרת המשחק המרכזי"""
    
    def __init__(self):
        self.clients = {}  # websocket -> {"color": str, "player_id": str}
        self.game_state = GameState()
        self.max_players = 2
        
    async def register_client(self, websocket) -> Optional[str]:
        """רישום לקוח חדש"""
        if len(self.clients) >= self.max_players:
            await websocket.send(json.dumps({
                "type": "error", 
                "message": "המשחק מלא - יש כבר 2 שחקנים"
            }))
            return None
            
        # הקצאת צבע
        if "white" not in [client["color"] for client in self.clients.values()]:
            color = "white"
        elif "black" not in [client["color"] for client in self.clients.values()]:
            color = "black"
        else:
            return None
            
        # רישום הלקוח
        player_id = f"player_{len(self.clients) + 1}"
        self.clients[websocket] = {"color": color, "player_id": player_id}
        
        # שליחת הודעת הקצאת צבע
        await websocket.send(json.dumps({
            "type": "assign_color", 
            "color": color,
            "player_id": player_id
        }))
        
        # שליחת מצב מלא של המשחק
        await websocket.send(json.dumps(self.game_state.get_full_state()))
        
        # התחלת המשחק מיד (אפילו עם שחקן אחד - לבדיקה)
        if not self.game_state.game_started:
            self.game_state.start_game()
            await self.broadcast_to_all({
                "type": "game_started",
                "message": "המשחק התחיל! אין תורות - כל שחקן יכול להזיז מתי שהוא רוצה!"
            })
        
        # הודעה נוספת אם יש 2 שחקנים
        if len(self.clients) == 2:
            await self.broadcast_to_all({
                "type": "info",
                "message": "שני שחקנים מחוברים - המשחק יכול להתחיל ברצינות!"
            })            
        return color

    async def handle_move_request(self, websocket, data: Dict[str, Any]):
        """טיפול בבקשת מהלך מלקוח"""
        if websocket not in self.clients:
            return
            
        client = self.clients[websocket]
        player_color = client["color"]
        
        from_pos = data.get("from")
        to_pos = data.get("to")
        piece_id = data.get("piece", "")
        
        # ביצוע המהלך בלוגיקה המרכזית
        success, result = self.game_state.execute_move(from_pos, to_pos, piece_id, player_color)
        
        if success:
            # שליחת עדכון לכל הלקוחות
            await self.broadcast_to_all(result)
            
            # בדיקת ניצחון
            if self.game_state.victory_manager.is_victory():
                await self.broadcast_to_all({
                    "type": "game_over",
                    "winner": "black" if player_color == "white" else "white",
                    "reason": "victory"
                })
        else:
            # שליחת שגיאה רק לשחקן שניסה לבצע את המהלך
            await websocket.send(json.dumps({
                "type": "move_error",
                "message": result["error"]
            }))

    async def broadcast_to_all(self, message: Dict[str, Any]):
        """שליחת הודעה לכל הלקוחות"""
        if self.clients:
            disconnected = []
            # יצירת רשימה קבועה של הלקוחות כדי למנוע שינוי במהלך הלולאה
            clients_list = list(self.clients.keys())
            for websocket in clients_list:
                try:
                    await websocket.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.append(websocket)
                    
            # הסרת לקוחות מנותקים
            for ws in disconnected:
                await self.remove_client(ws)

    async def remove_client(self, websocket):
        """הסרת לקוח מנותק"""
        if websocket in self.clients:
            client = self.clients[websocket]
            print(f"❌ שחקן {client['player_id']} ({client['color']}) התנתק")
            del self.clients[websocket]
            
            # הודעה ללקוחות הנותרים
            if self.clients:
                await self.broadcast_to_all({
                    "type": "player_disconnected",
                    "player": client["player_id"],
                    "color": client["color"]
                })

    async def handle_client(self, websocket):
        """טיפול בלקוח בודד"""
        try:
            # רישום הלקוח
            color = await self.register_client(websocket)
            if color is None:
                await websocket.close()
                return
                
            # האזנה להודעות מהלקוח
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"📨 קיבלתי מ-{self.clients[websocket]['player_id']}: {data}")
                    
                    if data.get("action") == "move":
                        await self.handle_move_request(websocket, data)
                    elif data.get("action") == "get_state":
                        await websocket.send(json.dumps(self.game_state.get_full_state()))
                    else:
                        print(f"⚠️ פעולה לא מוכרת: {data.get('action')}")
                        
                except json.JSONDecodeError:
                    print(f"❌ שגיאה בפענוח JSON: {message}")
                except Exception as e:
                    print(f"❌ שגיאה בטיפול בהודעה: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 חיבור נסגר")
        except Exception as e:
            print(f"❌ שגיאה בטיפול בלקוח: {e}")
        finally:
            await self.remove_client(websocket)

async def main():
    """פונקציה ראשית לשרת"""
    game_server = GameServer()
    port = int(os.getenv("PORT", 8765))
    print("🚀 מתחיל שרת משחק KungFu Chess על localhost:8765")

    async with websockets.serve(game_server.handle_client, "0.0.0.0", port):


    
    # async with websockets.serve(game_server.handle_client, "localhost", 8765):
        print("✅ השרת רץ ומחכה לחיבורים...")
        await asyncio.Future()  # רץ לנצח


if __name__ == "__main__":
    asyncio.run(main())

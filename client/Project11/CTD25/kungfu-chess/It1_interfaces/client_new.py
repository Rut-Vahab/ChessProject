import asyncio
import websockets
import json
import threading
import time
import queue
from pathlib import Path
from typing import Optional, Dict, Any
from Board import Board
from Game import Game
from img import Img


class GameClient:
    """לקוח המשחק שמתקשר עם השרת המרכזי"""
    
    def __init__(self, board: Board, pieces_root: Path, placement_csv: Path):
        self.board = board
        self.pieces_root = pieces_root
        self.placement_csv = placement_csv
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.player_color: Optional[str] = None
        self.player_id: Optional[str] = None
        self.game: Optional[Game] = None
        self.running = False
        self.move_queue = queue.Queue()  # תור למהלכים
        
    async def connect_to_server(self, uri: str = "ws://localhost:8765"):
        """התחברות לשרת המשחק"""
        try:
            print(f"🔌 מתחבר לשרת: {uri}")
            self.websocket = await websockets.connect(uri)
            self.running = True
            
            # קבלת הודעת הקצאת צבע
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "assign_color":
                self.player_color = data["color"]
                self.player_id = data.get("player_id", f"player_{self.player_color}")
                print(f"🎨 קיבלתי צבע: {self.player_color} (ID: {self.player_id})")
                
                # יצירת אובייקט המשחק
                self.game = Game(
                    board=self.board,
                    pieces_root=self.pieces_root,
                    placement_csv=self.placement_csv,
                    player_color=self.player_color,
                    websocket=self.websocket
                )
                
                # הוספת רפרנס ללקוח במחלקת Game
                self.game.client = self
                
                # הרצת המשחק בחוט נפרד
                threading.Thread(target=self.game.run, daemon=True).start()
                
                # התחלת עיבוד מהלכים באופן אסינכרוני
                move_task = asyncio.create_task(self.process_move_queue())
                
                # התחלת האזנה להודעות מהשרת
                await self.listen_for_messages()
                
            elif data.get("type") == "error":
                print(f"❌ שגיאה מהשרת: {data.get('message')}")
                
        except Exception as e:
            print(f"❌ שגיאה בחיבור לשרת: {e}")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()

    async def listen_for_messages(self):
        """האזנה להודעות מהשרת"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_server_message(data)
                
        except websockets.exceptions.ConnectionClosed:
            print("🔌 החיבור לשרת נסגר")
        except Exception as e:
            print(f"❌ שגיאה באזנה להודעות: {e}")
            import traceback
            traceback.print_exc()

    async def process_move_queue(self):
        """עיבוד מהלכים מהתור - רץ ללא הפסקה"""
        while self.running:
            try:
                if not self.move_queue.empty():
                    move_data = self.move_queue.get_nowait()
                    print(f"🔄 מעבד מהלך מהתור: {move_data}")
                    await self.send_move_to_server(
                        move_data["from"], 
                        move_data["to"], 
                        move_data["piece"]
                    )
                await asyncio.sleep(0.01)  # המתנה קצרה
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"❌ שגיאה בעיבוד מהלך מהתור: {e}")
                await asyncio.sleep(0.1)

    async def handle_server_message(self, data: Dict[str, Any]):
        """טיפול בהודעות מהשרת"""
        message_type = data.get("type")
        print(f"🔔 מטפל בהודעה מהשרת: {message_type} - {data}")
        
        if message_type == "full_state":
            print("📊 קיבלתי מצב מלא של המשחק")
            await self.apply_full_state(data)
            
        elif message_type == "move_executed":
            print(f"♟️ מהלך בוצע: {data.get('from')} -> {data.get('to')}")
            await self.apply_move_update(data)
            
        elif message_type == "game_started":
            print(f"🎮 {data.get('message')}")
            if self.game:
                self.game.game_started = True
                
        elif message_type == "game_over":
            winner = data.get("winner")
            reason = data.get("reason", "")
            print(f"🏆 המשחק נגמר! המנצח: {winner} ({reason})")
            if self.game:
                self.game.game_over = True
                self.game.winner = winner
                
        elif message_type == "move_error":
            print(f"❌ שגיאה במהלך: {data.get('message')}")
            
        elif message_type == "player_disconnected":
            disconnected_player = data.get("player")
            print(f"👋 שחקן {disconnected_player} התנתק")
            
        elif message_type == "info":
            print(f"ℹ️ מידע: {data.get('message')}")
            
        else:
            print(f"📨 הודעה לא מזוהה מהשרת: {data}")

    async def apply_full_state(self, state_data: Dict[str, Any]):
        """יישום מצב מלא של המשחק"""
        if not self.game:
            return
            
        board_state = state_data.get("board", {})
        current_turn = state_data.get("current_turn")
        
        # עדכון הלוח במשחק
        if hasattr(self.game, 'apply_board_state'):
            self.game.apply_board_state(board_state)
            
        print(f"📋 עדכנתי את מצב הלוח")

    async def apply_move_update(self, move_data: Dict[str, Any]):
        """יישום עדכון מהלך"""
        print(f"🔧 מתחיל יישום מהלך: {move_data}")
        
        if not self.game:
            print("❌ אין אובייקט משחק!")
            return
            
        from_pos = move_data.get("from")
        to_pos = move_data.get("to")
        piece = move_data.get("piece")
        captured = move_data.get("captured")
        promoted = move_data.get("promoted", False)
        
        print(f"📋 פרטי המהלך: {from_pos} -> {to_pos}, כלי: {piece}, נלכד: {captured}, קודם: {promoted}")
        
        # יישום המהלך במשחק המקומי
        if hasattr(self.game, 'apply_server_move'):
            print("✅ קורא לפונקציה apply_server_move")
            self.game.apply_server_move(from_pos, to_pos, piece, captured, promoted)
            
            # הקידום יטופל אוטומטית ב-apply_server_move
            if promoted:
                print(f"👑 השרת דיווח על קידום: {piece}")
        else:
            print("❌ אין פונקציה apply_server_move!")
            
        print(f"🔄 סיימתי יישום מהלך: {from_pos} -> {to_pos}")

    async def send_move_to_server(self, from_pos: str, to_pos: str, piece_id: str):
        """שליחת מהלך לשרת"""
        if not self.websocket or not self.running:
            print("❌ אין חיבור לשרת")
            return False
            
        message = {
            "action": "move",
            "from": from_pos,
            "to": to_pos,
            "piece": piece_id
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"📤 שלחתי מהלך לשרת: {from_pos} -> {to_pos}")
            return True
        except Exception as e:
            print(f"❌ שגיאה בשליחת מהלך: {e}")
            return False

    def send_move_from_thread(self, from_pos: str, to_pos: str, piece_id: str):
        """שליחת מהלך מחוט אחר (לשימוש מGame)"""
        print(f"🌐 קיבלתי בקשה לשלוח מהלך: {from_pos} -> {to_pos}")
        if self.running:
            # הוספת המהלך לתור
            move_data = {
                "from": from_pos,
                "to": to_pos,
                "piece": piece_id
            }
            self.move_queue.put(move_data)
            print(f"📤 הוספתי מהלך לתור: {from_pos} -> {to_pos}")
        else:
            print(f"❌ לא יכול לשלוח - לא רץ")


async def main():
    """פונקציה ראשית ללקוח"""
    # הגדרת נתיבים
    base_path = Path(__file__).resolve().parent
    pieces_root = base_path.parent / "PIECES"
    placement_csv = base_path / "board.csv"

    # יצירת הלוח
    board = Board(
        cell_H_pix=80,
        cell_W_pix=80,
        cell_H_m=1,
        cell_W_m=1,
        W_cells=8,
        H_cells=8,
        img=Img().read("../board.png", size=(640, 640))
    )

    # יצירת הלקוח והתחברות
    client = GameClient(board, pieces_root, placement_csv)
    await client.connect_to_server()


if __name__ == "__main__":
    asyncio.run(main())

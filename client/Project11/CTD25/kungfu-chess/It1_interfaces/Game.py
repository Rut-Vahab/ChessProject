import csv
import pathlib
import time
import queue
import cv2
import numpy as np
from typing import Dict, Tuple, Optional
import threading
import keyboard
from Board import Board
from Command import Command
from Piece import Piece
from img import Img
from PieceFactory import PieceFactory
from EventManager import EventManager
from MoveHistory import MoveHistory
from ScoreBoard import ScoreBoard
from VictoryManager import VictoryManager
from GameMessagesManager import GameMessagesManager
from SoundManager import SoundManager
from Physics import LongRestPhysics
import asyncio
import json
import websockets
import threading
class Game:
    def __init__(self, board: Board, pieces_root: pathlib.Path, placement_csv: pathlib.Path, player_color: str, websocket=None):
        self.board = board
        self.websocket = websocket
        self.player_color = player_color
        self.user_input_queue = queue.Queue()
        self.start_time = time.monotonic()
        self.piece_factory = PieceFactory(board, pieces_root)
        self.pieces: Dict[str, Piece] = {}
        self.pos_to_piece: Dict[Tuple[int, int], Piece] = {}
        self._current_board = None
        self._load_pieces_from_csv(placement_csv)
        
        # הגדרת מיקום התחלה של הסמנים לפי צבע השחקן
        if self.player_color == "white":
            self.focus_cell = (7, 4)  # התחלה במלך הלבן (שורה 7, עמודה 4)
        else:
            self.focus_cell = (0, 4)  # התחלה במלך השחור (שורה 0, עמודה 4)
            
        self._selection_mode = "source"  # עבור משתמש ראשון
        self._selected_source: Optional[Tuple[int, int]] = None
        
        if self.player_color == "black":
            self.focus_cell2 = (0, 4)  # התחלה במלך השחור
        else:
            self.focus_cell2 = (7, 4)  # התחלה במלך הלבן
            
        self._selection_mode2 = "source"
        self._selected_source2: Optional[Tuple[int, int]] = None 
        self._lock = threading.Lock()
        self._running = True
        self.event_manager = EventManager()
        self.move_history = MoveHistory()
        self.scoreboard = ScoreBoard()
        self.victory_manager = VictoryManager()
        self.messages_manager = GameMessagesManager()
        self.sound_manager = SoundManager(pathlib.Path("../MUSIC"))
        
        self.event_manager.subscribe("move_made", self.move_history.on_move_made)
        self.event_manager.subscribe("piece_captured", self.scoreboard.on_piece_captured)
        self.event_manager.subscribe("piece_captured", self.victory_manager.on_king_captured)  # בדיקת לכידת מלך
        
        self.event_manager.subscribe("game_start", self.messages_manager.on_game_start)
        self.event_manager.subscribe("game_end", self.messages_manager.on_game_end)
        self.event_manager.subscribe("piece_captured", self.messages_manager.on_piece_captured)
        self.event_manager.subscribe("move_made", self.messages_manager.on_move_made)
        self.event_manager.subscribe("king_captured", self.victory_manager.on_king_captured)
        
        self.event_manager.subscribe("move_made", self.sound_manager.on_move_made)
        self.event_manager.subscribe("piece_captured", self.sound_manager.on_piece_captured)
        
        # הוספת תכונות חדשות לשרת
        self.client = None  # רפרנס ללקוח
        self.game_started = False
        self.game_over = False
        self.winner = None
        self.current_turn = "white"
    
    def _load_pieces_from_csv(self, csv_path: pathlib.Path):
        with csv_path.open() as f:
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader):
                for col_idx, code in enumerate(row):
                    code = code.strip()
                    if not code:
                        continue
                    cell = (row_idx, col_idx)
                    piece = self.piece_factory.create_piece(code, cell)
                    self.pieces[piece.get_unique()] = piece
                    self.pos_to_piece[cell] = piece

    def game_time_ms(self) -> int:
        return int((time.monotonic() - self.start_time) * 1000)

    def clone_board(self) -> Board:
        return self.board.clone()

    def start_keyboard_thread(self):
        def keyboard_loop():
            while self._running:
                time.sleep(0.05)
                with self._lock:
                    # --- טיפול בקלט למשתמש הראשון ---
                    if self.player_color == "white":
                        dy, dx = 0, 0
                        if keyboard.is_pressed('esc'):
                            self._running = False
                            break
                        if keyboard.is_pressed('left'):
                            dx = -1
                        elif keyboard.is_pressed('right'):
                            dx = 1
                        if keyboard.is_pressed('up'):
                            dy = -1
                        elif keyboard.is_pressed('down'):
                            dy = 1
                        if dx != 0 or dy != 0:
                            h, w = self.board.H_cells, self.board.W_cells
                            y, x = self.focus_cell
                            self.focus_cell = ((y + dy) % h, (x + dx) % w)
                            time.sleep(0.2)
                        if keyboard.is_pressed('enter'):
                            self._on_enter_pressed()
                            time.sleep(0.2)
                    elif self.player_color == "black":
                    # --- טיפול בקלט למשתמש השני ---
                        dy2, dx2 = 0, 0
                        if keyboard.is_pressed('a'):
                            dx2 = -1
                        elif keyboard.is_pressed('d'):
                            dx2 = 1
                        if keyboard.is_pressed('w'):
                            dy2 = -1
                        elif keyboard.is_pressed('s'):
                            dy2 = 1
                        if dx2 != 0 or dy2 != 0:
                            h, w = self.board.H_cells, self.board.W_cells
                            y2, x2 = self.focus_cell2
                            self.focus_cell2 = ((y2 + dy2) % h, (x2 + dx2) % w)
                            time.sleep(0.2)
                        if keyboard.is_pressed('space'):
                            self._on_space_pressed()
                            time.sleep(0.2)
        threading.Thread(target=keyboard_loop, daemon=True).start()

    def run(self):
        self.start_keyboard_thread()
        start_ms = self.game_time_ms()
        for piece in self.pieces.values():
            piece.reset(start_ms)
        game_start_data = {
            'timestamp': start_ms,
            'message': 'Game Started!'
        }
        self.event_manager.publish("game_start", game_start_data)
        victory_start_time = None
        while self._running:
            now = self.game_time_ms()
            if self.victory_manager.is_victory() or self._is_win():
                if victory_start_time is None:
                    victory_start_time = time.monotonic()
                elapsed_time = time.monotonic() - victory_start_time
                if elapsed_time >= 10.0:
                    break

            for piece in self.pieces.values():
                piece.update(now)
            self._update_position_mapping()
                
            while not self.user_input_queue.empty():
                cmd = self.user_input_queue.get()
                
                if cmd.type == "move":
                    src_cell = self.board.algebraic_to_cell(cmd.params[0])
                    dst_cell = self.board.algebraic_to_cell(cmd.params[1])
                elif cmd.type == "jump":
                    src_cell = self.board.algebraic_to_cell(cmd.params[0])
                    dst_cell = src_cell  # כי הקפיצה היא במקום
                    
                if src_cell not in self.pos_to_piece:
                    continue
                moving_piece = self.pos_to_piece[src_cell]
                if isinstance(moving_piece._state._physics, LongRestPhysics):
                    continue
                piece_id = moving_piece.get_id()
                if piece_id.startswith('P'):
                    color = piece_id[1]  # W או B
                    if(dst_cell == src_cell):
                        allowed_move = True
                    else:
                        dr = dst_cell[0] - src_cell[0]  # שינוי שורה
                        dc = dst_cell[1] - src_cell[1]  # שינוי עמודה
                        
                        if color == 'W':
                            forward_step = -1 
                        else:
                            forward_step = 1 
                        if dst_cell not in self.pos_to_piece:
                            if dr != forward_step or dc != 0:
                                continue  
                        else:
                            if dr != forward_step or abs(dc) != 1:
                                continue 
                if dst_cell in self.pos_to_piece:
                    target_piece = self.pos_to_piece[dst_cell]
                    if target_piece.get_id()[1] == moving_piece.get_id()[1]:
                        if(dst_cell == src_cell):
                            pass
                        else:
                            continue
                    else:    
                        capture_data = {
                            'captured_piece_id': target_piece.get_id(),  # שונה מ-get_unique() ל-get_id()
                            'captured_by': moving_piece.get_id(),        # שונה מ-get_unique() ל-get_id()
                            'timestamp': self.game_time_ms()
                        }
                        self.event_manager.publish("piece_captured", capture_data)
                        
                        if target_piece.get_id().lower().startswith('k'):
                            king_capture_data = {
                                'captured_piece_id': target_piece.get_id(),
                                'captured_by': moving_piece.get_id(),
                                'timestamp': self.game_time_ms()
                            }
                            self.event_manager.publish("king_captured", king_capture_data)
                            
                            removed = self.pieces.pop(target_piece.get_unique(), None)
                            
                        removed = self.pieces.pop(target_piece.get_unique(), None)
                    
                path_clear = True
                dx = dst_cell[1] - src_cell[1]
                dy = dst_cell[0] - src_cell[0]
                if dx != 0:
                    step_x = dx // abs(dx)
                else:
                    step_x = 0
                if dy != 0:
                    step_y = dy // abs(dy)
                else:
                    step_y = 0
                if (step_x != 0 or step_y != 0) and (abs(dx) == abs(dy) or dx == 0 or dy == 0):
                    cur_cell = (src_cell[0] + step_y, src_cell[1] + step_x)
                    while cur_cell != dst_cell:
                        if cur_cell in self.pos_to_piece:
                            path_clear = False
                            break
                        cur_cell = (cur_cell[0] + step_y, cur_cell[1] + step_x)
                if not path_clear:
                    continue
                    
                # הפרדה בין מהלכים אמיתיים לקפיצות במקום
                piece_id = moving_piece.get_id()
                from_pos = cmd.params[0]
                to_pos = cmd.params[1] if len(cmd.params) > 1 else cmd.params[0]
                
                # בדיקה נכונה של צבע הכלי - התו השני הוא הצבע
                if len(piece_id) >= 2:
                    piece_color_char = piece_id[1]  # W או B
                    piece_color = "white" if piece_color_char == 'W' else "black"
                else:
                    piece_color = "unknown"
                    
                if piece_color != self.player_color:
                    continue
                
                # בדיקה אם זה קפיצה במקום או מהלך אמיתי
                if cmd.type == "jump" or from_pos == to_pos:
                    # קפיצה במקום - מבוצעת מקומית
                    moving_piece.on_command(cmd, now)
                else:
                    # מהלך אמיתי - נשלח לשרת
                    self.send_move_to_server(from_pos, to_pos, piece_id)

                # הקוד הישן - כבר לא מבוצע מקומית
                # self.pos_to_piece[src_cell].on_command(cmd, now)
                # self.pos_to_piece[src_cell].on_command(cmd, now)

                # הקוד למלכה נועבר לשרת

            self._draw()

            cv2.imshow("Chess", self._current_board.img.img)
            cv2.waitKey(1)

        game_end_data = {
            'timestamp': self.game_time_ms(),
            'reason': 'victory' if self.victory_manager.is_victory() else 'normal_end'
        }
        self.event_manager.publish("game_end", game_end_data)

        self._announce_win()
        self._running = False
        
        self.sound_manager.cleanup()
        
        cv2.destroyAllWindows()

    def get_path_cells(self, src: Tuple[int, int], dst: Tuple[int, int]) -> list[Tuple[int, int]]:
        path = []
        dx = dst[1] - src[1]
        dy = dst[0] - src[0]
        step_x = dx // abs(dx) if dx != 0 else 0
        step_y = dy // abs(dy) if dy != 0 else 0

        cur = (src[0] + step_y, src[1] + step_x)
        while cur != dst:
            path.append(cur)
            cur = (cur[0] + step_y, cur[1] + step_x)
        return path

    def _update_position_mapping(self):
        self.pos_to_piece.clear()
        to_remove = set()

        for piece in list(self.pieces.values()): 
            x, y = map(int, piece._state._physics.get_pos())
            if not self.board.is_valid_cell(x, y):
                continue
            cell_x = x // self.board.cell_W_pix
            cell_y = y // self.board.cell_H_pix
            pos = (cell_y, cell_x)

            if pos in self.pos_to_piece:
                opponent = self.pos_to_piece[pos]
                if (not opponent._state._current_command or 
                    opponent._state._current_command.type in ["idle", "long_rest", "short_rest"] or
                        (piece._state._current_command and
                         piece._state._current_command.type not in ["idle", "long_rest", "short_rest"] and
                        opponent._state._physics.start_time > piece._state._physics.start_time)):

                    if opponent.get_unique() in self.pieces:
                        print(f"Position mapping capture: {piece.get_id()} captures {opponent.get_id()}")
                        capture_data = {
                            'captured_piece_id': opponent.get_id(),    # שונה מ-get_unique() ל-get_id()
                            'captured_by': piece.get_id(),            # שונה מ-get_unique() ל-get_id()
                            'timestamp': self.game_time_ms()
                        }
                        self.event_manager.publish("piece_captured", capture_data)
                        
                        if opponent.get_id().lower().startswith('k'):
                            king_capture_data = {
                                'captured_piece_id': opponent.get_id(),
                                'captured_by': piece.get_id(),
                                'timestamp': self.game_time_ms()
                            }
                            self.event_manager.publish("king_captured", king_capture_data)
                            
                            to_remove.add(opponent.get_unique())
                            print(f"*** KING CAPTURED IN POSITION MAPPING - VICTORY ANNOUNCED ***")
                    
                    self.pos_to_piece[pos] = piece
                    to_remove.add(opponent.get_unique())
                else:
                    to_remove.add(piece.get_unique())
            else:
                self.pos_to_piece[pos] = piece

        for k in to_remove:
            self.pieces.pop(k, None)  

    def _draw(self):
        board = self.clone_board()
        now_ms = self.game_time_ms()

        for piece in self.pieces.values():
            piece.draw_on_board(board, now_ms)

            if piece.is_queen_mode:
                x, y = map(int, piece._state._physics.get_pos())
                cell_x = x // self.board.cell_W_pix
                cell_y = y // self.board.cell_H_pix

                x1 = cell_x * self.board.cell_W_pix
                y1 = cell_y * self.board.cell_H_pix
                x2 = x1 + self.board.cell_W_pix
                y2 = y1 + self.board.cell_H_pix

                border_color = (0, 255, 255) 
                thickness = 2
                cv2.rectangle(board.img.img, (x1, y1), (x2, y2), border_color, thickness)

        y, x = self.focus_cell
        x1 = x * self.board.cell_W_pix
        y1 = y * self.board.cell_H_pix
        x2 = (x + 1) * self.board.cell_W_pix
        y2 = (y + 1) * self.board.cell_H_pix

        # הצגת סמנים לפי צבע השחקן
        if self.player_color == "white":
            # שחקן לבן - מראה רק את הסמן הצהוב שלו
            cv2.rectangle(board.img.img, (x1, y1), (x2, y2), (0, 255, 255), 2)
            
            # מראה בחירה של שחקן לבן
            if self._selected_source:
                sy, sx = self._selected_source
                sx1 = sx * self.board.cell_W_pix
                sy1 = sy * self.board.cell_H_pix
                sx2 = (sx + 1) * self.board.cell_W_pix
                sy2 = (sy + 1) * self.board.cell_H_pix
                cv2.rectangle(board.img.img, (sx1, sy1), (sx2, sy2), (0, 0, 255), 2)
                
        elif self.player_color == "black":
            # שחקן שחור - מראה רק את הסמן הכחול שלו
            y2_, x2_ = self.focus_cell2
            sx1 = x2_ * self.board.cell_W_pix
            sy1 = y2_ * self.board.cell_H_pix
            sx2 = (x2_ + 1) * self.board.cell_W_pix
            sy2 = (y2_ + 1) * self.board.cell_H_pix
            cv2.rectangle(board.img.img, (sx1, sy1), (sx2, sy2), (255, 0, 0), 2)
            
            # מראה בחירה של שחקן שחור
            if self._selected_source2:
                sy, sx = self._selected_source2
                sx1 = sx * self.board.cell_W_pix
                sy1 = sy * self.board.cell_H_pix
                sx2 = (sx + 1) * self.board.cell_W_pix
                sy2 = (sy + 1) * self.board.cell_H_pix
                cv2.rectangle(board.img.img, (sx1, sy1), (sx2, sy2), (0, 255, 0), 2)

        frame_size_vertical = 100 
        frame_size_horizontal = 300 
        board_h, board_w = board.img.img.shape[:2]
        new_h = board_h + 2 * frame_size_vertical
        new_w = board_w + 2 * frame_size_horizontal
        
        try:
            background_img = Img().read("../backGround.jpg", size=(new_w, new_h))
            framed_img = background_img.img.copy()
            
            board_channels = len(board.img.img.shape)
            background_channels = len(framed_img.shape)
            
            if board_channels == 3 and background_channels == 3:
                if board.img.img.shape[2] != framed_img.shape[2]:
                    if board.img.img.shape[2] == 3 and framed_img.shape[2] == 4:
                        framed_img = cv2.cvtColor(framed_img, cv2.COLOR_BGRA2BGR)
                    elif board.img.img.shape[2] == 4 and framed_img.shape[2] == 3:
                        board.img.img = cv2.cvtColor(board.img.img, cv2.COLOR_BGRA2BGR)
            
        except Exception as e:
            print(f"Could not load background image: {e}")
            if len(board.img.img.shape) == 3:
                framed_img = np.full((new_h, new_w, board.img.img.shape[2]), 255, dtype=np.uint8)
            else:
                framed_img = np.full((new_h, new_w), 255, dtype=np.uint8)
        
        framed_img[frame_size_vertical:frame_size_vertical+board_h, frame_size_horizontal:frame_size_horizontal+board_w] = board.img.img
        
        self._draw_move_tables(framed_img, frame_size_horizontal, frame_size_vertical, board_h)
        
        board.img.img = framed_img
        
        if self.victory_manager.is_victory():
            self.victory_manager.draw_victory_overlay(board.img.img, now_ms)
        
        self.messages_manager.draw_messages(board.img.img, now_ms)

        self._current_board = board

    def _draw_move_tables(self, img, frame_horizontal, frame_vertical, board_height):
        """מציירת טבלאות מהלכים בצדי הלוח בפורמט טבלאי"""
        
        moves = self.move_history.get_moves()
        
        white_moves = []
        black_moves = []
        
        for move in moves:
            piece_type_str = move.get('piece_type', '')
            piece_id = move.get('piece_id', '')
            timestamp = move.get('timestamp', 0)
            
            time_seconds = timestamp / 1000 if timestamp else 0
            hours = int(time_seconds // 3600)
            minutes = int((time_seconds % 3600) // 60)
            seconds = time_seconds % 60
            
            if hours > 0:
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:04.1f}"
            else:
                time_str = f"{minutes:02d}:{seconds:04.1f}"
            
            if piece_type_str and isinstance(piece_type_str, str) and len(piece_type_str) >= 2:
                color = piece_type_str[1]  # W או B
                piece_type = piece_type_str[0]  # P, N, B, R, Q, K
                move_data = {
                    'piece': piece_type,
                    'from': move.get('from', ''),
                    'to': move.get('to', ''),
                    'time': time_str
                }
                if color == 'W':
                    white_moves.append(move_data)
                elif color == 'B':
                    black_moves.append(move_data)
            else:
                if isinstance(piece_id, (int, float)):
                    piece_id = str(piece_id)
                
                if isinstance(piece_id, str) and len(piece_id) > 1:
                    color = piece_id[1]  # W או B
                    piece_type = piece_id[0]  # P, N, B, R, Q, K
                    move_data = {
                        'piece': piece_type,
                        'from': move.get('from', ''),
                        'to': move.get('to', ''),
                        'time': time_str
                    }
                    if color == 'W':
                        white_moves.append(move_data)
                    elif color == 'B':
                        black_moves.append(move_data)
                else:
                    move_data = {
                        'piece': '?',
                        'from': move.get('from', ''),
                        'to': move.get('to', ''),
                        'time': time_str
                    }
                    white_moves.append(move_data)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        small_font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        small_scale = 0.4
        thickness = 1
        text_color = (0, 0, 0)  # שחור
        header_color = (255, 255, 255)  # לבן
        background_color = (255, 255, 255, 200)  # לבן שקוף
        table_bg_color = (240, 240, 240)  # רקע טבלה
        border_color = (100, 100, 100)  # גבול טבלה
        
        def draw_text_with_background(img, text, pos, font, scale, color, thickness, bg_color=None):
            if bg_color:
                (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
                x, y = pos
                cv2.rectangle(img, (x-2, y-text_height-2), (x+text_width+2, y+baseline+2), bg_color[:3], -1)
            cv2.putText(img, text, pos, font, scale, color, thickness)
        
        def draw_table(img, moves, start_x, start_y, title, max_rows=14):
            col_widths = [30, 25, 35, 35, 65]  # #, כלי, מ, אל, זמן
            col_positions = [start_x]
            for width in col_widths[:-1]:
                col_positions.append(col_positions[-1] + width)
            
            row_height = 18
            header_height = 25
            
            table_width = sum(col_widths)
            table_height = header_height + (max_rows * row_height) + 10
            
            cv2.rectangle(img, (start_x-5, start_y-5), 
                         (start_x + table_width + 5, start_y + table_height + 5), 
                         table_bg_color, -1)
            
            cv2.rectangle(img, (start_x-5, start_y-5), 
                         (start_x + table_width + 5, start_y + table_height + 5), 
                         border_color, 2)
            
            cv2.rectangle(img, (start_x-3, start_y-3), 
                         (start_x + table_width + 3, start_y + header_height), 
                         border_color, -1)
            
            cv2.putText(img, title, (start_x + 10, start_y + 18), 
                       font, 0.7, header_color, 2)
            
            headers = ["#", "type ", " from ", " to", " time "]
            header_y = start_y + header_height + 15
            
            for i, header in enumerate(headers):
                cv2.putText(img, header, (col_positions[i] + 2, header_y), 
                           small_font, small_scale, text_color, 1)
            
            cv2.line(img, (start_x-3, header_y + 5), 
                    (start_x + table_width + 3, header_y + 5), border_color, 1)
            
            recent_moves = moves[-max_rows:] if len(moves) > max_rows else moves
            start_index = max(0, len(moves) - max_rows)
            
            for i, move in enumerate(recent_moves):
                row_y = header_y + 20 + (i * row_height)
                
                if i % 2 == 0:
                    cv2.rectangle(img, (start_x-3, row_y-12), 
                                 (start_x + table_width + 3, row_y + 6), 
                                 (250, 250, 250), -1)
                
                move_num = start_index + i + 1
                cv2.putText(img, f"{move_num}", (col_positions[0] + 2, row_y), 
                           small_font, small_scale, text_color, 1)
                
                cv2.putText(img, move['piece'], (col_positions[1] + 5, row_y), 
                           small_font, small_scale, text_color, 1)
                
                cv2.putText(img, move['from'], (col_positions[2] + 2, row_y), 
                           small_font, small_scale, text_color, 1)
                
                cv2.putText(img, move['to'], (col_positions[3] + 2, row_y), 
                           small_font, small_scale, text_color, 1)
                
                cv2.putText(img, move['time'], (col_positions[4] + 2, row_y), 
                           small_font, small_scale, text_color, 1)
                
                for j in range(1, len(col_positions)):
                    cv2.line(img, (col_positions[j]-1, row_y-12), 
                            (col_positions[j]-1, row_y + 6), border_color, 1)
        
        left_x = 10
        table_y = frame_vertical + 30
        draw_table(img, black_moves, left_x, table_y, "BLACK MOVES")
    
        right_x = frame_horizontal * 2 + 640 - 280
        draw_table(img, white_moves, right_x, table_y, "WHITE MOVES")
    
        captured_by_white = self.scoreboard.captured_pieces.get('W', [])
        captured_by_black = self.scoreboard.captured_pieces.get('B', [])
   
        white_score = self.scoreboard.get_score('W')
        black_score = self.scoreboard.get_score('B')

        captured_text_black = "pieces: " + "".join([cap['piece'][0] for cap in captured_by_black[-10:]])
        draw_text_with_background(img, captured_text_black, (left_x, frame_vertical + board_height - 70), 
                                font, 0.5, text_color, 1, background_color)
        
        score_text_black = f"score: {black_score}"
        score_y_pos = frame_vertical + board_height - 15
        draw_text_with_background(img, score_text_black, (left_x, score_y_pos), 
                                font, 1.0, text_color, 3, background_color)
        
        captured_text_white = "pieces: " + "".join([cap['piece'][0] for cap in captured_by_white[-10:]])
        draw_text_with_background(img, captured_text_white, (right_x, frame_vertical + board_height - 45), 
                                font, 0.5, text_color, 1, background_color)

        score_text_white = f"score: {white_score}"
        draw_text_with_background(img, score_text_white, (right_x, score_y_pos), 
                                font, 1.0, text_color, 3, background_color)
    def _is_win(self) -> bool:
        kings = [p for p in self.pieces.values() if p.get_id().lower().startswith("k")]
        return len(kings) <= 1

    def _announce_win(self):
        kings = [p for p in self.pieces.values() if p.get_id().lower().startswith("k")]
        
        if len(kings) == 0:
            print("Draw - No kings left!")
        elif len(kings) == 1:
            remaining_king = kings[0]
            king_color = remaining_king.get_id()[1]  # W או B
            if king_color == 'W':
                winner = "WHITE"
            else:
                winner = "BLACK"
        else:
            print("Game over.")
    def _on_enter_pressed(self):
        if self._selection_mode == "source":
            if self.focus_cell in self.pos_to_piece:
                piece = self.pos_to_piece[self.focus_cell]
                # בדיקה שהכלי שייך לשחקן הנוכחי
                piece_color = "white" if piece.get_id()[1] == 'W' else "black"
                if piece_color != self.player_color:
                    return
                self._selected_source = self.focus_cell
                self._selection_mode = "dest"
        elif self._selection_mode == "dest":
            if self._selected_source is None:
                return
            src_cell = self._selected_source
            dst_cell = self.focus_cell
            src_alg = self.board.cell_to_algebraic(src_cell)
            dst_alg = self.board.cell_to_algebraic(dst_cell)
            piece = self.pos_to_piece.get(src_cell)
            if piece:
                if src_cell == dst_cell:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="jump",
                        params=[src_alg]
                    )
                else:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="move",
                        params=[src_alg, dst_alg]
                    )

                self.user_input_queue.put(cmd)

            self._reset_selection()

    def _on_space_pressed(self):
        # טיפול בבחירה עבור משתמש שני
        if self._selection_mode2 == "source":
            if self.focus_cell2 in self.pos_to_piece:
                piece = self.pos_to_piece[self.focus_cell2]
                # בדיקה שהכלי שייך לשחקן הנוכחי
                piece_color = "white" if piece.get_id()[1] == 'W' else "black"
                if piece_color != self.player_color:
                    return
                src_alg = self.board.cell_to_algebraic(self.focus_cell2)
                self._selected_source2 = self.focus_cell2
                self._selection_mode2 = "dest"

        elif self._selection_mode2 == "dest":
            if self._selected_source2 is None:
                return
            src_cell = self._selected_source2
            dst_cell = self.focus_cell2
            src_alg = self.board.cell_to_algebraic(src_cell)
            dst_alg = self.board.cell_to_algebraic(dst_cell)
            piece = self.pos_to_piece.get(src_cell)
            if piece:
                if src_cell == dst_cell:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="jump",
                        params=[src_alg]
                    )
                else:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="move",
                        params=[src_alg, dst_alg]
                    )

                self.user_input_queue.put(cmd)
            self._reset_selection2()
    def _reset_selection(self):
        self._selection_mode = "source"
        self._selected_source = None

    def _reset_selection2(self):
        self._selection_mode2 = "source"
        self._selected_source2 = None

    def promote_to_queen(self, moving_piece, cell):
        """קידום חייל למלכה"""
        print(f"👑 מקדם חייל למלכה במיקום {cell}")
        
        # שמירת ה-ID הישן לפני השינוי
        old_id = moving_piece.get_id()
        old_unique = moving_piece.get_unique()
        print(f"🔄 משנה {old_id} למלכה...")
        
        # יצירת מצב חדש של מלכה (בהתאם לצבע)
        if old_id.startswith('PW'):
            queen_folder = "QW"
            new_id = "QW" + old_id[2:]
        elif old_id.startswith('PB'):
            queen_folder = "QB" 
            new_id = "QB" + old_id[2:]
        else:
            print(f"❌ שגיאה: לא ניתן לקדם כלי {old_id}")
            return
            
        queen_state = self.piece_factory._build_state_machine(
            self.piece_factory.pieces_root / queen_folder, cell
        )

        queen_state._physics.start_cell = cell
        queen_state._physics.pos = queen_state._physics.board.cell_to_world(cell)

        # עדכון הכלי
        moving_piece._state = queen_state
        moving_piece._state._moves = queen_state._moves  
        moving_piece.is_queen_mode = True
        moving_piece._id = new_id
        
        # עדכון המילון pieces עם ה-unique החדש
        if old_unique in self.pieces:
            del self.pieces[old_unique]
            self.pieces[moving_piece.get_unique()] = moving_piece
            
        print(f"✅ חייל קודם בהצלחה: {old_id} -> {new_id}")

    def apply_board_state(self, board_state: Dict[str, str]):
        """יישום מצב לוח מהשרת"""
        # ניקוי המיפוי הנוכחי
        self.pos_to_piece.clear()
        
        # עדכון הכלים לפי המצב החדש
        for algebraic_pos, piece_id in board_state.items():
            if piece_id:
                cell = self.board.algebraic_to_cell(algebraic_pos)
                # חיפוש הכלי במבנה הנתונים
                for piece in self.pieces.values():
                    if piece.get_id() == piece_id:
                        # עדכון המיקום של הכלי
                        piece._state._physics.start_cell = cell
                        piece._state._physics.pos = piece._state._physics.board.cell_to_world(cell)
                        self.pos_to_piece[cell] = piece
                        break

    def apply_server_move(self, from_pos: str, to_pos: str, piece_id: str, captured_piece: str = None, promoted: bool = False):
        """יישום מהלך שהגיע מהשרת"""
        from_cell = self.board.algebraic_to_cell(from_pos)
        to_cell = self.board.algebraic_to_cell(to_pos)
        
        # העברת הכלי
        if from_cell in self.pos_to_piece:
            piece = self.pos_to_piece[from_cell]
            original_piece_id = piece.get_id()
            
            # במקום פשוט להעביר את הכלי, נפעיל את פקודת התזוזה שלו
            current_time = self.game_time_ms()
            
            # בדיקה איזה סוג מהלך זה - כל הכלים מקבלים "move" רגיל
            # הפיזיקה תטפל בהבדלים (קפיצה מול החלקה)
            move_cmd = Command(
                timestamp=current_time,
                piece_id=piece.get_id(),
                type="move",
                params=[from_pos, to_pos]
            )
            
            # הפעלת הפקודה על הכלי
            if piece.is_command_possible(move_cmd):
                # הסרה מהמיקום הישן במיפוי רק אחרי שהפקודה מתחילה
                del self.pos_to_piece[from_cell]
                piece.on_command(move_cmd, current_time)
                # הוספת הכלי למיקום החדש במיפוי מיד
                self.pos_to_piece[to_cell] = piece
            else:
                # גיבוי - העברה פשוטה אם הפקודה לא עובדת
                del self.pos_to_piece[from_cell]
                self.pos_to_piece[to_cell] = piece
                piece._state._physics.start_cell = to_cell
                piece._state._physics.pos = piece._state._physics.board.cell_to_world(to_cell)
                piece.reset(current_time)
            
            # טיפול בקידום חייל למלכה אם השרת אמר שצריך
            if promoted:
                print(f"👑 השרת אמר לקדם חייל במיקום {to_pos}")
                # הכלי כבר במיקום החדש במיפוי, נוכל לקדם מיד
                print(f"🔍 בודק אם יש כלי במיקום {to_cell}: {to_cell in self.pos_to_piece}")
                if to_cell in self.pos_to_piece:
                    piece_to_promote = self.pos_to_piece[to_cell]
                    print(f"✅ מצאתי כלי לקידום: {piece_to_promote.get_id()}")
                    # נחכה רגע קצר שהאנימציה תתחיל ואז נקדם
                    def promote_after_delay():
                        time.sleep(0.2)  # המתנה קצרה לאנימציה
                        self.promote_to_queen(piece_to_promote, to_cell)
                    
                    import threading
                    threading.Thread(target=promote_after_delay, daemon=True).start()
                else:
                    print(f"❌ לא מצאתי כלי במיקום {to_cell} לקידום")
            
            # פרסום אירוע מהלך
            move_data = {
                'piece_id': piece_id,
                'piece_type': piece.get_id(),
                'from': from_pos,
                'to': to_pos,
                'timestamp': current_time
            }
            self.event_manager.publish("move_made", move_data)

    def send_move_to_server(self, from_pos: str, to_pos: str, piece_id: str):
        """שליחת מהלך לשרת דרך הלקוח"""
        if self.client:
            self.client.send_move_from_thread(from_pos, to_pos, piece_id)
   
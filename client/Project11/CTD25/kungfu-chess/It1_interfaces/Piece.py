import PhysicsFactory
from Board import Board
from Command import Command
from State import State
from typing import Optional
import cv2
import Moves
class Piece:
    nextCode = 0
    def __init__(self, piece_id: str, init_state: State):
        self._id = piece_id
        self._uniqueNumber = Piece.nextCode
        Piece.nextCode += 1
        self._state = init_state
        self._current_cmd: Optional[Command] = None
        count = 0
        self.is_queen_mode = False  # ברירת מחדל - לא מלכה


    def on_command(self, cmd: Command, now_ms: int):
        if self.is_command_possible(cmd):
            self._current_cmd = cmd
            self._state = self._state.process_command(cmd, now_ms)

    def is_command_possible(self, cmd: Command) -> bool:
        print(f"Checking command {cmd.type} for piece {self._id}")
        print("CMD PARAMS:", cmd.params)

        if self.is_queen_mode:
            src = self._state._physics.start_cell
            
            # מקבלים את היעד
            param = cmd.params[1]
            if isinstance(param, (tuple, list)):
                dst = tuple(param)       # אם זה כבר תא (0,1)
            else:
                dst = self._state._physics.board.algebraic_to_cell(param)  # אם זה מחרוזת כמו 'a4'

            # בודקים את המהלכים של המלכה
            legal = self._state._moves.get_moves(*src)  # בהמשך אפשר להרחיב ל-get_queen_moves אם קיים
            if dst not in legal:
                return False
            return True
        if cmd.type == "move":
            src = self._state._physics.start_cell
            dst = self._state._physics.board.algebraic_to_cell(cmd.params[1])
            legal = self._state._moves.get_moves(*src)
            if dst not in legal:
                return False
        # ✨ תוודא שיש תמיכה גם ב־jump

        if cmd.type == "jump":
            return cmd.type in self._state.transitions
        return cmd is not None and cmd.type in self._state.transitions
    def reset(self, start_ms: int):
        # def reset(self, start_ms: int):
        # אתחול אנימציה לכל הכלים - גם אלה שלא זזים
        idle_cmd = Command(start_ms, self._id, "idle", ["", ""])
        self._state._graphics.reset(idle_cmd)
       
        if self._current_cmd:
            self._state.reset(self._current_cmd)
    def update(self, now_ms: int):
        # עדכון האנימציה תמיד - גם אם הכלי לא זז
        self._state._graphics.update(now_ms)
        
        # if self._current_cmd:
        #     self._state.reset(self._current_cmd)

    def update(self, now_ms: int):
        self._state = self._state.update(now_ms)
        if self._state._physics.finished:
            next_state =  next(iter(self._state.transitions.keys()))
            new_cell = self._state._physics.get_pos_in_cell()
            cmd = Command(now_ms, self._id, next_state, [new_cell, new_cell])
            self.on_command(cmd, now_ms)

    def draw_on_board(self, board: Board, now_ms: int):
        pos = self._state._physics.get_pos()
        img = self._state._graphics.get_img().img
        if img is not None:
            h, w = img.shape[:2]
            x, y = int(pos[0]), int(pos[1])

            board_img = board.img.img

            # ✅ חישוב גבולות כדי למנוע חריגה גם מלמעלה וגם משמאל
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(board_img.shape[1], x + w)
            y2 = min(board_img.shape[0], y + h)

            # ✅ אם הכלי כולו מחוץ למסך – לא מציירים כלום
            if x1 >= x2 or y1 >= y2:
                return

            # ✅ חיתוך החלק שנכנס למסך בלבד
            piece_img = img[y1 - y:y2 - y, x1 - x:x2 - x]
            base = board_img[y1:y2, x1:x2]

            # התאמת ערוצים
            target_channels = base.shape[2]
            piece_img = self._match_channels(piece_img, target_channels)

            board_img[y1:y2, x1:x2] = self._blend(base, piece_img)

            if self.is_queen_mode:
                color = (0, 0, 0)
                thickness = 4
                cv2.rectangle(board_img, (x1, y1), (x2-1, y2-1), color, thickness)

    def _blend(self, base, overlay):
        alpha = 0.8  # Simple fixed alpha
        return cv2.addWeighted(overlay, alpha, base, 1 - alpha, 0)

    def _match_channels(self, img, target_channels=3):
        """Convert image to target_channels (3=BGR, 4=BGRA)."""
        if img.shape[2] == target_channels:
            return img
        if target_channels == 3 and img.shape[2] == 4:
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        if target_channels == 4 and img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        return img

    def get_id(self):
        return self._id

    def get_unique(self):
        return self._uniqueNumber

    def get_command(self):
        return self._state.get_command()

    def clone_to(self, cell: tuple[int, int], physics_factory: PhysicsFactory) -> "Piece":
        """
        Clone this piece to a new piece at a different cell.
        Graphics is copied, physics is recreated (new cell), moves are shared.
        """
        # מעתיק את הגרפיקה
        graphics_copy = self._state._graphics.copy()

        # יוצר פיזיקס חדש – משתמש בנתונים שכבר קיימים באובייקט
        state_name = self._state._physics.__class__.__name__.replace("Physics", "").lower()
        speed = getattr(self._state._physics, "speed", 1.0)
        # אין לנו cfg, אז נבנה מינימלי
        cfg = {"physics": {"speed_m_per_sec": speed}}

        new_physics = physics_factory.create(state_name, cell, cfg)

        # יוצר סטייט חדש
        new_state = State(self._state._moves, graphics_copy, new_physics)

        # מעתיק את הטרנזישנים הקיימים
        for event, target in self._state.transitions.items():
            new_state.set_transition(event, target)

        return Piece(self._id, new_state)
    def set_id(self, new_id):
        self.piece_id = new_id
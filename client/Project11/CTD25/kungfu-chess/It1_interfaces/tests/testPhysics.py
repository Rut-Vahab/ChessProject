# מייבאים את pytest כדי להריץ טסטים
import pytest

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# מייבאים את MagicMock כדי לדמות אובייקטים חיצוניים כמו Board ו-Command
from unittest.mock import MagicMock

# מייבאים את המחלקות שנבדוק
from Physics import IdlePhysics, MovePhysics, JumpPhysics, ShortRestPhysics, LongRestPhysics
from Command import Command

# ----------------------------------------------------------------------
# פיקסטורה (fixture) להכנה של Mock Board
# ----------------------------------------------------------------------
@pytest.fixture
def mock_board():
    """
    יוצר Mock למחלקת Board.
    כל קריאה לפונקציות של Board (כמו cell_to_world) תוחזר עם ערכים שנבחר.
    """
    board = MagicMock()
    board.cell_to_world.return_value = (1.0, 1.0)         # כל תא יוחזר כנקודה (1.0,1.0)
    board.algebraic_to_cell.side_effect = lambda x: (0, 0)  # כל מחרוזת אלגברית תהפוך ל-(0,0)
    board.world_to_cell.return_value = (5, 5)             # תמיד מחזיר תא (5,5)
    return board


# ----------------------------------------------------------------------
# טסטים ל- IdlePhysics
# ----------------------------------------------------------------------
def test_idle_physics_reset_and_update(mock_board):
    # יוצרים אובייקט IdlePhysics עם Mock של Board
    physics = IdlePhysics(start_cell=(0, 0), board=mock_board)

    # יוצרים Mock ל-Command עם פרמטרים שכוללים תא יעד
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.params = [[2, 2]]

    # מפעילים reset
    physics.reset(mock_cmd)

    # בודקים ש-start_cell השתנה בהתאם לפקודה
    assert physics.start_cell == (2, 2)

    # בודקים שהפונקציה של Board נקראה
    mock_board.cell_to_world.assert_called()

    # update תמיד מחזיר None ב-IdlePhysics
    assert physics.update(1000) is None


# ----------------------------------------------------------------------
# טסטים ל- MovePhysics
# ----------------------------------------------------------------------
def test_move_physics_flow(mock_board):
    # יוצרים MovePhysics עם Mock Board
    physics = MovePhysics(start_cell=(0, 0), board=mock_board)

    # מכינים פקודת Mock שמחזירה מחרוזות (אלגבריות) ל-algebraic_to_cell
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.params = ["a1", "a2"]

    # קוראים ל-reset
    physics.reset(mock_cmd)

    # בודקים שה-AlgebraicToCell נקראה פעמיים (ל- start ול-end)
    assert mock_board.algebraic_to_cell.call_count == 2

    # בודקים שה-pos התחילה כמו start_pos
    assert physics.pos == physics.start_pos

    # בודקים שה-update לא מחזיר Command לפני שהסתיים הזמן
    physics.start_time = 0
    physics.duration_ms = 1000
    assert physics.update(500) is None

    # בודקים שה-cmd מוחזר רק אחרי שהזמן הכולל הסתיים
    physics.start_time = 0
    physics.duration_ms = 0
    physics.finished = False
    result = physics.update(2000)
    assert result == mock_cmd


# ----------------------------------------------------------------------
# טסטים ל- JumpPhysics
# ----------------------------------------------------------------------
def test_jump_physics_update_and_reset(mock_board):
    # יוצרים JumpPhysics
    physics = JumpPhysics(start_cell=(0, 0), board=mock_board)

    # יוצרים Mock ל-Command
    mock_cmd = MagicMock(spec=Command)

    # קוראים ל-reset ומוודאים שלא נשבר
    physics.reset(mock_cmd)

    # לפני סיום הזמן – update מחזיר None
    physics.start_time = 0
    physics.jump_duration = 1000
    assert physics.update(500) is None

    # אחרי סיום הזמן – update מחזיר את הפקודה
    assert physics.update(2000) == mock_cmd


# ----------------------------------------------------------------------
# טסטים ל- ShortRestPhysics
# ----------------------------------------------------------------------
def test_short_rest_physics_update(mock_board):
    physics = ShortRestPhysics(start_cell=(0, 0), board=mock_board)
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.params = [[1, 1]]

    # קוראים ל-reset
    physics.reset(mock_cmd)

    # לפני סיום זמן המנוחה – None
    physics.start_time = 0
    physics.rest_duration = 500
    assert physics.update(200) is None

    # אחרי הזמן – הפקודה מוחזרת
    assert physics.update(600) == mock_cmd


# ----------------------------------------------------------------------
# טסטים ל- LongRestPhysics
# ----------------------------------------------------------------------
def test_long_rest_physics_update(mock_board):
    physics = LongRestPhysics(start_cell=(0, 0), board=mock_board)
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.piece_id = "P1"
    mock_cmd.params = [[3, 3]]

    # קוראים ל-reset
    physics.reset(mock_cmd)

    # לפני הזמן – מחזיר None
    physics.start_time = 0
    physics.rest_duration = 1500
    assert physics.update(1000) is None

    # אחרי הזמן – מחזיר Command חדש (לא את ה-Mock!)
    result = physics.update(2000)
    assert isinstance(result, Command)
    assert result.type == "idle"
    assert result.piece_id == "P1"

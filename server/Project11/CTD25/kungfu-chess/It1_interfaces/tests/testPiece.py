import pytest

from unittest.mock import MagicMock
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Piece import Piece
from Command import Command
from State import State
import PhysicsFactory

@pytest.fixture
def mock_state():
    # יוצר mock של State עם תכונות שהמחלקה משתמשת בהן
    state = MagicMock(spec=State)
    state._physics = MagicMock()
    state._physics.start_cell = (0, 0)
    state._physics.board = MagicMock()
    state._physics.board.algebraic_to_cell.return_value = (1, 1)
    state._physics.finished = True
    state._physics.get_pos_in_cell.return_value = (1, 1)
    state._physics.get_pos.return_value = (100, 100)

    # כאן ההבדל: _moves הוא Mock עם מתודה get_moves
    state._moves = MagicMock()
    state._moves.get_moves = MagicMock(return_value=[(1, 1)])

    state._graphics = MagicMock()
    state._graphics.get_img.return_value.img = MagicMock()
    state.transitions = {"move": "new_state"}

    state.process_command.return_value = state
    state.update.return_value = state
    state.get_command.return_value = MagicMock()
    state.set_transition = MagicMock()
    state.reset = MagicMock()

    return state

@pytest.fixture
def piece(mock_state):
    return Piece("P1", mock_state)

def test_on_command_calls_process_command(piece):
    cmd = MagicMock(spec=Command)
    cmd.type = "move"
    cmd.params = ["a1", "b2"]

    piece.is_command_possible = MagicMock(return_value=True)

    piece.on_command(cmd, 123)
    piece.is_command_possible.assert_called_once_with(cmd)
    assert piece._current_cmd == cmd
    piece._state.process_command.assert_called_once_with(cmd, 123)

def test_is_command_possible_true(piece, mock_state):
    cmd = MagicMock(spec=Command)
    cmd.type = "move"
    cmd.params = ["a1", "b2"]

    mock_state._moves.get_moves = MagicMock(return_value=[(1, 1)])
    mock_state.transitions = {"move": "new_state"}
    mock_state._physics.start_cell = (0, 0)
    mock_state._physics.board.algebraic_to_cell.return_value = (1, 1)

    assert piece.is_command_possible(cmd)

def test_is_command_possible_false_invalid_move(piece, mock_state):
    cmd = MagicMock(spec=Command)
    cmd.type = "move"
    cmd.params = ["a1", "c3"]  # ציון תא לא חוקי

    mock_state._moves.get_moves = MagicMock(return_value=[(1, 1)])  # רק (1,1) חוקי
    mock_state.transitions = {"move": "new_state"}
    mock_state._physics.start_cell = (0, 0)
    mock_state._physics.board.algebraic_to_cell.return_value = (2, 2)  # לא ברשימת חוקיים

    assert not piece.is_command_possible(cmd)

def test_reset_calls_state_reset(piece):
    cmd = MagicMock()
    piece._current_cmd = cmd
    piece.reset(100)
    piece._state.reset.assert_called_once_with(cmd)

def test_update_calls_on_command(piece, mock_state):
    mock_state._physics.finished = True
    mock_state.transitions = {"next_state": "something"}

    called = {}
    def fake_on_command(cmd, now_ms):
        called["called"] = True
        called["cmd"] = cmd
        called["now_ms"] = now_ms

    piece.on_command = fake_on_command
    piece._state.update = MagicMock(return_value=mock_state)

    piece.update(1000)
    assert called["called"] is True
    assert isinstance(called["cmd"], Command)
    assert called["now_ms"] == 1000

def test_draw_on_board_calls_cv2_methods(piece, mock_state):
    img_mock = MagicMock()
    img_mock.shape = (10, 10, 3)
    mock_state._graphics.get_img.return_value.img = img_mock
    mock_state._physics.get_pos.return_value = (0, 0)

    board_img_mock = MagicMock()
    board_img_mock.shape = (100, 100, 3)
    board_mock = MagicMock()
    board_mock.img.img = board_img_mock

    piece._blend = MagicMock(return_value="blended")
    piece._match_channels = MagicMock(return_value=img_mock)

    piece.draw_on_board(board_mock, 0)

    piece._match_channels.assert_called_once()
    piece._blend.assert_called_once()

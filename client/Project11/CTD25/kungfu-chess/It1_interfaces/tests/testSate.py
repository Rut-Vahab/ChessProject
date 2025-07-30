import pytest
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock
from State import State
from Command import Command

@pytest.fixture
def mock_objects():
    """יוצר אובייקטים מדומים לכל התלויות של State"""
    moves = MagicMock()
    graphics = MagicMock()
    physics = MagicMock()
    return moves, graphics, physics

def test_reset_calls_reset_on_graphics_and_physics(mock_objects):
    moves, graphics, physics = mock_objects
    state = State(moves, graphics, physics)

    cmd = MagicMock(spec=Command)
    state.reset(cmd)

    graphics.reset.assert_called_once_with(cmd)
    physics.reset.assert_called_once_with(cmd)
    assert state.get_command() == cmd

def test_update_stays_in_same_state_when_no_command(mock_objects):
    moves, graphics, physics = mock_objects
    state = State(moves, graphics, physics)

    physics.update.return_value = None  # physics לא מחזיר פקודה
    next_state = state.update(now_ms=123)

    graphics.update.assert_called_once_with(123)
    physics.update.assert_called_once_with(123)
    assert next_state is state  # נשאר באותו מצב

def test_update_transitions_to_next_state(mock_objects):
    moves, graphics, physics = mock_objects
    state = State(moves, graphics, physics)

    cmd = MagicMock(spec=Command)
    cmd.type = "MOVE"

    # יוצרים מצב יעד
    next_state = State(moves, graphics, physics)

    # מוסיפים טרנזישן למצב אחר
    state.set_transition("MOVE", next_state)

    # physics מחזיר פקודה כדי לגרום למעבר
    physics.update.return_value = cmd

    returned_state = state.update(now_ms=555)

    # וידוא שנקרא reset על המצב הבא
    assert returned_state is next_state
    graphics.update.assert_called_once_with(555)
    physics.update.assert_called_once_with(555)
    assert next_state.get_command() == cmd

def test_can_transition_true_if_physics_returns_command(mock_objects):
    moves, graphics, physics = mock_objects
    state = State(moves, graphics, physics)

    physics.update.return_value = MagicMock(spec=Command)

    assert state.can_transition(999) is True

def test_can_transition_false_if_physics_returns_none(mock_objects):
    moves, graphics, physics = mock_objects
    state = State(moves, graphics, physics)

    physics.update.return_value = None

    assert state.can_transition(999) is False

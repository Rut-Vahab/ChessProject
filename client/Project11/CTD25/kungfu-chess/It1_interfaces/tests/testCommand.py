import pytest
from unittest.mock import MagicMock, create_autospec
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Command import Command

# === טסט 1: יצירת Mock של Command ובדיקת שימוש בשדות ===
def test_command_mock_basic_fields():
    # יוצרים Mock למחלקת Command
    mock_cmd = MagicMock(spec=Command)

    # קובעים ערכים לשדות כמו במופע אמיתי
    mock_cmd.timestamp = 1234
    mock_cmd.piece_id = "P1"
    mock_cmd.type = "Move"
    mock_cmd.params = ["a2", "a4"]

    # בודקים שהערכים קיימים ומוחזרים כמו שהגדרנו
    assert mock_cmd.timestamp == 1234
    assert mock_cmd.piece_id == "P1"
    assert mock_cmd.type == "Move"
    assert mock_cmd.params == ["a2", "a4"]


# === טסט 2: שימוש ב-autospec כדי לאפשר רק שדות אמיתיים של Command ===
def test_command_autospec():
    # create_autospec יוצר Mock שמדמה במדויק את Command (אין שדות מומצאים)
    mock_cmd = create_autospec(Command, instance=True)

    # אפשר לשנות ערכים קיימים
    mock_cmd.timestamp = 500
    mock_cmd.piece_id = "Q1"
    mock_cmd.type = "Jump"
    mock_cmd.params = ["d1", "h5"]

    # בדיקה שהשדות שונו
    assert mock_cmd.timestamp == 500
    assert mock_cmd.type == "Jump"


# === טסט 3: פונקציה שמשתמשת ב-Command – ונבדוק אותה עם Mock ===
def process_command(cmd: Command):
    """פונקציה פשוטה (לצורך בדיקה) שמחזירה טקסט שמתאר את הפקודה"""
    return f"{cmd.piece_id} does {cmd.type} to {cmd.params}"

def test_process_command_with_mock():
    # יוצרים Mock של Command
    mock_cmd = MagicMock(spec=Command)

    # מגדירים התנהגות של השדות
    mock_cmd.piece_id = "KN1"
    mock_cmd.type = "Jump"
    mock_cmd.params = ["g1", "f3"]

    # קוראים לפונקציה שלנו עם ה-Mock
    result = process_command(mock_cmd)

    # בודקים שהתוצאה השתמשה בנתונים מתוך ה-Mock
    assert result == "KN1 does Jump to ['g1', 'f3']"

    # בודקים שהשדות אכן נדרשו מתוך ה-Mock
    assert mock_cmd.piece_id == "KN1"
    assert mock_cmd.type == "Jump"
    assert mock_cmd.params == ["g1", "f3"]

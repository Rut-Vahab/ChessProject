import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# מייבאים pytest כדי להריץ טסטים
import pytest

# MagicMock כדי שנוכל ליצור אובייקטים מזויפים (Mocks)
from unittest.mock import MagicMock, patch

# מייבאים את המחלקה שנבדוק
from Graphics import Graphics
import pathlib


# ------------------------------------------------------------------
# טסט 1: בדיקה ש-_load_sprites טוען קבצים (באמצעות Mock)
# ------------------------------------------------------------------
def test_load_sprites_with_mock():
    mock_board = MagicMock()
    mock_board.cell_W_pix = 64
    mock_board.cell_H_pix = 64

    mock_folder = MagicMock()

    # מחזירים רשימת pathlib.Path אמיתיים (עם סיומות)
    fake_files = [
        pathlib.Path("sprite1.png"),
        pathlib.Path("sprite2.jpg"),
    ]
    mock_folder.iterdir.return_value = fake_files

    with patch("Graphics.Img") as mock_img_class:
        mock_img_instance = MagicMock()
        mock_img_class.return_value = mock_img_instance
        mock_img_instance.read.return_value = "FAKE_IMAGE"

        g = Graphics(sprites_folder=mock_folder, board=mock_board)

        assert g.sprites == ["FAKE_IMAGE", "FAKE_IMAGE"]


# ------------------------------------------------------------------
# טסט 2: בדיקת reset() עם Mock
# ------------------------------------------------------------------
def test_reset_sets_start_time_and_frame():
    # יוצרים Graphics עם Mock (כדי לא לטעון קבצים אמיתיים)
    mock_board = MagicMock()
    mock_folder = MagicMock()
    mock_folder.iterdir.return_value = []  # אין קבצים אמיתיים

    with patch("Graphics.Img") as mock_img_class:
        g = Graphics(sprites_folder=mock_folder, board=mock_board)

        # יוצרים Mock ל־Command
        mock_cmd = MagicMock()
        mock_cmd.timestamp = 12345

        # מפעילים reset
        g.reset(mock_cmd)

        # בודקים שה-start_time השתנה והפריים הנוכחי אפס
        assert g.start_time == 12345
        assert g.current_frame == 0


# ------------------------------------------------------------------
# טסט 3: בדיקת update() כשהזמן רץ בלולאה
# ------------------------------------------------------------------
def test_update_loops_frames():
    mock_board = MagicMock()
    mock_folder = MagicMock()

    # עושים Mock לרשימת תמונות (ניצור שלוש תמונות)
    fake_img_list = ["IMG1", "IMG2", "IMG3"]

    with patch("Graphics.Img") as mock_img_class:
        # נגרום לקריאה ל־_load_sprites להחזיר שלוש תמונות
        g = Graphics(sprites_folder=mock_folder, board=mock_board)
        g.sprites = fake_img_list
        g.frame_time_ms = 100  # כל פריים מתחלף כל 100ms
        g.loop = True
        g.start_time = 0

        # מפעילים update עם זמן שהפריים צריך להתקדם (נגיד 250ms)
        g.update(250)

        # 250ms / 100ms = 2.5 → צריך להיות פריים מס׳ 2 (אינדקס 2)
        assert g.current_frame == 2 % len(fake_img_list)  # = 2


# ------------------------------------------------------------------
# טסט 4: בדיקת update() כש-loop=False (לא אמור להתגלגל)
# ------------------------------------------------------------------
def test_update_non_loop_stops_on_last_frame():
    mock_board = MagicMock()
    mock_folder = MagicMock()

    with patch("Graphics.Img"):
        g = Graphics(sprites_folder=mock_folder, board=mock_board)
        g.sprites = ["IMG1", "IMG2", "IMG3"]
        g.frame_time_ms = 100
        g.loop = False
        g.start_time = 0

        # נגרום לזמן גדול יותר ממספר פריימים (500ms)
        g.update(500)

        # כי loop=False → current_frame אמור להיות האחרון (2)
        assert g.current_frame == len(g.sprites) - 1  # 2


# ------------------------------------------------------------------
# טסט 5: בדיקת get_img() מחזיר את התמונה הנוכחית
# ------------------------------------------------------------------
def test_get_img_returns_current_sprite():
    mock_board = MagicMock()
    mock_folder = MagicMock()

    with patch("Graphics.Img"):
        g = Graphics(sprites_folder=mock_folder, board=mock_board)
        g.sprites = ["IMG1", "IMG2", "IMG3"]

        # נבחר פריים נוכחי
        g.current_frame = 1

        # בודקים שה get_img מחזיר את התמונה הנכונה
        assert g.get_img() == "IMG2"

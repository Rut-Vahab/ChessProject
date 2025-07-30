# מייבא את pytest להרצת הבדיקות
import pytest

# מייבא MagicMock ליצירת אובייקטים מדומים (mock objects) במקום אובייקטים אמיתיים
from unittest.mock import MagicMock

# מייבא מודולים של מערכת ההפעלה וניהול נתיבים
import os
import sys

# מוסיף לתחילת רשימת הנתיבים של פייתון את התיקייה שמכילה את הקובץ הנוכחי, בגרסת תיקיית האב
# זאת כדי שפייתון ידע למצוא את המודולים כמו Board ו-img שנמצאים בתיקייה מעל
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# מייבא את מחלקת Board מתוך הקובץ Board.py שבתיקיית האב (It1_interfaces)
from Board import Board


# מגדיר fixture בשם mock_img שמייצר אובייקט מדומה (mock) עבור Img
@pytest.fixture
def mock_img():
    """יוצר אובייקט Img מזויף"""
    return MagicMock(name="MockImg")


# מגדיר fixture בשם board שמייצר אובייקט Board עם פרמטר img שמקבל את ה-mock שיצרנו
@pytest.fixture
def board(mock_img):
    """יוצר Board לבדיקה עם mock של Img"""
    return Board(
        cell_H_pix=100,  # גובה תא בפיקסלים
        cell_W_pix=100,  # רוחב תא בפיקסלים
        cell_H_m=1,      # גובה תא במטרים
        cell_W_m=1,      # רוחב תא במטרים
        W_cells=8,       # מספר תאים לרוחב
        H_cells=8,       # מספר תאים לגובה
        img=mock_img     # האובייקט המדומה (mock) של Img
    )


# טסט שבודק את הפונקציה clone של Board
def test_clone_creates_deepcopy(board):
    clone = board.clone()  # קורא לפונקציה clone שמחזירה עותק חדש של Board
    assert isinstance(clone, Board)    # בודק שהעותק הוא מופע מסוג Board
    assert clone is not board          # בודק שהעותק הוא אובייקט חדש ולא אותו אובייקט בזיכרון
    assert clone.img is not board.img  # בודק שה-img גם הוא עותק נפרד (העתקה עמוקה)


# טסט שבודק את הפונקציה cell_to_world שממירה תא (row,col) למיקום פיקסלים בעולם
def test_cell_to_world(board):
    assert board.cell_to_world((0, 0)) == (0, 0)       # תא (0,0) ממופה למיקום (0,0) בפיקסלים
    assert board.cell_to_world((1, 1)) == (100, 100)   # תא (1,1) ממופה למיקום (100,100)
    assert board.cell_to_world((2, 3)) == (300, 200)   # תא (2,3) ממופה למיקום (300,200)


# טסט שבודק את הפונקציה algebraic_to_cell שממירה תווים אלגבראיים (לדוגמה a1) לתא במטריצת לוח
def test_algebraic_to_cell(board):
    assert board.algebraic_to_cell("a1") == (7, 0)  # a1 היא התא בשורה 7 ועמודה 0 במטריצה
    assert board.algebraic_to_cell("h8") == (0, 7)  # h8 היא התא בשורה 0 ועמודה 7
    assert board.algebraic_to_cell("d5") == (3, 3)  # d5 היא התא בשורה 3 ועמודה 3


# טסט לפונקציה world_to_cell שממירה מיקום פיקסלים לתא במטריצה (row,col)
def test_world_to_cell(board):
    assert board.world_to_cell((0, 0)) == (0, 0)       # מיקום (0,0) בפיקסלים הוא תא (0,0)
    assert board.world_to_cell((150, 250)) == (2, 1)   # מיקום (150,250) בפיקסלים הוא תא (2,1)


# טסט לפונקציה cell_to_algebraic שממירה תא (row,col) לתווים אלגבראיים בשחמט
def test_cell_to_algebraic(board):
    assert board.cell_to_algebraic((7, 0)) == "a1"  # התא (7,0) הוא a1
    assert board.cell_to_algebraic((0, 7)) == "h8"  # התא (0,7) הוא h8
    assert board.cell_to_algebraic((3, 3)) == "d5"  # התא (3,3) הוא d5


# טסט לפונקציה is_valid_cell שבודקת האם מיקום בפיקסלים נמצא בדיוק על גבול תא
def test_is_valid_cell(board):
    assert board.is_valid_cell(100, 200)      # מיקום חוקי (מחלקים בדיוק בגודל התא)
    assert not board.is_valid_cell(105, 200)  # לא חוקי - x לא מתחלק בדיוק בגודל התא
    assert not board.is_valid_cell(100, 205)  # לא חוקי - y לא מתחלק בדיוק בגודל התא

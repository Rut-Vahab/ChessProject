# testImg.py

import sys
import os
import pytest                         # ספריית טסטים פופולרית ב־Python
import numpy as np                    # עבודה עם מטריצות/תמונות
import cv2                            # OpenCV – ספריית עיבוד תמונה
from unittest.mock import MagicMock  # בשביל MOCK של פונקציות

# מוסיפים את תיקיית האב (It1_interfaces) לנתיב כדי שנוכל לייבא את Img
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from img import Img

# === טסט ראשון: בדיקה של read() עם Mock ===
def test_read_with_mock(monkeypatch):
    fake_img = np.zeros((10, 10, 3), dtype=np.uint8)
    monkeypatch.setattr(cv2, "imread", lambda *a, **kw: fake_img)
    monkeypatch.setattr(cv2, "resize", lambda img, size, interpolation: img)
    img = Img().read("fake_path.png", size=(5, 5))
    assert isinstance(img, Img)
    assert img.img.shape == (10, 10, 3)

# === טסט שני: בדיקה של show() עם Mock ===
def test_show_is_mocked(monkeypatch):
    fake_img = np.ones((5, 5, 3), dtype=np.uint8)
    image = Img()
    image.img = fake_img
    mock_imshow = MagicMock()
    mock_waitKey = MagicMock()
    mock_destroy = MagicMock()
    monkeypatch.setattr(cv2, "imshow", mock_imshow)
    monkeypatch.setattr(cv2, "waitKey", mock_waitKey)
    monkeypatch.setattr(cv2, "destroyAllWindows", mock_destroy)
    image.show()
    mock_imshow.assert_called_once()
    mock_waitKey.assert_called_once()
    mock_destroy.assert_called_once()

# === טסט שלישי: בדיקה של put_text() עם Mock ===
def test_put_text(monkeypatch):
    fake_img = np.zeros((20, 2, 3), dtype=np.uint8)
    image = Img()
    image.img = fake_img
    mock_putText = MagicMock()
    monkeypatch.setattr(cv2, "putText", mock_putText)
    image.put_text("HELLO", 10, 10, 1.0)
    mock_putText.assert_called_once()
    args, kwargs = mock_putText.call_args
    assert args[1] == "HELLO"

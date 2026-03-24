"""Kittens animation - three kittens that follow mouse with eyes and head"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPixmap, QColor, QBrush
from PyQt6.QtCore import QObject, QTimer, QPoint, QRect, Qt


class KittenWidget(QWidget):
    """Three kittens that follow mouse movement with eyes and head"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Mouse position
        self._mouse_pos = QPoint(0, 0)

        # Kitten parameters - three kittens in bottom right
        self._kittens = [
            {"x": 100, "y": 0, "scale": 0.8},
            {"x": 200, "y": 20, "scale": 1.0},
            {"x": 320, "y": 10, "scale": 0.9},
        ]

        # Update timer for smooth animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(16)  # ~60 FPS

        # Start tracking mouse when mouse is in the widget area
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        """Track mouse movement"""
        self._mouse_pos = event.position()
        self.update()

    def paintEvent(self, event):
        """Draw the kittens"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # For this implementation, draw simple colored kitten-shaped blobs
        # In real use, you'd replace with actual kitten images
        for kitten in self._kittens:
            self._draw_kitten(painter, kitten)

    def _draw_kitten(self, painter, kitten):
        """Draw a single kitten"""
        # Center in widget bottom
        base_x = self.width() - 400 + kitten["x"]
        base_y = self.height() - 120 + kitten["y"]
        scale = kitten["scale"]

        # Calculate eye direction towards mouse
        mouse_x = self._mouse_pos.x() - (base_x + 20 * scale)
        mouse_y = self._mouse_pos.y() - (base_y + 30 * scale)
        import math
        dist = math.sqrt(mouse_x ** 2 + mouse_y ** 2)
        if dist > 0:
            # Clamp maximum movement
            max_move = 5 * scale
            dx = (mouse_x / dist) * max_move
            dy = (mouse_y / dist) * max_move
        else:
            dx = dy = 0

        # Draw body (light orange)
        body_rect = QRect(
            int(base_x), int(base_y),
            int(70 * scale), int(80 * scale)
        )
        painter.setBrush(QBrush(QColor(255, 200, 150)))
        painter.setPen(QColor(0, 0, 0))
        painter.drawRoundedRect(body_rect, 15, 15)

        # Draw head (darker orange)
        head_rect = QRect(
            int(base_x + 5 * scale), int(base_y - 20 * scale),
            int(60 * scale), int(40 * scale)
        )
        painter.setBrush(QBrush(QColor(255, 180, 120)))
        painter.drawRoundedRect(head_rect, 10, 10)

        # Draw eyes (white)
        eye_size = int(10 * scale)
        eye_spacing = int(20 * scale)
        left_eye_x = int(base_x + 10 * scale + dx / 2)
        right_eye_x = int(base_x + 10 + eye_spacing * scale + dx / 2)
        eye_y = int(base_y - 10 * scale + dy / 2)

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(left_eye_x, eye_y, eye_size, eye_size)
        painter.drawEllipse(right_eye_x, eye_y, eye_size, eye_size)

        # Draw pupils (black) - follow mouse
        pupil_size = int(4 * scale)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(left_eye_x + int(eye_size/2 - pupil_size/2) + int(dx/2),
                         eye_y + int(eye_size/2 - pupil_size/2) + int(dy/2),
                         pupil_size, pupil_size)
        painter.drawEllipse(right_eye_x + int(eye_size/2 - pupil_size/2) + int(dx/2),
                         eye_y + int(eye_size/2 - pupil_size/2) + int(dy/2),
                         pupil_size, pupil_size)

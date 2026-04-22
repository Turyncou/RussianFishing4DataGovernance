"""Toast notification widget for non-intrusive feedback"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect, QApplication
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtGui import QFont


class Toast(QWidget):
    """Lightweight toast notification for success/error/info messages"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_animation()
        self.hide()

    def _setup_ui(self):
        """Setup toast UI"""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(320)

        # Container widget with rounded background
        self.container = QWidget(self)
        self.container.setObjectName("toastContainer")
        self.container.setStyleSheet("""
            #toastContainer {
                background-color: rgba(40, 40, 40, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Title label
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.title_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self.title_label)

        # Message label
        self.message_label = QLabel()
        self.message_label.setFont(QFont("Segoe UI", 12))
        self.message_label.setStyleSheet("color: #cccccc;")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        # Status colors
        self._status_colors = {
            self.INFO: "#4a90e2",
            self.SUCCESS: "#5cb85c",
            self.WARNING: "#f0ad4e",
            self.ERROR: "#d9534f"
        }

    def _setup_animation(self):
        """Setup slide and fade animations"""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # Slide up animation
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(300)
        self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Fade animation
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        # Connect finished signal once at initialization
        self.fade_anim.finished.connect(self.hide)

        # Auto-hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._start_hide_animation)

    def show_message(self, title: str, message: str = "", status: str = INFO, duration: int = 3000):
        """Show toast notification

        Args:
            title: Main title text
            message: Optional detail message
            status: Toast type (info/success/warning/error)
            duration: Auto-hide duration in ms (0 = no auto-hide)
        """
        # Stop any running animations before starting new ones
        if self.slide_anim.state() == QPropertyAnimation.Running:
            self.slide_anim.stop()
        if self.fade_anim.state() == QPropertyAnimation.Running:
            self.fade_anim.stop()

        self.title_label.setText(title)
        if message:
            self.message_label.setText(message)
            self.message_label.show()
        else:
            self.message_label.hide()

        # Set status color
        color = self._status_colors.get(status, self._status_colors[self.INFO])
        self.title_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")

        # Adjust size to content before calculating position
        self.adjustSize()

        # Calculate position (bottom-right corner)
        parent = self.parentWidget()
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.right() - self.width() - 20
            y = parent_geo.bottom() - self.height() - 20
        else:
            # If no parent, position at bottom-right of primary screen
            screen_geo = QApplication.primaryScreen().availableGeometry()
            x = screen_geo.right() - self.width() - 20
            y = screen_geo.bottom() - self.height() - 20

        start_y = y + 30  # Start below final position
        self.move(x, start_y)

        # Animate slide up and fade in
        self.slide_anim.setStartValue(QPoint(x, start_y))
        self.slide_anim.setEndValue(QPoint(x, y))

        self.opacity_effect.setOpacity(0.0)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)

        self.show()
        self.slide_anim.start()
        self.fade_anim.start()
        self.raise_()

        # Start auto-hide timer
        if duration > 0:
            self.hide_timer.start(duration)

    def _start_hide_animation(self):
        """Start fade out animation"""
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.start()

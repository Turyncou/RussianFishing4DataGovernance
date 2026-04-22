"""Loading overlay widget for showing progress during long operations"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor


class LoadingOverlay(QWidget):
    """Semi-transparent loading overlay with spinner and message"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_animation()
        self.hide()

    def _setup_ui(self):
        """Setup overlay UI"""
        # Make overlay cover entire parent
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("""
            LoadingOverlay {
                background-color: rgba(0, 0, 0, 0.6);
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        # Loading spinner
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(200, 8)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        # Loading text
        self.message_label = QLabel("加载中...")
        self.message_label.setFont(QFont("Segoe UI", 14))
        self.message_label.setStyleSheet("color: #ffffff;")
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)

        # Detail text (optional)
        self.detail_label = QLabel("")
        self.detail_label.setFont(QFont("Segoe UI", 11))
        self.detail_label.setStyleSheet("color: #cccccc;")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.hide()
        layout.addWidget(self.detail_label)

    def _setup_animation(self):
        """Setup fade in/out animations"""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_in_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(200)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_out_anim.finished.connect(self._on_fade_out_finished)

    def show_loading(self, message: str = "加载中...", detail: str = ""):
        """Show loading overlay with message

        Args:
            message: Main loading message
            detail: Optional detail text
        """
        self.message_label.setText(message)
        if detail:
            self.detail_label.setText(detail)
            self.detail_label.show()
        else:
            self.detail_label.hide()

        self.show()
        self.raise_()
        self.fade_in_anim.start()

    def hide_loading(self):
        """Hide loading overlay with fade out animation"""
        self.fade_out_anim.start()

    def _on_fade_out_finished(self):
        """Callback when fade out animation finishes"""
        self.hide()

    def resizeEvent(self, event):
        """Resize overlay to cover entire parent"""
        if self.parentWidget():
            self.resize(self.parentWidget().size())
        super().resizeEvent(event)

"""
Floating overlay window to display recording duration.
Uses Windows API to exclude from screen capture so it's visible to user but not in recording.
"""
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer, QPoint, Slot, Signal
from PySide6.QtGui import QFont


class RecordingOverlay(QWidget):
    """Floating overlay window showing recording duration and audio controls.

    Uses Windows SetWindowDisplayAffinity API to exclude from screen capture,
    so it's always visible to the user but NEVER captured in screenshot/recording.
    This eliminates flickering from hide/show cycles.
    """

    audio_toggled = Signal(bool, bool)  # (is_mic, enabled)

    def __init__(self, record_mic_enabled: bool = False, record_system_enabled: bool = False):
        super().__init__()
        # Store current audio state
        self._mic_enabled = record_mic_enabled
        self._system_enabled = record_system_enabled

        # Window flags: frameless, always on top, tool tip (doesn't show in taskbar)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        # Transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Drag variables
        self._drag_position = None

        # Timer for updating duration
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_duration)
        self._start_time = None

        # Setup UI
        self._setup_ui()

        # Exclude from screen capture on Windows
        self._exclude_from_capture()

    def _setup_ui(self):
        """Setup the overlay UI with duration and audio toggles"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Duration label
        self._duration_label = QLabel("⏹️ 未录制")
        self._duration_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self._duration_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: rgba(220, 0, 0, 0.85);
                padding: 8px 16px;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self._duration_label)

        # Audio controls row
        self._audio_row = QWidget()
        audio_layout = QHBoxLayout(self._audio_row)
        audio_layout.setContentsMargins(0, 0, 0, 0)
        audio_layout.setSpacing(8)

        # Mic toggle button
        self._mic_btn = QPushButton()
        self._update_mic_button_style()
        self._mic_btn.clicked.connect(self._toggle_mic)
        audio_layout.addWidget(self._mic_btn)

        # System audio toggle button
        self._system_btn = QPushButton()
        self._update_system_button_style()
        self._system_btn.clicked.connect(self._toggle_system)
        audio_layout.addWidget(self._system_btn)

        audio_layout.addStretch()
        layout.addWidget(self._audio_row)

        self._update_audio_visibility()
        self._update_size()

        self.setLayout(layout)

        # Move to top-right corner by default
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            self.move(geometry.width() - self.width() - 20, 20)

    def _update_mic_button_style(self):
        """Update button style based on current state"""
        if self._mic_enabled:
            # Enabled - blue background
            self._mic_btn.setText("🎤 麦克风")
            self._mic_btn.setStyleSheet("""
                QPushButton {
                    color: #ffffff;
                    background-color: rgba(31, 111, 235, 0.9);
                    border: 2px solid rgba(31, 111, 235, 1);
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(31, 111, 235, 1.0);
                }
                QPushButton:pressed {
                    background-color: rgba(21, 79, 127, 1.0);
                }
            """)
        else:
            # Disabled - gray background
            self._mic_btn.setText("🎤 麦克风(关)")
            self._mic_btn.setStyleSheet("""
                QPushButton {
                    color: #cccccc;
                    background-color: rgba(80, 80, 80, 0.8);
                    border: 2px solid rgba(100, 100, 100, 0.8);
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(90, 90, 90, 0.9);
                }
                QPushButton:pressed {
                    background-color: rgba(60, 60, 60, 1.0);
                }
            """)

    def _update_system_button_style(self):
        """Update button style based on current state"""
        if self._system_enabled:
            # Enabled - blue background
            self._system_btn.setText("🔊 系统音")
            self._system_btn.setStyleSheet("""
                QPushButton {
                    color: #ffffff;
                    background-color: rgba(31, 111, 235, 0.9);
                    border: 2px solid rgba(31, 111, 235, 1);
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(31, 111, 235, 1.0);
                }
                QPushButton:pressed {
                    background-color: rgba(21, 79, 127, 1.0);
                }
            """)
        else:
            # Disabled - gray background
            self._system_btn.setText("🔊 系统音(关)")
            self._system_btn.setStyleSheet("""
                QPushButton {
                    color: #cccccc;
                    background-color: rgba(80, 80, 80, 0.8);
                    border: 2px solid rgba(100, 100, 100, 0.8);
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(90, 90, 90, 0.9);
                }
                QPushButton:pressed {
                    background-color: rgba(60, 60, 60, 1.0);
                }
            """)

    def _toggle_mic(self):
        """Toggle mic on click"""
        self._mic_enabled = not self._mic_enabled
        self._update_mic_button_style()
        self.audio_toggled.emit(True, self._mic_enabled)

    def _toggle_system(self):
        """Toggle system audio on click"""
        self._system_enabled = not self._system_enabled
        self._update_system_button_style()
        self.audio_toggled.emit(False, self._system_enabled)

    def _update_audio_visibility(self):
        """Update audio widget visibility - always show for better UX"""
        # Always show the buttons so user can toggle them even during recording
        self._audio_row.setVisible(True)
        self._update_size()

    def _update_size(self):
        """Update size based on whether audio controls are shown"""
        # Always show audio controls now
        self.resize(240, 120)

    def _exclude_from_capture(self):
        """Exclude this window from screen capture using Windows API.
        This makes the window visible to user but not captured by screenshots/recording.
        Only works on Windows.
        """
        import sys
        if sys.platform != "win32":
            return

        try:
            import ctypes
            from ctypes import wintypes

            # Get native window handle
            hwnd = self.winId()
            if not hwnd:
                return

            # Define Windows API
            user32 = ctypes.WinDLL('user32', use_last_error=True)

            # SetWindowDisplayAffinity constants
            WDA_EXCLUDEFROMCAPTURE = 0x11

            # Call the API
            success = user32.SetWindowDisplayAffinity(
                ctypes.c_void_p(int(hwnd)),
                WDA_EXCLUDEFROMCAPTURE
            )

            if success:
                print("Recording overlay excluded from screen capture successfully")
            else:
                print("Warning: Failed to exclude overlay from screen capture")
        except Exception as e:
            print(f"Warning: Could not exclude overlay from capture: {e}")

    @Slot()
    def start_recording(self):
        """Start recording and begin updating duration"""
        self._start_time = self._get_current_time()
        self._timer.start(1000)  # Update every second
        self.show()
        self._update_duration()

    @Slot()
    def stop_recording(self):
        """Stop recording and stop updating duration"""
        self._timer.stop()
        self._duration_label.setText("⏹️ 已停止")
        self.hide()

    def _get_current_time(self) -> float:
        """Get current time in seconds"""
        import time
        return time.time()

    def _update_duration(self):
        """Update the duration display"""
        if self._start_time is None:
            return
        elapsed = int(self._get_current_time() - self._start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        self._duration_label.setText(f"⏺️ 录制中 {minutes}:{seconds:02d}")

    def get_mic_enabled(self) -> bool:
        """Get current mic enabled state"""
        return self._mic_enabled

    def get_system_enabled(self) -> bool:
        """Get current system audio enabled state"""
        return self._system_enabled

    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton and self._drag_position is not None:
            new_position = event.globalPosition().toPoint() - self._drag_position
            self.move(new_position)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """Double click to hide (user can drag it out of way or hide)"""
        if event.button() == Qt.LeftButton:
            self.hide()
            event.accept()

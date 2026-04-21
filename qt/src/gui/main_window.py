"""Main application window for PySide6 implementation"""
import os
import shutil
import threading
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QProgressBar,
    QMessageBox, QSizePolicy
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QTimer, QSize, Signal, QUrl
from PySide6.QtGui import QIcon, QFont, QPalette, QBrush, QPixmap
from PySide6.QtMultimedia import QMediaPlayer

from src.data.persistence import (
    LotteryPersistence, ActivityPersistence, StoragePersistence, BaitPersistence,
    FriendLinkPersistence, CredentialsPersistence, AppSettingsPersistence,
    DailyTaskPersistence, create_auto_backup, list_backups
)
from src.core.models import FriendLink, ActivityType


class LoadingWidget(QWidget):
    """Loading screen widget displayed during startup"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        window = self.window()
        is_dark = True
        if hasattr(window, '_current_theme'):
            is_dark = (window._current_theme == "dark")

        if is_dark:
            self.setStyleSheet("""
                LoadingWidget {
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                LoadingWidget {
                    background-color: #f5f5f5;
                }
            """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Title
        title = QLabel("RF4 数据统计工具")
        title.setFont(QFont("Segoe UI", 32, QFont.Bold))
        if is_dark:
            title.setStyleSheet("color: #ffffff;")
        else:
            title.setStyleSheet("color: #000000;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Spacer
        spacer = QWidget()
        spacer.setFixedHeight(30)
        layout.addWidget(spacer)

        # Loading spinner using progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate mode
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(200, 8)
        if is_dark:
            self.progress.setStyleSheet("""
                QProgressBar {
                    background-color: #2d2d2d;
                    border-radius: 4px;
                    border: none;
                }
                QProgressBar::chunk {
                    background-color: #1f6feb;
                    border-radius: 4px;
                }
            """)
        else:
            self.progress.setStyleSheet("""
                QProgressBar {
                    background-color: #e0e0e0;
                    border-radius: 4px;
                    border: none;
                }
                QProgressBar::chunk {
                    background-color: #1f6feb;
                    border-radius: 4px;
                }
            """)
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        # Spacer
        spacer2 = QWidget()
        spacer2.setFixedHeight(20)
        layout.addWidget(spacer2)

        # Loading text
        label = QLabel("正在加载数据...")
        label.setFont(QFont("Segoe UI", 16))
        if is_dark:
            label.setStyleSheet("color: #cccccc;")
        else:
            label.setStyleSheet("color: #666666;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window"""

    data_loaded = Signal()

    def __init__(self, data_dir: str):
        super().__init__()
        # Enable true transparency for the entire window
        # This allows seeing through the window to what's behind when custom background is set
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Remove window frame border for completely frameless window
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        # Base background
        self.setStyleSheet("QMainWindow { background-color: rgba(0, 0, 0, 0); }");
        self.data_dir = data_dir
        self._frame_cache = {}
        self.current_widget = None

        # For dragging the frameless window
        self._drag_position = None

        # For window resizing from edges
        self._resize_margin = 8  # pixels from edge to detect resize
        self._resize_direction = None  # None, 'left', 'right', 'top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        self._resize_start_pos = None
        self._resize_start_geometry = None

        # Track double-click for maximize toggle
        self._last_click_time = 0
        self._double_click_interval = 300  # milliseconds

        # Persistence instances (will be initialized in background)
        self.lottery_persistence = None
        self.activity_persistence = None
        self.storage_persistence = None
        self.bait_persistence = None
        self.friend_link_persistence = None
        self.credentials_persistence = None
        self.app_settings_persistence = None
        self.backup_dir = None

        # Background image settings
        self._background_image_path = None
        self._background_opacity = 0.15
        self._background_label = None

        # Theme settings
        self._current_theme = "dark"

        # Income display settings
        self._show_income_info = False

        # Daily tasks persistence
        self.daily_task_persistence = None

        # Screen recorder settings
        self._screen_recorder = None
        self._screen_recorder_start_hotkey = "ctrl+shift+r"
        self._screen_recorder_stop_hotkey = "ctrl+shift+s"
        self._screen_recorder_save_path = None
        self._screen_recorder_record_mic = False
        self._screen_recorder_record_system = False

        # Special cursor on hover setting
        self._special_cursor_on_hover = True

        # Home page navigation buttons (for theme updates)
        self._home_buttons = []

        # Window setup
        self.setWindowTitle("RF4 Data Process")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)

        # Set default dark theme (will be overridden after loading settings)
        self._apply_dark_theme()

        # Create loading screen
        self._create_loading_screen()

        # Start background loading
        self._start_background_loading()

    def _apply_dark_theme(self):
        """Apply dark theme stylesheet"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(0, 0, 0, 0);
            }
            QWidget {
                background-color: rgba(0, 0, 0, 0);
            }
            QMenuBar {
                background-color: #252525;
                color: #ffffff;
            }
            QMenuBar::item {
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #1f6feb;
            }
            QMenu {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #3a3a3a;
            }
            QMenu::item:selected {
                background-color: #1f6feb;
            }
            QPushButton {
                background-color: #2c5aa0;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1a3d66;
            }
            QPushButton:pressed {
                background-color: #152f4f;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px;
            }
            QLineEdit:focus {
                border-color: #1f6feb;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #1f6feb;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                gridline-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 6px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #555555;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #777777;
            }
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #1f6feb;
                border-color: #1f6feb;
            }
            QDialog {
                background-color: #1e1e1e;
            }
            QScrollArea {
                background-color: transparent;
            }
        """)
        # Update window control buttons for dark theme
        if hasattr(self, 'min_btn') and hasattr(self, 'max_btn'):
            self.min_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(80, 80, 80, 0.6);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(120, 120, 120, 0.8);
                }
            """)
            self.max_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(80, 80, 80, 0.6);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(120, 120, 120, 0.8);
                }
            """)
            self.close_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(232, 17, 35, 0.8);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(232, 17, 35, 1);
                }
            """)
            self.topmost_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(80, 80, 80, 0.6);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 16px;
                }
                QPushButton:checked {
                    background-color: rgba(31, 111, 235, 0.9);
                }
                QPushButton:hover {
                    background-color: rgba(120, 120, 120, 0.8);
                }
            """)

    def _apply_light_theme(self):
        """Apply light theme stylesheet"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(0, 0, 0, 0);
            }
            QWidget {
                background-color: rgba(0, 0, 0, 0);
            }
            QMenuBar {
                background-color: #e0e0e0;
                color: #000000;
            }
            QMenuBar::item {
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
            QMenu {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid #cccccc;
            }
            QMenu::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2c5aa0;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1a3d66;
            }
            QPushButton:pressed {
                background-color: #152f4f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QLabel {
                color: #000000;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px;
            }
            QLineEdit:focus {
                border-color: #1f6feb;
            }
            QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #1f6feb;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
            }
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #dddddd;
                border: 1px solid #dddddd;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid #dddddd;
                padding: 6px;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #aaaaaa;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #888888;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #aaaaaa;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #888888;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #000000;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QCheckBox {
                color: #000000;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #aaaaaa;
                border-radius: 3px;
                background-color: #f0f0f0;
            }
            QCheckBox::indicator:checked {
                background-color: #1f6feb;
                border-color: #1f6feb;
            }
            QDialog {
                background-color: #f5f5f5;
            }
            QProgressBar {
                background-color: #e0e0e0;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #1f6feb;
                border-radius: 4px;
            }
            QScrollArea {
                background-color: transparent;
            }
        """)
        # Update window control buttons for light theme
        if hasattr(self, 'min_btn') and hasattr(self, 'max_btn'):
            self.min_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(100, 100, 100, 0.5);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(100, 100, 100, 0.8);
                }
            """)
            self.max_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(100, 100, 100, 0.5);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(100, 100, 100, 0.8);
                }
            """)
            self.close_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(232, 17, 35, 0.8);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 18px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(232, 17, 35, 1);
                }
            """)
            self.topmost_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(100, 100, 100, 0.5);
                    color: #ffffff;
                    border-radius: 4px;
                    font-size: 16px;
                }
                QPushButton:checked {
                    background-color: rgba(31, 111, 235, 0.9);
                }
                QPushButton:hover {
                    background-color: rgba(100, 100, 120, 0.8);
                }
            """)

    def _apply_current_theme(self):
        """Apply the currently selected theme"""
        if self._current_theme == "dark":
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def _toggle_theme(self):
        """Toggle between dark and light theme"""
        if self._current_theme == "dark":
            self._current_theme = "light"
        else:
            self._current_theme = "dark"

        self._apply_current_theme()

        # Navigation bar fully transparent to show main background
        if hasattr(self, 'nav_bar'):
            self.nav_bar.setStyleSheet("QFrame { background-color: rgba(0, 0, 0, 0); border-radius: 12px; }")

        # Save the new theme setting
        if self.app_settings_persistence:
            self.app_settings_persistence.save_settings(
                background_image_path=self._background_image_path,
                background_opacity=self._background_opacity,
                theme=self._current_theme,
                show_income_info=self._show_income_info
            )

        # Update background if needed
        if self._background_image_path and os.path.exists(self._background_image_path):
            self._update_background()

        # Update stylesheet for all cached frames that support theme switching
        for frame in self._frame_cache.values():
            if hasattr(frame, '_update_stylesheet'):
                frame._update_stylesheet()

        # Update home page navigation button styles for current theme
        if self._home_buttons and self.current_widget is not None:
            # Only update if we're on the home page
            base_style = """
                QPushButton {
                    background-color: rgba(44, 90, 160, 0.15);
                    color: %s;
                    border: 2px solid rgba(44, 90, 160, 0.6);
                    border-radius: 12px;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(44, 90, 160, 0.85);
                    border-color: rgba(44, 90, 160, 1);
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: rgba(21, 47, 79, 0.95);
                }
            """
            is_dark = (self._current_theme == "dark")
            text_color = "#ffffff" if is_dark else "#000000"
            button_style = base_style % text_color
            for btn in self._home_buttons:
                btn.setStyleSheet(button_style)

    def _create_loading_screen(self):
        """Create loading screen - check for video and play if available, fallback to static loading"""
        # Check if video folder exists and has any video file
        script_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        video_dir = os.path.join(script_dir, '..', 'video')

        self._video_player = None
        self._video_widget = None

        has_video = False
        video_path = None

        if os.path.exists(video_dir):
            # Look for common video extensions
            extensions = ['.mp4', '.webm', '.avi', '.mkv', '.mov']
            for file in os.listdir(video_dir):
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    video_path = os.path.join(video_dir, file)
                    has_video = True
                    break

        if has_video and video_path:
            # Create video loading screen
            self._video_widget = QVideoWidget()
            self.setCentralWidget(self._video_widget)

            # Create media player
            self._video_player = QMediaPlayer()
            self._video_player.setVideoOutput(self._video_widget)
            self._video_player.setSource(QUrl.fromLocalFile(video_path))

            # Connect signal when video finishes
            self._video_player.playbackStateChanged.connect(self._on_video_finished)
            self._video_player.play()
        else:
            # Fallback to static loading widget
            self.loading_widget = LoadingWidget()
            self.setCentralWidget(self.loading_widget)

    def _on_video_finished(self, state):
        """Called when video playback finishes - switch to main UI"""
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.StoppedState:
            # Clean up video player
            if self._video_player:
                self._video_player.stop()
                self._video_player = None
            if self._video_widget:
                self._video_widget = None

            # Data loading should already be running in background
            # Check if loading is complete, if not just keep waiting
            if self.activity_persistence is not None:
                # Already loaded, finish immediately
                self._finish_loading()
            # else: background thread still working, will call _finish_loading when done

    def _start_background_loading(self):
        """Start loading all data in background thread"""
        def background_task():
            # Initialize all persistence instances
            self.lottery_persistence = LotteryPersistence(os.path.join(self.data_dir, 'lottery.json'))
            self.activity_persistence = ActivityPersistence(os.path.join(self.data_dir, 'activity.json'))
            self.storage_persistence = StoragePersistence(os.path.join(self.data_dir, 'storage.json'))
            self.bait_persistence = BaitPersistence(os.path.join(self.data_dir, 'bait.json'))
            self.friend_link_persistence = FriendLinkPersistence(os.path.join(self.data_dir, 'friend_links.json'))
            self.credentials_persistence = CredentialsPersistence(os.path.join(self.data_dir, 'credentials.json'))
            self.app_settings_persistence = AppSettingsPersistence(os.path.join(self.data_dir, 'app_settings.json'))

            # Load app settings including background
            settings = self.app_settings_persistence.load_settings()
            self._background_image_path = settings.get('background_image_path')
            self._background_opacity = settings.get('background_opacity', 0.15)
            self._current_theme = settings.get('theme', 'dark')
            self._show_income_info = settings.get('show_income_info', False)
            self._screen_recorder_start_hotkey = settings.get('screen_recorder_start_hotkey', 'ctrl+shift+r')
            self._screen_recorder_stop_hotkey = settings.get('screen_recorder_stop_hotkey', 'ctrl+shift+s')
            self._screen_recorder_save_path = settings.get('screen_recorder_save_path', None)
            self._screen_recorder_record_mic = settings.get('screen_recorder_record_mic', False)
            self._screen_recorder_record_system = settings.get('screen_recorder_record_system', False)
            self._special_cursor_on_hover = settings.get('special_cursor_on_hover', True)

            # Initialize daily tasks persistence
            self.daily_task_persistence = DailyTaskPersistence(os.path.join(self.data_dir, 'daily_tasks.json'))

            # Create automatic backup on startup
            self.backup_dir = os.path.join(self.data_dir, 'backups')
            os.makedirs(self.backup_dir, exist_ok=True)
            # Keep last 10 backups automatically
            backups = list_backups(self.backup_dir)
            if len(backups) >= 10:
                # Remove oldest backups beyond 10
                for old_backup in backups[10:]:
                    old_path = os.path.join(self.backup_dir, old_backup)
                    shutil.rmtree(old_path, ignore_errors=True)
            # Create new backup
            create_auto_backup(self.data_dir, self.backup_dir)

            # Signal that loading is done
            self.data_loaded.emit()

        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()
        self.data_loaded.connect(self._finish_loading)

    def _finish_loading(self):
        """Called after background loading completes - switch to main UI"""
        # If we have a video player still playing, wait for it to finish
        if self._video_player is not None:
            # Data loaded, just wait for video to finish before switching UI
            return

        # Apply loaded theme
        self._apply_current_theme()

        # Create main UI
        self._create_main_ui()
        self.show_home_page()
        # Update background after central widget is created and layout done
        if self._background_image_path and os.path.exists(self._background_image_path):
            QTimer.singleShot(50, self._update_background)

        # Initialize screen recorder
        self._init_screen_recorder()

    def _create_main_ui(self):
        """Create the main UI after loading"""
        # Create central widget - subclass that ensures background is painted
        class CentralWidget(QWidget):
            """Custom central widget that always paints a tiny alpha background to prevent click-through"""
            def paintEvent(self, event):
                from PySide6.QtGui import QPainter, QColor
                painter = QPainter(self)
                # Fill with 2% opacity black - completely invisible visually
                # But guarantees all pixels have alpha > 0, so Windows won't click through
                painter.fillRect(self.rect(), QColor(0, 0, 0, 5))
                super().paintEvent(event)

        # Create central widget and main layout
        self.central_widget = CentralWidget()
        self.central_widget.setAutoFillBackground(False)
        self.central_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.central_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setCentralWidget(self.central_widget)

        # Add drop shadow effect to the entire window for better visual separation
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 0)
        self.central_widget.setGraphicsEffect(shadow)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(8)

        # Top navigation bar - fully transparent background
        self.nav_bar = QFrame()
        self.nav_bar.setStyleSheet("QFrame { background-color: rgba(0, 0, 0, 0); border-radius: 12px; }")
        self.nav_bar.setFixedHeight(60)
        self.nav_bar.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(10, 10, 10, 10)

        # Back button
        self.back_button = QPushButton("返回主页")
        self.back_button.setFixedWidth(80)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #555555;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        self.back_button.clicked.connect(self.show_home_page)
        nav_layout.addWidget(self.back_button)

        # Title
        self.title_label = QLabel("RF4 数据统计")
        self.title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        nav_layout.addWidget(self.title_label)

        nav_layout.addStretch()

        # App settings button - contains theme, background, and all other settings
        self.settings_btn = QPushButton("⚙ 设置")
        self.settings_btn.setFixedWidth(80)
        self.settings_btn.clicked.connect(self.open_app_settings)
        nav_layout.addWidget(self.settings_btn)

        # Window always on top toggle button
        self.topmost_btn = QPushButton("📌")
        self.topmost_btn.setFixedWidth(46)
        self.topmost_btn.setToolTip("切换窗口置顶")
        self.topmost_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(80, 80, 80, 0.6);
                color: #ffffff;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:checked {
                background-color: rgba(31, 111, 235, 0.9);
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 0.8);
            }
        """)
        self.topmost_btn.setCheckable(True)
        self.topmost_btn.clicked.connect(self._toggle_topmost)
        nav_layout.addWidget(self.topmost_btn)

        # Window control buttons (minimize, maximize, close)
        self.min_btn = QPushButton("−")
        self.min_btn.setFixedSize(46, 36)
        self.min_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(80, 80, 80, 0.6);
                color: #ffffff;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 0.8);
            }
        """)
        self.min_btn.clicked.connect(self.showMinimized)
        nav_layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("□")
        self.max_btn.setFixedSize(46, 36)
        self.max_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(80, 80, 80, 0.6);
                color: #ffffff;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 0.8);
            }
        """)
        self.max_btn.clicked.connect(self._toggle_maximize)
        nav_layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(46, 36)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(232, 17, 35, 0.8);
                color: #ffffff;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(232, 17, 35, 1);
            }
        """)
        self.close_btn.clicked.connect(self.close)
        nav_layout.addWidget(self.close_btn)

        nav_layout.setSpacing(8)
        main_layout.addWidget(self.nav_bar)

        # Add background image label that covers the entire central widget
        if self._background_image_path and os.path.exists(self._background_image_path):
            self._update_background()

        # Content area - scrollable, with tiny alpha to prevent click-through
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setAttribute(Qt.WA_TranslucentBackground, True)
        # Tiny alpha to prevent click-through on Windows
        self.scroll_area.setStyleSheet("QScrollArea { background-color: rgba(0, 0, 0, 2); }")
        self.scroll_area.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.content_container = QWidget()
        self.content_container.setAttribute(Qt.WA_TranslucentBackground, True)
        # Tiny alpha to prevent click-through
        self.content_container.setStyleSheet("QWidget { background-color: rgba(0, 0, 0, 0); }")
        self.content_container.setAutoFillBackground(False)
        self.content_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.content_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Bottom bar for backup and friend links
        self.bottom_bar = QFrame()
        # Tiny alpha to prevent click-through on Windows
        self.bottom_bar.setStyleSheet("QFrame { background-color: rgba(0, 0, 0, 2); }")
        self.bottom_bar.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

# Remove the resize detector - we handle it directly in main window event() now

        # Backup button
        backup_button = QPushButton("💾 备份恢复")
        backup_button.setFixedWidth(120)
        backup_button.clicked.connect(self.open_backup_dialog)
        bottom_layout.addWidget(backup_button)

        # Sync fish data button
        self.sync_button = QPushButton("🔄 同步鱼种")
        self.sync_button.setFixedWidth(120)
        self.sync_button.clicked.connect(self.start_fish_sync)
        bottom_layout.addWidget(self.sync_button)

        bottom_layout.addStretch()

        # Friend links button
        friend_button = QPushButton("友情链接")
        friend_button.setFixedWidth(120)
        friend_button.clicked.connect(self.open_friend_links)
        bottom_layout.addWidget(friend_button)

        main_layout.addWidget(self.bottom_bar)

    def show_home_page(self):
        """Show home page with big navigation buttons"""
        self.clear_current_content()
        self.back_button.hide()

        # Home container
        home_widget = QWidget()
        home_widget.setAutoFillBackground(False)
        home_layout = QVBoxLayout(home_widget)
        home_layout.setContentsMargins(0, 0, 0, 0)
        # Make home widget background transparent so main background shows through
        home_widget.setAutoFillBackground(False)

        # Welcome label
        welcome = QLabel("欢迎使用RF4数据统计工具")
        welcome.setFont(QFont("Segoe UI", 28, QFont.Bold))
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setStyleSheet("background-color: transparent;")
        home_layout.addWidget(welcome)
        home_layout.addSpacing(40)

        # Button grid container
        btn_container = QWidget()
        btn_container.setAutoFillBackground(False)
        grid = QGridLayout(btn_container)
        grid.setSpacing(16)

        # Make all columns and rows expand equally
        for i in range(2):
            grid.setColumnStretch(i, 1)

        # Create navigation buttons - transparent background, only show on hover
        button_font = QFont("Segoe UI", 16, QFont.Bold)
        button_size = QSize(190, 70)
        base_style = """
            QPushButton {
                background-color: rgba(44, 90, 160, 0.15);
                color: %s;
                border: 2px solid rgba(44, 90, 160, 0.6);
                border-radius: 12px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: rgba(44, 90, 160, 0.85);
                border-color: rgba(44, 90, 160, 1);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(21, 47, 79, 0.95);
            }
        """

        # Get theme-appropriate text color
        is_dark = (self._current_theme == "dark")
        text_color = "#ffffff" if is_dark else "#000000"
        button_style = base_style % text_color

        # Clear old button references
        self._home_buttons.clear()

        # Row 0
        activity_btn = QPushButton("📊\n活动统计")
        activity_btn.setFont(button_font)
        activity_btn.setMinimumSize(button_size)
        activity_btn.setStyleSheet(button_style)
        activity_btn.clicked.connect(self.show_activity_stats)
        grid.addWidget(activity_btn, 0, 0)
        self._home_buttons.append(activity_btn)

        storage_btn = QPushButton("📦\n存储时长")
        storage_btn.setFont(button_font)
        storage_btn.setMinimumSize(button_size)
        storage_btn.setStyleSheet(button_style)
        storage_btn.clicked.connect(self.show_storage)
        grid.addWidget(storage_btn, 0, 1)
        self._home_buttons.append(storage_btn)

        # Row 1
        bait_btn = QPushButton("🎣\n饵料库存")
        bait_btn.setFont(button_font)
        bait_btn.setMinimumSize(button_size)
        bait_btn.setStyleSheet(button_style)
        bait_btn.clicked.connect(self.show_bait)
        grid.addWidget(bait_btn, 1, 0)
        self._home_buttons.append(bait_btn)

        lottery_btn = QPushButton("🎡\n转盘抽奖")
        lottery_btn.setFont(button_font)
        lottery_btn.setMinimumSize(button_size)
        lottery_btn.setStyleSheet(button_style)
        lottery_btn.clicked.connect(self.show_lottery)
        grid.addWidget(lottery_btn, 1, 1)
        self._home_buttons.append(lottery_btn)

        # Row 2
        credentials_btn = QPushButton("🔐\n账号管理")
        credentials_btn.setFont(button_font)
        credentials_btn.setMinimumSize(button_size)
        credentials_btn.setStyleSheet(button_style)
        credentials_btn.clicked.connect(self.show_credentials)
        grid.addWidget(credentials_btn, 2, 0)
        self._home_buttons.append(credentials_btn)

        statistics_btn = QPushButton("📈\n数据分析")
        statistics_btn.setFont(button_font)
        statistics_btn.setMinimumSize(button_size)
        statistics_btn.setStyleSheet(button_style)
        statistics_btn.clicked.connect(self.show_statistics)
        grid.addWidget(statistics_btn, 2, 1)
        self._home_buttons.append(statistics_btn)

        # Row 3
        task_btn = QPushButton("📋\n每日任务")
        task_btn.setFont(button_font)
        task_btn.setMinimumSize(button_size)
        task_btn.setStyleSheet(button_style)
        task_btn.clicked.connect(self.show_daily_tasks)
        grid.addWidget(task_btn, 3, 0)
        self._home_buttons.append(task_btn)

        # Row 4
        multi_btn = QPushButton("🚀\n多开启动")
        multi_btn.setFont(button_font)
        multi_btn.setMinimumSize(button_size)
        multi_btn.setStyleSheet(button_style)
        multi_btn.clicked.connect(self.show_multi_launcher)
        grid.addWidget(multi_btn, 3, 1)
        self._home_buttons.append(multi_btn)

        # Make rows expand
        for i in range(4):
            grid.setRowStretch(i, 1)

        home_layout.addWidget(btn_container, 1)
        home_layout.addStretch()

        self.content_layout.addWidget(home_widget)
        self.current_widget = home_widget

    def clear_current_content(self):
        """Clear current content from content layout"""
        if self.current_widget is not None:
            self.content_layout.removeWidget(self.current_widget)
            self.current_widget.hide()
            self.current_widget = None

    def _prepare_page(self):
        """Common preparation for showing a page"""
        self.back_button.show()
        self.clear_current_content()

    def show_activity_stats(self):
        """Show activity statistics page"""
        from .activity_frame import ActivityFrame

        self._prepare_page()

        cache_key = "activity_stats"
        if cache_key in self._frame_cache:
            frame = self._frame_cache[cache_key]
            frame._show_income_info = self._show_income_info
            # Refresh both tabs to apply setting
            if frame.current_character:
                frame.update_display(ActivityType.GRINDING)
                frame.update_display(ActivityType.STAR_WAITING)
            frame.update_data()
        else:
            frame = ActivityFrame(self.activity_persistence, self._show_income_info)
            self._frame_cache[cache_key] = frame

        self.content_layout.addWidget(frame)
        frame.show()
        self.current_widget = frame

    def show_storage(self):
        """Show storage duration page"""
        from .storage_frame import StorageFrame

        self._prepare_page()

        cache_key = "storage"
        if cache_key in self._frame_cache:
            frame = self._frame_cache[cache_key]
            frame.update_table()
        else:
            frame = StorageFrame(self.storage_persistence)
            self._frame_cache[cache_key] = frame

        self.content_layout.addWidget(frame)
        frame.show()
        self.current_widget = frame

    def show_lottery(self):
        """Show lottery wheel page"""
        from .lottery_frame import LotteryFrame

        self._prepare_page()

        cache_key = "lottery"
        if cache_key in self._frame_cache:
            frame = self._frame_cache[cache_key]
            frame.refresh_wheel()
        else:
            frame = LotteryFrame(self.lottery_persistence)
            self._frame_cache[cache_key] = frame

        self.content_layout.addWidget(frame)
        frame.show()
        self.current_widget = frame

    def show_credentials(self):
        """Show account credentials manager page"""
        from .credentials_frame import CredentialsFrame

        self._prepare_page()

        cache_key = "credentials"
        if cache_key in self._frame_cache:
            frame = self._frame_cache[cache_key]
            frame.update_combobox()
        else:
            frame = CredentialsFrame(self.credentials_persistence)
            self._frame_cache[cache_key] = frame

        self.content_layout.addWidget(frame)
        frame.show()
        self.current_widget = frame

    def show_bait(self):
        """Show bait/tackle consumption tracking page"""
        from .bait_frame import BaitFrame

        self._prepare_page()

        cache_key = "bait"
        if cache_key in self._frame_cache:
            frame = self._frame_cache[cache_key]
            frame.update_table()
        else:
            frame = BaitFrame(self.bait_persistence)
            self._frame_cache[cache_key] = frame

        self.content_layout.addWidget(frame)
        frame.show()
        self.current_widget = frame

    def show_statistics(self):
        """Show data analysis page with visualizations"""
        from .statistics_frame import StatisticsFrame

        self._prepare_page()

        cache_key = "statistics"
        if cache_key in self._frame_cache:
            frame = self._frame_cache[cache_key]
            frame.refresh_plots()
        else:
            frame = StatisticsFrame(self.activity_persistence)
            self._frame_cache[cache_key] = frame

        self.content_layout.addWidget(frame)
        frame.show()
        self.current_widget = frame

    def show_daily_tasks(self):
        """Show daily task tracking page"""
        from .daily_task_frame import DailyTaskFrame

        self._prepare_page()

        # Load current activity characters - always get latest to add/remove roles
        characters, _ = self.activity_persistence.load_characters()

        cache_key = "daily_tasks"
        if cache_key in self._frame_cache:
            frame = self._frame_cache[cache_key]
            # Update with latest characters list (in case roles added/removed)
            frame.update_data(characters)
        else:
            frame = DailyTaskFrame(self.daily_task_persistence, characters)
            self._frame_cache[cache_key] = frame

        self.content_layout.addWidget(frame)
        frame.show()
        self.current_widget = frame

    def show_multi_launcher(self):
        """Open multiple instances launcher dialog"""
        try:
            from .multi_launcher import MultiLauncherDialog
            # Use non-modal dialog so main window can still be moved/dragged
            self._multi_dialog = MultiLauncherDialog(self)
            self._multi_dialog.show()
        except ImportError as e:
            QMessageBox.warning(
                self,
                "缺少依赖",
                f"多开功能需要安装额外依赖:\n{str(e)}\n\n请运行:\npip install psutil pywin32"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "启动失败",
                f"多开启动器启动失败:\n{str(e)}"
            )

    def open_friend_links(self):
        """Open friend links dialog"""
        from .dialogs.friend_links_dialog import FriendLinksDialog
        links = self.friend_link_persistence.load_links()
        dialog = FriendLinksDialog(self, links)
        dialog.links_changed.connect(self._on_friend_links_changed)
        dialog.exec()

    def _on_friend_links_changed(self, new_links):
        """Callback when friend links are changed"""
        self.friend_link_persistence.save_links(new_links)

    def open_backup_dialog(self):
        """Open backup and restore dialog"""
        from .dialogs.backup_dialog import BackupRestoreDialog
        dialog = BackupRestoreDialog(self, self.data_dir, self.backup_dir)
        dialog.exec()

    def closeEvent(self, event):
        """Handle window closing - save all data and cleanup"""
        # Cleanup screen recorder
        if self._screen_recorder:
            if self._screen_recorder.is_currently_recording():
                self._screen_recorder.stop_recording()
            self._screen_recorder.unregister_hotkeys()

        # Save data from all cached frames
        if "activity_stats" in self._frame_cache:
            self._frame_cache["activity_stats"].save_data()
        if "storage" in self._frame_cache:
            self._frame_cache["storage"].save_data()
        if "bait" in self._frame_cache:
            self._frame_cache["bait"].save_data()
        if "daily_tasks" in self._frame_cache:
            self._frame_cache["daily_tasks"].save_data()
        event.accept()

    def open_app_settings(self):
        """Open application settings dialog"""
        from .dialogs.app_settings_dialog import AppSettingsDialog
        dialog = AppSettingsDialog(
            self,
            self._background_image_path,
            self._background_opacity,
            self._current_theme,
            self._show_income_info,
            self._screen_recorder_start_hotkey,
            self._screen_recorder_stop_hotkey,
            self._screen_recorder_save_path,
            self._screen_recorder_record_mic,
            self._screen_recorder_record_system,
            self._special_cursor_on_hover
        )
        dialog.settings_changed.connect(self._on_app_settings_changed)
        dialog.exec()

    def _on_app_settings_changed(self, image_path: str, opacity: float, theme: str, show_income: bool,
                                  start_hotkey: str = None, stop_hotkey: str = None, save_path: str = None,
                                  record_mic: bool = None, record_system: bool = None,
                                  special_cursor_on_hover: bool = None):
        """Callback when application settings are changed"""
        self._background_image_path = image_path
        self._background_opacity = opacity
        self._current_theme = theme
        self._show_income_info = show_income
        if start_hotkey is not None:
            self._screen_recorder_start_hotkey = start_hotkey
        if stop_hotkey is not None:
            self._screen_recorder_stop_hotkey = stop_hotkey
        self._screen_recorder_save_path = save_path
        if record_mic is not None:
            self._screen_recorder_record_mic = record_mic
        if record_system is not None:
            self._screen_recorder_record_system = record_system
        if special_cursor_on_hover is not None:
            self._special_cursor_on_hover = special_cursor_on_hover

        # Update theme if it changed
        self._apply_current_theme()

        # Update activity frame to reflect setting change
        if "activity_stats" in self._frame_cache:
            self._frame_cache["activity_stats"]._show_income_info = show_income
            # Refresh display for both tabs
            if self._frame_cache["activity_stats"].current_character:
                self._frame_cache["activity_stats"].update_display(ActivityType.GRINDING)
                self._frame_cache["activity_stats"].update_display(ActivityType.STAR_WAITING)

        # Update screen recorder settings
        self._update_screen_recorder_settings()

        # Save settings
        if self.app_settings_persistence:
            self.app_settings_persistence.save_settings(
                background_image_path=self._background_image_path,
                background_opacity=self._background_opacity,
                theme=self._current_theme,
                show_income_info=self._show_income_info,
                screen_recorder_start_hotkey=self._screen_recorder_start_hotkey,
                screen_recorder_stop_hotkey=self._screen_recorder_stop_hotkey,
                screen_recorder_save_path=self._screen_recorder_save_path,
                screen_recorder_record_mic=self._screen_recorder_record_mic,
                screen_recorder_record_system=self._screen_recorder_record_system,
                special_cursor_on_hover=self._special_cursor_on_hover
            )

        # Update background display
        self._update_background()

    def _update_background(self):
        """Update the background image display"""
        # Remove old background label if exists
        if self._background_label is not None:
            self.central_widget.layout().removeWidget(self._background_label)
            self._background_label.deleteLater()
            self._background_label = None

        if not self._background_image_path or not os.path.exists(self._background_image_path):
            # No background image - create an opaque-in-hit-test layer covering everything
            # This must block click-through on Windows, which requires any alpha > 0
            from PySide6.QtGui import QPalette, QColor
            self._background_label = QLabel(self.central_widget)
            self._background_label.resize(self.central_widget.size())
            # Use QPalette to set background - more reliable than stylesheet
            palette = self._background_label.palette()
            # Alpha=5 (~2%) - completely invisible visually but alpha > 0
            palette.setBrush(QPalette.Window, QBrush(QColor(0, 0, 0, 5)))
            self._background_label.setPalette(palette)
            self._background_label.setAutoFillBackground(True)
            # Absolutely critical: do NOT allow mouse to pass through this widget
            self._background_label.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._background_label.setAttribute(Qt.WA_OpaquePaintEvent, False)
            # Send to absolute bottom so it's behind everything else
            self._background_label.lower()
            self._background_label.show()
            return

        # Custom background label that keeps the original pixmap and auto-scales on paint
        from PySide6.QtGui import QPainter, QColor, QPixmap
        class BackgroundLabel(QLabel):
            def __init__(self, original_pixmap, opacity, parent=None):
                super().__init__(parent)
                self._original_pixmap = original_pixmap
                self._opacity = opacity

            def paintEvent(self, event):
                # Auto-scale to current label size during paint
                painter = QPainter(self)
                painter.setOpacity(self._opacity)
                scaled = self._original_pixmap.scaled(
                    self.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                # Center the scaled image
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()

        # Load original pixmap once - keep it in memory
        original_pixmap = QPixmap(self._background_image_path)
        if not original_pixmap.isNull():
            # Create custom background label
            self._background_label = BackgroundLabel(original_pixmap, self._background_opacity, self.central_widget)
            self._background_label.resize(self.central_widget.size())
            self._background_label.setAutoFillBackground(False)
            # Absolutely critical: do NOT allow mouse to pass through this widget
            self._background_label.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self._background_label.setAttribute(Qt.WA_OpaquePaintEvent, False)
            # Background goes below all other content
            self._background_label.lower()
            self._background_label.show()

        # Also update background for home page content container
        if self.current_widget:
            # Make the content container background transparent
            # so the main background shows through
            self.current_widget.setAutoFillBackground(False)
            self.content_container.setAutoFillBackground(False)

    def showEvent(self, event):
        """Ensure transparency is applied when window shows"""
        super().showEvent(event)
        # Double ensure transparency
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.update()

    def resizeEvent(self, event):
        """Handle window resize to update background scaling"""
        super().resizeEvent(event)
        # Just update label size - background will automatically scale on paint
        if self._background_label:
            self._background_label.resize(self.central_widget.size())
            # Trigger repaint - scaling is done in paintEvent
            self._background_label.update()

    def _get_resize_direction(self, pos):
        """Determine which edge/corner the mouse is over for resizing"""
        rect = self.rect()
        margin = self._resize_margin
        x = pos.x()
        y = pos.y()
        w = rect.width()
        h = rect.height()

        left = x < margin
        right = x > w - margin
        top = y < margin
        bottom = y > h - margin

        if top and left:
            return 'top-left'
        elif top and right:
            return 'top-right'
        elif bottom and left:
            return 'bottom-left'
        elif bottom and right:
            return 'bottom-right'
        elif left:
            return 'left'
        elif right:
            return 'right'
        elif top:
            return 'top'
        elif bottom:
            return 'bottom'
        return None

    def mousePressEvent(self, event):
        """Handle mouse press for dragging the frameless window or resizing"""
        if event.button() == Qt.LeftButton:
            # Check if we're on a resize edge
            self._resize_direction = self._get_resize_direction(event.position().toPoint())
            if self._resize_direction is not None:
                # Start resizing
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geometry = self.geometry()
                # Grab mouse so we get events even if it moves outside the window
                self.grabMouse()
                event.accept()
                return

            # If not resizing, check if we can drag (click on title bar or empty space)
            # Allow dragging anywhere except over content widgets
            child = self.childAt(event.position().toPoint())
            if child is None or isinstance(child, QLabel) or child == self.nav_bar or child == self.bottom_bar:
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                # Also grab mouse for dragging to get events outside window
                self.grabMouse()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging the frameless window or resizing"""
        from PySide6.QtGui import QCursor

        if event.buttons() == Qt.LeftButton:
            if self._resize_direction is not None:
                # Get current mouse position in global screen coordinates
                mouse_global = event.globalPosition().toPoint()

                # Get the starting geometry (from when mouse was first pressed)
                start = self._resize_start_geometry
                if not start:
                    event.accept()
                    return

                # Initialize with starting values
                new_x = start.x()
                new_y = start.y()
                new_right = start.x() + start.width()
                new_bottom = start.y() + start.height()

                # Directly set the edge being dragged to current mouse position
                # This guarantees the dragged edge is always exactly under the mouse
                if 'left' in self._resize_direction:
                    new_x = mouse_global.x()
                if 'right' in self._resize_direction:
                    new_right = mouse_global.x()
                if 'top' in self._resize_direction:
                    new_y = mouse_global.y()
                if 'bottom' in self._resize_direction:
                    new_bottom = mouse_global.y()

                # Calculate new dimensions
                new_width = new_right - new_x
                new_height = new_bottom - new_y

                # Apply minimum size constraints
                if new_width < self.minimumWidth():
                    # If we're dragging left edge, fix it to maintain minimum width
                    if 'left' in self._resize_direction:
                        new_x = new_right - self.minimumWidth()
                    else:
                        new_right = new_x + self.minimumWidth()
                    new_width = self.minimumWidth()

                if new_height < self.minimumHeight():
                    if 'top' in self._resize_direction:
                        new_y = new_bottom - self.minimumHeight()
                    else:
                        new_bottom = new_y + self.minimumHeight()
                    new_height = self.minimumHeight()

                print(f"[resize] direction={self._resize_direction}, mouse=({mouse_global.x()},{mouse_global.y()}), result=({new_width}x{new_height})")
                self.setGeometry(new_x, new_y, new_width, new_height)
                event.accept()
                return

            elif self._drag_position is not None:
                # Handle dragging
                self.move(event.globalPosition().toPoint() - self._drag_position)
                event.accept()
        else:
            # Update cursor shape when hovering over edges
            direction = self._get_resize_direction(event.position().toPoint())
            if direction is None:
                self.setCursor(Qt.ArrowCursor)
            elif direction in ['left', 'right']:
                self.setCursor(Qt.SizeHorCursor)
            elif direction in ['top', 'bottom']:
                self.setCursor(Qt.SizeVerCursor)
            elif direction in ['top-left', 'bottom-right']:
                self.setCursor(Qt.SizeFDiagCursor)
            elif direction in ['top-right', 'bottom-left']:
                self.setCursor(Qt.SizeBDiagCursor)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to finish dragging or resizing"""
        self._drag_position = None
        self._resize_direction = None
        self._resize_start_pos = None
        self._resize_start_geometry = None
        # Release mouse capture
        self.releaseMouse()
        # Reset cursor
        self.setCursor(Qt.ArrowCursor)
        event.accept()

    def _toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("□")
        else:
            self.showMaximized()
            self.max_btn.setText("❐")

    def _toggle_topmost(self):
        """Toggle window always on top"""
        if self.topmost_btn.isChecked():
            # Set window always on top
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
        else:
            # Remove always on top
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()

    def mouseDoubleClickEvent(self, event):
        """Handle double-click on title bar/navigation area to toggle maximize"""
        # Check if click is on the navigation bar area
        pos = event.position().toPoint()
        if pos.y() <= self.nav_bar.height() + 15:  # Within title bar area
            self._toggle_maximize()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def start_fish_sync(self):
        """Start syncing fish data from official website"""
        try:
            from ..core.fish_sync import FishSyncDialog
            dialog = FishSyncDialog(self, self.data_dir)
            dialog.exec()
        except ImportError as e:
            QMessageBox.warning(
                self,
                "缺少依赖",
                f"数据同步功能需要安装额外依赖:\n{str(e)}\n\n请运行:\ncd qt\npip install lxml pandas"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "启动失败",
                f"数据同步启动失败:\n{str(e)}"
            )

    def _init_screen_recorder(self):
        """Initialize screen recorder with loaded settings"""
        try:
            from .screen_recorder import ScreenRecorder
            self._screen_recorder = ScreenRecorder(
                start_hotkey=self._screen_recorder_start_hotkey,
                stop_hotkey=self._screen_recorder_stop_hotkey,
                save_path=self._screen_recorder_save_path,
                record_mic=self._screen_recorder_record_mic,
                record_system=self._screen_recorder_record_system
            )
            success = self._screen_recorder.setup_hotkeys()
            if not success:
                print("Warning: Failed to setup screen recorder hotkeys. Check if keyboard library is installed.")
            else:
                # Connect recording finished signal for logging
                self._screen_recorder.recording_finished.connect(
                    lambda path: print(f"✓ Recording completed: {path}")
                )
        except ImportError as e:
            print(f"Screen recorder not available: {e}")
            print("To enable screen recorder, run: pip install keyboard pyautogui opencv-python numpy")
            print("For audio recording, also install: pip install pyaudio sounddevice soundfile")
        except Exception as e:
            print(f"Failed to initialize screen recorder: {e}")
            self._screen_recorder = None

    def _update_screen_recorder_settings(self):
        """Update screen recorder with new settings"""
        if self._screen_recorder is None:
            # Try to initialize again
            self._init_screen_recorder()
            return

        try:
            self._screen_recorder.update_settings(
                start_hotkey=self._screen_recorder_start_hotkey,
                stop_hotkey=self._screen_recorder_stop_hotkey,
                save_path=self._screen_recorder_save_path,
                record_mic=self._screen_recorder_record_mic,
                record_system=self._screen_recorder_record_system
            )
        except Exception as e:
            print(f"Failed to update screen recorder settings: {e}")

    def closeEvent(self, event):
        """Handle window closing - save all data and cleanup"""
        # Cleanup screen recorder
        if self._screen_recorder:
            if self._screen_recorder.is_currently_recording():
                self._screen_recorder.stop_recording()
            self._screen_recorder.unregister_hotkeys()

        # Save data from all cached frames
        if "activity_stats" in self._frame_cache:
            self._frame_cache["activity_stats"].save_data()
        if "storage" in self._frame_cache:
            self._frame_cache["storage"].save_data()
        if "bait" in self._frame_cache:
            self._frame_cache["bait"].save_data()
        if "daily_tasks" in self._frame_cache:
            self._frame_cache["daily_tasks"].save_data()
        event.accept()

    def enterEvent(self, event):
        """Mouse enters window - change to hand cursor if enabled"""
        if self._special_cursor_on_hover:
            from PySide6.QtGui import QCursor, QPixmap, QBitmap
            import os
            # Check for custom cursor files in assets directory
            script_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            # Try .cur file first (Windows cursor format)
            cur_path = os.path.join(script_dir, '..', 'assets', 'custom_cursor.cur')
            png_path = os.path.join(script_dir, '..', 'assets', 'custom_cursor.png')

            custom_cursor = None
            if os.path.exists(cur_path):
                # Load cursor from .cur file
                pixmap = QPixmap(cur_path)
                if not pixmap.isNull():
                    # Use top-left as hotspot
                    custom_cursor = QCursor(pixmap, 0, 0)
            elif os.path.exists(png_path):
                # Load cursor from .png file
                pixmap = QPixmap(png_path)
                if not pixmap.isNull():
                    # Assume hotspot at top-left (0,0)
                    # If you need different hotspot, you can modify this code
                    custom_cursor = QCursor(pixmap, 0, 0)

            if custom_cursor and not custom_cursor.pixmap().isNull():
                self.setCursor(custom_cursor)
            else:
                # Fallback to default pointing hand cursor
                self.setCursor(Qt.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Mouse leaves window - revert to arrow cursor"""
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def event(self, event):
        """Override main window event to handle resize detection before it goes to child widgets
        This guarantees edge resize always works regardless of content layout
        """
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import Qt

        # Handle mouse events first for resize detection
        if event.type() in [
            QMouseEvent.MouseButtonPress,
            QMouseEvent.MouseMove,
            QMouseEvent.MouseButtonRelease
        ]:
            me = event
            local_pos = me.position().toPoint()
            direction = self._get_resize_direction(local_pos)

            if direction is not None or self._resize_direction is not None:
                # We need to handle this resize
                if event.type() == QMouseEvent.MouseButtonPress:
                    self.mousePressEvent(me)
                elif event.type() == QMouseEvent.MouseMove:
                    self.mouseMoveEvent(me)
                elif event.type() == QMouseEvent.MouseButtonRelease:
                    self.mouseReleaseEvent(me)
                # Event handled - don't pass to children
                return True

        # Let other events through normally
        return super().event(event)
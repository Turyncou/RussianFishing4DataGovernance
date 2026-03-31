"""Main application window for PySide6 implementation"""
import os
import shutil
import threading
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QProgressBar,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QIcon, QFont, QPalette, QBrush, QPixmap

from src.data.persistence import (
    LotteryPersistence, ActivityPersistence, StoragePersistence, BaitPersistence,
    FriendLinkPersistence, CredentialsPersistence, AppSettingsPersistence,
    create_auto_backup, list_backups
)
from src.core.models import FriendLink


class LoadingWidget(QWidget):
    """Loading screen widget displayed during startup"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            LoadingWidget {
                background-color: #1a1a1a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Title
        title = QLabel("RF4 数据统计工具")
        title.setFont(QFont("Segoe UI", 32, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
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
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        # Spacer
        spacer2 = QWidget()
        spacer2.setFixedHeight(20)
        layout.addWidget(spacer2)

        # Loading text
        label = QLabel("正在加载数据...")
        label.setFont(QFont("Segoe UI", 16))
        label.setStyleSheet("color: #cccccc;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window"""

    data_loaded = Signal()

    def __init__(self, data_dir: str):
        super().__init__()
        self.data_dir = data_dir
        self._frame_cache = {}
        self.current_widget = None

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

        # Window setup
        self.setWindowTitle("RF4 Data Process")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)

        # Set dark theme stylesheet
        self._apply_dark_theme()

        # Create loading screen
        self._create_loading_screen()

        # Start background loading
        self._start_background_loading()

    def _apply_dark_theme(self):
        """Apply dark theme stylesheet"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
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
        """)

    def _create_loading_screen(self):
        """Create loading screen as central widget"""
        self.loading_widget = LoadingWidget()
        self.setCentralWidget(self.loading_widget)

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
        # Create main UI
        self._create_main_ui()
        self.show_home_page()

    def _create_main_ui(self):
        """Create the main UI after loading"""
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(8)

        # Top navigation bar
        self.nav_bar = QFrame()
        self.nav_bar.setStyleSheet("QFrame { background-color: #252525; border-radius: 12px; }")
        self.nav_bar.setFixedHeight(60)
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

        # Background settings button
        bg_btn = QPushButton("🖼️ 背景")
        bg_btn.setFixedWidth(80)
        bg_btn.clicked.connect(self.open_background_settings)
        nav_layout.addWidget(bg_btn)

        main_layout.addWidget(self.nav_bar)

        # Add background image label that covers the entire central widget
        if self._background_image_path and os.path.exists(self._background_image_path):
            self._update_background()

        # Content area - scrollable
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.content_container = QWidget()
        self.content_container.setAutoFillBackground(False)
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.content_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Bottom bar for backup and friend links
        self.bottom_bar = QFrame()
        self.bottom_bar.setStyleSheet("QFrame { background-color: transparent; }")
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Backup button
        backup_button = QPushButton("💾 备份恢复")
        backup_button.setFixedWidth(120)
        backup_button.clicked.connect(self.open_backup_dialog)
        bottom_layout.addWidget(backup_button)

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
        home_layout = QVBoxLayout(home_widget)
        home_layout.setContentsMargins(0, 0, 0, 0)
        # Make home widget background transparent so main background shows through
        home_widget.setAutoFillBackground(False)

        # Welcome label
        welcome = QLabel("欢迎使用 RF4 数据统计工具")
        welcome.setFont(QFont("Segoe UI", 32, QFont.Bold))
        welcome.setAlignment(Qt.AlignCenter)
        home_layout.addWidget(welcome)
        home_layout.addSpacing(60)

        # Button grid container
        btn_container = QWidget()
        grid = QGridLayout(btn_container)
        grid.setSpacing(20)

        # Make all columns and rows expand equally
        for i in range(3):
            grid.setRowStretch(i, 1)
        for i in range(2):
            grid.setColumnStretch(i, 1)

        # Create big buttons
        button_font = QFont("Segoe UI", 20, QFont.Bold)
        button_size = QSize(220, 80)

        # Row 0
        activity_btn = QPushButton("📊\n活动统计")
        activity_btn.setFont(button_font)
        activity_btn.setMinimumSize(button_size)
        activity_btn.clicked.connect(self.show_activity_stats)
        grid.addWidget(activity_btn, 0, 0)

        storage_btn = QPushButton("📦\n存储时长")
        storage_btn.setFont(button_font)
        storage_btn.setMinimumSize(button_size)
        storage_btn.clicked.connect(self.show_storage)
        grid.addWidget(storage_btn, 0, 1)

        # Row 1
        bait_btn = QPushButton("🎣\n饵料库存")
        bait_btn.setFont(button_font)
        bait_btn.setMinimumSize(button_size)
        bait_btn.clicked.connect(self.show_bait)
        grid.addWidget(bait_btn, 1, 0)

        lottery_btn = QPushButton("🎡\n转盘抽奖")
        lottery_btn.setFont(button_font)
        lottery_btn.setMinimumSize(button_size)
        lottery_btn.clicked.connect(self.show_lottery)
        grid.addWidget(lottery_btn, 1, 1)

        # Row 2
        credentials_btn = QPushButton("🔐\n账号管理")
        credentials_btn.setFont(button_font)
        credentials_btn.setMinimumSize(button_size)
        credentials_btn.clicked.connect(self.show_credentials)
        grid.addWidget(credentials_btn, 2, 0)

        statistics_btn = QPushButton("📈\n数据分析")
        statistics_btn.setFont(button_font)
        statistics_btn.setMinimumSize(button_size)
        statistics_btn.clicked.connect(self.show_statistics)
        grid.addWidget(statistics_btn, 2, 1)

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
            frame.update_data()
        else:
            frame = ActivityFrame(self.activity_persistence)
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
        """Handle window closing - save all data"""
        # Save data from all cached frames
        if "activity_stats" in self._frame_cache:
            self._frame_cache["activity_stats"].save_data()
        if "storage" in self._frame_cache:
            self._frame_cache["storage"].save_data()
        if "bait" in self._frame_cache:
            self._frame_cache["bait"].save_data()
        event.accept()

    def open_background_settings(self):
        """Open background settings dialog"""
        from .dialogs.background_settings_dialog import BackgroundSettingsDialog
        dialog = BackgroundSettingsDialog(self, self._background_image_path, self._background_opacity)
        dialog.settings_changed.connect(self._on_background_settings_changed)
        dialog.exec()

    def _on_background_settings_changed(self, image_path: str, opacity: float):
        """Callback when background settings are changed"""
        self._background_image_path = image_path
        self._background_opacity = opacity

        # Save settings
        if self.app_settings_persistence:
            self.app_settings_persistence.save_settings(self._background_image_path, self._background_opacity)

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
            # No background, use default dark background
            return

        # Create new background label that covers the entire central widget
        self._background_label = QLabel(self.central_widget)
        pixmap = QPixmap(self._background_image_path)
        if not pixmap.isNull():
            # Scale pixmap to fit window
            scaled_pixmap = pixmap.scaled(
                self.central_widget.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            # Apply opacity
            palette = QPalette()
            brush = QBrush(scaled_pixmap)
            palette.setBrush(QPalette.Window, brush)
            self._background_label.setPalette(palette)
            # Make background transparent enough to not block content
            self._background_label.setWindowOpacity(self._background_opacity)
            self._background_label.setAutoFillBackground(True)
            self._background_label.resize(self.central_widget.size())
            # Background goes below all other content
            self._background_label.lower()
            self._background_label.show()

        # Also update background for home page content container
        if self.current_widget:
            # Make the content container background transparent
            # so the main background shows through
            self.current_widget.setAutoFillBackground(False)
            self.content_container.setAutoFillBackground(False)

    def resizeEvent(self, event):
        """Handle window resize to update background scaling"""
        super().resizeEvent(event)
        if self._background_label and self._background_image_path:
            self._update_background()

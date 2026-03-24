"""RF4 Data Tracker - Main entry point"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout
)
from PyQt6.QtGui import QPalette, QBrush, QPixmap, QColor
from PyQt6.QtCore import Qt

from src.core.data_manager import DataManager
from src.ui.lucky_draw import LuckyDrawWidget
from src.ui.grinding_stats import GrindingStatsWidget
from src.ui.storage_tracking import StorageTrackingWidget
from src.ui.kittens import KittenWidget
from src.core.background import BackgroundModel


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, data_dir: Path):
        super().__init__()
        self.data_dir = data_dir
        self.data_manager = DataManager(data_dir)
        self.background_model = BackgroundModel()

        # Load saved background settings
        bg_settings = self.data_manager.load_background_settings()
        self.background_model.load_from_data(bg_settings)

        self.setup_ui()
        self.setup_background()

    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("RF4 数据统计与推荐")
        self.resize(1200, 800)

        # Create menu bar
        self._setup_menu_bar()

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tabs = QTabWidget()

        # Add each tab
        self.lucky_draw_widget = LuckyDrawWidget(self.data_manager)
        self.tabs.addTab(self.lucky_draw_widget, "转盘抽奖")

        self.grinding_widget = GrindingStatsWidget(self.data_manager)
        self.tabs.addTab(self.grinding_widget, "搬砖统计")

        self.storage_widget = StorageTrackingWidget(self.data_manager)
        self.tabs.addTab(self.storage_widget, "窝子计时")

        # Import here to avoid circular dependency
        from src.ui.friend_links import FriendLinksWidget
        self.friend_links_widget = FriendLinksWidget(self.data_manager)
        self.tabs.addTab(self.friend_links_widget, "友情链接")

        # Add activity scheduler tab
        from src.ui.activity_scheduler import ActivitySchedulerWidget
        self.activity_widget = ActivitySchedulerWidget(self.data_manager)
        self.tabs.addTab(self.activity_widget, "活动推荐")

        layout.addWidget(self.tabs)

        # Add kittens that follow mouse (bottom right overlay)
        self.kittens = KittenWidget(self.centralWidget())
        self.kittens.move(
            self.width() - self.kittens.width() - 10,
            self.height() - self.kittens.height() - 10
        )
        self.kittens.show()

        # Save last open tab on close
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Load last open tab
        config = self.data_manager.load_config()
        if "last_open_tab" in config:
            self.tabs.setCurrentIndex(config["last_open_tab"])

    def setup_background(self):
        """Setup background image with transparency"""
        from PyQt6.QtWidgets import QWidget
        palette = self.centralWidget().palette()
        custom_path = self.background_model.get_custom_image_path()
        transparency = self.background_model.get_settings()["transparency"]

        if custom_path is not None and os.path.exists(custom_path):
            pixmap = QPixmap(custom_path)
            if not pixmap.isNull():
                # Scale to window size
                scaled = pixmap.scaled(
                    self.centralWidget().size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                # Create a new pixmap with transparency applied
                from PyQt6.QtGui import QPainter
                result = QPixmap(scaled.size())
                result.fill(Qt.GlobalColor.transparent)

                painter = QPainter(result)
                painter.setOpacity(transparency)
                painter.drawPixmap(0, 0, scaled)
                painter.end()

                brush = QBrush(result)
                palette.setBrush(QPalette.ColorRole.Window, brush)
                self.centralWidget().setAutoFillBackground(True)
                self.centralWidget().setPalette(palette)
        else:
            # Default light gray background
            palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
            self.centralWidget().setAutoFillBackground(True)
            self.centralWidget().setPalette(palette)

    def on_tab_changed(self, index):
        """Save last open tab"""
        config = self.data_manager.load_config()
        config["last_open_tab"] = index
        self.data_manager.save_config(config)

    def resizeEvent(self, event):
        """Handle resize - refresh background and reposition kittens"""
        super().resizeEvent(event)
        self.setup_background()
        # Reposition kittens to bottom right
        self.kittens.move(
            self.width() - self.kittens.width() - 10,
            self.height() - self.kittens.height() - 10
        )

    def _setup_menu_bar(self):
        """Setup the main menu bar"""
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("设置")

        # Background settings action
        from src.ui.background_settings import BackgroundSettingsDialog
        bg_action = settings_menu.addAction("背景设置")
        bg_action.triggered.connect(self._open_background_settings)

    def _open_background_settings(self):
        """Open background settings dialog"""
        from src.ui.background_settings import BackgroundSettingsDialog
        dialog = BackgroundSettingsDialog(self, self.background_model)
        if dialog.exec() == dialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            self.background_model.load_from_data(settings)
            self.setup_background()

    def closeEvent(self, event):
        """Save all data on close"""
        # All widgets save their own data on change, but just in case
        config = self.data_manager.load_config()
        config["window_width"] = self.width()
        config["window_height"] = self.height()
        self.data_manager.save_config(config)
        self.data_manager.save_background_settings(self.background_model.get_data_for_saving())
        event.accept()


def main():
    """Main entry point"""
    # Use data directory in same folder as exe or script
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        base_dir = Path(sys.executable).parent
    else:
        # Running as script
        base_dir = Path(__file__).parent.parent

    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)

    app = QApplication(sys.argv)
    window = MainWindow(data_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

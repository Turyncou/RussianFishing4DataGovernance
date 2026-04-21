"""
RF4 Data Process Application
Main entry point for PySide6 version
"""
import os
import sys
import logging

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Configure logging for performance monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src.gui.main_window import MainWindow
from src.gui.desktop_reminder import DesktopReminder
from src.utils.performance_monitor import PerformanceMonitor


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Get app data directory
    app_dir = os.path.join(os.path.expanduser('~'), '.rf4_data_process')
    os.makedirs(app_dir, exist_ok=True)

    # Load app settings first to check if performance logging is enabled
    from src.data.persistence import AppSettingsPersistence
    app_settings_persistence = AppSettingsPersistence(os.path.join(app_dir, 'app_settings.json'))
    settings = app_settings_persistence.load_settings()
    enable_performance_log = settings.get('enable_performance_log', True)

    # Start performance monitor if enabled
    perf_monitor = None
    if enable_performance_log:
        perf_monitor = PerformanceMonitor(interval_seconds=10.0)
        perf_monitor.start()
        if perf_monitor:
            perf_monitor.log_current()

    # Set application icon
    script_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(script_dir, "芋泥.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create main window
    main_window = MainWindow(app_dir)
    main_window.show()

    if perf_monitor:
        perf_monitor.log_current()

    # Create desktop floating reminder
    desktop_reminder = DesktopReminder()
    desktop_reminder.show()

    # Connect after data loaded to set daily task data for reminders
    def on_data_loaded():
        # Get activity characters after loading
        if main_window.activity_persistence and main_window.daily_task_persistence:
            characters, _ = main_window.activity_persistence.load_characters()
            desktop_reminder.set_daily_task_data(main_window.daily_task_persistence, characters)
        if perf_monitor:
            perf_monitor.log_current()

    main_window.data_loaded.connect(on_data_loaded)

    # Handle application exit
    try:
        exit_code = app.exec()
    finally:
        if perf_monitor:
            perf_monitor.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

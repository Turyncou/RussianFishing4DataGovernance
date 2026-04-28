"""
RF4 Data Process Application
Main entry point for PySide6 version - optimized for fast startup
"""
import os
import sys

# 启动时间测量 - 第一行就开始
import time
start_time = time.time()

# Add src to path - do this EARLY before any other imports
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 延迟导入：只导入最核心的，其他在后面按需导入
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 延迟重模块导入 - 在函数内部按需导入


def main():
    """Main entry point - optimized for fast startup"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set application icon FIRST - important for Windows taskbar to cache correctly
    script_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(script_dir, "芋泥.ico")
    app.setWindowIcon(QIcon(icon_path))

    # Get app data directory
    app_dir = os.path.join(os.path.expanduser('~'), '.rf4_data_process')
    os.makedirs(app_dir, exist_ok=True)

    # Load app settings first to check if performance logging is enabled
    # Do this BEFORE creating main window to avoid delays
    from src.data.persistence import AppSettingsPersistence
    app_settings_persistence = AppSettingsPersistence(os.path.join(app_dir, 'app_settings.json'))
    settings = app_settings_persistence.load_settings()
    enable_performance_log = settings.get('enable_performance_log', True)

    # Start performance monitor if enabled
    perf_monitor = None
    if enable_performance_log:
        from src.utils.performance_monitor import PerformanceMonitor
        perf_monitor = PerformanceMonitor(interval_seconds=10.0)
        perf_monitor.start()
        if perf_monitor:
            perf_monitor.log_current()

    # Create and show main window immediately
    # The loading screen will be visible while background data loads
    from src.gui.main_window import MainWindow
    main_window = MainWindow(app_dir)
    main_window.show()

    if perf_monitor:
        perf_monitor.log_current()

    # Create desktop reminder AFTER window is shown and after a delay
    # This avoids adding more work during the critical startup phase
    desktop_reminder = [None]  # Use list to allow modification in nested scope

    def delayed_desktop_reminder_setup():
        """Create desktop reminder after main window is fully loaded"""
        from src.gui.desktop_reminder import DesktopReminder
        desktop_reminder[0] = DesktopReminder()
        desktop_reminder[0].show()

    from PySide6.QtCore import QTimer
    QTimer.singleShot(2000, delayed_desktop_reminder_setup)

    # Connect after data loaded to set daily task data for reminders
    def on_data_loaded():
        # Get activity characters after loading
        if main_window.activity_persistence and main_window.daily_task_persistence:
            characters, _ = main_window.activity_persistence.load_characters()
            if desktop_reminder[0]:
                desktop_reminder[0].set_daily_task_data(main_window.daily_task_persistence, characters)
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

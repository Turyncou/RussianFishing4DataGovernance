"""
RF4 Data Process Application
Main entry point for PySide6 version
"""
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.gui.main_window import MainWindow
from src.gui.desktop_reminder import DesktopReminder


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Get app data directory
    app_dir = os.path.join(os.path.expanduser('~'), '.rf4_data_process')
    os.makedirs(app_dir, exist_ok=True)

    # Set application icon
    script_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(script_dir, "芋泥.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create main window
    main_window = MainWindow(app_dir)
    main_window.show()

    # Create desktop floating reminder
    desktop_reminder = DesktopReminder()
    desktop_reminder.show()

    # Handle application exit
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

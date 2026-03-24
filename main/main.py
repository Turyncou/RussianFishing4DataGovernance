"""
RF4 Data Process Application
Main entry point
"""
import os
import sys
import customtkinter as ctk

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from gui.main_window import MainWindow
from gui.desktop_reminder import DesktopReminderWindow


def main():
    """Main entry point"""
    # Set appearance mode and color theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Create app
    app = ctk.CTk()

    # Set window icon - for CustomTkinter needs after to work correctly
    script_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(script_dir, "芋泥.ico")
    if os.path.exists(icon_path):
        try:
            # After window is created, set icon
            app.after(100, lambda: app.iconbitmap(icon_path))
        except:
            pass  # Ignore if icon loading fails

    # Get app data directory
    app_dir = os.path.join(os.path.expanduser('~'), '.rf4_data_process')
    os.makedirs(app_dir, exist_ok=True)

    # Create main window
    main_window = MainWindow(app, app_dir)

    # Create desktop floating reminder (circular placeholder for Live2D)
    desktop_reminder = DesktopReminderWindow(app)

    # Set closing protocol
    def on_closing():
        # Close both windows
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    # Run the app
    app.mainloop()


if __name__ == "__main__":
    main()

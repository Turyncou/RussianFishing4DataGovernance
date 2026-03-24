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


def main():
    """Main entry point"""
    # Set appearance mode and color theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Create app
    app = ctk.CTk()

    # Get app data directory
    app_dir = os.path.join(os.path.expanduser('~'), '.rf4_data_process')
    os.makedirs(app_dir, exist_ok=True)

    # Create main window
    main_window = MainWindow(app, app_dir)

    # Set closing protocol
    app.protocol("WM_DELETE_WINDOW", main_window.on_closing)

    # Run the app
    app.mainloop()


if __name__ == "__main__":
    main()

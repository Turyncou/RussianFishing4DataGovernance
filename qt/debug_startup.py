"""
Startup debug script - prints timestamp at each step
Run this to see EXACTLY where the hang is happening!
"""
import sys
import os
import time

def t(step_name):
    """Print timestamp"""
    elapsed = time.time() - START_TIME
    print(f"[{elapsed:7.3f}s] {step_name}", flush=True)

START_TIME = time.time()
t("PROCESS START - Python interpreter initialized")

# Add src path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
t("Source path configured")

# Test 1: Import QtCore
print("\n--- IMPORTING QtCore ---", flush=True)
from PySide6.QtCore import Qt, QTimer, QSize, Signal
t("QtCore imported")

# Test 2: Import QtGui
print("\n--- IMPORTING QtGui ---", flush=True)
from PySide6.QtGui import QIcon, QFont, QPalette, QBrush, QPixmap
t("QtGui imported")

# Test 3: Import QtWidgets (THIS IS THE BIG ONE)
print("\n--- IMPORTING QtWidgets (THIS IS USUALLY SLOW) ---", flush=True)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QProgressBar,
    QMessageBox, QSizePolicy, QApplication
)
t("QtWidgets imported - THIS WAS THE HEAVIEST IMPORT")

# Test 4: Import main window
print("\n--- IMPORTING MainWindow ---", flush=True)
from src.gui.main_window import MainWindow
t("MainWindow imported")

# Test 5: Create QApplication
print("\n--- CREATING QApplication ---", flush=True)
app = QApplication(sys.argv)
app.setStyle("Fusion")
t("QApplication created")

# Test 6: Create MainWindow
print("\n--- CREATING MainWindow INSTANCE ---", flush=True)
data_dir = os.path.join(os.path.expanduser('~'), '.rf4_data_process')
os.makedirs(data_dir, exist_ok=True)
t(f"Data dir ready: {data_dir}")

window = MainWindow(data_dir)
t("MainWindow instance created")

# Test 7: Show window
print("\n--- SHOWING WINDOW ---", flush=True)
window.show()
t("Window shown - UI should be VISIBLE NOW!")

print("\n" + "="*60)
total = time.time() - START_TIME
print(f"TOTAL TIME TO WINDOW VISIBLE: {total:.3f} seconds")
print("="*60)
print("\nLook at the timestamps above.")
print("Which step took the LONGEST time? That's where the problem is!")
print("\nClosing in 5 seconds...")

# Close after 5 seconds
QTimer.singleShot(5000, app.quit)
app.exec()

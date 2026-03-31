"""Desktop floating reminder with circular placeholder (will replace with Live2D later)"""
import sys
import math
import random
from datetime import datetime, date
from typing import Optional
import ctypes
from ctypes import wintypes

from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QLabel, QPushButton, QDialog,
    QHBoxLayout, QSpinBox, QLineEdit, QMessageBox, QMenu
)
from PySide6.QtGui import (
    QPainter, QBrush, QPen, QColor, QMouseEvent, QFont, QPaintEvent,
    QRegion, QAction
)
from PySide6.QtCore import (
    Qt, QPoint, QTimer, QRect, QSize, Signal
)


# ========== 可自定义的随机鼓励话语 ==========
RANDOM_MESSAGES = [
    "今天也加油钓哦！🎣",
    "记得休息，身体最重要！💪",
    "今天会上星哦！✨",
    "多喝水，活动脖子，保护颈椎！🪑",
    "希望你今天出星星✨",
    "搬砖辛苦了，休息一下吧😴",
    "保持耐心，周榜鱼就在前方！🎯",
    "今天也要出货满满！💰",
    "站起来走两步，有益身体健康🚶",
]
# ========== 可自定义区域结束 ==========


# Windows API constants
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000


class CircularWidget(QWidget):
    """Circular widget that draws a circle with text"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(150, 150)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event: QPaintEvent):
        """Draw the circle"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw circle
        center = QPoint(75, 75)
        radius = 65
        painter.setBrush(QBrush(QColor("#2c5aa0")))
        painter.setPen(QPen(QColor("#1a3d66"), 3))
        painter.drawEllipse(center, radius, radius)

        # Draw text
        painter.setFont(QFont("Arial", 18, QFont.Bold))
        painter.setPen(QPen(QColor("white")))
        painter.drawText(self.rect(), Qt.AlignCenter, "RF4")


class DesktopReminder(QMainWindow):
    """Desktop floating reminder window - circular placeholder for Live2D"""

    # Configurable dimensions
    MAIN_WINDOW_SIZE = 150
    DEFAULT_SCREEN_MARGIN_X = 30
    DEFAULT_SCREEN_MARGIN_Y = 50
    BUBBLE_FIXED_WIDTH = 280
    BUBBLE_TAIL_HEIGHT = 15
    BUBBLE_TIP_DISTANCE_FROM_MODEL = 8

    def __init__(self):
        super().__init__()
        self.is_visible = True
        self.click_steals_focus = False  # 是否点击抢焦点，False = 点击不抢焦点（保持游戏焦点）
        self.bubble_always_top = True  # 气泡是否始终置顶
        self._bubble_anim_phase = 0
        self._bubble_anim_running = False

        # Get screen geometry
        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            screen_width = screen_geo.width()
            screen_height = screen_geo.height()
            x = screen_width - self.MAIN_WINDOW_SIZE - self.DEFAULT_SCREEN_MARGIN_X
            y = screen_height - self.MAIN_WINDOW_SIZE - self.DEFAULT_SCREEN_MARGIN_Y
        else:
            x = 1000
            y = 500

        # Window setup
        self.setWindowTitle("RF4 桌面提醒")
        self.setFixedSize(self.MAIN_WINDOW_SIZE, self.MAIN_WINDOW_SIZE)
        self.move(x, y)

        # Remove window frame, make background transparent
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # On Windows, set the window to not activate when clicked using Windows API
        # This keeps focus on the original game while still allowing dragging
        if sys.platform == 'win32':
            try:
                hwnd = int(self.winId())
                style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
                style |= WS_EX_NOACTIVATE
                style |= WS_EX_TOOLWINDOW  # Tool window - don't show in taskbar
                style &= ~WS_EX_APPWINDOW  # Remove app window flag
                ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
            except Exception:
                pass

        # Central widget with circle
        central = CircularWidget()
        self.setCentralWidget(central)
        self.circular_widget = central

        # Bubble state
        self.bubble_window: Optional[BubbleWindow] = None
        self.bubble_visible = False
        self.bubble_message = ""
        self.context_menu: Optional[QMenu] = None
        self.last_reminder_type: Optional[str] = None
        self.reminder_shown = False
        # Track which day we've already reminded for daily reminders
        self.last_reminded_date: Optional[date] = None
        self.daily_reminded_flags = {
            "00:00": False,
            "18:00": False,
            "meal": False,
        }

        # Bubble animation timer
        self._bubble_timer: Optional[QTimer] = None
        self._bubble_anim_phase = 0

        # Mouse dragging state
        self._drag_start_pos: Optional[QPoint] = None
        self._window_start_pos: Optional[QPoint] = None

        # Install event filter for mouse events
        central.mousePressEvent = self._on_mouse_press
        central.mouseMoveEvent = self._on_mouse_move
        central.mouseDoubleClickEvent = self._on_double_click
        central.contextMenuEvent = self._show_context_menu

        # Start timer for time checking
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self.check_time)
        self._check_timer.start(60 * 1000)  # Check every minute

        # Schedule first random talk after 15-30 seconds for testing
        self._schedule_random_talk()

    def _on_mouse_press(self, event: QMouseEvent):
        """Start dragging"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._window_start_pos = self.pos()

    def _on_mouse_move(self, event: QMouseEvent):
        """Continue dragging"""
        if self._drag_start_pos is not None and self._window_start_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            new_pos = self._window_start_pos + delta

            # Keep window within screen bounds
            screen = self.screen()
            if screen:
                screen_geo = screen.availableGeometry()
                new_pos.setX(max(0, min(new_pos.x(), screen_geo.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), screen_geo.height() - self.height())))

            self.move(new_pos)
            self._update_bubble_position()

    def _on_double_click(self, event: QMouseEvent):
        """Toggle visibility on double click"""
        if event.button() == Qt.LeftButton:
            self.toggle_visibility()

    def toggle_visibility(self):
        """Toggle window visibility"""
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.show()
        else:
            self.hide()
            self.close_bubble()

    def show_bubble(self, message: str, has_button: bool = False, button_text: str = "知道了"):
        """Show speech bubble with message"""
        # Ensure any existing animation is completely stopped before creating new bubble
        if self._bubble_timer is not None:
            self._bubble_timer.stop()
            self._bubble_timer.timeout.disconnect()
            self._bubble_timer.deleteLater()
            self._bubble_timer = None

        self.close_bubble()

        self.bubble_visible = True
        self.bubble_message = message
        self.reminder_shown = True

        self.bubble_window = BubbleWindow(message, has_button, button_text, self)
        self.bubble_window.close_requested.connect(self.close_bubble)

        # Set window flags for no activation
        if sys.platform == 'win32' and not self.click_steals_focus:
            try:
                hwnd = int(self.bubble_window.winId())
                style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
                style |= WS_EX_NOACTIVATE
                style |= WS_EX_TOOLWINDOW
                style &= ~WS_EX_APPWINDOW
                ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
            except Exception:
                pass

        if self.bubble_always_top:
            self.bubble_window.setWindowFlags(
                self.bubble_window.windowFlags() | Qt.WindowStaysOnTopHint
            )

        self._update_bubble_position()
        self.bubble_window.show()
        self._start_bubble_animation()

    def _start_bubble_animation(self):
        """Start floating animation for bubble"""
        # Stop any existing animation completely before starting new one
        if self._bubble_timer is not None:
            self._bubble_timer.stop()
            try:
                self._bubble_timer.timeout.disconnect(self._animate_bubble)
            except (TypeError, RuntimeError):
                pass  # Already disconnected
            self._bubble_timer.deleteLater()
            self._bubble_timer = None

        self._bubble_anim_phase = 0
        self._bubble_timer = QTimer(self)
        self._bubble_timer.timeout.connect(self._animate_bubble)
        self._bubble_timer.start(16)  # 60 FPS = 16ms per frame

    def _animate_bubble(self):
        """Animate bubble floating"""
        if self.bubble_window is None or self._bubble_timer is None:
            return

        # Calculate base position
        main_x = self.x()
        main_y = self.y()
        main_w = self.width()
        main_h = self.height()
        bubble_h = self.bubble_window.height()
        bubble_w = self.bubble_window.width()

        circle_center_y = main_y + main_h // 2
        circle_top_y = circle_center_y - (main_h // 2)
        base_y = circle_top_y - self.BUBBLE_TIP_DISTANCE_FROM_MODEL - bubble_h
        base_x = main_x + (main_w - bubble_w) // 2

        # Floating animation
        amplitude = 6
        speed = 0.15
        offset = math.sin(self._bubble_anim_phase) * amplitude
        self._bubble_anim_phase += speed

        final_y = int(base_y + offset)
        final_x = int(base_x)

        # Keep within screen bounds
        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            if final_x < 0:
                final_x = 0
            if final_x + bubble_w > screen_geo.width():
                final_x = screen_geo.width() - bubble_w
            if final_y < 0:
                final_y = 0

        self.bubble_window.move(final_x, final_y)

    def close_bubble(self):
        """Close the speech bubble"""
        # Stop animation timer completely
        if self._bubble_timer is not None:
            self._bubble_timer.stop()
            try:
                self._bubble_timer.timeout.disconnect(self._animate_bubble)
            except (TypeError, RuntimeError):
                pass  # Already disconnected
            self._bubble_timer.deleteLater()
            self._bubble_timer = None

        if self.bubble_visible and self.bubble_window is not None:
            self.bubble_visible = False
            self.bubble_message = ""
            self.reminder_shown = False
            self.bubble_window.close()
            self.bubble_window = None

    def _update_bubble_position(self):
        """Update bubble position to follow main window"""
        if not self.bubble_visible or self.bubble_window is None:
            return

        main_x = self.x()
        main_y = self.y()
        main_w = self.width()
        main_h = self.height()
        bubble_h = self.bubble_window.height()
        bubble_w = self.bubble_window.width()

        circle_center_y = main_y + main_h // 2
        circle_top_y = circle_center_y - (main_h // 2)
        bubble_tip_y = circle_top_y - self.BUBBLE_TIP_DISTANCE_FROM_MODEL
        bubble_y = bubble_tip_y - bubble_h

        bubble_x = main_x + (main_w - bubble_w) // 2

        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            if bubble_x < 0:
                bubble_x = 0
            if bubble_x + bubble_w > screen_geo.width():
                bubble_x = screen_geo.width() - bubble_w
            if bubble_y < 0:
                bubble_y = 0

        self.bubble_window.move(int(bubble_x), int(bubble_y))

    def check_time(self):
        """Check current time and trigger scheduled reminders"""
        now = datetime.now()
        today = now.date()
        hour = now.hour
        minute = now.minute

        # Reset daily reminder flags when date changes
        if self.last_reminded_date != today:
            self.daily_reminded_flags["00:00"] = False
            self.daily_reminded_flags["18:00"] = False
            self.daily_reminded_flags["meal"] = False
            self.last_reminded_date = today

        triggered = False
        message = ""
        has_button = False

        # 00:00 - remind open overtime machine
        if hour == 0 and 0 <= minute < 8 and not self.daily_reminded_flags["00:00"]:
            message = "📅 已经到零点啦\n记得打开加班机开始肝了哦！"
            has_button = True
            triggered = True
            self.daily_reminded_flags["00:00"] = True
            # Schedule second reminder if not confirmed
            QTimer.singleShot(5 * 60 * 1000, lambda: self.check_second_reminder("00:00"))

        # 18:00 - remind start streaming
        elif hour == 18 and 0 <= minute < 8 and not self.daily_reminded_flags["18:00"]:
            message = "🎬 到开播时间啦\n记得开播打渔哦！"
            has_button = True
            triggered = True
            self.daily_reminded_flags["18:00"] = True
            # Schedule second reminder if not confirmed
            QTimer.singleShot(5 * 60 * 1000, lambda: self.check_second_reminder("18:00"))

        # Meal time reminders
        elif (hour == 12 and 0 <= minute < 30) or (hour == 18 and 30 <= minute < 60) or (hour == 7 and 0 <= minute < 30):
            if not self.daily_reminded_flags["meal"] or self.last_reminder_type != "meal":
                message = "🍚 到饭点了哦\n记得放下鱼竿去吃饭\n多喝水，多走动！"
                triggered = True
                self.last_reminder_type = "meal"

        # Every two hours - remind rest
        elif minute == 0 and not triggered:
            if hour % 2 == 0:
                message = "💪 已经玩了一小时啦\n起来活动一下\n喝口水转转腰~"
                triggered = True

        if triggered and message:
            self.show_bubble(message, has_button)

    def check_second_reminder(self, reminder_type: str):
        """Check if reminder was not confirmed and remind again"""
        if self.reminder_shown:
            return

        if reminder_type == "00:00":
            self.show_bubble("⏰ 又到零点五分啦\n还记得打开加班机了吗？记得打开哦！", True, "打开了")
        elif reminder_type == "18:00":
            self.show_bubble("⏰ 到六点五分啦\n还记得开播了吗？记得开播哦！", True, "开播了")

    def _schedule_random_talk(self):
        """Schedule random small talk reminder (15-30 minutes interval)"""
        interval = random.randint(15 * 60 * 1000, 30 * 60 * 1000)
        QTimer.singleShot(interval, self._trigger_random_talk)

    def _trigger_random_talk(self):
        """Trigger random talk and reschedule"""
        # 50% chance to show
        if random.random() < 0.5:
            message = random.choice(RANDOM_MESSAGES)
            if not self.reminder_shown:
                self.show_bubble(message, has_button=False)
        self._schedule_random_talk()

    def _show_context_menu(self, event):
        """Show right click context menu"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }
            QMenu::item {
                padding: 6px 12px;
            }
            QMenu::item:selected {
                background-color: #1f6feb;
            }
        """)

        # Menu items
        action_summary = QAction("💬 显示今日提醒", self)
        action_summary.triggered.connect(self.show_today_summary)
        menu.addAction(action_summary)

        action_custom = QAction("⏰ 添加自定义提醒", self)
        action_custom.triggered.connect(self.open_custom_reminder_dialog)
        menu.addAction(action_custom)

        menu.addSeparator()

        focus_text = "✅ 点击不抢焦点" if not self.click_steals_focus else "❌ 点击抢焦点"
        action_focus = QAction(focus_text, self)
        action_focus.triggered.connect(self.toggle_focus_mode)
        menu.addAction(action_focus)

        top_text = "✅ 气泡始终置顶" if self.bubble_always_top else "❌ 气泡不强制置顶"
        action_top = QAction(top_text, self)
        action_top.triggered.connect(self.toggle_bubble_top)
        menu.addAction(action_top)

        menu.addSeparator()

        action_vis = QAction("👁️ 切换显示", self)
        action_vis.triggered.connect(lambda: self.toggle_visibility())
        menu.addAction(action_vis)

        action_random = QAction("🔄 弹出随机鼓励", self)
        action_random.triggered.connect(self.trigger_random_message)
        menu.addAction(action_random)

        menu.exec(event.globalPos())

    def show_today_summary(self):
        """Show today's summary reminder"""
        now = datetime.now()
        summary = f"📅 今日提醒\n\n当前时间: {now.strftime('%H:%M')}\n\n"
        summary += "• 00:00 提醒打开加班机\n"
        summary += "• 18:00 提醒开播\n"
        summary += "• 饭点提醒吃饭喝水\n"
        summary += "• 每两小时提醒休息"
        self.show_bubble(summary)

    def trigger_random_message(self):
        """Trigger a random message now"""
        if self.reminder_shown:
            self.close_bubble()
        message = random.choice(RANDOM_MESSAGES)
        self.show_bubble(message)

    def open_custom_reminder_dialog(self):
        """Open dialog to add custom one-time reminder"""
        dialog = CustomReminderDialog(self)
        dialog.accepted.connect(self._on_custom_reminder)
        dialog.exec()

    def _on_custom_reminder(self, minutes: int, message: str):
        """Schedule a custom reminder after N minutes"""
        QTimer.singleShot(minutes * 60 * 1000, lambda: self.show_bubble(message, True))

    def toggle_focus_mode(self):
        """Toggle whether clicking steals focus"""
        self.click_steals_focus = not self.click_steals_focus

        # Apply the setting using Windows API
        if sys.platform == 'win32':
            try:
                hwnd = int(self.winId())
                style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
                if not self.click_steals_focus:
                    style |= WS_EX_NOACTIVATE
                else:
                    style &= ~WS_EX_NOACTIVATE
                ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
            except Exception:
                pass

        # Show status
        if self.click_steals_focus:
            self.show_bubble("当前模式：点击会抢焦点\n游戏焦点会被夺走")
        else:
            self.show_bubble("当前模式：点击不抢焦点✓\n焦点保持在游戏\n仍可以正常拖动")

    def toggle_bubble_top(self):
        """Toggle whether bubble is always on top"""
        self.bubble_always_top = not self.bubble_always_top

        # Apply to current bubble
        if self.bubble_window is not None:
            if self.bubble_always_top:
                self.bubble_window.setWindowFlags(
                    self.bubble_window.windowFlags() | Qt.WindowStaysOnTopHint
                )
            else:
                self.bubble_window.setWindowFlags(
                    self.bubble_window.windowFlags() & ~Qt.WindowStaysOnTopHint
                )
            self.bubble_window.show()

        if self.bubble_always_top:
            self.show_bubble("当前：气泡始终置顶✓")
        else:
            self.show_bubble("当前：气泡不强制置顶\n可能被其他窗口覆盖")


class BubbleWindow(QWidget):
    """Speech bubble window with tail pointing to main circle"""

    close_requested = Signal()

    def __init__(self, message: str, has_button: bool, button_text: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 17)  # Extra space at bottom for tail

        # Content frame
        content = QWidget()
        content.setStyleSheet("""
            QWidget {
                background-color: #3a3a3a;
                border-radius: 10px;
            }
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 15, 15, 10 if has_button else 15)

        # Message label
        label = QLabel(message)
        label.setFont(QFont("Segoe UI", 14))
        label.setStyleSheet("color: #f0f0f0;")
        label.setWordWrap(True)
        label.setFixedWidth(250)
        label.mousePressEvent = lambda e: self.close_requested.emit()
        content_layout.addWidget(label)

        # Button if needed
        if has_button:
            btn = QPushButton(button_text)
            btn.setFixedSize(80, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #555555;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #777777;
                }
            """)
            btn.clicked.connect(self.close_requested.emit)
            content_layout.addWidget(btn, alignment=Qt.AlignHCenter)

        layout.addWidget(content)
        self.setLayout(layout)

        # Make it fit content
        self.adjustSize()

    def paintEvent(self, event):
        """Draw the tail pointing to main window"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the tail at bottom center pointing down
        content_width = self.width() - 4
        tail_center_x = content_width // 2
        frame_bottom_y = self.height() - 17

        # Polygon points for tail
        points = [
            QPoint(tail_center_x - 10, frame_bottom_y),
            QPoint(tail_center_x - 3, frame_bottom_y + (15 - 3)),
            QPoint(tail_center_x + 3, frame_bottom_y + (15 - 3)),
            QPoint(tail_center_x + 10, frame_bottom_y),
        ]

        painter.setBrush(QBrush(QColor("#3a3a3a")))
        painter.setPen(QPen(QColor("#3a3a3a")))
        painter.drawPolygon(points)

    def mousePressEvent(self, event):
        """Close when clicked anywhere"""
        super().mousePressEvent(event)
        self.close_requested.emit()


class CustomReminderDialog(QDialog):
    """Dialog to create a custom one-time reminder"""

    accepted = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加自定义提醒")
        self.setFixedSize(350, 250)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Minutes
        layout.addWidget(QLabel("多少分钟后提醒"))
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(1, 999)
        self.minutes_spin.setValue(30)
        layout.addWidget(self.minutes_spin)

        # Message
        layout.addWidget(QLabel("提醒内容"))
        self.message_edit = QLineEdit()
        self.message_edit.setText("该休息一下了哦")
        layout.addWidget(self.message_edit)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #888888;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(btn_layout)

    def _confirm(self):
        """Confirm and schedule"""
        try:
            minutes = self.minutes_spin.value()
            message = self.message_edit.text().strip()
            if minutes > 0 and message:
                self.accepted.emit(minutes, message)
                self.accept()
            else:
                if minutes <= 0:
                    QMessageBox.warning(self, "输入错误", "提醒分钟数必须大于0")
                else:
                    QMessageBox.warning(self, "输入错误", "提醒内容不能为空")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的分钟数")

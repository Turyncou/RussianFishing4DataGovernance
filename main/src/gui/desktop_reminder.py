"""Desktop floating reminder with circular placeholder (will replace with Live2D later)"""
import customtkinter as ctk
from tkinter import Canvas
from datetime import datetime
from typing import Optional
import random


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


class DesktopReminderWindow:
    """Desktop floating reminder window - circular placeholder for Live2D"""

    def __init__(self, root):
        self.root = root
        self.is_visible = True
        self.click_steals_focus = False  # 是否点击抢焦点，False = 点击不抢焦点（保持游戏焦点）
        self.bubble_always_top = True  # 气泡是否始终置顶

        # Create independent toplevel window
        # Position at bottom-right corner by default
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = screen_width - 180
        y = screen_height - 200

        self.window = ctk.CTkToplevel(root)
        self.window.title("RF4 桌面提醒")
        self.window.geometry(f"150x150+{x}+{y}")
        self.window.overrideredirect(True)  # No title bar
        self.window.attributes('-topmost', True)  # Always on top

        # On Windows, use transparent color for the window background
        self.window.attributes('-transparentcolor', '#1a1a1a')

        # On Windows, set the window to not activate when clicked
        # This keeps focus on the original game while still allowing dragging
        try:
            # Use extended window style to prevent activation
            import ctypes
            from ctypes import wintypes
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_LAYERED = 0x00080000
            hwnd = self.window.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
            style |= WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
        except:
            # If not on Windows or fails, just continue normally
            pass

        # Canvas for circular placeholder
        self.canvas = Canvas(
            self.window,
            width=150,
            height=150,
            bg='#1a1a1a',
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Draw circular placeholder
        self.draw_circle()

        # Bind mouse events for dragging
        self.canvas.bind('<Button-1>', self.on_start_drag)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<Double-1>', self.toggle_visibility)
        # Right click to show context menu
        self.canvas.bind('<Button-3>', self.show_context_menu)

        # Speech bubble (hidden by default)
        self.bubble: Optional[ctk.CTkToplevel] = None
        self.context_menu: Optional[ctk.CTkToplevel] = None
        self.last_reminder_type: Optional[str] = None
        self.reminder_shown = False

        # Start timer check
        self.check_time()
        # Random small talk timer (every 15-30 minutes)
        self.schedule_random_talk()

    def draw_circle(self):
        """Draw the circular placeholder"""
        self.canvas.delete("all")
        # Draw gradient-like circle
        self.canvas.create_oval(
            10, 10, 140, 140,
            fill='#2c5aa0',
            outline='#1a3d66',
            width=3,
            tags="circle"
        )
        # Draw text as placeholder
        self.canvas.create_text(
            75, 75,
            text="RF4",
            fill="white",
            font=("Arial", 18, "bold")
        )

    def on_start_drag(self, event):
        """Start dragging the window"""
        self.x_start = event.x
        self.y_start = event.y

    def on_drag(self, event):
        """Continue dragging, move bubble along with us, keep window inside screen bounds"""
        dx = event.x - self.x_start
        dy = event.y - self.y_start
        x = self.window.winfo_x() + dx
        y = self.window.winfo_y() + dy

        # Keep window within screen bounds - don't allow dragging outside
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()

        # Constrain x: at least 0, at most screen_width - window_width
        x = max(0, min(x, screen_width - window_width))
        # Constrain y: at least 0, at most screen_height - window_height
        y = max(0, min(y, screen_height - window_height))

        self.window.geometry(f"+{x}+{y}")

        # If bubble is visible, move it along with the circle
        if self.bubble is not None and hasattr(self.bubble, 'winfo_exists') and self.bubble.winfo_exists():
            self.reposition_bubble()

    def reposition_bubble(self):
        """Reposition bubble to follow current circle position"""
        if self.bubble is None or not hasattr(self.bubble, 'winfo_exists') or not self.bubble.winfo_exists():
            return

        # Get current circle position
        win_x = self.window.winfo_x()
        win_y = self.window.winfo_y()
        win_w = self.window.winfo_width()
        win_h = self.window.winfo_height()

        # Recalculate bubble position
        bubble_width = 280
        bubble_height = 120
        bubble_x = win_x + (win_w - bubble_width) // 2
        bubble_y = win_y - bubble_height - 20

        # Update bubble geometry
        self.bubble.geometry(f"{bubble_width}x{bubble_height}+{bubble_x}+{bubble_y}")

    def toggle_visibility(self, event):
        """Toggle window visibility on double click"""
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.window.deiconify()
        else:
            self.window.withdraw()

    def show_bubble(self, message: str, has_button: bool = False, button_text: str = "知道了"):
        """Show speech bubble with message - positioned above current circle position"""
        # Close existing bubble
        if self.bubble is not None:
            try:
                self.bubble.destroy()
            except:
                pass

        # Get current circle position
        win_x = self.window.winfo_x()
        win_y = self.window.winfo_y()
        win_w = self.window.winfo_width()
        win_h = self.window.winfo_height()

        # Bubble width fixed, calculate dynamic height based on content
        bubble_width = 280
        # Estimate number of lines: count explicit newlines + estimate wrapped lines
        import math
        explicit_lines = message.count('\n') + 1
        # Each line after wrapping is about (bubble_width - 30) / average char width
        avg_chars_per_line = (bubble_width - 30) // 10
        wrapped_lines = math.ceil(len(message) / avg_chars_per_line) if message else 1
        estimated_lines = max(explicit_lines, wrapped_lines)
        # Calculate height: base padding + estimated text lines + button space if needed
        line_height = 22
        base_height = 30  # top/bottom padding
        button_height = 40 if has_button else 0
        bubble_height = base_height + estimated_lines * line_height + button_height
        # Minimum height
        bubble_height = max(bubble_height, 100)
        # Maximum height to prevent too big
        bubble_height = min(bubble_height, 350)

        # Position bubble centered above the circle
        bubble_x = win_x + (win_w - bubble_width) // 2
        bubble_y = win_y - bubble_height - 20  # 20px gap above circle

        # Create new bubble window with transparent background
        self.bubble = ctk.CTkToplevel(self.window)
        self.bubble.title("提醒")
        self.bubble.overrideredirect(True)
        if self.bubble_always_top:
            self.bubble.attributes('-topmost', True)
        self.bubble.attributes('-transparentcolor', '#1a1a1a')
        self.bubble.geometry(f"{bubble_width}x{bubble_height}+{bubble_x}+{bubble_y}")

        # Also prevent bubble from stealing focus if needed
        if not self.click_steals_focus:
            try:
                import ctypes
                from ctypes import wintypes
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                hwnd = self.bubble.winfo_id()
                style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
                style |= WS_EX_NOACTIVATE
                ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
            except:
                pass

        # Create bubble canvas to draw bubble shape with tail pointing to circle
        bubble_canvas = Canvas(
            self.bubble,
            width=bubble_width,
            height=bubble_height,
            bg='#1a1a1a',
            highlightthickness=0,
            bd=0
        )
        bubble_canvas.pack(fill="both", expand=True)

        # Draw bubble shape (rounded rectangle with pointed tail)
        # We need to create rounded rectangle manually for canvas
        # Draw main body - larger radius creates cloud-like rounded corners
        self._draw_rounded_rect(bubble_canvas, 5, 5, bubble_width-5, bubble_height-25, "#252525", "#444444")

        # Draw tail pointing down to the circle - slightly wider for more natural look
        tail_points = [
            bubble_width // 2 - 10, bubble_height - 25,
            bubble_width // 2, bubble_height - 8,
            bubble_width // 2 + 10, bubble_height - 25,
        ]
        bubble_canvas.create_polygon(
            tail_points,
            fill="#252525",
            outline="#444444",
            width=1
        )

        # Add text frame
        text_frame = ctk.CTkFrame(
            bubble_canvas,
            fg_color="#252525",
            corner_radius=0
        )
        text_frame.place(x=12, y=8, relwidth=0.92)

        label = ctk.CTkLabel(
            text_frame,
            text=message,
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            wraplength=bubble_width - 30,
            text_color="#ffffff",
            justify="center"
        )
        label.pack(padx=5, pady=(0, 5))

        # Add confirm button if needed
        if has_button:
            btn = ctk.CTkButton(
                text_frame,
                text=button_text,
                command=self.close_bubble,
                width=80,
                corner_radius=8
            )
            btn.pack(pady=(5, 0))

        # Click anywhere to close
        bubble_canvas.bind('<Button-1>', lambda e: self.close_bubble())

        self.reminder_shown = True

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, fill, outline):
        """Draw rounded rectangle on canvas - large radius for cloud/bubble-like shape"""
        radius = 20  # Larger radius for more cloud-like appearance
        # Draw the main rectangle
        canvas.create_rectangle(x1+radius, y1, x2-radius, y2, fill=fill, outline="")
        canvas.create_rectangle(x1, y1+radius, x2, y2-radius, fill=fill, outline="")
        # Draw the four corners - larger radius makes it more cloud-like
        canvas.create_oval(x1, y1, x1+radius*2, y1+radius*2, fill=fill, outline="")
        canvas.create_oval(x2-radius*2, y1, x2, y1+radius*2, fill=fill, outline="")
        canvas.create_oval(x1, y2-radius*2, x1+radius*2, y2, fill=fill, outline="")
        canvas.create_oval(x2-radius*2, y2-radius*2, x2, y2, fill=fill, outline="")
        # Draw the outline
        canvas.create_line(x1+radius, y1, x2-radius, y1, fill=outline, width=1)
        canvas.create_line(x1+radius, y2, x2-radius, y2, fill=outline, width=1)
        canvas.create_line(x1, y1+radius, x1, y2-radius, fill=outline, width=1)
        canvas.create_line(x2, y1+radius, x2, y2-radius, fill=outline, width=1)

    def close_bubble(self):
        """Close the speech bubble"""
        if self.bubble is not None:
            self.bubble.destroy()
            self.bubble = None
            self.reminder_shown = False

    def check_time(self):
        """Check current time and trigger scheduled reminders"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute

        triggered = False
        message = ""
        has_button = False

        # 00:00 - remind open overtime machine
        if hour == 0 and 0 <= minute < 8 and not self.reminder_shown:
            message = "📅 已经到零点啦\n记得打开加班机开始肝了哦！"
            has_button = True
            triggered = True
            # Schedule second reminder if not confirmed
            self.root.after(5 * 60 * 1000, lambda: self.check_second_reminder("00:00"))

        # 18:00 - remind start streaming
        elif hour == 18 and 0 <= minute < 8 and not self.reminder_shown:
            message = "🎬 到开播时间啦\n记得开播打渔哦！"
            has_button = True
            triggered = True
            # Schedule second reminder if not confirmed
            self.root.after(5 * 60 * 1000, lambda: self.check_second_reminder("18:00"))

        # Meal time reminders
        elif (hour == 12 and 0 <= minute < 30) or (hour == 18 and 30 <= minute < 60) or (hour == 7 and 0 <= minute < 30):
            if not self.reminder_shown or self.last_reminder_type != "meal":
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

        # Check again in 1 minute
        self.root.after(60 * 1000, self.check_time)

    def check_second_reminder(self, reminder_type: str):
        """Check if reminder was not confirmed and remind again"""
        if self.reminder_shown:
            # Already confirmed, do nothing
            return

        if reminder_type == "00:00":
            self.show_bubble("⏰ 又到零点五分啦\n还记得打开加班机了吗？记得打开哦！", True, "打开了")
        elif reminder_type == "18:00":
            self.show_bubble("⏰ 到六点五分啦\n还记得开播了吗？记得开播哦！", True, "开播了")

    def schedule_random_talk(self):
        """Schedule random small talk reminder (15-30 minutes interval)"""
        # Random interval between 15-30 minutes
        interval = random.randint(15 * 60 * 1000, 30 * 60 * 1000)

        # 50% chance to show random encouragement
        if random.random() < 0.5:
            message = random.choice(RANDOM_MESSAGES)
            # Don't show if already showing a scheduled reminder
            if not self.reminder_shown:
                self.show_bubble(message, has_button=False)

        # Schedule next random talk
        self.root.after(interval, self.schedule_random_talk)

    def show_context_menu(self, event):
        """Show right click context menu - easy to extend with new menu items"""
        # Close existing menu
        if self.context_menu is not None:
            try:
                self.context_menu.destroy()
            except:
                pass

        # Get click position for menu placement
        click_x = self.window.winfo_x() + event.x
        click_y = self.window.winfo_y() + event.y

        # Create context menu window
        self.context_menu = ctk.CTkToplevel(self.window)
        self.context_menu.title("菜单")
        self.context_menu.overrideredirect(True)
        self.context_menu.attributes('-topmost', True)
        # Position menu at click point
        self.context_menu.geometry(f"180x-auto+{click_x}+{click_y}")
        # Also prevent context menu from stealing focus
        if not self.click_steals_focus:
            try:
                import ctypes
                from ctypes import wintypes
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                hwnd = self.context_menu.winfo_id()
                style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
                style |= WS_EX_NOACTIVATE
                ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
            except:
                pass

        # Menu container
        menu_frame = ctk.CTkFrame(
            self.context_menu,
            fg_color="#252525",
            corner_radius=8
        )
        menu_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Menu items - add new items here easily
        focus_text = "✅ 点击不抢焦点" if not self.click_steals_focus else "❌ 点击抢焦点"
        top_text = "✅ 气泡始终置顶" if self.bubble_always_top else "❌ 气泡不强制置顶"
        menu_items = [
            ("💬 显示今日提醒", self.show_today_summary),
            ("⏰ 添加自定义提醒", self.open_custom_reminder_dialog),
            (focus_text, self.toggle_focus_mode),
            (top_text, self.toggle_bubble_top),
            ("👁️ 切换显示", self.toggle_visibility_menu),
            ("🔄 弹出随机鼓励", self.trigger_random_message),
        ]

        # Add each menu item
        for text, callback in menu_items:
            btn = ctk.CTkButton(
                menu_frame,
                text=text,
                command=lambda cb=callback: self.execute_menu(cb),
                width=160,
                height=32,
                corner_radius=6,
                fg_color="#333333",
                hover_color="#444444"
            )
            btn.pack(pady=2, padx=5)

        # Close menu when clicking elsewhere
        def close_on_click_outside(event):
            # Check if click is inside menu
            x, y = event.x, event.y
            if 0 <= x <= self.context_menu.winfo_width() and 0 <= y <= self.context_menu.winfo_height():
                return
            self.close_context_menu()

        self.context_menu.bind('<Button-1>', close_on_click_outside)

    def close_context_menu(self):
        """Close the context menu"""
        if self.context_menu is not None:
            try:
                self.context_menu.destroy()
            except:
                pass
            self.context_menu = None

    def execute_menu(self, callback):
        """Execute menu callback then close menu"""
        callback()
        self.close_context_menu()

    def show_today_summary(self):
        """Show today's summary reminder"""
        now = datetime.now()
        summary = f"📅 今日提醒\n\n当前时间: {now.strftime('%H:%M')}\n"

        # Add scheduled reminders info
        summary += "\n• 00:00 提醒打开加班机"
        summary += "\n• 18:00 提醒开播"
        summary += "\n• 饭点提醒吃饭喝水"
        summary += "\n• 每两小时提醒休息"

        self.show_bubble(summary)

    def toggle_visibility_menu(self):
        """Toggle visibility from menu"""
        self.toggle_visibility(None)

    def trigger_random_message(self):
        """Trigger a random message now"""
        if self.reminder_shown:
            self.close_bubble()
        message = random.choice(RANDOM_MESSAGES)
        self.show_bubble(message)

    def open_custom_reminder_dialog(self):
        """Open dialog to add custom one-time reminder"""
        CustomReminderDialog(self.window, self.on_custom_reminder)

    def on_custom_reminder(self, minutes: int, message: str):
        """Schedule a custom reminder after N minutes"""
        self.root.after(minutes * 60 * 1000, lambda: self.show_bubble(message, True))


class CustomReminderDialog(ctk.CTkToplevel):
    """Dialog to create a custom one-time reminder"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("添加自定义提醒")
        self.geometry("350x250")
        self.resizable(False, False)
        self.grab_set()

        scrollable_frame = ctk.CTkScrollableFrame(self, width=330, height=210)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            scrollable_frame,
            text="多少分钟后提醒",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(15, 5))
        self.minutes_entry = ctk.CTkEntry(scrollable_frame, width=250, corner_radius=8)
        self.minutes_entry.insert(0, "30")
        self.minutes_entry.pack(pady=5)

        ctk.CTkLabel(
            scrollable_frame,
            text="提醒内容",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(15, 5))
        self.message_entry = ctk.CTkEntry(scrollable_frame, width=250, corner_radius=8)
        self.message_entry.insert(0, "该休息一下了哦")
        self.message_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self.confirm,
            width=80,
            corner_radius=8
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.destroy,
            width=80,
            corner_radius=8,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def confirm(self):
        """Confirm and schedule reminder"""
        try:
            minutes = int(self.minutes_entry.get())
            message = self.message_entry.get().strip()
            if minutes > 0 and message:
                self.callback(minutes, message)
                self.destroy()
        except ValueError:
            pass


# Add new toggle methods to DesktopReminderWindow
def toggle_focus_mode(self):
    """Toggle whether clicking the window steals focus from other programs"""
    self.click_steals_focus = not self.click_steals_focus
    # Apply the setting using Windows API
    try:
        import ctypes
        from ctypes import wintypes
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        hwnd = self.window.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
        if not self.click_steals_focus:
            # Add NOACTIVATE flag - don't steal focus
            style |= WS_EX_NOACTIVATE
        else:
            # Remove NOACTIVATE flag - allow stealing focus
            style &= ~WS_EX_NOACTIVATE
        ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
        # Also update for bubble if exists
        if self.bubble and hasattr(self.bubble, 'winfo_id'):
            bubble_hwnd = self.bubble.winfo_id()
            bubble_style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(bubble_hwnd), GWL_EXSTYLE)
            if not self.click_steals_focus:
                bubble_style |= WS_EX_NOACTIVATE
            else:
                bubble_style &= ~WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongW(wintypes.HWND(bubble_hwnd), GWL_EXSTYLE, bubble_style)
    except:
        # If not on Windows or API fails, just continue
        pass
    # Close menu after toggling
    self.close_context_menu()
    # Show status
    if self.click_steals_focus:
        self.show_bubble("当前模式：点击会抢焦点\n游戏焦点会被夺走")
    else:
        self.show_bubble("当前模式：点击不抢焦点✓\n焦点保持在游戏\n仍可以正常拖动")

DesktopReminderWindow.toggle_focus_mode = toggle_focus_mode

def toggle_bubble_top(self):
    """Toggle whether bubble is always on top of other windows"""
    self.bubble_always_top = not self.bubble_always_top
    # Close menu after toggling
    self.close_context_menu()
    # If bubble is open, recreate it to apply new setting
    if self.bubble is not None:
        current_message = self.bubble.winfo_children()[0].winfo_children()[0].cget("text") if self.bubble else None
        if current_message:
            self.show_bubble(current_message)
    # Show status
    if self.bubble_always_top:
        self.show_bubble("当前设置：气泡始终置顶✓")
    else:
        self.show_bubble("当前设置：气泡不强制置顶\n可能被其他窗口覆盖")

DesktopReminderWindow.toggle_bubble_top = toggle_bubble_top

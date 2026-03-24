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

        # Speech bubble drawn on main canvas (same window)
        self.bubble_visible = False
        self.bubble_message = ""
        self.bubble_has_button = False
        self.bubble_button_text = "知道了"
        self.context_menu: Optional[ctk.CTkToplevel] = None
        self.last_reminder_type: Optional[str] = None
        self.reminder_shown = False
        # Track which day we've already reminded for daily reminders
        from datetime import date
        self.last_reminded_date: Optional[date] = None
        self.daily_reminded_flags = {
            "00:00": False,
            "18:00": False,
            "meal": False,
        }

        # Draw circle now after all initialization
        self.draw_circle()

        # Bind mouse events for dragging
        self.canvas.bind('<Button-1>', self.on_start_drag)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<Double-1>', self.toggle_visibility)
        # Right click to show context menu
        self.canvas.bind('<Button-3>', self.show_context_menu)

        # Start timer check
        self.check_time()
        # Random small talk timer (every 15-30 minutes)
        self.schedule_random_talk()

    def draw_circle(self):
        """Draw the circular placeholder, and draw bubble if visible"""
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
        # Draw bubble if visible
        if self.bubble_visible:
            self._draw_bubble_on_canvas()

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

        # Bubble is on same canvas, so it automatically moves with the window
        # No need to reposition separately

    def toggle_visibility(self, event):
        """Toggle window visibility on double click"""
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.window.deiconify()
        else:
            self.window.withdraw()

    def show_bubble(self, message: str, has_button: bool = False, button_text: str = "知道了"):
        """Show speech bubble with message - drawn on main canvas above the circle"""
        # Close existing bubble
        self.close_bubble()

        # Store bubble state
        self.bubble_visible = True
        self.bubble_message = message
        self.bubble_has_button = has_button
        self.bubble_button_text = button_text
        self.reminder_shown = True

        # Redraw canvas to show bubble
        self.draw_circle()

        # Bind click to close when clicking anywhere
        self.canvas.bind('<Button-1>', self._on_canvas_click)

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, fill, outline):
        """Draw natural cloud-like shape with randomly sized bumps along all edges"""
        # Fill the main rectangle first
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")

        # Add random-sized bumps along each edge to create natural cloud shape
        import random
        bump_min = 6
        bump_max = 14

        # Top edge - add bumps upward
        width = x2 - x1
        steps = int(width / 25)  # One bump every ~25px
        for i in range(steps + 1):
            x_center = x1 + int(width * i / steps)
            bump_size = random.randint(bump_min, bump_max)
            canvas.create_oval(
                x_center - bump_size, y1 - bump_size,
                x_center + bump_size, y1 + bump_size,
                fill=fill, outline=""
            )

        # Bottom edge - add bumps downward
        for i in range(steps + 1):
            x_center = x1 + int(width * i / steps)
            bump_size = random.randint(bump_min, bump_max)
            canvas.create_oval(
                x_center - bump_size, y2 - bump_size,
                x_center + bump_size, y2 + bump_size,
                fill=fill, outline=""
            )

        # Left edge - add bumps leftward (skip corners already done)
        height = y2 - y1
        steps = int(height / 25)
        for i in range(1, steps):
            y_center = y1 + int(height * i / steps)
            bump_size = random.randint(bump_min, bump_max)
            canvas.create_oval(
                x1 - bump_size, y_center - bump_size,
                x1 + bump_size, y_center + bump_size,
                fill=fill, outline=""
            )

        # Right edge - add bumps rightward
        for i in range(1, steps):
            y_center = y1 + int(height * i / steps)
            bump_size = random.randint(bump_min, bump_max)
            canvas.create_oval(
                x2 - bump_size, y_center - bump_size,
                x2 + bump_size, y_center + bump_size,
                fill=fill, outline=""
            )

        # Add extra larger bumps at the four corners
        corner_bump = 18
        # Top-left
        canvas.create_oval(x1 - corner_bump, y1 - corner_bump,
                          x1 + corner_bump//2, y1 + corner_bump//2,
                          fill=fill, outline="")
        # Top-right
        canvas.create_oval(x2 - corner_bump//2, y1 - corner_bump,
                          x2 + corner_bump, y1 + corner_bump//2,
                          fill=fill, outline="")
        # Bottom-left
        canvas.create_oval(x1 - corner_bump, y2 - corner_bump//2,
                          x1 + corner_bump//2, y2 + corner_bump,
                          fill=fill, outline="")
        # Bottom-right
        canvas.create_oval(x2 - corner_bump//2, y2 - corner_bump//2,
                          x2 + corner_bump, y2 + corner_bump,
                          fill=fill, outline="")

        # Draw a light outline around the whole shape for definition
        # We just draw the main rectangle outline, the bumps extend beyond it
        canvas.create_rectangle(x1, y1, x2, y2, fill="", outline=outline, width=1)

    def _draw_bubble_on_canvas(self):
        """Draw bubble directly on main canvas, positioned above the circle"""
        # Bubble dimensions - fixed width, dynamic height based on content
        bubble_width = 280
        # Calculate dynamic height based on content
        import math
        message = self.bubble_message
        explicit_lines = message.count('\n') + 1
        avg_chars_per_line = (bubble_width - 40) // 10
        wrapped_lines = math.ceil(len(message) / avg_chars_per_line) if message else 1
        estimated_lines = max(explicit_lines, wrapped_lines)
        line_height = 22
        base_height = 20
        button_height = 40 if self.bubble_has_button else 0
        bubble_height = base_height + estimated_lines * line_height + button_height + 20
        bubble_height = max(bubble_height, 80)
        bubble_height = min(bubble_height, 300)

        # Position bubble centered above the circle
        # Circle is from (10,10) to (140,140) in canvas coordinates
        bubble_x = (150 - bubble_width) // 2  # canvas is 150x150
        bubble_y = -bubble_height  # above the canvas (canvas starts at 0,0)

        # Draw bubble shape on main canvas - natural cloud-like with random bumps
        canvas_x1 = bubble_x + 5
        canvas_y1 = bubble_y + 5
        canvas_x2 = bubble_x + bubble_width - 5
        canvas_y2 = bubble_y + bubble_height - 20  # leave space for tail
        self._draw_rounded_rect(self.canvas, canvas_x1, canvas_y1, canvas_x2, canvas_y2, "#3a3a3a", "#666666")

        # Draw tail pointing down to the circle
        tail_center_x = bubble_x + bubble_width // 2
        tail_base_y = bubble_y + bubble_height - 20
        tail_tip_y = bubble_y + bubble_height - 5
        tail_points = [
            tail_center_x - 12, tail_base_y,
            tail_center_x - 4, tail_base_y + 4,
            tail_center_x, tail_tip_y,
            tail_center_x + 4, tail_base_y + 4,
            tail_center_x + 12, tail_base_y,
        ]
        self.canvas.create_polygon(
            tail_points,
            fill="#3a3a3a",
            outline="#666666",
            width=1,
            tags="bubble"
        )

        # Draw text
        # Use canvas create_text because we can't have widgets on canvas - simpler
        # Center text horizontally
        current_y = bubble_y + 18
        lines = message.split('\n')
        for line in lines:
            self.canvas.create_text(
                bubble_x + bubble_width // 2,
                current_y,
                text=line,
                fill="#f0f0f0",
                font=("Microsoft YaHei", 14),
                justify="center",
                tags="bubble"
            )
            current_y += 22

        # Draw button rectangle if needed (we can't have CTkButton on canvas, just draw it)
        if self.bubble_has_button:
            btn_y = current_y + 8
            btn_h = 30
            btn_w = 80
            btn_x = bubble_x + (bubble_width - btn_w) // 2
            # Button background
            self.canvas.create_rectangle(
                btn_x, btn_y, btn_x + btn_w, btn_y + btn_h,
                fill="#555555",
                outline="#777777",
                radius=8,
                tags=("bubble", "bubble_button")
            )
            # Button text
            self.canvas.create_text(
                btn_x + btn_w // 2,
                btn_y + btn_h // 2,
                text=self.bubble_button_text,
                fill="#ffffff",
                font=("Microsoft YaHei", 12),
                tags="bubble"
            )

    def _on_canvas_click(self, event):
        """Handle click on canvas - close bubble if clicked, detect button click"""
        # If button exists and click is on button, close bubble
        if self.bubble_has_button:
            # Check if click is on the button area
            # Recalculate button position same as in _draw_bubble_on_canvas
            bubble_width = 280
            message = self.bubble_message
            import math
            explicit_lines = message.count('\n') + 1
            avg_chars_per_line = (bubble_width - 40) // 10
            wrapped_lines = math.ceil(len(message) / avg_chars_per_line) if message else 1
            estimated_lines = max(explicit_lines, wrapped_lines)
            line_height = 22
            base_height = 20
            button_height = 40 if self.bubble_has_button else 0
            bubble_height = base_height + estimated_lines * line_height + button_height + 20
            bubble_height = max(bubble_height, 80)
            bubble_height = min(bubble_height, 300)
            bubble_x = (150 - bubble_width) // 2
            bubble_y = -bubble_height

            btn_h = 30
            btn_w = 80
            current_y = bubble_y + 18 + estimated_lines * 22 + 8
            btn_y = current_y
            btn_x = bubble_x + (bubble_width - btn_w) // 2

            # Check if click is inside button
            if (btn_x <= event.x <= btn_x + btn_w and
                btn_y <= event.y <= btn_y + btn_h):
                # Clicked button, close
                self.close_bubble()
                return

        # Any click on bubble area closes it
        self.close_bubble()

    def close_bubble(self):
        """Close the speech bubble"""
        if self.bubble_visible:
            self.bubble_visible = False
            self.bubble_message = ""
            self.reminder_shown = False
            # Redraw to remove bubble
            self.draw_circle()
            # Restore original bindings
            self.canvas.bind('<Button-1>', self.on_start_drag)
            self.canvas.bind('<B1-Motion>', self.on_drag)

    def check_time(self):
        """Check current time and trigger scheduled reminders"""
        now = datetime.now()
        today = now.date()
        hour = now.hour
        minute = now.minute

        # Reset daily reminder flags when date changes
        if self.last_reminded_date != today:
            # New day, reset all daily reminder flags
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
            self.root.after(5 * 60 * 1000, lambda: self.check_second_reminder("00:00"))

        # 18:00 - remind start streaming
        elif hour == 18 and 0 <= minute < 8 and not self.daily_reminded_flags["18:00"]:
            message = "🎬 到开播时间啦\n记得开播打渔哦！"
            has_button = True
            triggered = True
            self.daily_reminded_flags["18:00"] = True
            # Schedule second reminder if not confirmed
            self.root.after(5 * 60 * 1000, lambda: self.check_second_reminder("18:00"))

        # Meal time reminders (breakfast 7:00-7:30, lunch 12:00-12:30, dinner 18:30-19:00)
        elif (hour == 12 and 0 <= minute < 30) or (hour == 18 and 30 <= minute < 60) or (hour == 7 and 0 <= minute < 30):
            if not self.daily_reminded_flags["meal"] or self.last_reminder_type != "meal":
                message = "🍚 到饭点了哦\n记得放下鱼竿去吃饭\n多喝水，多走动！"
                triggered = True
                self.last_reminder_type = "meal"
                # Don't set the flag immediately, allow multiple meal reminders in one day

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

        # Get click position for menu placement - screen coordinates
        click_x = self.window.winfo_x() + event.x
        click_y = self.window.winfo_y() + event.y

        # Create context menu window
        self.context_menu = ctk.CTkToplevel(self.window)
        self.context_menu.title("菜单")
        self.context_menu.overrideredirect(True)
        self.context_menu.attributes('-topmost', True)

        # Count menu items to calculate estimated height
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
        # Calculate height: each item ~36px + padding
        menu_height = len(menu_items) * 36 + 8
        menu_width = 180
        # Position menu so it opens to the side of the click, keep inside screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # Adjust if menu would go outside screen
        if click_x + menu_width > screen_width:
            click_x = screen_width - menu_width - 5
        if click_y + menu_height > screen_height:
            click_y = click_y - menu_height

        # Set explicit size (no auto - Tkinter doesn't handle auto correctly)
        self.context_menu.geometry(f"{menu_width}x{menu_height}+{click_x}+{click_y}")

        # Context menu needs to be clickable, don't set NOACTIVATE
        # Even if main window doesn't steal focus, menu must accept clicks
        # After clicking, menu closes anyway - focus doesn't stay on menu

        # Menu container
        menu_frame = ctk.CTkFrame(
            self.context_menu,
            fg_color="#252525",
            corner_radius=8
        )
        menu_frame.pack(fill="both", expand=True, padx=2, pady=2)

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
            # After click, check if we need to close
            # Schedule check after click processing
            self.context_menu.after(100, self._check_close_context)
        self.context_menu.bind('<Button-1>', close_on_click_outside)

    def close_context_menu(self):
        """Close the context menu"""
        if self.context_menu is not None:
            try:
                self.context_menu.destroy()
            except:
                pass
            self.context_menu = None

    def _check_close_context(self):
        """Check if click is outside context menu, close if yes"""
        # This is needed because with WS_EX_NOACTIVATE we can't get correct event coordinates
        # For our usage, any click anywhere should close the menu
        self.close_context_menu()

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
        # Bubble is now on same window, no need to update separately
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
    """Toggle whether bubble is always on top of other windows
    Now that bubble is on same canvas as main window, this setting doesn't matter anymore
    Main window is always topmost, so bubble is always top
    """
    self.bubble_always_top = not self.bubble_always_top
    # Close menu after toggling
    self.close_context_menu()
    # Bubble is on same window which is always topmost, so this setting has no effect now
    self.show_bubble("气泡与模型同窗口\n始终置顶，设置不生效")

DesktopReminderWindow.toggle_bubble_top = toggle_bubble_top

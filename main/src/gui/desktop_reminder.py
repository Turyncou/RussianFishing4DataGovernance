"""Desktop floating reminder with circular placeholder (will replace with Live2D later)"""
import customtkinter as ctk
from tkinter import Canvas
from CTkMessagebox import CTkMessagebox
from datetime import datetime
from typing import Optional
import random
import math
import ctypes
from ctypes import wintypes


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

    # Configurable dimensions - adjust these when replacing with a different size model
    MAIN_WINDOW_SIZE = 150          # Size of main model window (square)
    DEFAULT_SCREEN_MARGIN_X = 30    # Margin from right edge of screen
    DEFAULT_SCREEN_MARGIN_Y = 50    # Margin from bottom edge of screen
    BUBBLE_FIXED_WIDTH = 280        # Fixed width for speech bubble (content wraps at this width)
    BUBBLE_TAIL_HEIGHT = 15         # Height of the tail pointing to model
    BUBBLE_TIP_DISTANCE_FROM_MODEL = 8  # Distance between bubble tip and model circle
    BUBBLE_PADDING_TOP = 2          # Top padding for bubble frame
    BUBBLE_PADDING_BOTTOM = 2       # Bottom padding before tail

    def __init__(self, root):
        self.root = root
        self.is_visible = True
        self.click_steals_focus = False  # 是否点击抢焦点，False = 点击不抢焦点（保持游戏焦点）
        self.bubble_always_top = True  # 气泡是否始终置顶
        self._bubble_anim_phase = 0
        self._bubble_anim_running = False   


        # Create independent toplevel window
        # Position at bottom-right corner by default
        # Only MAIN_WINDOW_SIZE x MAIN_WINDOW_SIZE for the circle model, bubble goes in separate window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = screen_width - self.MAIN_WINDOW_SIZE - self.DEFAULT_SCREEN_MARGIN_X
        y = screen_height - self.MAIN_WINDOW_SIZE - self.DEFAULT_SCREEN_MARGIN_Y

        self.window = ctk.CTkToplevel(root)
        self.window.title("RF4 桌面提醒")
        self.window.geometry(f"{self.MAIN_WINDOW_SIZE}x{self.MAIN_WINDOW_SIZE}+{x}+{y}")
        self.window.overrideredirect(True)  # No title bar
        self.window.attributes('-topmost', True)  # Always on top

        # On Windows, use transparent color for the window background
        self.window.attributes('-transparentcolor', '#1a1a1a')

        # On Windows, set the window to not activate when clicked
        # This keeps focus on the original game while still allowing dragging
        # Also use TOOLWINDOW + remove APPWINDOW to prevent showing in taskbar/preview
        try:
            # Use extended window style to prevent activation
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_LAYERED = 0x00080000
            hwnd = self.window.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
            style |= WS_EX_NOACTIVATE
            style |= WS_EX_TOOLWINDOW  # Tool window - don't show in taskbar
            style &= ~WS_EX_APPWINDOW  # Remove app window flag - don't show in taskbar preview
            ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
        except:
            # If not on Windows or fails, just continue normally
            pass

        # Canvas just for the circle
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
        # Right click to show context menu
        self.canvas.bind('<Button-3>', self.show_context_menu)

        # Start timer check
        self.check_time()
        # Random small talk timer (every 15-30 minutes)
        self.schedule_random_talk()

    def draw_circle(self):
        """Draw the circular placeholder"""
        self.canvas.delete("all")
        # Draw gradient-like circle in the center
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
        # Guard against missing drag start coordinates
        if not hasattr(self, 'x_start') or not hasattr(self, 'y_start'):
            return
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

        # Update bubble position to follow main window
        self._update_bubble_position()

    def toggle_visibility(self, event):
        """Toggle window visibility on double click"""
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.window.deiconify()
        else:
            self.window.withdraw()
            # Also close bubble when main window is hidden
            self.close_bubble()

    def show_bubble(self, message: str, has_button: bool = False, button_text: str = "知道了"):
        """Show speech bubble with message - separate popup window with tail to circle"""
        # Close existing bubble
        self.close_bubble()

        # Store bubble state
        self.bubble_visible = True
        self.bubble_message = message
        self.bubble_has_button = has_button
        self.bubble_button_text = button_text
        self.reminder_shown = True

        # Create a separate toplevel window for the bubble
        self.bubble_window = ctk.CTkToplevel(self.window)
        self.bubble_window.title("提醒")
        self.bubble_window.overrideredirect(True)
        self.bubble_window.attributes('-topmost', self.bubble_always_top)
        self.bubble_window.config(bg='#1a1a1a')
        self.bubble_window.attributes('-transparentcolor', '#1a1a1a')
        # Hide initially to avoid flash in top-left corner before position is set
        self.bubble_window.withdraw()

        # Same NOACTIVATE style as main window to not steal focus
        # Also use TOOLWINDOW style + remove APPWINDOW to prevent showing in taskbar/preview
        try:
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            hwnd = self.bubble_window.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)
            style |= WS_EX_NOACTIVATE
            style |= WS_EX_TOOLWINDOW  # Tool window - don't show in taskbar
            style &= ~WS_EX_APPWINDOW  # Remove app window flag - don't show in taskbar preview
            ctypes.windll.user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
        except:
            pass

        # Create canvas to draw bubble with tail
        # We need extra space at bottom for the tail pointing to circle
        # Fixed width for better text wrapping, dynamic height based on content
        canvas = Canvas(
            self.bubble_window,
            bg='#1a1a1a',
            highlightthickness=0,
            bd=0
        )
        canvas.pack(fill="both", expand=True)

        # Allow clicking anywhere on bubble to close
        def handle_click(event):
            # Click anywhere on bubble (including frame/background) closes it
            self.close_bubble()

        # Content frame
        frame = ctk.CTkFrame(
            canvas,
            fg_color="#3a3a3a",
            corner_radius=10,
            width=self.BUBBLE_FIXED_WIDTH
        )
        frame.pack(padx=2, pady=(self.BUBBLE_PADDING_TOP, 0))  # bottom padding is handled in window total height
        # Bind click on frame to close too
        frame.bind('<Button-1>', handle_click)

        # Message label - word wrap based on fixed width
        label = ctk.CTkLabel(
            frame,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color="#f0f0f0",
            wraplength=self.BUBBLE_FIXED_WIDTH - 40
        )
        label.pack(padx=15, pady=(15, 10 if has_button else 15))
        label.bind('<Button-1>', handle_click)

        # Button if needed
        if has_button:
            btn = ctk.CTkButton(
                frame,
                text=button_text,
                command=self.close_bubble,
                width=80,
                height=30,
                fg_color="#555555",
                hover_color="#777777"
            )
            btn.pack(pady=(0, 10))

        # Calculate bubble window size based on content
        self.bubble_window.update_idletasks()
        frame_w = frame.winfo_reqwidth()
        frame_h = frame.winfo_reqheight()
        # Extra padding at bottom to ensure full tail is visible
        # Add +2 extra pixels to make sure tip is not cut off
        total_height = self.BUBBLE_PADDING_TOP + frame_h + self.BUBBLE_TAIL_HEIGHT + self.BUBBLE_PADDING_BOTTOM + 2
        total_width = frame_w + 4  # padding left/right
        self.bubble_window.geometry(f"{total_width}x{total_height}")

        # Draw the tail on the canvas - the tail goes below the frame toward the circle
        # Tail points from bottom center of bubble toward the main circle
        tail_center_x = (frame_w // 2) + 2  # centered
        # Tail starts at the bottom of the frame, extends down
        frame_bottom_y = self.BUBBLE_PADDING_TOP + frame_h + self.BUBBLE_PADDING_BOTTOM
        # Coordinates for the tail polygon - points down toward circle
        # tail covers from frame_bottom_y to frame_bottom_y + BUBBLE_TAIL_HEIGHT
        # Leave 1px at bottom to ensure tip is not cut off
        points = [
            tail_center_x - 10, frame_bottom_y,                     # left top (connected to frame)
            tail_center_x - 3, frame_bottom_y + (self.BUBBLE_TAIL_HEIGHT - 3), # left bottom (tip area)
            tail_center_x + 3, frame_bottom_y + (self.BUBBLE_TAIL_HEIGHT - 3), # right bottom (tip area)
            tail_center_x + 10, frame_bottom_y,                     # right top (connected to frame)
        ]
        # Fill with same color as frame to blend naturally - no outline
        canvas.create_polygon(points, fill="#3a3a3a", outline="#3a3a3a", tags="bubble")

        # Bind click to close on all elements
        canvas.bind('<Button-1>', handle_click)

        # Content frame placement
        frame.pack(padx=2, pady=(self.BUBBLE_PADDING_TOP, 0))  # bottom padding is handled in window total height

        # Wait for window to complete layout then update position correctly
        # This ensures we get the correct bubble height before calculating position
        # Only show after position is set to avoid flash in top-left corner
        def update_position():
            self.bubble_window.update_idletasks()
            self._update_bubble_position()
            # Now that position is correct, show the bubble
            self.bubble_window.deiconify()

        self.bubble_window.after(20, update_position)
        self._start_bubble_animation()

    def _start_bubble_animation(self):
        """Start floating animation"""
        self._bubble_anim_running = True
        self._bubble_anim_phase = 0
        self._animate_bubble()

    def _animate_bubble(self):
        if not self._bubble_anim_running:
            return

        if not hasattr(self, 'bubble_window') or self.bubble_window is None:
            return

        # 基础位置（真实位置）
        main_x = self.window.winfo_x()
        main_y = self.window.winfo_y()
        main_w = self.window.winfo_width()
        main_h = self.window.winfo_height()

        bubble_h = self.bubble_window.winfo_reqheight()
        bubble_w = self.bubble_window.winfo_reqwidth()

        # ===== 原始位置计算（你的逻辑）=====
        circle_center_y = main_y + main_h // 2
        circle_top_y = circle_center_y - (main_h // 2)
        base_y = circle_top_y - self.BUBBLE_TIP_DISTANCE_FROM_MODEL - bubble_h

        base_x = main_x + (main_w - bubble_w) // 2

        # ===== 浮动动画 =====
        amplitude = 6   # 浮动幅度（像素）
        speed = 0.15    # 速度（越小越慢）

        offset = math.sin(self._bubble_anim_phase) * amplitude
        self._bubble_anim_phase += speed

        final_y = int(base_y + offset)
        final_x = int(base_x)

        # 限制屏幕边界
        screen_width = self.root.winfo_screenwidth()
        if final_x < 0:
            final_x = 0
        if final_x + bubble_w > screen_width:
            final_x = screen_width - bubble_w

        if final_y < 0:
            final_y = 0

        self.bubble_window.geometry(f"+{final_x}+{final_y}")

        # 下一帧（约60FPS）
        self.root.after(16, self._animate_bubble)

    def _on_canvas_click(self, event):
        """Handle click on canvas - close bubble if clicked, detect button click
        If click is not on bubble/button, pass through to drag handler
        """
        # Still allow dragging when bubble is visible - check if click is outside bubble
        bubble_width = 280
        message = self.bubble_message
        explicit_lines = message.count('\n') + 1
        avg_chars_per_line = (bubble_width - 40) // 10
        wrapped_lines = math.ceil(len(message) / avg_chars_per_line) if message else 1
        estimated_lines = max(explicit_lines, wrapped_lines)
        line_height = 22
        base_height = 20
        button_height = 45 if self.bubble_has_button else 0
        bubble_height = base_height + estimated_lines * line_height + button_height + 20
        bubble_height = max(bubble_height, 80)
        bubble_height = min(bubble_height, 300)
        bubble_x = (150 - bubble_width) // 2
        # Circle is at 300px offset down, bubble sits just above it
        circle_offset_y = 300
        bubble_y = max(0, circle_offset_y - bubble_height - 10)  # just above circle, never < 0

        # Check if click is on bubble/button
        clicked_on_bubble = (bubble_x <= event.x <= bubble_x + bubble_width and
                          bubble_y <= event.y <= bubble_y + bubble_height)

        if clicked_on_bubble and self.bubble_has_button:
            # Check if click is specifically on the button
            btn_h = 30
            btn_w = 80
            current_y = bubble_y + 22 + estimated_lines * 22 + 8
            btn_y = current_y
            btn_x = bubble_x + (bubble_width - btn_w) // 2
            if (btn_x <= event.x <= btn_x + btn_w and
                btn_y <= event.y <= btn_y + btn_h):
                # Clicked button, close
                self.close_bubble()
                return

        if clicked_on_bubble:
            # Any click on bubble area closes it
            self.close_bubble()
            return

        # Click not on bubble - this is a drag attempt
        # Pass through to drag handler
        self.on_start_drag(event)

    def close_bubble(self):
        """Close the speech bubble"""
        if self.bubble_visible:
            self.bubble_visible = False
            self.bubble_message = ""
            self.reminder_shown = False
            # Close bubble window
            if hasattr(self, 'bubble_window') and self.bubble_window is not None:
                try:
                    self.bubble_window.destroy()
                except:
                    pass
                self.bubble_window = None
        self._bubble_anim_running = False

    def _update_bubble_position(self):
        """Update bubble position to follow main window when dragging
        Always keeps the tail tip at fixed distance from the model circle,
        regardless of how much content is in the bubble.

        Bubble appears ABOVE the model, tail points down towards model top.
        """
        if not self.bubble_visible or not hasattr(self, 'bubble_window') or self.bubble_window is None:
            return
        # Main window is the circle
        main_x = self.window.winfo_x()
        main_y = self.window.winfo_y()
        main_w = self.window.winfo_width()
        main_h = self.window.winfo_height()
        bubble_h = self.bubble_window.winfo_reqheight()
        bubble_w = self.bubble_window.winfo_reqwidth()


        # Fixed distance from circle center to bubble tail tip
        # Tail is at bottom of bubble, so bubble needs to positioned such that
        # the bottom edge of bubble (where tail tip is) is fixed distance above circle
        circle_center_y = main_y + main_h // 2  # center of the main circle
        circle_top_y = circle_center_y - (main_h // 2)  # Y coordinate of circle top
        bubble_tip_y = circle_top_y - self.BUBBLE_TIP_DISTANCE_FROM_MODEL  # bubble tip should be here
        # Bubble window bottom = bubble tip position (because tip is at bottom of window)
        # So: bubble_y + bubble_h = bubble_tip_y → bubble_y = bubble_tip_y - bubble_h
        bubble_y = bubble_tip_y - bubble_h

        # Center bubble horizontally over main window
        bubble_x = main_x + (main_w - bubble_w) // 2

        # Ensure bubble stays within screen bounds
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if bubble_x < 0:
            bubble_x = 0
        if bubble_x + bubble_w > screen_width:
            bubble_x = screen_width - bubble_w
        if bubble_y < 0:
            bubble_y = 0
        self.bubble_window.geometry(f"+{int(bubble_x)}+{int(bubble_y)}")

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
            self.close_context_menu()

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
            ("✖️ 关闭菜单", lambda: None),  # Just close menu
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

        # Intercept ALL mouse down events on the menu to prevent propagation to root
        # This is needed because:
        # 1. If we don't intercept, click goes through to root and closes menu immediately
        # 2. Button click never gets a chance to fire
        def intercept_all(event):
            # Absorb the event, don't let it go to root
            return "break"
        # Bind to all mouse buttons on menu window and container
        self.context_menu.bind('<Button-1>', intercept_all)
        self.context_menu.bind('<Button-3>', intercept_all)
        menu_frame.bind('<Button-1>', intercept_all)
        menu_frame.bind('<Button-3>', intercept_all)

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

        # Click anywhere on the root main window (outside menu) will close the menu
        # Store the binding ID so we can remove it when menu closes
        self._root_click_binding = self.root.bind('<Button-1>', lambda e: self._check_close_context(), add="+")

    def close_context_menu(self):
        """Close the context menu"""
        if self.context_menu is not None:
            # Delay destroy to let all events complete first
            # This prevents "bad window path name" errors when menu items open new dialogs
            try:
                menu = self.context_menu
                self.context_menu = None
                self.root.after(10, lambda: self._safe_destroy_menu(menu))
            except:
                pass

    def _safe_destroy_menu(self, menu):
        """Safely destroy context menu window"""
        try:
            menu.destroy()
        except:
            pass

    def _check_close_context(self):
        """Check if click is outside context menu, close if yes
        For our usage, any click anywhere outside the menu should close it
        """
        if self.context_menu is None:
            return
        self.close_context_menu()


    def execute_menu(self, callback):
        """Execute menu callback then close menu
        Close menu first, then execute callback to avoid focus issues with new dialogs
        """
        # Keep reference before closing
        menu_was_open = self.context_menu is not None
        # Close menu first so any new dialog opened by callback doesn't get focus errors
        if menu_was_open:
            self.close_context_menu()
        # Execute callback after a short delay to guarantee menu is fully destroyed
        self.window.after(20, callback)

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
            command=self.cancel,
            width=80,
            corner_radius=8,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def cancel(self):
        """Cancel and close dialog"""
        self.grab_release()
        # Delay destroy to let all pending events complete first
        self.after(10, self.destroy)

    def confirm(self):
        """Confirm and schedule reminder"""
        try:
            minutes = int(self.minutes_entry.get().strip())
            message = self.message_entry.get().strip()
            if minutes > 0 and message:
                self.callback(minutes, message)
                self.grab_release()
                # Delay destroy to let all pending events complete first
                # This prevents "bad window path name" error
                self.after(10, self.destroy)
            else:
                if minutes <= 0:
                    CTkMessagebox(title="输入错误", message="提醒分钟数必须大于0", icon="warning", option_1="确定")
                else:
                    CTkMessagebox(title="输入错误", message="提醒内容不能为空", icon="warning", option_1="确定")
        except ValueError:
            CTkMessagebox(title="输入错误", message="请输入有效的分钟数", icon="warning", option_1="确定")


# Add new toggle methods to DesktopReminderWindow
def toggle_focus_mode(self):
    """Toggle whether clicking the window steals focus from other programs"""
    self.click_steals_focus = not self.click_steals_focus
    # Apply the setting using Windows API
    try:
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
    """Toggle whether bubble is always on top of other windows"""
    self.bubble_always_top = not self.bubble_always_top
    # Close menu after toggling
    self.close_context_menu()
    # Apply the setting to current bubble if visible
    if hasattr(self, 'bubble_window') and self.bubble_window is not None:
        self.bubble_window.attributes('-topmost', self.bubble_always_top)
    # Show status
    if self.bubble_always_top:
        self.show_bubble("当前：气泡始终置顶✓")
    else:
        self.show_bubble("当前：气泡不强制置顶\n可能被其他窗口覆盖")

DesktopReminderWindow.toggle_bubble_top = toggle_bubble_top

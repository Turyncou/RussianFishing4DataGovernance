"""Main application window"""
import sys
import os
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import Canvas, messagebox
import webbrowser

from data.persistence import (
    LotteryPersistence, ActivityPersistence, StoragePersistence,
    FriendLinkPersistence, BackgroundPersistence
)
from core.models import FriendLink, BackgroundConfig
from .cat_follower import CatFollower
from .lottery_frame import LotteryFrame
from .activity_frame import ActivityFrame
from .storage_frame import StorageFrame
from .background_dialog import BackgroundDialog
from .friend_links_dialog import FriendLinksDialog


class MainWindow:
    """Main application window"""

    def __init__(self, app: ctk.CTk, data_dir: str):
        self.app = app
        self.data_dir = data_dir
        self.background_image = None
        self.background_photo = None
        self.background_config = None
        self.current_frame = None

        # Initialize persistence
        self.lottery_persistence = LotteryPersistence(os.path.join(data_dir, 'lottery.json'))
        self.activity_persistence = ActivityPersistence(os.path.join(data_dir, 'activity.json'))
        self.storage_persistence = StoragePersistence(os.path.join(data_dir, 'storage.json'))
        self.friend_link_persistence = FriendLinkPersistence(os.path.join(data_dir, 'friend_links.json'))
        self.background_persistence = BackgroundPersistence(os.path.join(data_dir, 'background.json'))

        # Setup window
        self.app.title("RF4 Data Process")
        self.app.geometry("1200x800")
        self.app.minsize(1000, 700)

        # Create main container with background canvas
        self.create_background_canvas()

        # Create main content frame on top of background
        self.create_main_content()

        # Load saved data
        self.load_background()

        # Show home page by default
        self.show_home_page()

        # Update background again after window is fully rendered
        self.app.after(200, self.update_background)

    def create_background_canvas(self):
        """Create the background canvas with cat followers"""
        self.bg_canvas = Canvas(
            self.app,
            highlightthickness=0,
            bg='#1a1a1a'
        )
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Create cat followers
        self.cat_follower = CatFollower(self.bg_canvas, 3)

        # Bind mouse movement for cat followers
        self.bg_canvas.bind('<Motion>', self.on_mouse_move)
        self.bg_canvas.bind('<Configure>', self.on_canvas_resize)

        # After canvas is created, create cats
        self.app.after(100, self.cat_follower.create_cats)

    def create_main_content(self):
        """Create the main content container"""
        self.main_container = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
            corner_radius=0
        )
        self.main_container.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Top navigation bar with title and buttons
        self.nav_bar = ctk.CTkFrame(self.main_container, fg_color="#252525", corner_radius=12, height=60)
        self.nav_bar.pack(fill="x", padx=15, pady=(15, 8))

        # Back button (only visible when not on home page)
        self.back_button = ctk.CTkButton(
            self.nav_bar,
            text="返回主页",
            command=self.show_home_page,
            width=80,
            fg_color="#555555",
            hover_color="#333333"
        )

        self.title_label = ctk.CTkLabel(
            self.nav_bar,
            text="RF4 数据统计",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(side="left", padx=20, pady=15)

        # Content area - scrollable for any content size
        self.content_container = ctk.CTkScrollableFrame(self.main_container, corner_radius=8, fg_color="#1e1e1e")
        self.content_container.pack(fill="both", expand=True, padx=15, pady=8)

        # Bottom buttons bar (background and friend links)
        self.bottom_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.bottom_bar.pack(fill="x", padx=15, pady=(8, 15))

        # Background button (left)
        self.bg_button = ctk.CTkButton(
            self.bottom_bar,
            text="更换背景",
            command=self.open_background_dialog,
            width=100,
            corner_radius=8
        )
        self.bg_button.pack(side="left", padx=5)

        # Friend links button (right)
        self.friend_button = ctk.CTkButton(
            self.bottom_bar,
            text="友情链接",
            command=self.open_friend_links,
            width=100,
            corner_radius=8
        )
        self.friend_button.pack(side="right", padx=5)

    def show_home_page(self):
        """Show home page with big navigation buttons"""
        # Clear current content
        self.clear_current_content()

        # Hide back button on home page
        if self.back_button.winfo_ismapped():
            self.back_button.pack_forget()

        # Home page container
        home_frame = ctk.CTkFrame(self.content_container, fg_color="#252525", corner_radius=16)
        home_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Welcome label
        welcome_label = ctk.CTkLabel(
            home_frame,
            text="欢迎使用 RF4 数据统计工具",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        welcome_label.pack(pady=(80, 50))

        # Button container
        btn_container = ctk.CTkFrame(home_frame, fg_color="transparent")
        btn_container.pack(fill="x", padx=200, pady=30)

        # Big buttons for each function
        btn_size = 240
        btn_height = 90
        btn_font = ctk.CTkFont(size=20, weight="bold")

        activity_btn = ctk.CTkButton(
            btn_container,
            text="📊 活动统计",
            command=self.show_activity_stats,
            width=btn_size,
            height=btn_height,
            font=btn_font,
            corner_radius=12,
            fg_color="#2c5aa0",
            hover_color="#1a3d66"
        )
        activity_btn.pack(pady=12)

        storage_btn = ctk.CTkButton(
            btn_container,
            text="📦 存储时长",
            command=self.show_storage,
            width=btn_size,
            height=btn_height,
            font=btn_font,
            corner_radius=12,
            fg_color="#2c5aa0",
            hover_color="#1a3d66"
        )
        storage_btn.pack(pady=12)

        lottery_btn = ctk.CTkButton(
            btn_container,
            text="🎡 转盘抽奖",
            command=self.show_lottery,
            width=btn_size,
            height=btn_height,
            font=btn_font,
            corner_radius=12,
            fg_color="#2c5aa0",
            hover_color="#1a3d66"
        )
        lottery_btn.pack(pady=12)

        self.current_frame = home_frame

    def clear_current_content(self):
        """Clear the current content frame"""
        if self.current_frame is not None:
            self.current_frame.destroy()
            self.current_frame = None

    def show_activity_stats(self):
        """Show activity statistics page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        self.activity_frame = ActivityFrame(
            frame,
            self.activity_persistence
        )
        self.activity_frame.pack(fill="both", expand=True)

        self.current_frame = frame

    def show_storage(self):
        """Show storage duration page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        self.storage_frame = StorageFrame(
            frame,
            self.storage_persistence
        )
        self.storage_frame.pack(fill="both", expand=True)

        self.current_frame = frame

    def show_lottery(self):
        """Show lottery wheel page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        self.lottery_frame = LotteryFrame(
            frame,
            self.lottery_persistence
        )
        self.lottery_frame.pack(fill="both", expand=True)

        self.current_frame = frame

    def load_background(self):
        """Load background configuration from file"""
        self.background_config = self.background_persistence.load_config()

        # Check default background
        # Get correct path whether running as source or packaged exe
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Running as source code
            # __file__ = src/gui/main_window.py → go up 3 levels: src/gui/ → main/
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        default_bg = os.path.join(base_path, '微信图片_20250817002102.jpg')

        if self.background_config.image_path is None and os.path.exists(default_bg):
            self.background_config.image_path = default_bg

        self.update_background()

    def update_background(self):
        """Update the background image on canvas"""
        if self.background_config and self.background_config.image_path:
            if os.path.exists(self.background_config.image_path):
                try:
                    # Open and resize image to fit canvas
                    image = Image.open(self.background_config.image_path)
                    canvas_width = self.bg_canvas.winfo_width()
                    canvas_height = self.bg_canvas.winfo_height()
                    # If canvas not yet sized (during startup), use current window size
                    if canvas_width <= 1:
                        canvas_width = self.app.winfo_width()
                    if canvas_height <= 1:
                        canvas_height = self.app.winfo_height()
                    if canvas_width > 1 and canvas_height > 1:
                        image = image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                        # Apply opacity
                        if image.mode != 'RGBA':
                            image = image.convert('RGBA')
                        # Create alpha channel with the desired opacity (efficient method)
                        alpha = int(self.background_config.opacity * 255)
                        alpha_channel = Image.new('L', image.size, alpha)
                        image.putalpha(alpha_channel)
                        # We need to keep a reference
                        self.background_image = image
                        self.background_photo = ImageTk.PhotoImage(image)
                        self.bg_canvas.delete("background")
                        self.bg_canvas.create_image(
                            0, 0,
                            image=self.background_photo,
                            anchor="nw",
                            tags=("background",)
                        )
                        # Set opacity by changing canvas alpha - need to redraw cats on top
                        self.bg_canvas.tag_lower("background")
                except Exception as e:
                    messagebox.showerror("错误", f"加载背景图片失败: {str(e)}")

    def on_mouse_move(self, event):
        """Handle mouse movement to update cat positions"""
        self.cat_follower.update_position(event.x, event.y)

    def on_canvas_resize(self, event):
        """Handle canvas resize"""
        self.cat_follower.on_resize(event)
        self.update_background()

    def open_background_dialog(self):
        """Open dialog to change background image"""
        dialog = BackgroundDialog(
            self.app,
            self.background_config,
            self.on_background_changed,
            self.data_dir
        )

    def on_background_changed(self, new_config: BackgroundConfig):
        """Callback when background config is changed"""
        self.background_config = new_config
        self.background_persistence.save_config(new_config)
        self.update_background()

    def open_friend_links(self):
        """Open friend links dialog"""
        links = self.friend_link_persistence.load_links()
        dialog = FriendLinksDialog(
            self.app,
            links,
            self.on_friend_links_changed
        )

    def on_friend_links_changed(self, new_links: list[FriendLink]):
        """Callback when friend links are changed"""
        self.friend_link_persistence.save_links(new_links)

    def on_closing(self):
        """Handle window closing - save all data"""
        # Save all dirty data if they've been created
        if hasattr(self, 'activity_frame'):
            self.activity_frame.save_data()
        if hasattr(self, 'storage_frame'):
            self.storage_frame.save_data()
        self.app.destroy()

"""Main application window"""
import sys
import os
import shutil
import threading
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import Canvas, messagebox
import webbrowser

from data.persistence import (
    LotteryPersistence, ActivityPersistence, StoragePersistence, BaitPersistence,
    FriendLinkPersistence, BackgroundPersistence, CredentialsPersistence,
    create_auto_backup, list_backups
)
from core.models import FriendLink, BackgroundConfig
from .cat_follower import CatFollower
from .lottery_frame import LotteryFrame
from .activity_frame import ActivityFrame
from .storage_frame import StorageFrame
from .credentials_frame import CredentialsFrame
from .bait_frame import BaitFrame
from .backup_dialog import BackupRestoreDialog
from .background_dialog import BackgroundDialog
from .friend_links_dialog import FriendLinksDialog


class MainWindow:
    """Main application window"""

    def __init__(self, app: ctk.CTk, data_dir: str):
        self.app = app
        self.data_dir = data_dir
        self.background_image = None
        self.background_photo = None
        self.background_original_image = None  # Cache original raw image
        self.background_original_alpha = None  # Cache original with opacity applied
        self.last_cached_size = (0, 0)  # Last size we rendered for
        self.background_config = None
        self.current_frame = None
        self._resize_after_id = None  # For debouncing resize

        # All persistence instances will be initialized in background
        self.lottery_persistence = None
        self.activity_persistence = None
        self.storage_persistence = None
        self.bait_persistence = None
        self.friend_link_persistence = None
        self.background_persistence = None
        self.credentials_persistence = None

        # Setup window
        self.app.title("RF4 Data Process")
        self.app.geometry("1200x800")
        self.app.minsize(1000, 700)

        # Create loading screen first
        self._create_loading_screen()

        # Start background loading
        self._start_background_loading()

    def _create_loading_screen(self):
        """Create fullscreen loading screen shown during startup"""
        # Create loading frame that covers entire window
        self.loading_frame = ctk.CTkFrame(
            self.app,
            fg_color="#1a1a1a",
            corner_radius=0
        )
        self.loading_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Center container
        container = ctk.CTkFrame(self.loading_frame, fg_color="transparent")
        container.place(relx=0.5, rely=0.4, anchor="center")

        # Title
        title = ctk.CTkLabel(
            container,
            text="RF4 数据统计工具",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(0, 30))

        # Create spinning canvas
        self.loading_canvas = ctk.CTkCanvas(
            container,
            width=60,
            height=60,
            bg="#1a1a1a",
            highlightthickness=0
        )
        self.loading_canvas.pack(pady=(0, 20))

        # Loading message
        self.loading_label = ctk.CTkLabel(
            container,
            text="正在加载数据...",
            font=ctk.CTkFont(size=16)
        )
        self.loading_label.pack()

        # Animation state
        self.loading_angle = 0
        self.loading_animation_id = None
        self._animate_loading()

    def _animate_loading(self):
        """Animate the spinning loading indicator"""
        if not hasattr(self, 'loading_canvas') or not self.loading_canvas.winfo_exists():
            return
        self.loading_canvas.delete("spinner")
        x0, y0, x1, y1 = 5, 5, 55, 55
        self.loading_canvas.create_arc(
            x0, y0, x1, y1,
            start=self.loading_angle,
            extent=120,
            outline="#1f6feb",
            width=4,
            style="arc",
            tags="spinner"
        )
        self.loading_angle = (self.loading_angle + 10) % 360
        self.loading_animation_id = self.app.after(30, self._animate_loading)

    def _start_background_loading(self):
        """Start loading all data in background thread"""
        def background_task():
            # Initialize all persistence instances (this loads data from disk)
            self.lottery_persistence = LotteryPersistence(os.path.join(self.data_dir, 'lottery.json'))
            self.activity_persistence = ActivityPersistence(os.path.join(self.data_dir, 'activity.json'))
            self.storage_persistence = StoragePersistence(os.path.join(self.data_dir, 'storage.json'))
            self.bait_persistence = BaitPersistence(os.path.join(self.data_dir, 'bait.json'))
            self.friend_link_persistence = FriendLinkPersistence(os.path.join(self.data_dir, 'friend_links.json'))
            self.background_persistence = BackgroundPersistence(os.path.join(self.data_dir, 'background.json'))
            self.credentials_persistence = CredentialsPersistence(os.path.join(self.data_dir, 'credentials.json'))

            # Create automatic backup on startup
            self.backup_dir = os.path.join(self.data_dir, 'backups')
            os.makedirs(self.backup_dir, exist_ok=True)
            # Keep last 10 backups automatically
            backups = list_backups(self.backup_dir)
            if len(backups) >= 10:
                # Remove oldest backups beyond 10
                for old_backup in backups[10:]:
                    old_path = os.path.join(self.backup_dir, old_backup)
                    shutil.rmtree(old_path, ignore_errors=True)
            # Create new backup
            create_auto_backup(self.data_dir, self.backup_dir)

            # Load background config
            self.loading_label.after(0, lambda: self.loading_label.configure(text="正在加载背景..."))
            self.background_config = self.background_persistence.load_config()

            # All loading done - switch to main UI on main thread
            self.app.after(0, self._finish_loading)

        # Start background thread
        thread = threading.Thread(target=background_task, daemon=True)
        thread.start()

    def _finish_loading(self):
        """Called after background loading completes - switch to main UI"""
        # Stop loading animation
        if self.loading_animation_id:
            self.app.after_cancel(self.loading_animation_id)

        # Remove loading screen
        self.loading_frame.destroy()

        # Create main UI
        self.create_background_canvas()
        self.create_main_content()
        self.load_background()
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

        # Backup/Restore button (middle-left)
        self.backup_button = ctk.CTkButton(
            self.bottom_bar,
            text="💾 备份恢复",
            command=self.open_backup_dialog,
            width=100,
            corner_radius=8
        )
        self.backup_button.pack(side="left", padx=5)

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
        btn_height = 80
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
        activity_btn.pack(pady=10)

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
        storage_btn.pack(pady=10)

        bait_btn = ctk.CTkButton(
            btn_container,
            text="🎣 饵料库存",
            command=self.show_bait,
            width=btn_size,
            height=btn_height,
            font=btn_font,
            corner_radius=12,
            fg_color="#2c5aa0",
            hover_color="#1a3d66"
        )
        bait_btn.pack(pady=10)

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
        lottery_btn.pack(pady=10)

        credentials_btn = ctk.CTkButton(
            btn_container,
            text="🔐 账号管理",
            command=self.show_credentials,
            width=btn_size,
            height=btn_height,
            font=btn_font,
            corner_radius=12,
            fg_color="#2c5aa0",
            hover_color="#1a3d66"
        )
        credentials_btn.pack(pady=10)

        self.current_frame = home_frame
        # Update scrollable region after adding content
        self.content_container.update()

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
        # Update scrollable region after adding content
        self.content_container.update()

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
        # Update scrollable region after adding content
        self.content_container.update()

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
        # Update scrollable region after adding content
        self.content_container.update()

    def show_credentials(self):
        """Show account credentials manager page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        self.credentials_frame = CredentialsFrame(
            frame,
            self.credentials_persistence
        )
        self.credentials_frame.pack(fill="both", expand=True)

        self.current_frame = frame
        # Update scrollable region after adding content
        self.content_container.update()

    def show_bait(self):
        """Show bait/tackle consumption tracking page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        self.bait_frame = BaitFrame(
            frame,
            self.bait_persistence
        )
        self.bait_frame.pack(fill="both", expand=True)

        self.current_frame = frame
        # Update scrollable region after adding content
        self.content_container.update()

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
        """Update the background image on canvas - TURNED OFF for performance"""
        # Temporarily disabled - no background image to avoid resize redraws
        # If you want to re-enable, comment out the return below
        return

        if self.background_config and self.background_config.image_path:
            if os.path.exists(self.background_config.image_path):
                try:
                    canvas_width = self.bg_canvas.winfo_width()
                    canvas_height = self.bg_canvas.winfo_height()
                    # If canvas not yet sized (during startup), use current window size
                    if canvas_width <= 1:
                        canvas_width = self.app.winfo_width()
                    if canvas_height <= 1:
                        canvas_height = self.app.winfo_height()
                    # If still not sized, schedule a retry - don't give up permanently
                    if canvas_width <= 1 or canvas_height <= 1:
                        self.app.after(100, self.update_background)
                        return

                    # Check if we need to rebuild the alpha cached original
                    # Rebuild if:
                    # 1. No cache doesn't exist
                    # 2. Image path changed
                    # 3. Opacity changed
                    needs_rebuild_alpha = (
                        self.background_original_alpha is None or
                        getattr(self, '_last_bg_path', None) != self.background_config.image_path or
                        getattr(self, '_last_opacity', None) != self.background_config.opacity
                    )

                    if needs_rebuild_alpha:
                        self._last_bg_path = self.background_config.image_path
                        self._last_opacity = self.background_config.opacity
                        # Load original image
                        self.background_original_image = Image.open(self.background_config.image_path)
                        # Pre-process with opacity once
                        original = self.background_original_image
                        if original.mode != 'RGBA':
                            original = original.convert('RGBA')
                        # Apply opacity to the original image
                        alpha = int(self.background_config.opacity * 255)
                        alpha_channel = Image.new('L', original.size, alpha)
                        original.putalpha(alpha_channel)
                        self.background_original_alpha = original
                        # Force resize cache is invalid now
                        self.last_cached_size = (0, 0)

                    # Only re-resize if size changed significantly (> 20px)
                    # This avoids re-rendering for tiny resize adjustments
                    last_w, last_h = self.last_cached_size
                    size_changed_enough = (
                        abs(canvas_width - last_w) > 20 or
                        abs(canvas_height - last_h) > 20
                    )

                    if size_changed_enough or self.background_photo is None:
                        # Resize from pre-processed original with alpha
                        image = self.background_original_alpha.resize(
                            (canvas_width, canvas_height),
                            Image.Resampling.LANCZOS
                        )
                        # We need to keep a reference
                        self.background_image = image
                        self.background_photo = ImageTk.PhotoImage(image)
                        self.last_cached_size = (canvas_width, canvas_height)

                    # Update canvas
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
        """Handle canvas resize with debouncing for performance"""
        self.cat_follower.on_resize(event)
        # Debounce: only update background after resize stops for 200ms
        if self._resize_after_id is not None:
            self.app.after_cancel(self._resize_after_id)
        self._resize_after_id = self.app.after(200, self.update_background)

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
        # Invalidate all caches when background changes
        self.background_original_image = None
        self.background_original_alpha = None
        self.last_cached_size = (0, 0)
        self._last_bg_path = None
        self._last_opacity = None
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

    def open_backup_dialog(self):
        """Open backup and restore dialog"""
        BackupRestoreDialog(
            self.app,
            self.data_dir,
            self.backup_dir
        )

    def on_closing(self):
        """Handle window closing - save all data"""
        # Save all dirty data if they've been created
        if hasattr(self, 'activity_frame'):
            self.activity_frame.save_data()
        if hasattr(self, 'storage_frame'):
            self.storage_frame.save_data()
        self.app.destroy()

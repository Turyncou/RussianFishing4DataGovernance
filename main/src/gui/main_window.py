"""Main application window"""
import sys
import os
import shutil
import threading
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import webbrowser

from data.persistence import (
    LotteryPersistence, ActivityPersistence, StoragePersistence, BaitPersistence,
    FriendLinkPersistence, CredentialsPersistence,
    create_auto_backup, list_backups
)
from core.models import FriendLink
from .lottery_frame import LotteryFrame
from .activity_frame import ActivityFrame
from .storage_frame import StorageFrame
from .credentials_frame import CredentialsFrame
from .bait_frame import BaitFrame
from .statistics_frame import StatisticsFrame
from .backup_dialog import BackupRestoreDialog
from .friend_links_dialog import FriendLinksDialog


class MainWindow:
    """Main application window"""

    def __init__(self, app: ctk.CTk, data_dir: str):
        self.app = app
        self.data_dir = data_dir
        self.current_frame = None
        self._resize_after_id = None  # For debouncing resize

        # Frame cache - cache created frames for faster switching instead of recreating
        self._frame_cache = {}

        # All persistence instances will be initialized in background
        self.lottery_persistence = None
        self.activity_persistence = None
        self.storage_persistence = None
        self.bait_persistence = None
        self.friend_link_persistence = None
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
        self.create_main_content()
        self.show_home_page()

        # Bind global keyboard shortcuts
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        """Bind global keyboard shortcuts"""
        # Ctrl+S: Save data
        self.app.bind('<Control-s>', lambda e: self._handle_save_shortcut())
        self.app.bind('<Control-S>', lambda e: self._handle_save_shortcut())
        # Ctrl+N: Add new item
        self.app.bind('<Control-n>', lambda e: self._handle_new_shortcut())
        self.app.bind('<Control-N>', lambda e: self._handle_new_shortcut())
        # Delete: Delete selected item
        self.app.bind('<Delete>', lambda e: self._handle_delete_shortcut())
        # Escape: Close toplevel dialog
        self.app.bind('<Escape>', lambda e: self._handle_escape_shortcut())

    def _handle_save_shortcut(self):
        """Handle Ctrl+S save shortcut"""
        # Try to save on the current active frame
        saved = False
        # Check activity frame
        if hasattr(self, 'activity_frame') and self.activity_frame.winfo_exists():
            self.activity_frame.save_data()
            saved = True
        # Check storage frame
        elif hasattr(self, 'storage_frame') and self.storage_frame.winfo_exists():
            self.storage_frame.save_data()
            saved = True
        # Check bait frame
        elif hasattr(self, 'bait_frame') and self.bait_frame.winfo_exists():
            self.bait_frame.save_data()
            saved = True
        # No save needed for other frames (auto-save already)

    def _handle_new_shortcut(self):
        """Handle Ctrl+N new item shortcut"""
        # Trigger add new on the current active frame
        # Check activity frame
        if hasattr(self, 'activity_frame') and self.activity_frame.winfo_exists():
            # Activity frame adds new character
            self.activity_frame.add_character()
        # Check storage frame
        elif hasattr(self, 'storage_frame') and self.storage_frame.winfo_exists():
            self.storage_frame.add_character()
        # Check bait frame
        elif hasattr(self, 'bait_frame') and self.bait_frame.winfo_exists():
            self.bait_frame.add_bait()
        # Check lottery frame - no add needed
        # Check credentials frame
        elif hasattr(self, 'credentials_frame') and self.credentials_frame.winfo_exists():
            self.credentials_frame.add_account()

    def _handle_delete_shortcut(self):
        """Handle Delete delete selected item shortcut"""
        # Trigger delete selected on the current active frame
        # Check activity frame
        if hasattr(self, 'activity_frame') and self.activity_frame.winfo_exists():
            self.activity_frame.delete_character()
        # Check storage frame
        elif hasattr(self, 'storage_frame') and self.storage_frame.winfo_exists():
            self.storage_frame.delete_selected()
        # Check bait frame
        elif hasattr(self, 'bait_frame') and self.bait_frame.winfo_exists():
            self.bait_frame.delete_selected()
        # Check credentials frame
        elif hasattr(self, 'credentials_frame') and self.credentials_frame.winfo_exists():
            self.credentials_frame.delete_selected()

    def _handle_escape_shortcut(self):
        """Handle Escape shortcut - close toplevel dialog"""
        # Find the toplevel window and close it
        # The toplevel is the topmost window in the window stack
        toplevel = None
        for w in self.app.winfo_children():
            if isinstance(w, ctk.CTkToplevel) and w.winfo_exists():
                # Check if it's visible
                if w.winfo_ismapped():
                    toplevel = w
        if toplevel:
            try:
                toplevel.grab_release()
                toplevel.destroy()
            except:
                pass


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
        self.content_container = ctk.CTkScrollableFrame(self.main_container, corner_radius=8)
        self.content_container.pack(fill="both", expand=True, padx=15, pady=8)

        # Bottom buttons bar (backup and friend links)
        self.bottom_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.bottom_bar.pack(fill="x", padx=15, pady=(8, 15))

        # Backup/Restore button (left)
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

        # Home page container - transparent to show background
        home_frame = ctk.CTkFrame(self.content_container, fg_color="transparent", corner_radius=16)
        home_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Welcome label
        welcome_label = ctk.CTkLabel(
            home_frame,
            text="欢迎使用 RF4 数据统计工具",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        welcome_label.pack(pady=(60, 40))

        # Button container - use grid layout for better space usage on large screens
        btn_container = ctk.CTkFrame(home_frame, fg_color="transparent")
        btn_container.pack(fill="both", expand=True, padx=50, pady=20)

        # Configure grid: 2 columns, 3 rows, all cells equally weighted
        btn_container.grid_rowconfigure(0, weight=1)
        btn_container.grid_rowconfigure(1, weight=1)
        btn_container.grid_rowconfigure(2, weight=1)
        btn_container.grid_columnconfigure(0, weight=1)
        btn_container.grid_columnconfigure(1, weight=1)

        # Big buttons for each function - 2 columns x 3 rows grid layout
        btn_size = 220
        btn_height = 80
        btn_font = ctk.CTkFont(size=20, weight="bold")

        # Row 0
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
        activity_btn.grid(row=0, column=0, padx=20, pady=15)

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
        storage_btn.grid(row=0, column=1, padx=20, pady=15)

        # Row 1
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
        bait_btn.grid(row=1, column=0, padx=20, pady=15)

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
        lottery_btn.grid(row=1, column=1, padx=20, pady=15)

        # Row 2
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
        credentials_btn.grid(row=2, column=0, padx=20, pady=15)

        statistics_btn = ctk.CTkButton(
            btn_container,
            text="📈 数据分析",
            command=self.show_statistics,
            width=btn_size,
            height=btn_height,
            font=btn_font,
            corner_radius=12,
            fg_color="#2c5aa0",
            hover_color="#1a3d66"
        )
        statistics_btn.grid(row=2, column=1, padx=20, pady=15)

        self.current_frame = home_frame
        # Update scrollable region after adding content
        self.content_container.update()

    def clear_current_content(self):
        """Clear the current content frame - for cached frames, just unpact don't destroy"""
        if self.current_frame is not None:
            self.current_frame.pack_forget()
            # Don't destroy cached frames, they are kept in cache
            self.current_frame = None

    def show_activity_stats(self):
        """Show activity statistics page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        # Use cached frame if already created
        cache_key = "activity_stats"
        if cache_key in self._frame_cache:
            frame, activity_frame = self._frame_cache[cache_key]
            frame.pack(fill="both", expand=True)
            activity_frame.update()  # Refresh display
        else:
            frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            frame.pack(fill="both", expand=True)
            activity_frame = ActivityFrame(
                frame,
                self.activity_persistence
            )
            activity_frame.pack(fill="both", expand=True)
            self._frame_cache[cache_key] = (frame, activity_frame)
        self.activity_frame = activity_frame
        self.current_frame = frame

        # Update scrollable region after adding content
        self.content_container.update()

    def show_storage(self):
        """Show storage duration page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        # Use cached frame if already created
        cache_key = "storage"
        if cache_key in self._frame_cache:
            frame, storage_frame = self._frame_cache[cache_key]
            frame.pack(fill="both", expand=True)
            storage_frame.update_table()  # Refresh display
        else:
            frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            frame.pack(fill="both", expand=True)
            storage_frame = StorageFrame(
                frame,
                self.storage_persistence
            )
            storage_frame.pack(fill="both", expand=True)
            self._frame_cache[cache_key] = (frame, storage_frame)
        self.storage_frame = storage_frame
        self.current_frame = frame

        # Update scrollable region after adding content
        self.content_container.update()

    def show_lottery(self):
        """Show lottery wheel page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        # Use cached frame if already created
        cache_key = "lottery"
        if cache_key in self._frame_cache:
            frame, lottery_frame = self._frame_cache[cache_key]
            frame.pack(fill="both", expand=True)
            lottery_frame.draw_wheel()  # Refresh display
        else:
            frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            frame.pack(fill="both", expand=True)
            lottery_frame = LotteryFrame(
                frame,
                self.lottery_persistence
            )
            lottery_frame.pack(fill="both", expand=True)
            self._frame_cache[cache_key] = (frame, lottery_frame)
        self.lottery_frame = lottery_frame
        self.current_frame = frame

        # Update scrollable region after adding content
        self.content_container.update()

    def show_credentials(self):
        """Show account credentials manager page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        # Use cached frame if already created
        cache_key = "credentials"
        if cache_key in self._frame_cache:
            frame, credentials_frame = self._frame_cache[cache_key]
            frame.pack(fill="both", expand=True)
            credentials_frame.update_dropdown()  # Refresh display
        else:
            frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            frame.pack(fill="both", expand=True)
            credentials_frame = CredentialsFrame(
                frame,
                self.credentials_persistence
            )
            credentials_frame.pack(fill="both", expand=True)
            self._frame_cache[cache_key] = (frame, credentials_frame)
        self.credentials_frame = credentials_frame
        self.current_frame = frame

        # Update scrollable region after adding content
        self.content_container.update()

    def show_bait(self):
        """Show bait/tackle consumption tracking page"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        # Use cached frame if already created
        cache_key = "bait"
        if cache_key in self._frame_cache:
            frame, bait_frame = self._frame_cache[cache_key]
            frame.pack(fill="both", expand=True)
            bait_frame.update_table()  # Refresh display
        else:
            frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            frame.pack(fill="both", expand=True)
            bait_frame = BaitFrame(
                frame,
                self.bait_persistence
            )
            bait_frame.pack(fill="both", expand=True)
            self._frame_cache[cache_key] = (frame, bait_frame)
        self.bait_frame = bait_frame
        self.current_frame = frame

        # Update scrollable region after adding content
        self.content_container.update()

    def show_statistics(self):
        """Show data analysis page with visualizations"""
        # Show back button
        self.back_button.pack(side="left", padx=(10, 0), pady=10)
        self.clear_current_content()

        # Use cached frame if already created
        cache_key = "statistics"
        if cache_key in self._frame_cache:
            frame, statistics_frame = self._frame_cache[cache_key]
            frame.pack(fill="both", expand=True)
            statistics_frame.refresh_plots()  # Refresh data
        else:
            frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            frame.pack(fill="both", expand=True)
            statistics_frame = StatisticsFrame(
                frame,
                self.activity_persistence
            )
            statistics_frame.pack(fill="both", expand=True)
            self._frame_cache[cache_key] = (frame, statistics_frame)
        self.statistics_frame = statistics_frame
        self.current_frame = frame

        # Update scrollable region after adding content
        self.content_container.update()

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

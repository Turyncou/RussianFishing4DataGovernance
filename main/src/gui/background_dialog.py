"""Background image change dialog"""
import os
import shutil
import customtkinter as ctk
from tkinter import filedialog
from core.models import BackgroundConfig


class BackgroundDialog(ctk.CTkToplevel):
    """Dialog for changing background image and adjusting opacity"""

    def __init__(self, parent, current_config: BackgroundConfig, callback, app_data_dir: str):
        super().__init__(parent)
        self.callback = callback
        self.current_config = current_config
        self.app_data_dir = app_data_dir
        self.new_image_path = current_config.image_path

        self.title("更换背景")
        self.geometry("450x280")
        self.resizable(False, False)
        self.grab_set()

        # Use scrollable frame
        scrollable_frame = ctk.CTkScrollableFrame(self, width=430, height=240)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.create_widgets(scrollable_frame)

    def create_widgets(self, parent):
        """Create dialog widgets"""
        ctk.CTkLabel(
            parent,
            text="更换背景图片",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 10))

        # Current path display
        path_frame = ctk.CTkFrame(parent, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(path_frame, text="当前图片:").pack(side="left", padx=5)
        if self.current_config.image_path:
            display_path = os.path.basename(self.current_config.image_path)
        else:
            display_path = "无"
        self.path_label = ctk.CTkLabel(path_frame, text=display_path)
        self.path_label.pack(side="left", padx=5)

        # Select button
        select_btn = ctk.CTkButton(
            parent,
            text="选择图片",
            command=self.select_image,
            width=120
        )
        select_btn.pack(pady=10)

        # Opacity slider
        opacity_frame = ctk.CTkFrame(parent, fg_color="transparent")
        opacity_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(opacity_frame, text="透明度:").pack(side="left", padx=5)

        self.opacity_slider = ctk.CTkSlider(
            opacity_frame,
            from_=0.1,
            to=1.0,
            number_of_steps=18,
            width=200
        )
        self.opacity_slider.set(self.current_config.opacity)
        self.opacity_slider.pack(side="left", padx=10)

        self.opacity_label = ctk.CTkLabel(
            opacity_frame,
            text=f"{int(self.current_config.opacity * 100)}%"
        )
        self.opacity_label.pack(side="left", padx=5)

        def update_label(value):
            self.opacity_label.configure(text=f"{int(value * 100)}%")

        self.opacity_slider.configure(command=update_label)

        # Buttons
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 20))

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            command=self.save,
            width=100
        )
        save_btn.pack(side="right", padx=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.destroy,
            width=100,
            fg_color="#888888",
            hover_color="#666666"
        )
        cancel_btn.pack(side="right", padx=5)

        clear_btn = ctk.CTkButton(
            btn_frame,
            text="清除背景",
            command=self.clear_image,
            width=100,
            fg_color="#cc3333",
            hover_color="#aa2222"
        )
        clear_btn.pack(side="left", padx=5)

    def select_image(self):
        """Open file dialog to select image"""
        filetypes = [
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif"),
            ("所有文件", "*.*")
        ]
        filename = filedialog.askopenfilename(
            title="选择背景图片",
            filetypes=filetypes
        )
        if filename:
            self.new_image_path = filename
            self.path_label.configure(text=os.path.basename(filename))

    def clear_image(self):
        """Clear the background image"""
        self.new_image_path = None
        self.path_label.configure(text="无")

    def save(self):
        """Save the new configuration, copy image to app data directory"""
        opacity = self.opacity_slider.get()

        if self.new_image_path is not None and os.path.exists(self.new_image_path):
            # Copy the selected image to app data directory
            # Use original filename but make sure it's unique
            filename = os.path.basename(self.new_image_path)
            dest_path = os.path.join(self.app_data_dir, f"background_{filename}")
            # If file already exists, don't overwrite - keep the same name
            if not os.path.exists(dest_path):
                try:
                    shutil.copy2(self.new_image_path, dest_path)
                    self.new_image_path = dest_path
                except Exception:
                    # If copy fails, keep original path
                    pass

        new_config = BackgroundConfig(
            image_path=self.new_image_path,
            opacity=opacity
        )
        self.callback(new_config)
        self.grab_release()
        self.destroy()

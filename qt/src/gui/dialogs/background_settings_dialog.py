"""Background settings dialog - select background image and adjust opacity"""
import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QLineEdit, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class BackgroundSettingsDialog(QDialog):
    """Dialog for setting background image and adjusting opacity"""

    settings_changed = Signal(str, float)  # (image_path, opacity)

    def __init__(self, parent=None, current_path: str = None, current_opacity: float = 0.15):
        super().__init__(parent)
        self.setWindowTitle("背景设置")
        self.resize(500, 220)
        self.setModal(True)

        self.selected_image_path = current_path
        self.backgrounds_dir = None
        if parent and hasattr(parent, 'data_dir'):
            self.backgrounds_dir = os.path.join(parent.data_dir, 'backgrounds')
            os.makedirs(self.backgrounds_dir, exist_ok=True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Current image path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("背景图片:"))
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        if current_path:
            self.path_edit.setText(current_path)
        else:
            self.path_edit.setText("未选择图片")
        path_layout.addWidget(self.path_edit, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_image)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Opacity slider
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        # opacity 0-1 -> slider 0-100
        self.opacity_slider.setValue(int(current_opacity * 100))
        opacity_layout.addWidget(self.opacity_slider, 1)
        self.opacity_label = QLabel(f"{current_opacity * 100:.0f}%")
        self.opacity_label.setFixedWidth(40)
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)

        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)

        # Clear background checkbox
        checkbox_layout = QHBoxLayout()
        self.clear_checkbox = QCheckBox("清除背景图片")
        self.clear_checkbox.setChecked(not current_path)
        self.clear_checkbox.clicked.connect(self._on_clear_clicked)
        checkbox_layout.addWidget(self.clear_checkbox)
        layout.addLayout(checkbox_layout)

        # Preview label
        preview_label = QLabel("提示：透明度建议设置 10%-20%，不影响内容阅读")
        preview_label.setStyleSheet("color: #888888;")
        layout.addWidget(preview_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _browse_image(self):
        """Open file dialog to select image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择背景图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
        )
        if file_path:
            self.selected_image_path = file_path
            self.path_edit.setText(file_path)
            self.clear_checkbox.setChecked(False)

    def _on_opacity_changed(self, value):
        """Update opacity label when slider changes"""
        opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")

    def _on_clear_clicked(self, checked):
        """Clear selected image when checkbox is checked"""
        if checked:
            self.selected_image_path = None
            self.path_edit.setText("未选择图片")
        else:
            if not self.selected_image_path:
                self._browse_image()

    def _save_settings(self):
        """Save settings and emit signal"""
        opacity = self.opacity_slider.value() / 100.0

        if self.clear_checkbox.isChecked():
            # No background
            self.settings_changed.emit(None, opacity)
            self.accept()
            return

        if not self.selected_image_path:
            # Nothing selected
            self.settings_changed.emit(None, opacity)
            self.accept()
            return

        # Copy image to data/backgrounds folder if we have the directory
        if self.backgrounds_dir and os.path.exists(self.selected_image_path):
            # Get file extension
            ext = os.path.splitext(self.selected_image_path)[1].lower()
            # Create new filename based on original name with hash to avoid conflicts
            import hashlib
            hash_name = hashlib.md5(self.selected_image_path.encode()).hexdigest()[:8]
            base_name = os.path.basename(self.selected_image_path)
            base_name = os.path.splitext(base_name)[0]
            cached_filename = f"{base_name}_{hash_name}{ext}"
            cached_path = os.path.join(self.backgrounds_dir, cached_filename)

            # Copy file to cache
            try:
                shutil.copy2(self.selected_image_path, cached_path)
                # Use cached path for storage
                self.selected_image_path = cached_path
            except Exception as e:
                # If copy fails, just keep original path
                pass

        self.settings_changed.emit(self.selected_image_path, opacity)
        self.accept()

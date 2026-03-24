"""Background Settings UI dialog"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton, QLabel, QSlider, QFileDialog
)
from PyQt6.QtCore import Qt
from src.core.background import BackgroundModel


class BackgroundSettingsDialog(QDialog):
    """Dialog for background image settings"""

    def __init__(self, parent, model: BackgroundModel):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("背景设置")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Current image info
        self.current_path_label = QLabel()
        current_path = model.get_custom_image_path()
        if current_path:
            self.current_path_label.setText(f"当前背景: {current_path}")
        else:
            self.current_path_label.setText("当前背景: 默认")
        layout.addWidget(self.current_path_label)

        # Browse button
        self.browse_button = QPushButton("选择图片")
        self.browse_button.clicked.connect(self.on_browse_clicked)
        layout.addWidget(self.browse_button)

        # Clear button
        self.clear_button = QPushButton("清除自定义背景")
        self.clear_button.clicked.connect(self.on_clear_clicked)
        layout.addWidget(self.clear_button)

        # Transparency slider
        layout.addWidget(QLabel("背景透明度 (0 = 完全透明, 1 = 完全不透明):"))
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(0, 100)
        self.transparency_slider.setValue(int(model.get_settings()["transparency"] * 100))
        layout.addWidget(self.transparency_slider)
        self.transparency_slider.valueChanged.connect(self.on_transparency_changed)

        # Current transparency value
        self.transparency_label = QLabel(f"当前透明度: {model.get_settings()['transparency']:.2f}")
        layout.addWidget(self.transparency_label)

        # Reset to default button
        self.reset_button = QPushButton("重置为默认")
        self.reset_button.clicked.connect(self.on_reset_clicked)
        layout.addWidget(self.reset_button)

        # Buttons
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._selected_path = model.get_custom_image_path()

    def on_browse_clicked(self):
        """Handle browse button click"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择背景图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif);;所有文件 (*)"
        )
        if file_path:
            self._selected_path = file_path
            self.current_path_label.setText(f"选择: {file_path}")

    def on_clear_clicked(self):
        """Clear custom image"""
        self._selected_path = None
        self.current_path_label.setText("当前背景: 默认")

    def on_transparency_changed(self, value):
        """Update transparency label"""
        transparency = value / 100.0
        self.transparency_label.setText(f"当前透明度: {transparency:.2f}")

    def on_reset_clicked(self):
        """Reset to default"""
        self._selected_path = None
        self.transparency_slider.setValue(80)
        self.current_path_label.setText("当前背景: 默认")

    def get_settings(self):
        """Get the updated settings"""
        transparency = self.transparency_slider.value() / 100.0
        return {
            "custom_image_path": self._selected_path,
            "transparency": transparency
        }

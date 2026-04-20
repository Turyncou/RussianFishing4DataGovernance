"""Application settings dialog - general settings including theme and background"""
import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QSlider, QLineEdit, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class AppSettingsDialog(QDialog):
    """Application settings dialog for all app settings"""

    settings_changed = Signal(str, float, str, bool, str, str, str, bool, bool, bool)
    # (background_image_path, background_opacity, theme, show_income_info, start_hotkey, stop_hotkey, save_path, record_mic, record_system, special_cursor_on_hover)

    def __init__(self, parent=None,
                 current_path: str = None,
                 current_opacity: float = 0.15,
                 current_theme: str = "dark",
                 current_show_income: bool = False,
                 current_start_hotkey: str = "ctrl+shift+r",
                 current_stop_hotkey: str = "ctrl+shift+s",
                 current_save_path: str = None,
                 current_record_mic: bool = False,
                 current_record_system: bool = False,
                 current_special_cursor: bool = True,
                 current_mic_device: str = None,
                 current_system_device: str = None):
        super().__init__(parent)
        self.setWindowTitle("应用设置")
        self.resize(600, 680)
        self.setModal(True)

        self.selected_image_path = current_path
        self.selected_save_path = current_save_path
        self.current_record_mic = current_record_mic
        self.current_record_system = current_record_system
        self.current_special_cursor = current_special_cursor
        self.current_mic_device = current_mic_device
        self.current_system_device = current_system_device
        self.backgrounds_dir = None
        if parent and hasattr(parent, 'data_dir'):
            self.backgrounds_dir = os.path.join(parent.data_dir, 'backgrounds')
            os.makedirs(self.backgrounds_dir, exist_ok=True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Theme selection
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("主题:"))
        self.dark_checkbox = QCheckBox("深色主题")
        self.dark_checkbox.setChecked(current_theme == "dark")
        self.dark_checkbox.clicked.connect(self._on_theme_changed)
        theme_layout.addWidget(self.dark_checkbox)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        # Background image path
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
        opacity_layout.addWidget(QLabel("背景透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        # opacity 0-1 -> slider 0-100
        self.opacity_slider.setValue(int(current_opacity * 100))
        self.opacity_label = QLabel(f"{current_opacity * 100:.0f}%")
        self.opacity_label.setFixedWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)

        # Clear background checkbox
        clear_layout = QHBoxLayout()
        self.clear_checkbox = QCheckBox("清除背景图片")
        self.clear_checkbox.setChecked(not current_path)
        self.clear_checkbox.clicked.connect(self._on_clear_clicked)
        clear_layout.addWidget(self.clear_checkbox)
        layout.addLayout(clear_layout)

        # Show income info checkbox
        income_layout = QHBoxLayout()
        self.show_income_checkbox = QCheckBox("显示收入信息")
        self.show_income_checkbox.setChecked(current_show_income)
        self.show_income_checkbox.setToolTip(
            "在活动统计页面显示\"已获得收入/总收入\"\n"
            "关闭后界面更简洁，保护收入隐私"
        )
        income_layout.addWidget(self.show_income_checkbox)
        layout.addLayout(income_layout)

        # Special cursor on hover checkbox
        cursor_layout = QHBoxLayout()
        self.special_cursor_checkbox = QCheckBox("鼠标悬停切换特殊指针")
        self.special_cursor_checkbox.setChecked(current_special_cursor)
        self.special_cursor_checkbox.setToolTip(
            "鼠标移入窗口时自动切换为手型指针\n"
            "移出后恢复箭头指针"
        )
        cursor_layout.addWidget(self.special_cursor_checkbox)
        layout.addLayout(cursor_layout)

        # Screen Recorder Settings
        # Add separator
        separator = QLabel("────────────────────────────────────────")
        separator.setStyleSheet("color: #888888;")
        layout.addWidget(separator)

        # Title for screen recorder
        screen_recorder_title = QLabel("<b>全屏录屏设置</b>")
        screen_recorder_title.setTextFormat(Qt.RichText)
        layout.addWidget(screen_recorder_title)

        # Start hotkey
        start_hotkey_layout = QHBoxLayout()
        start_hotkey_layout.addWidget(QLabel("开始录屏快捷键:"))
        self.start_hotkey_edit = QLineEdit(current_start_hotkey)
        self.start_hotkey_edit.setPlaceholderText("例如: ctrl+shift+r")
        start_hotkey_layout.addWidget(self.start_hotkey_edit)
        layout.addLayout(start_hotkey_layout)

        # Stop hotkey
        stop_hotkey_layout = QHBoxLayout()
        stop_hotkey_layout.addWidget(QLabel("停止录屏快捷键:"))
        self.stop_hotkey_edit = QLineEdit(current_stop_hotkey)
        self.stop_hotkey_edit.setPlaceholderText("例如: ctrl+shift+s")
        stop_hotkey_layout.addWidget(self.stop_hotkey_edit)
        layout.addLayout(stop_hotkey_layout)

        # Save path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("录屏保存路径:"))
        self.save_path_edit = QLineEdit()
        if self.selected_save_path:
            self.save_path_edit.setText(self.selected_save_path)
        else:
            self.save_path_edit.setText("默认: 用户视频文件夹")
        self.save_path_edit.setReadOnly(True)
        path_layout.addWidget(self.save_path_edit, 1)
        browse_path_btn = QPushButton("浏览...")
        browse_path_btn.clicked.connect(self._browse_save_path)
        path_layout.addWidget(browse_path_btn)
        layout.addLayout(path_layout)

        # Hint
        hint_label = QLabel("提示：背景透明度建议设置 10%-20%，不影响内容阅读")
        hint_label.setStyleSheet("color: #888888;")
        layout.addWidget(hint_label)

        # Audio recording options
        audio_layout = QVBoxLayout()
        self.record_mic_checkbox = QCheckBox("录制麦克风音频")
        self.record_mic_checkbox.setChecked(current_record_mic)
        self.record_mic_checkbox.setToolTip("开启后会录制麦克风声音到视频中\n需要安装 pyaudio 库")
        audio_layout.addWidget(self.record_mic_checkbox)

        self.record_system_checkbox = QCheckBox("录制系统音频")
        self.record_system_checkbox.setChecked(current_record_system)
        self.record_system_checkbox.setToolTip(
            "开启后会录制系统播放声音（游戏背景音乐等）到视频中\n"
            "使用 WASAPI 直接捕获系统输出，不需要修改 Windows 默认设备\n"
            "耳机、扬声器都可以正常录制，需要安装 pycaw comtypes 库"
        )
        audio_layout.addWidget(self.record_system_checkbox)

        # Audio device selection combo boxes
        from PySide6.QtWidgets import QComboBox
        device_layout = QVBoxLayout()
        device_layout.addSpacing(8)
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("麦克风设备:"))
        self.mic_device_combo = QComboBox()
        mic_layout.addWidget(self.mic_device_combo)
        device_layout.addLayout(mic_layout)

        system_layout = QHBoxLayout()
        system_layout.addWidget(QLabel("系统音频设备:"))
        self.system_device_combo = QComboBox()
        system_layout.addWidget(self.system_device_combo)
        device_layout.addLayout(system_layout)

        audio_layout.addLayout(device_layout)

        layout.addLayout(audio_layout)

        # Populate devices after UI is created
        self._populate_audio_devices()

        # Hotkey hint
        hotkey_hint = QLabel("快捷键格式说明: ctrl+shift+r, alt+s 等 (需要 keyboard 库支持)\n音频录制需要额外安装: pip install pyaudio sounddevice")
        hotkey_hint.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(hotkey_hint)
        hotkey_hint.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(hotkey_hint)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(80)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _on_theme_changed(self):
        """Update theme checkbox - only one can be selected"""
        # dark_checkbox checked means dark theme, unchecked means light
        pass

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

    def _populate_audio_devices(self):
        """Enumerate all available audio input devices and add to combo boxes"""
        # Try to get device list from sounddevice
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            device_names = []
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    # Only include input devices
                    name = dev['name'].strip()
                    # Add (channels) info
                    chan = dev['max_input_channels']
                    device_names.append(f"{name} ({chan} ch)")
            # Add default option
            device_names.insert(0, "默认 (使用系统默认)")
            # Clear and add to combo boxes
            self.mic_device_combo.clear()
            self.mic_device_combo.addItems(device_names)
            self.system_device_combo.clear()
            self.system_device_combo.addItems(device_names)
        except ImportError:
            # sounddevice not installed, just add default
            self.mic_device_combo.clear()
            self.mic_device_combo.addItem("默认 (使用系统默认)")
            self.system_device_combo.clear()
            self.system_device_combo.addItem("默认 (使用系统默认)")
        except Exception as e:
            print(f"Failed to enumerate audio devices: {e}")
            self.mic_device_combo.clear()
            self.mic_device_combo.addItem("默认 (使用系统默认)")
            self.system_device_combo.clear()
            self.system_device_combo.addItem("默认 (使用系统默认)")

    def _browse_save_path(self):
        """Browse for save directory"""
        folder = QFileDialog.getExistingDirectory(self, "选择录屏保存文件夹", self.selected_save_path or "")
        if folder:
            self.selected_save_path = folder
            self.save_path_edit.setText(folder)

    def _save_settings(self):
        """Save settings and emit signal"""
        opacity = self.opacity_slider.value() / 100.0
        theme = "dark" if self.dark_checkbox.isChecked() else "light"
        show_income = self.show_income_checkbox.isChecked()
        start_hotkey = self.start_hotkey_edit.text().strip() or "ctrl+shift+r"
        stop_hotkey = self.stop_hotkey_edit.text().strip() or "ctrl+shift+s"
        save_path = self.selected_save_path if self.selected_save_path else None
        record_mic = self.record_mic_checkbox.isChecked()
        record_system = self.record_system_checkbox.isChecked()
        special_cursor = self.special_cursor_checkbox.isChecked()

        # Get selected device names
        mic_device = self.mic_device_combo.currentText()
        system_device = self.system_device_combo.currentText()
        # Clean up " (X ch)" suffix if present - we just need the name
        if mic_device and " (" in mic_device:
            mic_device = mic_device.rsplit(" (", 1)[0]
        if mic_device == "默认 (使用系统默认)":
            mic_device = None
        if system_device and " (" in system_device:
            system_device = system_device.rsplit(" (", 1)[0]
        if system_device == "默认 (使用系统默认)":
            system_device = None

        if self.clear_checkbox.isChecked():
            # No background
            self.settings_changed.emit(None, opacity, theme, show_income, start_hotkey, stop_hotkey, save_path, record_mic, record_system, special_cursor)
            self.accept()
            return

        if not self.selected_image_path:
            # Nothing selected
            self.settings_changed.emit(None, opacity, theme, show_income, start_hotkey, stop_hotkey, save_path, record_mic, record_system, special_cursor)
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

        self.settings_changed.emit(self.selected_image_path, opacity, theme, show_income, start_hotkey, stop_hotkey, save_path, record_mic, record_system, special_cursor)
        self.accept()

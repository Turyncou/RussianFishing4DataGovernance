"""Storage Tracking UI widget"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QDialog, QFormLayout,
    QLineEdit, QSpinBox, QDialogButtonBox, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt
from src.core.data_manager import DataManager
from src.core.storage_tracking import StorageTrackingModel


class StorageTrackingWidget(QWidget):
    """Storage duration tracking widget"""

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.model = StorageTrackingModel()

        # Load saved data
        saved_data = data_manager.load_storage_tracking()
        self.model.load_from_data(saved_data)

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)

        # Summary
        self.total_label = QLabel("总计剩余时间: 0 分钟")
        layout.addWidget(self.total_label)

        # Storage table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["窝子", "剩余分钟", "+", "-"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Controls
        controls_layout = QHBoxLayout()

        self.add_button = QPushButton("添加窝子")
        self.add_button.clicked.connect(self.on_add_clicked)
        controls_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("删除窝子")
        self.remove_button.clicked.connect(self.on_remove_clicked)
        controls_layout.addWidget(self.remove_button)

        layout.addLayout(controls_layout)

        self.setLayout(layout)

    def refresh(self):
        """Refresh display from model"""
        total = self.model.get_total_remaining()
        self.total_label.setText(f"总计剩余时间: {total:,} 分钟 = {total / 60:.1f} 小时")

        characters = self.model.get_characters()
        self.table.setRowCount(len(characters))

        for row, char in enumerate(characters):
            name_item = QTableWidgetItem(char["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            remaining_item = QTableWidgetItem(str(char["remaining_minutes"]))
            remaining_item.setFlags(remaining_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, remaining_item)

            # Add plus button
            plus_button = QPushButton("+")
            plus_button.setFixedWidth(60)
            plus_button.clicked.connect(lambda checked, r=row: self.on_add_time(r))
            self.table.setCellWidget(row, 2, plus_button)

            # Add minus button
            minus_button = QPushButton("-")
            minus_button.setFixedWidth(60)
            minus_button.clicked.connect(lambda checked, r=row: self.on_subtract_time(r))
            self.table.setCellWidget(row, 3, minus_button)

        self.save()

    def on_add_clicked(self):
        """Add new character"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加窝子")
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        layout.addRow("窝子名称:", name_edit)

        initial_spin = QSpinBox()
        initial_spin.setRange(0, 10000)
        initial_spin.setValue(0)
        layout.addRow("初始剩余分钟:", initial_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            initial = initial_spin.value()
            if not name:
                QMessageBox.warning(self, "警告", "窝子名称不能为空")
                return
            if not self.model.add_character(name, initial):
                QMessageBox.warning(self, "警告", "窝子名称已存在")
                return
            self.refresh()

    def on_remove_clicked(self):
        """Remove selected character"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择要删除的窝子")
            return

        name = self.table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, "确认删除", f"确认删除窝子 '{name}' 吗?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.model.remove_character(name)
            self.refresh()

    def on_add_time(self, row):
        """Add time to character"""
        name = self.table.item(row, 0).text()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"增加时间 - {name}")
        layout = QFormLayout(dialog)

        add_spin = QSpinBox()
        add_spin.setRange(1, 1440)
        add_spin.setValue(15)
        layout.addRow("增加分钟:", add_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            minutes = add_spin.value()
            self.model.add_time(name, minutes)
            self.refresh()

    def on_subtract_time(self, row):
        """Subtract time from character"""
        name = self.table.item(row, 0).text()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"减少时间 - {name}")
        layout = QFormLayout(dialog)

        subtract_spin = QSpinBox()
        subtract_spin.setRange(1, 1440)
        subtract_spin.setValue(15)
        layout.addRow("减少分钟:", subtract_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            minutes = subtract_spin.value()
            self.model.subtract_time(name, minutes)
            self.refresh()

    def save(self):
        """Save current data"""
        data = self.model.get_data_for_saving()
        self.data_manager.save_storage_tracking(data)

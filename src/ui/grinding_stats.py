"""Grinding Statistics UI widget"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QLabel, QGroupBox,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt
from src.core.data_manager import DataManager
from src.core.grinding_stats import GrindingStatsModel


class GrindingStatsWidget(QWidget):
    """Grinding statistics widget"""

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.model = GrindingStatsModel()

        # Load saved data
        saved_data = data_manager.load_grinding_stats()
        self.model.load_from_data(saved_data)

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)

        # Summary group box
        summary_group = QGroupBox("总体统计")
        summary_layout = QVBoxLayout(summary_group)

        self.today_label = QLabel("今日银币: 0 | 今日时长: 0 分钟")
        summary_layout.addWidget(self.today_label)

        self.total_label = QLabel("总计银币: 0 | 总计时长: 0 分钟")
        summary_layout.addWidget(self.total_label)

        # Progress bars
        self.silver_progress = QProgressBar()
        self.silver_progress.setRange(0, 100)
        summary_layout.addWidget(QLabel("银币目标进度:"))
        summary_layout.addWidget(self.silver_progress)

        self.minutes_progress = QProgressBar()
        self.minutes_progress.setRange(0, 100)
        summary_layout.addWidget(QLabel("时长目标进度:"))
        summary_layout.addWidget(self.minutes_progress)

        self.remaining_label = QLabel("剩余银币: 0 | 剩余时长: 0 分钟")
        summary_layout.addWidget(self.remaining_label)

        layout.addWidget(summary_group)

        # Character table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["角色", "今日银币", "今日时长"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Controls
        controls_layout = QHBoxLayout()

        self.add_char_button = QPushButton("添加角色")
        self.add_char_button.clicked.connect(self.on_add_character)
        controls_layout.addWidget(self.add_char_button)

        self.remove_char_button = QPushButton("删除角色")
        self.remove_char_button.clicked.connect(self.on_remove_character)
        controls_layout.addWidget(self.remove_char_button)

        self.add_data_button = QPushButton("添加今日数据")
        self.add_data_button.clicked.connect(self.on_add_data)
        controls_layout.addWidget(self.add_data_button)

        self.set_goal_button = QPushButton("设置目标")
        self.set_goal_button.clicked.connect(self.on_set_goal)
        controls_layout.addWidget(self.set_goal_button)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        controls_layout.addWidget(self.refresh_button)

        layout.addLayout(controls_layout)

        self.setLayout(layout)

    def refresh(self):
        """Refresh display from model"""
        # Update summary
        today = datetime.now().strftime("%Y-%m-%d")
        overall = self.model.get_overall_total()
        progress = self.model.calculate_progress()
        remaining = self.model.calculate_remaining()

        # Find today's total across all characters
        today_silver = 0
        today_minutes = 0
        for char in self.model.get_characters():
            if today in char["daily_data"]:
                today_silver += char["daily_data"][today]["silver"]
                today_minutes += char["daily_data"][today]["minutes"]

        self.today_label.setText(f"今日银币: {today_silver:,} | 今日时长: {today_minutes} 分钟")
        self.total_label.setText(f"总计银币: {overall['total_silver']:,} | 总计时长: {overall['total_minutes']} 分钟")
        self.silver_progress.setValue(int(progress["silver_percent"]))
        self.minutes_progress.setValue(int(progress["minutes_percent"]))
        self.remaining_label.setText(
            f"剩余银币: {remaining['remaining_silver']:,} | 剩余时长: {remaining['remaining_minutes']} 分钟"
        )

        # Update table
        characters = self.model.get_characters()
        self.table.setRowCount(len(characters))

        for row, char in enumerate(characters):
            name_item = QTableWidgetItem(char["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            today_data = char["daily_data"].get(today, {"silver": 0, "minutes": 0})
            silver_item = QTableWidgetItem(str(today_data["silver"]))
            self.table.setItem(row, 1, silver_item)

            minutes_item = QTableWidgetItem(str(today_data["minutes"]))
            self.table.setItem(row, 2, minutes_item)

        self.save()

    def on_add_character(self):
        """Add new character"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加角色")
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        layout.addRow("角色名称:", name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "警告", "角色名称不能为空")
                return
            if not self.model.add_character(name):
                QMessageBox.warning(self, "警告", "角色名称已存在")
                return
            self.refresh()

    def on_remove_character(self):
        """Remove selected character"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择要删除的角色")
            return

        character_name = self.table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, "确认删除", f"确认删除角色 '{character_name}' 吗?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.model.remove_character(character_name)
            self.refresh()

    def on_add_data(self):
        """Add today's data"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择角色")
            return

        character_name = self.table.item(current_row, 0).text()
        today = datetime.now().strftime("%Y-%m-%d")

        dialog = QDialog(self)
        dialog.setWindowTitle(f"添加今日数据 - {character_name}")
        layout = QFormLayout(dialog)

        silver_spin = QSpinBox()
        silver_spin.setRange(0, 10000000)
        silver_spin.setSingleStep(10000)
        layout.addRow("今日银币:", silver_spin)

        minutes_spin = QSpinBox()
        minutes_spin.setRange(0, 1440)
        minutes_spin.setSingleStep(15)
        layout.addRow("今日时长(分钟):", minutes_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            silver = silver_spin.value()
            minutes = minutes_spin.value()
            self.model.add_daily_data(character_name, today, silver, minutes)
            self.refresh()

    def on_set_goal(self):
        """Set overall goal"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置搬砖目标")
        layout = QFormLayout(dialog)

        goal = self.model.get_goal()

        silver_spin = QSpinBox()
        silver_spin.setRange(0, 100000000)
        silver_spin.setSingleStep(100000)
        silver_spin.setValue(goal["target_silver"])
        layout.addRow("目标银币:", silver_spin)

        minutes_spin = QSpinBox()
        minutes_spin.setRange(0, 10000)
        minutes_spin.setSingleStep(60)
        minutes_spin.setValue(goal["target_minutes"])
        layout.addRow("目标时长(分钟):", minutes_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            target_silver = silver_spin.value()
            target_minutes = minutes_spin.value()
            self.model.set_goal(target_silver, target_minutes)
            self.refresh()

    def save(self):
        """Save current data"""
        data = self.model.get_data_for_saving()
        self.data_manager.save_grinding_stats(data)

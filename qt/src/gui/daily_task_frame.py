"""Daily task tracking frame - displays and manages daily activity duration targets"""
from datetime import date
from typing import List

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.models import DailyTask, ActivityType, ActivityCharacter, DailyTaskCompletion
from src.data.persistence import DailyTaskPersistence


class DailyTaskFrame(QFrame):
    """Frame for managing daily activity duration tasks and showing completion status"""

    def __init__(self, task_persistence: DailyTaskPersistence, activity_characters: List[ActivityCharacter]):
        super().__init__()
        self.task_persistence = task_persistence
        self.activity_characters = activity_characters
        self.tasks: List[DailyTask] = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup the user interface"""
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #2c5aa0;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1a3d66;
            }
            QPushButton:pressed {
                background-color: #152f4f;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #1f6feb;
            }
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #1f6feb;
                border-color: #1f6feb;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                gridline-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 6px;
            }
            QProgressBar {
                background-color: #2d2d2d;
                border-radius: 4px;
                border: none;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Today's status summary
        self._create_status_summary(layout)

        # Add new task section
        self._create_add_task_section(layout)

        # Tasks table
        self._create_tasks_table(layout)

    def _create_status_summary(self, parent_layout):
        """Create today's completion status summary"""
        group = QGroupBox("📋 今日任务状态")
        layout = QHBoxLayout(group)

        self.summary_label = QLabel("加载中...")
        self.summary_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(self.summary_label)

        layout.addStretch()

        self.refresh_button = QPushButton("🔄 刷新")
        self.refresh_button.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_button)

        parent_layout.addWidget(group)

    def _create_add_task_section(self, parent_layout):
        """Create add new task section"""
        group = QGroupBox("➕ 添加每日任务")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Character selection
        layout.addWidget(QLabel("选择角色:"), 0, 0)
        self.character_combo = QComboBox()
        self._update_character_combo()
        layout.addWidget(self.character_combo, 0, 1)

        # Activity type
        layout.addWidget(QLabel("活动类型:"), 0, 2)
        self.type_combo = QComboBox()
        self.type_combo.addItem("搬砖", ActivityType.GRINDING)
        self.type_combo.addItem("蹲星", ActivityType.STAR_WAITING)
        layout.addWidget(self.type_combo, 0, 3)

        # Target duration
        layout.addWidget(QLabel("目标时长 (分钟):"), 1, 0)
        self.target_spin = QSpinBox()
        self.target_spin.setRange(30, 480)
        self.target_spin.setValue(240)
        self.target_spin.setSingleStep(30)
        layout.addWidget(self.target_spin, 1, 1)

        # Enabled checkbox
        self.enabled_check = QCheckBox("启用任务")
        self.enabled_check.setChecked(True)
        layout.addWidget(self.enabled_check, 1, 2)

        layout.setColumnStretch(3, 1)

        # Add button
        self.add_button = QPushButton("添加任务")
        self.add_button.clicked.connect(self._add_task)
        layout.addWidget(self.add_button, 1, 3)

        parent_layout.addWidget(group)

    def _create_tasks_table(self, parent_layout):
        """Create tasks table with progress"""
        group = QGroupBox("📊 任务列表")
        layout = QVBoxLayout(group)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "角色", "活动类型", "目标时长", "今日已完成", "进度", "操作"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 100)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        parent_layout.addWidget(group)

    def _update_character_combo(self):
        """Update the character combo box with current characters"""
        self.character_combo.clear()
        for char in self.activity_characters:
            self.character_combo.addItem(char.name, char.name)

    def load_data(self):
        """Load tasks from persistence and update UI"""
        self.tasks = self.task_persistence.load_tasks()
        self.refresh_data()

    def refresh_data(self):
        """Refresh the display with latest data"""
        # Get current completion from activity records
        completions = self.task_persistence.get_today_completion(self.tasks, self.activity_characters)
        completed, total, percent = self.task_persistence.get_completion_stats(self.tasks, self.activity_characters)

        # Update summary
        if total == 0:
            self.summary_label.setText("<b>今日还没有设置任何每日任务</b>")
        else:
            summary_text = f"今日进度: {completed}/{total} 任务已完成 ({percent:.0f}%)"
            if percent >= 100:
                summary_text = f"✅ {summary_text} - 今日全部任务已完成！"
            self.summary_label.setText(f"<b>{summary_text}</b>")

        # Update table
        self._update_table(completions)

    def _update_table(self, completions: List[DailyTaskCompletion]):
        """Update the tasks table with current completion data"""
        self.table.setRowCount(len(completions))

        for row, completion in enumerate(completions):
            # Character name
            self.table.setItem(row, 0, QTableWidgetItem(completion.character_name))

            # Activity type
            type_name = "搬砖" if completion.activity_type == ActivityType.GRINDING else "蹲星"
            self.table.setItem(row, 1, QTableWidgetItem(type_name))

            # Target
            target_hours = completion.target_minutes / 60
            self.table.setItem(row, 2, QTableWidgetItem(f"{completion.target_minutes} 分钟 ({target_hours:.1f} 小时)"))

            # Actual
            actual_hours = completion.actual_minutes / 60
            self.table.setItem(row, 3, QTableWidgetItem(f"{completion.actual_minutes} 分钟 ({actual_hours:.1f} 小时)"))

            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setMaximum(100)
            progress_bar.setValue(int(completion.progress_percent))

            if completion.completed:
                progress_bar.setStyleSheet("""
                    QProgressBar {
                        background-color: #2d2d2d;
                        border-radius: 4px;
                        border: none;
                        text-align: center;
                        color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #28a745;
                        border-radius: 4px;
                    }
                """)
            else:
                progress_bar.setStyleSheet("""
                    QProgressBar {
                        background-color: #2d2d2d;
                        border-radius: 4px;
                        border: none;
                        text-align: center;
                        color: white;
                    }
                    QProgressBar::chunk {
                        background-color: #1f6feb;
                        border-radius: 4px;
                    }
                """)

            progress_bar.setFormat(f"{completion.progress_percent:.0f}%")
            self.table.setCellWidget(row, 4, progress_bar)

            # Delete button
            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a02c2c;
                    color: white;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #661a1a;
                }
            """)
            delete_btn.clicked.connect(lambda checked, r=row: self._delete_task(r))
            self.table.setCellWidget(row, 5, delete_btn)

    def _add_task(self):
        """Add a new task"""
        character_name = self.character_combo.currentData()
        if not character_name:
            QMessageBox.warning(self, "提示", "请先选择一个角色")
            return

        activity_type = self.type_combo.currentData()
        target_minutes = self.target_spin.value()
        enabled = self.enabled_check.isChecked()

        # Check if this (character + type) already exists
        for task in self.tasks:
            if task.character_name == character_name and task.activity_type == activity_type:
                QMessageBox.warning(self, "提示", "该角色的这个活动类型已经存在每日任务")
                return

        new_task = DailyTask(
            character_name=character_name,
            activity_type=activity_type,
            target_minutes=target_minutes,
            enabled=enabled
        )
        self.tasks.append(new_task)
        self._save_tasks()
        self.refresh_data()
        QMessageBox.information(self, "成功", "每日任务添加成功")

    def _delete_task(self, row: int):
        """Delete a task from the table"""
        # Get completion at this row to find the task
        completions = self.task_persistence.get_today_completion(self.tasks, self.activity_characters)
        if row < 0 or row >= len(completions):
            return

        completion = completions[row]
        # Find and remove from tasks list
        self.tasks = [
            t for t in self.tasks
            if not (
                t.enabled and
                t.character_name == completion.character_name and
                t.activity_type == completion.activity_type
            )
        ]
        self._save_tasks()
        self.refresh_data()

    def _save_tasks(self):
        """Save current tasks to file"""
        self.task_persistence.save_tasks(self.tasks)

    def save_data(self):
        """Save data - called on window close by main window"""
        self._save_tasks()

    def update_data(self, new_characters: List[ActivityCharacter] = None):
        """Update data when activity records change
        If new_characters is provided, updates internal character list (for when characters added/removed)
        """
        if new_characters is not None:
            self.activity_characters = new_characters
        # Reload characters if needed
        self.refresh_data()

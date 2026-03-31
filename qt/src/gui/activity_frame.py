"""Activity statistics frame (grinding + star waiting)"""
from datetime import date
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QTabWidget, QProgressBar, QDialog, QSpinBox,
    QDoubleSpinBox, QLineEdit, QMessageBox, QGroupBox, QScrollArea,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.core.models import (
    ActivityType, ActivityRecord, ActivityCharacter, ActivityGoal,
    SuggestionUserSettings, ActivitySuggestion
)
from src.data.persistence import ActivityPersistence
from .suggestion_calculator import calculate_suggestion_for_all


class ActivityFrame(QWidget):
    """Activity statistics frame - supports both grinding and star waiting"""

    def __init__(self, persistence: ActivityPersistence):
        super().__init__()
        self.persistence = persistence
        self.characters: List[ActivityCharacter] = []
        self.current_character: Optional[ActivityCharacter] = None
        # Global suggestion settings (not per-character)
        self.global_suggestion_settings = SuggestionUserSettings()
        # Sorting state for each activity type
        self._sort_state = {
            ActivityType.GRINDING: ("日期", True),
            ActivityType.STAR_WAITING: ("日期", True),
        }

        self._stats_labels = {}
        self._progress_bars = {}
        self._tables = {}

        self._create_widgets()
        self.load_data()

    def _create_widgets(self):
        """Create the widgets"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Left side - character selection
        left_group = QGroupBox("🎭 角色列表")
        left_group.setFont(QFont("Segoe UI", 16, QFont.Bold))
        left_layout = QVBoxLayout(left_group)
        left_layout.setSpacing(6)
        left_group.setFixedWidth(200)

        self.character_list = QListWidget()
        self.character_list.itemSelectionChanged.connect(self._on_character_select)
        left_layout.addWidget(self.character_list)

        add_btn = QPushButton("+ 添加角色")
        add_btn.clicked.connect(self.add_character)
        left_layout.addWidget(add_btn)

        del_btn = QPushButton("- 删除角色")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc3333;
            }
            QPushButton:hover {
                background-color: #aa2222;
            }
        """)
        del_btn.clicked.connect(self.delete_character)
        left_layout.addWidget(del_btn)

        layout.addWidget(left_group)

        # Right side - stats and tabs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Tab view
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Segoe UI", 14))

        # Add tabs
        self._build_activity_tab(ActivityType.GRINDING, "搬砖")
        self._build_activity_tab(ActivityType.STAR_WAITING, "蹲星")

        right_layout.addWidget(self.tab_widget, 1)

        # Bottom - suggestion section
        suggestion_group = QGroupBox("活动安排建议")
        suggestion_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        suggestion_layout = QVBoxLayout(suggestion_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        settings_btn = QPushButton("建议设置")
        settings_btn.setFixedWidth(120)
        settings_btn.clicked.connect(self.open_suggestion_settings)
        btn_layout.addWidget(settings_btn)

        get_suggestion_btn = QPushButton("获取建议")
        get_suggestion_btn.setFixedWidth(120)
        get_suggestion_btn.clicked.connect(self.calculate_and_show_suggestion)
        btn_layout.addWidget(get_suggestion_btn)

        suggestion_layout.addLayout(btn_layout)

        # Suggestion text
        self.suggestion_label = QLabel("点击上方按钮获取安排建议")
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setFont(QFont("Segoe UI", 12))
        self.suggestion_label.setAlignment(Qt.AlignLeft)
        suggestion_layout.addWidget(self.suggestion_label)

        right_layout.addWidget(suggestion_group)

        layout.addWidget(right_widget, 1)

        self.setLayout(layout)

    def _build_activity_tab(self, activity_type: ActivityType, tab_name: str):
        """Build a tab for an activity"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # Statistics cards
        stats_group = QGroupBox("统计信息")
        stats_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(15)
        stats_layout.setContentsMargins(15, 15, 15, 10)

        value_name = "银币" if activity_type == ActivityType.GRINDING else "蹲星成功数量"
        full_value_name = "今日获得银币" if activity_type == ActivityType.GRINDING else "今日蹲星成功数量"
        remaining_value_name = "剩余目标银币" if activity_type == ActivityType.GRINDING else "剩余蹲星成功数量"

        if activity_type == ActivityType.GRINDING:
            stats = [
                (full_value_name, "today_value", "0"),
                ("今日搬砖时长", "today_duration", "0分钟"),
                (f"总计获得银币", "total_value", "0"),
                ("总计搬砖时长", "total_duration", "0分钟"),
                (remaining_value_name, "remaining_value", "0"),
                ("已获得收入/总收入", "income_progress", "0 / 0"),
            ]
        else:
            stats = [
                (full_value_name, "today_value", "0"),
                ("今日蹲星时长", "today_duration", "0分钟"),
                (f"总计蹲星成功数量", "total_value", "0"),
                ("总计蹲星时长", "total_duration", "0分钟"),
                (remaining_value_name, "remaining_value", "0"),
                ("已获得收入/总收入", "income_progress", "0 / 0"),
            ]

        if activity_type not in self._stats_labels:
            self._stats_labels[activity_type] = {}

        for i, (label_text, key, default) in enumerate(stats):
            row = i // 3
            col = i % 3
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(10, 10, 10, 10)
            label_title = QLabel(label_text)
            label_title.setFont(QFont("Segoe UI", 14))
            label_title.setAlignment(Qt.AlignCenter)
            container_layout.addWidget(label_title)
            label_value = QLabel(default)
            label_value.setFont(QFont("Segoe UI", 16, QFont.Bold))
            label_value.setAlignment(Qt.AlignCenter)
            container_layout.addWidget(label_value)
            stats_layout.addWidget(container, row, col)
            self._stats_labels[activity_type][key] = label_value

        layout.addWidget(stats_group)

        # Progress bars
        progress_group = QGroupBox("目标进度")
        progress_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(20, 10, 20, 10)

        # Value progress
        value_progress = QProgressBar()
        value_progress.setRange(0, 100)
        value_progress.setValue(0)
        value_progress.setTextVisible(False)
        progress_layout.addWidget(value_progress)
        value_label = QLabel(f"{value_name}: 0%")
        value_label.setFont(QFont("Segoe UI", 12))
        progress_layout.addWidget(value_label)

        # Duration progress
        duration_progress = QProgressBar()
        duration_progress.setRange(0, 100)
        duration_progress.setValue(0)
        duration_progress.setTextVisible(False)
        progress_layout.addWidget(duration_progress)
        duration_label = QLabel(f"时长: 0%")
        duration_label.setFont(QFont("Segoe UI", 12))
        progress_layout.addWidget(duration_label)

        # Set goal button
        set_goal_btn = QPushButton("设置目标")
        set_goal_btn.setFixedWidth(120)
        set_goal_btn.clicked.connect(lambda: self.open_set_goal(activity_type))
        progress_layout.addWidget(set_goal_btn, alignment=Qt.AlignHCenter)

        self._progress_bars[activity_type] = {
            'value': (value_progress, value_label),
            'duration': (duration_progress, duration_label)
        }

        layout.addWidget(progress_group)

        # Data table
        table_group = QGroupBox("今日记录")
        table_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(10, 10, 10, 10)

        if activity_type == ActivityType.GRINDING:
            columns = ["日期", "银币", "时长(分钟)"]
        else:
            columns = ["日期", "成功数量", "时长(分钟)"]

        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.setMinimumHeight(200)

        table_layout.addWidget(table)

        # Add record button
        add_record_btn = QPushButton("+ 添加记录")
        add_record_btn.setFixedWidth(100)
        add_record_btn.clicked.connect(lambda: self.add_record(activity_type))
        table_layout.addWidget(add_record_btn, alignment=Qt.AlignHCenter)

        # Save button
        save_btn = QPushButton("保存数据")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_data)
        table_layout.addWidget(save_btn, alignment=Qt.AlignHCenter)

        self._tables[activity_type] = table

        layout.addWidget(table_group, 1)

        self.tab_widget.addTab(tab, tab_name)

    def load_data(self):
        """Load data from persistence"""
        result = self.persistence.load_characters()
        if isinstance(result, tuple) and len(result) == 2:
            self.characters, loaded_global_settings = result
            # If we have loaded global settings, use it
            if loaded_global_settings:
                self.global_suggestion_settings = loaded_global_settings
        else:
            # Backward compatibility
            self.characters = result
        self.update_character_list()
        if self.characters:
            self.character_list.setCurrentRow(0)
            self._on_character_select()

    def update_data(self):
        """Refresh data from storage and update display"""
        self.load_data()

    def update_character_list(self):
        """Update the character listbox"""
        self.character_list.clear()
        for char in self.characters:
            item = QListWidgetItem(char.name)
            item.setData(Qt.UserRole, char)
            self.character_list.addItem(item)

    def _on_character_select(self):
        """Handle character selection"""
        items = self.character_list.selectedItems()
        if not items:
            return
        item = items[0]
        self.current_character = item.data(Qt.UserRole)
        self.update_all_displays()

    def update_all_displays(self):
        """Update display for both activities"""
        if not self.current_character:
            return
        self.update_display(ActivityType.GRINDING)
        self.update_display(ActivityType.STAR_WAITING)

    def update_display(self, activity_type: ActivityType):
        """Update the display with current character data"""
        if not self.current_character:
            return

        value_name = "银币" if activity_type == ActivityType.GRINDING else "成功数量"
        total_value, total_duration, remaining_value = self.current_character.calculate_totals(activity_type)
        today_value, today_duration = self.current_character.calculate_today_totals(activity_type)

        # Update stats
        stats_labels = self._stats_labels[activity_type]
        stats_labels['today_value'].setText(f"{today_value:,}")
        stats_labels['today_duration'].setText(f"{today_duration}分钟")
        stats_labels['total_value'].setText(f"{total_value:,}")
        stats_labels['total_duration'].setText(f"{total_duration}分钟")
        stats_labels['remaining_value'].setText(f"{remaining_value:,}")

        # Calculate income progress
        goal = (
            self.current_character.grinding_goal
            if activity_type == ActivityType.GRINDING
            else self.current_character.star_waiting_goal
        )
        if goal and goal.total_income > 0:
            total_income = goal.total_income
            earned_income = 0
            if activity_type == ActivityType.GRINDING:
                if self.current_character.grinding_goal:
                    total_value_g, _, _ = self.current_character.calculate_totals(ActivityType.GRINDING)
                    if self.current_character.grinding_goal.target_value > 0:
                        progress = total_value_g / self.current_character.grinding_goal.target_value
                        progress = min(progress, 1.0)
                        earned_income = int(self.current_character.grinding_goal.total_income * progress)
            else:
                if self.current_character.star_waiting_goal:
                    total_value_s, _, _ = self.current_character.calculate_totals(ActivityType.STAR_WAITING)
                    if self.current_character.star_waiting_goal.target_value > 0:
                        progress = total_value_s / self.current_character.star_waiting_goal.target_value
                        progress = min(progress, 1.0)
                        earned_income = int(self.current_character.star_waiting_goal.total_income * progress)
            stats_labels['income_progress'].setText(f"{earned_income:,} / {total_income:,}")
        else:
            stats_labels['income_progress'].setText("0 / 0")

        # Update progress
        progress_value, progress_duration = self.current_character.calculate_progress(activity_type)
        progress_bars = self._progress_bars[activity_type]
        value_progress, value_label = progress_bars['value']
        duration_progress, duration_label = progress_bars['duration']

        if progress_value is not None:
            value_progress.setValue(int(progress_value * 100))
            value_label.setText(f"{value_name}: {int(progress_value * 100)}%")
        else:
            value_progress.setValue(0)
            value_label.setText(f"{value_name}: 未设置目标")

        if progress_duration is not None:
            duration_progress.setValue(int(progress_duration * 100))
            duration_label.setText(f"时长: {int(progress_duration * 100)}%")
        else:
            duration_progress.setValue(0)
            duration_label.setText(f"时长: 未设置目标")

        # Update table
        table = self._tables[activity_type]
        table.setRowCount(0)
        today = date.today()

        # Collect all today records for this activity
        records = [
            record for record in self.current_character.records
            if record.date == today and record.activity_type == activity_type
        ]

        # Sort based on current sort settings
        sort_col, sort_asc = self._sort_state[activity_type]
        if sort_col == "日期":
            key_func = lambda r: r.date
        elif sort_col == "银币" or sort_col == "成功数量":
            if activity_type == ActivityType.GRINDING:
                key_func = lambda r: r.silver_count
            else:
                key_func = lambda r: r.success_count
        elif sort_col == "时长(分钟)":
            key_func = lambda r: r.duration_minutes
        else:
            key_func = lambda r: r.date

        records.sort(key=key_func, reverse=not sort_asc)

        # Insert sorted records
        row = 0
        for record in records:
            if activity_type == ActivityType.GRINDING:
                value = record.silver_count
            else:
                value = record.success_count
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(record.date.strftime("%Y-%m-%d")))
            table.setItem(row, 1, QTableWidgetItem(f"{value:,}"))
            table.setItem(row, 2, QTableWidgetItem(str(record.duration_minutes)))
            row += 1

    def add_character(self):
        """Add a new character"""
        dialog = AddCharacterDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.get_name()
            if name.strip():
                char = ActivityCharacter(name.strip())
                self.characters.append(char)
                self.update_character_list()
                self.character_list.setCurrentRow(len(self.characters) - 1)
                self._on_character_select()
                self.save_data()

    def delete_character(self):
        """Delete selected character"""
        if not self.current_character:
            return
        confirm = QMessageBox.question(
            self, "确认删除",
            f"确定要删除角色 {self.current_character.name} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.characters.remove(self.current_character)
            self.current_character = None
            self.update_character_list()
            self.save_data()
            self.update_all_displays()

    def open_set_goal(self, activity_type: ActivityType):
        """Open dialog to set activity goal"""
        if not self.current_character:
            QMessageBox.information(self, "提示", "请先在左侧选择一个角色")
            return
        current_goal = (
            self.current_character.grinding_goal
            if activity_type == ActivityType.GRINDING
            else self.current_character.star_waiting_goal
        )
        dialog = SetGoalDialog(self, activity_type, current_goal)
        dialog.goal_set.connect(self._on_set_goal_done)
        dialog.exec()

    def _on_set_goal_done(self, activity_type: ActivityType, target_value, target_duration, total_income):
        """Callback after setting goal"""
        if not self.current_character:
            return
        if target_value <= 0 and target_duration <= 0:
            goal = None
        else:
            goal = ActivityGoal(
                activity_type=activity_type,
                target_value=target_value,
                target_duration=target_duration,
                total_income=total_income
            )

        if activity_type == ActivityType.GRINDING:
            self.current_character.grinding_goal = goal
        else:
            self.current_character.star_waiting_goal = goal

        self.update_display(activity_type)
        self.save_data()

    def add_record(self, activity_type: ActivityType):
        """Add a new record for today"""
        if self.current_character is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一个角色")
            return
        dialog = AddRecordDialog(self, activity_type)
        dialog.record_added.connect(self._on_add_record_done)
        dialog.exec()

    def _on_add_record_done(self, activity_type: ActivityType, value, duration_minutes):
        """Callback after adding record"""
        try:
            char = self.current_character
            if not char:
                QMessageBox.information(self, "提示", "请先在左侧选择一个角色")
                return
            if activity_type == ActivityType.GRINDING:
                record = ActivityRecord(
                    date=date.today(),
                    activity_type=activity_type,
                    silver_count=value,
                    duration_minutes=duration_minutes
                )
            else:
                record = ActivityRecord(
                    date=date.today(),
                    activity_type=activity_type,
                    success_count=value,
                    duration_minutes=duration_minutes
                )
            char.add_record(record)
            self.update_display(activity_type)
            self.save_data()
        except Exception as e:
            QMessageBox.warning(self, "添加记录失败", f"错误: {str(e)}")

    def open_suggestion_settings(self):
        """Open global suggestion settings dialog"""
        dialog = SuggestionSettingsDialog(self, self.global_suggestion_settings)
        dialog.settings_changed.connect(self._on_suggestion_settings_done)
        dialog.exec()

    def _on_suggestion_settings_done(self, new_settings: SuggestionUserSettings):
        """Callback when suggestion settings updated"""
        self.global_suggestion_settings = new_settings
        self.save_data()

    def calculate_and_show_suggestion(self):
        """Calculate and show the suggestion based on all characters"""
        if not self.characters:
            self.suggestion_label.setText("没有角色，无法生成建议")
            return

        # Check if any character has goals set
        has_any_goal = any(
            char.grinding_goal or char.star_waiting_goal
            for char in self.characters
        )
        if not has_any_goal:
            self.suggestion_label.setText("没有设置任何目标，无法生成建议\n请在各角色中设置搬砖/蹲星目标")
            return

        suggestion = calculate_suggestion_for_all(self.characters, self.global_suggestion_settings)
        if not suggestion:
            self.suggestion_label.setText("所有目标已完成！恭喜！")
            return

        text = (
            f"【全部角色汇总建议】\n"
            f"每日安排:\n"
            f"  搬砖: {suggestion.daily_grinding_minutes:.1f} 分钟/天\n"
            f"  蹲星: {suggestion.daily_star_waiting_minutes:.1f} 分钟/天\n"
            f"预计还需要 {suggestion.estimated_days_remaining:.1f} 天完成全部目标\n"
            f"预计剩余总收入: {suggestion.estimated_total_income:,} 人民币\n"
            f"\n{suggestion.recommendation}"
        )
        self.suggestion_label.setText(text)

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_characters(self.characters, self.global_suggestion_settings)


class AddCharacterDialog(QDialog):
    """Dialog to add a new character"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加角色")
        self.setFixedSize(300, 150)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("角色名称"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #888888;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(btn_layout)

    def accept(self):
        """Override accept to validate input"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "角色名称不能为空")
            return
        super().accept()

    def get_name(self):
        """Get the entered name"""
        return self.name_edit.text().strip()


class SetGoalDialog(QDialog):
    """Dialog to set activity goal"""

    goal_set = Signal(object, object, object, object)

    def __init__(self, parent, activity_type: ActivityType, current_goal: Optional[ActivityGoal], parent_widget=None):
        super().__init__(parent or parent_widget)
        self.activity_type = activity_type
        value_name = "银币数量" if activity_type == ActivityType.GRINDING else "成功数量"

        self.setWindowTitle("设置目标")
        self.setFixedSize(380, 320)
        self.setModal(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        layout.addWidget(QLabel(f"目标{value_name}"))
        self.value_edit = QLineEdit()
        if current_goal:
            self.value_edit.setText(str(current_goal.target_value))
        layout.addWidget(self.value_edit)

        layout.addWidget(QLabel("目标时长(分钟)"))
        self.duration_edit = QLineEdit()
        if current_goal:
            self.duration_edit.setText(str(current_goal.target_duration))
        layout.addWidget(self.duration_edit)

        layout.addWidget(QLabel("完成总收入(人民币)"))
        self.income_edit = QLineEdit()
        if current_goal:
            self.income_edit.setText(str(current_goal.total_income))
        layout.addWidget(self.income_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self.confirm)
        btn_layout.addWidget(ok_btn)

        clear_btn = QPushButton("清除目标")
        clear_btn.setFixedWidth(90)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc3333;
            }
            QPushButton:hover {
                background-color: #aa2222;
            }
        """)
        clear_btn.clicked.connect(self.clear)
        btn_layout.addWidget(clear_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #888888;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def _parse_int(self, text: str) -> int:
        """Extract only digits from input, supports both half-width and full-width digits"""
        try:
            if not text:
                return 0
            result_digits = []
            for c in str(text):
                code = ord(c)
                # ASCII half-width digits 0-9: codes 48-57
                if 48 <= code <= 57:
                    result_digits.append(c)
                # Full-width digits ０-９: codes 0xFF10-0xFF19
                elif 0xFF10 <= code <= 0xFF19:
                    ascii_code = code - 0xFF10 + 48
                    result_digits.append(chr(ascii_code))
            if not result_digits:
                return 0
            return max(0, int(''.join(result_digits)))
        except Exception:
            return 0

    def confirm(self):
        """Confirm and set goal"""
        try:
            target_value = self._parse_int(self.value_edit.text())
            target_duration = self._parse_int(self.duration_edit.text())
            total_income = self._parse_int(self.income_edit.text())

            if target_value >= 0 and target_duration >= 0 and total_income >= 0:
                self.goal_set.emit(self.activity_type, target_value, target_duration, total_income)
                self.accept()
            else:
                QMessageBox.warning(self, "输入错误", "数值不能为负数，请重新输入")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数字")

    def clear(self):
        """Clear goal"""
        self.goal_set.emit(self.activity_type, 0, 0, 0)
        self.accept()


class AddRecordDialog(QDialog):
    """Dialog to add a new activity record"""

    record_added = Signal(object, object, object)

    def __init__(self, parent, activity_type: ActivityType):
        super().__init__(parent)
        self.activity_type = activity_type
        value_name = "银币数量" if activity_type == ActivityType.GRINDING else "成功数量"
        default_value = 1000000 if activity_type == ActivityType.GRINDING else 1

        self.setWindowTitle("添加记录")
        self.setFixedSize(350, 250)
        self.setModal(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        today_label = QLabel(f"日期: {date.today().strftime('%Y-%m-%d')}")
        today_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(today_label)

        layout.addWidget(QLabel(value_name))
        self.value_edit = QLineEdit()
        self.value_edit.setText(str(default_value))
        layout.addWidget(self.value_edit)

        layout.addWidget(QLabel("时长(分钟)"))
        self.duration_edit = QLineEdit()
        self.duration_edit.setText("120")
        layout.addWidget(self.duration_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self.confirm)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #888888;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def _clean_digits(self, text: str) -> int:
        """Extract only digits from input text"""
        try:
            if not text:
                return 0
            result_digits = []
            for c in str(text):
                code = ord(c)
                if 48 <= code <= 57:
                    result_digits.append(c)
                elif 0xFF10 <= code <= 0xFF19:
                    ascii_code = code - 0xFF10 + 48
                    result_digits.append(chr(ascii_code))
            if not result_digits:
                return 0
            result = int(''.join(result_digits))
            return max(0, result)
        except Exception:
            return 0

    def confirm(self):
        """Confirm and add record"""
        try:
            value = self._clean_digits(self.value_edit.text())
            duration = self._clean_digits(self.duration_edit.text())
            value = max(0, value)
            duration = max(0, duration)

            if value <= 0 and duration <= 0:
                QMessageBox.warning(self, "输入错误", "数值和时长不能同时为0，请至少输入一项大于0的值")
                return

            self.record_added.emit(self.activity_type, value, duration)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "添加记录失败", f"错误: {str(e)}")


class SuggestionSettingsDialog(QDialog):
    """Dialog for suggestion settings"""

    settings_changed = Signal(object)

    def __init__(self, parent, current_settings: SuggestionUserSettings):
        super().__init__(parent)
        self.setWindowTitle("建议设置")
        self.setFixedSize(400, 300)
        self.setModal(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        layout.addWidget(QLabel("每日总活动时长(小时)"))
        self.daily_total_edit = QLineEdit()
        self.daily_total_edit.setText(str(current_settings.daily_total_hours))
        layout.addWidget(self.daily_total_edit)

        layout.addWidget(QLabel("同时可进行搬砖活动数量"))
        self.grinding_concurrent_edit = QLineEdit()
        self.grinding_concurrent_edit.setText(str(current_settings.grinding_concurrent))
        layout.addWidget(self.grinding_concurrent_edit)

        layout.addWidget(QLabel("同时可进行蹲星活动数量"))
        self.star_concurrent_edit = QLineEdit()
        self.star_concurrent_edit.setText(str(current_settings.star_waiting_concurrent))
        layout.addWidget(self.star_concurrent_edit)

        layout.addWidget(QLabel("切换活动需要时间(分钟)"))
        self.switch_edit = QLineEdit()
        self.switch_edit.setText(str(current_settings.switch_minutes))
        layout.addWidget(self.switch_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(80)
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #888888;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def save(self):
        """Save the settings"""
        try:
            daily = float(self.daily_total_edit.text().strip())
            grinding = int(self.grinding_concurrent_edit.text().strip())
            star = int(self.star_concurrent_edit.text().strip())
            switch = int(self.switch_edit.text().strip())
            if daily > 0 and grinding > 0 and star > 0 and switch >= 0:
                new_settings = SuggestionUserSettings(
                    daily_total_hours=daily,
                    grinding_concurrent=grinding,
                    star_waiting_concurrent=star,
                    switch_minutes=switch
                )
                self.settings_changed.emit(new_settings)
                self.accept()
            else:
                QMessageBox.warning(self, "输入错误", "数值必须大于0，请重新输入")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数字")

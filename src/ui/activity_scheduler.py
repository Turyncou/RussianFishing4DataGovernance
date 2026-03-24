"""Activity Scheduler UI widget - shows recommendations"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, Qt.ConnectionType, pyqtSlot
from activity_scheduler import OptimizationResults
from src.core.data_manager import DataManager
from src.core.activity_scheduler import ActivitySchedulerIntegration


class ActivitySchedulerWidget(QWidget):
    """Activity Recommendation widget - integrates the activity scheduler"""

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.integration = ActivitySchedulerIntegration()

        # Load from data files
        data_dir = data_manager.data_dir
        activities_path = str(data_dir / "activities.csv")
        config_path = str(data_dir / "user.json")

        # Try to load from files (they might not exist yet)
        self.integration.load_from_files(activities_path, config_path)

        # Start watching for changes - auto-refresh when files modified
        def on_data_changed(results: OptimizationResults):
            # Use Qt.InvokeQueuedConnection to run refresh on main thread
            QMetaObject.invokeMethod(
                self, "refresh", Qt.ConnectionType.QueuedConnection
            )

        self.integration.start_watching(on_data_changed, activities_path, config_path)

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)

        # Activities table
        self.activities_table = QTableWidget()
        self.activities_table.setColumnCount(4)
        self.activities_table.setHorizontalHeaderLabels(["名称", "类型", "时长(分钟)", "价值"])
        self.activities_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(QLabel("活动列表:"))
        layout.addWidget(self.activities_table)

        # User config display
        config_group = QGroupBox("用户配置")
        config_layout = QVBoxLayout(config_group)
        self.config_label = QLabel("最大并行B: N/A | 总可用时长: N/A 小时")
        config_layout.addWidget(self.config_label)
        layout.addWidget(config_group)

        # Controls
        controls_layout = QHBoxLayout()

        self.refresh_button = QPushButton("刷新推荐")
        self.refresh_button.clicked.connect(self.refresh)
        controls_layout.addWidget(self.refresh_button)

        layout.addLayout(controls_layout)

        # Results - Maximum Gain
        max_group = QGroupBox("最大收益推荐")
        max_layout = QVBoxLayout(max_group)
        self.max_result_text = QTextEdit()
        self.max_result_text.setReadOnly(True)
        self.max_result_text.setMaximumHeight(200)
        max_layout.addWidget(self.max_result_text)
        layout.addWidget(max_group)

        # Results - Balanced
        balanced_group = QGroupBox("均衡收益推荐")
        balanced_layout = QVBoxLayout(balanced_group)
        self.balanced_result_text = QTextEdit()
        self.balanced_result_text.setReadOnly(True)
        self.balanced_result_text.setMaximumHeight(200)
        balanced_layout.addWidget(self.balanced_result_text)
        layout.addWidget(balanced_group)

        self.setLayout(layout)

    @pyqtSlot()
    def refresh(self):
        """Refresh display"""
        # Update activities table
        activities = self.integration.get_activities()
        self.activities_table.setRowCount(len(activities))
        for row, act in enumerate(activities):
            self.activities_table.setItem(row, 0, QTableWidgetItem(act["name"]))
            self.activities_table.setItem(row, 1, QTableWidgetItem(act["type"]))
            self.activities_table.setItem(row, 2, QTableWidgetItem(str(act["duration"])))
            self.activities_table.setItem(row, 3, QTableWidgetItem(str(act["value"])))

        # Update config
        config = self.integration.get_user_config()
        if config:
            self.config_label.setText(
                f"最大并行B: {config['max_concurrent_b']} | 总可用时长: {config['total_available_hours']} 小时"
            )
        else:
            self.config_label.setText("最大并行B: N/A | 总可用时长: N/A 小时")

        # Try to get recommendations
        try:
            results = self.integration.get_recommendations()

            # Format max gain
            max_text = f"总收益: {results.maximum_gain.total_value:.1f}\n"
            max_text += f"总时长: {results.maximum_gain.total_duration} 分钟\n"
            max_text += f"休息时间: {results.maximum_gain.rest_time} 分钟\n"
            max_text += "活动:\n"
            for i, item in enumerate(results.maximum_gain.schedule, 1):
                type_label = "A" if item.activity.type.value == "typeA" else "B"
                dur = item.end_time - item.start_time
                max_text += f"  {i}. [{type_label}] {item.activity.activity_name} - {dur} min\n"
            self.max_result_text.setText(max_text)

            # Format balanced
            balanced_text = f"总收益: {results.balanced.total_value:.1f}\n"
            balanced_text += f"总时长: {results.balanced.total_duration} 分钟\n"
            balanced_text += f"休息时间: {results.balanced.rest_time} 分钟\n"
            balanced_text += "活动:\n"
            for i, item in enumerate(results.balanced.schedule, 1):
                type_label = "A" if item.activity.type.value == "typeA" else "B"
                dur = item.end_time - item.start_time
                balanced_text += f"  {i}. [{type_label}] {item.activity.activity_name} - {dur} min\n"
            self.balanced_result_text.setText(balanced_text)

        except Exception as e:
            self.max_result_text.setText(f"获取推荐失败: {str(e)}\n\n请先添加活动和配置")
            self.balanced_result_text.setText("")

    def on_add_activity(self):
        # TODO: Add dialog for adding activity
        pass

    def closeEvent(self, event):
        """Stop watching when closed"""
        self.integration.stop_watching()
        super().closeEvent(event)

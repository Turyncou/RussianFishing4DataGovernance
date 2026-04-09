"""Data analysis page with practical actionable insights for RF4 players"""
from collections import defaultdict
from datetime import date, timedelta
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Configure matplotlib to use Chinese font
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QComboBox,
    QGroupBox, QGridLayout, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from src.data.persistence import ActivityPersistence
from src.core.models import ActivityType, ActivityCharacter


class StatisticsFrame(QWidget):
    """Data analysis page with practical insights for RF4 players"""

    def __init__(self, activity_persistence: ActivityPersistence):
        super().__init__()
        self.activity_persistence = activity_persistence
        self.animations = []
        self.characters = []
        self.global_settings = None

        # Filtered records for detail table
        self.all_records = []
        self.filtered_records = []

        self._create_widgets()
        self.refresh_plots()

    def _create_widgets(self):
        """Create the UI widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Title
        title = QLabel("📈 数据分析")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Summary overview container
        summary_container = self._create_summary_container()
        layout.addWidget(summary_container)

        # Tabbed interface
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Segoe UI", 14))

        # 1. 效率分析 - 核心功能（只保留排名，去掉趋势图）
        self._create_efficiency_tab()

        # 2. 目标进度 - 核心功能
        self._create_goal_progress_tab()

        # 3. 每日收入 - 用户最关注: 每天赚多少钱
        self._create_daily_income_tab()

        # 4. 任务完成统计 - 用户最关注: 任务每日完成情况
        self._create_task_completion_tab()

        # 5. 收益明细 - 查看详细记录
        self._create_detailed_records_tab()

        layout.addWidget(self.tab_widget, 1)

    def _create_summary_container(self):
        """Create the KPI summary container"""
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(5, 0, 5, 5)
        main_layout.setSpacing(8)

        # KPI row
        kpi_widget = QWidget()
        kpi_layout = QHBoxLayout(kpi_widget)
        kpi_layout.setSpacing(15)

        # Total Activities
        activities_layout = QVBoxLayout()
        activities_layout.addWidget(QLabel("总记录数:"))
        self.label_total_activities = QLabel("-")
        self.label_total_activities.setFont(QFont("Segoe UI", 14, QFont.Bold))
        activities_layout.addWidget(self.label_total_activities)
        kpi_layout.addLayout(activities_layout)

        # Total Silver
        silver_layout = QVBoxLayout()
        silver_layout.addWidget(QLabel("累计银币:"))
        self.label_total_silver = QLabel("-")
        self.label_total_silver.setFont(QFont("Segoe UI", 14, QFont.Bold))
        silver_layout.addWidget(self.label_total_silver)
        kpi_layout.addLayout(silver_layout)

        # Total Duration
        duration_layout = QVBoxLayout()
        duration_layout.addWidget(QLabel("累计时长:"))
        self.label_total_duration = QLabel("-")
        self.label_total_duration.setFont(QFont("Segoe UI", 14, QFont.Bold))
        duration_layout.addWidget(self.label_total_duration)
        kpi_layout.addLayout(duration_layout)

        # Average SPM
        spm_layout = QVBoxLayout()
        spm_layout.addWidget(QLabel("平均SPM:"))
        self.label_avg_spm = QLabel("-")
        self.label_avg_spm.setFont(QFont("Segoe UI", 14, QFont.Bold))
        spm_layout.addWidget(self.label_avg_spm)
        kpi_layout.addLayout(spm_layout)

        kpi_layout.addStretch()
        main_layout.addWidget(kpi_widget)

        # Date range selector
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("📅 时间范围:"))
        self.date_range_combo = QComboBox()
        self.date_range_combo.addItems(["全部数据", "最近 7 天", "最近 30 天", "最近 90 天"])
        self.date_range_combo.currentIndexChanged.connect(self.refresh_plots)
        self.date_range_combo.setFixedWidth(120)
        date_layout.addWidget(self.date_range_combo)

        # Refresh button
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setFixedWidth(70)
        refresh_btn.clicked.connect(self.refresh_plots)
        date_layout.addWidget(refresh_btn)

        date_layout.addStretch()
        main_layout.addLayout(date_layout)

        return container

    def _create_efficiency_tab(self):
        """Create efficiency analysis tab - only keep rankings"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # SPM ranking chart
        self.fig_spm = Figure(figsize=(8, 3.5), dpi=100)
        self.ax_spm = self.fig_spm.add_subplot(111)
        self.canvas_spm = FigureCanvas(self.fig_spm)
        layout.addWidget(self.canvas_spm)

        # Star per hour ranking chart
        self.fig_star = Figure(figsize=(8, 3.5), dpi=100)
        self.ax_star = self.fig_star.add_subplot(111)
        self.canvas_star = FigureCanvas(self.fig_star)
        layout.addWidget(self.canvas_star)

        self.tab_widget.addTab(tab, "⚡ 效率分析")

    def _create_goal_progress_tab(self):
        """Create goal progress tab with progress bars and completion forecast"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Scroll area for many characters
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        self.goal_layout = QVBoxLayout(scroll_content)
        self.goal_layout.setSpacing(8)

        # Will be populated in refresh_plots
        self.goal_progress_widgets = []

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        self.tab_widget.addTab(tab, "🎯 目标进度")


    def _create_detailed_records_tab(self):
        """Create detailed records tab with filterable table"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Filters
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("角色:"))
        self.char_filter_combo = QComboBox()
        self.char_filter_combo.addItem("全部")
        self.char_filter_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.char_filter_combo)

        filter_layout.addWidget(QLabel("活动类型:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItem("全部")
        self.type_filter_combo.addItem("搬砖")
        self.type_filter_combo.addItem("蹲星")
        self.type_filter_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.type_filter_combo)

        filter_layout.addStretch()

        self.record_count_label = QLabel("共 0 条记录")
        filter_layout.addWidget(self.record_count_label)

        layout.addLayout(filter_layout)

        # Table
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(7)
        self.records_table.setHorizontalHeaderLabels(["日期", "角色", "活动类型", "时长(分钟)", "银币", "星星数", "效率"])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.records_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.records_table.verticalHeader().setVisible(False)
        layout.addWidget(self.records_table)

        self.tab_widget.addTab(tab, "📋 收益明细")

    def _create_daily_trend_tab(self):
        """Create daily trend tab (retained from original)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        self.fig_daily = Figure(figsize=(8, 5), dpi=100)
        self.ax_daily = self.fig_daily.add_subplot(111)
        self.canvas_daily = FigureCanvas(self.fig_daily)
        layout.addWidget(self.canvas_daily)
        self.tab_widget.addTab(tab, "每日收益趋势")

    def _create_character_comparison_tab(self):
        """Create character comparison tab (retained from original)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        self.fig_char = Figure(figsize=(8, 5), dpi=100)
        self.ax_char = self.fig_char.add_subplot(111)
        self.canvas_char = FigureCanvas(self.fig_char)
        layout.addWidget(self.canvas_char)
        self.tab_widget.addTab(tab, "角色收益对比")

    def _create_type_distribution_tab(self):
        """Create activity type distribution tab (retained from original)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        self.fig_type = Figure(figsize=(6, 4), dpi=100)
        self.ax_type = self.fig_type.add_subplot(111)
        self.canvas_type = FigureCanvas(self.fig_type)
        layout.addWidget(self.canvas_type)
        self.tab_widget.addTab(tab, "活动类型分布")

    def _create_character_time_tab(self):
        """Create character time distribution tab (retained from original)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        self.fig_char_time = Figure(figsize=(6, 4), dpi=100)
        self.ax_char_time = self.fig_char_time.add_subplot(111)
        self.canvas_char_time = FigureCanvas(self.fig_char_time)
        layout.addWidget(self.canvas_char_time)
        self.tab_widget.addTab(tab, "角色时长分布")

    def _setup_axes_theme(self, ax):
        """Setup axes for current theme"""
        window = self.window()
        is_dark = True
        if hasattr(window, '_current_theme'):
            is_dark = (window._current_theme == "dark")
        if is_dark:
            ax.set_facecolor("#2b2b2b")
            if ax.figure is not None:
                ax.figure.set_facecolor("#2b2b2b")
            for spine in ax.spines.values():
                spine.set_color('white')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            ax.yaxis.label.set_color('white')
            ax.xaxis.label.set_color('white')
            if ax.title is not None:
                ax.title.set_color('white')
        else:
            ax.set_facecolor("#ffffff")
            if ax.figure is not None:
                ax.figure.set_facecolor("#ffffff")
            for spine in ax.spines.values():
                spine.set_color('black')
            ax.tick_params(axis='x', colors='black')
            ax.tick_params(axis='y', colors='black')
            ax.yaxis.label.set_color('black')
            ax.xaxis.label.set_color('black')
            if ax.title is not None:
                ax.title.set_color('black')

    def refresh_plots(self):
        """Refresh data and replay all animations"""
        # Stop existing animations
        for anim in self.animations:
            if anim is not None and anim.event_source is not None:
                anim.event_source.stop()
        self.animations.clear()

        self._load_data()
        self._update_summary_kpi()
        self._plot_efficiency()
        self._plot_goal_progress()
        self._plot_daily_income()
        self._plot_task_completion()
        self._apply_filters()

    def replay_animation(self):
        """Replay all animations"""
        self.refresh_plots()

    def _load_data(self):
        """Load data with date range filtering"""
        self.characters, self.global_settings = self.activity_persistence.load_all_characters()

        # Get date range selection
        range_text = self.date_range_combo.currentText()
        today = date.today()

        if range_text == "最近 7 天":
            cutoff = today - timedelta(days=7)
        elif range_text == "最近 30 天":
            cutoff = today - timedelta(days=30)
        elif range_text == "最近 90 天":
            cutoff = today - timedelta(days=90)
        else:  # 全部数据
            cutoff = date.min

        # Filter records by date and collect all records for detail table
        self.all_records = []
        for char in self.characters:
            for record in char.records:
                if record.date >= cutoff:
                    self.all_records.append({
                        'date': record.date,
                        'character': char.name,
                        'type': record.activity_type,
                        'duration': record.duration_minutes,
                        'silver': record.silver_count,
                        'success': record.success_count
                    })

        # Sort by date descending
        self.all_records.sort(key=lambda x: x['date'], reverse=True)
        self._update_filter_combos()
        self._apply_filters()

    def _update_summary_kpi(self):
        """Update summary KPI labels"""
        total_activities = len(self.all_records)
        total_silver = sum(r['silver'] for r in self.all_records)
        total_duration_min = sum(r['duration'] for r in self.all_records)

        self.label_total_activities.setText(str(total_activities))
        self.label_total_silver.setText(f"{total_silver:,}")

        if total_duration_min > 0:
            total_duration_hours = total_duration_min / 60
            self.label_total_duration.setText(f"{total_duration_hours:.1f}h")

            # Calculate average SPM from grinding activities
            grinding_records = [r for r in self.all_records if r['type'] == ActivityType.GRINDING]
            if grinding_records:
                total_grind_silver = sum(r['silver'] for r in grinding_records)
                total_grind_duration = sum(r['duration'] for r in grinding_records)
                if total_grind_duration > 0:
                    avg_spm = total_grind_silver / total_grind_duration
                    self.label_avg_spm.setText(f"{avg_spm:.2f}")
                else:
                    self.label_avg_spm.setText("-")
            else:
                self.label_avg_spm.setText("-")
        else:
            self.label_total_duration.setText("-")
            self.label_avg_spm.setText("-")

    def _update_filter_combos(self):
        """Update filter combos with available characters"""
        self.char_filter_combo.blockSignals(True)
        self.char_filter_combo.clear()
        self.char_filter_combo.addItem("全部")
        char_names = sorted(set(r['character'] for r in self.all_records))
        for name in char_names:
            self.char_filter_combo.addItem(name)
        self.char_filter_combo.blockSignals(False)

    def _apply_filters(self):
        """Apply filters to detailed records table"""
        char_filter = self.char_filter_combo.currentText()
        type_filter = self.type_filter_combo.currentText()

        self.filtered_records = self.all_records.copy()

        if char_filter != "全部":
            self.filtered_records = [r for r in self.filtered_records if r['character'] == char_filter]

        if type_filter != "全部":
            type_enum = ActivityType.GRINDING if type_filter == "搬砖" else ActivityType.STAR_WAITING
            self.filtered_records = [r for r in self.filtered_records if r['type'] == type_enum]

        self.record_count_label.setText(f"共 {len(self.filtered_records)} 条记录")
        self._populate_records_table()

    def _populate_records_table(self):
        """Populate the detailed records table"""
        self.records_table.setRowCount(len(self.filtered_records))

        for i, record in enumerate(self.filtered_records):
            # Date
            self.records_table.setItem(i, 0, QTableWidgetItem(record['date'].strftime('%Y-%m-%d')))
            # Character
            self.records_table.setItem(i, 1, QTableWidgetItem(record['character']))
            # Type
            type_text = "搬砖" if record['type'] == ActivityType.GRINDING else "蹲星"
            self.records_table.setItem(i, 2, QTableWidgetItem(type_text))
            # Duration
            self.records_table.setItem(i, 3, QTableWidgetItem(str(record['duration'])))
            # Silver
            self.records_table.setItem(i, 4, QTableWidgetItem(f"{record['silver']:,}"))
            # Success
            self.records_table.setItem(i, 5, QTableWidgetItem(str(record['success'])))
            # Efficiency
            if record['duration'] > 0:
                if record['type'] == ActivityType.GRINDING:
                    efficiency = record['silver'] / record['duration']
                    self.records_table.setItem(i, 6, QTableWidgetItem(f"{efficiency:.2f} SPM"))
                else:
                    efficiency = (record['success'] / record['duration']) * 60
                    self.records_table.setItem(i, 6, QTableWidgetItem(f"{efficiency:.2f} 星星/小时"))
            else:
                self.records_table.setItem(i, 6, QTableWidgetItem("-"))

    def _calculate_efficiency_data(self):
        """Calculate efficiency data for each character"""
        spm_data = []  # (name, spm, total_silver, total_duration)
        star_data = []  # (name, star_per_hour, total_stars, total_duration)

        for char in self.characters:
            # Calculate SPM for grinding
            total_silver = 0
            total_duration_grind = 0
            for record in char.records:
                if record.activity_type == ActivityType.GRINDING:
                    total_silver += record.silver_count
                    total_duration_grind += record.duration_minutes
            if total_duration_grind > 0:
                spm = total_silver / total_duration_grind
                spm_data.append((char.name, spm, total_silver, total_duration_grind))

            # Calculate star per hour for star waiting
            total_stars = 0
            total_duration_star = 0
            for record in char.records:
                if record.activity_type == ActivityType.STAR_WAITING:
                    total_stars += record.success_count
                    total_duration_star += record.duration_minutes
            if total_duration_star > 0:
                star_per_hour = (total_stars / total_duration_star) * 60
                star_data.append((char.name, star_per_hour, total_stars, total_duration_star))

        # Sort descending by efficiency
        spm_data.sort(key=lambda x: x[1], reverse=True)
        star_data.sort(key=lambda x: x[1], reverse=True)

        return spm_data, star_data

    def _calculate_average_daily_progress(self, char: ActivityCharacter, activity_type: ActivityType):
        """Calculate average daily progress (quantity) from historical data"""
        date_values = defaultdict(int)
        for record in char.records:
            if record.activity_type == activity_type:
                if activity_type == ActivityType.GRINDING:
                    date_values[record.date] += record.silver_count
                else:
                    date_values[record.date] += record.success_count

        if not date_values:
            return 0

        return sum(date_values.values()) / len(date_values)

    def _calculate_average_daily_duration(self, char: ActivityCharacter, activity_type: ActivityType):
        """Calculate average daily duration from historical data"""
        date_duration = defaultdict(int)
        for record in char.records:
            if record.activity_type == activity_type:
                date_duration[record.date] += record.duration_minutes

        if not date_duration:
            return 0

        return sum(date_duration.values()) / len(date_duration)

    def _plot_goal_progress(self):
        """Clear existing goal progress widgets and recreate
        Shows both quantity progress and duration progress since they have separate income
        """
        # Clear existing widgets
        for i in reversed(range(self.goal_layout.count())):
            item = self.goal_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.goal_progress_widgets.clear()

        has_any_goal = False

        for char in self.characters:
            # Handle all grinding goals
            for goal in char.grinding_goals:
                has_any_goal = True
                total_value, total_duration, _ = char.calculate_totals(ActivityType.GRINDING)

                # Calculate progress for both value (silver) and duration within this goal
                # For multiple independent goals, each goal has its own target
                # If target_value = 0 -> this is a duration-only goal, value progress is 100%
                # If target_duration = 0 -> this is a quantity-only goal, duration progress is 100%
                # All records contribute to both value and duration cumulative, so multiple goals progress simultaneously
                progress_value_pct = (total_value / goal.target_value * 100) if goal.target_value > 0 else 100
                progress_value_pct = min(progress_value_pct, 100)
                progress_duration_pct = (total_duration / goal.target_duration * 100) if goal.target_duration > 0 else 100
                progress_duration_pct = min(progress_duration_pct, 100)

                # Calculate remaining for this goal
                remaining_value = max(0, goal.target_value - total_value) if goal.target_value > 0 else 0
                remaining_duration = max(0, goal.target_duration - total_duration) if goal.target_duration > 0 else 0

                # Calculate estimated remaining days based on average daily progress
                # If it's a pure duration goal (target_value=0), predict based on remaining duration
                # If it's a pure quantity goal (target_duration=0), predict based on remaining quantity
                avg_daily_value = self._calculate_average_daily_progress(char, ActivityType.GRINDING)
                avg_daily_duration = self._calculate_average_daily_duration(char, ActivityType.GRINDING)
                remaining_days_text = ""

                if goal.target_value > 0 and remaining_value > 0:
                    # Predict based on quantity
                    if avg_daily_value > 0:
                        remaining_days = remaining_value / avg_daily_value
                        remaining_days_text = f"预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "无法预测"
                elif goal.target_duration > 0 and remaining_duration > 0:
                    # Predict based on duration (pure duration goal)
                    if avg_daily_duration > 0:
                        remaining_days = remaining_duration / avg_daily_duration
                        remaining_days_text = f"预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "无法预测"
                else:
                    remaining_days_text = "已完成"

                # Calculate remaining income based on both progresses
                remaining_income = 0
                if goal.total_income > 0:
                    # Both value and duration need to be completed
                    # Remaining income is proportional to the maximum of the two remaining progress
                    remaining_value_ratio = remaining_value / goal.target_value if goal.target_value > 0 else 0
                    remaining_duration_ratio = remaining_duration / goal.target_duration if goal.target_duration > 0 else 0
                    max_remaining_ratio = max(remaining_value_ratio, remaining_duration_ratio)
                    remaining_income = int(goal.total_income * max_remaining_ratio)

                group = QGroupBox(f"{char.name} - 搬砖目标 #{char.grinding_goals.index(goal) + 1}")
                layout = QVBoxLayout(group)
                layout.setSpacing(8)

                # Quantity (silver) progress bar
                progress_value_widget = QProgressBar()
                progress_value_widget.setMinimum(0)
                progress_value_widget.setMaximum(100)
                progress_value_widget.setValue(int(progress_value_pct))
                progress_value_widget.setTextVisible(True)
                progress_value_widget.setFormat(f"数量: {progress_value_pct:.1f}% - {total_value:,} / {goal.target_value:,} 银币")
                layout.addWidget(progress_value_widget)

                # Duration progress bar
                progress_duration_widget = QProgressBar()
                progress_duration_widget.setMinimum(0)
                progress_duration_widget.setMaximum(100)
                progress_duration_widget.setValue(int(progress_duration_pct))
                progress_duration_widget.setTextVisible(True)
                progress_duration_widget.setFormat(f"时长: {progress_duration_pct:.1f}% - {total_duration} / {goal.target_duration} 分钟")
                layout.addWidget(progress_duration_widget)

                # Build info text based on what's tracked
                info_parts = []
                if goal.target_value > 0:
                    info_parts.append(f"剩余银币: {remaining_value:,}")
                if goal.total_income > 0:
                    info_parts.append(f"剩余收入: {remaining_income:,}")
                info_parts.append(remaining_days_text)
                info_label = QLabel(" | ".join(info_parts))
                layout.addWidget(info_label)

                self.goal_layout.addWidget(group)
                self.goal_progress_widgets.append((group, progress_value_widget, progress_duration_widget, info_label))

            # Handle all star waiting goals
            for goal in char.star_waiting_goals:
                has_any_goal = True
                total_value, total_duration, _ = char.calculate_totals(ActivityType.STAR_WAITING)

                # Calculate progress for both value (star count) and duration within this goal
                progress_value_pct = (total_value / goal.target_value * 100) if goal.target_value > 0 else 100
                progress_value_pct = min(progress_value_pct, 100)
                progress_duration_pct = (total_duration / goal.target_duration * 100) if goal.target_duration > 0 else 100
                progress_duration_pct = min(progress_duration_pct, 100)

                # Calculate remaining for this goal
                remaining_value = max(0, goal.target_value - total_value) if goal.target_value > 0 else 0
                remaining_duration = max(0, goal.target_duration - total_duration) if goal.target_duration > 0 else 0

                # Calculate estimated remaining days
                # If it's a pure duration goal (target_value=0), predict based on remaining duration
                # If it's a pure quantity goal (target_duration=0), predict based on remaining quantity
                avg_daily_value = self._calculate_average_daily_progress(char, ActivityType.STAR_WAITING)
                avg_daily_duration = self._calculate_average_daily_duration(char, ActivityType.STAR_WAITING)
                remaining_days_text = ""

                if goal.target_value > 0 and remaining_value > 0:
                    # Predict based on quantity
                    if avg_daily_value > 0:
                        remaining_days = remaining_value / avg_daily_value
                        remaining_days_text = f"预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "无法预测"
                elif goal.target_duration > 0 and remaining_duration > 0:
                    # Predict based on duration (pure duration goal)
                    if avg_daily_duration > 0:
                        remaining_days = remaining_duration / avg_daily_duration
                        remaining_days_text = f"预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "无法预测"
                else:
                    remaining_days_text = "已完成"

                # Calculate remaining income based on both progresses
                remaining_income = 0
                if goal.total_income > 0:
                    remaining_value_ratio = remaining_value / goal.target_value if goal.target_value > 0 else 0
                    remaining_duration_ratio = remaining_duration / goal.target_duration if goal.target_duration > 0 else 0
                    max_remaining_ratio = max(remaining_value_ratio, remaining_duration_ratio)
                    remaining_income = int(goal.total_income * max_remaining_ratio)

                group = QGroupBox(f"{char.name} - 蹲星目标 #{char.star_waiting_goals.index(goal) + 1}")
                layout = QVBoxLayout(group)
                layout.setSpacing(8)

                # Quantity (star count) progress bar
                progress_value_widget = QProgressBar()
                progress_value_widget.setMinimum(0)
                progress_value_widget.setMaximum(100)
                progress_value_widget.setValue(int(progress_value_pct))
                progress_value_widget.setTextVisible(True)
                progress_value_widget.setFormat(f"数量: {progress_value_pct:.1f}% - {total_value} / {goal.target_value} 星星")
                layout.addWidget(progress_value_widget)

                # Duration progress bar
                progress_duration_widget = QProgressBar()
                progress_duration_widget.setMinimum(0)
                progress_duration_widget.setMaximum(100)
                progress_duration_widget.setValue(int(progress_duration_pct))
                progress_duration_widget.setTextVisible(True)
                progress_duration_widget.setFormat(f"时长: {progress_duration_pct:.1f}% - {total_duration} / {goal.target_duration} 分钟")
                layout.addWidget(progress_duration_widget)

                # Build info text based on what's tracked
                info_parts = []
                if goal.target_value > 0:
                    info_parts.append(f"剩余星星: {remaining_value}")
                if goal.total_income > 0:
                    info_parts.append(f"剩余收入: {remaining_income:,}")
                info_parts.append(remaining_days_text)
                info_label = QLabel(" | ".join(info_parts))
                layout.addWidget(info_label)

                self.goal_layout.addWidget(group)
                self.goal_progress_widgets.append((group, progress_value_widget, progress_duration_widget, info_label))

        if not has_any_goal:
            label = QLabel("暂无目标设置\n请在活动统计页面为角色设置目标")
            label.setAlignment(Qt.AlignCenter)
            window = self.window()
            is_dark = True
            if hasattr(window, '_current_theme'):
                is_dark = (window._current_theme == "dark")
            if is_dark:
                label.setStyleSheet("color: #aaaaaa;")
            else:
                label.setStyleSheet("color: #666666;")
            label.setFont(QFont("Segoe UI", 14))
            self.goal_layout.addWidget(label)

        self.goal_layout.addStretch()


    def _create_daily_income_tab(self):
        """Create daily income tab - user cares about how much earned each day"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)

        # Daily income chart
        self.fig_daily_income = Figure(figsize=(8, 5), dpi=100)
        self.ax_daily_income = self.fig_daily_income.add_subplot(111)
        self.canvas_daily_income = FigureCanvas(self.fig_daily_income)
        layout.addWidget(self.canvas_daily_income)

        # Cumulative chart
        self.fig_cumulative = Figure(figsize=(8, 4), dpi=100)
        self.ax_cumulative = self.fig_cumulative.add_subplot(111)
        self.canvas_cumulative = FigureCanvas(self.fig_cumulative)
        layout.addWidget(self.canvas_cumulative)

        self.tab_widget.addTab(tab, "💰 每日收入")

    def _create_task_completion_tab(self):
        """Create task completion tab - user cares about daily task completion"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)

        # Daily completion rate chart
        self.fig_completion = Figure(figsize=(8, 5), dpi=100)
        self.ax_completion = self.fig_completion.add_subplot(111)
        self.canvas_completion = FigureCanvas(self.fig_completion)
        layout.addWidget(self.canvas_completion)

        # Character completion summary table
        from PySide6.QtWidgets import QTableWidget
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["角色", "活动类型", "目标时长", "完成率"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.task_table.verticalHeader().setVisible(False)
        layout.addWidget(self.task_table)

        self.tab_widget.addTab(tab, "✅ 任务完成")

    def _plot_efficiency(self):
        """Plot efficiency analysis charts"""
        spm_data, star_data = self._calculate_efficiency_data()

        # Plot SPM ranking
        self.ax_spm.clear()
        self._setup_axes_theme(self.ax_spm)

        if spm_data:
            names = [d[0] for d in spm_data]
            values = [d[1] for d in spm_data]

            # Limit to top 10
            if len(names) > 10:
                names = names[:10]
                values = values[:10]

            # Reverse for bottom to top display
            names.reverse()
            values.reverse()

            self.final_spm_heights = values
            self.bars_spm = self.ax_spm.barh(names, [0] * len(names), color='#2196F3')
            self.ax_spm.set_title("SPM (银币每分钟) 排名", fontsize=12)
            self.ax_spm.set_xlabel("银币/分钟")

            def animate_spm(frame):
                progress = frame / 30
                for i, bar in enumerate(self.bars_spm):
                    bar.set_width(self.final_spm_heights[i] * progress)
                return list(self.bars_spm)

            anim = FuncAnimation(
                self.fig_spm, animate_spm, frames=30, interval=20, repeat=False, blit=False
            )
            self.animations.append(anim)
        else:
            self._show_no_data_in_ax(self.ax_spm)

        self.canvas_spm.draw()

        # Plot star per hour ranking
        self.ax_star.clear()
        self._setup_axes_theme(self.ax_star)

        if star_data:
            names = [d[0] for d in star_data]
            values = [d[1] for d in star_data]

            if len(names) > 10:
                names = names[:10]
                values = values[:10]

            names.reverse()
            values.reverse()

            self.final_star_heights = values
            self.bars_star = self.ax_star.barh(names, [0] * len(names), color='#FF9800')
            self.ax_star.set_title("星星每小时 排名", fontsize=12)
            self.ax_star.set_xlabel("星星/小时")

            def animate_star(frame):
                progress = frame / 30
                for i, bar in enumerate(self.bars_star):
                    bar.set_width(self.final_star_heights[i] * progress)
                return list(self.bars_star)

            anim = FuncAnimation(
                self.fig_star, animate_star, frames=30, interval=20, repeat=False, blit=False
            )
            self.animations.append(anim)
        else:
            self._show_no_data_in_ax(self.ax_star)

        self.canvas_star.draw()

    def _plot_daily_income(self):
        """Plot daily income chart - what user cares about"""
        # Aggregate by day
        daily_data = defaultdict(int)
        for record in self.all_records:
            daily_data[record['date']] += record['silver']

        # Plot daily income
        self.ax_daily_income.clear()
        self._setup_axes_theme(self.ax_daily_income)

        if daily_data:
            sorted_dates = sorted(daily_data.keys())
            values = [daily_data[d] for d in sorted_dates]

            # Limit to last 30 days for better visibility
            if len(sorted_dates) > 30:
                sorted_dates = sorted_dates[-30:]
                values = values[-30:]

            self.final_daily_values = values
            self.bars_daily = self.ax_daily_income.bar(
                [d.strftime('%m-%d') for d in sorted_dates],
                [0] * len(values),
                color='#FF9800'
            )
            self.ax_daily_income.set_title("每日银币收入 (最近30天)", fontsize=12)
            self.ax_daily_income.set_ylabel("银币数量")

            if len(sorted_dates) > 10:
                plt.setp(self.ax_daily_income.get_xticklabels(), rotation=45)

            def animate_daily(frame):
                progress = frame / 50
                for i, bar in enumerate(self.bars_daily):
                    bar.set_height(self.final_daily_values[i] * progress)
                return list(self.bars_daily)

            anim = FuncAnimation(
                self.fig_daily_income, animate_daily, frames=50, interval=20, repeat=False, blit=False
            )
            self.animations.append(anim)
        else:
            self._show_no_data_in_ax(self.ax_daily_income)

        self.canvas_daily_income.draw()

        # Plot cumulative income
        self.ax_cumulative.clear()
        self._setup_axes_theme(self.ax_cumulative)

        if daily_data:
            sorted_dates = sorted(daily_data.keys())
            daily_silver = [daily_data[d] for d in sorted_dates]

            # Calculate cumulative
            cumulative = []
            total = 0
            for s in daily_silver:
                total += s
                cumulative.append(total)

            x_numeric = list(range(len(sorted_dates)))
            self.final_x_cum = x_numeric
            self.final_y_cum = cumulative
            self.line_cum, = self.ax_cumulative.plot([], [], color='#4CAF50', linewidth=3)
            self.ax_cumulative.set_title("累计银币收入", fontsize=12)
            self.ax_cumulative.set_ylabel("累计银币")
            self.ax_cumulative.grid(True, alpha=0.3)

            step = max(1, len(x_numeric) // 10)
            self.ax_cumulative.set_xticks(x_numeric[::step])
            self.ax_cumulative.set_xticklabels([d.strftime('%m-%d') for d in sorted_dates[::step]])

            def animate_cum(frame):
                if frame < len(self.final_x_cum):
                    self.line_cum.set_data(self.final_x_cum[:frame+1], self.final_y_cum[:frame+1])
                return [self.line_cum]

            anim = FuncAnimation(
                self.fig_cumulative, animate_cum, frames=len(x_numeric) + 5, interval=30, repeat=False, blit=False
            )
            self.animations.append(anim)
        else:
            self._show_no_data_in_ax(self.ax_cumulative)

        self.canvas_cumulative.draw()

    def _plot_task_completion(self):
        """Plot task completion statistics - what user cares about"""
        # We need to get daily task persistence from somewhere
        # Actually, daily task data is stored separately, but we can get it from main window
        # For now, we'll show completion based on what we can get from existing data

        # Collect all tasks from daily tasks - but we don't have access here
        # So we'll just show based on character activity records compared to daily targets

        has_data = False
        task_data = []

        for char in self.characters:
            # Check if there are any today's records
            today = date.today()
            for activity_type in [ActivityType.GRINDING, ActivityType.STAR_WAITING]:
                total_value, actual_duration = char.calculate_today_totals(activity_type)
                # We can't get the daily target from here, but we can show based on goals
                task_data.append({
                    'character': char.name,
                    'type': activity_type,
                    'actual_duration': actual_duration
                })
                has_data = True

        # Plot completion rate trend (if we had historical data)
        # For now, just show a summary table
        self._populate_task_table(task_data)

        # Plot chart - we'll show actual duration by character
        self.ax_completion.clear()
        self._setup_axes_theme(self.ax_completion)

        if has_data and task_data:
            char_names = []
            durations = []
            colors = []
            for d in task_data:
                char_names.append(f"{d['character']}\n({'搬砖' if d['type'] == ActivityType.GRINDING else '蹲星'})")
                durations.append(d['actual_duration'] / 60)  # convert to hours
                colors.append('#2196F3' if d['type'] == ActivityType.GRINDING else '#FF9800')

            char_names.reverse()
            durations.reverse()
            colors.reverse()

            self.final_task_heights = durations
            self.bars_task = self.ax_task = self.ax_completion.barh(char_names, [0] * len(durations), color=colors)
            self.ax_completion.set_title("今日活动时长 (小时)", fontsize=12)
            self.ax_completion.set_xlabel("时长(小时)")

            def animate_task(frame):
                progress = frame / 30
                for i, bar in enumerate(self.bars_task):
                    bar.set_width(self.final_task_heights[i] * progress)
                return list(self.bars_task)

            anim = FuncAnimation(
                self.fig_completion, animate_task, frames=30, interval=20, repeat=False, blit=False
            )
            self.animations.append(anim)
        else:
            self._show_no_data_in_ax(self.ax_completion)

        self.canvas_completion.draw()

    def _populate_task_table(self, task_data):
        """Populate the task completion summary table"""
        self.task_table.setRowCount(len(task_data))

        for i, data in enumerate(task_data):
            type_text = "搬砖" if data['type'] == ActivityType.GRINDING else "蹲星"
            duration_hours = data['actual_duration'] / 60

            self.task_table.setItem(i, 0, QTableWidgetItem(data['character']))
            self.task_table.setItem(i, 1, QTableWidgetItem(type_text))
            self.task_table.setItem(i, 2, QTableWidgetItem(f"{duration_hours:.1f} 小时"))

            # Can't calculate completion rate without daily target, leave empty
            self.task_table.setItem(i, 3, QTableWidgetItem("-"))

    def _show_no_data_in_ax(self, ax):
        """Show no data message in axis"""
        window = self.window()
        is_dark = True
        if hasattr(window, '_current_theme'):
            is_dark = (window._current_theme == "dark")
        text_color = 'white' if is_dark else 'black'
        ax.text(0.5, 0.5, '暂无活动记录数据\n请先在活动统计中添加记录',
                horizontalalignment='center',
                verticalalignment='center',
                transform=ax.transAxes,
                color=text_color,
                fontsize=14)

    def _update_stylesheet(self):
        """Update chart theme based on current theme"""
        # Update tab widget style
        window = self.window()
        is_dark = True
        if hasattr(window, '_current_theme'):
            is_dark = (window._current_theme == "dark")

        if is_dark:
            self.tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    background-color: #1e1e1e;
                    border: 1px solid #3a3a3a;
                    border-radius: 6px;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 16px;
                    border: 1px solid #3a3a3a;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                }
                QTabBar::tab:hover {
                    background-color: #3a3a3a;
                }
            """)
        else:
            self.tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    background-color: #ffffff;
                    border: 1px solid #dddddd;
                    border-radius: 6px;
                }
                QTabBar::tab {
                    background-color: #f0f0f0;
                    color: #000000;
                    padding: 8px 16px;
                    border: 1px solid #dddddd;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                }
                QTabBar::tab:hover {
                    background-color: #e0e0e0;
                }
            """)

        # Refresh plots with new theme
        self.refresh_plots()

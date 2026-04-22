"""Data analysis page with practical actionable insights for RF4 players
Uses HTML + ECharts for better performance and beautiful interactive charts"""
from collections import defaultdict
from datetime import date, timedelta
import os
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QComboBox,
    QGroupBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from src.data.persistence import ActivityPersistence
from src.core.models import ActivityType, ActivityCharacter


class StatisticsFrame(QWidget):
    """Data analysis page with practical insights for RF4 players
    Uses ECharts via QWebEngineView for beautiful interactive charts"""

    def __init__(self, activity_persistence: ActivityPersistence):
        super().__init__()
        self.activity_persistence = activity_persistence
        self.characters = []
        self.global_settings = None

        # Filtered records for detail table
        self.all_records = []
        self.filtered_records = []
        self.html_loaded = False

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

        # 1. 图表汇总 - all charts in one tab via ECharts
        self._create_charts_tab()

        # 2. 目标进度 - 核心功能
        self._create_goal_progress_tab()

        # 3. 收益明细 - 查看详细记录
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

    def _create_charts_tab(self):
        """Create charts tab with ECharts in QWebEngineView"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Create web view for ECharts
        self.web_view = QWebEngineView()
        self.html_loaded = False
        # Connect load finished signal
        self.web_view.loadFinished.connect(self._on_html_loaded)
        # Load local HTML file
        script_dir = os.path.abspath(os.path.dirname(__file__))
        html_path = os.path.join(script_dir, 'charts', 'statistics_charts.html')
        html_url = QUrl.fromLocalFile(html_path)
        self.web_view.load(html_url)

        layout.addWidget(self.web_view)
        self.tab_widget.addTab(tab, "📊 数据图表")

    def _on_html_loaded(self, success):
        """Called when HTML finishes loading"""
        if success:
            self.html_loaded = True
            # Update charts once loaded
            self._update_charts_html()

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

    def _get_current_theme(self):
        """Get current theme from main window"""
        window = self.window()
        if hasattr(window, '_current_theme'):
            return window._current_theme
        return "dark"

    def refresh_plots(self):
        """Refresh data and update all charts"""
        self._load_data()
        self._update_summary_kpi()
        self._plot_goal_progress()
        self._update_charts_html()
        self._apply_filters()

    def _update_charts_html(self):
        """Send data to HTML via JavaScript for ECharts rendering"""
        if not self.html_loaded:
            return

        # Prepare chart data
        chart_data = {
            'spm': self._prepare_spm_data(),
            'star': self._prepare_star_data(),
            'dailyIncome': self._prepare_daily_income_data(),
            'cumulative': self._prepare_cumulative_data(),
            'task': self._prepare_task_data()
        }

        theme = self._get_current_theme()
        json_data = json.dumps(chart_data, ensure_ascii=False)

        # Call JavaScript function to update charts
        js_code = f"window.updateChartsFromPython({json_data}, '{theme}');"
        self.web_view.page().runJavaScript(js_code)

    def _prepare_spm_data(self):
        """Prepare SPM ranking data for ECharts"""
        spm_data, _ = self._calculate_efficiency_data()
        result = []
        if spm_data:
            # Limit to top 10
            if len(spm_data) > 10:
                spm_data = spm_data[:10]
            # Reverse for bottom to top in chart
            spm_data.reverse()
            for d in spm_data:
                result.append({
                    'name': d[0],
                    'value': round(d[1], 2)
                })
        return result

    def _prepare_star_data(self):
        """Prepare star per hour data for ECharts"""
        _, star_data = self._calculate_efficiency_data()
        result = []
        if star_data:
            # Limit to top 10
            if len(star_data) > 10:
                star_data = star_data[:10]
            # Reverse for bottom to top in chart
            star_data.reverse()
            for d in star_data:
                result.append({
                    'name': d[0],
                    'value': round(d[1], 2)
                })
        return result

    def _prepare_daily_income_data(self):
        """Prepare daily income data for ECharts"""
        daily_data = defaultdict(int)
        for record in self.all_records:
            daily_data[record['date']] += record['silver']

        result = []
        if daily_data:
            sorted_dates = sorted(daily_data.keys())
            # Limit to last 30 days
            if len(sorted_dates) > 30:
                sorted_dates = sorted_dates[-30:]

            for d in sorted_dates:
                result.append({
                    'date': d.strftime('%m-%d'),
                    'value': daily_data[d]
                })
        return result

    def _prepare_cumulative_data(self):
        """Prepare cumulative income data for ECharts"""
        daily_data = defaultdict(int)
        for record in self.all_records:
            daily_data[record['date']] += record['silver']

        result = []
        if daily_data:
            sorted_dates = sorted(daily_data.keys())
            cumulative = []
            total = 0
            for d in sorted_dates:
                total += daily_data[d]
                cumulative.append(total)
                result.append({
                    'date': d.strftime('%m-%d'),
                    'cumulative': total
                })
        return result

    def _prepare_task_data(self):
        """Prepare today's task duration data for ECharts"""
        has_data = False
        task_data = []
        today = date.today()

        for char in self.characters:
            for activity_type in [ActivityType.GRINDING, ActivityType.STAR_WAITING]:
                _, actual_duration = char.calculate_today_totals(activity_type)
                if actual_duration > 0:
                    has_data = True
                    type_name = "grinding" if activity_type == ActivityType.GRINDING else "star"
                    char_name = f"{char.name} ({'搬砖' if activity_type == ActivityType.GRINDING else '蹲星'})"
                    task_data.append({
                        'name': char_name,
                        'duration': round(actual_duration / 60, 1),
                        'type': type_name
                    })

        if has_data and task_data:
            # Reverse for bottom to top display
            task_data.reverse()

        return task_data

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

    def _create_heatmap_dots(self, progress_pct: float, is_dark: bool, base_color: str, empty_color: str):
        """Create heatmap-style progress visualization
        Continuous colored blocks with heat intensity gradient
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 10, 0, 10)

        # 30 blocks for heatmap - creates smoother gradient effect
        num_blocks = 30
        filled_blocks = int(progress_pct * num_blocks / 100)
        if progress_pct > 0 and filled_blocks == 0:
            filled_blocks = 1

        # Create heatmap blocks - intensity increases with progress
        for i in range(num_blocks):
            block = QLabel()
            block.setFixedSize(1, 20)

            if i < filled_blocks:
                # Calculate intensity: earlier blocks are darker, later (newer) are lighter
                # This creates a heat effect where the "front" glows brighter
                intensity = i / max(filled_blocks - 1, 1) if filled_blocks > 1 else 0.5
                lighten_amount = 0.1 + (intensity * 0.4)  # 0.1 (dark) to 0.5 (light)
                color = self._lighten_color(base_color, lighten_amount)
                block.setStyleSheet(f"""
                    QLabel {{
                        background-color: {color};
                        border-radius: 1px;
                    }}
                """)
            else:
                # Empty blocks
                if is_dark:
                    bg_color = "rgba(255, 255, 255, 0.08)"
                else:
                    bg_color = empty_color
                block.setStyleSheet(f"""
                    QLabel {{
                        background-color: {bg_color};
                        border-radius: 1px;
                    }}
                """)
            layout.addWidget(block)

        # Add stretch to push percentage label to the right
        layout.addStretch()

        # Add percentage label at the end
        pct_label = QLabel(f" {progress_pct:.1f}%")
        pct_label.setFixedWidth(65)
        pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if is_dark:
            pct_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 13px;")
        else:
            pct_label.setStyleSheet("color: #444444; font-weight: bold; font-size: 13px;")
        layout.addWidget(pct_label)

        return container

    def _lighten_color(self, color_hex, amount=0.3):
        """Lighten a hex color by given amount (0-1)"""
        # Handle rgba format - convert to hex
        if color_hex.startswith('rgba'):
            # For rgba, just return the original since we only lighten solid colors
            return color_hex
        # Remove # if present
        color_hex = color_hex.lstrip('#')
        # Convert to RGB
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        # Lighten
        r = int(r + (255 - r) * amount)
        g = int(g + (255 - g) * amount)
        b = int(b + (255 - b) * amount)
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_thermal_heatmap(self, progress_pct: float, is_dark: bool, dark_color: str, light_color: str):
        """Create a continuous thermal heatmap progress bar
        Gradient effect from cold (dark color) to hot (light color) at the progress edge
        Automatically expands to fill available width and resizes with window
        """
        from PySide6.QtWidgets import QSizePolicy
        container = QWidget()
        container.setFixedHeight(24)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(container)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        # 50 blocks for smooth thermal gradient effect - evenly distributed
        num_blocks = 50
        filled_blocks = int(progress_pct * num_blocks / 100)
        if progress_pct > 0 and filled_blocks == 0:
            filled_blocks = 1

        for i in range(num_blocks):
            block = QLabel()
            block.setFixedHeight(24)
            block.setMinimumWidth(1)
            # All blocks get equal space, container handles the expanding
            block.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

            if i < filled_blocks:
                # Thermal gradient effect - from dark (older) to light (hotter at the edge)
                intensity = i / max(filled_blocks - 1, 1) if filled_blocks > 1 else 0.5
                lighten_amount = intensity * 0.4
                color = self._lighten_color(dark_color, lighten_amount)
                block.setStyleSheet(f"QLabel {{ background-color: {color}; border-radius: 2px; }}")
            else:
                # Empty background
                if is_dark:
                    bg_color = "rgba(255, 255, 255, 0.08)"
                else:
                    bg_color = "#e8e8e8"
                block.setStyleSheet(f"QLabel {{ background-color: {bg_color}; border-radius: 2px; }}")
            layout.addWidget(block)

        return container

    def _plot_goal_progress(self):
        """Clear existing goal progress widgets and recreate
        Modern thermal heatmap progress - each goal is a clean card with full-width gradient
        """
        # Clear existing widgets
        for i in reversed(range(self.goal_layout.count())):
            item = self.goal_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.goal_progress_widgets.clear()

        has_any_goal = False
        window = self.window()
        is_dark = True
        if hasattr(window, '_current_theme'):
            is_dark = (window._current_theme == "dark")

        for char in self.characters:
            # Count total goals for this character
            total_goals = len(char.grinding_goals) + len(char.star_waiting_goals)
            if total_goals == 0:
                continue

            has_any_goal = True

            # Character section header
            char_header = QWidget()
            header_layout = QHBoxLayout(char_header)
            header_layout.setContentsMargins(4, 8, 4, 12)

            char_title = QLabel(f"👤 {char.name}")
            char_title.setFont(QFont("Segoe UI", 15, QFont.Bold))
            if is_dark:
                char_title.setStyleSheet("color: #ffffff;")
            else:
                char_title.setStyleSheet("color: #222222;")
            header_layout.addWidget(char_title)
            header_layout.addStretch()

            goal_count_label = QLabel(f"{total_goals} 个目标")
            if is_dark:
                goal_count_label.setStyleSheet("color: #aaaaaa; font-size: 13px; background: rgba(255, 255, 255, 0.1); padding: 4px 10px; border-radius: 10px;")
            else:
                goal_count_label.setStyleSheet("color: #666666; font-size: 13px; background: #f0f0f0; padding: 4px 10px; border-radius: 10px;")
            header_layout.addWidget(goal_count_label)
            self.goal_layout.addWidget(char_header)

            # Container for goals
            goals_container = QWidget()
            goals_layout = QVBoxLayout(goals_container)
            goals_layout.setSpacing(16)
            goals_layout.setContentsMargins(4, 0, 4, 20)

            # Add all grinding goals
            for goal_idx, goal in enumerate(char.grinding_goals):
                _, total_duration, _ = char.calculate_totals(ActivityType.GRINDING)
                # Use goal's own current_progress instead of total from records
                # This ensures cumulative progress is correct even when records are filtered
                total_value = goal.current_progress

                # Calculate progress
                progress_value_pct = (total_value / goal.target_value * 100) if goal.target_value > 0 else 100
                progress_value_pct = min(progress_value_pct, 100)
                progress_duration_pct = (total_duration / goal.target_duration * 100) if goal.target_duration > 0 else 100
                progress_duration_pct = min(progress_duration_pct, 100)

                # Calculate remaining
                remaining_value = max(0, goal.target_value - total_value) if goal.target_value > 0 else 0
                remaining_duration = max(0, goal.target_duration - total_duration) if goal.target_duration > 0 else 0

                # Calculate estimated days
                avg_daily_value = self._calculate_average_daily_progress(char, ActivityType.GRINDING)
                avg_daily_duration = self._calculate_average_daily_duration(char, ActivityType.GRINDING)
                remaining_days_text = ""

                if goal.target_value > 0 and remaining_value > 0:
                    if avg_daily_value > 0:
                        remaining_days = remaining_value / avg_daily_value
                        remaining_days_text = f"⏳ 预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "⏳ 无法预测"
                elif goal.target_duration > 0 and remaining_duration > 0:
                    if avg_daily_duration > 0:
                        remaining_days = remaining_duration / avg_daily_duration
                        remaining_days_text = f"⏳ 预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "⏳ 无法预测"
                else:
                    remaining_days_text = "🎉 已完成"

                # Calculate remaining income
                remaining_income = 0
                if goal.total_income > 0:
                    remaining_value_ratio = remaining_value / goal.target_value if goal.target_value > 0 else 0
                    remaining_duration_ratio = remaining_duration / goal.target_duration if goal.target_duration > 0 else 0
                    max_remaining_ratio = max(remaining_value_ratio, remaining_duration_ratio)
                    remaining_income = int(goal.total_income * max_remaining_ratio)

                # Single goal card
                goal_widget = QWidget()
                goal_vbox = QVBoxLayout(goal_widget)
                goal_vbox.setSpacing(8)
                goal_vbox.setContentsMargins(12, 12, 12, 12)

                # Top row: goal name + status tag
                top_row = QWidget()
                top_layout = QHBoxLayout(top_row)
                top_layout.setContentsMargins(0, 0, 0, 4)

                goal_name = QLabel(f"🏭 搬砖目标 #{goal_idx + 1}")
                goal_name.setFont(QFont("Segoe UI", 12, QFont.Bold))
                if progress_value_pct >= 100 or progress_duration_pct >= 100:
                    if is_dark:
                        goal_name.setStyleSheet("color: #4CAF50;")
                        status_text = "<span style='background: #4CAF50; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>已完成</span>"
                    else:
                        goal_name.setStyleSheet("color: #4CAF50;")
                        status_text = "<span style='background: #4CAF50; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>已完成</span>"
                else:
                    if is_dark:
                        goal_name.setStyleSheet("color: #ffffff;")
                        status_text = "<span style='background: #2196F3; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>进行中</span>"
                    else:
                        goal_name.setStyleSheet("color: #333333;")
                        status_text = "<span style='background: #2196F3; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>进行中</span>"
                top_layout.addWidget(goal_name)
                top_layout.addStretch()
                status_label = QLabel()
                status_label.setText(status_text)
                top_layout.addWidget(status_label)
                goal_vbox.addWidget(top_row)

                # Value progress with thermal heatmap
                if goal.target_value > 0:
                    stats_text = f"📊 {total_value:,} / {goal.target_value:,} 银币"
                    stats_label = QLabel(stats_text)
                    if is_dark:
                        stats_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                    else:
                        stats_label.setStyleSheet("color: #555555; font-size: 12px;")
                    goal_vbox.addWidget(stats_label)
                    heat_widget = self._create_thermal_heatmap(progress_value_pct, is_dark, "#1976D2", "#0D47A1")
                    goal_vbox.addWidget(heat_widget)

                # Duration progress with thermal heatmap
                if goal.target_duration > 0:
                    stats_text = f"⏱️ {total_duration} / {goal.target_duration} 分钟"
                    stats_label = QLabel(stats_text)
                    if is_dark:
                        stats_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                    else:
                        stats_label.setStyleSheet("color: #555555; font-size: 12px;")
                    goal_vbox.addWidget(stats_label)
                    heat_widget = self._create_thermal_heatmap(progress_duration_pct, is_dark, "#2E7D32", "#1B5E20")
                    goal_vbox.addWidget(heat_widget)

                # Bottom info row
                info_parts = []
                if goal.target_value > 0:
                    info_parts.append(f"剩余: {remaining_value:,} 银币")
                if goal.total_income > 0:
                    info_parts.append(f"预期剩余收入: {remaining_income:,}")
                info_text = " • ".join(info_parts + [remaining_days_text])
                info_label = QLabel(info_text)
                if is_dark:
                    info_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
                else:
                    info_label.setStyleSheet("color: #666666; font-size: 11px;")
                goal_vbox.addWidget(info_label)

                # Card styling
                if is_dark:
                    goal_widget.setStyleSheet("""
                        QWidget {
                            border-radius: 12px;
                            background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                        }
                    """)
                else:
                    goal_widget.setStyleSheet("""
                        QWidget {
                            border-radius: 12px;
                            background: linear-gradient(135deg, #ffffff 0%, #fafafa 100%);
                            border: 1px solid rgba(0, 0, 0, 0.06);
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                        }
                    """)
                goals_layout.addWidget(goal_widget)
                self.goal_progress_widgets.append((goal_widget, None, None, info_label))

            # Add all star waiting goals
            for goal_idx, goal in enumerate(char.star_waiting_goals):
                _, total_duration, _ = char.calculate_totals(ActivityType.STAR_WAITING)
                # Use goal's own current_progress instead of total from records
                # This ensures cumulative progress is correct even when records are filtered
                total_value = goal.current_progress

                # Calculate progress
                progress_value_pct = (total_value / goal.target_value * 100) if goal.target_value > 0 else 100
                progress_value_pct = min(progress_value_pct, 100)
                progress_duration_pct = (total_duration / goal.target_duration * 100) if goal.target_duration > 0 else 100
                progress_duration_pct = min(progress_duration_pct, 100)

                # Calculate remaining
                remaining_value = max(0, goal.target_value - total_value) if goal.target_value > 0 else 0
                remaining_duration = max(0, goal.target_duration - total_duration) if goal.target_duration > 0 else 0

                # Calculate estimated days
                avg_daily_value = self._calculate_average_daily_progress(char, ActivityType.STAR_WAITING)
                avg_daily_duration = self._calculate_average_daily_duration(char, ActivityType.STAR_WAITING)
                remaining_days_text = ""

                if goal.target_value > 0 and remaining_value > 0:
                    if avg_daily_value > 0:
                        remaining_days = remaining_value / avg_daily_value
                        remaining_days_text = f"⏳ 预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "⏳ 无法预测"
                elif goal.target_duration > 0 and remaining_duration > 0:
                    if avg_daily_duration > 0:
                        remaining_days = remaining_duration / avg_daily_duration
                        remaining_days_text = f"⏳ 预计还需 {remaining_days:.1f} 天"
                    else:
                        remaining_days_text = "⏳ 无法预测"
                else:
                    remaining_days_text = "🎉 已完成"

                # Calculate remaining income
                remaining_income = 0
                if goal.total_income > 0:
                    remaining_value_ratio = remaining_value / goal.target_value if goal.target_value > 0 else 0
                    remaining_duration_ratio = remaining_duration / goal.target_duration if goal.target_duration > 0 else 0
                    max_remaining_ratio = max(remaining_value_ratio, remaining_duration_ratio)
                    remaining_income = int(goal.total_income * max_remaining_ratio)

                # Single goal card
                goal_widget = QWidget()
                goal_vbox = QVBoxLayout(goal_widget)
                goal_vbox.setSpacing(8)
                goal_vbox.setContentsMargins(12, 12, 12, 12)

                # Top row: goal name + status tag
                top_row = QWidget()
                top_layout = QHBoxLayout(top_row)
                top_layout.setContentsMargins(0, 0, 0, 4)

                goal_name = QLabel(f"⭐ 蹲星目标 #{goal_idx + 1}")
                goal_name.setFont(QFont("Segoe UI", 12, QFont.Bold))
                if progress_value_pct >= 100 or progress_duration_pct >= 100:
                    if is_dark:
                        goal_name.setStyleSheet("color: #4CAF50;")
                        status_text = "<span style='background: #4CAF50; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>已完成</span>"
                    else:
                        goal_name.setStyleSheet("color: #4CAF50;")
                        status_text = "<span style='background: #4CAF50; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>已完成</span>"
                else:
                    if is_dark:
                        goal_name.setStyleSheet("color: #ffffff;")
                        status_text = "<span style='background: #FF9800; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>进行中</span>"
                    else:
                        goal_name.setStyleSheet("color: #333333;")
                        status_text = "<span style='background: #FF9800; color: white; padding: 3px 8px; border-radius: 8px; font-size: 11px;'>进行中</span>"
                top_layout.addWidget(goal_name)
                top_layout.addStretch()
                status_label = QLabel()
                status_label.setText(status_text)
                top_layout.addWidget(status_label)
                goal_vbox.addWidget(top_row)

                # Value progress with thermal heatmap (warm orange for stars)
                if goal.target_value > 0:
                    stats_text = f"📊 {total_value} / {goal.target_value} 星星"
                    stats_label = QLabel(stats_text)
                    if is_dark:
                        stats_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                    else:
                        stats_label.setStyleSheet("color: #555555; font-size: 12px;")
                    goal_vbox.addWidget(stats_label)
                    heat_widget = self._create_thermal_heatmap(progress_value_pct, is_dark, "#F57C00", "#E65100")
                    goal_vbox.addWidget(heat_widget)

                # Duration progress
                if goal.target_duration > 0:
                    stats_text = f"⏱️ {total_duration} / {goal.target_duration} 分钟"
                    stats_label = QLabel(stats_text)
                    if is_dark:
                        stats_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                    else:
                        stats_label.setStyleSheet("color: #555555; font-size: 12px;")
                    goal_vbox.addWidget(stats_label)
                    heat_widget = self._create_thermal_heatmap(progress_duration_pct, is_dark, "#F57C00", "#E65100")
                    goal_vbox.addWidget(heat_widget)

                # Bottom info row
                info_parts = []
                if goal.target_value > 0:
                    info_parts.append(f"剩余: {remaining_value} 星星")
                if goal.total_income > 0:
                    info_parts.append(f"预期剩余收入: {remaining_income:,}")
                info_text = " • ".join(info_parts + [remaining_days_text])
                info_label = QLabel(info_text)
                if is_dark:
                    info_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
                else:
                    info_label.setStyleSheet("color: #666666; font-size: 11px;")
                goal_vbox.addWidget(info_label)

                # Card styling
                if is_dark:
                    goal_widget.setStyleSheet("""
                        QWidget {
                            border-radius: 12px;
                            background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                        }
                    """)
                else:
                    goal_widget.setStyleSheet("""
                        QWidget {
                            border-radius: 12px;
                            background: linear-gradient(135deg, #ffffff 0%, #fafafa 100%);
                            border: 1px solid rgba(0, 0, 0, 0.06);
                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                        }
                    """)
                goals_layout.addWidget(goal_widget)
                self.goal_progress_widgets.append((goal_widget, None, None, info_label))

            # Add goals container to layout
            self.goal_layout.addWidget(goals_container)

        if not has_any_goal:
            label = QLabel("暂无目标设置\n请在活动统计页面为角色设置目标")
            label.setAlignment(Qt.AlignCenter)
            if is_dark:
                label.setStyleSheet("color: #aaaaaa;")
            else:
                label.setStyleSheet("color: #666666;")
            label.setFont(QFont("Segoe UI", 14))
            self.goal_layout.addWidget(label)

        self.goal_layout.addStretch()

    def _populate_task_table(self, task_data):
        """Populate the task completion summary table (kept for compatibility, not used in new layout)"""
        # This method is kept but not used in the new HTML-based layout
        pass

    def resizeEvent(self, event):
        """Resize web view when widget resizes"""
        super().resizeEvent(event)
        if hasattr(self, 'web_view') and self.html_loaded:
            # Trigger resize in ECharts
            self.web_view.page().runJavaScript("window.resizeAll();")

    def _update_stylesheet(self):
        """Update chart theme when theme changes"""
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

        # Refresh charts with new theme
        if self.html_loaded:
            self._update_charts_html()

    def mousePressEvent(self, event):
        """Forward mouse press to main window for resizing"""
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtGui import QMouseEvent
        window = self.window()
        if event.button() == Qt.LeftButton and hasattr(window, '_get_resize_direction'):
            # Convert to window coordinates
            original_pos = event.position().toPoint()
            local_pos = self.mapTo(window, original_pos)
            w = window.width()
            h = window.height()
            print(f"[DEBUG {self.__class__.__name__}] mousePress: original=({original_pos.x()}, {original_pos.y()}), window=({local_pos.x()}, {local_pos.y()}), window_size=({w}, {h})")

            direction = window._get_resize_direction(local_pos)
            print(f"[DEBUG {self.__class__.__name__}] direction: {direction}")

            if direction is not None:
                # Create new event with corrected coordinates
                new_event = QMouseEvent(
                    event.type(),
                    QPointF(local_pos),
                    event.globalPosition(),
                    event.button(),
                    event.buttons(),
                    event.modifiers()
                )
                window.mousePressEvent(new_event)
                if new_event.isAccepted():
                    print(f"[DEBUG {self.__class__.__name__}] event accepted by main window")
                    event.accept()
                    return
            else:
                print(f"[DEBUG {self.__class__.__name__}] no direction, pass through")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Forward mouse move to main window for resizing"""
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtGui import QMouseEvent
        window = self.window()
        if hasattr(window, '_get_resize_direction'):
            # Convert to window coordinates
            original_pos = event.position().toPoint()
            local_pos = self.mapTo(window, original_pos)

            if (event.buttons() & Qt.LeftButton) and hasattr(window, '_resize_direction'):
                if window._resize_direction is not None:
                    # We are already resizing - always forward
                    new_event = QMouseEvent(
                        event.type(),
                        QPointF(local_pos),
                        event.globalPosition(),
                        event.button(),
                        event.buttons(),
                        event.modifiers()
                    )
                    window.mouseMoveEvent(new_event)
                    if new_event.isAccepted():
                        event.accept()
                        return
            else:
                # Check if we are on the edge for cursor change
                direction = window._get_resize_direction(local_pos)
                if direction is not None:
                    new_event = QMouseEvent(
                        event.type(),
                        QPointF(local_pos),
                        event.globalPosition(),
                        event.button(),
                        event.buttons(),
                        event.modifiers()
                    )
                    window.mouseMoveEvent(new_event)
                    if new_event.isAccepted():
                        event.accept()
                        return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Forward mouse release to main window for resizing"""
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        window = self.window()
        if hasattr(window, '_resize_direction') and window._resize_direction is not None:
            # Convert to window coordinates
            local_pos = self.mapTo(window, event.position().toPoint())
            new_event = QMouseEvent(
                event.type(),
                QPointF(local_pos),
                event.globalPosition(),
                event.button(),
                event.buttons(),
                event.modifiers()
            )
            window.mouseReleaseEvent(new_event)
            if new_event.isAccepted():
                event.accept()
                return
        super().mouseReleaseEvent(event)
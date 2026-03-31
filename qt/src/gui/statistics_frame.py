"""Data analysis page with animated visualizations"""
from collections import defaultdict
from datetime import date
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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.data.persistence import ActivityPersistence


class StatisticsFrame(QWidget):
    """Data analysis page with animated charts"""

    def __init__(self, activity_persistence: ActivityPersistence):
        super().__init__()
        self.activity_persistence = activity_persistence
        self.animations = []

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

        # Description
        desc = QLabel("数据可视化展示 - 图表加载时有动画效果")
        desc.setFont(QFont("Segoe UI", 14))
        desc.setStyleSheet("color: #aaaaaa;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # Refresh button
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        refresh_btn = QPushButton("🔄 重新加载数据")
        refresh_btn.setFixedWidth(120)
        refresh_btn.clicked.connect(self.refresh_plots)
        btn_layout.addWidget(refresh_btn)

        reanimate_btn = QPushButton("🎬 重新播放动画")
        reanimate_btn.setFixedWidth(120)
        reanimate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        reanimate_btn.clicked.connect(self.replay_animation)
        btn_layout.addWidget(reanimate_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Tabbed interface
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Segoe UI", 14))

        # 1. Daily trend tab - daily + cumulative
        self.tab1 = QWidget()
        layout1 = QVBoxLayout(self.tab1)
        layout1.setContentsMargins(5, 5, 5, 5)
        self.fig_daily = Figure(figsize=(8, 5), dpi=100)
        self.ax_daily = self.fig_daily.add_subplot(111)
        self._setup_dark_axes(self.ax_daily)
        self.canvas_daily = FigureCanvas(self.fig_daily)
        layout1.addWidget(self.canvas_daily)
        self.tab_widget.addTab(self.tab1, "每日收益趋势")

        # 2. Character comparison tab
        self.tab2 = QWidget()
        layout2 = QVBoxLayout(self.tab2)
        layout2.setContentsMargins(5, 5, 5, 5)
        self.fig_char = Figure(figsize=(8, 5), dpi=100)
        self.ax_char = self.fig_char.add_subplot(111)
        self._setup_dark_axes(self.ax_char)
        self.canvas_char = FigureCanvas(self.fig_char)
        layout2.addWidget(self.canvas_char)
        self.tab_widget.addTab(self.tab2, "角色收益对比")

        # 3. Activity type time distribution
        self.tab3 = QWidget()
        layout3 = QVBoxLayout(self.tab3)
        layout3.setContentsMargins(5, 5, 5, 5)
        self.fig_type = Figure(figsize=(6, 4), dpi=100)
        self.ax_type = self.fig_type.add_subplot(111)
        self.fig_type.set_facecolor("#2b2b2b")
        self.ax_type.set_facecolor("#2b2b2b")
        self.canvas_type = FigureCanvas(self.fig_type)
        layout3.addWidget(self.canvas_type)
        self.tab_widget.addTab(self.tab3, "活动类型分布")

        # 4. Character time distribution
        self.tab4 = QWidget()
        layout4 = QVBoxLayout(self.tab4)
        layout4.setContentsMargins(5, 5, 5, 5)
        self.fig_char_time = Figure(figsize=(6, 4), dpi=100)
        self.ax_char_time = self.fig_char_time.add_subplot(111)
        self.fig_char_time.set_facecolor("#2b2b2b")
        self.ax_char_time.set_facecolor("#2b2b2b")
        self.canvas_char_time = FigureCanvas(self.fig_char_time)
        layout4.addWidget(self.canvas_char_time)
        self.tab_widget.addTab(self.tab4, "角色时长分布")

        layout.addWidget(self.tab_widget, 1)
        self.setLayout(layout)

    def _setup_dark_axes(self, ax):
        """Setup dark theme for axes"""
        ax.set_facecolor("#2b2b2b")
        if ax.figure is not None:
            ax.figure.set_facecolor("#2b2b2b")
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.title.set_color('white')

    def refresh_plots(self):
        """Refresh data and replay all animations"""
        # Stop existing animations
        for anim in self.animations:
            if anim is not None and anim.event_source is not None:
                anim.event_source.stop()
        self.animations.clear()

        self._load_data_and_plot()

    def replay_animation(self):
        """Replay all animations"""
        self.refresh_plots()

    def _load_data_and_plot(self):
        """Load data from persistence and create plots with animation"""
        # Load ALL records for statistics analysis (not just today)
        characters, _ = self.activity_persistence.load_all_characters()

        if not characters:
            self._show_no_data()
            return

        has_data = False

        # Process data for daily trend: both daily and cumulative
        daily_data = defaultdict(int)  # date -> total silver
        daily_duration = defaultdict(int)  # date -> total duration
        for char in characters:
            for record in char.records:
                daily_data[record.date] += record.silver_count
                daily_duration[record.date] += record.duration_minutes

        if daily_data:
            has_data = True
            # Sort by date
            sorted_dates = sorted(daily_data.keys())
            daily_silver = [daily_data[d] for d in sorted_dates]

            # Calculate cumulative silver
            cumulative = []
            total = 0
            for s in daily_silver:
                total += s
                cumulative.append(total)

            # Plot daily trend with animation (two lines: daily + cumulative)
            self._plot_daily_trend_animated(sorted_dates, daily_silver, cumulative)

        # Process data for character comparison
        char_totals = []
        char_names = []
        char_total_time = []
        for char in characters:
            total_grinding = 0
            total_time_char = 0
            for record in char.records:
                total_time_char += record.duration_minutes
                if char.grinding_goal and record.activity_type == char.grinding_goal.activity_type:
                    total_grinding += record.silver_count
            if char.grinding_goal:
                char_totals.append(char.grinding_goal.total_income - char.get_remaining_income())
                char_names.append(char.name)
                char_total_time.append(total_time_char)
            else:
                if total_grinding > 0:
                    char_totals.append(total_grinding)
                    char_names.append(char.name)
                    char_total_time.append(total_time_char)

        if char_totals:
            has_data = True
            self._plot_character_comparison_animated(char_names, char_totals)

        # Process data for time distribution by activity type
        grinding_total = 0
        star_total = 0
        for char in characters:
            for record in char.records:
                if record.activity_type.value == "grinding":
                    grinding_total += record.duration_minutes
                else:
                    star_total += record.duration_minutes

        total_time = grinding_total + star_total
        if total_time > 0:
            has_data = True
            self._plot_type_distribution_pie(grinding_total, star_total)

        # Process data for time distribution by character
        if char_total_time and len(char_names) > 0:
            has_data = True
            self._plot_character_time_distribution_pie(char_names, char_total_time)

        if not has_data:
            self._show_no_data()

    def _plot_daily_trend_animated(self, sorted_dates, daily_silver, cumulative):
        """Plot daily trend with animation: two lines, daily and cumulative"""
        self.ax_daily.clear()
        self._setup_dark_axes(self.ax_daily)

        self.ax_daily.set_title("每日银币收益 - 当日vs累计", fontsize=14)
        self.ax_daily.set_xlabel("日期", fontsize=12)
        self.ax_daily.set_ylabel("银币数量", fontsize=12)

        # Use numeric index for x
        x_numeric = list(range(len(sorted_dates)))
        self.final_x = x_numeric
        self.final_y_daily = daily_silver
        self.final_y_cum = cumulative

        # Set custom tick labels with dates
        self.ax_daily.set_xticks(x_numeric)
        self.ax_daily.set_xticklabels([d.strftime('%m-%d') for d in sorted_dates])

        # Reduce tick density if there are many dates
        if len(sorted_dates) > 10:
            step = max(1, len(sorted_dates) // 10)
            self.ax_daily.set_xticks(x_numeric[::step])
            self.ax_daily.set_xticklabels([d.strftime('%m-%d') for d in sorted_dates[::step]])

        # Start with empty lines
        self.line_daily, = self.ax_daily.plot([], [], color='#FF9800', linewidth=3, label='当日收益')
        self.line_cum, = self.ax_daily.plot([], [], color='#4CAF50', linewidth=3, label='累计收益')
        self.ax_daily.relim()
        self.ax_daily.autoscale_view()

        # Add grid
        self.ax_daily.grid(True, alpha=0.3, color='gray')
        self.ax_daily.legend(loc='upper left', facecolor="#333333", labelcolor="white")

        # Animate: gradually draw both lines
        def animate(frame):
            if frame < len(self.final_x):
                self.line_daily.set_data(self.final_x[:frame+1], self.final_y_daily[:frame+1])
                self.line_cum.set_data(self.final_x[:frame+1], self.final_y_cum[:frame+1])
            return [self.line_daily, self.line_cum]

        anim = FuncAnimation(
            self.fig_daily,
            animate,
            frames=len(self.final_x) + 10,
            interval=40,
            repeat=False,
            blit=False
        )
        self.animations.append(anim)
        self.canvas_daily.draw()

    def _plot_character_comparison_animated(self, char_names, char_totals):
        """Plot character comparison with animated bars that grow from bottom"""
        self.ax_char.clear()
        self._setup_dark_axes(self.ax_char)

        self.ax_char.set_title("各角色累计已获得银币", fontsize=14)
        self.ax_char.set_ylabel("已获得银币", fontsize=12)

        # Sort by value descending
        sorted_pairs = sorted(zip(char_names, char_totals), key=lambda x: x[1], reverse=True)
        char_names = [p[0] for p in sorted_pairs]
        char_totals = [p[1] for p in sorted_pairs]

        # Limit to top 10 if too many
        if len(char_names) > 10:
            char_names = char_names[:10]
            char_totals = char_totals[:10]

        # Store final heights for animation
        self.final_heights = char_totals

        # Create bars starting at 0
        bars = self.ax_char.bar(char_names, [0] * len(char_names), color='#2196F3', edgecolor='white', linewidth=1)
        self.bars = list(bars)

        plt.setp(self.ax_char.get_xticklabels(), rotation=45)
        self.ax_char.relim()
        self.ax_char.autoscale_view()

        # Animate: bars grow from bottom to top
        def animate(frame):
            progress = frame / 50  # 50 frames
            for i, bar in enumerate(self.bars):
                bar.set_height(self.final_heights[i] * progress)
            return self.bars

        anim = FuncAnimation(
            self.fig_char,
            animate,
            frames=50,
            interval=20,
            repeat=False,
            blit=False
        )
        self.animations.append(anim)

        self.canvas_char.draw()

    def _plot_type_distribution_pie(self, grinding_minutes, star_minutes):
        """Plot time distribution by activity type as pie chart with animation"""
        self.ax_type.clear()
        self.fig_type.set_facecolor("#2b2b2b")
        self.ax_type.set_facecolor("#2b2b2b")
        self.ax_type.set_title("总活动时长分布 (按活动类型)", fontsize=14, color='white')

        grinding_hours = grinding_minutes / 60
        star_hours = star_minutes / 60
        total_hours = grinding_hours + star_hours

        labels = [
            f'搬砖\n({grinding_hours:.1f}小时)',
            f'蹲星\n({star_hours:.1f}小时)'
        ]
        sizes = [grinding_minutes, star_minutes]
        colors = ['#2196F3', '#FF9800']

        def animate(frame):
            self.ax_type.clear()
            self.fig_type.set_facecolor("#2b2b2b")
            self.ax_type.set_facecolor("#2b2b2b")
            self.ax_type.set_title("总活动时长分布 (按活动类型)", fontsize=14, color='white')
            start_angle = 90 - (frame * 3.6)  # 100 frames = 360 degrees
            wedges, texts, autotexts = self.ax_type.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                startangle=start_angle,
                textprops={'color': 'white'}
            )
            self.ax_type.axis('equal')
            return wedges

        anim = FuncAnimation(
            self.fig_type,
            animate,
            frames=100,
            interval=10,
            repeat=False,
            blit=False
        )
        self.animations.append(anim)

        self.canvas_type.draw()

    def _plot_character_time_distribution_pie(self, char_names, char_minutes):
        """Plot time distribution by character as pie chart with animation"""
        self.ax_char_time.clear()
        self.fig_char_time.set_facecolor("#2b2b2b")
        self.ax_char_time.set_facecolor("#2b2b2b")
        self.ax_char_time.set_title("总活动时长分布 (按角色)", fontsize=14, color='white')

        # Sort by total time descending
        sorted_pairs = sorted(zip(char_names, char_minutes), key=lambda x: x[1], reverse=True)
        char_names = [p[0] for p in sorted_pairs]
        char_minutes = [p[1] for p in sorted_pairs]

        # If more than 8 characters, combine smaller ones into "其他"
        if len(char_names) > 8:
            top_names = char_names[:7]
            top_minutes = char_minutes[:7]
            other_minutes = sum(char_minutes[7:])
            top_names.append("其他")
            top_minutes.append(other_minutes)
            char_names = top_names
            char_minutes = top_minutes

        colors = [
            '#2196F3', '#FF9800', '#4CAF50', '#F44336',
            '#9C27B0', '#FFC107', '#00BCD4', '#E91E63'
        ]

        # Add hour info to labels
        labels = [
            f'{name}\n({m/60:.1f}小时)'
            for name, m in zip(char_names, char_minutes)
        ]
        sizes = char_minutes

        def animate(frame):
            self.ax_char_time.clear()
            self.fig_char_time.set_facecolor("#2b2b2b")
            self.ax_char_time.set_facecolor("#2b2b2b")
            self.ax_char_time.set_title("总活动时长分布 (按角色)", fontsize=14, color='white')
            start_angle = 90 - (frame * 3.6)
            wedges, texts, autotexts = self.ax_char_time.pie(
                sizes,
                labels=labels,
                colors=colors[:len(sizes)],
                autopct='%1.1f%%',
                startangle=start_angle,
                textprops={'color': 'white'}
            )
            self.ax_char_time.axis('equal')
            return wedges

        anim = FuncAnimation(
            self.fig_char_time,
            animate,
            frames=100,
            interval=10,
            repeat=False,
            blit=False
        )
        self.animations.append(anim)

        self.canvas_char_time.draw()

    def _show_no_data(self):
        """Show message when no data available"""
        for ax, canvas in [(self.ax_daily, self.canvas_daily),
                          (self.ax_char, self.canvas_char),
                          (self.ax_type, self.canvas_type),
                          (self.ax_char_time, self.canvas_char_time)]:
            ax.clear()
            ax.set_facecolor("#2b2b2b")
            ax.text(0.5, 0.5, '暂无活动记录数据\n请先在活动统计中添加记录',
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=ax.transAxes,
                   color='white',
                   fontsize=14)
            canvas.draw()

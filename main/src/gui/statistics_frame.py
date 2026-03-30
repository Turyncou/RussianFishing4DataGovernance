"""Data analysis page with animated visualizations"""
import customtkinter as ctk
from datetime import date, datetime
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter, DayLocator

# Configure matplotlib to use Chinese font
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

from data.persistence import ActivityPersistence


class StatisticsFrame(ctk.CTkFrame):
    """Data analysis page with animated charts"""

    def __init__(self, parent, activity_persistence: ActivityPersistence):
        super().__init__(parent, fg_color="transparent", corner_radius=16)
        self.activity_persistence = activity_persistence
        self.animation = None
        self.bars = None
        self.final_heights = None
        self.line = None
        self.final_x = None
        self.final_y = None

        self.create_widgets()
        self.load_data_and_plot()

    def create_widgets(self):
        """Create the UI widgets"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="📈 数据分析",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(15, 10))

        # Description
        desc = ctk.CTkLabel(
            self,
            text="数据可视化展示 - 图表加载时有动画效果",
            font=ctk.CTkFont(size=14),
            text_color="#aaaaaa"
        )
        desc.pack(pady=(0, 10))

        # Refresh button
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=5)

        refresh_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 重新加载数据",
            command=self.refresh_plots,
            width=120,
            corner_radius=8
        )
        refresh_btn.pack(side="left", padx=5)

        reanimate_btn = ctk.CTkButton(
            btn_frame,
            text="🎬 重新播放动画",
            command=self.replay_animation,
            width=120,
            corner_radius=8,
            fg_color="#4CAF50",
            hover_color="#388E3C"
        )
        reanimate_btn.pack(side="left", padx=5)

        # Notebook (tabbed interface for multiple plots)
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

        # Create tabs
        self.tab_daily = self.tabview.add("每日收益趋势")
        self.tab_character = self.tabview.add("角色收益对比")
        self.tab_time = self.tabview.add("活动时长分布")

        # Create matplotlib figures for each tab
        self._create_daily_trend_plot()
        self._create_character_comparison_plot()
        self._create_time_distribution_plot()

    def _create_daily_trend_plot(self):
        """Create daily income trend plot (line chart with animation)"""
        self.fig_daily, self.ax_daily = plt.subplots(
            figsize=(8, 4),
            dpi=100,
            facecolor="#2b2b2b"
        )
        self.ax_daily.set_facecolor("#2b2b2b")
        self.ax_daily.tick_params(axis='x', colors='white')
        self.ax_daily.tick_params(axis='y', colors='white')
        self.ax_daily.spines['bottom'].set_color('white')
        self.ax_daily.spines['top'].set_color('white')
        self.ax_daily.spines['left'].set_color('white')
        self.ax_daily.spines['right'].set_color('white')
        self.ax_daily.yaxis.label.set_color('white')
        self.ax_daily.xaxis.label.set_color('white')
        self.ax_daily.title.set_color('white')

        self.canvas_daily = FigureCanvasTkAgg(self.fig_daily, master=self.tab_daily)
        self.canvas_daily.draw()
        self.canvas_daily.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def _create_character_comparison_plot(self):
        """Create character income comparison plot (animated bar chart)"""
        self.fig_char, self.ax_char = plt.subplots(
            figsize=(8, 4),
            dpi=100,
            facecolor="#2b2b2b"
        )
        self.ax_char.set_facecolor("#2b2b2b")
        self.ax_char.tick_params(axis='x', colors='white')
        self.ax_char.tick_params(axis='y', colors='white')
        self.ax_char.spines['bottom'].set_color('white')
        self.ax_char.spines['top'].set_color('white')
        self.ax_char.spines['left'].set_color('white')
        self.ax_char.spines['right'].set_color('white')
        self.ax_char.yaxis.label.set_color('white')
        self.ax_char.xaxis.label.set_color('white')
        self.ax_char.title.set_color('white')

        self.canvas_char = FigureCanvasTkAgg(self.fig_char, master=self.tab_character)
        self.canvas_char.draw()
        self.canvas_char.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def _create_time_distribution_plot(self):
        """Create activity time distribution pie chart"""
        self.fig_pie, self.ax_pie = plt.subplots(
            figsize=(6, 4),
            dpi=100,
            facecolor="#2b2b2b"
        )
        self.ax_pie.set_facecolor("#2b2b2b")

        self.canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=self.tab_time)
        self.canvas_pie.draw()
        self.canvas_pie.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def load_data_and_plot(self):
        """Load data from persistence and create plots with animation"""
        characters, _ = self.activity_persistence.load_characters()

        if not characters:
            # No data available
            self._show_no_data()
            return

        # Process data for daily trend
        daily_data = defaultdict(int)  # date -> total silver
        for char in characters:
            for record in char.records:
                daily_data[record.date] += record.silver_count

        if not daily_data:
            self._show_no_data()
            return

        # Sort by date
        sorted_dates = sorted(daily_data.keys())
        sorted_silver = [daily_data[d] for d in sorted_dates]

        # Calculate cumulative
        cumulative = []
        total = 0
        for s in sorted_silver:
            total += s
            cumulative.append(total)

        # Plot daily trend with animation
        self._plot_daily_trend_animated(sorted_dates, cumulative)

        # Process data for character comparison
        char_totals = []
        char_names = []
        for char in characters:
            total_grinding = 0
            for record in char.records:
                if record.activity_type == char.grinding_goal.activity_type if char.grinding_goal else None:
                    total_grinding += record.silver_count
            if char.grinding_goal:
                char_totals.append(char.grinding_goal.total_income - char.get_remaining_income())
                char_names.append(char.name)
            else:
                if total_grinding > 0:
                    char_totals.append(total_grinding)
                    char_names.append(char.name)

        if char_totals:
            self._plot_character_comparison_animated(char_names, char_totals)

        # Process data for time distribution
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
            self._plot_time_distribution_pie(grinding_total, star_total)

    def _plot_daily_trend_animated(self, sorted_dates, cumulative):
        """Plot daily trend with animation: line draws from left to right"""
        self.ax_daily.clear()
        self.ax_daily.set_facecolor("#2b2b2b")

        # Setup axes
        self.ax_daily.set_title("累计银币收益趋势", fontsize=14)
        self.ax_daily.set_xlabel("日期", fontsize=12)
        self.ax_daily.set_ylabel("累计银币", fontsize=12)

        # Format x-axis for dates
        self.ax_daily.xaxis.set_major_locator(DayLocator(interval=max(1, len(sorted_dates) // 10)))
        self.ax_daily.xaxis.set_major_formatter(DateFormatter('%m-%d'))

        # Convert dates to numbers for animation
        x_numeric = list(range(len(sorted_dates)))
        self.final_x = x_numeric
        self.final_y = cumulative

        # Start with empty line
        self.line, = self.ax_daily.plot([], [], color='#4CAF50', linewidth=3, label='累计收益')
        self.ax_daily.relim()
        self.ax_daily.autoscale_view()

        # Add grid
        self.ax_daily.grid(True, alpha=0.3, color='gray')
        self.ax_daily.legend(loc='upper left', facecolor="#333333", labelcolor="white")

        # Animate: gradually draw the line
        def animate_daily(frame):
            if frame < len(self.final_x):
                self.line.set_data(self.final_x[:frame+1], self.final_y[:frame+1])
            return [self.line]

        self.animation_daily = FuncAnimation(
            self.fig_daily,
            animate_daily,
            frames=len(self.final_x) + 10,
            interval=30,
            repeat=False
        )

        self.canvas_daily.draw()

    def _plot_character_comparison_animated(self, char_names, char_totals):
        """Plot character comparison with animated bars that grow from bottom"""
        self.ax_char.clear()
        self.ax_char.set_facecolor("#2b2b2b")

        self.ax_char.set_title("各角色已完成收益", fontsize=14)
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

        self.ax_char.tick_params(axis='x', rotation=45)
        self.ax_char.relim()
        self.ax_char.autoscale_view()

        # Animate: bars grow from bottom to top
        def animate_char(frame):
            progress = frame / 50  # 50 frames
            for i, bar in enumerate(self.bars):
                bar.set_height(self.final_heights[i] * progress)
            return self.bars

        self.animation_char = FuncAnimation(
            self.fig_char,
            animate_char,
            frames=50,
            interval=20,
            repeat=False
        )

        self.canvas_char.draw()

    def _plot_time_distribution_pie(self, grinding_minutes, star_minutes):
        """Plot time distribution as pie chart"""
        self.ax_pie.clear()
        self.ax_pie.set_facecolor("#2b2b2b")
        self.ax_pie.set_title("今日活动时长分布", fontsize=14, color='white')

        grinding_hours = grinding_minutes / 60
        star_hours = star_minutes / 60
        total_hours = grinding_hours + star_hours

        labels = [
            f'搬砖\n({grinding_hours:.1f}小时)',
            f'蹲星\n({star_hours:.1f}小时)'
        ]
        sizes = [grinding_minutes, star_minutes]
        colors = ['#2196F3', '#FF9800']
        wedges, texts, autotexts = self.ax_pie.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'color': 'white'}
        )
        self.ax_pie.axis('equal')  # Equal aspect ratio ensures pie is circular

        # Animate pie: rotation from 0
        def animate_pie(frame):
            self.ax_pie.clear()
            self.ax_pie.set_facecolor("#2b2b2b")
            self.ax_pie.set_title("今日活动时长分布", fontsize=14, color='white')
            start_angle = 90 - (frame * 3.6)  # 100 frames = 360 degrees
            wedges, texts, autotexts = self.ax_pie.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                startangle=start_angle,
                textprops={'color': 'white'}
            )
            self.ax_pie.axis('equal')
            return wedges

        self.animation_pie = FuncAnimation(
            self.fig_pie,
            animate_pie,
            frames=100,
            interval=10,
            repeat=False
        )

        self.canvas_pie.draw()

    def _show_no_data(self):
        """Show message when no data available"""
        for ax, canvas in [(self.ax_daily, self.canvas_daily),
                          (self.ax_char, self.canvas_char),
                          (self.ax_pie, self.canvas_pie)]:
            ax.clear()
            ax.text(0.5, 0.5, '暂无活动记录数据\n请先在活动统计中添加记录',
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=ax.transAxes,
                   color='white',
                   fontsize=14)
            canvas.draw()

    def refresh_plots(self):
        """Refresh data and replay all animations"""
        # Stop existing animations
        for anim in [getattr(self, 'animation_daily', None),
                    getattr(self, 'animation_char', None),
                    getattr(self, 'animation_pie', None)]:
            if anim is not None:
                anim.event_source.stop()

        self.load_data_and_plot()

    def replay_animation(self):
        """Replay all animations"""
        self.refresh_plots()

    def update(self):
        """Required interface for caching"""
        pass

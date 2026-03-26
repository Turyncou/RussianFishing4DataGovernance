"""Activity statistics frame (grinding + star waiting)"""
import customtkinter as ctk
from tkinter import ttk, Listbox, messagebox
from datetime import date
from typing import List, Optional
import json
import os
import requests

from core.models import (
    ActivityType, ActivityRecord, ActivityCharacter, ActivityGoal,
    SuggestionUserSettings, ActivitySuggestion
)
from data.persistence import ActivityPersistence
from .suggestion_calculator import calculate_suggestion


class ActivityFrame(ctk.CTkFrame):
    """Activity statistics frame - supports both grinding and star waiting"""

    def __init__(self, parent, persistence: ActivityPersistence):
        super().__init__(parent, fg_color="transparent", corner_radius=16)
        self.persistence = persistence
        self.characters: List[ActivityCharacter] = []
        self.current_character: Optional[ActivityCharacter] = None
        # Global suggestion settings (not per-character)
        self.global_suggestion_settings = SuggestionUserSettings()

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        """Create the widgets"""
        # Left side - character selection
        left_frame = ctk.CTkFrame(self, fg_color="#252525", width=200, corner_radius=12)
        left_frame.pack(side="left", fill="y", padx=8, pady=8)

        ctk.CTkLabel(
            left_frame,
            text="🎭 角色列表",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 8))

        # Use standard Listbox
        listbox_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        listbox_frame.pack(fill="y", expand=True, pady=8)
        self.character_listbox = Listbox(
            listbox_frame,
            bg="#333333",
            fg="white",
            selectbackground="#1f538d",
            selectforeground="white",
            borderwidth=0
        )
        self.character_listbox.pack(fill="both", expand=True)
        self.character_listbox.bind("<<ListboxSelect>>", self.on_character_select)

        # Character buttons
        add_char_btn = ctk.CTkButton(
            left_frame,
            text="+ 添加角色",
            command=self.add_character,
            width=100,
            corner_radius=8
        )
        add_char_btn.pack(pady=6)

        del_char_btn = ctk.CTkButton(
            left_frame,
            text="- 删除角色",
            command=self.delete_character,
            width=100,
            fg_color="#cc3333",
            hover_color="#aa2222",
            corner_radius=8
        )
        del_char_btn.pack(pady=6)

        # Right side - stats and table (use grid to avoid covering buttons)
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        right_frame.grid_rowconfigure(0, weight=1)  # Tab gets all remaining space
        right_frame.grid_columnconfigure(0, weight=1)

        # Top/Middle - tab view
        self.tab_view = ctk.CTkTabview(right_frame, corner_radius=8)
        self.tab_view.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        # Add tabs
        self.tab_grinding = self.tab_view.add("搬砖")
        self.tab_star_waiting = self.tab_view.add("蹲星")

        # Build activity tabs
        self.build_activity_tab(self.tab_grinding, ActivityType.GRINDING)
        self.build_activity_tab(self.tab_star_waiting, ActivityType.STAR_WAITING)

        # Bottom - suggestion buttons and result (fixed bottom, not covered)
        suggestion_bottom_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        suggestion_bottom_frame.grid(row=1, column=0, sticky="ew")

        # Suggestion buttons
        suggestion_btn_frame = ctk.CTkFrame(suggestion_bottom_frame, fg_color="transparent")
        suggestion_btn_frame.pack(fill="x", pady=(0, 8))

        # Center the buttons
        btn_container = ctk.CTkFrame(suggestion_btn_frame, fg_color="transparent")
        btn_container.pack(anchor="center")

        settings_btn = ctk.CTkButton(
            btn_container,
            text="建议设置",
            command=self.open_suggestion_settings,
            width=100
        )
        settings_btn.pack(side="left", padx=5)

        get_suggestion_btn = ctk.CTkButton(
            btn_container,
            text="获取建议",
            command=self.calculate_and_show_suggestion,
            width=100
        )
        get_suggestion_btn.pack(side="left", padx=5)

        # Suggestion result
        suggestion_frame = ctk.CTkFrame(suggestion_bottom_frame, fg_color="#252525", corner_radius=12)
        suggestion_frame.pack(fill="x")

        ctk.CTkLabel(
            suggestion_frame,
            text="活动安排建议",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        self.suggestion_text = ctk.CTkLabel(
            suggestion_frame,
            text="点击上方按钮获取安排建议",
            font=ctk.CTkFont(size=12),
            wraplength=600
        )
        self.suggestion_text.pack(pady=5)

    def build_activity_tab(self, parent, activity_type: ActivityType):
        """Build a tab for an activity"""
        # Initialize instance dicts
        if not hasattr(self, '_stats_labels'):
            self._stats_labels = {}
        if activity_type not in self._stats_labels:
            self._stats_labels[activity_type] = {}

        # Statistics cards
        stats_frame = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=12)
        stats_frame.pack(fill="x", pady=(0, 10))

        value_name = "银币" if activity_type == ActivityType.GRINDING else "蹲星成功数量"
        full_value_name = "今日获得银币" if activity_type == ActivityType.GRINDING else "今日蹲星成功数量"
        remaining_value_name = "剩余目标银币" if activity_type == ActivityType.GRINDING else "剩余蹲星成功数量"

        if activity_type == ActivityType.GRINDING:
            stats = [
                (f"今日获得银币", "today_value", "0"),
                ("今日搬砖时长", "today_duration", "0分钟"),
                (f"总计获得银币", "total_value", "0"),
                ("总计搬砖时长", "total_duration", "0分钟"),
                ("剩余目标银币", "remaining_value", "0"),
                ("已获得收入/总收入", "income_progress", "0 / 0"),
            ]
        else:
            stats = [
                (f"今日蹲星成功数量", "today_value", "0"),
                ("今日蹲星时长", "today_duration", "0分钟"),
                (f"总计蹲星成功数量", "total_value", "0"),
                ("总计蹲星时长", "total_duration", "0分钟"),
                ("剩余蹲星成功数量", "remaining_value", "0"),
                ("已获得收入/总收入", "income_progress", "0 / 0"),
            ]
        for i, (label_text, key, default) in enumerate(stats):
            row = i // 3
            col = i % 3
            frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            frame.grid(row=row, column=col, padx=15, pady=10)
            ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=14)).pack()
            label = ctk.CTkLabel(frame, text=default, font=ctk.CTkFont(size=16, weight="bold"))
            label.pack()
            self._stats_labels[activity_type][key] = label

        # Progress bars
        progress_frame = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=12)
        progress_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            progress_frame,
            text="目标进度",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        value_progress = ctk.CTkProgressBar(progress_frame)
        value_progress.pack(fill="x", padx=20, pady=5)
        value_progress.set(0)
        value_label = ctk.CTkLabel(progress_frame, text=f"{value_name}: 0%")
        value_label.pack()

        duration_progress = ctk.CTkProgressBar(progress_frame)
        duration_progress.pack(fill="x", padx=20, pady=5)
        duration_progress.set(0)
        duration_label = ctk.CTkLabel(progress_frame, text=f"时长: 0%")
        duration_label.pack(pady=(0, 10))

        if not hasattr(self, '_progress_bars'):
            self._progress_bars = {}
        if activity_type not in self._progress_bars:
            self._progress_bars[activity_type] = {}
        self._progress_bars[activity_type] = {
            'value': (value_progress, value_label),
            'duration': (duration_progress, duration_label)
        }

        # Set goal button
        set_goal_btn = ctk.CTkButton(
            progress_frame,
            text="设置目标",
            command=lambda: self.open_set_goal(activity_type),
            width=120
        )
        set_goal_btn.pack(pady=(0, 10))

        # Data table
        table_frame = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=12)
        table_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            table_frame,
            text="今日记录",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        # Treeview for records
        if activity_type == ActivityType.GRINDING:
            columns = ("日期", "银币", "时长(分钟)")
        else:
            columns = ("日期", "成功数量", "时长(分钟)")

        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.configure("Treeview", background="#333333", foreground="white", fieldbackground="#333333")

        if not hasattr(self, '_trees'):
            self._trees = {}
        self._trees[activity_type] = tree

        # Add record button
        add_record_btn = ctk.CTkButton(
            table_frame,
            text="+ 添加记录",
            command=lambda: self.add_record(activity_type),
            width=100
        )
        add_record_btn.pack(pady=10)

        # Save button
        save_btn = ctk.CTkButton(
            table_frame,
            text="保存数据",
            command=self.save_data,
            width=100
        )
        save_btn.pack(pady=(0, 10))

    def _get_stats_labels(self, activity_type: ActivityType):
        """Get stats labels dict for activity type"""
        if not hasattr(self, '_stats_labels'):
            self._stats_labels = {}
        if activity_type not in self._stats_labels:
            self._stats_labels[activity_type] = {}
        return self._stats_labels[activity_type]

    def _get_progress_bars(self, activity_type: ActivityType):
        """Get progress bars dict for activity type"""
        if not hasattr(self, '_progress_bars'):
            self._progress_bars = {}
        if activity_type not in self._progress_bars:
            self._progress_bars[activity_type] = {}
        return self._progress_bars[activity_type]

    def _get_trees(self, activity_type: ActivityType):
        """Get tree widget for activity type"""
        if not hasattr(self, '_trees'):
            self._trees = {}
        return self._trees[activity_type]

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
            self.character_listbox.selection_set(0)
            self.on_character_select(None)

    def update_character_list(self):
        """Update the character listbox"""
        self.character_listbox.delete(0, ctk.END)
        for char in self.characters:
            self.character_listbox.insert(ctk.END, char.name)

    def on_character_select(self, event):
        """Handle character selection"""
        selection = self.character_listbox.curselection()
        if not selection:
            self.current_character = None
            return
        index = selection[0]
        self.current_character = self.characters[index]
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
        stats_labels = self._get_stats_labels(activity_type)
        stats_labels['today_value'].configure(text=f"{today_value:,}")
        stats_labels['today_duration'].configure(text=f"{today_duration}分钟")
        stats_labels['total_value'].configure(text=f"{total_value:,}")
        stats_labels['total_duration'].configure(text=f"{total_duration}分钟")
        stats_labels['remaining_value'].configure(text=f"{remaining_value:,}")

        # Calculate income progress
        goal = (
            self.current_character.grinding_goal
            if activity_type == ActivityType.GRINDING
            else self.current_character.star_waiting_goal
        )
        if goal and goal.total_income > 0:
            total_income = goal.total_income
            remaining_income = 0
            if activity_type == ActivityType.GRINDING:
                if self.current_character.grinding_goal:
                    total_value, _, _ = self.current_character.calculate_totals(ActivityType.GRINDING)
                    if self.current_character.grinding_goal.target_value > 0:
                        progress = total_value / self.current_character.grinding_goal.target_value
                        progress = min(progress, 1.0)
                        earned_income = int(self.current_character.grinding_goal.total_income * progress)
                    else:
                        earned_income = 0
            else:
                if self.current_character.star_waiting_goal:
                    total_value, _, _ = self.current_character.calculate_totals(ActivityType.STAR_WAITING)
                    if self.current_character.star_waiting_goal.target_value > 0:
                        progress = total_value / self.current_character.star_waiting_goal.target_value
                        progress = min(progress, 1.0)
                        earned_income = int(self.current_character.star_waiting_goal.total_income * progress)
                    else:
                        earned_income = 0
            stats_labels['income_progress'].configure(text=f"{earned_income:,} / {total_income:,}")
        else:
            stats_labels['income_progress'].configure(text="0 / 0")

        # Update progress
        progress_value, progress_duration = self.current_character.calculate_progress(activity_type)
        progress_bars = self._get_progress_bars(activity_type)
        value_progress, value_label = progress_bars['value']
        duration_progress, duration_label = progress_bars['duration']

        if progress_value is not None:
            value_progress.set(progress_value)
            value_label.configure(text=f"{value_name}: {int(progress_value * 100)}%")
        else:
            value_progress.set(0)
            value_label.configure(text=f"{value_name}: 未设置目标")

        if progress_duration is not None:
            duration_progress.set(progress_duration)
            duration_label.configure(text=f"时长: {int(progress_duration * 100)}%")
        else:
            duration_progress.set(0)
            duration_label.configure(text=f"时长: 未设置目标")

        # Update table
        tree = self._get_trees(activity_type)
        for item in tree.get_children():
            tree.delete(item)
        today = date.today()
        for record in self.current_character.records:
            if record.date == today and record.activity_type == activity_type:
                if activity_type == ActivityType.GRINDING:
                    value = record.silver_count
                else:
                    value = record.success_count
                tree.insert(
                    "",
                    ctk.END,
                    values=(record.date.strftime("%Y-%m-%d"), f"{value:,}", record.duration_minutes)
                )

    def add_character(self):
        """Add a new character"""
        dialog = AddCharacterDialog(self.winfo_toplevel(), self.on_add_character_done)

    def on_add_character_done(self, name):
        """Callback after adding character"""
        if not name.strip():
            return
        char = ActivityCharacter(name.strip())
        self.characters.append(char)
        self.update_character_list()
        self.character_listbox.selection_clear(0, ctk.END)
        self.character_listbox.selection_set(len(self.characters) - 1)
        self.on_character_select(None)
        self.save_data()

    def delete_character(self):
        """Delete selected character"""
        if not self.current_character:
            return
        self.characters.remove(self.current_character)
        self.current_character = None
        self.update_character_list()
        self.save_data()
        self.update_all_displays()

    def open_set_goal(self, activity_type: ActivityType):
        """Open dialog to set activity goal"""
        if not self.current_character:
            return
        current_goal = (
            self.current_character.grinding_goal
            if activity_type == ActivityType.GRINDING
            else self.current_character.star_waiting_goal
        )
        dialog = SetGoalDialog(
            self.winfo_toplevel(),
            activity_type,
            current_goal,
            self.on_set_goal_done
        )

    def on_set_goal_done(self, activity_type: ActivityType, target_value, target_duration, total_income):
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
        if not self.current_character:
            return
        dialog = AddRecordDialog(self.winfo_toplevel(), activity_type, self.on_add_record_done)

    def on_add_record_done(self, activity_type: ActivityType, value, duration_minutes):
        """Callback after adding record"""
        if not self.current_character:
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
        self.current_character.add_record(record)
        self.update_display(activity_type)
        self.save_data()

    def open_suggestion_settings(self):
        """Open global suggestion settings dialog"""
        def callback(new_settings):
            self.global_suggestion_settings = new_settings
            self.save_data()
        dialog = SuggestionSettingsDialog(
            self.winfo_toplevel(),
            self.global_suggestion_settings,
            callback
        )

    def on_suggestion_settings_done(self, new_settings: SuggestionUserSettings):
        """Callback when suggestion settings updated"""
        if not self.current_character:
            return
        self.current_character.suggestion_settings = new_settings
        self.save_data()

    def calculate_and_show_suggestion(self):
        """Calculate and show the suggestion based on all characters"""
        if not self.characters:
            self.suggestion_text.configure(text="没有角色，无法生成建议")
            return

        # Check if any character has goals set
        has_any_goal = any(
            char.grinding_goal or char.star_waiting_goal
            for char in self.characters
        )
        if not has_any_goal:
            self.suggestion_text.configure(text="没有设置任何目标，无法生成建议\n请在各角色中设置搬砖/蹲星目标")
            return

        from .suggestion_calculator import calculate_suggestion_for_all
        suggestion = calculate_suggestion_for_all(self.characters, self.global_suggestion_settings)
        if not suggestion:
            self.suggestion_text.configure(text="所有目标已完成！恭喜！")
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
        self.suggestion_text.configure(text=text)

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_characters(self.characters, self.global_suggestion_settings)


class AddCharacterDialog(ctk.CTkToplevel):
    """Dialog to add a new character"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("添加角色")
        self.geometry("300x150")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="角色名称", font=ctk.CTkFont(size=14)).pack(pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, width=200)
        self.name_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self.confirm,
            width=80
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.cancel,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def cancel(self):
        """Cancel and close dialog"""
        # Delay release/destroy to let Tkinter process events properly
        self.after(10, lambda: [self.grab_release(), self.destroy()])

    def confirm(self):
        name = self.name_entry.get()
        if name.strip():
            self.callback(name.strip())
            # Delay release/destroy to let Tkinter process events properly
            self.after(10, lambda: [self.grab_release(), self.destroy()])


class SetGoalDialog(ctk.CTkToplevel):
    """Dialog to set activity goal"""

    def __init__(self, parent, activity_type: ActivityType, current_goal: Optional[ActivityGoal], callback):
        super().__init__(parent)
        self.callback = callback
        self.activity_type = activity_type
        value_name = "银币数量" if activity_type == ActivityType.GRINDING else "成功数量"

        self.title("设置目标")
        self.geometry("380x320")
        self.resizable(False, False)
        self.grab_set()

        # Use scrollable frame for content
        scrollable_frame = ctk.CTkScrollableFrame(self, width=360, height=280)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(scrollable_frame, text=f"目标{value_name}", font=ctk.CTkFont(size=14)).pack(pady=(20, 5))
        self.value_entry = ctk.CTkEntry(scrollable_frame, width=300)
        if current_goal:
            self.value_entry.insert(0, str(current_goal.target_value))
        self.value_entry.pack(pady=5)

        ctk.CTkLabel(scrollable_frame, text="目标时长(分钟)", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.duration_entry = ctk.CTkEntry(scrollable_frame, width=300)
        if current_goal:
            self.duration_entry.insert(0, str(current_goal.target_duration))
        self.duration_entry.pack(pady=5)

        ctk.CTkLabel(scrollable_frame, text="完成总收入(人民币)", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.income_entry = ctk.CTkEntry(scrollable_frame, width=300)
        if current_goal:
            self.income_entry.insert(0, str(current_goal.total_income))
        self.income_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self.confirm,
            width=80
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="清除目标",
            command=self.clear,
            width=80,
            fg_color="#cc3333",
            hover_color="#aa2222"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.cancel,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def cancel(self):
        """Cancel and close dialog"""
        # Delay release/destroy to let Tkinter process events properly
        self.after(10, lambda: [self.grab_release(), self.destroy()])

    def confirm(self):
        try:
            target_value = int((self.value_entry.get() or "0").strip())
            target_duration = int((self.duration_entry.get() or "0").strip())
            total_income = int((self.income_entry.get() or "0").strip())
            if target_value >= 0 and target_duration >= 0 and total_income >= 0:
                self.callback(self.activity_type, target_value, target_duration, total_income)
                # Delay release/destroy to let Tkinter process events properly
                self.after(10, lambda: self._cleanup())
            else:
                # Invalid values - show message
                messagebox.showwarning("输入错误", "数值不能为负数，请重新输入")
        except ValueError:
            # Invalid input - show message
            from tkinter import messagebox
            messagebox.showwarning("输入错误", "请输入有效的数字")

    def _cleanup(self):
        """Clean up and close dialog"""
        self.grab_release()
        self.destroy()

    def clear(self):
        self.callback(self.activity_type, 0, 0, 0)
        # Delay release/destroy to let Tkinter process events properly
        self.after(10, lambda: [self.grab_release(), self.destroy()])


class AddRecordDialog(ctk.CTkToplevel):
    """Dialog to add a new activity record"""

    def __init__(self, parent, activity_type: ActivityType, callback):
        super().__init__(parent)
        self.callback = callback
        self.activity_type = activity_type
        value_name = "银币数量" if activity_type == ActivityType.GRINDING else "成功数量"
        default_value = 1000000 if activity_type == ActivityType.GRINDING else 1

        self.title("添加记录")
        self.geometry("350x250")
        self.resizable(False, False)
        self.grab_set()

        # Use scrollable frame for content
        scrollable_frame = ctk.CTkScrollableFrame(self, width=330, height=210)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(scrollable_frame, text=f"日期: {date.today().strftime('%Y-%m-%d')}", font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

        ctk.CTkLabel(scrollable_frame, text=value_name, font=ctk.CTkFont(size=14)).pack(pady=(5, 5))
        self.value_entry = ctk.CTkEntry(scrollable_frame, width=250)
        self.value_entry.insert(0, str(default_value))
        self.value_entry.pack(pady=5)

        ctk.CTkLabel(scrollable_frame, text="时长(分钟)", font=ctk.CTkFont(size=14)).pack(pady=(5, 5))
        self.duration_entry = ctk.CTkEntry(scrollable_frame, width=250)
        self.duration_entry.insert(0, "120")
        self.duration_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self.confirm,
            width=80
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.cancel,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def cancel(self):
        """Cancel and close dialog"""
        # Delay release/destroy to let Tkinter process events properly
        self.after(10, lambda: [self.grab_release(), self.destroy()])

    def confirm(self):
        try:
            value = int(self.value_entry.get().strip())
            duration = int(self.duration_entry.get().strip())
            if value >= 0 and duration >= 0:
                self.callback(self.activity_type, value, duration)
                # Delay release/destroy to let Tkinter process events properly
                self.after(10, lambda: self._cleanup())
            else:
                # Invalid values - show message
                messagebox.showwarning("输入错误", "数值不能为负数，请重新输入")
        except ValueError:
            # Invalid input - show message
            from tkinter import messagebox
            messagebox.showwarning("输入错误", "请输入有效的数字")

    def _cleanup(self):
        """Clean up and close dialog"""
        self.grab_release()
        self.destroy()


class SuggestionSettingsDialog(ctk.CTkToplevel):
    """Dialog for suggestion settings"""

    def __init__(self, parent, current_settings: SuggestionUserSettings, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("建议设置")
        self.geometry("400x300")
        self.resizable(False, False)
        self.grab_set()

        # Use scrollable frame for content
        scrollable_frame = ctk.CTkScrollableFrame(self, width=380, height=260)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(scrollable_frame, text="每日总活动时长(小时)", font=ctk.CTkFont(size=14)).pack(pady=(20, 5))
        self.daily_total_entry = ctk.CTkEntry(scrollable_frame, width=300)
        self.daily_total_entry.insert(0, str(current_settings.daily_total_hours))
        self.daily_total_entry.pack(pady=5)

        ctk.CTkLabel(scrollable_frame, text="同时可进行搬砖活动数量", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.grinding_concurrent_entry = ctk.CTkEntry(scrollable_frame, width=300)
        self.grinding_concurrent_entry.insert(0, str(current_settings.grinding_concurrent))
        self.grinding_concurrent_entry.pack(pady=5)

        ctk.CTkLabel(scrollable_frame, text="同时可进行蹲星活动数量", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.star_concurrent_entry = ctk.CTkEntry(scrollable_frame, width=300)
        self.star_concurrent_entry.pack(pady=5)
        self.star_concurrent_entry.insert(0, str(current_settings.star_waiting_concurrent))

        ctk.CTkLabel(scrollable_frame, text="切换活动需要时间(分钟)", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.switch_entry = ctk.CTkEntry(scrollable_frame, width=300)
        self.switch_entry.insert(0, str(current_settings.switch_minutes))
        self.switch_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="保存",
            command=self.save,
            width=80
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.cancel,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def cancel(self):
        """Cancel and close dialog"""
        # Delay release/destroy to let Tkinter process events properly
        self.after(10, lambda: [self.grab_release(), self.destroy()])

    def save(self):
        try:
            daily = float(self.daily_total_entry.get().strip())
            grinding = int(self.grinding_concurrent_entry.get().strip())
            star = int(self.star_concurrent_entry.get().strip())
            switch = int(self.switch_entry.get().strip())
            if daily > 0 and grinding > 0 and star > 0 and switch >= 0:
                new_settings = SuggestionUserSettings(
                    daily_total_hours=daily,
                    grinding_concurrent=grinding,
                    star_waiting_concurrent=star,
                    switch_minutes=switch
                )
                self.callback(new_settings)
                # Delay release/destroy to let Tkinter process events properly
                self.after(10, lambda: self._cleanup())
            else:
                # Invalid values - show message
                messagebox.showwarning("输入错误", "数值必须大于0，请重新输入")
        except ValueError:
            # Invalid input - show message
            from tkinter import messagebox
            messagebox.showwarning("输入错误", "请输入有效的数字")

    def _cleanup(self):
        """Clean up and close dialog"""
        self.grab_release()
        self.destroy()

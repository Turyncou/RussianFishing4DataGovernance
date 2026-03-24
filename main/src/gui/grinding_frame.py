"""Grinding statistics frame"""
import customtkinter as ctk
from tkinter import ttk, Listbox
from datetime import date
from typing import List, Optional
import json
import os
import requests

from core.models import GrindingCharacter, GrindingRecord, GrindingGoal
from data.persistence import GrindingPersistence


class GrindingFrame(ctk.CTkFrame):
    """Grinding statistics frame"""

    def __init__(self, parent, persistence: GrindingPersistence):
        super().__init__(parent, fg_color="#2b2b2b", corner_radius=8)
        self.persistence = persistence
        self.characters: List[GrindingCharacter] = []
        self.current_character: Optional[GrindingCharacter] = None
        # Load saved API settings
        self.api_settings = self.load_api_settings()

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        """Create the widgets"""
        # Left side - character selection
        left_frame = ctk.CTkFrame(self, fg_color="transparent", width=200)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(
            left_frame,
            text="角色列表",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))

        # Use standard Listbox since CTkListbox not available in older CustomTkinter
        listbox_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        listbox_frame.pack(fill="y", expand=True, pady=5)
        self.character_listbox = Listbox(
            listbox_frame,
            bg="#333333",
            fg="white",
            selectbackground="#1f538d",
            selectforeground="white",
            height=10
        )
        self.character_listbox.pack(fill="both", expand=True)
        self.character_listbox.bind("<<ListboxSelect>>", self.on_character_select)

        # Character buttons
        add_char_btn = ctk.CTkButton(
            left_frame,
            text="+ 添加角色",
            command=self.add_character,
            width=100
        )
        add_char_btn.pack(pady=5)

        del_char_btn = ctk.CTkButton(
            left_frame,
            text="- 删除角色",
            command=self.delete_character,
            width=100,
            fg_color="#cc3333",
            hover_color="#aa2222"
        )
        del_char_btn.pack(pady=5)

        set_goal_btn = ctk.CTkButton(
            left_frame,
            text="设置目标",
            command=self.open_set_goal,
            width=100
        )
        set_goal_btn.pack(pady=5)

        # Right side - stats and table
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Statistics cards
        stats_frame = ctk.CTkFrame(right_frame, fg_color="#333333", corner_radius=8)
        stats_frame.pack(fill="x", pady=(0, 10))

        # Grid layout for stats
        self.stats_labels = {}
        stats = [
            ("今日银币", "today_silver", "0"),
            ("今日时长", "today_duration", "0分钟"),
            ("总计银币", "total_silver", "0"),
            ("总计时长", "total_duration", "0分钟"),
        ]
        for i, (label_text, key, default) in enumerate(stats):
            row = i // 2
            col = i % 2
            frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            frame.grid(row=row, column=col, padx=20, pady=15)
            ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=14)).pack()
            label = ctk.CTkLabel(frame, text=default, font=ctk.CTkFont(size=18, weight="bold"))
            label.pack()
            self.stats_labels[key] = label

        # Progress bars
        progress_frame = ctk.CTkFrame(right_frame, fg_color="#333333", corner_radius=8)
        progress_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            progress_frame,
            text="目标进度",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        self.silver_progress = ctk.CTkProgressBar(progress_frame)
        self.silver_progress.pack(fill="x", padx=20, pady=5)
        self.silver_progress.set(0)
        self.silver_label = ctk.CTkLabel(progress_frame, text="银币: 0%")
        self.silver_label.pack()

        self.duration_progress = ctk.CTkProgressBar(progress_frame)
        self.duration_progress.pack(fill="x", padx=20, pady=5)
        self.duration_progress.set(0)
        self.duration_label = ctk.CTkLabel(progress_frame, text="时长: 0%")
        self.duration_label.pack(pady=(0, 10))

        # API Suggestion area
        self.suggestion_frame = ctk.CTkFrame(right_frame, fg_color="#333333", corner_radius=8)
        self.suggestion_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.suggestion_frame,
            text="AI建议",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        self.suggestion_text = ctk.CTkLabel(
            self.suggestion_frame,
            text="点击下方按钮获取建议\n需先设置API接口地址",
            font=ctk.CTkFont(size=12),
            wraplength=600
        )
        self.suggestion_text.pack(pady=5)

        # Buttons for API
        api_btn_frame = ctk.CTkFrame(self.suggestion_frame, fg_color="transparent")
        api_btn_frame.pack(pady=(5, 10))

        api_settings_btn = ctk.CTkButton(
            api_btn_frame,
            text="API设置",
            command=self.open_api_settings,
            width=100
        )
        api_settings_btn.pack(side="left", padx=5)

        get_suggestion_btn = ctk.CTkButton(
            api_btn_frame,
            text="获取建议",
            command=self.get_api_suggestion,
            width=100
        )
        get_suggestion_btn.pack(side="left", padx=5)

        # Data table
        table_frame = ctk.CTkFrame(right_frame, fg_color="#333333", corner_radius=8)
        table_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            table_frame,
            text="今日记录",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))

        # Treeview for records
        columns = ("日期", "银币", "时长(分钟)")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.configure("Treeview", background="#333333", foreground="white", fieldbackground="#333333")

        # Add record button
        add_record_btn = ctk.CTkButton(
            table_frame,
            text="+ 添加记录",
            command=self.add_record,
            width=100
        )
        add_record_btn.pack(pady=10)

        # Add record button at bottom
        add_record_btn = ctk.CTkButton(
            table_frame,
            text="保存数据",
            command=self.save_data,
            width=100
        )
        add_record_btn.pack(pady=(0, 10))

    def load_data(self):
        """Load data from persistence"""
        self.characters = self.persistence.load_characters()
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
        self.update_display()

    def update_display(self):
        """Update the display with current character data"""
        if not self.current_character:
            return

        # Update stats
        today_silver, today_duration = self.current_character.calculate_today_totals()
        total_silver, total_duration = self.current_character.calculate_totals()

        self.stats_labels['today_silver'].configure(text=f"{today_silver:,}")
        self.stats_labels['today_duration'].configure(text=f"{today_duration}分钟")
        self.stats_labels['total_silver'].configure(text=f"{total_silver:,}")
        self.stats_labels['total_duration'].configure(text=f"{total_duration}分钟")

        # Update progress
        progress_silver, progress_duration = self.current_character.calculate_progress()

        if progress_silver is not None:
            self.silver_progress.set(progress_silver)
            self.silver_label.configure(text=f"银币: {int(progress_silver * 100)}%")
        else:
            self.silver_progress.set(0)
            self.silver_label.configure(text="银币: 未设置目标")

        if progress_duration is not None:
            self.duration_progress.set(progress_duration)
            self.duration_label.configure(text=f"时长: {int(progress_duration * 100)}%")
        else:
            self.duration_progress.set(0)
            self.duration_label.configure(text="时长: 未设置目标")

        # Update table
        for item in self.tree.get_children():
            self.tree.delete(item)
        today = date.today()
        for record in self.current_character.records:
            if record.date == today:
                self.tree.insert(
                    "",
                    ctk.END,
                    values=(record.date.strftime("%Y-%m-%d"), f"{record.silver_count:,}", record.duration_minutes)
                )

    def add_character(self):
        """Add a new character"""
        dialog = AddCharacterDialog(self.winfo_toplevel(), self.on_add_character_done)

    def on_add_character_done(self, name):
        """Callback after adding character"""
        if not name.strip():
            return
        char = GrindingCharacter(name.strip())
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
        self.update_display()

    def open_set_goal(self):
        """Open dialog to set grinding goal"""
        if not self.current_character:
            return
        dialog = SetGoalDialog(
            self.winfo_toplevel(),
            self.current_character.goal,
            self.on_set_goal_done
        )

    def on_set_goal_done(self, target_silver, target_duration):
        """Callback after setting goal"""
        if not self.current_character:
            return
        if target_silver <= 0 and target_duration <= 0:
            self.current_character.goal = None
        else:
            self.current_character.goal = GrindingGoal(target_silver, target_duration)
        self.update_display()
        self.save_data()

    def add_record(self):
        """Add a new record for today"""
        if not self.current_character:
            return
        dialog = AddRecordDialog(self.winfo_toplevel(), self.on_add_record_done)

    def on_add_record_done(self, silver_count, duration_minutes):
        """Callback after adding record"""
        if not self.current_character:
            return
        record = GrindingRecord(date.today(), silver_count, duration_minutes)
        self.current_character.add_record(record)
        self.update_display()
        self.save_data()

    def get_api_suggestion(self):
        """Get API suggestion based on current data"""
        if not self.current_character:
            return

        total_silver, total_duration = self.current_character.calculate_totals()
        if total_duration == 0:
            self.suggestion_text.configure(text="还没有数据，无法生成建议")
            return

        # Try to call API if configured
        if self.api_settings.get('api_url') and self.api_settings.get('api_key'):
            try:
                data = {
                    'current_total_silver': total_silver,
                    'current_total_duration_minutes': total_duration,
                    'goal': None
                }
                if self.current_character.goal:
                    data['goal'] = {
                        'target_silver': self.current_character.goal.target_silver,
                        'target_duration_minutes': self.current_character.goal.target_duration
                    }

                headers = {
                    'Authorization': f"Bearer {self.api_settings['api_key']}",
                    'Content-Type': 'application/json'
                }

                response = requests.post(
                    self.api_settings['api_url'],
                    json=data,
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    suggestion_text = result.get('suggestion', 'No suggestion received')
                    if 'silver_per_hour' in result:
                        suggestion_text = f"当前效率: {int(result['silver_per_hour']):,} 银币/小时\n"
                        if 'estimated_completion_days' in result and self.current_character.goal:
                            suggestion_text += f"预计完成天数: {result['estimated_completion_days']:.1f} 天\n"
                        if 'recommendation' in result:
                            suggestion_text += f"建议: {result['recommendation']}"
                    self.suggestion_text.configure(text=suggestion_text)
                    return
                else:
                    self.suggestion_text.configure(text=f"API请求失败: HTTP {response.status_code}\n使用本地计算:\n\n")
            except Exception as e:
                self.suggestion_text.configure(text=f"API调用错误: {str(e)}\n使用本地计算:\n\n")

        # Fallback to local calculation
        silver_per_hour = (total_silver / total_duration) * 60

        suggestion_text = f"当前效率: {int(silver_per_hour):,} 银币/小时\n"

        if self.current_character.goal:
            remaining_silver = self.current_character.goal.target_silver - total_silver
            remaining_silver = max(0, remaining_silver)
            if silver_per_hour > 0:
                days_needed = (remaining_silver / silver_per_hour)
                suggestion_text += f"预计完成天数: {days_needed:.1f} 天\n"

                if days_needed <= 7:
                    suggestion_text += "建议: 继续保持，很快就能完成目标！"
                elif days_needed <= 30:
                    suggestion_text += "建议: 保持当前节奏，稳步推进。"
                else:
                    suggestion_text += "建议: 目标较大，建议分段完成。"
        else:
            suggestion_text += "未设置目标，可以设置目标后获取更准确建议。\n建议: 根据自身情况设置一个合理目标吧！"

        self.suggestion_text.configure(text=suggestion_text)

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_characters(self.characters)
        self.save_api_settings()

    def load_api_settings(self):
        """Load saved API settings from file"""
        api_file = os.path.join(os.path.dirname(self.persistence.file_path), 'api_settings.json')
        default_settings = {
            'api_url': '',
            'api_key': ''
        }
        if not os.path.exists(api_file):
            return default_settings
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default_settings

    def save_api_settings(self):
        """Save API settings to file"""
        api_file = os.path.join(os.path.dirname(self.persistence.file_path), 'api_settings.json')
        directory = os.path.dirname(api_file)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(api_file, 'w', encoding='utf-8') as f:
            json.dump(self.api_settings, f, ensure_ascii=False, indent=2)

    def open_api_settings(self):
        """Open API settings dialog"""
        dialog = ApiSettingsDialog(
            self.winfo_toplevel(),
            self.api_settings,
            self.on_api_settings_done
        )

    def on_api_settings_done(self, new_settings):
        """Callback when API settings are updated"""
        self.api_settings = new_settings
        self.save_api_settings()


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
            command=self.destroy,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def confirm(self):
        name = self.name_entry.get()
        if name.strip():
            self.callback(name.strip())
            self.destroy()


class SetGoalDialog(ctk.CTkToplevel):
    """Dialog to set grinding goal"""

    def __init__(self, parent, current_goal: Optional[GrindingGoal], callback):
        super().__init__(parent)
        self.callback = callback
        self.title("设置目标")
        self.geometry("350x250")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="目标银币数量", font=ctk.CTkFont(size=14)).pack(pady=(20, 5))
        self.silver_entry = ctk.CTkEntry(self, width=250)
        if current_goal:
            self.silver_entry.insert(0, str(current_goal.target_silver))
        self.silver_entry.pack(pady=5)

        ctk.CTkLabel(self, text="目标时长(分钟)", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.duration_entry = ctk.CTkEntry(self, width=250)
        if current_goal:
            self.duration_entry.insert(0, str(current_goal.target_duration))
        self.duration_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
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
            command=self.destroy,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def confirm(self):
        try:
            target_silver = int(self.silver_entry.get() or "0")
            target_duration = int(self.duration_entry.get() or "0")
            self.callback(target_silver, target_duration)
            self.destroy()
        except ValueError:
            pass

    def clear(self):
        self.callback(0, 0)
        self.destroy()


class AddRecordDialog(ctk.CTkToplevel):
    """Dialog to add a new grinding record"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("添加记录")
        self.geometry("350x220")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text=f"日期: {date.today().strftime('%Y-%m-%d')}", font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

        ctk.CTkLabel(self, text="银币数量", font=ctk.CTkFont(size=14)).pack(pady=(5, 5))
        self.silver_entry = ctk.CTkEntry(self, width=250)
        self.silver_entry.pack(pady=5)
        self.silver_entry.insert(0, "1000000")

        ctk.CTkLabel(self, text="时长(分钟)", font=ctk.CTkFont(size=14)).pack(pady=(5, 5))
        self.duration_entry = ctk.CTkEntry(self, width=250)
        self.duration_entry.pack(pady=5)
        self.duration_entry.insert(0, "120")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
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
            command=self.destroy,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def confirm(self):
        try:
            silver = int(self.silver_entry.get())
            duration = int(self.duration_entry.get())
            if silver >= 0 and duration >= 0:
                self.callback(silver, duration)
                self.destroy()
        except ValueError:
            pass


class ApiSettingsDialog(ctk.CTkToplevel):
    """Dialog for API settings"""

    def __init__(self, parent, current_settings, callback):
        super().__init__(parent)
        self.callback = callback
        self.current_settings = current_settings

        self.title("API设置")
        self.geometry("450x300")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text="API接口地址",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(20, 5))
        self.url_entry = ctk.CTkEntry(self, width=380)
        self.url_entry.insert(0, current_settings.get('api_url', ''))
        self.url_entry.pack(pady=5)

        ctk.CTkLabel(
            self,
            text="API Key",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(10, 5))
        self.key_entry = ctk.CTkEntry(self, width=380, show='*')
        self.key_entry.insert(0, current_settings.get('api_key', ''))
        self.key_entry.pack(pady=5)

        ctk.CTkLabel(
            self,
            text="留空则使用本地计算",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(pady=(5, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
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
            command=self.destroy,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def save(self):
        """Save the new settings"""
        new_settings = {
            'api_url': self.url_entry.get().strip(),
            'api_key': self.key_entry.get().strip()
        }
        self.callback(new_settings)
        self.destroy()

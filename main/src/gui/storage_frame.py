"""Storage duration tracking frame"""
import customtkinter as ctk
from tkinter import ttk
from CTkMessagebox import CTkMessagebox
from typing import List

from core.models import StorageCharacter
from data.persistence import StoragePersistence


class StorageFrame(ctk.CTkFrame):
    """Storage duration tracking frame"""

    def __init__(self, parent, persistence: StoragePersistence):
        super().__init__(parent, fg_color="transparent", corner_radius=16)
        self.persistence = persistence
        self.characters: List[StorageCharacter] = []
        # Sorting state
        self._sort_column = "角色名称"
        self._sort_ascending = True

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        """Create the widgets"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="📦 存储时长统计",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(15, 10))

        # Button bar
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=8)

        add_btn = ctk.CTkButton(
            btn_frame,
            text="+ 添加角色",
            command=self.add_character,
            width=100,
            corner_radius=8
        )
        add_btn.pack(side="left", padx=5)

        delete_btn = ctk.CTkButton(
            btn_frame,
            text="- 删除角色",
            command=self.delete_selected,
            width=100,
            fg_color="#cc3333",
            hover_color="#aa2222",
            corner_radius=8
        )
        delete_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 保存数据",
            command=self.save_data,
            width=100,
            corner_radius=8
        )
        save_btn.pack(side="right", padx=5)

        # Table
        table_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12)
        table_frame.pack(fill="both", expand=True, padx=15, pady=10)

        columns = ("角色名称", "剩余时长(分钟)", "操作")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        # Bind click on heading for sorting
        for col in columns:
            if col != "操作":  # Don't sort on operation column
                self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))
            else:
                self.tree.heading(col, text=col)
            if col == "角色名称":
                self.tree.column(col, width=200, anchor="center")
            elif col == "剩余时长(分钟)":
                self.tree.column(col, width=150, anchor="center")
            else:
                self.tree.column(col, width=300, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure dark theme style for Treeview - only need to do this once globally
        if not hasattr(self.__class__, '_tree_style_configured'):
            style = ttk.Style()
            style.configure("Treeview", background="#333333", foreground="white", fieldbackground="#333333")
            # Also configure heading for better dark theme appearance
            style.configure("Treeview.Heading", background="#444444", foreground="white")
            setattr(self.__class__, '_tree_style_configured', True)

        # Control area for adding/removing minutes
        control_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12)
        control_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            control_frame,
            text="⚡ 调整时长",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(12, 8))

        input_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        input_frame.pack(pady=8)

        ctk.CTkLabel(input_frame, text="分钟数: ", font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        self.minutes_entry = ctk.CTkEntry(input_frame, width=100, corner_radius=8)
        self.minutes_entry.insert(0, "60")
        self.minutes_entry.pack(side="left", padx=5)

        add_btn = ctk.CTkButton(
            input_frame,
            text="+ 增加",
            command=self.add_minutes,
            width=80,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            corner_radius=8
        )
        add_btn.pack(side="left", padx=10)

        remove_btn = ctk.CTkButton(
            input_frame,
            text="- 减少",
            command=self.remove_minutes,
            width=80,
            fg_color="#F44336",
            hover_color="#D32F2F",
            corner_radius=8
        )
        remove_btn.pack(side="left", padx=5)

    def load_data(self):
        """Load data from persistence"""
        self.characters = self.persistence.load_characters()
        self.update_table()

    def update_table(self):
        """Update the table display"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for char in self.characters:
            self.tree.insert(
                "",
                ctk.END,
                values=(char.name, f"{char.remaining_minutes:,}", "")
            )

    def get_selected_character(self):
        """Get the currently selected character"""
        selection = self.tree.selection()
        if not selection:
            return None
        index = self.tree.index(selection[0])
        if 0 <= index < len(self.characters):
            return self.characters[index]
        return None

    def _sort_by_column(self, column: str):
        """Sort the storage character list by the clicked column"""
        # Toggle sort order if clicking the same column again
        if column == self._sort_column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True

        # Get key extractor based on column
        if column == "角色名称":
            key_func = lambda c: c.name.lower()
        elif column == "剩余时长(分钟)":
            key_func = lambda c: c.remaining_minutes
        else:
            key_func = lambda c: c.name.lower()

        # Sort
        self.characters.sort(key=key_func, reverse=not self._sort_ascending)
        self.update_table()

    def add_character(self):
        """Add a new character"""
        dialog = AddStorageCharacterDialog(self.winfo_toplevel(), self.on_add_character_done)

    def on_add_character_done(self, name, minutes: int):
        """Callback after adding character"""
        if not name.strip():
            return
        char = StorageCharacter(name.strip(), minutes)
        self.characters.append(char)
        self.update_table()
        self.save_data()

    def delete_selected(self):
        """Delete selected character"""
        char = self.get_selected_character()
        if char:
            self.characters.remove(char)
            self.update_table()
            self.save_data()

    def add_minutes(self):
        """Add minutes to selected character"""
        char = self.get_selected_character()
        if not char:
            CTkMessagebox(title="提示", message="请先选择一个角色", icon="warning", option_1="确定")
            return
        try:
            minutes = int(self.minutes_entry.get().strip())
            if minutes <= 0:
                CTkMessagebox(title="输入错误", message="分钟数必须大于0", icon="warning", option_1="确定")
                return
            char.add_minutes(minutes)
            self.update_table()
            self.save_data()
        except ValueError:
            CTkMessagebox(title="输入错误", message="请输入有效的分钟数", icon="warning", option_1="确定")

    def remove_minutes(self):
        """Remove minutes from selected character"""
        char = self.get_selected_character()
        if not char:
            CTkMessagebox(title="提示", message="请先选择一个角色", icon="warning", option_1="确定")
            return
        try:
            minutes = int(self.minutes_entry.get().strip())
            if minutes <= 0:
                CTkMessagebox(title="输入错误", message="分钟数必须大于0", icon="warning", option_1="确定")
                return
            char.remove_minutes(minutes)
            self.update_table()
            self.save_data()
        except ValueError:
            CTkMessagebox(title="输入错误", message="请输入有效的分钟数", icon="warning", option_1="确定")

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_characters(self.characters)


class AddStorageCharacterDialog(ctk.CTkToplevel):
    """Dialog to add a new storage character"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("添加存储角色")
        self.geometry("350x200")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="角色名称", font=ctk.CTkFont(size=14)).pack(pady=(30, 10))
        self.name_entry = ctk.CTkEntry(self, width=250)
        self.name_entry.pack(pady=10)

        ctk.CTkLabel(self, text="初始剩余时长(分钟)", font=ctk.CTkFont(size=14)).pack(pady=(10, 10))
        self.minutes_entry = ctk.CTkEntry(self, width=250)
        self.minutes_entry.insert(0, "0")
        self.minutes_entry.pack(pady=10)

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
        name = self.name_entry.get().strip()
        if not name:
            CTkMessagebox(title="输入错误", message="角色名称不能为空", icon="warning", option_1="确定")
            self.after(200, lambda: self.grab_set())
            return
        try:
            minutes = int(self.minutes_entry.get().strip())
            # Will be clamped to >=0 by model
        except ValueError:
            CTkMessagebox(title="输入错误", message="请输入有效的分钟数", icon="warning", option_1="确定")
            self.after(200, lambda: self.grab_set())
            return

        self.callback(name, minutes)
        self.grab_release()
        self.destroy()

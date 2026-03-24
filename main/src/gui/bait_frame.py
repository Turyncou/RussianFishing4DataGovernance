"""Bait/Tackle consumption tracking frame - tracks bought/used/remaining"""
import customtkinter as ctk
from tkinter import ttk
from CTkMessagebox import CTkMessagebox
from typing import List

from core.models import BaitConsumption
from data.persistence import BaitPersistence


class BaitFrame(ctk.CTkFrame):
    """Bait/Tackle consumption tracking frame - tracks bought/used/remaining"""

    def __init__(self, parent, persistence: BaitPersistence):
        super().__init__(parent, fg_color="transparent", corner_radius=16)
        self.persistence = persistence
        self.baits: List[BaitConsumption] = []
        self.selected_bait: BaitConsumption | None = None

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        """Create the widgets"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="🎣 饵料/钓具库存统计",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(15, 10))

        # Button bar
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=8)

        add_btn = ctk.CTkButton(
            btn_frame,
            text="+ 添加饵料/钓具",
            command=self.add_bait,
            width=120,
            corner_radius=8
        )
        add_btn.pack(side="left", padx=5)

        delete_btn = ctk.CTkButton(
            btn_frame,
            text="- 删除当前",
            command=self.delete_selected,
            width=100,
            fg_color="#cc3333",
            hover_color="#aa2222",
            corner_radius=8
        )
        delete_btn.pack(side="left", padx=5)

        # Add stock / use stock area
        adjust_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12)
        adjust_frame.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(
            adjust_frame,
            text="⚡ 调整库存",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(12, 8))

        input_row = ctk.CTkFrame(adjust_frame, fg_color="transparent")
        input_row.pack(pady=8, padx=15)

        ctk.CTkLabel(input_row, text="数量: ", font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        self.quantity_entry = ctk.CTkEntry(input_row, width=100, corner_radius=8)
        self.quantity_entry.insert(0, "10")
        self.quantity_entry.pack(side="left", padx=5)

        add_stock_btn = ctk.CTkButton(
            input_row,
            text="➕ 增加库存",
            command=self.add_stock,
            width=100,
            corner_radius=8,
            fg_color="#4CAF50",
            hover_color="#388E3C"
        )
        add_stock_btn.pack(side="left", padx=15)

        use_stock_btn = ctk.CTkButton(
            input_row,
            text="➖ 使用库存",
            command=self.use_stock,
            width=100,
            corner_radius=8,
            fg_color="#F44336",
            hover_color="#D32F2F"
        )
        use_stock_btn.pack(side="left", padx=5)

        # Bait list table
        table_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12)
        table_frame.pack(fill="both", expand=True, padx=15, pady=10)

        columns = ("名称", "已购买", "已使用", "剩余")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "名称":
                self.tree.column(col, width=200, anchor="center")
            else:
                self.tree.column(col, width=120, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_bait_select)

        style = ttk.Style()
        style.configure("Treeview", background="#333333", foreground="white", fieldbackground="#333333")

        # Status / summary
        summary_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12)
        summary_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            summary_frame,
            text="📊 汇总统计",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(8, 5))

        self.summary_label = ctk.CTkLabel(
            summary_frame,
            text="总品类: 0  |  总剩余: 0",
            font=ctk.CTkFont(size=14)
        )
        self.summary_label.pack(pady=(0, 8))

    def load_data(self):
        """Load data from persistence"""
        self.baits = self.persistence.load_baits()
        self.update_table()
        self.update_summary()

    def update_table(self):
        """Update the table display"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for bait in self.baits:
            self.tree.insert(
                "",
                ctk.END,
                values=(bait.name, bait.total_bought, bait.total_used, bait.remaining)
            )

        self.update_summary()

    def update_summary(self):
        """Update summary display"""
        total_types = len(self.baits)
        total_remaining = sum(b.remaining for b in self.baits)
        self.summary_label.configure(text=f"总品类: {total_types}  |  总剩余: {total_remaining:,}")

    def on_bait_select(self, event):
        """Handle bait selection"""
        selection = self.tree.selection()
        if not selection:
            self.selected_bait = None
            return
        index = self.tree.index(selection[0])
        if 0 <= index < len(self.baits):
            self.selected_bait = self.baits[index]

    def add_bait(self):
        """Open dialog to add new bait"""
        dialog = AddBaitDialog(self.winfo_toplevel(), self.on_add_bait_done)

    def on_add_bait_done(self, name: str, initial_stock: int):
        """Callback after adding bait"""
        if not name.strip():
            return

        # Check duplicate
        for b in self.baits:
            if b.name == name.strip():
                CTkMessagebox(title="错误", message="该饵料名称已存在", icon="cancel")
                return

        new_bait = BaitConsumption(
            name=name.strip(),
            total_bought=initial_stock,
            total_used=0
        )
        self.baits.append(new_bait)
        self.selected_bait = new_bait
        self.update_table()
        self.save_data()
        CTkMessagebox(title="成功", message="添加成功", icon="info")

    def delete_selected(self):
        """Delete selected bait"""
        if not self.selected_bait:
            CTkMessagebox(title="提示", message="请先选择一个饵料/钓具", icon="warning")
            return

        confirm = CTkMessagebox(
            title="确认删除",
            message=f"确定要删除 '{self.selected_bait.name}' 吗？\n此操作不可恢复！",
            icon="warning",
            option_1="取消",
            option_2="删除"
        )
        if confirm.get() == "删除":
            self.baits.remove(self.selected_bait)
            self.selected_bait = None
            self.update_table()
            self.save_data()

    def add_stock(self):
        """Add stock to selected bait"""
        if not self.selected_bait:
            CTkMessagebox(title="提示", message="请先选择一个饵料/钓具", icon="warning")
            return

        try:
            quantity = int(self.quantity_entry.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            CTkMessagebox(title="错误", message="请输入有效的正整数", icon="cancel")
            return

        self.selected_bait.add_stock(quantity)
        self.update_table()
        self.save_data()
        CTkMessagebox(title="成功", message=f"已增加 {quantity} 个 [{self.selected_bait.name}]", icon="info")

    def use_stock(self):
        """Use stock from selected bait"""
        if not self.selected_bait:
            CTkMessagebox(title="提示", message="请先选择一个饵料/钓具", icon="warning")
            return

        try:
            quantity = int(self.quantity_entry.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            CTkMessagebox(title="错误", message="请输入有效的正整数", icon="cancel")
            return

        if quantity > self.selected_bait.remaining:
            confirm = CTkMessagebox(
                title="库存不足",
                message=f"剩余只有 {self.selected_bait.remaining}，但要使用 {quantity}\n是否继续使用全部剩余？",
                icon="warning",
                option_1="取消",
                option_2="继续"
            )
            if confirm.get() != "继续":
                return

        self.selected_bait.use_stock(quantity)
        self.update_table()
        self.save_data()
        CTkMessagebox(title="成功", message=f"已使用 {quantity} 个 [{self.selected_bait.name}]", icon="info")

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_baits(self.baits)


class AddBaitDialog(ctk.CTkToplevel):
    """Dialog to add new bait"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("添加饵料/钓具")
        self.geometry("350x250")
        self.resizable(False, False)
        self.grab_set()

        scrollable_frame = ctk.CTkScrollableFrame(self, width=330, height=200)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            scrollable_frame,
            text="饵料/钓具名称",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(20, 5))
        self.name_entry = ctk.CTkEntry(scrollable_frame, width=250, corner_radius=8)
        self.name_entry.pack(pady=5)

        ctk.CTkLabel(
            scrollable_frame,
            text="初始库存数量",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(15, 5))
        self.stock_entry = ctk.CTkEntry(scrollable_frame, width=250, corner_radius=8)
        self.stock_entry.insert(0, "100")
        self.stock_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self.confirm,
            width=80,
            corner_radius=8
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.destroy,
            width=80,
            fg_color="#888888",
            hover_color="#666666",
            corner_radius=8
        ).pack(side="left", padx=5)

    def confirm(self):
        """Confirm and add"""
        name = self.name_entry.get().strip()
        try:
            initial_stock = int(self.stock_entry.get())
            if initial_stock < 0:
                initial_stock = 0
        except ValueError:
            initial_stock = 0
        if name:
            self.callback(name, initial_stock)
            self.destroy()

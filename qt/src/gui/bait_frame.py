"""Bait/Tackle consumption tracking frame - tracks bought/used/remaining"""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QLineEdit, QMessageBox,
    QGroupBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.models import BaitConsumption
from src.data.persistence import BaitPersistence


class BaitFrame(QWidget):
    """Bait/Tackle consumption tracking frame - tracks bought/used/remaining"""

    def __init__(self, persistence: BaitPersistence):
        super().__init__()
        self.persistence = persistence
        self.baits: List[BaitConsumption] = []
        self.selected_bait: BaitConsumption | None = None
        # Sorting state
        self._sort_column = "名称"
        self._sort_ascending = True

        self._create_widgets()
        self.load_data()

    def _create_widgets(self):
        """Create the widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("🎣 饵料/钓具库存统计")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)

        # Button bar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        add_btn = QPushButton("+ 添加饵料/钓具")
        add_btn.setFixedWidth(140)
        add_btn.clicked.connect(self.add_bait)
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("- 删除当前")
        delete_btn.setFixedWidth(100)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc3333;
            }
            QPushButton:hover {
                background-color: #aa2222;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        save_btn = QPushButton("💾 保存数据")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        # Adjust stock area
        adjust_group = QGroupBox("⚡ 调整库存")
        adjust_group.setFont(QFont("Segoe UI", 16, QFont.Bold))
        adjust_layout = QHBoxLayout(adjust_group)
        adjust_layout.setContentsMargins(12, 12, 12, 12)
        adjust_layout.setSpacing(10)
        adjust_layout.setAlignment(Qt.AlignCenter)

        adjust_layout.addWidget(QLabel("数量: "))
        self.quantity_edit = QLineEdit()
        self.quantity_edit.setText("10")
        self.quantity_edit.setFixedWidth(100)
        adjust_layout.addWidget(self.quantity_edit)

        add_stock_btn = QPushButton("➕ 增加库存")
        add_stock_btn.setFixedWidth(120)
        add_stock_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        add_stock_btn.clicked.connect(self.add_stock)
        adjust_layout.addWidget(add_stock_btn)

        use_stock_btn = QPushButton("➖ 使用库存")
        use_stock_btn.setFixedWidth(120)
        use_stock_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        use_stock_btn.clicked.connect(self.use_stock)
        adjust_layout.addWidget(use_stock_btn)

        layout.addWidget(adjust_group)

        # Bait list table
        table_group = QGroupBox("饵料列表")
        table_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["名称", "已购买", "已使用", "剩余"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.selectionModel().selectionChanged.connect(self._on_bait_select)

        table_layout.addWidget(self.table)
        layout.addWidget(table_group, 1)

        # Summary
        summary_group = QGroupBox("📊 汇总统计")
        summary_group.setFont(QFont("Segoe UI", 16, QFont.Bold))
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(8, 8, 8, 8)

        self.summary_label = QLabel("总品类: 0  |  总剩余: 0")
        self.summary_label.setFont(QFont("Segoe UI", 14))
        summary_layout.addWidget(self.summary_label)

        layout.addWidget(summary_group)

        self.setLayout(layout)

    def load_data(self):
        """Load data from persistence"""
        self.baits = self.persistence.load_baits()
        self.update_table()
        self.update_summary()

    def update_table(self):
        """Update the table display"""
        self.table.setRowCount(0)
        row = 0
        for bait in self.baits:
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(bait.name))
            self.table.setItem(row, 1, QTableWidgetItem(str(bait.total_bought)))
            self.table.setItem(row, 2, QTableWidgetItem(str(bait.total_used)))
            self.table.setItem(row, 3, QTableWidgetItem(str(bait.remaining)))
            row += 1
        self.update_summary()

    def update_summary(self):
        """Update summary display"""
        total_types = len(self.baits)
        total_remaining = sum(b.remaining for b in self.baits)
        self.summary_label.setText(f"总品类: {total_types}  |  总剩余: {total_remaining:,}")

    def _on_bait_select(self):
        """Handle bait selection"""
        selected = self.table.selectedItems()
        if not selected:
            self.selected_bait = None
            return
        row = selected[0].row()
        if 0 <= row < len(self.baits):
            self.selected_bait = self.baits[row]

    def add_bait(self):
        """Open dialog to add new bait"""
        dialog = AddBaitDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, initial_stock = dialog.get_values()
            if not name.strip():
                return

            # Check duplicate
            for b in self.baits:
                if b.name == name.strip():
                    QMessageBox.critical(self, "错误", "该饵料名称已存在")
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
            QMessageBox.information(self, "成功", "添加成功")

    def delete_selected(self):
        """Delete selected bait"""
        if not self.selected_bait:
            QMessageBox.information(self, "提示", "请先选择一个饵料/钓具")
            return

        confirm = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 '{self.selected_bait.name}' 吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.baits.remove(self.selected_bait)
            self.selected_bait = None
            self.update_table()
            self.save_data()

    def add_stock(self):
        """Add stock to selected bait"""
        if not self.selected_bait:
            QMessageBox.information(self, "提示", "请先选择一个饵料/钓具")
            return

        try:
            quantity = int(self.quantity_edit.text())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "错误", "请输入有效的正整数")
            return

        self.selected_bait.add_stock(quantity)
        self.update_table()
        self.save_data()
        QMessageBox.information(self, "成功", f"已增加 {quantity} 个 [{self.selected_bait.name}]")

    def use_stock(self):
        """Use stock from selected bait"""
        if not self.selected_bait:
            QMessageBox.information(self, "提示", "请先选择一个饵料/钓具")
            return

        try:
            quantity = int(self.quantity_edit.text())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "错误", "请输入有效的正整数")
            return

        if quantity > self.selected_bait.remaining:
            confirm = QMessageBox.question(
                self, "库存不足",
                f"剩余只有 {self.selected_bait.remaining}，但要使用 {quantity}\n是否继续使用全部剩余？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

        self.selected_bait.use_stock(quantity)
        self.update_table()
        self.save_data()
        QMessageBox.information(self, "成功", f"已使用 {quantity} 个 [{self.selected_bait.name}]")

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_baits(self.baits)


class AddBaitDialog(QDialog):
    """Dialog to add new bait"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加饵料/钓具")
        self.setFixedSize(350, 250)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("饵料/钓具名称"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("初始库存数量"))
        self.stock_edit = QLineEdit()
        self.stock_edit.setText("100")
        layout.addWidget(self.stock_edit)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

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

    def confirm(self):
        """Confirm and add"""
        name = self.name_edit.text().strip()
        try:
            initial_stock = int(self.stock_edit.text().strip())
            if initial_stock < 0:
                initial_stock = 0
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的库存数量")
            return

        if name:
            self.accept()
        else:
            QMessageBox.warning(self, "输入错误", "饵料/钓具名称不能为空")

    def get_values(self):
        """Get the entered values"""
        name = self.name_edit.text().strip()
        initial_stock = int(self.stock_edit.text().strip())
        return name, max(0, initial_stock)

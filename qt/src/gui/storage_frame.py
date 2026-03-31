"""Storage duration tracking frame"""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QLineEdit, QMessageBox,
    QGroupBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.models import StorageCharacter
from src.data.persistence import StoragePersistence


class StorageFrame(QWidget):
    """Storage duration tracking frame"""

    def __init__(self, persistence: StoragePersistence):
        super().__init__()
        self.persistence = persistence
        self.characters: List[StorageCharacter] = []
        # Sorting state
        self._sort_column = "角色名称"
        self._sort_ascending = True

        self._create_widgets()
        self.load_data()

    def _create_widgets(self):
        """Create the widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("📦 存储时长统计")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)

        # Button bar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        add_btn = QPushButton("+ 添加角色")
        add_btn.setFixedWidth(100)
        add_btn.clicked.connect(self.add_character)
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("- 删除角色")
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

        # Table
        table_group = QGroupBox("存储角色列表")
        table_group.setFont(QFont("Segoe UI", 14, QFont.Bold))
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["角色名称", "剩余时长(分钟)", ""])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)

        table_layout.addWidget(self.table)
        layout.addWidget(table_group, 1)

        # Control area for adding/removing minutes
        control_group = QGroupBox("⚡ 调整时长")
        control_group.setFont(QFont("Segoe UI", 16, QFont.Bold))
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(12, 12, 12, 12)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        input_layout.setAlignment(Qt.AlignCenter)

        input_layout.addWidget(QLabel("分钟数: "))
        self.minutes_edit = QLineEdit()
        self.minutes_edit.setText("60")
        self.minutes_edit.setFixedWidth(100)
        input_layout.addWidget(self.minutes_edit)

        add_btn = QPushButton("+ 增加")
        add_btn.setFixedWidth(80)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        add_btn.clicked.connect(self.add_minutes)
        input_layout.addWidget(add_btn)

        remove_btn = QPushButton("- 减少")
        remove_btn.setFixedWidth(80)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        remove_btn.clicked.connect(self.remove_minutes)
        input_layout.addWidget(remove_btn)

        control_layout.addLayout(input_layout)
        layout.addWidget(control_group)

        self.setLayout(layout)

    def load_data(self):
        """Load data from persistence"""
        self.characters = self.persistence.load_characters()
        self.update_table()

    def update_table(self):
        """Update the table display"""
        self.table.setRowCount(0)
        row = 0
        for char in self.characters:
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(char.name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{char.remaining_minutes:,}"))
            row += 1

    def get_selected_character(self):
        """Get the currently selected character"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        if 0 <= row < len(self.characters):
            return self.characters[row]
        return None

    def add_character(self):
        """Add a new character"""
        dialog = AddStorageCharacterDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, minutes = dialog.get_values()
            if name.strip():
                char = StorageCharacter(name.strip(), minutes)
                self.characters.append(char)
                self.update_table()
                self.save_data()

    def delete_selected(self):
        """Delete selected character"""
        char = self.get_selected_character()
        if char:
            confirm = QMessageBox.question(
                self, "确认删除",
                f"确定要删除角色 {char.name} 吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                self.characters.remove(char)
                self.update_table()
                self.save_data()

    def add_minutes(self):
        """Add minutes to selected character"""
        char = self.get_selected_character()
        if not char:
            QMessageBox.information(self, "提示", "请先选择一个角色")
            return
        try:
            minutes = int(self.minutes_edit.text().strip())
            if minutes <= 0:
                QMessageBox.warning(self, "输入错误", "分钟数必须大于0")
                return
            char.add_minutes(minutes)
            self.update_table()
            self.save_data()
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的分钟数")

    def remove_minutes(self):
        """Remove minutes from selected character"""
        char = self.get_selected_character()
        if not char:
            QMessageBox.information(self, "提示", "请先选择一个角色")
            return
        try:
            minutes = int(self.minutes_edit.text().strip())
            if minutes <= 0:
                QMessageBox.warning(self, "输入错误", "分钟数必须大于0")
                return
            char.remove_minutes(minutes)
            self.update_table()
            self.save_data()
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的分钟数")

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_characters(self.characters)


class AddStorageCharacterDialog(QDialog):
    """Dialog to add a new storage character"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加存储角色")
        self.setFixedSize(350, 200)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(30, 30, 30, 20)

        layout.addWidget(QLabel("角色名称"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("初始剩余时长(分钟)"))
        self.minutes_edit = QLineEdit()
        self.minutes_edit.setText("0")
        layout.addWidget(self.minutes_edit)

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
        if not name:
            QMessageBox.warning(self, "输入错误", "角色名称不能为空")
            return

        try:
            minutes = int(self.minutes_edit.text().strip())
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的分钟数")
            return

    def get_values(self):
        """Get the entered values"""
        name = self.name_edit.text().strip()
        minutes = int(self.minutes_edit.text().strip())
        return name, max(0, minutes)

"""Account credentials manager frame (with encrypted password storage)"""
import sys
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QDialog, QCheckBox, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.models import AccountCredential
from src.data.persistence import CredentialsPersistence


class CredentialsFrame(QWidget):
    """Account credentials manager frame - dropdown selection, click button to copy password"""

    def __init__(self, persistence: CredentialsPersistence):
        super().__init__()
        self.persistence = persistence
        self.accounts: List[AccountCredential] = []
        self.selected_account: AccountCredential | None = None

        self._create_widgets()
        self.load_data()

    def _create_widgets(self):
        """Create the widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(15)

        # Title
        title = QLabel("🔐 账号密码管理")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Top button bar - add/delete
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        add_btn = QPushButton("+ 添加账号")
        add_btn.setFixedWidth(100)
        add_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("- 删除当前账号")
        delete_btn.setFixedWidth(120)
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

        edit_btn = QPushButton("✏️ 修改密码")
        edit_btn.setFixedWidth(100)
        edit_btn.clicked.connect(self.edit_password)
        btn_layout.addWidget(edit_btn)

        btn_layout.addStretch()

        save_btn = QPushButton("💾 保存数据")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        # Selection area
        selection_group = QWidget()
        selection_group.setStyleSheet("QWidget { background-color: #252525; border-radius: 12px; }")
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setContentsMargins(20, 15, 20, 15)
        selection_layout.setSpacing(15)

        # Account selection
        account_row = QHBoxLayout()
        account_row.setSpacing(15)
        account_row.addWidget(QLabel("选择账号:"))

        self.account_combo = QComboBox()
        self.account_combo.setFixedWidth(250)
        self.account_combo.currentTextChanged.connect(self._on_account_selected)
        account_row.addWidget(self.account_combo)
        account_row.addStretch()
        selection_layout.addLayout(account_row)

        # Password display and copy
        password_row = QHBoxLayout()
        password_row.setSpacing(15)
        password_row.addWidget(QLabel("账号密码:"))

        self.password_edit = QLineEdit()
        self.password_edit.setFixedWidth(250)
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setReadOnly(True)
        password_row.addWidget(self.password_edit)

        self.copy_btn = QPushButton("📋 复制密码")
        self.copy_btn.setFixedWidth(100)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2aa040;
            }
            QPushButton:hover {
                background-color: #1a7030;
            }
        """)
        self.copy_btn.clicked.connect(self.copy_password)
        password_row.addWidget(self.copy_btn)

        selection_layout.addLayout(password_row)
        layout.addWidget(selection_group)

        layout.addStretch()
        self.setLayout(layout)

    def load_data(self):
        """Load data from persistence"""
        self.accounts = self.persistence.load_credentials()
        self.update_combobox()

    def update_combobox(self):
        """Update the dropdown menu with account names"""
        self.account_combo.clear()
        account_names = [acc.account_name for acc in self.accounts]
        if not account_names:
            self.password_edit.clear()
            self.selected_account = None
            return

        for name in account_names:
            self.account_combo.addItem(name)

        if self.selected_account is None or not any(
            acc.account_name == self.selected_account.account_name for acc in self.accounts
        ):
            # Select first account
            self.selected_account = self.accounts[0]
            self.account_combo.setCurrentIndex(0)

        self._update_password_display()

    def _on_account_selected(self, selected_name):
        """Handle account selection from dropdown"""
        if not selected_name:
            return
        for acc in self.accounts:
            if acc.account_name == selected_name:
                self.selected_account = acc
                break
        self._update_password_display()

    def _update_password_display(self):
        """Update the password display for selected account"""
        self.password_edit.clear()
        if self.selected_account:
            # Always show fixed 6 asterisks regardless of actual password length
            masked_pw = "******"
            self.password_edit.setText(masked_pw)

    def copy_password(self):
        """Copy selected account's password to clipboard"""
        if not self.selected_account:
            QMessageBox.information(self, "提示", "请先选择一个账号")
            return

        plain_password = self.persistence.get_plain_password(self.selected_account)
        if plain_password:
            # Try to use Qt clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(plain_password)
            QMessageBox.information(self, "成功", f"已复制 [{self.selected_account.account_name}] 的密码到剪贴板")

    def add_account(self):
        """Open dialog to add new account"""
        dialog = AddEditAccountDialog(self, None)
        if dialog.exec() == QDialog.Accepted:
            account_name, plain_password = dialog.get_values()
            if not account_name.strip() or not plain_password.strip():
                return

            # Check for duplicate name
            for acc in self.accounts:
                if acc.account_name == account_name.strip():
                    QMessageBox.critical(self, "错误", "该账号名称已存在")
                    return

            new_account = self.persistence.add_account(account_name.strip(), plain_password.strip())
            self.accounts.append(new_account)
            self.selected_account = new_account
            self.update_combobox()
            self.save_data()
            QMessageBox.information(self, "成功", "账号添加成功")

    def delete_selected(self):
        """Delete selected account"""
        if not self.selected_account:
            QMessageBox.information(self, "提示", "请先选择一个账号")
            return

        confirm = QMessageBox.question(
            self, "确认删除",
            f"确定要删除账号 '{self.selected_account.account_name}' 吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.accounts.remove(self.selected_account)
            self.selected_account = None
            self.update_combobox()
            self.save_data()

    def edit_password(self):
        """Open dialog to edit password of selected account"""
        if not self.selected_account:
            QMessageBox.information(self, "提示", "请先选择一个账号")
            return

        dialog = AddEditAccountDialog(self, self.selected_account.account_name)
        if dialog.exec() == QDialog.Accepted:
            account_name, new_password = dialog.get_values()
            if not new_password.strip():
                return

            # Check if name changed to existing
            if account_name.strip() != self.selected_account.account_name:
                for acc in self.accounts:
                    if acc.account_name == account_name.strip() and acc != self.selected_account:
                        QMessageBox.critical(self, "错误", "该账号名称已存在")
                        return

            # Remove old and add new (with new encrypted password)
            self.accounts.remove(self.selected_account)
            new_account = self.persistence.add_account(account_name.strip(), new_password.strip())
            self.accounts.append(new_account)
            self.selected_account = new_account
            self.update_combobox()
            self.save_data()
            QMessageBox.information(self, "成功", "密码修改成功")

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_credentials(self.accounts)


class AddEditAccountDialog(QDialog):
    """Dialog to add or edit an account"""

    def __init__(self, parent, existing_name: str | None):
        super().__init__(parent)
        self.existing_name = existing_name

        if existing_name is None:
            self.setWindowTitle("添加账号")
        else:
            self.setWindowTitle(f"修改密码 - {existing_name}")

        self.setFixedSize(400, 280)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("账号名称"))
        self.name_edit = QLineEdit()
        if existing_name:
            self.name_edit.setText(existing_name)
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("账号密码"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_edit)

        # Show/hide password checkbox
        self.show_password_check = QCheckBox("显示密码")
        self.show_password_check.toggled.connect(self._toggle_password_visibility)
        layout.addWidget(self.show_password_check)

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

    def _toggle_password_visibility(self, checked):
        """Toggle password visibility"""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)

    def confirm(self):
        """Confirm and add/edit"""
        name = self.name_edit.text().strip()
        password = self.password_edit.text().strip()
        if name and password:
            self.accept()
        else:
            QMessageBox.warning(self, "输入错误", "账号名称和密码不能为空")

    def get_values(self):
        """Get the entered values"""
        name = self.name_edit.text().strip()
        password = self.password_edit.text().strip()
        return name, password

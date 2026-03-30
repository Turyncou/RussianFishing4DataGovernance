"""Account credentials manager frame (with encrypted password storage)"""
import customtkinter as ctk
import pyperclip
from typing import List
from CTkMessagebox import CTkMessagebox

from core.models import AccountCredential
from data.persistence import CredentialsPersistence


class CredentialsFrame(ctk.CTkFrame):
    """Account credentials manager frame - dropdown selection, click button to copy password"""

    def __init__(self, parent, persistence: CredentialsPersistence):
        super().__init__(parent, fg_color="transparent", corner_radius=16)
        self.persistence = persistence
        self.accounts: List[AccountCredential] = []
        self.selected_account: AccountCredential | None = None

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        """Create the widgets"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="🔐 账号密码管理",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(15, 20))

        # Top button bar - add/delete
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        add_btn = ctk.CTkButton(
            btn_frame,
            text="+ 添加账号",
            command=self.add_account,
            width=100,
            corner_radius=8
        )
        add_btn.pack(side="left", padx=5)

        delete_btn = ctk.CTkButton(
            btn_frame,
            text="- 删除当前账号",
            command=self.delete_selected,
            width=120,
            fg_color="#cc3333",
            hover_color="#aa2222",
            corner_radius=8
        )
        delete_btn.pack(side="left", padx=5)

        edit_btn = ctk.CTkButton(
            btn_frame,
            text="✏️ 修改密码",
            command=self.edit_password,
            width=100,
            corner_radius=8
        )
        edit_btn.pack(side="left", padx=5)

        # Selection area
        selection_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12)
        selection_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Account selection
        account_row = ctk.CTkFrame(selection_frame, fg_color="transparent")
        account_row.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            account_row,
            text="选择账号:",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 15))

        self.account_var = ctk.StringVar(value="请选择账号")
        self.account_dropdown = ctk.CTkOptionMenu(
            account_row,
            variable=self.account_var,
            values=[],
            command=self.on_account_selected,
            width=250,
            corner_radius=8
        )
        self.account_dropdown.pack(side="left", padx=(0, 15))

        # Password display and copy
        password_row = ctk.CTkFrame(selection_frame, fg_color="transparent")
        password_row.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            password_row,
            text="账号密码:",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 15))

        self.password_entry = ctk.CTkEntry(
            password_row,
            width=250,
            corner_radius=8,
            show="*",
            state="readonly"
        )
        self.password_entry.pack(side="left", padx=(0, 15))

        self.copy_btn = ctk.CTkButton(
            password_row,
            text="📋 复制密码",
            command=self.copy_password,
            width=100,
            corner_radius=8,
            fg_color="#2aa040",
            hover_color="#1a7030"
        )
        self.copy_btn.pack(side="left")

    def load_data(self):
        """Load data from persistence"""
        self.accounts = self.persistence.load_credentials()
        self.update_dropdown()

    def update_dropdown(self):
        """Update the dropdown menu with account names"""
        account_names = [acc.account_name for acc in self.accounts]
        self.account_dropdown.configure(values=account_names)

        if not self.accounts:
            self.account_var.set("请选择账号")
            self.password_entry.configure(state="normal")
            self.password_entry.delete(0, ctk.END)
            self.password_entry.configure(state="readonly")
            self.selected_account = None
        elif self.selected_account is None or self.selected_account not in self.accounts:
            # Select first account
            self.selected_account = self.accounts[0]
            self.account_var.set(self.selected_account.account_name)
            self.update_password_display()

    def on_account_selected(self, selected_name):
        """Handle account selection from dropdown"""
        for acc in self.accounts:
            if acc.account_name == selected_name:
                self.selected_account = acc
                break
        self.update_password_display()

    def update_password_display(self):
        """Update the password display for selected account"""
        self.password_entry.configure(state="normal")
        self.password_entry.delete(0, ctk.END)
        if self.selected_account:
            plain_pw = self.persistence.get_plain_password(self.selected_account)
            masked_pw = "*" * len(plain_pw)
            self.password_entry.insert(0, masked_pw)
        self.password_entry.configure(state="readonly")

    def copy_password(self):
        """Copy selected account's password to clipboard"""
        if not self.selected_account:
            CTkMessagebox(title="提示", message="请先选择一个账号", icon="warning")
            return

        plain_password = self.persistence.get_plain_password(self.selected_account)
        if plain_password:
            pyperclip.copy(plain_password)
            CTkMessagebox(title="成功", message=f"已复制 [{self.selected_account.account_name}] 的密码到剪贴板", icon="info")

    def add_account(self):
        """Open dialog to add new account"""
        dialog = AddEditAccountDialog(self.winfo_toplevel(), None, self.on_add_account_done)

    def on_add_account_done(self, account_name: str, plain_password: str):
        """Callback after adding account"""
        if not account_name.strip() or not plain_password.strip():
            return

        # Check for duplicate name
        for acc in self.accounts:
            if acc.account_name == account_name.strip():
                CTkMessagebox(title="错误", message="该账号名称已存在", icon="cancel")
                return

        new_account = self.persistence.add_account(account_name.strip(), plain_password.strip())
        self.accounts.append(new_account)
        self.selected_account = new_account
        self.update_dropdown()
        self.save_data()
        CTkMessagebox(title="成功", message="账号添加成功", icon="info")

    def delete_selected(self):
        """Delete selected account"""
        if not self.selected_account:
            CTkMessagebox(title="提示", message="请先选择一个账号", icon="warning")
            return

        confirm = CTkMessagebox(
            title="确认删除",
            message=f"确定要删除账号 '{self.selected_account.account_name}' 吗？\n此操作不可恢复！",
            icon="warning",
            option_1="取消",
            option_2="删除"
        )
        if confirm.get() == "删除":
            self.accounts.remove(self.selected_account)
            self.selected_account = None
            self.update_dropdown()
            self.save_data()

    def edit_password(self):
        """Open dialog to edit password of selected account"""
        if not self.selected_account:
            CTkMessagebox(title="提示", message="请先选择一个账号", icon="warning")
            return

        dialog = AddEditAccountDialog(
            self.winfo_toplevel(),
            self.selected_account.account_name,
            self.on_edit_password_done
        )

    def on_edit_password_done(self, account_name: str, new_password: str):
        """Callback after editing password"""
        if not new_password.strip():
            return

        # Check if name changed to existing
        if account_name.strip() != self.selected_account.account_name:
            for acc in self.accounts:
                if acc.account_name == account_name.strip() and acc != self.selected_account:
                    CTkMessagebox(title="错误", message="该账号名称已存在", icon="cancel")
                    return

        # Remove old and add new (with new encrypted password)
        self.accounts.remove(self.selected_account)
        new_account = self.persistence.add_account(account_name.strip(), new_password.strip())
        self.accounts.append(new_account)
        self.selected_account = new_account
        self.update_dropdown()
        self.save_data()
        CTkMessagebox(title="成功", message="密码修改成功", icon="info")

    def save_data(self):
        """Save all data to persistence"""
        self.persistence.save_credentials(self.accounts)


class AddEditAccountDialog(ctk.CTkToplevel):
    """Dialog to add or edit an account"""

    def __init__(self, parent, existing_name: str | None, callback):
        super().__init__(parent)
        self.callback = callback
        self.existing_name = existing_name

        if existing_name is None:
            self.title("添加账号")
        else:
            self.title(f"修改密码 - {existing_name}")

        self.geometry("400x280")
        self.resizable(False, False)
        self.grab_set()

        # Scrollable frame
        scrollable_frame = ctk.CTkScrollableFrame(self, width=380, height=240)
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            scrollable_frame,
            text="账号名称",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(20, 5))
        self.name_entry = ctk.CTkEntry(scrollable_frame, width=300, corner_radius=8)
        if existing_name:
            self.name_entry.insert(0, existing_name)
        self.name_entry.pack(pady=5)

        ctk.CTkLabel(
            scrollable_frame,
            text="账号密码",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(15, 5))
        self.password_entry = ctk.CTkEntry(scrollable_frame, width=300, corner_radius=8, show="*")
        self.password_entry.pack(pady=5)

        # Show/hide password checkbox
        self.show_password_var = ctk.BooleanVar(value=False)
        show_password_cb = ctk.CTkCheckBox(
            scrollable_frame,
            text="显示密码",
            variable=self.show_password_var,
            command=self.toggle_password_visibility
        )
        show_password_cb.pack(pady=(10, 5))

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

    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def confirm(self):
        """Confirm and add/edit"""
        name = self.name_entry.get().strip()
        password = self.password_entry.get().strip()
        if name and password:
            self.callback(name, password)
            self.grab_release()
            self.destroy()
        else:
            CTkMessagebox(title="输入错误", message="账号名称和密码不能为空", icon="warning", option_1="确定")

"""Friend Links UI widget"""
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt
from src.core.data_manager import DataManager
from src.core.friend_links import FriendLinksModel


class FriendLinksWidget(QWidget):
    """Friend Links widget"""

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.model = FriendLinksModel()

        # Load saved data
        saved_data = data_manager.load_friend_links()
        self.model.load_from_data(saved_data)

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)

        # Links list
        self.links_list = QListWidget()
        layout.addWidget(self.links_list)

        # Controls
        controls_layout = QHBoxLayout()

        self.add_button = QPushButton("添加链接")
        self.add_button.clicked.connect(self.on_add_clicked)
        controls_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("编辑链接")
        self.edit_button.clicked.connect(self.on_edit_clicked)
        controls_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("删除链接")
        self.remove_button.clicked.connect(self.on_remove_clicked)
        controls_layout.addWidget(self.remove_button)

        self.open_button = QPushButton("打开链接")
        self.open_button.clicked.connect(self.on_open_clicked)
        controls_layout.addWidget(self.open_button)

        layout.addLayout(controls_layout)

        self.setLayout(layout)

    def refresh(self):
        """Refresh display from model"""
        self.links_list.clear()
        for i, link in enumerate(self.model.get_links()):
            item_text = f"{link['name']} - {link['url']}"
            item = QListWidgetItem(item_text)
            self.links_list.addItem(item)
        self.save()

    def on_add_clicked(self):
        """Add new link"""
        dialog = LinkDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            name, url = dialog.get_values()
            if not name or not url:
                QMessageBox.warning(self, "警告", "名称和链接不能为空")
                return
            if not self.model.validate_url(url):
                QMessageBox.warning(self, "警告", "链接必须以 http:// 或 https:// 开头")
                return
            if not self.model.add_link(name, url):
                QMessageBox.warning(self, "警告", "添加失败")
                return
            self.refresh()

    def on_edit_clicked(self):
        """Edit selected link"""
        current_item = self.links_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "警告", "请先选择要编辑的链接")
            return
        index = self.links_list.row(current_item)
        link = self.model.get_links()[index]

        dialog = LinkDialog(self, link["name"], link["url"])
        if dialog.exec() == dialog.DialogCode.Accepted:
            name, url = dialog.get_values()
            if not name or not url:
                QMessageBox.warning(self, "警告", "名称和链接不能为空")
                return
            if not self.model.validate_url(url):
                QMessageBox.warning(self, "警告", "链接必须以 http:// 或 https:// 开头")
                return
            self.model.update_link(index, name, url)
            self.refresh()

    def on_remove_clicked(self):
        """Remove selected link"""
        current_item = self.links_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "警告", "请先选择要删除的链接")
            return
        index = self.links_list.row(current_item)

        reply = QMessageBox.question(
            self, "确认删除", "确认删除选中的链接吗?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.model.remove_link(index)
            self.refresh()

    def on_open_clicked(self):
        """Open selected link in browser"""
        current_item = self.links_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "警告", "请先选择要打开的链接")
            return
        index = self.links_list.row(current_item)
        link = self.model.get_links()[index]
        webbrowser.open(link["url"])

    def save(self):
        """Save current data"""
        data = self.model.get_data_for_saving()
        self.data_manager.save_friend_links(data)


class LinkDialog(QDialog):
    """Dialog for adding/editing a link"""

    def __init__(self, parent, name: str = "", url: str = ""):
        super().__init__(parent)
        self.setWindowTitle("链接设置")
        layout = QFormLayout(self)

        self.name_edit = QLine(name)
        layout.addRow("名称:", self.name_edit)

        self.url_edit = QLine(url)
        layout.addRow("链接:", self.url_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self):
        """Get entered values"""
        return self.name_edit.text().strip(), self.url_edit.text().strip()

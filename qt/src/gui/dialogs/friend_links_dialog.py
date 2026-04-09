"""Friend links dialog"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
    QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.core.models import FriendLink


class BrowserWindow(QDialog):
    """Internal browser window for displaying links"""

    def __init__(self, parent, title: str, url: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 650)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.url = url
        self.title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Show loading message first
        from PySide6.QtWidgets import QLabel
        self.loading_label = QLabel("正在加载网页，请稍候...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 16px; color: #666;")
        layout.addWidget(self.loading_label)

        # Load web view after event loop processes
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._load_webview)

    def _load_webview(self):
        """Actually load the web view after window is shown"""
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtCore import QUrl

            # Remove loading label
            layout = self.layout()
            layout.removeWidget(self.loading_label)
            self.loading_label.deleteLater()

            # Create web view
            self.web_view = QWebEngineView()
            self.web_view.load(QUrl(self.url))
            layout.addWidget(self.web_view)
        except ImportError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "依赖缺失",
                "无法加载网页浏览功能，请先安装依赖：\n"
                "cd qt\n"
                "pip install PySide6-WebEngine>=6.5.0"
            )
            self.close()


class FriendLinksDialog(QDialog):
    """Dialog for displaying and managing friend links"""

    links_changed = Signal(object)

    def __init__(self, parent, current_links: list[FriendLink]):
        super().__init__(parent)
        self.links = current_links.copy()
        self.setWindowTitle("友情链接")
        self.setFixedSize(500, 450)
        self.setModal(True)

        self._create_widgets()
        self._update_list()

    def _create_widgets(self):
        """Create dialog widgets"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 10, 20, 20)

        title = QLabel("友情链接")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._open_selected)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        open_btn = QPushButton("打开链接")
        open_btn.setFixedWidth(90)
        open_btn.clicked.connect(self._open_selected)
        btn_layout.addWidget(open_btn)

        add_btn = QPushButton("添加")
        add_btn.setFixedWidth(90)
        add_btn.clicked.connect(self._add_link)
        btn_layout.addWidget(add_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setFixedWidth(90)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc3333;
            }
            QPushButton:hover {
                background-color: #aa2222;
            }
        """)
        delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(90)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _update_list(self):
        """Update the listbox"""
        self.list_widget.clear()
        for link in self.links:
            item = QListWidgetItem(f"{link.text} - {link.url}")
            item.setData(Qt.UserRole, link)
            self.list_widget.addItem(item)

    def _get_selected(self):
        """Get selected link"""
        items = self.list_widget.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.UserRole)

    def _open_selected(self, event=None):
        """Open the selected link in internal browser window"""
        link = self._get_selected()
        if not link:
            return
        try:
            browser = BrowserWindow(self, link.text, link.url)
            browser.setAttribute(Qt.WA_DeleteOnClose)
            browser.show()
        except ImportError:
            QMessageBox.critical(
                self, "依赖缺失",
                "无法加载网页浏览功能，请先安装依赖：\n"
                "cd qt\n"
                "pip install PySide6-WebEngine>=6.5.0"
            )

    def _add_link(self):
        """Open dialog to add new link"""
        dialog = AddLinkDialog(self)
        if dialog.exec() == QDialog.Accepted:
            text, url = dialog.get_values()
            try:
                new_link = FriendLink(text, url)
                self.links.append(new_link)
                self._update_list()
            except ValueError as e:
                QMessageBox.critical(self, "错误", str(e))

    def _delete_selected(self):
        """Delete selected link"""
        items = self.list_widget.selectedItems()
        if not items:
            return
        index = self.list_widget.row(items[0])
        del self.links[index]
        self._update_list()

    def _save(self):
        """Save changes and close"""
        self.links_changed.emit(self.links)
        self.accept()


class AddLinkDialog(QDialog):
    """Dialog to add a new friend link"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("添加友情链接")
        self.setFixedSize(400, 230)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Text entry
        label = QLabel("文字说明")
        label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(label)
        self.text_edit = QLineEdit()
        self.text_edit.setFixedHeight(32)
        layout.addWidget(self.text_edit)

        # URL entry
        label2 = QLabel("链接地址")
        label2.setFont(QFont("Segoe UI", 14))
        layout.addWidget(label2)
        self.url_edit = QLineEdit()
        self.url_edit.setFixedHeight(32)
        layout.addWidget(self.url_edit)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self._confirm)
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

    def _confirm(self):
        """Confirm and add link"""
        text = self.text_edit.text().strip()
        url = self.url_edit.text().strip()
        if text and url:
            self.accept()
        else:
            QMessageBox.warning(self, "输入错误", "文字说明和链接地址都不能为空")

    def get_values(self):
        """Get the entered values"""
        return self.text_edit.text().strip(), self.url_edit.text().strip()

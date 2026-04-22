"""Fish data synchronization from official website"""
import os
from dataclasses import dataclass
from lxml import etree
import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl


@dataclass
class SyncResult:
    """Result of fish synchronization"""
    success: bool
    message: str
    fish_count: int = 0


class FishSynchronizer:
    """Fish data synchronizer that extracts fish names from RF4 official website"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def sync_from_official(self) -> SyncResult:
        """Synchronize fish names from RF4 official website by downloading the page directly

        Returns:
            SyncResult with success status and message
        """
        try:
            import requests
            url = "https://rf4game.com/cn/records/"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html = response.text
            return self._parse_html(html)
        except ImportError:
            return SyncResult(success=False, message="缺少requests依赖，请运行: pip install requests")
        except Exception as e:
            return SyncResult(success=False, message=f"下载失败: {str(e)}")

    def _parse_html(self, html: str) -> SyncResult:
        """Parse HTML and extract fish names

        Args:
            html: Full HTML content from the records page

        Returns:
            SyncResult with success status and message
        """
        try:
            tree = etree.HTML(html)
            result = []
            i = 1
            while True:
                text = tree.xpath(
                    f'//*[@id="tabular_body"]/div[1]/div/div[2]/div[2]/div[{i}]/div/div[1]/div[1]/div/div[2]/text()'
                )
                if not text:
                    break
                name = text[0].strip()
                if name:
                    result.append(name)
                i += 1

            if not result:
                return SyncResult(success=False, message="未找到任何鱼种数据，请检查网页内容")

            # Save to CSV file
            csv_fish = pd.Series(result)
            csv_fish = csv_fish.str.replace("'", "", regex=False)

            output_path = os.path.join(self.data_dir, 'fish_names.csv')
            os.makedirs(self.data_dir, exist_ok=True)
            csv_fish.to_csv(output_path, index=False, header=False, encoding='utf-8')

            return SyncResult(
                success=True,
                message=f"鱼种数据同步成功！\n\n共 {len(result)} 个鱼种已保存到:\n{output_path}",
                fish_count=len(result)
            )

        except Exception as e:
            return SyncResult(success=False, message=f"同步失败: {str(e)}")


class FishSyncDialog(QDialog):
    """Dialog for synchronizing fish data from official website"""

    def __init__(self, parent, data_dir: str):
        super().__init__(parent)
        self.data_dir = data_dir
        self.setWindowTitle("同步鱼种数据")
        self.setFixedSize(600, 450)
        self.setModal(True)

        self._is_running = False
        self._check_count = 0
        self._max_checks = 30  # Max 30 seconds wait

        self._create_widgets()

    def _create_widgets(self):
        """Create dialog widgets"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 10, 20, 20)

        # Title
        title = QLabel("从官网同步鱼种数据")
        title.setFont(self.font())
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "此功能将从 https://rf4game.com/cn/records/ 爬取全部鱼种名称，\n"
            "保存为 fish_names.csv 供蹲星目标功能使用。\n"
            "爬取过程中请耐心等待，网页加载可能需要几秒钟时间。"
        )
        desc.setStyleSheet("color: #888888;")
        layout.addWidget(desc)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        self.progress.hide()

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_output)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.start_btn = QPushButton("开始同步")
        self.start_btn.setFixedWidth(100)
        self.start_btn.clicked.connect(self._start_sync)
        btn_layout.addWidget(self.start_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setFixedWidth(100)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _log(self, message):
        """Add message to log output"""
        self.log_output.append(message)
        # Scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _start_sync(self):
        """Start synchronization"""
        if self._is_running:
            return

        self._is_running = True
        self._check_count = 0
        self.start_btn.setEnabled(False)
        self.progress.show()
        self._log("开始加载网页...")

        # Create web view in main thread
        self.web_view = QWebEngineView()
        self.web_view.page().loadFinished.connect(self._on_load_finished)
        self.web_view.load(QUrl("https://rf4game.com/cn/records/"))

        # We don't need to show the web view, just use it to load page
        self.web_view.hide()

    def _on_load_finished(self, success):
        """Called when page loading finishes"""
        if success:
            self._log("页面加载完成，开始检测数据表格...")
            # Start timer to check for element every second
            self.check_timer = QTimer(self)
            self.check_timer.timeout.connect(self._check_for_element)
            self.check_timer.start(1000)
        else:
            self._log("❌ 页面加载失败，请检查网络连接")
            self._finish()

    def _check_for_element(self):
        """Check if target element exists on page"""
        self._check_count += 1
        if self._check_count > self._max_checks:
            self._log(f"❌ 等待超时 ({self._max_checks} 秒)，未找到数据表格，请重试")
            self.check_timer.stop()
            self._finish()
            return

        self._log(f"⏳ 等待数据加载... ({self._check_count}/{self._max_checks})")
        self.web_view.page().toHtml(self._on_html_ready)

    def _on_html_ready(self, html):
        """Process HTML when it's ready"""
        tree = etree.HTML(html)
        element = tree.xpath('//*[@id="tabular_body"]')

        if element:
            self._log("✅ 数据表格已加载，开始爬取鱼种名称...")
            self.check_timer.stop()
            synchronizer = FishSynchronizer(self.data_dir)
            result = synchronizer._parse_html(html)
            if result.success:
                self._log(f"✅ 爬取完成，共找到 {result.fish_count} 种鱼种")
                self._log(f"✅ 数据已保存到: {os.path.join(self.data_dir, 'fish_names.csv')}")
                QMessageBox.information(
                    self,
                    "同步完成",
                    result.message
                )
            else:
                self._log(f"❌ {result.message}")
            self._finish()
        # else: keep waiting, timer will check again next second

    def _finish(self):
        """Called when sync completes"""
        self._is_running = False
        self.start_btn.setEnabled(True)
        self.progress.hide()
        if hasattr(self, 'web_view'):
            self.web_view.deleteLater()
        self._log("\n同步完成！可以关闭窗口了。")

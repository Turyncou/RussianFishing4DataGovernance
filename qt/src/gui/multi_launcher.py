"""
RF4 Multiple Instances Launcher
Safe launcher for managing multiple RF4 game instances
"""
import os
import json
import time
import psutil
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QFrame, QMessageBox, QDialog
)
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent


# =========================
# 1. 数据结构：实例定义
# =========================

@dataclass
class AppInstance:
    instance_id: str
    lnk_path: str
    launcher_path: str  # 用于区分副本（关键）


# =========================
# 2. 安全启动器
# =========================

class SafeLauncher(QObject):

    def __init__(self):
        super().__init__()

        # instance_id -> launcher_pid
        self.launchers: Dict[str, Optional[int]] = {}

        # instance_id -> full info
        self.running: Dict[str, dict] = {}

    # -------------------------
    # 最安全启动方式
    # -------------------------
    def launch(self, instance: AppInstance):
        """
        只做一件事：让 Windows 通过 Shell 打开 .lnk
        """
        if not instance.lnk_path.lower().endswith(".lnk"):
            raise ValueError("Only .lnk allowed")

        self.launchers[instance.instance_id] = None
        self.running[instance.instance_id] = {
            "status": "launching",
            "launcher_pid": None,
            "children": []
        }

        os.startfile(instance.lnk_path)

    # -------------------------
    # 查找 launcher（按路径匹配）
    # -------------------------
    def scan_launchers(self, instances: List[AppInstance]):
        """
        关键：用 exe full path 匹配副本
        """
        instance_map = {}

        # Reset all to None first
        for inst in instances:
            self.launchers[inst.instance_id] = None

        # Normalize all paths for comparison (case-insensitive on Windows)
        for p in psutil.process_iter(['pid', 'exe']):
            try:
                exe = p.info['exe']
                if not exe:
                    continue
                # Normalize path for matching
                exe_norm = os.path.normcase(os.path.normpath(exe)).lower()

                for inst in instances:
                    inst_norm = os.path.normcase(os.path.normpath(inst.launcher_path)).lower()
                    if inst_norm == exe_norm:
                        instance_map[inst.instance_id] = p.info['pid']

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Update launcher pid
        for k, v in instance_map.items():
            self.launchers[k] = v

        # Initialize running dict for all instances
        for inst in instances:
            if inst.instance_id not in self.running:
                self.running[inst.instance_id] = {
                    "status": "stopped",
                    "launcher_pid": None,
                    "children": []
                }

        return instance_map

    # -------------------------
    # 更新状态 - 只要找到launcher进程就算运行
    # -------------------------
    def update_children(self):
        """
       只要 launcher 进程存在就标记为 running
        """
        for instance_id, pid in self.launchers.items():

            # Ensure entry exists
            if instance_id not in self.running:
                self.running[instance_id] = {
                    "status": "stopped",
                    "launcher_pid": None,
                    "children": []
                }

            if not pid:
                self.running[instance_id]["status"] = "stopped"
                continue

            try:
                # Check if the launcher process exists
                psutil.Process(pid)
                # If we get here, the process exists - it's running
                self.running[instance_id]["status"] = "running"

            except psutil.NoSuchProcess:
                self.running[instance_id]["status"] = "stopped"
                if instance_id in self.launchers:
                    self.launchers[instance_id] = None


# =========================
# 3. 监控线程（UI安全）
# =========================

# No automatic scanning - only scan on manual refresh
# This avoids frequent process enumeration which could trigger anti-cheat detection
class MonitorThread(QThread):
    update_signal = Signal(dict)

    def __init__(self, launcher: SafeLauncher, instances: List[AppInstance]):
        super().__init__()
        self.launcher = launcher
        self.instances = instances
        self.running = False

    def run(self):
        # No automatic scanning - we only scan on manual refresh
        # This avoids frequent process enumeration which could trigger anti-cheat detection
        self.running = True
        while self.running:
            # Just sleep, we don't automatically scan
            time.sleep(10)

    def do_scan(self):
        """Do a single scan and update UI"""
        # 1. 扫 launcher（路径匹配）
        self.launcher.scan_launchers(self.instances)
        # 2. 更新子进程
        self.launcher.update_children()
        # 3. 推送 UI
        self.update_signal.emit(self.launcher.running)

    def stop(self):
        self.running = False


# =========================
# 4. MultiLauncher Dialog
# =========================

class DropArea(QFrame):
    """Drag and drop area for adding instances"""

    dropped = Signal(list)  # Emits list of dropped file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(60)

        layout = QVBoxLayout(self)
        self.label = QLabel("👇 将RF4快捷方式拖放到这里\n自动添加实例", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.label)

        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #888888;
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.05);
            }
            DropArea:hover {
                border-color: #1f6feb;
                background-color: rgba(31, 111, 235, 0.1);
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropArea {
                    border: 2px dashed #1f6feb;
                    border-radius: 8px;
                    background-color: rgba(31, 111, 235, 0.15);
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #888888;
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.05);
            }
            DropArea:hover {
                border-color: #1f6feb;
                background-color: rgba(31, 111, 235, 0.1);
            }
        """)

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.lnk'):
                files.append(path)
        if files:
            self.dropped.emit(files)
        event.acceptProposedAction()
        self.dragLeaveEvent(None)


def resolve_lnk_target(lnk_path: str) -> Optional[str]:
    """Resolve the target path from a .lnk shortcut
    Returns None if fails to resolve
    """
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        target = shortcut.TargetPath
        if target and os.path.exists(target):
            return target
        # Sometimes target is relative, try to resolve against working directory
        working_dir = shortcut.WorkingDirectory
        if working_dir and target:
            full_path = os.path.join(working_dir, target)
            if os.path.exists(full_path):
                return full_path
        # If target doesn't exist, guess based on lnk directory
        dir_name = os.path.dirname(lnk_path)
        guess_exe = os.path.join(dir_name, "RF4Launcher.exe")
        if os.path.exists(guess_exe):
            return guess_exe
        guess_exe2 = os.path.join(dir_name, "RussianFishing4.exe")
        if os.path.exists(guess_exe2):
            return guess_exe2
        return None
    except Exception:
        # If win32com not available or fails, try to guess
        dir_name = os.path.dirname(lnk_path)
        # Guess common names
        for guess_name in ["RF4Launcher.exe", "RussianFishing4.exe", "launcher.exe", "Game.exe"]:
            guess_path = os.path.join(dir_name, guess_name)
            if os.path.exists(guess_path):
                return guess_path
        return None


class MultiLauncherDialog(QDialog):
    """Multiple instances launcher dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RF4 多开启动器")
        self.resize(550, 480)
        self.setModal(False)  # Non-modal - allow main window interaction

        # Open at top-left corner doesn't block main window
        # User can easily drag it anywhere
        if parent:
            # Place next to parent top-left corner
            parent_geo = parent.geometry()
            self.move(parent_geo.left() + 10, parent_geo.top() + 10)

        self.launcher = SafeLauncher()
        self.instances: List[AppInstance] = []

        # UI setup
        self._setup_ui()

        # Load saved instances from persistent storage
        self._load_saved_instances()

        # Start monitor thread
        self.monitor = MonitorThread(self.launcher, self.instances)
        self.monitor.update_signal.connect(self.update_ui)
        self.monitor.start()

        # Do initial scan once after loading saved instances
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._force_refresh)

    def _get_config_path(self):
        """Get path to save instances config"""
        app_dir = os.path.join(os.path.expanduser('~'), '.rf4_data_process')
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, 'multi_launcher_instances.json')

    def _load_saved_instances(self):
        """Load saved instances from json"""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    inst = AppInstance(
                        instance_id=item.get('instance_id', ''),
                        lnk_path=item.get('lnk_path', ''),
                        launcher_path=item.get('launcher_path', '')
                    )
                    if inst.instance_id and inst.lnk_path and inst.launcher_path:
                        self.instances.append(inst)
            except Exception as e:
                self.log.append(f"[警告] 加载保存的实例失败: {str(e)}")

    def _save_instances(self):
        """Save current instances to json"""
        config_path = self._get_config_path()
        try:
            data = [asdict(inst) for inst in self.instances]
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存实例配置:\n{str(e)}")

    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("RF4 多实例管理")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title)

        # Drag and drop area
        self.drop_area = DropArea()
        self.drop_area.dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_area)

        layout.addSpacing(8)

        # Instance list label
        instances_label = QLabel("已添加实例:")
        instances_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(instances_label)

        # Instance list display
        self.instance_frame = QFrame()
        self.instance_layout = QVBoxLayout(self.instance_frame)
        self.instance_layout.setSpacing(6)
        layout.addWidget(self.instance_frame)

        layout.addSpacing(4)

        # Status log label
        status_label = QLabel("运行状态:")
        status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(status_label)

        # Status log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        layout.addWidget(self.log)

        # Buttons
        btn_refresh = QPushButton("刷新状态")
        btn_close = QPushButton("关闭")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        # Connect
        btn_refresh.clicked.connect(self._force_refresh)
        btn_close.clicked.connect(self.close)

        self.setLayout(layout)

    def _load_default_instances(self):
        """Load default instances from common locations"""
        # Try to find RF4 installations in common locations
        # User can add their own instances later
        self._rebuild_instance_buttons()

    def _on_files_dropped(self, files: List[str]):
        """Handle dropped files"""
        for lnk_path in files:
            self._add_instance_from_lnk(lnk_path)
        self._force_refresh()

    def _add_instance_from_lnk(self, lnk_path: str):
        """Parse lnk and add instance"""
        # Get instance ID from filename
        base_name = os.path.basename(lnk_path)
        instance_id = os.path.splitext(base_name)[0]

        # Resolve target path
        launcher_path = resolve_lnk_target(lnk_path)

        if launcher_path is None:
            # Couldn't resolve - ask user to select manually
            result = QMessageBox.question(
                self,
                "无法解析快捷方式",
                f"无法自动解析目标路径\n快捷方式: {lnk_path}\n\n是否仍然添加实例？请手动确认启动器路径。",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                # Add with just lnk path (user needs to fix later)
                guess_path = os.path.splitext(lnk_path)[0] + ".exe"
                self.add_instance(instance_id, lnk_path, guess_path)
                self.log.append(f"[添加] {instance_id} - 添加成功，请确认启动器路径正确")
            return

        # Check if launcher exists
        if not os.path.exists(launcher_path):
            QMessageBox.warning(
                self,
                "启动器不存在",
                f"解析得到的启动器路径不存在:\n{launcher_path}\n\n实例未添加。"
            )
            return

        # Add the instance
        self.add_instance(instance_id, lnk_path, launcher_path)
        self.log.append(f"[添加] {instance_id}")
        self.log.append(f"      快捷方式: {lnk_path}")
        self.log.append(f"      启动器: {launcher_path}")

    def _rebuild_instance_buttons(self):
        """Rebuild the instance button list"""
        # Clear existing
        for i in reversed(range(self.instance_layout.count())):
            widget = self.instance_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # Add button for each instance
        running_data = self.launcher.running
        for inst in self.instances:
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            h_layout = QHBoxLayout(frame)
            h_layout.setContentsMargins(8, 6, 8, 6)

            # Instance info
            label = QLabel(f"{inst.instance_id}\n{inst.lnk_path}")
            label.setFont(QFont("Segoe UI", 10))
            label.setMinimumWidth(220)
            h_layout.addWidget(label)

            # Status indicator - get current status
            status_info = running_data.get(inst.instance_id, {})
            status = status_info.get('status', 'stopped')

            if status == 'running':
                status_text = "✅ 运行中"
                status_color = "#2ea043"
            elif status == 'launching':
                status_text = "⏳ 启动中"
                status_color = "#d29922"
            else:
                status_text = "⏹️ 未运行"
                status_color = "#888888"

            status_label = QLabel(status_text)
            status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            status_label.setStyleSheet(f"color: {status_color};")
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setMinimumWidth(80)
            h_layout.addWidget(status_label)
            h_layout.addStretch()

            btn_launch = QPushButton("启动")
            btn_launch.clicked.connect(lambda checked, i=inst: self.launch_instance(i))
            h_layout.addWidget(btn_launch)

            btn_remove = QPushButton("删除")
            btn_remove.setStyleSheet("""
                QPushButton {
                    background-color: rgba(200, 50, 50, 0.8);
                }
                QPushButton:hover {
                    background-color: rgba(200, 50, 50, 1);
                }
            """)
            btn_remove.clicked.connect(lambda checked, i=inst: self._remove_instance(i))
            h_layout.addWidget(btn_remove)

            self.instance_layout.addWidget(frame)

        # Force layout update
        self.instance_frame.update()
        self.instance_frame.repaint()

    def launch_instance(self, inst: AppInstance):
        """Launch the specified instance"""
        try:
            if not os.path.exists(inst.lnk_path):
                QMessageBox.warning(
                    self,
                    "文件不存在",
                    f"快捷方式不存在:\n{inst.lnk_path}\n\n请检查路径是否正确。"
                )
                return

            if not os.path.exists(inst.launcher_path):
                QMessageBox.warning(
                    self,
                    "启动器不存在",
                    f"启动器不存在:\n{inst.launcher_path}\n\n请检查路径是否正确。"
                )
                return

            self.launcher.launch(inst)
            self.log.append(f"[启动] {inst.instance_id} - 已发送启动命令")

            # Update status immediately to launching
            if inst.instance_id not in self.launcher.running:
                self.launcher.running[inst.instance_id] = {
                    "status": "launching",
                    "launcher_pid": None,
                    "children": [],
                }
            # Update UI immediately to show launching status in the list
            self.update_ui(self.launcher.running)
            # Refresh again after 1 second to capture launched process
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, self._force_refresh)

        except Exception as e:
            QMessageBox.critical(self, "启动失败", f"错误: {str(e)}")

    def _force_refresh(self):
        """Force a refresh - do one manual scan"""
        self.monitor.do_scan()

    def update_ui(self, data: Dict):
        """Update the status log and instance status display"""
        self.log.clear()

        if not data:
            self.log.append("没有检测到运行中的实例")
        else:
            for instance_id, status_info in data.items():
                status = status_info.get('status', 'unknown')
                children = status_info.get('children', [])

                if status == 'running':
                    self.log.append(f"✅ {instance_id}: running")
                    for c in children:
                        self.log.append(f"   └─ {c['name']} (PID: {c['pid']})")
                else:
                    self.log.append(f"⚠️  {instance_id}: {status}")

        # Rebuild instance buttons to update status indicators - this refreshes the status display
        self._rebuild_instance_buttons()

    def add_instance(self, instance_id: str, lnk_path: str, launcher_path: str):
        """Add a new instance to the list"""
        inst = AppInstance(instance_id, lnk_path, launcher_path)
        self.instances.append(inst)
        # Update instances in monitor
        self.monitor.instances = self.instances
        self._rebuild_instance_buttons()
        self._save_instances()

    def _remove_instance(self, inst: AppInstance):
        """Remove an instance from the list"""
        if inst in self.instances:
            self.instances.remove(inst)
            if inst.instance_id in self.launcher.launchers:
                del self.launcher.launchers[inst.instance_id]
            if inst.instance_id in self.launcher.running:
                del self.launcher.running[inst.instance_id]
            self.monitor.instances = self.instances
            self._rebuild_instance_buttons()
            self.log.append(f"[删除] {inst.instance_id}")
            self._save_instances()

    def closeEvent(self, event):
        """Clean up when closing"""
        # Save current instances config
        self._save_instances()
        self.monitor.stop()
        # Don't wait() - it blocks UI thread causing not responding
        # Thread will exit on its own since we set running = False
        self.monitor.quit()
        event.accept()

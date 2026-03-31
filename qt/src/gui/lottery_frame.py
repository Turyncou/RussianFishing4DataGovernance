"""Wheel of Fortune (Lottery) frame"""
import math
import random
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QTableWidget, QTableWidgetItem, QDoubleSpinBox,
    QLineEdit, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QFont
from PySide6.QtCore import QPointF

from src.core.models import LotteryPrize
from src.data.persistence import LotteryPersistence


def _is_dark(color_hex: str) -> bool:
    """Check if a hex color is dark"""
    color_hex = color_hex.lstrip('#')
    if len(color_hex) != 6:
        return True
    try:
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        # Calculate luminance
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        return luminance < 128
    except Exception:
        return True


class WheelWidget(QWidget):
    """Wheel drawing widget"""

    def __init__(self):
        super().__init__()
        self.prizes: List[LotteryPrize] = []
        self.current_angle = 0
        self.setFixedSize(400, 400)

    def update_prizes(self, prizes: List[LotteryPrize], current_angle: float = 0):
        """Update prizes and redraw"""
        self.prizes = prizes
        self.current_angle = current_angle
        self.update()

    def paintEvent(self, event):
        """Draw the wheel"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = QPointF(200, 200)
        radius = 180

        if not self.prizes:
            return

        total_probability = sum(p.probability for p in self.prizes)
        angle_start = 0

        for prize in self.prizes:
            slice_angle = (prize.probability / total_probability) * 360
            self._draw_slice(painter, center, radius, angle_start, slice_angle, prize)
            angle_start += slice_angle

        # Draw pointer triangle at top center
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(QColor("white"), 2))
        points = [
            QPointF(200, 10),
            QPointF(190, -5),
            QPointF(210, -5),
        ]
        painter.drawPolygon(points)

    def _draw_slice(self, painter: QPainter, center: QPointF, r: float,
                    start_angle: float, sweep_angle: float, prize: LotteryPrize):
        """Draw a single slice"""
        # Convert to radians, Qt uses clockwise from 3 o'clock, we start from top (12 o'clock) = -90 degrees
        start_rad = math.radians(-90 + (start_angle + self.current_angle))
        end_rad = math.radians(-90 + (start_angle + sweep_angle + self.current_angle))

        color = QColor(prize.color)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor("black"), 2))

        # Generate polygon
        from math import cos, sin
        points = [center]
        steps = int(sweep_angle / 2) + 2
        for i in range(steps):
            angle = math.radians(-90 + start_angle + i * (sweep_angle / (steps - 1)) + self.current_angle)
            x = center.x() + r * cos(angle)
            y = center.y() + r * sin(angle)
            points.append(QPointF(x, y))
        points.append(center)

        painter.drawPolygon(points)

        # Draw label in the middle of the slice
        mid_angle = math.radians(-90 + start_angle + sweep_angle/2 + self.current_angle)
        label_r = r * 0.6
        lx = center.x() + label_r * cos(mid_angle)
        ly = center.y() + label_r * sin(mid_angle)

        # Choose text color based on background darkness
        if _is_dark(prize.color):
            text_color = QColor("white")
        else:
            text_color = QColor("black")

        painter.setPen(QPen(text_color))
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QPointF(lx, ly), prize.name)


class LotteryFrame(QWidget):
    """Wheel of Fortune lottery frame"""

    def __init__(self, persistence: LotteryPersistence):
        super().__init__()
        self.persistence = persistence
        self.prizes: List[LotteryPrize] = []
        self.is_spinning = False
        self.current_angle = 0
        self.spin_speed = 0
        self.deceleration = 0.98

        self._create_widgets()
        self.load_prizes()

    def _create_widgets(self):
        """Create the widgets for the lottery frame"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("🎡 转盘抽奖")
        title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Main content frame
        content_group = QWidget()
        content_group.setStyleSheet("QWidget { background-color: #252525; border-radius: 12px; }")
        content_layout = QHBoxLayout(content_group)
        content_layout.setContentsMargins(15, 15, 15, 15)

        # Left side - wheel
        self.wheel_widget = WheelWidget()
        content_layout.addWidget(self.wheel_widget, 0, Qt.AlignCenter)

        # Right side - controls
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(10, 20, 10, 20)
        control_layout.setSpacing(8)

        # Result label
        self.result_label = QLabel("点击开始\n抽奖")
        self.result_label.setFont(QFont("Segoe UI", 18))
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumHeight(100)
        control_layout.addWidget(self.result_label)

        # Buttons
        self.spin_button = QPushButton("🎯 开始抽奖")
        self.spin_button.setFont(QFont("Segoe UI", 16))
        self.spin_button.setFixedSize(130, 50)
        self.spin_button.setStyleSheet("""
            QPushButton {
                background-color: #2aa040;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #1a7030;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.spin_button.clicked.connect(self.start_spin)
        control_layout.addWidget(self.spin_button, 0, Qt.AlignHCenter)

        self.setting_button = QPushButton("⚙️ 奖项设置")
        self.setting_button.setFont(QFont("Segoe UI", 16))
        self.setting_button.setFixedSize(130, 50)
        self.setting_button.setStyleSheet("border-radius: 10px;")
        self.setting_button.clicked.connect(self.open_settings)
        control_layout.addWidget(self.setting_button, 0, Qt.AlignHCenter)

        control_layout.addStretch()
        content_layout.addWidget(control_widget)

        layout.addWidget(content_group, 1)
        self.setLayout(layout)

    def load_prizes(self):
        """Load prizes from persistence"""
        self.prizes = self.persistence.load_prizes()
        self.refresh_wheel()

    def refresh_wheel(self):
        """Refresh wheel display"""
        self.wheel_widget.update_prizes(self.prizes, self.current_angle)

    def start_spin(self):
        """Start spinning the wheel"""
        if self.is_spinning:
            return

        if not self.prizes:
            QMessageBox.warning(self, "警告", "请先设置奖项")
            return

        total_probability = sum(p.probability for p in self.prizes)
        if total_probability <= 0:
            QMessageBox.warning(self, "警告", "总概率必须大于0")
            return

        self.is_spinning = True
        self.spin_button.setEnabled(False)
        # Random spin between 5 and 10 full rotations
        self.spin_speed = random.uniform(10, 20)
        self._animate_spin()

    def _animate_spin(self):
        """Animate the spinning"""
        if not self.is_spinning:
            return

        self.current_angle += self.spin_speed
        self.current_angle %= 360
        self.spin_speed *= self.deceleration
        self.refresh_wheel()

        if self.spin_speed < 0.1:
            self.stop_spin()
            return

        QTimer.singleShot(16, self._animate_spin)

    def stop_spin(self):
        """Stop spinning and determine winner"""
        self.is_spinning = False
        # Find which slice the pointer is on
        # Pointer is fixed at top (12 o'clock), wheel is rotated clockwise
        # The pointer sees angle = (360 - current_angle) mod 360
        pointer_angle = (360 - self.current_angle) % 360
        current_angle = 0
        total_probability = sum(p.probability for p in self.prizes)
        winning_prize = None

        for prize in self.prizes:
            slice_angle = (prize.probability / total_probability) * 360
            if current_angle <= pointer_angle < current_angle + slice_angle:
                winning_prize = prize
                break
            current_angle += slice_angle

        if winning_prize:
            self.result_label.setText(f"恭喜!\n{winning_prize.name}")
        else:
            self.result_label.setText("再来一次!")

        self.spin_button.setEnabled(True)

    def open_settings(self):
        """Open prize settings dialog"""
        dialog = PrizeSettingsDialog(self, self.prizes)
        dialog.prizes_saved.connect(self._on_settings_saved)
        dialog.exec()

    def _on_settings_saved(self, new_prizes: List[LotteryPrize]):
        """Save new prizes settings"""
        self.prizes = new_prizes
        self.persistence.save_prizes(new_prizes)
        self.refresh_wheel()


class PrizeSettingsDialog(QDialog):
    """Dialog for editing lottery prizes"""

    prizes_saved = Signal(object)

    def __init__(self, parent, current_prizes: List[LotteryPrize]):
        super().__init__(parent)
        self.prizes = current_prizes.copy()

        self.setWindowTitle("奖项设置")
        self.setFixedSize(500, 480)
        self.setModal(True)

        self._create_widgets()

    def _create_widgets(self):
        """Create dialog widgets"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel("奖项设置")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Prize table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["奖项名称", "概率(%)", "颜色", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        for i, prize in enumerate(self.prizes):
            self._add_prize_row(i, prize)

        # Add button
        add_btn = QPushButton("+ 添加奖项")
        add_btn.setFixedWidth(120)
        add_btn.clicked.connect(self._add_prize)
        layout.addWidget(add_btn, 0, Qt.AlignLeft)

        # Bottom buttons and total
        bottom_layout = QHBoxLayout()
        total_probability = sum(p.probability for p in self.prizes)
        self.total_label = QLabel(f"总概率: {total_probability:.1f}%")
        bottom_layout.addWidget(self.total_label)

        bottom_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self._save_settings)
        bottom_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #888888;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        layout.addLayout(bottom_layout)

    def _add_prize_row(self, index: int, prize: LotteryPrize):
        """Add a row to the prize table"""
        self.table.insertRow(index)

        name_item = QTableWidgetItem(prize.name)
        self.table.setItem(index, 0, name_item)

        prob_item = QTableWidgetItem(f"{prize.probability}")
        self.table.setItem(index, 1, prob_item)

        color_item = QTableWidgetItem(prize.color)
        self.table.setItem(index, 2, color_item)

        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc3333;
            }
            QPushButton:hover {
                background-color: #aa2222;
            }
        """)
        delete_btn.clicked.connect(lambda: self._delete_prize(index))
        self.table.setCellWidget(index, 3, delete_btn)

    def _add_prize(self):
        """Add a new empty prize"""
        new_prize = LotteryPrize("新奖项", 10.0, "#cccccc")
        self.prizes.append(new_prize)
        self._add_prize_row(len(self.prizes) - 1, new_prize)
        self._update_total()

    def _delete_prize(self, index):
        """Delete a prize row"""
        self.table.removeRow(index)
        del self.prizes[index]
        # Recreate table to fix indices
        self.table.clear()
        self.table.setRowCount(0)
        for i, prize in enumerate(self.prizes):
            self._add_prize_row(i, prize)
        self._update_total()

    def _update_total(self):
        """Update total probability display"""
        total = 0
        for row in range(self.table.rowCount()):
            prob_item = self.table.item(row, 1)
            if prob_item:
                try:
                    prob = float(prob_item.text())
                    total += prob
                except ValueError:
                    pass
        self.total_label.setText(f"总概率: {total:.1f}%")

    def _save_settings(self):
        """Save settings and close"""
        new_prizes = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            prob_item = self.table.item(row, 1)
            color_item = self.table.item(row, 2)

            if not name_item or not prob_item:
                continue

            name = name_item.text().strip()
            if not name:
                continue

            try:
                prob = float(prob_item.text())
                if prob < 0 or prob > 100:
                    QMessageBox.warning(self, "警告", f"第{row+1}行: 概率必须在0-100之间")
                    return
                color = "#cccccc"
                if color_item and color_item.text().strip():
                    color = color_item.text().strip()
                new_prizes.append(LotteryPrize(name, prob, color))
            except ValueError:
                QMessageBox.warning(self, "警告", f"第{row+1}行: 概率必须是数字")
                return

        total = sum(p.probability for p in new_prizes)
        if total <= 0:
            QMessageBox.warning(self, "警告", "总概率必须大于0")
            return

        if abs(total - 100) > 0.1:
            result = QMessageBox.question(
                self,
                "提示",
                f"当前总概率为 {total:.1f}%, 不等于100%, 是否继续保存?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return

        self.prizes_saved.emit(new_prizes)
        self.accept()

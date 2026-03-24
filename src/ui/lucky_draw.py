"""Lucky Draw Wheel UI widget"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QDialogButtonBox, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem
)
from PyQt6.QtGui import QBrush, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF
from src.core.data_manager import DataManager
from src.ui.lucky_draw import LuckyDrawModel


class LuckyDrawWidget(QWidget):
    """Lucky draw wheel widget"""

    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.data_manager = data_manager
        self.model = LuckyDrawModel()

        # Load saved data
        saved_data = data_manager.load_lucky_draw()
        for prize in saved_data:
            self.model.add_prize(prize["name"], prize["probability"])

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)

        # Graphics view for wheel
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumHeight(400)
        layout.addWidget(self.view)

        # Redraw wheel
        self.draw_wheel()

        # Controls
        controls_layout = QHBoxLayout()

        self.spin_button = QPushButton("开始抽奖")
        self.spin_button.clicked.connect(self.on_spin_clicked)
        controls_layout.addWidget(self.spin_button)

        self.add_button = QPushButton("添加奖项")
        self.add_button.clicked.connect(self.on_add_clicked)
        controls_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("编辑奖项")
        self.edit_button.clicked.connect(self.on_edit_clicked)
        controls_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("删除奖项")
        self.remove_button.clicked.connect(self.on_remove_clicked)
        controls_layout.addWidget(self.remove_button)

        layout.addLayout(controls_layout)

        # Prize list
        self.prize_list = QListWidget()
        self.update_prize_list()
        layout.addWidget(self.prize_list)

        self.setLayout(layout)

    def draw_wheel(self):
        """Draw the prize wheel on the graphics scene"""
        self.scene.clear()
        prizes = self.model.get_prizes()

        if not prizes:
            return

        diameter = 380
        center_x = 200
        center_y = 200
        start_angle = 0

        colors = [
            QColor(255, 100, 100),
            QColor(100, 255, 100),
            QColor(100, 100, 255),
            QColor(255, 255, 100),
            QColor(255, 100, 255),
            QColor(100, 255, 255),
            QColor(255, 170, 100),
            QColor(170, 255, 100),
        ]

        for i, prize in enumerate(prizes):
            angle_span = 360 * prize["probability"]
            rect = QRectF(
                center_x - diameter/2,
                center_y - diameter/2,
                diameter,
                diameter
            )
            ellipse = QGraphicsEllipseItem(rect)
            ellipse.setStartAngle(int(start_angle * 16))
            ellipse.setSpanAngle(int(angle_span * 16))
            color_idx = i % len(colors)
            ellipse.setBrush(QBrush(colors[color_idx]))
            ellipse.setPen(QPen(QColor(0, 0, 0), 2))
            self.scene.addItem(ellipse)

            # Add text label in the middle of the slice
            mid_angle = start_angle + angle_span / 2
            import math
            rad = mid_angle * math.pi / 180
            text_x = center_x + (diameter/4) * math.cos(rad)
            text_y = center_y + (diameter/4) * math.sin(rad)
            text = self.scene.addText(prize["name"])
            text.setPos(text_x - text.boundingRect().width()/2, text_y - text.boundingRect().height()/2)
            text.setDefaultTextColor(QColor(0, 0, 0))
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            text.setFont(font)

            start_angle += angle_span

        # Draw outer circle border
        outer = QGraphicsEllipseItem(QRectF(
            center_x - diameter/2 - 5,
            center_y - diameter/2 - 5,
            diameter + 10,
            diameter + 10
        ))
        outer.setPen(QPen(QColor(0, 0, 0), 3))
        outer.setBrush(QBrush(Qt.GlobalColor.transparent))
        self.scene.addItem(outer)

        # Draw fixed pointer at top center
        pointer_polygon = self.scene.addPolygon([
            QPointF(center_x - 10, center_y - diameter/2 - 20),
            QPointF(center_x + 10, center_y - diameter/2 - 20),
            QPointF(center_x, center_y - diameter/2 + 10),
        ])
        pointer_polygon.setBrush(QBrush(QColor(200, 0, 0)))
        pointer_polygon.setPen(QPen(QColor(0, 0, 0), 1))

    def update_prize_list(self):
        """Update the prize list display"""
        self.prize_list.clear()
        for i, prize in enumerate(self.model.get_prizes()):
            item_text = f"{i+1}. {prize['name']} - {prize['probability']*100:.1f}%"
            item = QListWidgetItem(item_text)
            self.prize_list.addItem(item)
        self.save()

    def on_spin_clicked(self):
        """Handle spin button click"""
        result = self.model.spin()
        if result is None:
            return
        # TODO: Add spin animation and show result dialog
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "抽奖结果", f"恭喜中奖: {result['name']}")

    def on_add_clicked(self):
        """Handle add button click"""
        dialog = PrizeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, prob = dialog.get_values()
            self.model.add_prize(name, prob)
            self.update_prize_list()
            self.draw_wheel()

    def on_edit_clicked(self):
        """Handle edit button click"""
        current_item = self.prize_list.currentItem()
        if current_item is None:
            return
        index = self.prize_list.row(current_item)
        prize = self.model.get_prizes()[index]

        dialog = PrizeDialog(self, prize["name"], prize["probability"])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, prob = dialog.get_values()
            self.model.update_prize(index, name, prob)
            self.update_prize_list()
            self.draw_wheel()

    def on_remove_clicked(self):
        """Handle remove button click"""
        current_item = self.prize_list.currentItem()
        if current_item is None:
            return
        index = self.prize_list.row(current_item)
        self.model.remove_prize(index)
        self.update_prize_list()
        self.draw_wheel()

    def save(self):
        """Save current data"""
        data = []
        for prize in self.model.get_prizes():
            data.append({
                "name": prize["name"],
                "probability": prize["probability"]
            })
        self.data_manager.save_lucky_draw(data)


class PrizeDialog(QDialog):
    """Dialog for adding/editing a prize"""

    def __init__(self, parent, name: str = "", probability: float = 0.1):
        super().__init__(parent)
        self.setWindowTitle("奖项设置")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(name)
        layout.addRow("奖项名称:", self.name_edit)

        self.prob_spin = QDoubleSpinBox()
        self.prob_spin.setRange(0.01, 1.0)
        self.prob_spin.setSingleStep(0.05)
        self.prob_spin.setValue(probability)
        layout.addRow("概率 (0-1):", self.prob_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self):
        """Get the entered values"""
        return self.name_edit.text().strip(), self.prob_spin.value()


class LuckyDrawModel:
    """Model for lucky draw business logic"""

    def __init__(self):
        self._prizes = []

    def get_prizes(self):
        """Get all prizes"""
        return self._prizes

    def add_prize(self, name: str, probability: float) -> bool:
        """Add a prize"""
        if not name.strip():
            return False
        self._prizes.append({
            "name": name.strip(),
            "probability": probability
        })
        self._normalize()
        return True

    def update_prize(self, index: int, name: str, probability: float) -> bool:
        """Update a prize"""
        if not (0 <= index < len(self._prizes)):
            return False
        if not name.strip():
            return False
        self._prizes[index] = {
            "name": name.strip(),
            "probability": probability
        }
        self._normalize()
        return True

    def remove_prize(self, index: int) -> bool:
        """Remove a prize"""
        if not (0 <= index < len(self._prizes)):
            return False
        del self._prizes[index]
        self._normalize()
        return True

    def _normalize(self):
        """Normalize probabilities to sum to 1"""
        if not self._prizes:
            return
        total = sum(p["probability"] for p in self._prizes)
        if total > 0:
            for p in self._prizes:
                p["probability"] = p["probability"] / total

    def spin(self):
        """Spin the wheel and return the winning prize"""
        if not self._prizes:
            return None

        import random
        r = random.random()
        cumulative = 0.0
        for prize in self._prizes:
            cumulative += prize["probability"]
            if r <= cumulative:
                return prize
        return self._prizes[-1]

    def clear_all(self):
        """Clear all prizes"""
        self._prizes.clear()

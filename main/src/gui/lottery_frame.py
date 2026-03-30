"""Wheel of Fortune (Lottery) frame"""
import math
import random
import customtkinter as ctk
from tkinter import Canvas
from CTkMessagebox import CTkMessagebox
from typing import List

from core.models import LotteryPrize
from data.persistence import LotteryPersistence


class LotteryFrame(ctk.CTkFrame):
    """Wheel of Fortune lottery frame"""

    def __init__(self, parent, persistence: LotteryPersistence):
        super().__init__(parent, fg_color="transparent", corner_radius=16)
        self.persistence = persistence
        self.prizes: List[LotteryPrize] = []
        self.is_spinning = False
        self.current_angle = 0
        self.target_angle = 0
        self.spin_speed = 0
        self.deceleration = 0.98

        self.create_widgets()
        self.load_prizes()

    def create_widgets(self):
        """Create the widgets for the lottery frame"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="🎡 转盘抽奖",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.pack(pady=(15, 8))

        # Main content frame
        content_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12)
        content_frame.pack(fill="both", expand=True, padx=15, pady=8)

        # Left side - wheel
        self.wheel_canvas = Canvas(
            content_frame,
            width=400,
            height=400,
            bg="#252525",
            highlightthickness=0
        )
        self.wheel_canvas.pack(side="left", padx=(20, 10), pady=20)

        # Right side - controls
        control_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        control_frame.pack(side="right", fill="y", padx=(10, 20), pady=20)

        # Result label
        self.result_label = ctk.CTkLabel(
            control_frame,
            text="点击开始\n抽奖",
            font=ctk.CTkFont(size=18),
            justify="center"
        )
        self.result_label.pack(pady=(0, 30))

        # Buttons
        self.spin_button = ctk.CTkButton(
            control_frame,
            text="🎯 开始抽奖",
            command=self.start_spin,
            font=ctk.CTkFont(size=16),
            width=130,
            height=50,
            corner_radius=10,
            fg_color="#2aa040",
            hover_color="#1a7030"
        )
        self.spin_button.pack(pady=8)

        self.setting_button = ctk.CTkButton(
            control_frame,
            text="⚙️ 奖项设置",
            command=self.open_settings,
            font=ctk.CTkFont(size=16),
            width=130,
            height=50,
            corner_radius=10
        )
        self.setting_button.pack(pady=8)

        # Fixed pointer at top center
        self.wheel_canvas.create_polygon(
            200, 10, 190, -5, 210, -5,
            fill="white",
            tags="pointer"
        )
        self.draw_wheel()

    def load_prizes(self):
        """Load prizes from persistence"""
        self.prizes = self.persistence.load_prizes()
        self.draw_wheel()

    def draw_wheel(self):
        """Draw the wheel on canvas"""
        # Clear old wheel
        self.wheel_canvas.delete("slice")

        if not self.prizes:
            return

        center_x = 200
        center_y = 200
        radius = 180

        total_probability = sum(p.probability for p in self.prizes)
        current_angle = self.current_angle
        angle_start = 0

        for prize in self.prizes:
            # Calculate slice angle
            slice_angle = (prize.probability / total_probability) * 360
            self._draw_slice(center_x, center_y, radius, angle_start, slice_angle, prize.color, prize.name)
            angle_start += slice_angle

    def _draw_slice(self, cx, cy, r, start_angle, sweep_angle, color, label):
        """Draw a single slice on the wheel"""
        # Convert to radians, start from top
        start_rad = math.radians(-90 + (start_angle + self.current_angle))
        end_rad = math.radians(-90 + (start_angle + sweep_angle + self.current_angle))

        # Generate points for the polygon
        points = [(cx, cy)]
        steps = int(sweep_angle / 2) + 2
        for i in range(steps):
            angle = math.radians(-90 + start_angle + i * (sweep_angle / (steps - 1)) + self.current_angle)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        points.append((cx, cy))

        # Convert to flat list
        flat_points = []
        for x, y in points:
            flat_points.extend([x, y])

        self.wheel_canvas.create_polygon(
            flat_points,
            fill=color,
            outline="black",
            width=2,
            tags="slice"
        )

        # Draw label in the middle of the slice
        mid_angle = math.radians(-90 + start_angle + sweep_angle/2 + self.current_angle)
        label_r = r * 0.6
        lx = cx + label_r * math.cos(mid_angle)
        ly = cy + label_r * math.sin(mid_angle)
        self.wheel_canvas.create_text(
            lx, ly,
            text=label,
            fill="white" if _is_dark(color) else "black",
            font=("Arial", 10, "bold"),
            tags="slice"
        )

    def start_spin(self):
        """Start spinning the wheel"""
        if self.is_spinning:
            return

        if not self.prizes:
            CTkMessagebox(title="警告", message="请先设置奖项", icon="warning", option_1="确定")
            return

        total_probability = sum(p.probability for p in self.prizes)
        if total_probability <= 0:
            CTkMessagebox(title="警告", message="总概率必须大于0", icon="warning", option_1="确定")
            return

        self.is_spinning = True
        self.spin_button.configure(state="disabled")
        # Random spin between 5 and 10 full rotations
        self.spin_speed = random.uniform(10, 20)
        self.animate_spin()

    def animate_spin(self):
        """Animate the spinning"""
        if not self.is_spinning:
            return

        self.current_angle += self.spin_speed
        self.current_angle %= 360
        self.spin_speed *= self.deceleration
        self.draw_wheel()

        if self.spin_speed < 0.1:
            self.stop_spin()
            return

        self.after(16, self.animate_spin)

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
            self.result_label.configure(text=f"恭喜!\n{winning_prize.name}")
        else:
            self.result_label.configure(text="再来一次!")

        self.spin_button.configure(state="normal")

    def open_settings(self):
        """Open prize settings dialog"""
        dialog = PrizeSettingsDialog(self.winfo_toplevel(), self.prizes, self.on_settings_saved)

    def on_settings_saved(self, new_prizes: List[LotteryPrize]):
        """Save new prizes settings"""
        self.prizes = new_prizes
        self.persistence.save_prizes(new_prizes)
        self.draw_wheel()


class PrizeSettingsDialog(ctk.CTkToplevel):
    """Dialog for editing lottery prizes"""

    def __init__(self, parent, current_prizes: List[LotteryPrize], callback):
        super().__init__(parent)
        self.callback = callback
        self.prizes = current_prizes.copy()

        self.title("奖项设置")
        self.geometry("500x480")
        self.resizable(False, False)

        self.grab_set()

        self.create_widgets()

    def create_widgets(self):
        """Create dialog widgets"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="奖项设置",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)

        # Prize list frame
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Headers
        headers_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        headers_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(headers_frame, text="奖项名称", width=150).pack(side="left", padx=5)
        ctk.CTkLabel(headers_frame, text="概率(%)", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(headers_frame, text="颜色", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(headers_frame, text="操作", width=80).pack(side="left", padx=5)

        # Scrollable frame for prizes
        self.scroll_frame = ctk.CTkScrollableFrame(list_frame, height=220)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom buttons - create total_label first before adding rows
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        total_probability = sum(p.probability for p in self.prizes)
        self.total_label = ctk.CTkLabel(
            btn_frame,
            text=f"总概率: {total_probability:.1f}%"
        )
        self.total_label.pack(side="left")

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            command=self.save_settings,
            width=100
        )
        save_btn.pack(side="right", padx=5)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.destroy,
            width=100,
            fg_color="#888888",
            hover_color="#666666"
        )
        cancel_btn.pack(side="right", padx=5)

        # Now add prize rows after total_label is created
        self.prize_rows = []
        for i, prize in enumerate(self.prizes):
            self._add_prize_row(i, prize)

        # Add button
        add_btn = ctk.CTkButton(
            list_frame,
            text="+ 添加奖项",
            command=self.add_prize,
            width=120
        )
        add_btn.pack(pady=10)

    def _add_prize_row(self, index, prize: LotteryPrize):
        """Add a row to the prize list"""
        row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        name_var = ctk.StringVar(value=prize.name)
        name_entry = ctk.CTkEntry(row_frame, width=140, textvariable=name_var)
        name_entry.pack(side="left", padx=5)

        prob_var = ctk.StringVar(value=f"{prize.probability}")
        prob_entry = ctk.CTkEntry(row_frame, width=70, textvariable=prob_var)
        prob_entry.pack(side="left", padx=5)

        color_var = ctk.StringVar(value=prize.color)
        color_entry = ctk.CTkEntry(row_frame, width=70, textvariable=color_var)
        color_entry.pack(side="left", padx=5)

        delete_btn = ctk.CTkButton(
            row_frame,
            text="删除",
            command=lambda idx=index: self.delete_prize(row_frame, idx),
            width=60,
            fg_color="#cc3333",
            hover_color="#aa2222"
        )
        delete_btn.pack(side="left", padx=5)

        self.prize_rows.append({
            'frame': row_frame,
            'name_var': name_var,
            'prob_var': prob_var,
            'color_var': color_var
        })

        self._update_total()

    def add_prize(self):
        """Add a new empty prize"""
        new_prize = LotteryPrize("新奖项", 10.0, "#cccccc")
        self.prizes.append(new_prize)
        self._add_prize_row(len(self.prizes) - 1, new_prize)
        self._update_total()

    def delete_prize(self, row_frame, index):
        """Delete a prize row"""
        row_frame.destroy()
        del self.prizes[index]
        del self.prize_rows[index]
        self._update_total()

    def _update_total(self):
        """Update total probability display"""
        total = 0
        for i, row in enumerate(self.prize_rows):
            try:
                prob = float(row['prob_var'].get())
                total += prob
            except ValueError:
                pass
        self.total_label.configure(text=f"总概率: {total:.1f}%")

    def save_settings(self):
        """Save settings and close"""
        new_prizes = []
        for row in self.prize_rows:
            name = row['name_var'].get().strip()
            if not name:
                continue
            try:
                prob = float(row['prob_var'].get())
                if prob < 0 or prob > 100:
                    CTkMessagebox(title="警告", message="概率必须在0-100之间", icon="warning", option_1="确定")
                    return
                color = row['color_var'].get().strip() or "#cccccc"
                new_prizes.append(LotteryPrize(name, prob, color))
            except ValueError:
                CTkMessagebox(title="警告", message="概率必须是数字", icon="warning", option_1="确定")
                return

        total = sum(p.probability for p in new_prizes)
        if total <= 0:
            CTkMessagebox(title="警告", message="总概率必须大于0", icon="warning", option_1="确定")
            return

        if abs(total - 100) > 0.1:
            result = CTkMessagebox(
                title="提示",
                message=f"当前总概率为 {total:.1f}%, 不等于100%, 是否继续保存?",
                icon="question",
                option_1="否",
                option_2="是"
            )
            result = result.get() == "是"
            if not result:
                return

        self.callback(new_prizes)
        self.grab_release()
        self.destroy()


def _is_dark(color_hex: str) -> bool:
    """Check if a hex color is dark"""
    # Remove # if present
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

"""Cat follower widget - three cats that follow mouse movement"""
import math
import customtkinter as ctk
from PIL import Image, ImageTk


class CatFollower:
    """Manages multiple cats that follow mouse movement on the canvas"""

    def __init__(self, canvas, num_cats=3):
        self.canvas = canvas
        self.num_cats = num_cats
        self.cat_items = []
        self.mouse_x = 0
        self.mouse_y = 0
        self.current_angles = [i * (2 * math.pi / num_cats) for i in range(num_cats)]
        self.distances = [80 + i * 30 for i in range(num_cats)]
        self.cat_ids = []
        self.head_ids = []
        self.eye_ids = []

    def create_cats(self):
        """Create the cat shapes on the canvas"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Start with mouse at center
        self.mouse_x = canvas_width / 2
        self.mouse_y = canvas_height / 2

        for i in range(self.num_cats):
            self._create_single_cat(i)

    def _create_single_cat(self, index):
        """Create a single cat at the correct position based on index"""
        x, y = self._get_cat_position(index)
        # Body (oval)
        body = self.canvas.create_oval(
            x - 15, y - 12, x + 15, y + 12,
            fill='#8e8e8e', outline='#555555', width=2
        )
        # Head
        head_x = x + 20
        head_y = y - 5
        head = self.canvas.create_oval(
            head_x - 10, head_y - 10, head_x + 10, head_y + 10,
            fill='#a0a0a0', outline='#555555', width=2
        )
        # Eyes (will be updated)
        eye1_x = head_x + 3
        eye1_y = head_y - 3
        eye2_x = head_x + 3
        eye2_y = head_y + 3
        eye1 = self.canvas.create_oval(
            eye1_x - 2, eye1_y - 2, eye1_x + 2, eye1_y + 2,
            fill='black'
        )
        eye2 = self.canvas.create_oval(
            eye2_x - 2, eye2_y - 2, eye2_x + 2, eye2_y + 2,
            fill='black'
        )

        self.cat_ids.append(body)
        self.head_ids.append(head)
        self.eye_ids.append((eye1, eye2))

    def _get_cat_position(self, index):
        """Calculate current cat position based on mouse position"""
        angle = self.current_angles[index]
        distance = self.distances[index]
        x = self.mouse_x + distance * math.cos(angle)
        y = self.mouse_y + distance * math.sin(angle)
        return x, y

    def _get_head_position(self, body_x, body_y, angle):
        """Calculate head position facing towards mouse"""
        # Head is in front of body, towards mouse
        head_distance = 22
        head_x = body_x + head_distance * math.cos(angle)
        head_y = body_y + head_distance * math.sin(angle)
        return head_x, head_y

    def _get_eye_position(self, head_x, head_y, angle):
        """Calculate eye positions - eyes point towards mouse"""
        # Offset eyes from head center towards mouse
        offset_x = 4 * math.cos(angle)
        offset_y = 4 * math.sin(angle)
        # Vertical spacing between eyes
        spacing = 3
        eye1_x = head_x + offset_x
        eye1_y = head_y - spacing + offset_y * 0.3
        eye2_x = head_x + offset_x
        eye2_y = head_y + spacing + offset_y * 0.3
        return (eye1_x, eye1_y), (eye2_x, eye2_y)

    def update_position(self, mouse_x, mouse_y):
        """Update cat positions based on new mouse position"""
        self.mouse_x = mouse_x
        self.mouse_y = mouse_y

        for i in range(self.num_cats):
            # Calculate target angle (towards mouse center - cats orbit mouse)
            body_x, body_y = self._get_cat_position(i)
            angle_to_mouse = math.atan2(self.mouse_y - body_y, self.mouse_x - body_x)
            self.current_angles[i] = angle_to_mouse

            # Move body
            body = self.cat_ids[i]
            new_body_x, new_body_y = self._get_cat_position(i)
            body_bbox = self.canvas.coords(body)
            current_width = (body_bbox[2] - body_bbox[0]) / 2
            current_height = (body_bbox[3] - body_bbox[1]) / 2
            self.canvas.coords(body,
                new_body_x - current_width, new_body_y - current_height,
                new_body_x + current_width, new_body_y + current_height
            )

            # Move head
            head = self.head_ids[i]
            head_x, head_y = self._get_head_position(new_body_x, new_body_y, angle_to_mouse)
            head_bbox = self.canvas.coords(head)
            h_width = (head_bbox[2] - head_bbox[0]) / 2
            h_height = (head_bbox[3] - head_bbox[1]) / 2
            self.canvas.coords(head,
                head_x - h_width, head_y - h_height,
                head_x + h_width, head_y + h_height
            )

            # Move eyes
            eye1_id, eye2_id = self.eye_ids[i]
            (eye1_x, eye1_y), (eye2_x, eye2_y) = self._get_eye_position(head_x, head_y, angle_to_mouse)
            for eye_id, (e_x, e_y) in [(eye1_id, (eye1_x, eye1_y)), (eye2_id, (eye2_x, eye2_y))]:
                eye_bbox = self.canvas.coords(eye_id)
                e_width = (eye_bbox[2] - eye_bbox[0]) / 2
                e_height = (eye_bbox[3] - eye_bbox[1]) / 2
                self.canvas.coords(eye_id,
                    e_x - e_width, e_y - e_height,
                    e_x + e_width, e_y + e_height
                )

    def on_resize(self, event):
        """Handle canvas resize"""
        # Recreate cats on resize
        for cat_id in self.cat_ids + self.head_ids:
            self.canvas.delete(cat_id)
        for eye1, eye2 in self.eye_ids:
            self.canvas.delete(eye1)
            self.canvas.delete(eye2)
        self.cat_ids.clear()
        self.head_ids.clear()
        self.eye_ids.clear()
        self.create_cats()

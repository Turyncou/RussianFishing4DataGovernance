"""Loading animation dialog - shows spinning indicator with message"""
import customtkinter as ctk
import threading
from typing import Optional


class LoadingDialog(ctk.CTkToplevel):
    """Modal loading dialog with spinning animation indicator"""

    def __init__(self, parent, message: str = "加载中...", show_cancel: bool = False):
        super().__init__(parent)
        self.parent = parent
        self.message = message
        self.show_cancel = show_cancel

        # Dialog configuration
        self.title("")
        self.geometry("300x120")
        self.resizable(False, False)
        self.grab_set()  # Make it modal

        # Center the dialog on parent
        self._center_window()

        # Prevent closing from window manager
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self._create_widgets()
        self._start_animation()

    def _center_window(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()
        # Get parent geometry
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        # Calculate position
        dialog_width = 300
        dialog_height = 120
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create the dialog widgets"""
        # Main frame
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Progress indicator frame
        self.indicator_frame = ctk.CTkFrame(main_frame, fg_color="transparent", width=40, height=40)
        self.indicator_frame.pack(side="left", padx=(0, 15))

        # Create a canvas for the spinning circle
        self.canvas = ctk.CTkCanvas(self.indicator_frame, width=40, height=40,
                                  bg=self._fg_color(), highlightthickness=0)
        self.canvas.pack()

        # Message label
        self.message_label = ctk.CTkLabel(main_frame, text=self.message,
                                       font=ctk.CTkFont(size=14))
        self.message_label.pack(side="left", fill="both", expand=True)

        # Cancel button if requested
        if self.show_cancel:
            self.cancel_btn = ctk.CTkButton(main_frame, text="取消", command=self.cancel,
                                        width=80, fg_color="#cc3333", hover_color="#aa2222")
            self.cancel_btn.pack(side="bottom", pady=(10, 0))

        # Animation state
        self.angle = 0
        self.animation_id: Optional[str] = None
        self.is_cancelled = False

    def _fg_color(self):
        """Get the foreground color matching the current appearance mode"""
        return self._fg_color = ctk.get_appearance_mode() == "Dark" and "#2b2b2b" or "#f0f0f0"

    def _draw_spinner(self):
        """Draw the spinning indicator arc"""
        self.canvas.delete("spinner")
        # Draw an arc that rotates to indicate loading
        x0, y0, x1, y1 = 2, 2, 38, 38
        # Arc spans 120 degrees out of 360, starting from current angle
        self.canvas.create_arc(x0, y0, x1, y1, start=self.angle, extent=120,
                             outline="#1f6feb", width=3, style="arc", tags="spinner")

    def _animate(self):
        """Animation callback - rotate the spinner"""
        if not self.winfo_exists():
            return
        self.angle = (self.angle + 10) % 360
        self._draw_spinner()
        self.animation_id = self.after(30, self._animate)

    def _start_animation(self):
        """Start the spinning animation"""
        self._animate()

    def update_message(self, new_message: str):
        """Update the loading message"""
        self.message_label.configure(text=new_message)
        self.update()

    def cancel(self):
        """Cancel the loading operation"""
        self.is_cancelled = True

    def is_cancellation_requested(self) -> bool:
        """Check if user requested cancellation"""
        return self.is_cancelled

    def close(self):
        """Close the loading dialog"""
        if self.animation_id:
            self.after_cancel(self.animation_id)
        self.grab_release()
        self.destroy()


def run_with_loading(parent, message: str, task, callback=None, show_cancel: bool = False):
    """
    Helper to run a task with loading dialog.

    Args:
        parent: Parent window
        message: Initial loading message
        task: Function to run in background (accepts cancellation_checker: () -> bool)
        callback: Function to call after task completes (result) -> None
        show_cancel: Whether to show cancel button
    """
    loading = LoadingDialog(parent, message, show_cancel)

    def wrapped_task():
        result = task(loading.is_cancellation_requested)
        # Schedule closing on main thread
        loading.after(0, lambda: _on_complete(result, loading, callback))

    thread = threading.Thread(target=wrapped_task, daemon=True)
    thread.start()


def _on_complete(result, loading: LoadingDialog, callback):
    """Called when task completes on main thread"""
    loading.close()
    if callback:
        callback(result)

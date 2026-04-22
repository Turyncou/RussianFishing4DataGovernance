"""Animation utilities for smooth UI transitions"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint


class FadeSlideAnimator:
    """Fade and slide animation for page transitions"""

    @staticmethod
    def animate_in(widget: QWidget, duration: int = 300, start_y: int = 20):
        """Animate widget entering the screen (fade in + slide up)

        Args:
            widget: Target widget to animate
            duration: Animation duration in milliseconds
            start_y: Starting Y offset (pixels)
        """
        widget.setStyleSheet(widget.styleSheet())

        # Position animation (slide up)
        pos_anim = QPropertyAnimation(widget, b"pos")
        pos_anim.setDuration(duration)
        current_pos = widget.pos()
        pos_anim.setStartValue(QPoint(current_pos.x(), current_pos.y() + start_y))
        pos_anim.setEndValue(current_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Opacity animation (fade in)
        opacity_anim = QPropertyAnimation(widget, b"windowOpacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Group animations
        group = QParallelAnimationGroup(widget)
        group.addAnimation(pos_anim)
        group.addAnimation(opacity_anim)
        group.start()

        return group

    @staticmethod
    def animate_out(widget: QWidget, duration: int = 200, end_y: int = -20):
        """Animate widget exiting the screen (fade out + slide up)

        Args:
            widget: Target widget to animate
            duration: Animation duration in milliseconds
            end_y: End Y offset (pixels)
        """
        # Opacity animation
        opacity_anim = QPropertyAnimation(widget, b"windowOpacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.InCubic)

        opacity_anim.start()
        return opacity_anim


class ButtonPulseAnimator:
    """Pulse animation for button feedback"""

    @staticmethod
    def pulse(widget: QWidget, scale: float = 1.05, duration: int = 150):
        """Create a subtle pulse effect on button click

        Args:
            widget: Button widget
            scale: Scale factor
            duration: Animation duration
        """
        original_size = widget.size()

        # Scale up
        anim_up = QPropertyAnimation(widget, b"size")
        anim_up.setDuration(duration // 2)
        anim_up.setEndValue(original_size * scale)
        anim_up.setEasingCurve(QEasingCurve.OutQuad)

        # Scale down
        anim_down = QPropertyAnimation(widget, b"size")
        anim_down.setDuration(duration // 2)
        anim_down.setStartValue(original_size * scale)
        anim_down.setEndValue(original_size)
        anim_down.setEasingCurve(QEasingCurve.InQuad)

        from PySide6.QtCore import QSequentialAnimationGroup
        group = QSequentialAnimationGroup(widget)
        group.addAnimation(anim_up)
        group.addAnimation(anim_down)
        group.start()

        return group

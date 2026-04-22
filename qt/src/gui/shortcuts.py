"""Keyboard shortcut management for the application"""
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QKeySequence, QKeyEvent, QShortcut
from PySide6.QtCore import Qt, Signal, QObject
from typing import Dict, Callable, Optional


class ShortcutManager(QObject):
    """Global shortcut manager for the application"""

    # Signal for shortcut activation
    shortcut_activated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.shortcuts: Dict[str, QShortcut] = {}
        self.parent = parent

    def register_shortcut(self, key: str, sequence: str, callback: Callable, description: str = ""):
        """Register a keyboard shortcut

        Args:
            key: Unique identifier for the shortcut
            sequence: Keyboard sequence (e.g., "Ctrl+S")
            callback: Function to call when activated
            description: Human-readable description
        """
        if self.parent is None:
            return

        shortcut = QShortcut(QKeySequence(sequence), self.parent)
        shortcut.activated.connect(callback)
        shortcut.setContext(Qt.ApplicationShortcut)
        self.shortcuts[key] = shortcut

        # Store description for help display
        if not hasattr(self, '_descriptions'):
            self._descriptions = {}
        self._descriptions[key] = {
            'sequence': sequence,
            'description': description
        }

    def get_shortcut_help(self) -> str:
        """Get formatted help text for all registered shortcuts"""
        if not hasattr(self, '_descriptions'):
            return ""

        lines = ["键盘快捷键:\n"]
        for key, info in self._descriptions.items():
            lines.append(f"  {info['sequence']:<12} - {info['description']}")

        return "\n".join(lines)

    def show_shortcut_help(self):
        """Show a dialog with all keyboard shortcuts"""
        help_text = self.get_shortcut_help()
        QMessageBox.information(self.parent, "键盘快捷键", help_text)

"""Background customization model - business logic for background settings"""
import os
from typing import Optional, Dict


class BackgroundModel:
    """Business logic for background customization"""

    def __init__(self):
        self._settings = {
            "custom_image_path": None,
            "transparency": 0.8  # 0 = fully transparent, 1 = fully opaque
        }

    def load_from_data(self, data: Dict) -> None:
        """Load from persisted data"""
        self._settings = data

    def get_settings(self) -> Dict:
        """Get current settings"""
        return self._settings

    def set_transparency(self, transparency: float) -> None:
        """Set transparency (0-1)"""
        # Clamp to valid range
        transparency = max(0.0, min(1.0, transparency))
        self._settings["transparency"] = transparency

    def set_custom_image(self, image_path: Optional[str]) -> bool:
        """Set custom background image path"""
        if image_path is None:
            self._settings["custom_image_path"] = None
            return True

        if not os.path.exists(image_path):
            return False

        self._settings["custom_image_path"] = image_path
        return True

    def get_custom_image_path(self) -> Optional[str]:
        """Get custom image path"""
        return self._settings["custom_image_path"]

    def has_custom_image(self) -> bool:
        """Check if there's a custom image"""
        return self._settings["custom_image_path"] is not None

    def get_effective_opacity(self) -> int:
        """Get effective opacity for QSS (0-255)"""
        # transparency 0 = fully transparent -> opacity 0
        # transparency 1 = fully opaque -> opacity 255
        return int(self._settings["transparency"] * 255)

    def reset_to_default(self) -> None:
        """Reset to default settings"""
        self._settings = {
            "custom_image_path": None,
            "transparency": 0.8
        }

    def get_data_for_saving(self) -> Dict:
        """Get data for saving"""
        return self._settings

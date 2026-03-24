"""Data persistence manager - handles loading/saving all data to JSON files"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class DataManager:
    """Manages data persistence for all application features"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, filename: str) -> Path:
        """Get full path for a data file"""
        return self.data_dir / filename

    def _load_json(self, filename: str, default: Any) -> Any:
        """Load JSON from file, return default if file doesn't exist or is corrupted"""
        path = self._get_path(filename)
        if not path.exists():
            return default

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Corrupted file, return default
            return default

    def _save_json(self, filename: str, data: Any) -> None:
        """Save JSON to file with backup"""
        path = self._get_path(filename)

        # Create backup if file exists
        if path.exists():
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_path = self._get_path(f"{filename.split('.')[0]}.{timestamp}.backup.json")
            try:
                with open(path, 'r', encoding='utf-8') as src:
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            except Exception:
                pass  # Ignore backup errors

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Lucky Draw
    def load_lucky_draw(self) -> list:
        """Load lucky draw prizes"""
        return self._load_json("lucky_draw.json", [])

    def save_lucky_draw(self, data: list) -> None:
        """Save lucky draw prizes"""
        self._save_json("lucky_draw.json", data)

    # Grinding Stats
    def load_grinding_stats(self) -> dict:
        """Load grinding statistics"""
        default = {
            "characters": [],
            "goal": {
                "target_silver": 0,
                "target_minutes": 0
            }
        }
        return self._load_json("grinding_stats.json", default)

    def save_grinding_stats(self, data: dict) -> None:
        """Save grinding statistics"""
        self._save_json("grinding_stats.json", data)

    # Storage Tracking
    def load_storage_tracking(self) -> dict:
        """Load storage tracking data"""
        default = {"characters": []}
        return self._load_json("storage_tracking.json", default)

    def save_storage_tracking(self, data: dict) -> None:
        """Save storage tracking data"""
        self._save_json("storage_tracking.json", data)

    # Friend Links
    def load_friend_links(self) -> list:
        """Load friend links"""
        return self._load_json("friend_links.json", [])

    def save_friend_links(self, data: list) -> None:
        """Save friend links"""
        self._save_json("friend_links.json", data)

    # Background Settings
    def load_background_settings(self) -> dict:
        """Load background settings"""
        default = {
            "custom_image_path": None,
            "transparency": 0.8
        }
        return self._load_json("background.json", default)

    def save_background_settings(self, data: dict) -> None:
        """Save background settings"""
        self._save_json("background.json", data)

    # Application Config
    def load_config(self) -> dict:
        """Load application configuration"""
        default = {
            "window_width": 1200,
            "window_height": 800,
            "last_open_tab": 0
        }
        return self._load_json("config.json", default)

    def save_config(self, data: dict) -> None:
        """Save application configuration"""
        self._save_json("config.json", data)

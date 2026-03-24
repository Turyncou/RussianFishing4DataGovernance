"""Storage duration tracking model - business logic for tracking fish storage time"""
from typing import List, Dict, Optional


class StorageTrackingModel:
    """Business logic for storage duration tracking"""

    def __init__(self):
        self._data = {"characters": []}

    def load_from_data(self, data: Dict) -> None:
        """Load from persisted data"""
        self._data = data

    def get_characters(self) -> List[Dict]:
        """Get all storage characters/spots"""
        return self._data["characters"]

    def add_character(self, name: str, initial_minutes: int = 0) -> bool:
        """Add a new storage character/spot"""
        if not name.strip():
            return False

        # Check for duplicate name
        for char in self._data["characters"]:
            if char["name"] == name:
                return False

        self._data["characters"].append({
            "name": name,
            "remaining_minutes": max(0, initial_minutes),
        })
        return True

    def remove_character(self, name: str) -> bool:
        """Remove a storage character"""
        original_len = len(self._data["characters"])
        self._data["characters"] = [
            c for c in self._data["characters"] if c["name"] != name
        ]
        return len(self._data["characters"]) < original_len

    def get_character(self, name: str) -> Optional[Dict]:
        """Get character by name"""
        for char in self._data["characters"]:
            if char["name"] == name:
                return char
        return None

    def add_time(self, name: str, minutes: int) -> bool:
        """Add time to remaining storage"""
        char = self.get_character(name)
        if char is None:
            return False

        char["remaining_minutes"] += minutes
        return True

    def subtract_time(self, name: str, minutes: int) -> bool:
        """Subtract time from remaining storage"""
        char = self.get_character(name)
        if char is None:
            return False

        char["remaining_minutes"] = max(0, char["remaining_minutes"] - minutes)
        return True

    def set_time(self, name: str, minutes: int) -> bool:
        """Directly set remaining time"""
        char = self.get_character(name)
        if char is None:
            return False

        char["remaining_minutes"] = max(0, minutes)
        return True

    def get_total_remaining(self) -> int:
        """Get total remaining minutes across all characters"""
        total = 0
        for char in self._data["characters"]:
            total += char["remaining_minutes"]
        return total

    def get_data_for_saving(self) -> Dict:
        """Get data for saving"""
        return self._data

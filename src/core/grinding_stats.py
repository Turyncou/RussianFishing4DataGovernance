"""Grinding statistics model - business logic for tracking silver grinding"""
from datetime import datetime
from typing import List, Dict, Optional


class GrindingStatsModel:
    """Business logic for grinding statistics tracking"""

    def __init__(self):
        self._data = {
            "characters": [],
            "goal": {
                "target_silver": 0,
                "target_minutes": 0
            }
        }

    def load_from_data(self, data: Dict) -> None:
        """Load from persisted data"""
        self._data = data

    def get_characters(self) -> List[Dict]:
        """Get all characters"""
        return self._data["characters"]

    def add_character(self, name: str) -> bool:
        """Add a new character"""
        if not name.strip():
            return False

        # Check for duplicate name
        for char in self._data["characters"]:
            if char["name"] == name:
                return False

        self._data["characters"].append({
            "name": name,
            "daily_data": {},
            "total_silver": 0,
            "total_minutes": 0,
        })
        return True

    def remove_character(self, name: str) -> bool:
        """Remove a character by name"""
        original_len = len(self._data["characters"])
        self._data["characters"] = [
            c for c in self._data["characters"] if c["name"] != name
        ]
        return len(self._data["characters"]) < original_len

    def get_character(self, name: str) -> Optional[Dict]:
        """Get a character by name"""
        for char in self._data["characters"]:
            if char["name"] == name:
                return char
        return None

    def add_daily_data(self, character_name: str, date: str, silver: int, minutes: int) -> bool:
        """Add or update daily data for a character"""
        char = self.get_character(character_name)
        if char is None:
            return False

        char["daily_data"][date] = {
            "silver": silver,
            "minutes": minutes
        }
        return True

    def update_daily_data(self, character_name: str, date: str, silver: int, minutes: int) -> bool:
        """Update existing daily data"""
        return self.add_daily_data(character_name, date, silver, minutes)

    def clear_today_data(self, character_name: str, date: str) -> bool:
        """Clear today's data (set to zero)"""
        char = self.get_character(character_name)
        if char is None:
            return False
        char["daily_data"][date] = {
            "silver": 0,
            "minutes": 0
        }
        return True

    def calculate_totals(self, character_name: str) -> Dict:
        """Calculate total silver and minutes for a character"""
        char = self.get_character(character_name)
        if char is None:
            return {"total_silver": 0, "total_minutes": 0}

        total_silver = 0
        total_minutes = 0
        for date, data in char["daily_data"].items():
            total_silver += data["silver"]
            total_minutes += data["minutes"]

        char["total_silver"] = total_silver
        char["total_minutes"] = total_minutes
        return {"total_silver": total_silver, "total_minutes": total_minutes}

    def get_today_stats(self, character_name: str) -> Optional[Dict]:
        """Get today's statistics for a character"""
        today = datetime.now().strftime("%Y-%m-%d")
        char = self.get_character(character_name)
        if char is None:
            return None

        if today not in char["daily_data"]:
            return {"silver": 0, "minutes": 0}

        return char["daily_data"][today]

    def set_goal(self, target_silver: int, target_minutes: int) -> None:
        """Set the overall grinding goal"""
        self._data["goal"] = {
            "target_silver": target_silver,
            "target_minutes": target_minutes
        }

    def get_goal(self) -> Dict:
        """Get the current goal"""
        return self._data["goal"]

    def calculate_progress(self) -> Dict:
        """Calculate overall progress across all characters"""
        overall = self.get_overall_total()
        goal = self.get_goal()

        if goal["target_silver"] > 0:
            silver_percent = (overall["total_silver"] / goal["target_silver"]) * 100
        else:
            silver_percent = 0

        if goal["target_minutes"] > 0:
            minutes_percent = (overall["total_minutes"] / goal["target_minutes"]) * 100
        else:
            minutes_percent = 0

        return {
            "silver_total": overall["total_silver"],
            "silver_target": goal["target_silver"],
            "silver_percent": min(silver_percent, 100),
            "minutes_total": overall["total_minutes"],
            "minutes_target": goal["target_minutes"],
            "minutes_percent": min(minutes_percent, 100),
        }

    def calculate_remaining(self) -> Dict:
        """Calculate remaining silver and minutes to goal"""
        overall = self.get_overall_total()
        goal = self.get_goal()

        remaining_silver = max(0, goal["target_silver"] - overall["total_silver"])
        remaining_minutes = max(0, goal["target_minutes"] - overall["total_minutes"])

        return {
            "remaining_silver": remaining_silver,
            "remaining_minutes": remaining_minutes
        }

    def get_overall_total(self) -> Dict:
        """Get overall totals across all characters"""
        total_silver = 0
        total_minutes = 0

        for char in self._data["characters"]:
            # Recalculate to ensure up to date
            char_totals = self.calculate_totals(char["name"])
            total_silver += char_totals["total_silver"]
            total_minutes += char_totals["total_minutes"]

        return {
            "total_silver": total_silver,
            "total_minutes": total_minutes
        }

    def check_and_archive(self, yesterday: str, today: str) -> None:
        """Check and archive - ensure today starts clean if yesterday had data"""
        # If today hasn't been started, just ensure it exists with zero
        for char in self._data["characters"]:
            if today not in char["daily_data"]:
                char["daily_data"][today] = {
                    "silver": 0,
                    "minutes": 0
                }

    def get_data_for_saving(self) -> Dict:
        """Get the full data structure for saving"""
        return self._data

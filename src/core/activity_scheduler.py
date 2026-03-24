"""Activity scheduler integration - wraps the existing activity_scheduler API for the GUI"""
from typing import List, Dict, Optional
from activity_scheduler import (
    ActivityScheduler,
    ActivityType,
    OptimizationResults,
)


class ActivitySchedulerIntegration:
    """Integration layer between GUI and the existing activity scheduler package"""

    def __init__(self):
        self._scheduler = ActivityScheduler()

    def get_activities(self) -> List[Dict]:
        """Get all activities as dicts"""
        activities = self._scheduler.get_activities()
        return [
            {
                "name": a.activity_name,
                "type": "A" if a.type == ActivityType.TYPE_A else "B",
                "duration": a.duration,
                "value": a.value,
            }
            for a in activities
        ]

    def get_user_config(self) -> Optional[Dict]:
        """Get current user config"""
        config = self._scheduler.get_user_config()
        if config is None:
            return None
        return {
            "max_concurrent_b": config.max_concurrent_b,
            "total_available_hours": config.total_available_hours,
        }

    def add_activity(
        self,
        activity_name: str,
        activity_type: str,
        duration: int,
        value: float,
    ) -> bool:
        """Add an activity

        Args:
            activity_name: Activity name
            activity_type: "A" or "B"
            duration: Duration in minutes
            value: Value/gain

        Returns:
            True if added successfully, False otherwise
        """
        try:
            if activity_type == "A":
                type_enum = ActivityType.TYPE_A
            elif activity_type == "B":
                type_enum = ActivityType.TYPE_B
            else:
                raise ValueError(f"Invalid activity type: {activity_type}")

            self._scheduler.add_activity(activity_name, type_enum, duration, value)
            return True
        except Exception:
            return False

    def remove_activity(self, activity_name: str) -> bool:
        """Remove an activity by name"""
        return self._scheduler.remove_activity(activity_name)

    def set_user_config(self, max_concurrent_b: int, total_available_hours: float) -> None:
        """Set user configuration"""
        self._scheduler.update_user_config(max_concurrent_b, total_available_hours)

    def get_recommendations(self) -> OptimizationResults:
        """Get optimization recommendations (max gain and balanced)"""
        return self._scheduler.optimize()

    def load_from_files(self, activities_path: str, config_path: str) -> bool:
        """Load from existing files"""
        try:
            self._scheduler.load_activities_from_file(activities_path)
            self._scheduler.load_config_from_file(config_path)
            return True
        except Exception:
            return False

    def save_to_files(self, activities_path: str, config_path: str) -> bool:
        """Save current state to files"""
        try:
            self._scheduler.save_activities_to_file(activities_path)
            self._scheduler.save_config_to_file(config_path)
            return True
        except Exception:
            return False

    def start_watching(
        self,
        on_change,
        activities_file: Optional[str] = None,
        user_config_file: Optional[str] = None,
        debounce_ms: int = 500,
    ):
        """Start watching for file changes"""
        self._scheduler.start_watching(on_change, activities_file, user_config_file, debounce_ms)

    def stop_watching(self):
        """Stop watching for file changes"""
        self._scheduler.stop_watching()

    def is_watching(self) -> bool:
        """Check if currently watching"""
        return self._scheduler.is_watching()

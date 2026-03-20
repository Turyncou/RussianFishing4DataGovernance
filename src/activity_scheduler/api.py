"""Main API module for activity scheduling optimization.

This module provides the public API for programmatic access to the
activity scheduler functionality. External programs should import
and use the ActivityScheduler class as the main entry point.
"""
from typing import List, Optional
from .types import (
    Activity, ActivityType, UserConfig, ScheduleResult, OptimizationResults
)
from .data_loader import load_activities, load_user_config
from .exceptions import (
    InvalidActivityError, InvalidUserConfigError, NoValidScheduleError
)
from .optimizer import _optimize_for_max_gain, _optimize_for_balanced


class ActivityScheduler:
    """Main API class for activity scheduling optimization.

    Provides programmatic access to add/remove activities, update configuration,
    and get optimization recommendations.

    Example:
        >>> from activity_scheduler import ActivityScheduler, ActivityType
        >>> scheduler = ActivityScheduler()
        >>> scheduler.add_activity("Reading", ActivityType.TYPE_A, 60, 50)
        >>> scheduler.add_activity("Walking", ActivityType.TYPE_B, 60, 30)
        >>> scheduler.update_user_config(max_concurrent_b=2, total_available_hours=8)
        >>> results = scheduler.optimize()
        >>> print(f"Max gain value: {results.maximum_gain.total_value}")
    """

    def __init__(
        self,
        activities_file: Optional[str] = None,
        user_config_file: Optional[str] = None
    ):
        """Initialize the ActivityScheduler, optionally loading from files.

        Args:
            activities_file: Path to CSV file with activities. If provided,
                loads activities from this file, replacing any existing activities.
            user_config_file: Path to JSON file with user configuration. If provided,
                loads configuration from this file, replacing existing config.

        Raises:
            FileNotFoundError: If specified file doesn't exist.
            InvalidActivityError: If activity data is invalid.
            InvalidUserConfigError: If user configuration is invalid.
        """
        self._activities: List[Activity] = []
        self._user_config: Optional[UserConfig] = None

        if activities_file is not None:
            self.load_activities_from_file(activities_file)
        if user_config_file is not None:
            self.load_config_from_file(user_config_file)

    def add_activity(
        self,
        activity_name: str,
        activity_type: ActivityType,
        duration: int,
        value: float
    ) -> Activity:
        """Add a new activity programmatically.

        Args:
            activity_name: Name of the activity.
            activity_type: Type of activity (ActivityType.TYPE_A or TYPE_B).
            duration: Duration in minutes (must be positive).
            value: Value/gain of the activity (must be non-negative).

        Returns:
            The created Activity object.

        Raises:
            InvalidActivityError: If any parameters are invalid.
        """
        # Validate inputs
        if not activity_name.strip():
            raise InvalidActivityError("Activity name cannot be empty")

        if duration <= 0:
            raise InvalidActivityError(
                f"Duration must be positive, got {duration}"
            )

        if value < 0:
            raise InvalidActivityError(
                f"Value cannot be negative, got {value}"
            )

        if not isinstance(activity_type, ActivityType):
            raise InvalidActivityError(
                f"activity_type must be an ActivityType enum, got {type(activity_type)}"
            )

        activity = Activity(
            activity_name=activity_name.strip(),
            type=activity_type,
            duration=duration,
            value=value
        )

        # Check for duplicate name to avoid confusion
        existing = [a for a in self._activities if a.activity_name == activity.activity_name]
        if existing:
            raise InvalidActivityError(
                f"Activity with name '{activity.activity_name}' already exists"
            )

        self._activities.append(activity)
        return activity

    def remove_activity(self, activity_name: str) -> bool:
        """Remove an activity by name.

        Args:
            activity_name: Name of the activity to remove.

        Returns:
            True if the activity was found and removed, False if not found.
        """
        original_count = len(self._activities)
        self._activities = [
            a for a in self._activities
            if a.activity_name != activity_name
        ]
        return len(self._activities) < original_count

    def update_user_config(
        self,
        max_concurrent_b: int,
        total_available_hours: float
    ) -> None:
        """Update user configuration.

        Args:
            max_concurrent_b: Maximum number of concurrent type B activities
                (must be non-negative integer).
            total_available_hours: Total available hours for activities
                (must be positive).

        Raises:
            InvalidUserConfigError: If any parameters are invalid.
        """
        if not isinstance(max_concurrent_b, int) or max_concurrent_b < 0:
            raise InvalidUserConfigError(
                f"'max_concurrent_b' must be a non-negative integer, got {max_concurrent_b}"
            )

        if not isinstance(total_available_hours, (int, float)) or total_available_hours <= 0:
            raise InvalidUserConfigError(
                f"'total_available_hours' must be a positive number, got {total_available_hours}"
            )

        self._user_config = UserConfig(
            max_concurrent_b=max_concurrent_b,
            total_available_hours=float(total_available_hours)
        )

    def get_activities(self) -> List[Activity]:
        """Get all current activities.

        Returns:
            List of Activity objects (copy to prevent external modification).
        """
        return list(self._activities)

    def get_user_config(self) -> Optional[UserConfig]:
        """Get current user configuration.

        Returns:
            Current UserConfig or None if not set.
        """
        return self._user_config

    def optimize(self) -> OptimizationResults:
        """Run optimization and return results (max gain + balanced).

        Returns:
            OptimizationResults containing both maximum gain and balanced schedules.

        Raises:
            InvalidUserConfigError: If user configuration not set.
            NoValidScheduleError: If no valid schedule can be created.
        """
        if self._user_config is None:
            raise InvalidUserConfigError("User configuration not set")

        if not self._activities:
            raise NoValidScheduleError("No activities available for scheduling")

        total_available_minutes = int(self._user_config.total_available_hours * 60)

        # Run both optimizations
        max_gain = _optimize_for_max_gain(
            self._activities,
            self._user_config,
            total_available_minutes
        )
        balanced = _optimize_for_balanced(
            self._activities,
            self._user_config,
            total_available_minutes
        )

        return OptimizationResults(
            maximum_gain=max_gain,
            balanced=balanced
        )

    def load_activities_from_file(self, file_path: str) -> None:
        """Load activities from CSV file, replacing existing activities.

        The CSV must have columns: activity_name, type, duration, value

        Args:
            file_path: Path to the CSV file.

        Raises:
            FileNotFoundError: If file doesn't exist.
            InvalidActivityError: If activity data is invalid.
        """
        activities = load_activities(file_path)
        self._activities = activities

    def load_config_from_file(self, file_path: str) -> None:
        """Load user config from JSON file, replacing existing config.

        The JSON must have keys: max_concurrent_b, total_available_hours

        Args:
            file_path: Path to the JSON file.

        Raises:
            FileNotFoundError: If file doesn't exist.
            InvalidUserConfigError: If configuration is invalid.
        """
        config = load_user_config(file_path)
        self._user_config = config

    def save_activities_to_file(self, file_path: str) -> None:
        """Save current activities to CSV file.

        Args:
            file_path: Path where to save the CSV file.
        """
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvfile.write("activity_name,type,duration,value\n")
            for activity in self._activities:
                type_str = "typeA" if activity.type == ActivityType.TYPE_A else "typeB"
                csvfile.write(f"{activity.activity_name},{type_str},{activity.duration},{activity.value}\n")

    def save_config_to_file(self, file_path: str) -> None:
        """Save current user config to JSON file.

        Args:
            file_path: Path where to save the JSON file.

        Raises:
            InvalidUserConfigError: If user configuration not set.
        """
        if self._user_config is None:
            raise InvalidUserConfigError("User configuration not set")

        import json
        data = {
            "max_concurrent_b": self._user_config.max_concurrent_b,
            "total_available_hours": self._user_config.total_available_hours
        }
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2)

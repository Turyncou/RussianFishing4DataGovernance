"""Module for loading activity and user configuration data"""
import csv
import json
import os
from typing import List
from .types import Activity, ActivityType, UserConfig
from .exceptions import InvalidActivityError, InvalidUserConfigError


def load_activities(file_path: str) -> List[Activity]:
    """
    Load activities from a CSV file.

    Args:
        file_path: Path to the CSV file containing activities

    Returns:
        List of Activity objects

    Raises:
        FileNotFoundError: If the file doesn't exist
        InvalidActivityError: If activity data is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Activity file not found: {file_path}")

    activities = []

    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for row_num, row in enumerate(reader, start=2):  # row numbers start after header
            try:
                # Parse activity type
                type_str = row['type'].strip()
                if type_str == 'typeA':
                    activity_type = ActivityType.TYPE_A
                elif type_str == 'typeB':
                    activity_type = ActivityType.TYPE_B
                else:
                    raise InvalidActivityError(
                        f"Invalid activity type '{type_str}' in row {row_num}"
                    )

                # Parse duration
                duration = int(row['duration'].strip())
                if duration <= 0:
                    raise InvalidActivityError(
                        f"Duration must be positive in row {row_num}, got {duration}"
                    )

                # Parse value
                value = float(row['value'].strip())
                if value < 0:
                    raise InvalidActivityError(
                        f"Value cannot be negative in row {row_num}, got {value}"
                    )

                activity = Activity(
                    activity_name=row['activity_name'].strip(),
                    type=activity_type,
                    duration=duration,
                    value=value
                )
                activities.append(activity)

            except (ValueError, KeyError) as e:
                raise InvalidActivityError(f"Error parsing row {row_num}: {str(e)}")

    if not activities:
        raise InvalidActivityError("No valid activities found in the file")

    return activities


def load_user_config(file_path: str) -> UserConfig:
    """
    Load user configuration from a JSON file.

    Args:
        file_path: Path to the JSON file containing user configuration

    Returns:
        UserConfig object

    Raises:
        FileNotFoundError: If the file doesn't exist
        InvalidUserConfigError: If configuration data is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"User config file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as jsonfile:
        try:
            data = json.load(jsonfile)
        except json.JSONDecodeError as e:
            raise InvalidUserConfigError(f"Invalid JSON: {str(e)}")

    # Validate and extract max_concurrent_b
    if 'max_concurrent_b' not in data:
        raise InvalidUserConfigError("Missing 'max_concurrent_b' in config")

    max_concurrent_b = data['max_concurrent_b']
    if not isinstance(max_concurrent_b, int) or max_concurrent_b < 0:
        raise InvalidUserConfigError(
            f"'max_concurrent_b' must be a non-negative integer, got {max_concurrent_b}"
        )

    # Validate and extract total_available_hours
    if 'total_available_hours' not in data:
        raise InvalidUserConfigError("Missing 'total_available_hours' in config")

    total_available_hours = data['total_available_hours']
    if not isinstance(total_available_hours, (int, float)) or total_available_hours <= 0:
        raise InvalidUserConfigError(
            f"'total_available_hours' must be a positive number, got {total_available_hours}"
        )

    return UserConfig(
        max_concurrent_b=max_concurrent_b,
        total_available_hours=float(total_available_hours)
    )
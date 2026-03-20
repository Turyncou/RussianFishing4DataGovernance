"""Activity scheduling optimization module"""
import os
from typing import List, Dict, Any
from .types import (
    Activity, ActivityType, UserConfig, ScheduleItem,
    ScheduleResult, OptimizationResults
)
from .data_loader import load_activities, load_user_config
from .exceptions import NoValidScheduleError


def optimize_schedule(activities_file: str, user_config_file: str) -> OptimizationResults:
    """
    Optimize activity scheduling using the provided CSV and user config files.

    Args:
        activities_file: Path to CSV file with activities
        user_config_file: Path to JSON file with user configuration

    Returns:
        OptimizationResults containing maximum gain and balanced schedules

    Raises:
        NoValidScheduleError: If no valid schedule can be created
    """
    # Load data
    activities = load_activities(activities_file)
    user_config = load_user_config(user_config_file)

    total_available_minutes = int(user_config.total_available_hours * 60)

    # Run optimizations
    max_gain = _optimize_for_max_gain(activities, user_config, total_available_minutes)
    balanced = _optimize_for_balanced(activities, user_config, total_available_minutes)

    return OptimizationResults(
        maximum_gain=max_gain,
        balanced=balanced
    )


def _optimize_for_max_gain(activities: List[Activity], config: UserConfig, available_minutes: int) -> ScheduleResult:
    """
    Optimize schedule for maximum gain.

    Args:
        activities: List of available activities
        config: User configuration
        available_minutes: Total available minutes

    Returns:
        ScheduleResult with maximum possible gain
    """
    # Separate activities by type
    type_a_activities = [a for a in activities if a.type == ActivityType.TYPE_A]
    type_b_activities = [a for a in activities if a.type == ActivityType.TYPE_B]

    schedule = []
    current_time = 0
    total_value = 0.0
    total_overhead = 0
    last_activity_type = None

    # First, select type A activities (higher value per hour)
    type_a_activities.sort(key=lambda x: x.value / x.duration, reverse=True)

    # Add type A activities
    for activity in type_a_activities:
        if current_time + activity.duration <= available_minutes:
            # Add switching overhead
            if last_activity_type and last_activity_type != ActivityType.TYPE_A:
                overhead = 15  # use minimum overhead for maximum gain
                current_time += overhead
                total_overhead += overhead
                if current_time > available_minutes:
                    break

            schedule.append(ScheduleItem(
                activity=activity,
                start_time=current_time,
                end_time=current_time + activity.duration,
                concurrent_b_count=0
            ))

            total_value += activity.value
            current_time += activity.duration
            last_activity_type = ActivityType.TYPE_A

    # Then, fill remaining time with type B activities
    type_b_activities.sort(key=lambda x: x.value / x.duration, reverse=True)

    for activity in type_b_activities:
        # Calculate how many times we can repeat this activity
        while current_time + activity.duration <= available_minutes:
            # Add switching overhead
            if last_activity_type and last_activity_type != ActivityType.TYPE_B:
                overhead = 15
                current_time += overhead
                total_overhead += overhead
                if current_time > available_minutes:
                    break

            schedule.append(ScheduleItem(
                activity=activity,
                start_time=current_time,
                end_time=current_time + activity.duration,
                concurrent_b_count=1  # start with 1 concurrent
            ))

            total_value += activity.value
            current_time += activity.duration
            last_activity_type = ActivityType.TYPE_B

    # Calculate rest time
    rest_time = available_minutes - current_time

    if not schedule:
        raise NoValidScheduleError("No activities can be scheduled within available time")

    return ScheduleResult(
        schedule=schedule,
        total_value=total_value,
        total_duration=current_time,
        rest_time=rest_time,
        details={
            "optimization_type": "maximum_gain",
            "total_overhead": total_overhead,
            "num_activities": len(schedule),
            "activities": [item.activity.activity_name for item in schedule]
        }
    )


def _optimize_for_balanced(activities: List[Activity], config: UserConfig, available_minutes: int) -> ScheduleResult:
    """
    Optimize schedule for balanced gain and rest.

    Args:
        activities: List of available activities
        config: User configuration
        available_minutes: Total available minutes

    Returns:
        ScheduleResult with balanced value and rest
    """
    # Separate activities by type
    type_a_activities = [a for a in activities if a.type == ActivityType.TYPE_A]
    type_b_activities = [a for a in activities if a.type == ActivityType.TYPE_B]

    schedule = []
    current_time = 0
    total_value = 0.0
    total_overhead = 0
    last_activity_type = None

    # Select type A activities (moderate value)
    type_a_activities.sort(key=lambda x: x.value / x.duration, reverse=True)
    selected_type_a = type_a_activities[:1]  # pick top 1 type A

    for activity in selected_type_a:
        if current_time + activity.duration <= available_minutes * 0.6:  # limit to 60% of time for type A
            if last_activity_type:
                overhead = 18  # medium overhead
                current_time += overhead
                total_overhead += overhead

            schedule.append(ScheduleItem(
                activity=activity,
                start_time=current_time,
                end_time=current_time + activity.duration,
                concurrent_b_count=0
            ))

            total_value += activity.value
            current_time += activity.duration
            last_activity_type = ActivityType.TYPE_A

    # Add type B activities (varying types for balance)
    type_b_activities.sort(key=lambda x: x.value / x.duration, reverse=True)
    selected_type_b = type_b_activities[:2]  # pick top 2 type B

    for activity in selected_type_b:
        if current_time + activity.duration <= available_minutes * 0.8:
            if last_activity_type and last_activity_type != ActivityType.TYPE_B:
                overhead = 18
                current_time += overhead
                total_overhead += overhead

            schedule.append(ScheduleItem(
                activity=activity,
                start_time=current_time,
                end_time=current_time + activity.duration,
                concurrent_b_count=1
            ))

            total_value += activity.value
            current_time += activity.duration
            last_activity_type = ActivityType.TYPE_B

    # Calculate rest time
    rest_time = available_minutes - current_time

    if not schedule:
        raise NoValidScheduleError("No balanced activities can be scheduled within available time")

    return ScheduleResult(
        schedule=schedule,
        total_value=total_value,
        total_duration=current_time,
        rest_time=rest_time,
        details={
            "optimization_type": "balanced",
            "total_overhead": total_overhead,
            "num_activities": len(schedule),
            "activities": [item.activity.activity_name for item in schedule],
            "balance_score": total_value + rest_time / 60  # combine value and rest
        }
    )
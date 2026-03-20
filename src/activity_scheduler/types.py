from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any


class ActivityType(Enum):
    TYPE_A = "typeA"
    TYPE_B = "typeB"


@dataclass
class Activity:
    """Represents a single activity with its properties"""
    activity_name: str
    type: ActivityType
    duration: int  # in minutes
    value: float  # value/benefit


@dataclass
class UserConfig:
    """Represents user configuration settings"""
    max_concurrent_b: int  # maximum number of concurrent type B activities
    total_available_hours: float  # total available hours for activities


@dataclass
class ScheduleItem:
    """Represents an item in the schedule with start/end time and activity"""
    activity: Activity
    start_time: int  # in minutes from start
    end_time: int  # in minutes from start
    concurrent_b_count: int  # number of concurrent B activities during this item


@dataclass
class ScheduleResult:
    """Represents the result of a scheduling optimization"""
    schedule: List[ScheduleItem]
    total_value: float
    total_duration: int  # in minutes
    rest_time: int  # in minutes
    details: Dict[str, Any]  # additional details about the schedule


@dataclass
class OptimizationResults:
    """Represents all optimization results"""
    maximum_gain: ScheduleResult
    balanced: ScheduleResult
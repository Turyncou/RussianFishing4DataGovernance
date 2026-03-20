"""Activity Scheduling Optimization Package.

A Python package for optimal daily activity scheduling based on activity types,
value/gain, and user constraints. Provides two optimization strategies:
maximum gain and balanced (gain + rest).

Usage:
    >>> from activity_scheduler import ActivityScheduler, ActivityType
    >>> scheduler = ActivityScheduler()
    >>> scheduler.add_activity("Reading", ActivityType.TYPE_A, 60, 50)
    >>> scheduler.update_user_config(max_concurrent_b=2, total_available_hours=8)
    >>> results = scheduler.optimize()
"""

from .api import ActivityScheduler
from .types import (
    Activity,
    ActivityType,
    UserConfig,
    ScheduleItem,
    ScheduleResult,
    OptimizationResults,
)
from .exceptions import (
    ActivitySchedulerError,
    InvalidActivityError,
    InvalidUserConfigError,
    NoValidScheduleError,
)

__all__ = [
    # Main API class
    "ActivityScheduler",
    # Types
    "Activity",
    "ActivityType",
    "UserConfig",
    "ScheduleItem",
    "ScheduleResult",
    "OptimizationResults",
    # Exceptions
    "ActivitySchedulerError",
    "InvalidActivityError",
    "InvalidUserConfigError",
    "NoValidScheduleError",
]

__version__ = "0.1.0"

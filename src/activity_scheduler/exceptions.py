class ActivitySchedulerError(Exception):
    """Base exception for activity scheduler errors"""
    pass


class InvalidActivityError(ActivitySchedulerError):
    """Raised when an activity is invalid"""
    pass


class InvalidUserConfigError(ActivitySchedulerError):
    """Raised when user configuration is invalid"""
    pass


class NoValidScheduleError(ActivitySchedulerError):
    """Raised when no valid schedule can be created"""
    pass
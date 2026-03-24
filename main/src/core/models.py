"""Data models for the application"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional


class ActivityType(Enum):
    """Activity type enum"""
    GRINDING = "grinding"  # 搬砖
    STAR_WAITING = "star_waiting"  # 蹲星


@dataclass
class LotteryPrize:
    """Represents a prize in the wheel of fortune lottery"""
    name: str
    probability: float  # Percentage 0-100
    color: str = "#cccccc"

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Prize name cannot be empty")
        if self.probability < 0 or self.probability > 100:
            raise ValueError("Probability must be between 0 and 100")


@dataclass
class ActivityRecord:
    """Represents a single activity record for a specific day"""
    date: date
    activity_type: ActivityType
    duration_minutes: int  # Duration in minutes
    # For grinding: silver_count = silver, duration_minutes = duration
    # For star waiting: success_count = number of successful star fish, duration_minutes = duration
    silver_count: int = 0  # Number of silver coins (grinding)
    success_count: int = 0  # Number of successful star fish (star waiting)

    def __post_init__(self):
        if self.silver_count < 0:
            raise ValueError("Silver count cannot be negative")
        if self.success_count < 0:
            raise ValueError("Success count cannot be negative")
        if self.duration_minutes < 0:
            raise ValueError("Duration cannot be negative")


@dataclass
class ActivityGoal:
    """Represents a goal for an activity"""
    activity_type: ActivityType
    target_value: int  # target silver (grinding) or target success count (star waiting)
    target_duration: int  # In minutes
    total_income: int = 0  # Total income when goal is complete

    def __post_init__(self):
        if self.target_value < 0:
            raise ValueError("Target value cannot be negative")
        if self.target_duration < 0:
            raise ValueError("Target duration cannot be negative")
        if self.total_income < 0:
            raise ValueError("Total income cannot be negative")


@dataclass
class SuggestionUserSettings:
    """User settings for activity suggestion"""
    daily_total_hours: float = 8.0  # Total available hours per day
    grinding_concurrent: int = 1  # How many grinding activities can be done concurrently
    star_waiting_concurrent: int = 1  # How many star waiting activities can be done concurrently
    switch_minutes: int = 20  # Time needed to switch between activities in minutes


@dataclass
class ActivitySuggestion:
    """Represents a suggestion for activity arrangement"""
    daily_grinding_minutes: float
    daily_star_waiting_minutes: float
    estimated_days_remaining: float
    estimated_total_income: float
    recommendation: str


@dataclass
class ActivityCharacter:
    """Represents a character with activity statistics"""
    name: str
    records: List[ActivityRecord] = field(default_factory=list)
    grinding_goal: Optional[ActivityGoal] = None
    star_waiting_goal: Optional[ActivityGoal] = None
    suggestion_settings: SuggestionUserSettings = field(default_factory=SuggestionUserSettings)

    def add_record(self, record: ActivityRecord) -> None:
        """Add an activity record"""
        self.records.append(record)

    def calculate_totals(self, activity_type: ActivityType) -> tuple[int, int, int]:
        """Calculate total value (silver/success count) and duration across all records"""
        total_value = 0
        total_duration = 0
        for r in self.records:
            if r.activity_type == activity_type:
                if activity_type == ActivityType.GRINDING:
                    total_value += r.silver_count
                else:
                    total_value += r.success_count
                total_duration += r.duration_minutes
        remaining_value = 0
        if activity_type == ActivityType.GRINDING and self.grinding_goal:
            remaining_value = self.grinding_goal.target_value - total_value
            remaining_value = max(0, remaining_value)
        elif activity_type == ActivityType.STAR_WAITING and self.star_waiting_goal:
            remaining_value = self.star_waiting_goal.target_value - total_value
            remaining_value = max(0, remaining_value)
        return total_value, total_duration, remaining_value

    def calculate_today_totals(self, activity_type: ActivityType) -> tuple[int, int]:
        """Calculate today's value and duration"""
        today = date.today()
        today_value = 0
        today_duration = 0
        for r in self.records:
            if r.date == today and r.activity_type == activity_type:
                if activity_type == ActivityType.GRINDING:
                    today_value += r.silver_count
                else:
                    today_value += r.success_count
                today_duration += r.duration_minutes
        return today_value, today_duration

    def calculate_progress(self, activity_type: ActivityType) -> tuple[Optional[float], Optional[float]]:
        """Calculate progress towards goal as percentage 0-1"""
        total_value, total_duration, _ = self.calculate_totals(activity_type)
        goal = self.grinding_goal if activity_type == ActivityType.GRINDING else self.star_waiting_goal
        if goal is None:
            return None, None
        progress_value = total_value / goal.target_value if goal.target_value > 0 else 1.0
        progress_duration = total_duration / goal.target_duration if goal.target_duration > 0 else 1.0
        return min(progress_value, 1.0), min(progress_duration, 1.0)

    def get_remaining_income(self) -> int:
        """Get remaining income based on progress"""
        total_remaining = 0
        # For grinding
        if self.grinding_goal:
            total_value, _, _ = self.calculate_totals(ActivityType.GRINDING)
            if self.grinding_goal.target_value > 0:
                progress = total_value / self.grinding_goal.target_value
                remaining_ratio = 1.0 - min(progress, 1.0)
                total_remaining += int(self.grinding_goal.total_income * remaining_ratio)
        # For star waiting
        if self.star_waiting_goal:
            total_value, _, _ = self.calculate_totals(ActivityType.STAR_WAITING)
            if self.star_waiting_goal.target_value > 0:
                progress = total_value / self.star_waiting_goal.target_value
                remaining_ratio = 1.0 - min(progress, 1.0)
                total_remaining += int(self.star_waiting_goal.total_income * remaining_ratio)
        return total_remaining


@dataclass
class StorageCharacter:
    """Represents a character with stored duration"""
    name: str
    remaining_minutes: int

    def __post_init__(self):
        if self.remaining_minutes < 0:
            self.remaining_minutes = 0

    def add_minutes(self, minutes: int) -> None:
        """Add minutes to remaining time"""
        self.remaining_minutes += minutes

    def remove_minutes(self, minutes: int) -> None:
        """Remove minutes from remaining time, not below zero"""
        self.remaining_minutes = max(0, self.remaining_minutes - minutes)


@dataclass
class FriendLink:
    """Represents a friend link"""
    text: str
    url: str

    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("Link text cannot be empty")
        if not self.url.strip():
            raise ValueError("URL cannot be empty")


@dataclass
class BackgroundConfig:
    """Configuration for background image"""
    image_path: Optional[str] = None
    opacity: float = 1.0

    def __post_init__(self):
        self.opacity = max(0.0, min(1.0, self.opacity))


@dataclass
class AccountCredential:
    """Represents a stored account credential (username/password)"""
    account_name: str    # Account display name/username
    encrypted_password: str  # Encrypted password (base64 encoded for simple encryption)

    def __post_init__(self):
        if not self.account_name.strip():
            raise ValueError("Account name cannot be empty")
        if not self.encrypted_password.strip():
            raise ValueError("Password cannot be empty")


@dataclass
class BaitConsumption:
    """Represents a bait/tackle item with stock tracking"""
    name: str           # Bait/Tackle name
    total_bought: int   # Total quantity bought
    total_used: int     # Total quantity used

    @property
    def remaining(self) -> int:
        """Remaining quantity"""
        return max(0, self.total_bought - self.total_used)

    @property
    def usage_per_day_estimate(self) -> float:
        """Estimated usage per day based on history (not stored, calculated when needed)"""
        # This can be calculated from usage records if we add that later
        return 0

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Bait name cannot be empty")
        if self.total_bought < 0:
            raise ValueError("Total bought cannot be negative")
        if self.total_used < 0:
            raise ValueError("Total used cannot be negative")

    def add_stock(self, quantity: int) -> None:
        """Add more stock"""
        self.total_bought += quantity

    def use_stock(self, quantity: int) -> None:
        """Use some stock, cannot go below zero"""
        self.total_used = min(self.total_bought, self.total_used + quantity)

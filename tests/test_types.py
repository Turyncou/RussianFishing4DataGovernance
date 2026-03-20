import pytest
from src.activity_scheduler.types import (
    Activity, ActivityType, UserConfig, ScheduleItem,
    ScheduleResult, OptimizationResults
)
from src.activity_scheduler.exceptions import InvalidActivityError


class TestActivity:
    """Tests for Activity dataclass"""

    def test_create_activity_type_a(self):
        """Test creating a valid Type A activity"""
        activity = Activity(
            activity_name="Reading",
            type=ActivityType.TYPE_A,
            duration=60,
            value=50.0
        )
        assert activity.activity_name == "Reading"
        assert activity.type == ActivityType.TYPE_A
        assert activity.duration == 60
        assert activity.value == 50.0

    def test_create_activity_type_b(self):
        """Test creating a valid Type B activity"""
        activity = Activity(
            activity_name="Walking",
            type=ActivityType.TYPE_B,
            duration=30,
            value=25.0
        )
        assert activity.activity_name == "Walking"
        assert activity.type == ActivityType.TYPE_B
        assert activity.duration == 30
        assert activity.value == 25.0

    def test_activity_equality(self):
        """Test that two activities with same properties are equal"""
        activity1 = Activity("Reading", ActivityType.TYPE_A, 60, 50.0)
        activity2 = Activity("Reading", ActivityType.TYPE_A, 60, 50.0)
        assert activity1 == activity2

    def test_activity_inequality(self):
        """Test that different activities are not equal"""
        activity1 = Activity("Reading", ActivityType.TYPE_A, 60, 50.0)
        activity2 = Activity("Programming", ActivityType.TYPE_A, 120, 100.0)
        assert activity1 != activity2


class TestUserConfig:
    """Tests for UserConfig dataclass"""

    def test_create_user_config(self):
        """Test creating a valid user configuration"""
        config = UserConfig(
            max_concurrent_b=2,
            total_available_hours=8.0
        )
        assert config.max_concurrent_b == 2
        assert config.total_available_hours == 8.0

    def test_user_config_equality(self):
        """Test that two user configs with same properties are equal"""
        config1 = UserConfig(2, 8.0)
        config2 = UserConfig(2, 8.0)
        assert config1 == config2


class TestScheduleItem:
    """Tests for ScheduleItem dataclass"""

    def test_create_schedule_item(self):
        """Test creating a valid schedule item"""
        activity = Activity("Reading", ActivityType.TYPE_A, 60, 50.0)
        item = ScheduleItem(
            activity=activity,
            start_time=0,
            end_time=60,
            concurrent_b_count=0
        )
        assert item.activity == activity
        assert item.start_time == 0
        assert item.end_time == 60
        assert item.concurrent_b_count == 0
        assert item.end_time - item.start_time == activity.duration


class TestScheduleResult:
    """Tests for ScheduleResult dataclass"""

    def test_create_schedule_result(self):
        """Test creating a valid schedule result"""
        activity = Activity("Reading", ActivityType.TYPE_A, 60, 50.0)
        item = ScheduleItem(activity, 0, 60, 0)
        result = ScheduleResult(
            schedule=[item],
            total_value=50.0,
            total_duration=60,
            rest_time=0,
            details={"optimization_type": "test"}
        )
        assert len(result.schedule) == 1
        assert result.total_value == 50.0
        assert result.total_duration == 60
        assert result.rest_time == 0
        assert result.details == {"optimization_type": "test"}


class TestOptimizationResults:
    """Tests for OptimizationResults dataclass"""

    def test_create_optimization_results(self):
        """Test creating optimization results with both schedule types"""
        activity = Activity("Reading", ActivityType.TYPE_A, 60, 50.0)
        item = ScheduleItem(activity, 0, 60, 0)

        max_gain = ScheduleResult([item], 50.0, 60, 0, {"type": "max_gain"})
        balanced = ScheduleResult([item], 40.0, 60, 15, {"type": "balanced"})

        results = OptimizationResults(
            maximum_gain=max_gain,
            balanced=balanced
        )

        assert results.maximum_gain == max_gain
        assert results.balanced == balanced
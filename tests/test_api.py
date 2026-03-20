"""Tests for the ActivityScheduler public API"""
import pytest
import os
import tempfile
from activity_scheduler import (
    ActivityScheduler,
    ActivityType,
    InvalidActivityError,
    InvalidUserConfigError,
    NoValidScheduleError,
)


class TestActivitySchedulerAPI:
    """Tests for the ActivityScheduler API class"""

    def test_create_empty_scheduler(self):
        """Test creating an empty scheduler"""
        scheduler = ActivityScheduler()
        assert len(scheduler.get_activities()) == 0
        assert scheduler.get_user_config() is None

    def test_create_with_files(self):
        """Test creating scheduler by loading from existing files"""
        base_dir = os.path.dirname(__file__)
        activities_file = os.path.join(base_dir, "..", "data", "activities.csv")
        user_config_file = os.path.join(base_dir, "..", "data", "user.json")

        scheduler = ActivityScheduler(activities_file, user_config_file)
        assert len(scheduler.get_activities()) == 9
        config = scheduler.get_user_config()
        assert config is not None
        assert config.max_concurrent_b == 2
        assert config.total_available_hours == 8

    def test_add_activity(self):
        """Test adding an activity programmatically"""
        scheduler = ActivityScheduler()
        activity = scheduler.add_activity("Test", ActivityType.TYPE_A, 60, 50.0)

        assert activity.activity_name == "Test"
        assert activity.type == ActivityType.TYPE_A
        assert activity.duration == 60
        assert activity.value == 50.0

        activities = scheduler.get_activities()
        assert len(activities) == 1
        assert activities[0] == activity

    def test_add_duplicate_activity_name_raises(self):
        """Test adding duplicate activity name raises error"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("Test", ActivityType.TYPE_A, 60, 50.0)

        with pytest.raises(InvalidActivityError):
            scheduler.add_activity("Test", ActivityType.TYPE_B, 30, 20.0)

    def test_add_activity_invalid_duration(self):
        """Test adding activity with zero/negative duration raises error"""
        scheduler = ActivityScheduler()

        with pytest.raises(InvalidActivityError):
            scheduler.add_activity("Test", ActivityType.TYPE_A, 0, 50.0)

        with pytest.raises(InvalidActivityError):
            scheduler.add_activity("Test", ActivityType.TYPE_A, -10, 50.0)

    def test_add_activity_negative_value(self):
        """Test adding activity with negative value raises error"""
        scheduler = ActivityScheduler()

        with pytest.raises(InvalidActivityError):
            scheduler.add_activity("Test", ActivityType.TYPE_A, 60, -10.0)

    def test_add_activity_empty_name(self):
        """Test adding activity with empty name raises error"""
        scheduler = ActivityScheduler()

        with pytest.raises(InvalidActivityError):
            scheduler.add_activity("", ActivityType.TYPE_A, 60, 50.0)

        with pytest.raises(InvalidActivityError):
            scheduler.add_activity("   ", ActivityType.TYPE_A, 60, 50.0)

    def test_remove_activity(self):
        """Test removing an activity"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("TestA", ActivityType.TYPE_A, 60, 50.0)
        scheduler.add_activity("TestB", ActivityType.TYPE_B, 30, 20.0)

        assert len(scheduler.get_activities()) == 2

        # Remove existing activity
        result = scheduler.remove_activity("TestA")
        assert result is True
        assert len(scheduler.get_activities()) == 1
        assert scheduler.get_activities()[0].activity_name == "TestB"

        # Remove non-existent activity
        result = scheduler.remove_activity("DoesNotExist")
        assert result is False
        assert len(scheduler.get_activities()) == 1

    def test_update_user_config(self):
        """Test updating user configuration"""
        scheduler = ActivityScheduler()
        scheduler.update_user_config(max_concurrent_b=3, total_available_hours=10.0)

        config = scheduler.get_user_config()
        assert config is not None
        assert config.max_concurrent_b == 3
        assert config.total_available_hours == 10.0

        # Update again
        scheduler.update_user_config(max_concurrent_b=1, total_available_hours=4.5)
        assert scheduler.get_user_config().max_concurrent_b == 1
        assert scheduler.get_user_config().total_available_hours == 4.5

    def test_update_user_config_invalid_max_concurrent_b(self):
        """Test updating user config with invalid max_concurrent_b"""
        scheduler = ActivityScheduler()

        with pytest.raises(InvalidUserConfigError):
            scheduler.update_user_config(max_concurrent_b=-1, total_available_hours=8.0)

        with pytest.raises(InvalidUserConfigError):
            scheduler.update_user_config(max_concurrent_b=2.5, total_available_hours=8.0)

    def test_update_user_config_invalid_total_hours(self):
        """Test updating user config with invalid total_available_hours"""
        scheduler = ActivityScheduler()

        with pytest.raises(InvalidUserConfigError):
            scheduler.update_user_config(max_concurrent_b=2, total_available_hours=0)

        with pytest.raises(InvalidUserConfigError):
            scheduler.update_user_config(max_concurrent_b=2, total_available_hours=-4.0)

    def test_optimize_without_config_raises(self):
        """Test optimize called without setting config raises error"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("Test", ActivityType.TYPE_A, 60, 50.0)

        with pytest.raises(InvalidUserConfigError):
            scheduler.optimize()

    def test_optimize_without_activities_raises(self):
        """Test optimize called without activities raises error"""
        scheduler = ActivityScheduler()
        scheduler.update_user_config(max_concurrent_b=2, total_available_hours=8.0)

        with pytest.raises(NoValidScheduleError):
            scheduler.optimize()

    def test_optimize_returns_both_results(self):
        """Test optimize returns both maximum gain and balanced results"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("A1", ActivityType.TYPE_A, 120, 100)
        scheduler.add_activity("B1", ActivityType.TYPE_B, 60, 30)
        scheduler.add_activity("B2", ActivityType.TYPE_B, 45, 40)
        scheduler.update_user_config(max_concurrent_b=2, total_available_hours=4.0)

        results = scheduler.optimize()

        assert results.maximum_gain is not None
        assert results.balanced is not None
        assert len(results.maximum_gain.schedule) > 0
        assert len(results.balanced.schedule) > 0
        assert results.maximum_gain.total_value > 0
        assert results.balanced.total_value > 0
        assert results.maximum_gain.total_duration <= 4 * 60  # 4 hours in minutes
        assert results.balanced.total_duration <= 4 * 60

    def test_max_gain_higher_value_than_balanced(self):
        """Test maximum gain result has higher total value than balanced"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("Programming", ActivityType.TYPE_A, 120, 100)
        scheduler.add_activity("Reading", ActivityType.TYPE_A, 60, 50)
        scheduler.add_activity("Walking", ActivityType.TYPE_B, 60, 30)
        scheduler.add_activity("Yoga", ActivityType.TYPE_B, 45, 40)
        scheduler.update_user_config(max_concurrent_b=2, total_available_hours=8.0)

        results = scheduler.optimize()

        assert results.maximum_gain.total_value >= results.balanced.total_value

    def test_balanced_has_more_rest_than_max_gain(self):
        """Test balanced result has more rest time than maximum gain"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("Programming", ActivityType.TYPE_A, 120, 100)
        scheduler.add_activity("Reading", ActivityType.TYPE_A, 60, 50)
        scheduler.add_activity("Walking", ActivityType.TYPE_B, 60, 30)
        scheduler.update_user_config(max_concurrent_b=2, total_available_hours=8.0)

        results = scheduler.optimize()

        assert results.balanced.rest_time >= results.maximum_gain.rest_time

    def test_load_save_activities_roundtrip(self):
        """Test loading and saving activities round-trip works"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("TestA", ActivityType.TYPE_A, 60, 50.0)
        scheduler.add_activity("TestB", ActivityType.TYPE_B, 30, 20.5)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name

        try:
            scheduler.save_activities_to_file(temp_file)

            # Load into new scheduler
            scheduler2 = ActivityScheduler()
            scheduler2.load_activities_from_file(temp_file)

            activities = scheduler2.get_activities()
            assert len(activities) == 2

            names = {a.activity_name for a in activities}
            assert "TestA" in names
            assert "TestB" in names

            # Verify values
            for a in activities:
                if a.activity_name == "TestA":
                    assert a.type == ActivityType.TYPE_A
                    assert a.duration == 60
                    assert a.value == 50.0
                else:
                    assert a.type == ActivityType.TYPE_B
                    assert a.duration == 30
                    assert a.value == 20.5
        finally:
            os.unlink(temp_file)

    def test_load_save_config_roundtrip(self):
        """Test loading and saving user config round-trip works"""
        scheduler = ActivityScheduler()
        scheduler.update_user_config(max_concurrent_b=3, total_available_hours=12.5)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            scheduler.save_config_to_file(temp_file)

            # Load into new scheduler
            scheduler2 = ActivityScheduler()
            scheduler2.load_config_from_file(temp_file)

            config = scheduler2.get_user_config()
            assert config.max_concurrent_b == 3
            assert config.total_available_hours == 12.5
        finally:
            os.unlink(temp_file)

    def test_save_config_without_config_raises(self):
        """Test saving config when no config set raises error"""
        scheduler = ActivityScheduler()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            with pytest.raises(InvalidUserConfigError):
                scheduler.save_config_to_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_get_activities_returns_copy(self):
        """Test get_activities returns a copy so external changes don't affect internal state"""
        scheduler = ActivityScheduler()
        scheduler.add_activity("Test", ActivityType.TYPE_A, 60, 50.0)

        activities = scheduler.get_activities()
        assert len(activities) == 1

        # Try to modify the returned list
        activities.clear()

        # Internal state should still have the activity
        assert len(scheduler.get_activities()) == 1

    def test_full_api_workflow(self):
        """End-to-end test of complete API workflow"""
        # 1. Create empty scheduler
        scheduler = ActivityScheduler()

        # 2. Add activities
        scheduler.add_activity("DeepWork", ActivityType.TYPE_A, 120, 120)
        scheduler.add_activity("LightTask", ActivityType.TYPE_B, 45, 40)
        scheduler.add_activity("Break", ActivityType.TYPE_B, 15, 10)

        # 3. Set configuration
        scheduler.update_user_config(max_concurrent_b=2, total_available_hours=4.0)

        # 4. Verify state
        assert len(scheduler.get_activities()) == 3
        assert scheduler.get_user_config().max_concurrent_b == 2
        assert scheduler.get_user_config().total_available_hours == 4.0

        # 5. Run optimization
        results = scheduler.optimize()

        # 6. Verify results
        assert results.maximum_gain is not None
        assert results.balanced is not None
        assert results.maximum_gain.total_value > 0
        assert results.maximum_gain.total_duration <= 240  # 4h * 60m

        # 7. Remove an activity and optimize again
        assert scheduler.remove_activity("Break")
        results2 = scheduler.optimize()
        assert len(results2.maximum_gain.schedule) <= len(results.maximum_gain.schedule)

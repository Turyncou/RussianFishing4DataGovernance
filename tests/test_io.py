import pytest
import os
from src.activity_scheduler import data_loader
from src.activity_scheduler.types import ActivityType, UserConfig
from src.activity_scheduler.exceptions import InvalidActivityError, InvalidUserConfigError


class TestDataLoading:
    """Tests for data loading functionality"""

    def test_load_activities_from_csv(self):
        """Test loading activities from CSV file"""
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        activities = data_loader.load_activities(file_path)

        assert len(activities) > 0
        assert any(act.type == ActivityType.TYPE_A for act in activities)
        assert any(act.type == ActivityType.TYPE_B for act in activities)

        # Check if known activities are present
        activity_names = [act.activity_name for act in activities]
        assert "Reading" in activity_names
        assert "Programming" in activity_names
        assert "Walking" in activity_names
        assert "Meditation" in activity_names

    def test_load_activities_invalid_file(self):
        """Test loading activities from a non-existent file"""
        with pytest.raises(FileNotFoundError):
            data_loader.load_activities("invalid_file.csv")

    def test_load_user_config_from_json(self):
        """Test loading user configuration from JSON file"""
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")
        user_config = data_loader.load_user_config(file_path)

        assert isinstance(user_config, UserConfig)
        assert user_config.max_concurrent_b > 0
        assert user_config.total_available_hours > 0

    def test_load_user_config_invalid_file(self):
        """Test loading user config from a non-existent file"""
        with pytest.raises(FileNotFoundError):
            data_loader.load_user_config("invalid_file.json")

    def test_load_activities_data_types(self):
        """Test that loaded activities have correct data types"""
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        activities = data_loader.load_activities(file_path)

        for activity in activities:
            assert isinstance(activity.activity_name, str)
            assert activity.type in [ActivityType.TYPE_A, ActivityType.TYPE_B]
            assert isinstance(activity.duration, int)
            assert activity.duration > 0
            assert isinstance(activity.value, float)
            assert activity.value > 0

    def test_load_user_config_types(self):
        """Test that user config has correct types"""
        file_path = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")
        user_config = data_loader.load_user_config(file_path)

        assert isinstance(user_config.max_concurrent_b, int)
        assert user_config.max_concurrent_b >= 0
        assert isinstance(user_config.total_available_hours, float)
        assert user_config.total_available_hours > 0


class TestDataValidation:
    """Tests for data validation"""

    def test_load_invalid_activity_type(self):
        """Test loading CSV with invalid activity type"""
        import csv
        from io import StringIO

        invalid_csv = StringIO()
        writer = csv.writer(invalid_csv)
        writer.writerow(["activity_name", "type", "duration", "value"])
        writer.writerow(["Invalid", "invalid_type", 60, 50])

        temp_file = "temp_invalid_activities.csv"
        with open(temp_file, 'w', newline='') as f:
            f.write(invalid_csv.getvalue())

        with pytest.raises(InvalidActivityError):
            data_loader.load_activities(temp_file)

        os.remove(temp_file)

    def test_load_invalid_duration_activity(self):
        """Test loading CSV with negative duration"""
        import csv
        from io import StringIO

        invalid_csv = StringIO()
        writer = csv.writer(invalid_csv)
        writer.writerow(["activity_name", "type", "duration", "value"])
        writer.writerow(["Invalid", "typeA", -60, 50])

        temp_file = "temp_invalid_duration.csv"
        with open(temp_file, 'w', newline='') as f:
            f.write(invalid_csv.getvalue())

        with pytest.raises(InvalidActivityError):
            data_loader.load_activities(temp_file)

        os.remove(temp_file)
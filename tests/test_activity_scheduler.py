"""Tests for activity scheduler integration"""
import pytest
from src.core.activity_scheduler import ActivitySchedulerIntegration


class TestActivitySchedulerIntegration:
    """Tests for activity scheduler integration"""

    def test_create_integration(self):
        """Test creating activity scheduler integration"""
        integration = ActivitySchedulerIntegration()
        assert integration is not None

    def test_get_recommendations_with_default_data(self):
        """Test getting recommendations with default/loaded data"""
        integration = ActivitySchedulerIntegration()
        # Should load default data or return empty without error
        results = integration.get_recommendations()
        # If we have default data, results should have both max gain and balanced
        if results is not None:
            assert hasattr(results, 'maximum_gain')
            assert hasattr(results, 'balanced')

    def test_set_user_config(self):
        """Test setting user configuration"""
        integration = ActivitySchedulerIntegration()
        integration.set_user_config(max_concurrent_b=2, total_available_hours=8)
        config = integration.get_user_config()
        assert config['max_concurrent_b'] == 2
        assert config['total_available_hours'] == 8

    def test_add_activity(self):
        """Test adding an activity"""
        integration = ActivitySchedulerIntegration()
        initial_count = len(integration.get_activities())
        result = integration.add_activity(
            activity_name="Test Fishing",
            activity_type="A",
            duration=60,
            value=100
        )
        assert result is True
        assert len(integration.get_activities()) == initial_count + 1

    def test_remove_activity(self):
        """Test removing an activity"""
        integration = ActivitySchedulerIntegration()
        integration.add_activity("Test", "A", 60, 100)
        initial_count = len(integration.get_activities())

        result = integration.remove_activity("Test")
        assert result is True
        assert len(integration.get_activities()) == initial_count - 1

    def test_load_from_files(self, tmp_path):
        """Test loading from CSV and JSON files"""
        # Create test CSV
        csv_path = tmp_path / "activities.csv"
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("activity_name,type,duration,value\n")
            f.write("Fishing A,typeA,120,100\n")
            f.write("Fishing B,typeB,60,50\n")

        # Create test JSON
        json_path = tmp_path / "user.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write('{"max_concurrent_b": 2, "total_available_hours": 8}\n')

        integration = ActivitySchedulerIntegration()
        result = integration.load_from_files(str(csv_path), str(json_path))
        assert result is True
        assert len(integration.get_activities()) == 2
        assert integration.get_user_config() is not None

    def test_calculate_recommendations_after_update(self):
        """Test that recommendations update after adding/removing activities"""
        integration = ActivitySchedulerIntegration()
        integration.set_user_config(max_concurrent_b=2, total_available_hours=4)
        integration.add_activity("Activity 1", "A", 60, 50)

        results1 = integration.get_recommendations()
        value1 = results1.maximum_gain.total_value

        integration.add_activity("Activity 2", "A", 60, 100)
        results2 = integration.get_recommendations()
        value2 = results2.maximum_gain.total_value

        assert value2 > value1  # Should increase with higher value activity added

    def test_invalid_activity_type_raises(self):
        """Test that invalid activity type raises error"""
        integration = ActivitySchedulerIntegration()
        with pytest.raises(ValueError):
            integration.add_activity(
                activity_name="Test",
                activity_type="invalid",
                duration=60,
                value=50
            )

    def test_save_to_files(self, tmp_path):
        """Test saving current activities and config to files"""
        csv_path = tmp_path / "test_activities.csv"
        json_path = tmp_path / "test_user.json"

        integration = ActivitySchedulerIntegration()
        integration.add_activity("Test", "A", 60, 50)
        integration.set_user_config(max_concurrent_b=3, total_available_hours=10)

        result = integration.save_to_files(str(csv_path), str(json_path))
        assert result is True
        assert csv_path.exists()
        assert json_path.exists()

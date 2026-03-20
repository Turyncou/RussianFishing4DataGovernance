import pytest
import os
from src.activity_scheduler import optimizer
from src.activity_scheduler.types import ActivityType, OptimizationResults
from src.activity_scheduler.exceptions import NoValidScheduleError


class TestActivityOptimizer:
    """Tests for activity scheduling optimization"""

    def test_load_and_optimize_basic(self):
        """Test loading data and running optimization"""
        # Load test data
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        # Run optimization
        results = optimizer.optimize_schedule(activities_file, user_config_file)

        assert isinstance(results, OptimizationResults)

    def test_optimization_results_contain_both_schedules(self):
        """Test that both maximum gain and balanced schedules are returned"""
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        results = optimizer.optimize_schedule(activities_file, user_config_file)

        assert hasattr(results, "maximum_gain")
        assert hasattr(results, "balanced")
        assert results.maximum_gain.total_value > 0
        assert results.balanced.total_value > 0
        assert results.maximum_gain.total_duration > 0
        assert results.balanced.total_duration > 0

    def test_max_gain_has_higher_value_than_balanced(self):
        """Test that maximum gain schedule has higher value than balanced schedule"""
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        results = optimizer.optimize_schedule(activities_file, user_config_file)

        assert results.maximum_gain.total_value >= results.balanced.total_value

    def test_balanced_has_rest_time(self):
        """Test that balanced schedule includes rest time"""
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        results = optimizer.optimize_schedule(activities_file, user_config_file)

        # Balanced schedule should have more rest time than maximum gain
        assert results.balanced.rest_time >= 0
        assert results.maximum_gain.rest_time <= results.balanced.rest_time

    def test_schedule_does_not_exceed_available_time(self):
        """Test that scheduled time doesn't exceed available time plus overhead"""
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        results = optimizer.optimize_schedule(activities_file, user_config_file)

        total_available_minutes = 8 * 60  # 8 hours

        assert results.maximum_gain.total_duration <= total_available_minutes
        assert results.balanced.total_duration <= total_available_minutes

    def test_switching_overhead_is_accounted_for(self):
        """Test that activity switching overhead is properly accounted for"""
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        results = optimizer.optimize_schedule(activities_file, user_config_file)

        # Overhead should be included in schedule details
        assert "total_overhead" in results.maximum_gain.details
        assert "total_overhead" in results.balanced.details
        assert results.maximum_gain.details["total_overhead"] >= 0
        assert results.balanced.details["total_overhead"] >= 0

    def test_type_a_activities_not_overlapping(self):
        """Test that Type A activities are not scheduled in parallel"""
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        results = optimizer.optimize_schedule(activities_file, user_config_file)

        # Check max gain schedule for type A overlaps
        type_a_schedule = []
        for item in results.maximum_gain.schedule:
            if item.activity.type == ActivityType.TYPE_A:
                type_a_schedule.append(item)

        # Check no overlaps
        for i in range(len(type_a_schedule)):
            for j in range(i + 1, len(type_a_schedule)):
                item1 = type_a_schedule[i]
                item2 = type_a_schedule[j]
                assert not (item1.start_time < item2.end_time and item2.start_time < item1.end_time)

    def test_type_b_concurrency_limit(self):
        """Test that Type B activities respect maximum concurrency limit"""
        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")
        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        results = optimizer.optimize_schedule(activities_file, user_config_file)

        max_concurrent_b = 2

        # Check both schedules
        for schedule_result in [results.maximum_gain, results.balanced]:
            concurrency_counts = []
            for item in schedule_result.schedule:
                if item.activity.type == ActivityType.TYPE_B:
                    concurrency_counts.append(item.concurrent_b_count)

            assert all(count <= max_concurrent_b for count in concurrency_counts)

    def test_empty_activities_file(self):
        """Test optimization with empty activities file"""
        import csv
        import os
        import tempfile
        from src.activity_scheduler.exceptions import InvalidActivityError

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(["activity_name", "type", "duration", "value"])

        user_config_file = os.path.join(os.path.dirname(__file__), "..", "data", "user.json")

        with pytest.raises(InvalidActivityError):
            optimizer.optimize_schedule(f.name, user_config_file)

        os.unlink(f.name)

    def test_no_available_time(self):
        """Test optimization with zero available time"""
        import json
        import os
        import tempfile
        from src.activity_scheduler.exceptions import InvalidUserConfigError

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"max_concurrent_b": 2, "total_available_hours": 0}, f)

        activities_file = os.path.join(os.path.dirname(__file__), "..", "data", "activities.csv")

        with pytest.raises(InvalidUserConfigError):
            optimizer.optimize_schedule(activities_file, f.name)

        os.unlink(f.name)
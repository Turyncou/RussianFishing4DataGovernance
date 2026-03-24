"""Tests for grinding statistics functionality"""
import pytest
from datetime import datetime
from src.core.grinding_stats import GrindingStatsModel


class TestGrindingStatsModel:
    """Tests for the grinding statistics model"""

    def test_create_empty_model(self):
        """Test creating empty model"""
        model = GrindingStatsModel()
        assert len(model.get_characters()) == 0

    def test_add_character(self):
        """Test adding a character"""
        model = GrindingStatsModel()
        result = model.add_character("角色A")
        assert result is True
        assert len(model.get_characters()) == 1
        assert model.get_characters()[0]["name"] == "角色A"

    def test_remove_character(self):
        """Test removing a character"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        model.add_character("角色B")
        assert len(model.get_characters()) == 2

        result = model.remove_character("角色A")
        assert result is True
        assert len(model.get_characters()) == 1
        assert model.get_characters()[0]["name"] == "角色B"

    def test_add_daily_data(self):
        """Test adding daily data"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        today = datetime.now().strftime("%Y-%m-%d")

        result = model.add_daily_data("角色A", today, 100000, 60)
        assert result is True

        character = model.get_character("角色A")
        assert today in character["daily_data"]
        assert character["daily_data"][today]["silver"] == 100000
        assert character["daily_data"][today]["minutes"] == 60

    def test_calculate_totals(self):
        """Test calculating total silver and minutes"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        model.add_daily_data("角色A", "2025-03-20", 100000, 60)
        model.add_daily_data("角色A", "2025-03-21", 150000, 90)

        totals = model.calculate_totals("角色A")
        assert totals["total_silver"] == 250000
        assert totals["total_minutes"] == 150

    def test_get_today_stats(self):
        """Test getting today's statistics"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        today = datetime.now().strftime("%Y-%m-%d")
        model.add_daily_data("角色A", today, 100000, 60)

        today_stats = model.get_today_stats("角色A")
        assert today_stats is not None
        assert today_stats["silver"] == 100000
        assert today_stats["minutes"] == 60

    def test_set_goal(self):
        """Test setting grinding goal"""
        model = GrindingStatsModel()
        model.set_goal(target_silver=1000000, target_minutes=600)
        goal = model.get_goal()
        assert goal["target_silver"] == 1000000
        assert goal["target_minutes"] == 600

    def test_calculate_progress_percent(self):
        """Test calculating progress percentage"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        model.add_daily_data("角色A", "2025-03-20", 250000, 150)
        model.set_goal(target_silver=1000000, target_minutes=600)

        progress = model.calculate_progress()
        assert progress["silver_percent"] == pytest.approx(25.0)
        assert progress["minutes_percent"] == pytest.approx(25.0)

    def test_archive_yesterday_data(self):
        """Test archiving yesterday's data on new day"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        yesterday = "2025-03-20"
        today = "2025-03-21"
        model.add_daily_data("角色A", yesterday, 100000, 60)

        # Should detect that yesterday has data and today is new day
        model.check_and_archive(yesterday, today)
        character = model.get_character("角色A")
        # Today should be empty for new day
        assert today not in character["daily_data"] or character["daily_data"][today]["silver"] == 0

    def test_get_overall_total_all_characters(self):
        """Test getting overall totals across all characters"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        model.add_character("角色B")
        model.add_daily_data("角色A", "2025-03-20", 100000, 60)
        model.add_daily_data("角色B", "2025-03-20", 200000, 120)

        overall = model.get_overall_total()
        assert overall["total_silver"] == 300000
        assert overall["total_minutes"] == 180

    def test_calculate_remaining(self):
        """Test calculating remaining silver and minutes"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        model.add_daily_data("角色A", "2025-03-20", 200000, 120)
        model.set_goal(target_silver=1000000, target_minutes=600)

        remaining = model.calculate_remaining()
        assert remaining["remaining_silver"] == 800000
        assert remaining["remaining_minutes"] == 480

    def test_update_daily_data(self):
        """Test updating existing daily data"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        today = datetime.now().strftime("%Y-%m-%d")
        model.add_daily_data("角色A", today, 100000, 60)

        result = model.update_daily_data("角色A", today, 150000, 90)
        assert result is True

        character = model.get_character("角色A")
        assert character["daily_data"][today]["silver"] == 150000
        assert character["daily_data"][today]["minutes"] == 90

    def test_clear_today_data(self):
        """Test clearing today's data"""
        model = GrindingStatsModel()
        model.add_character("角色A")
        today = datetime.now().strftime("%Y-%m-%d")
        model.add_daily_data("角色A", today, 100000, 60)

        result = model.clear_today_data("角色A", today)
        assert result is True
        character = model.get_character("角色A")
        # Entry should still exist but be zero
        assert character["daily_data"][today]["silver"] == 0
        assert character["daily_data"][today]["minutes"] == 0

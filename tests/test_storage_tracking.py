"""Tests for storage duration tracking functionality"""
import pytest
from src.core.storage_tracking import StorageTrackingModel


class TestStorageTrackingModel:
    """Tests for the storage tracking model"""

    def test_create_empty_model(self):
        """Test creating empty model"""
        model = StorageTrackingModel()
        assert len(model.get_characters()) == 0

    def test_add_character(self):
        """Test adding a character/storage spot"""
        model = StorageTrackingModel()
        result = model.add_character("金鱼池", 1200)
        assert result is True
        assert len(model.get_characters()) == 1
        char = model.get_characters()[0]
        assert char["name"] == "金鱼池"
        assert char["remaining_minutes"] == 1200

    def test_add_character_without_initial_time(self):
        """Test adding character with zero initial time"""
        model = StorageTrackingModel()
        result = model.add_character("金鱼池")
        assert result is True
        char = model.get_characters()[0]
        assert char["remaining_minutes"] == 0

    def test_remove_character(self):
        """Test removing a character"""
        model = StorageTrackingModel()
        model.add_character("金鱼池", 1200)
        model.add_character("银鱼湖", 800)
        assert len(model.get_characters()) == 2

        result = model.remove_character("金鱼池")
        assert result is True
        assert len(model.get_characters()) == 1
        assert model.get_characters()[0]["name"] == "银鱼湖"

    def test_add_time(self):
        """Test adding time to remaining"""
        model = StorageTrackingModel()
        model.add_character("金鱼池", 1200)

        result = model.add_time("金鱼池", 60)
        assert result is True
        char = model.get_character("金鱼池")
        assert char["remaining_minutes"] == 1260

    def test_subtract_time(self):
        """Test subtracting time from remaining"""
        model = StorageTrackingModel()
        model.add_character("金鱼池", 1200)

        result = model.subtract_time("金鱼池", 60)
        assert result is True
        char = model.get_character("金鱼池")
        assert char["remaining_minutes"] == 1140

    def test_subtract_time_not_negative(self):
        """Test that subtracting more than available doesn't go negative"""
        model = StorageTrackingModel()
        model.add_character("金鱼池", 100)

        result = model.subtract_time("金鱼池", 200)
        assert result is True
        char = model.get_character("金鱼池")
        assert char["remaining_minutes"] == 0

    def test_set_time(self):
        """Test directly setting remaining time"""
        model = StorageTrackingModel()
        model.add_character("金鱼池", 100)

        result = model.set_time("金鱼池", 500)
        assert result is True
        char = model.get_character("金鱼池")
        assert char["remaining_minutes"] == 500

    def test_get_total_remaining(self):
        """Test getting total remaining across all characters"""
        model = StorageTrackingModel()
        model.add_character("金鱼池", 1200)
        model.add_character("银鱼湖", 800)
        model.add_character("铜鱼溪", 500)

        total = model.get_total_remaining()
        assert total == 2500

    def test_get_character_not_found_returns_none(self):
        """Test getting non-existent character returns None"""
        model = StorageTrackingModel()
        model.add_character("金鱼池", 1200)

        char = model.get_character("不存在")
        assert char is None

    def test_add_time_to_nonexistent_character_returns_false(self):
        """Test adding time to non-existent character returns False"""
        model = StorageTrackingModel()
        result = model.add_time("不存在", 60)
        assert result is False

    def test_remove_nonexistent_character_returns_false(self):
        """Test removing non-existent character returns False"""
        model = StorageTrackingModel()
        result = model.remove_character("不存在")
        assert result is False

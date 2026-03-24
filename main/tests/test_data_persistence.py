"""Tests for data persistence layer"""
import pytest
import json
import os
import tempfile
from datetime import date
from core.models import (
    LotteryPrize, ActivityRecord, ActivityCharacter, StorageCharacter,
    FriendLink, BackgroundConfig, ActivityGoal, ActivityType
)
from data.persistence import (
    DataPersistence,
    LotteryPersistence,
    ActivityPersistence,
    StoragePersistence,
    FriendLinkPersistence,
    BackgroundPersistence
)


class TestDataPersistence:
    """Tests for base DataPersistence class"""

    def test_save_and_load_data(self):
        """Test saving and loading data to/from file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            dp = DataPersistence(f.name)
            test_data = {"key": "value", "number": 42}
            dp.save(test_data)
            loaded = dp.load()
            assert loaded == test_data
            os.unlink(f.name)

    def test_load_nonexistent_file(self):
        """Test loading from a nonexistent file returns empty dict"""
        dp = DataPersistence("/nonexistent/path/file.json")
        loaded = dp.load()
        assert loaded == {}


class TestLotteryPersistence:
    """Tests for LotteryPersistence"""

    def test_save_and_load_prizes(self):
        """Test saving and loading lottery prizes"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            lp = LotteryPersistence(f.name)
            prizes = [
                LotteryPrize("一等奖", 10.0, "#ff0000"),
                LotteryPrize("二等奖", 20.0, "#00ff00"),
                LotteryPrize("三等奖", 70.0, "#0000ff"),
            ]
            lp.save_prizes(prizes)
            loaded_prizes = lp.load_prizes()
            assert len(loaded_prizes) == 3
            assert loaded_prizes[0].name == "一等奖"
            assert loaded_prizes[0].probability == 10.0
            assert loaded_prizes[0].color == "#ff0000"
            os.unlink(f.name)

    def test_load_empty_prizes(self):
        """Test loading when no prizes saved returns default prizes"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("[]")
            f.close()
            lp = LotteryPersistence(f.name)
            loaded_prizes = lp.load_prizes()
            assert len(loaded_prizes) >= 3  # Should have defaults
            os.unlink(f.name)


class TestActivityPersistence:
    """Tests for ActivityPersistence"""

    def test_save_and_load_characters(self):
        """Test saving and loading activity characters"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            ap = ActivityPersistence(f.name)
            char1 = ActivityCharacter("角色一")
            char1.add_record(ActivityRecord(
                date=date(2025, 3, 23),
                activity_type=ActivityType.GRINDING,
                duration_minutes=120,
                silver_count=1000000
            ))
            char2 = ActivityCharacter("角色二", grinding_goal=ActivityGoal(
                activity_type=ActivityType.GRINDING,
                target_value=50000000,
                target_duration=1000,
                total_income=50000000
            ))
            char2.add_record(ActivityRecord(
                date=date(2025, 3, 23),
                activity_type=ActivityType.GRINDING,
                duration_minutes=60,
                silver_count=2000000
            ))
            characters = [char1, char2]
            ap.save_characters(characters)
            loaded = ap.load_characters()
            assert len(loaded) == 2
            assert loaded[0].name == "角色一"
            assert len(loaded[0].records) == 1
            assert loaded[1].grinding_goal is not None
            assert loaded[1].grinding_goal.target_value == 50000000
            os.unlink(f.name)

    def test_save_and_load_both_activities(self):
        """Test saving and loading characters with both activity types"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            ap = ActivityPersistence(f.name)
            char = ActivityCharacter("双活动角色")
            char.grinding_goal = ActivityGoal(
                activity_type=ActivityType.GRINDING,
                target_value=10000000,
                target_duration=1000,
                total_income=10000000
            )
            char.star_waiting_goal = ActivityGoal(
                activity_type=ActivityType.STAR_WAITING,
                target_value=100,
                target_duration=5000,
                total_income=5000000
            )
            char.add_record(ActivityRecord(
                date=date(2025, 3, 23),
                activity_type=ActivityType.GRINDING,
                duration_minutes=120,
                silver_count=1000000
            ))
            char.add_record(ActivityRecord(
                date=date(2025, 3, 23),
                activity_type=ActivityType.STAR_WAITING,
                duration_minutes=180,
                success_count=5
            ))
            ap.save_characters([char])
            loaded = ap.load_characters()
            assert len(loaded) == 1
            loaded_char = loaded[0]
            assert loaded_char.grinding_goal is not None
            assert loaded_char.star_waiting_goal is not None
            assert len(loaded_char.records) == 2
            os.unlink(f.name)

    def test_get_today_records_archiving(self):
        """Test that yesterday's records are archived"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            ap = ActivityPersistence(f.name)
            char = ActivityCharacter("测试角色")
            yesterday = date.today().replace(day=date.today().day - 1)
            char.add_record(ActivityRecord(
                date=yesterday,
                activity_type=ActivityType.GRINDING,
                duration_minutes=120,
                silver_count=1000000
            ))
            ap.save_characters([char])
            loaded = ap.load_characters()
            assert len(loaded[0].records) == 0
            os.unlink(f.name)


class TestStoragePersistence:
    """Tests for StoragePersistence"""

    def test_save_and_load_storage_characters(self):
        """Test saving and loading storage characters"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            sp = StoragePersistence(f.name)
            chars = [
                StorageCharacter("角色A", 1500),
                StorageCharacter("角色B", 2800),
            ]
            sp.save_characters(chars)
            loaded = sp.load_characters()
            assert len(loaded) == 2
            assert loaded[0].name == "角色A"
            assert loaded[0].remaining_minutes == 1500
            assert loaded[1].remaining_minutes == 2800
            os.unlink(f.name)


class TestFriendLinkPersistence:
    """Tests for FriendLinkPersistence"""

    def test_save_and_load_friend_links(self):
        """Test saving and loading friend links"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            flp = FriendLinkPersistence(f.name)
            links = [
                FriendLink("百度", "https://www.baidu.com"),
                FriendLink("GitHub", "https://github.com"),
            ]
            flp.save_links(links)
            loaded = flp.load_links()
            assert len(loaded) == 2
            assert loaded[0].text == "百度"
            assert loaded[0].url == "https://www.baidu.com"
            os.unlink(f.name)


class TestBackgroundPersistence:
    """Tests for BackgroundPersistence"""

    def test_save_and_load_background_config(self):
        """Test saving and loading background config"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            bp = BackgroundPersistence(f.name)
            config = BackgroundConfig("test_image.jpg", 0.7)
            bp.save_config(config)
            loaded = bp.load_config()
            assert loaded.image_path == "test_image.jpg"
            assert loaded.opacity == 0.7
            os.unlink(f.name)

    def test_load_default_background_config(self):
        """Test loading default config when no file exists"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.close()
            os.unlink(f.name)
            bp = BackgroundPersistence(f.name)
            loaded = bp.load_config()
            assert isinstance(loaded, BackgroundConfig)

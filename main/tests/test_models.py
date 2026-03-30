"""Tests for data models"""
import pytest
from datetime import date
from core.models import (
    LotteryPrize, ActivityRecord, ActivityCharacter, StorageCharacter,
    FriendLink, ActivityGoal, ActivitySuggestion,
    SuggestionUserSettings, ActivityType, ActivityCharacter, StorageCharacter
)


class TestLotteryPrize:
    """Tests for LotteryPrize model"""

    def test_create_lottery_prize(self):
        """Test creating a lottery prize with valid data"""
        prize = LotteryPrize(name="一等奖", probability=10.0, color="#ff0000")
        assert prize.name == "一等奖"
        assert prize.probability == 10.0
        assert prize.color == "#ff0000"

    def test_create_lottery_prize_default_color(self):
        """Test creating a lottery prize with default color"""
        prize = LotteryPrize(name="二等奖", probability=20.0)
        assert prize.color == "#cccccc"

    def test_lottery_prize_validation(self):
        """Test that invalid probabilities raise ValueError"""
        with pytest.raises(ValueError):
            LotteryPrize(name="测试", probability=-5.0)

        with pytest.raises(ValueError):
            LotteryPrize(name="测试", probability=101.0)

    def test_lottery_prize_empty_name(self):
        """Test that empty name raises ValueError"""
        with pytest.raises(ValueError):
            LotteryPrize(name="", probability=10.0)


class TestActivityRecord:
    """Tests for ActivityRecord model"""

    def test_create_grinding_record(self):
        """Test creating a grinding activity record with valid data"""
        record = ActivityRecord(
            date=date(2025, 3, 23),
            activity_type=ActivityType.GRINDING,
            duration_minutes=120,
            silver_count=1000000
        )
        assert record.date == date(2025, 3, 23)
        assert record.activity_type == ActivityType.GRINDING
        assert record.silver_count == 1000000
        assert record.duration_minutes == 120

    def test_create_star_waiting_record(self):
        """Test creating a star waiting activity record with valid data"""
        record = ActivityRecord(
            date=date(2025, 3, 23),
            activity_type=ActivityType.STAR_WAITING,
            duration_minutes=120,
            success_count=5
        )
        assert record.date == date(2025, 3, 23)
        assert record.activity_type == ActivityType.STAR_WAITING
        assert record.success_count == 5
        assert record.duration_minutes == 120

    def test_create_record_negative_values(self):
        """Test that negative values raise ValueError"""
        with pytest.raises(ValueError):
            ActivityRecord(
                date=date(2025, 3, 23),
                activity_type=ActivityType.GRINDING,
                duration_minutes=60,
                silver_count=-1000
            )

        with pytest.raises(ValueError):
            ActivityRecord(
                date=date(2025, 3, 23),
                activity_type=ActivityType.GRINDING,
                duration_minutes=-30,
                silver_count=1000
            )

        with pytest.raises(ValueError):
            ActivityRecord(
                date=date(2025, 3, 23),
                activity_type=ActivityType.STAR_WAITING,
                duration_minutes=60,
                success_count=-5
            )


class TestActivityCharacter:
    """Tests for ActivityCharacter model"""

    def test_create_activity_character(self):
        """Test creating an activity character"""
        character = ActivityCharacter(name="测试角色")
        assert character.name == "测试角色"
        assert character.records == []
        assert character.grinding_goal is None
        assert character.star_waiting_goal is None

    def test_create_activity_character_with_goals(self):
        """Test creating an activity character with goals"""
        grinding_goal = ActivityGoal(
            activity_type=ActivityType.GRINDING,
            target_value=100000000,
            target_duration=100 * 60,
            total_income=100000000
        )
        character = ActivityCharacter(name="测试角色", grinding_goal=grinding_goal)
        assert character.grinding_goal == grinding_goal

    def test_add_record(self):
        """Test adding a record to a character"""
        character = ActivityCharacter(name="测试角色")
        record = ActivityRecord(
            date=date(2025, 3, 23),
            activity_type=ActivityType.GRINDING,
            duration_minutes=120,
            silver_count=1000000
        )
        character.add_record(record)
        assert len(character.records) == 1
        assert character.records[0] == record

    def test_calculate_totals_grinding(self):
        """Test calculating total silver and duration for grinding"""
        character = ActivityCharacter(name="测试角色")
        character.add_record(ActivityRecord(
            date=date(2025, 3, 21), activity_type=ActivityType.GRINDING,
            duration_minutes=60, silver_count=1000000
        ))
        character.add_record(ActivityRecord(
            date=date(2025, 3, 22), activity_type=ActivityType.GRINDING,
            duration_minutes=120, silver_count=2000000
        ))
        character.add_record(ActivityRecord(
            date=date(2025, 3, 23), activity_type=ActivityType.GRINDING,
            duration_minutes=180, silver_count=3000000
        ))

        total_value, total_duration, remaining_value = character.calculate_totals(ActivityType.GRINDING)
        assert total_value == 6000000
        assert total_duration == 360
        assert remaining_value == 0

    def test_calculate_totals_star_waiting(self):
        """Test calculating total success count and duration for star waiting"""
        character = ActivityCharacter(name="测试角色")
        character.add_record(ActivityRecord(
            date=date(2025, 3, 21), activity_type=ActivityType.STAR_WAITING,
            duration_minutes=60, success_count=2
        ))
        character.add_record(ActivityRecord(
            date=date(2025, 3, 22), activity_type=ActivityType.STAR_WAITING,
            duration_minutes=120, success_count=3
        ))

        total_value, total_duration, remaining_value = character.calculate_totals(ActivityType.STAR_WAITING)
        assert total_value == 5
        assert total_duration == 180
        assert remaining_value == 0

    def test_calculate_totals_with_remaining(self):
        """Test calculating remaining value when goal is set"""
        character = ActivityCharacter(name="测试角色")
        character.grinding_goal = ActivityGoal(
            activity_type=ActivityType.GRINDING,
            target_value=10000000,
            target_duration=1000,
            total_income=10000000
        )
        character.add_record(ActivityRecord(
            date=date(2025, 3, 23), activity_type=ActivityType.GRINDING,
            duration_minutes=300, silver_count=4000000
        ))

        total_value, total_duration, remaining_value = character.calculate_totals(ActivityType.GRINDING)
        assert total_value == 4000000
        assert total_duration == 300
        assert remaining_value == 6000000

    def test_calculate_today_totals_grinding(self):
        """Test calculating today's totals for grinding"""
        today = date.today()
        character = ActivityCharacter(name="测试角色")
        character.add_record(ActivityRecord(
            date=today, activity_type=ActivityType.GRINDING,
            duration_minutes=60, silver_count=1000000
        ))
        character.add_record(ActivityRecord(
            date=date(2025, 3, 22), activity_type=ActivityType.GRINDING,
            duration_minutes=120, silver_count=2000000
        ))

        today_value, today_duration = character.calculate_today_totals(ActivityType.GRINDING)
        assert today_value == 1000000
        assert today_duration == 60

    def test_calculate_progress(self):
        """Test calculating progress towards goal"""
        goal = ActivityGoal(
            activity_type=ActivityType.GRINDING,
            target_value=10000000,
            target_duration=1000
        )
        character = ActivityCharacter(name="测试角色", grinding_goal=goal)
        character.add_record(ActivityRecord(
            date=date(2025, 3, 23), activity_type=ActivityType.GRINDING,
            duration_minutes=500, silver_count=5000000
        ))

        progress_value, progress_duration = character.calculate_progress(ActivityType.GRINDING)
        assert progress_value == 0.5
        assert progress_duration == 0.5

    def test_calculate_progress_no_goal(self):
        """Test that calculate_progress returns None when no goal is set"""
        character = ActivityCharacter(name="测试角色")
        character.add_record(ActivityRecord(
            date=date(2025, 3, 23), activity_type=ActivityType.GRINDING,
            duration_minutes=60, silver_count=1000000
        ))

        progress_value, progress_duration = character.calculate_progress(ActivityType.GRINDING)
        assert progress_value is None
        assert progress_duration is None

    def test_get_remaining_income(self):
        """Test calculating remaining income across both activities"""
        character = ActivityCharacter(name="测试角色")
        character.grinding_goal = ActivityGoal(
            activity_type=ActivityType.GRINDING,
            target_value=10000000,
            target_duration=1000,
            total_income=10000000
        )
        character.star_waiting_goal = ActivityGoal(
            activity_type=ActivityType.STAR_WAITING,
            target_value=100,
            target_duration=5000,
            total_income=5000000
        )
        character.add_record(ActivityRecord(
            date=date(2025, 3, 23), activity_type=ActivityType.GRINDING,
            duration_minutes=500, silver_count=5000000
        ))

        remaining = character.get_remaining_income()
        assert remaining == 5000000 + 5000000  # 50% done on grinding, 0% on star


class TestStorageCharacter:
    """Tests for StorageCharacter model"""

    def test_create_storage_character(self):
        """Test creating a storage character"""
        character = StorageCharacter(name="存储角色", remaining_minutes=1000)
        assert character.name == "存储角色"
        assert character.remaining_minutes == 1000

    def test_add_minutes(self):
        """Test adding minutes to storage character"""
        character = StorageCharacter(name="存储角色", remaining_minutes=1000)
        character.add_minutes(500)
        assert character.remaining_minutes == 1500

    def test_remove_minutes(self):
        """Test removing minutes from storage character"""
        character = StorageCharacter(name="存储角色", remaining_minutes=1000)
        character.remove_minutes(300)
        assert character.remaining_minutes == 700

    def test_remove_more_than_available(self):
        """Test removing more minutes than available should not go negative"""
        character = StorageCharacter(name="存储角色", remaining_minutes=1000)
        character.remove_minutes(1500)
        assert character.remaining_minutes == 0

    def test_create_with_negative(self):
        """Test that initial negative minutes gets clamped to 0"""
        character = StorageCharacter(name="存储角色", remaining_minutes=-100)
        assert character.remaining_minutes == 0


class TestFriendLink:
    """Tests for FriendLink model"""

    def test_create_friend_link(self):
        """Test creating a friend link"""
        link = FriendLink(text="测试网站", url="https://example.com")
        assert link.text == "测试网站"
        assert link.url == "https://example.com"

    def test_friend_link_validation(self):
        """Test that empty text or URL raises ValueError"""
        with pytest.raises(ValueError):
            FriendLink(text="", url="https://example.com")

        with pytest.raises(ValueError):
            FriendLink(text="测试", url="")


class TestActivityGoal:
    """Tests for ActivityGoal model"""

    def test_create_grinding_goal(self):
        """Test creating an activity goal"""
        goal = ActivityGoal(
            activity_type=ActivityType.GRINDING,
            target_value=100000000,
            target_duration=200 * 60,
            total_income=100000000
        )
        assert goal.target_value == 100000000
        assert goal.target_duration == 200 * 60
        assert goal.total_income == 100000000

    def test_create_activity_goal_negative(self):
        """Test that negative values raise ValueError"""
        with pytest.raises(ValueError):
            ActivityGoal(
                activity_type=ActivityType.GRINDING,
                target_value=-1000,
                target_duration=100,
                total_income=1000
            )

        with pytest.raises(ValueError):
            ActivityGoal(
                activity_type=ActivityType.GRINDING,
                target_value=1000,
                target_duration=-100,
                total_income=1000
            )

        with pytest.raises(ValueError):
            ActivityGoal(
                activity_type=ActivityType.GRINDING,
                target_value=1000,
                target_duration=100,
                total_income=-1000
            )


class TestSuggestionUserSettings:
    """Tests for SuggestionUserSettings model"""

    def test_create_default_settings(self):
        """Test creating default user settings"""
        settings = SuggestionUserSettings()
        assert settings.daily_total_hours == 8.0
        assert settings.grinding_concurrent == 1
        assert settings.star_waiting_concurrent == 1
        assert settings.switch_minutes == 20

    def test_create_custom_settings(self):
        """Test creating custom user settings"""
        settings = SuggestionUserSettings(
            daily_total_hours=12.0,
            grinding_concurrent=1,
            star_waiting_concurrent=3,
            switch_minutes=15
        )
        assert settings.daily_total_hours == 12.0
        assert settings.grinding_concurrent == 1
        assert settings.star_waiting_concurrent == 3
        assert settings.switch_minutes == 15


class TestActivitySuggestion:
    """Tests for ActivitySuggestion model"""

    def test_create_activity_suggestion(self):
        """Test creating an activity suggestion"""
        suggestion = ActivitySuggestion(
            daily_grinding_minutes=240,
            daily_star_waiting_minutes=180,
            estimated_days_remaining=10.5,
            estimated_total_income=1500000,
            recommendation="保持当前节奏"
        )
        assert suggestion.daily_grinding_minutes == 240
        assert suggestion.daily_star_waiting_minutes == 180
        assert suggestion.estimated_days_remaining == 10.5
        assert suggestion.estimated_total_income == 1500000
        assert suggestion.recommendation == "保持当前节奏"

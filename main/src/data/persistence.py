"""Data persistence layer - handles saving and loading data from JSON files"""
import json
import os
from datetime import date
from typing import Any, List
from core.models import (
    LotteryPrize, ActivityRecord, ActivityCharacter, ActivityGoal, ActivityType,
    StorageCharacter, FriendLink, BackgroundConfig, SuggestionUserSettings
)


class DataPersistence:
    """Base class for data persistence"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def save(self, data: Any) -> None:
        """Save data to JSON file"""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> dict:
        """Load data from JSON file, returns empty dict if file doesn't exist"""
        if not os.path.exists(self.file_path):
            return {}

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}


class LotteryPersistence(DataPersistence):
    """Persistence for lottery prizes"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_prizes(self, prizes: List[LotteryPrize]) -> None:
        """Save prizes to file"""
        data = [
            {
                'name': p.name,
                'probability': p.probability,
                'color': p.color
            }
            for p in prizes
        ]
        self.save(data)

    def load_prizes(self) -> List[LotteryPrize]:
        """Load prizes from file, returns defaults if empty"""
        data = self.load()
        if not data:
            return self._get_default_prizes()

        try:
            prizes = []
            for item in data:
                prize = LotteryPrize(
                    name=item.get('name', ''),
                    probability=item.get('probability', 0.0),
                    color=item.get('color', '#cccccc')
                )
                prizes.append(prize)
            return prizes if prizes else self._get_default_prizes()
        except (KeyError, ValueError):
            return self._get_default_prizes()

    def _get_default_prizes(self) -> List[LotteryPrize]:
        """Get default prize configuration"""
        return [
            LotteryPrize("谢谢参与", 50.0, "#cccccc"),
            LotteryPrize("小奖", 30.0, "#4CAF50"),
            LotteryPrize("中奖", 15.0, "#FF9800"),
            LotteryPrize("大奖", 5.0, "#F44336"),
        ]


class ActivityPersistence(DataPersistence):
    """Persistence for activity character data (both grinding and star waiting)"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_characters(self, characters: List[ActivityCharacter]) -> None:
        """Save activity characters to file"""
        # Archive records from previous days
        today = date.today()
        data = []
        for char in characters:
            char_data = {
                'name': char.name,
                'records': [
                    {
                        'date': r.date.isoformat(),
                        'activity_type': r.activity_type.value,
                        'silver_count': r.silver_count,
                        'success_count': r.success_count,
                        'duration_minutes': r.duration_minutes
                    }
                    for r in char.records
                ],
                'grinding_goal': {
                    'activity_type': char.grinding_goal.activity_type.value,
                    'target_value': char.grinding_goal.target_value,
                    'target_duration': char.grinding_goal.target_duration,
                    'total_income': char.grinding_goal.total_income
                } if char.grinding_goal else None,
                'star_waiting_goal': {
                    'activity_type': char.star_waiting_goal.activity_type.value,
                    'target_value': char.star_waiting_goal.target_value,
                    'target_duration': char.star_waiting_goal.target_duration,
                    'total_income': char.star_waiting_goal.total_income
                } if char.star_waiting_goal else None,
                'suggestion_settings': {
                    'daily_total_hours': char.suggestion_settings.daily_total_hours,
                    'grinding_concurrent': char.suggestion_settings.grinding_concurrent,
                    'star_waiting_concurrent': char.suggestion_settings.star_waiting_concurrent,
                    'switch_minutes': char.suggestion_settings.switch_minutes
                }
            }
            data.append(char_data)
        self.save(data)

    def load_characters(self) -> List[ActivityCharacter]:
        """Load activity characters from file"""
        data = self.load()
        if not data:
            return []

        try:
            characters = []
            today = date.today()
            for item in data:
                char = ActivityCharacter(name=item.get('name', ''))

                # Load goals
                grinding_goal_data = item.get('grinding_goal')
                if grinding_goal_data:
                    char.grinding_goal = ActivityGoal(
                        activity_type=ActivityType.GRINDING,
                        target_value=grinding_goal_data.get('target_value', 0),
                        target_duration=grinding_goal_data.get('target_duration', 0),
                        total_income=grinding_goal_data.get('total_income', 0)
                    )

                star_waiting_goal_data = item.get('star_waiting_goal')
                if star_waiting_goal_data:
                    char.star_waiting_goal = ActivityGoal(
                        activity_type=ActivityType.STAR_WAITING,
                        target_value=star_waiting_goal_data.get('target_value', 0),
                        target_duration=star_waiting_goal_data.get('target_duration', 0),
                        total_income=star_waiting_goal_data.get('total_income', 0)
                    )

                # Load suggestion settings
                settings_data = item.get('suggestion_settings')
                if settings_data:
                    char.suggestion_settings = SuggestionUserSettings(
                        daily_total_hours=settings_data.get('daily_total_hours', 8.0),
                        grinding_concurrent=settings_data.get('grinding_concurrent', 1),
                        star_waiting_concurrent=settings_data.get('star_waiting_concurrent', 1),
                        switch_minutes=settings_data.get('switch_minutes', 20)
                    )

                # Only load records from today when opening
                for record_data in item.get('records', []):
                    record_date = date.fromisoformat(record_data.get('date'))
                    if record_date == today:
                        activity_type = ActivityType(record_data.get('activity_type'))
                        record = ActivityRecord(
                            date=record_date,
                            activity_type=activity_type,
                            silver_count=record_data.get('silver_count', 0),
                            success_count=record_data.get('success_count', 0),
                            duration_minutes=record_data.get('duration_minutes', 0)
                        )
                        char.add_record(record)
                characters.append(char)
            return characters
        except (KeyError, ValueError):
            return []


class StoragePersistence(DataPersistence):
    """Persistence for storage character duration data"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_characters(self, characters: List[StorageCharacter]) -> None:
        """Save storage characters to file"""
        data = [
            {
                'name': c.name,
                'remaining_minutes': c.remaining_minutes
            }
            for c in characters
        ]
        self.save(data)

    def load_characters(self) -> List[StorageCharacter]:
        """Load storage characters from file"""
        data = self.load()
        if not data:
            return []

        try:
            characters = []
            for item in data:
                char = StorageCharacter(
                    name=item.get('name', ''),
                    remaining_minutes=item.get('remaining_minutes', 0)
                )
                characters.append(char)
            return characters
        except (KeyError, ValueError):
            return []


class FriendLinkPersistence(DataPersistence):
    """Persistence for friend links"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_links(self, links: List[FriendLink]) -> None:
        """Save friend links to file"""
        data = [
            {
                'text': l.text,
                'url': l.url
            }
            for l in links
        ]
        self.save(data)

    def load_links(self) -> List[FriendLink]:
        """Load friend links from file"""
        data = self.load()
        if not data:
            return []

        try:
            links = []
            for item in data:
                link = FriendLink(
                    text=item.get('text', ''),
                    url=item.get('url', '')
                )
                links.append(link)
            return links
        except (KeyError, ValueError):
            return []


class BackgroundPersistence(DataPersistence):
    """Persistence for background configuration"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_config(self, config: BackgroundConfig) -> None:
        """Save background configuration to file"""
        data = {
            'image_path': config.image_path,
            'opacity': config.opacity
        }
        self.save(data)

    def load_config(self) -> BackgroundConfig:
        """Load background configuration from file"""
        data = self.load()
        if not data:
            return BackgroundConfig()

        try:
            return BackgroundConfig(
                image_path=data.get('image_path'),
                opacity=data.get('opacity', 1.0)
            )
        except (KeyError, ValueError):
            return BackgroundConfig()

"""Data persistence layer - handles saving and loading data from JSON files"""
import json
import os
import base64
import shutil
from datetime import datetime, date
from typing import Any, List
from cryptography.fernet import Fernet
from src.core.models import (
    LotteryPrize, ActivityRecord, ActivityCharacter, ActivityGoal, ActivityType,
    StorageCharacter, FriendLink, SuggestionUserSettings, OptimizationAlgorithm,
    AccountCredential, BaitConsumption, DailyTask, DailyTaskCompletion
)


class DataPersistence:
    """Base class for data persistence with memory caching to avoid repeated IO"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._cached_data: dict | None = None
        self._last_modified: float = 0

    def save(self, data: Any) -> None:
        """Save data to JSON file"""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Update cache after saving
        if isinstance(data, dict):
            self._cached_data = data
        else:
            self._cached_data = None
        if os.path.exists(self.file_path):
            self._last_modified = os.path.getmtime(self.file_path)

    def load(self) -> dict:
        """Load data from JSON file, returns empty dict if file doesn't exist
        Uses in-memory cache to avoid repeated disk reads when file hasn't changed
        """
        # Check if we have cached data and file hasn't been modified
        if self._cached_data is not None and os.path.exists(self.file_path):
            mtime = os.path.getmtime(self.file_path)
            if abs(mtime - self._last_modified) < 0.1:  # Within 100ms, consider unchanged
                return self._cached_data.copy()

        if not os.path.exists(self.file_path):
            self._cached_data = {}
            self._last_modified = 0
            return {}

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cached_data = data
                self._last_modified = os.path.getmtime(self.file_path)
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            self._cached_data = {}
            self._last_modified = 0
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
        # Store data directory (contains the file) for loading fish names
        self.data_dir = os.path.dirname(file_path)

    def save_characters(self, characters: List[ActivityCharacter], global_suggestion_settings: SuggestionUserSettings = None) -> None:
        """Save activity characters to file, with global suggestion settings"""
        # Archive records from previous days
        today = date.today()
        data = {
            'version': 2,
            'global_suggestion_settings': (
                {
                    'daily_total_hours': global_suggestion_settings.daily_total_hours,
                    'grinding_concurrent': global_suggestion_settings.grinding_concurrent,
                    'star_waiting_concurrent': global_suggestion_settings.star_waiting_concurrent,
                    'switch_minutes': global_suggestion_settings.switch_minutes,
                    'algorithm': (
                        global_suggestion_settings.algorithm.value
                        if isinstance(global_suggestion_settings.algorithm, OptimizationAlgorithm)
                        else OptimizationAlgorithm.BALANCED.value
                    )
                }
                if global_suggestion_settings
                else None
            ),
            'characters': []
        }
        for char in characters:
            char_data = {
                'name': char.name,
                'records': [
                    {
                        'date': r.date.isoformat(),
                        'activity_type': r.activity_type.value,
                        'silver_count': r.silver_count,
                        'success_count': r.success_count,
                        'duration_minutes': r.duration_minutes,
                        'caught_fish': r.caught_fish
                    }
                    for r in char.records
                ],
                # New format: multiple goals
                'grinding_goals': [
                    {
                        'activity_type': goal.activity_type.value,
                        'target_value': goal.target_value,
                        'target_duration': goal.target_duration,
                        'total_income': goal.total_income,
                        'fish_name': goal.fish_name,
                        'current_progress': goal.current_progress
                    }
                    for goal in char.grinding_goals
                ] if char.grinding_goals else None,
                'star_waiting_goals': [
                    {
                        'activity_type': goal.activity_type.value,
                        'target_value': goal.target_value,
                        'target_duration': goal.target_duration,
                        'total_income': goal.total_income,
                        'fish_name': goal.fish_name,
                        'current_progress': goal.current_progress
                    }
                    for goal in char.star_waiting_goals
                ] if char.star_waiting_goals else None,
                # Backward compatibility: single goal
                'grinding_goal': {
                    'activity_type': char.grinding_goal.activity_type.value,
                    'target_value': char.grinding_goal.target_value,
                    'target_duration': char.grinding_goal.target_duration,
                    'total_income': char.grinding_goal.total_income,
                    'fish_name': char.grinding_goal.fish_name,
                    'current_progress': char.grinding_goal.current_progress
                } if char.grinding_goal else None,
                'star_waiting_goal': {
                    'activity_type': char.star_waiting_goal.activity_type.value,
                    'target_value': char.star_waiting_goal.target_value,
                    'target_duration': char.star_waiting_goal.target_duration,
                    'total_income': char.star_waiting_goal.total_income,
                    'fish_name': char.star_waiting_goal.fish_name,
                    'current_progress': char.star_waiting_goal.current_progress
                } if char.star_waiting_goal else None,
                # Keep per-character settings for backward compatibility
                'suggestion_settings': {
                    'daily_total_hours': char.suggestion_settings.daily_total_hours,
                    'grinding_concurrent': char.suggestion_settings.grinding_concurrent,
                    'star_waiting_concurrent': char.suggestion_settings.star_waiting_concurrent,
                    'switch_minutes': char.suggestion_settings.switch_minutes
                }
            }
            data['characters'].append(char_data)
        self.save(data)

    def load_characters(self) -> tuple[List[ActivityCharacter], SuggestionUserSettings | None]:
        """Load activity characters from file, returns (characters, global_suggestion_settings)
        Only loads today's records into memory for activity statistics page
        """
        return self._load_characters_internal(only_today=True)

    def load_all_characters(self) -> tuple[List[ActivityCharacter], SuggestionUserSettings | None]:
        """Load activity characters from file with ALL records (for statistics/analysis page)"""
        return self._load_characters_internal(only_today=False)

    def _load_characters_internal(self, only_today: bool) -> tuple[List[ActivityCharacter], SuggestionUserSettings | None]:
        """Internal load method, can load only today or all records"""
        data = self.load()
        if not data:
            return [], None

        try:
            # Check if new format with global settings
            if isinstance(data, dict) and 'characters' in data:
                # Version 2 format
                characters_data = data.get('characters', [])
                global_settings_data = data.get('global_suggestion_settings')
                global_settings = None
                if global_settings_data:
                    # Load algorithm with backward compatibility
                    algorithm_val = global_settings_data.get('algorithm', OptimizationAlgorithm.BALANCED.value)
                    try:
                        algorithm = OptimizationAlgorithm(algorithm_val)
                    except ValueError:
                        algorithm = OptimizationAlgorithm.BALANCED

                    global_settings = SuggestionUserSettings(
                        daily_total_hours=global_settings_data.get('daily_total_hours', 8.0),
                        grinding_concurrent=global_settings_data.get('grinding_concurrent', 1),
                        star_waiting_concurrent=global_settings_data.get('star_waiting_concurrent', 1),
                        switch_minutes=global_settings_data.get('switch_minutes', 20),
                        algorithm=algorithm
                    )
            else:
                # Version 1 format - old format is just list of characters
                characters_data = data
                global_settings = None

            characters = []
            today = date.today()
            for item in characters_data:
                char = ActivityCharacter(name=item.get('name', ''))

                # Load goals - try new format first (multiple goals), then backward compatibility
                # Grinding goals
                grinding_goals_data = item.get('grinding_goals')
                if grinding_goals_data:
                    for goal_data in grinding_goals_data:
                        if goal_data:
                            char.grinding_goals.append(ActivityGoal(
                                activity_type=ActivityType.GRINDING,
                                target_value=goal_data.get('target_value', 0),
                                target_duration=goal_data.get('target_duration', 0),
                                total_income=goal_data.get('total_income', 0),
                                fish_name=goal_data.get('fish_name'),
                                current_progress=goal_data.get('current_progress', 0)
                            ))
                else:
                    # Backward compatibility: single goal
                    grinding_goal_data = item.get('grinding_goal')
                    if grinding_goal_data:
                        char.grinding_goals.append(ActivityGoal(
                            activity_type=ActivityType.GRINDING,
                            target_value=grinding_goal_data.get('target_value', 0),
                            target_duration=grinding_goal_data.get('target_duration', 0),
                            total_income=grinding_goal_data.get('total_income', 0),
                            fish_name=grinding_goal_data.get('fish_name'),
                            current_progress=grinding_goal_data.get('current_progress', 0)
                        ))

                # Star waiting goals
                star_waiting_goals_data = item.get('star_waiting_goals')
                if star_waiting_goals_data:
                    for goal_data in star_waiting_goals_data:
                        if goal_data:
                            char.star_waiting_goals.append(ActivityGoal(
                                activity_type=ActivityType.STAR_WAITING,
                                target_value=goal_data.get('target_value', 0),
                                target_duration=goal_data.get('target_duration', 0),
                                total_income=goal_data.get('total_income', 0),
                                fish_name=goal_data.get('fish_name'),
                                current_progress=goal_data.get('current_progress', 0)
                            ))
                else:
                    # Backward compatibility: single goal
                    star_waiting_goal_data = item.get('star_waiting_goal')
                    if star_waiting_goal_data:
                        char.star_waiting_goals.append(ActivityGoal(
                            activity_type=ActivityType.STAR_WAITING,
                            target_value=star_waiting_goal_data.get('target_value', 0),
                            target_duration=star_waiting_goal_data.get('target_duration', 0),
                            total_income=star_waiting_goal_data.get('total_income', 0),
                            fish_name=star_waiting_goal_data.get('fish_name'),
                            current_progress=star_waiting_goal_data.get('current_progress', 0)
                        ))

                # Load suggestion settings
                settings_data = item.get('suggestion_settings')
                if settings_data:
                    # Load algorithm with backward compatibility
                    algorithm_val = settings_data.get('algorithm', OptimizationAlgorithm.BALANCED.value)
                    try:
                        algorithm = OptimizationAlgorithm(algorithm_val)
                    except ValueError:
                        algorithm = OptimizationAlgorithm.BALANCED

                    char.suggestion_settings = SuggestionUserSettings(
                        daily_total_hours=settings_data.get('daily_total_hours', 8.0),
                        grinding_concurrent=settings_data.get('grinding_concurrent', 1),
                        star_waiting_concurrent=settings_data.get('star_waiting_concurrent', 1),
                        switch_minutes=settings_data.get('switch_minutes', 20),
                        algorithm=algorithm
                    )

                # Load records - only today or all
                for record_data in item.get('records', []):
                    record_date = date.fromisoformat(record_data.get('date'))
                    if not only_today or record_date == today:
                        activity_type = ActivityType(record_data.get('activity_type'))
                        record = ActivityRecord(
                            date=record_date,
                            activity_type=activity_type,
                            silver_count=record_data.get('silver_count', 0),
                            success_count=record_data.get('success_count', 0),
                            duration_minutes=record_data.get('duration_minutes', 0),
                            caught_fish=record_data.get('caught_fish', [])
                        )
                        char.add_record(record)
                characters.append(char)

            return characters, global_settings
        except (KeyError, ValueError):
            return [], None

    def export_to_csv(self, characters: List[ActivityCharacter], file_path: str) -> None:
        """Export all activity records to CSV file"""
        import csv
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['角色名称', '日期', '活动类型', '银币/成功数量', '时长(分钟)'])
            for char in characters:
                for record in char.records:
                    activity_type = '搬砖' if record.activity_type == ActivityType.GRINDING else '蹲星'
                    value = record.silver_count if record.activity_type == ActivityType.GRINDING else record.success_count
                    writer.writerow([char.name, record.date.strftime('%Y-%m-%d'), activity_type, value, record.duration_minutes])

    def import_from_csv(self, file_path: str) -> List[ActivityCharacter]:
        """Import activity records from CSV file
        Expected CSV format: 角色名称,日期,活动类型,银币/成功数量,时长(分钟)
        Returns list of ActivityCharacter with imported records
        """
        import csv
        characters_map: dict[str, ActivityCharacter] = {}
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            for row in reader:
                if len(row) < 5:
                    continue
                char_name = row[0].strip()
                date_str = row[1].strip()
                activity_type_str = row[2].strip()
                value_str = row[3].strip()
                duration_str = row[4].strip()

                try:
                    record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    value = int(float(value_str.replace(',', '')))
                    duration = int(float(duration_str))

                    if activity_type_str in ['搬砖', 'grinding', 'GRINDING']:
                        activity_type = ActivityType.GRINDING
                        silver_count = value
                        success_count = 0
                    else:
                        activity_type = ActivityType.STAR_WAITING
                        silver_count = 0
                        success_count = value

                    if char_name not in characters_map:
                        characters_map[char_name] = ActivityCharacter(char_name)
                    char = characters_map[char_name]
                    record = ActivityRecord(
                        date=record_date,
                        activity_type=activity_type,
                        silver_count=silver_count,
                        success_count=success_count,
                        duration_minutes=duration
                    )
                    char.add_record(record)
                except (ValueError, IndexError):
                    continue  # Skip invalid rows

        return list(characters_map.values())


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


class CredentialsPersistence(DataPersistence):
    """Persistence for account credentials (passwords stored with Fernet symmetric encryption)"""

    def __init__(self, file_path: str):
        super().__init__(file_path)
        # Key file is stored alongside the credentials file
        self._key_path = file_path + '.key'
        self._fernet = self._get_or_create_key()

    def _get_or_create_key(self) -> Fernet:
        """Get existing key from file or create a new one"""
        if os.path.exists(self._key_path):
            with open(self._key_path, 'rb') as f:
                key = f.read()
        else:
            # Generate new Fernet key
            key = Fernet.generate_key()
            directory = os.path.dirname(self._key_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            with open(self._key_path, 'wb') as f:
                f.write(key)
            # Make key file readable only by the current user (on Unix-like systems)
            try:
                os.chmod(self._key_path, 0o600)
            except:
                pass  # Windows doesn't support this, ignore
        return Fernet(key)

    def _encrypt_password(self, password: str) -> str:
        """Fernet symmetric encryption (standard secure encryption)"""
        password_bytes = password.encode('utf-8')
        encrypted = self._fernet.encrypt(password_bytes)
        return encrypted.decode('utf-8')

    def _decrypt_password(self, encrypted: str) -> str:
        """Decrypt password using Fernet"""
        try:
            encrypted_bytes = encrypted.encode('utf-8')
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except:
            return ""

    def save_credentials(self, accounts: List[AccountCredential]) -> None:
        """Save accounts to file"""
        data = [
            {
                'account_name': a.account_name,
                'encrypted_password': a.encrypted_password
            }
            for a in accounts
        ]
        self.save(data)

    def load_credentials(self) -> List[AccountCredential]:
        """Load accounts from file"""
        data = self.load()
        if not data:
            return []

        try:
            accounts = []
            for item in data:
                account = AccountCredential(
                    account_name=item.get('account_name', ''),
                    encrypted_password=item.get('encrypted_password', '')
                )
                accounts.append(account)
            return accounts
        except (KeyError, ValueError):
            return []

    def add_account(self, account_name: str, plain_password: str) -> AccountCredential:
        """Add a new account with encrypted password"""
        encrypted = self._encrypt_password(plain_password)
        return AccountCredential(account_name=account_name, encrypted_password=encrypted)

    def get_plain_password(self, account: AccountCredential) -> str:
        """Get decrypted plain password from account"""
        return self._decrypt_password(account.encrypted_password)


class BaitPersistence(DataPersistence):
    """Persistence for bait/tackle consumption tracking"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_baits(self, baits: List[BaitConsumption]) -> None:
        """Save bait list to file"""
        data = [
            {
                'name': b.name,
                'total_bought': b.total_bought,
                'total_used': b.total_used
            }
            for b in baits
        ]
        self.save(data)

    def load_baits(self) -> List[BaitConsumption]:
        """Load bait list from file"""
        data = self.load()
        if not data:
            return []

        try:
            baits = []
            for item in data:
                bait = BaitConsumption(
                    name=item.get('name', ''),
                    total_bought=item.get('total_bought', 0),
                    total_used=item.get('total_used', 0)
                )
                baits.append(bait)
            return baits
        except (KeyError, ValueError):
            return []


class AppSettingsPersistence(DataPersistence):
    """Persistence for application settings like background image"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_settings(self, background_image_path: str = None, background_opacity: float = 0.15, theme: str = "dark", show_income_info: bool = False,
                     screen_recorder_start_hotkey: str = None, screen_recorder_stop_hotkey: str = None, screen_recorder_save_path: str = None,
                     screen_recorder_record_mic: bool = False, screen_recorder_record_system: bool = False,
                     special_cursor_on_hover: bool = True,
                     enable_performance_log: bool = True) -> None:
        """Save application settings"""
        data = {
            'background_image_path': background_image_path if background_image_path else None,
            'background_opacity': background_opacity,
            'theme': theme,
            'show_income_info': show_income_info,
            'screen_recorder_start_hotkey': screen_recorder_start_hotkey,
            'screen_recorder_stop_hotkey': screen_recorder_stop_hotkey,
            'screen_recorder_save_path': screen_recorder_save_path,
            'screen_recorder_record_mic': screen_recorder_record_mic,
            'screen_recorder_record_system': screen_recorder_record_system,
            'special_cursor_on_hover': special_cursor_on_hover,
            'enable_performance_log': enable_performance_log,
        }
        self.save(data)

    def load_settings(self) -> dict:
        """Load application settings, returns dict with defaults if not found"""
        data = self.load()
        if not data:
            return {
                'background_image_path': None,
                'background_opacity': 0.15,
                'theme': 'dark',
                'show_income_info': False,
                'screen_recorder_start_hotkey': 'ctrl+shift+r',
                'screen_recorder_stop_hotkey': 'ctrl+shift+s',
                'screen_recorder_save_path': None,
                'screen_recorder_record_mic': False,
                'screen_recorder_record_system': False,
                'special_cursor_on_hover': True,
                'enable_performance_log': True,
            }

        try:
            return {
                'background_image_path': data.get('background_image_path', None),
                'background_opacity': float(data.get('background_opacity', 0.15)),
                'theme': data.get('theme', 'dark'),
                'show_income_info': data.get('show_income_info', False),
                'screen_recorder_start_hotkey': data.get('screen_recorder_start_hotkey', 'ctrl+shift+r'),
                'screen_recorder_stop_hotkey': data.get('screen_recorder_stop_hotkey', 'ctrl+shift+s'),
                'screen_recorder_save_path': data.get('screen_recorder_save_path', None),
                'screen_recorder_record_mic': data.get('screen_recorder_record_mic', False),
                'screen_recorder_record_system': data.get('screen_recorder_record_system', False),
                'special_cursor_on_hover': data.get('special_cursor_on_hover', True),
                'enable_performance_log': data.get('enable_performance_log', True),
            }
        except (KeyError, ValueError):
            return {
                'background_image_path': None,
                'background_opacity': 0.15,
                'theme': 'dark',
                'show_income_info': False,
                'screen_recorder_start_hotkey': 'ctrl+shift+r',
                'screen_recorder_stop_hotkey': 'ctrl+shift+s',
                'screen_recorder_save_path': None,
                'screen_recorder_record_mic': False,
                'screen_recorder_record_system': False,
                'special_cursor_on_hover': True,
                'enable_performance_log': True,
            }


def create_auto_backup(source_dir: str, backup_dir: str) -> str:
    """Create automatic backup of all JSON data files

    Returns:
        Path to the created backup directory
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'backup_{timestamp}')
    os.makedirs(backup_path, exist_ok=True)

    # Backup all JSON files in source directory
    for filename in os.listdir(source_dir):
        if filename.endswith('.json') or filename.endswith('.json.key'):
            source_file = os.path.join(source_dir, filename)
            dest_file = os.path.join(backup_path, filename)
            shutil.copy2(source_file, dest_file)

    return backup_path


def list_backups(backup_dir: str) -> list[str]:
    """List available backups sorted by newest first"""
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for name in os.listdir(backup_dir):
        if os.path.isdir(os.path.join(backup_dir, name)) and name.startswith('backup_'):
            backups.append(name)

    backups.sort(reverse=True)
    return backups


class DailyTaskPersistence(DataPersistence):
    """Persistence for daily tasks and their completion history"""

    def __init__(self, file_path: str):
        super().__init__(file_path)

    def save_tasks(self, tasks: List[DailyTask]) -> None:
        """Save daily task definitions to file"""
        data = {
            'tasks': [
                {
                    'character_name': t.character_name,
                    'activity_type': t.activity_type.value,
                    'target_minutes': t.target_minutes,
                    'enabled': t.enabled
                }
                for t in tasks
            ]
        }
        self.save(data)

    def load_tasks(self) -> List[DailyTask]:
        """Load daily task definitions from file"""
        data = self.load()
        if not data:
            return []

        try:
            tasks_data = data.get('tasks', [])
            tasks = []
            for item in tasks_data:
                task = DailyTask(
                    character_name=item.get('character_name', ''),
                    activity_type=ActivityType(item.get('activity_type')),
                    target_minutes=item.get('target_minutes', 0),
                    enabled=item.get('enabled', True)
                )
                if task.character_name.strip():
                    tasks.append(task)
            return tasks
        except (KeyError, ValueError):
            return []

    def get_today_completion(self, tasks: List[DailyTask], characters: List[ActivityCharacter]) -> List[DailyTaskCompletion]:
        """Calculate today's completion status for all tasks based on activity records"""
        today = date.today()
        completions = []

        for task in tasks:
            if not task.enabled:
                continue

            # Find the corresponding character
            char = next((c for c in characters if c.name == task.character_name), None)
            if char is None:
                # Character not found - skip
                continue

            # Get today's duration for this activity type
            _, actual_duration = char.calculate_today_totals(task.activity_type)

            completed = actual_duration >= task.target_minutes
            completion = DailyTaskCompletion(
                date=today,
                character_name=task.character_name,
                activity_type=task.activity_type,
                target_minutes=task.target_minutes,
                actual_minutes=actual_duration,
                completed=completed
            )
            completions.append(completion)

        return completions

    def get_incomplete_tasks(self, tasks: List[DailyTask], characters: List[ActivityCharacter]) -> List[DailyTaskCompletion]:
        """Get all incomplete tasks for today"""
        completions = self.get_today_completion(tasks, characters)
        return [c for c in completions if not c.completed]

    def get_completion_stats(self, tasks: List[DailyTask], characters: List[ActivityCharacter]) -> tuple[int, int, float]:
        """Get today's completion statistics: (completed_count, total_count, completion_percent)"""
        completions = self.get_today_completion(tasks, characters)
        if not completions:
            return 0, 0, 100.0
        completed = sum(1 for c in completions if c.completed)
        total = len(completions)
        percent = (completed / total) * 100 if total > 0 else 100.0
        return completed, total, percent

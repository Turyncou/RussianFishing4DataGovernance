"""GUI module containing all interface components"""
from .main_window import MainWindow
from .lottery_frame import LotteryFrame
from .activity_frame import ActivityFrame
from .storage_frame import StorageFrame
from .statistics_frame import StatisticsFrame
from .friend_links_dialog import FriendLinksDialog
from .suggestion_calculator import calculate_suggestion

__all__ = [
    'MainWindow',
    'LotteryFrame',
    'ActivityFrame',
    'StorageFrame',
    'StatisticsFrame',
    'FriendLinksDialog',
    'calculate_suggestion',
]

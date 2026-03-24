"""GUI module containing all interface components"""
from .main_window import MainWindow
from .cat_follower import CatFollower
from .lottery_frame import LotteryFrame
from .activity_frame import ActivityFrame
from .storage_frame import StorageFrame
from .background_dialog import BackgroundDialog
from .friend_links_dialog import FriendLinksDialog
from .suggestion_calculator import calculate_suggestion

__all__ = [
    'MainWindow',
    'CatFollower',
    'LotteryFrame',
    'ActivityFrame',
    'StorageFrame',
    'BackgroundDialog',
    'FriendLinksDialog',
    'calculate_suggestion',
]

"""Pytest configuration and fixtures for testing"""
import os
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def temp_data_dir():
    """Fixture providing a temporary directory for test data storage"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_lucky_draw_data():
    """Sample lucky draw prize data for testing"""
    return [
        {"name": "一等奖", "probability": 0.05, "enabled": True},
        {"name": "二等奖", "probability": 0.15, "enabled": True},
        {"name": "三等奖", "probability": 0.30, "enabled": True},
        {"name": "谢谢参与", "probability": 0.50, "enabled": True},
    ]


@pytest.fixture
def sample_grinding_data():
    """Sample grinding statistics data for testing"""
    return {
        "characters": [
            {
                "name": "角色A",
                "daily_data": {
                    "2025-03-20": {"silver": 100000, "minutes": 60}
                },
                "total_silver": 100000,
                "total_minutes": 60,
            }
        ],
        "goal": {
            "target_silver": 1000000,
            "target_minutes": 600,
        }
    }


@pytest.fixture
def sample_storage_data():
    """Sample storage tracking data for testing"""
    return {
        "characters": [
            {"name": "金鱼池", "remaining_minutes": 1200},
            {"name": "银鱼湖", "remaining_minutes": 800},
        ]
    }


@pytest.fixture
def sample_friend_links():
    """Sample friend links data for testing"""
    return [
        {"name": "俄罗斯钓鱼4官网", "url": "https://example.com/rf4"},
        {"name": "攻略网站", "url": "https://example.com/guide"},
    ]


@pytest.fixture
def empty_data_manager(temp_data_dir):
    """Fixture providing an empty DataManager instance"""
    from src.core.data_manager import DataManager
    dm = DataManager(data_dir=temp_data_dir)
    return dm

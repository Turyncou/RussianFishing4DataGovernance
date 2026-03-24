"""Tests for data persistence functionality"""
import json
import pytest
from src.core.data_manager import DataManager


class TestDataManager:
    """Tests for DataManager"""

    def test_create_data_manager(self, temp_data_dir):
        """Test creating DataManager"""
        dm = DataManager(data_dir=temp_data_dir)
        assert dm.data_dir == temp_data_dir
        assert dm.data_dir.exists()

    def test_save_lucky_draw(self, temp_data_dir, sample_lucky_draw_data):
        """Test saving lucky draw data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_lucky_draw(sample_lucky_draw_data)

        file_path = temp_data_dir / "lucky_draw.json"
        assert file_path.exists()

        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == sample_lucky_draw_data

    def test_load_lucky_draw(self, temp_data_dir, sample_lucky_draw_data):
        """Test loading lucky draw data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_lucky_draw(sample_lucky_draw_data)

        loaded = dm.load_lucky_draw()
        assert loaded == sample_lucky_draw_data

    def test_load_lucky_draw_returns_empty_list_when_no_file(self, temp_data_dir):
        """Test loading when file doesn't exist returns empty list"""
        dm = DataManager(data_dir=temp_data_dir)
        loaded = dm.load_lucky_draw()
        assert loaded == []

    def test_save_grinding_stats(self, temp_data_dir, sample_grinding_data):
        """Test saving grinding statistics data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_grinding_stats(sample_grinding_data)

        file_path = temp_data_dir / "grinding_stats.json"
        assert file_path.exists()

    def test_load_grinding_stats(self, temp_data_dir, sample_grinding_data):
        """Test loading grinding statistics data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_grinding_stats(sample_grinding_data)

        loaded = dm.load_grinding_stats()
        assert loaded == sample_grinding_data

    def test_save_storage_tracking(self, temp_data_dir, sample_storage_data):
        """Test saving storage tracking data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_storage_tracking(sample_storage_data)

        file_path = temp_data_dir / "storage_tracking.json"
        assert file_path.exists()

    def test_load_storage_tracking(self, temp_data_dir, sample_storage_data):
        """Test loading storage tracking data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_storage_tracking(sample_storage_data)

        loaded = dm.load_storage_tracking()
        assert loaded == sample_storage_data

    def test_save_friend_links(self, temp_data_dir, sample_friend_links):
        """Test saving friend links data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_friend_links(sample_friend_links)

        file_path = temp_data_dir / "friend_links.json"
        assert file_path.exists()

    def test_load_friend_links(self, temp_data_dir, sample_friend_links):
        """Test loading friend links data"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_friend_links(sample_friend_links)

        loaded = dm.load_friend_links()
        assert loaded == sample_friend_links

    def test_save_background_settings(self, temp_data_dir):
        """Test saving background settings"""
        settings = {
            "custom_image_path": None,
            "transparency": 0.8
        }
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_background_settings(settings)

        loaded = dm.load_background_settings()
        assert loaded == settings

    def test_save_config(self, temp_data_dir):
        """Test saving application config"""
        config = {
            "window_width": 1200,
            "window_height": 800,
            "last_open_tab": 0
        }
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_config(config)

        loaded = dm.load_config()
        assert loaded == config

    def test_corrupted_json_returns_empty(self, temp_data_dir):
        """Test that corrupted JSON returns empty data structure"""
        dm = DataManager(data_dir=temp_data_dir)
        file_path = temp_data_dir / "lucky_draw.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{ this is not valid json")

        loaded = dm.load_lucky_draw()
        assert loaded == []

    def test_backup_created_on_save(self, temp_data_dir, sample_lucky_draw_data):
        """Test that backup is created when saving"""
        dm = DataManager(data_dir=temp_data_dir)
        dm.save_lucky_draw(sample_lucky_draw_data)

        # Save again to trigger backup
        dm.save_lucky_draw(sample_lucky_draw_data)

        backup_files = list(temp_data_dir.glob("lucky_draw.*.backup.json"))
        assert len(backup_files) >= 1

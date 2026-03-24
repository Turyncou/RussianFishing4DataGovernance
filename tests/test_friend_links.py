"""Tests for friend links functionality"""
import pytest
from src.core.friend_links import FriendLinksModel


class TestFriendLinksModel:
    """Tests for the friend links model"""

    def test_create_empty_model(self):
        """Test creating empty model"""
        model = FriendLinksModel()
        assert len(model.get_links()) == 0

    def test_add_link(self):
        """Test adding a link"""
        model = FriendLinksModel()
        result = model.add_link("俄罗斯钓鱼4官网", "https://example.com/rf4")
        assert result is True
        assert len(model.get_links()) == 1
        link = model.get_links()[0]
        assert link["name"] == "俄罗斯钓鱼4官网"
        assert link["url"] == "https://example.com/rf4"

    def test_add_link_empty_name_returns_false(self):
        """Test adding link with empty name returns False"""
        model = FriendLinksModel()
        result = model.add_link("", "https://example.com")
        assert result is False

    def test_add_link_empty_url_returns_false(self):
        """Test adding link with empty url returns False"""
        model = FriendLinksModel()
        result = model.add_link("Test", "")
        assert result is False

    def test_remove_link(self):
        """Test removing a link"""
        model = FriendLinksModel()
        model.add_link("Link 1", "https://example.com/1")
        model.add_link("Link 2", "https://example.com/2")
        assert len(model.get_links()) == 2

        result = model.remove_link(0)
        assert result is True
        assert len(model.get_links()) == 1
        assert model.get_links()[0]["name"] == "Link 2"

    def test_update_link(self):
        """Test updating a link"""
        model = FriendLinksModel()
        model.add_link("Old Name", "https://old.com")

        result = model.update_link(0, "New Name", "https://new.com")
        assert result is True
        link = model.get_links()[0]
        assert link["name"] == "New Name"
        assert link["url"] == "https://new.com"

    def test_update_link_invalid_index_returns_false(self):
        """Test updating invalid index returns False"""
        model = FriendLinksModel()
        model.add_link("Test", "https://test.com")

        result = model.update_link(1, "New", "https://new.com")
        assert result is False

    def test_remove_link_invalid_index_returns_false(self):
        """Test removing invalid index returns False"""
        model = FriendLinksModel()
        model.add_link("Test", "https://test.com")

        result = model.remove_link(1)
        assert result is False

    def test_clear_all(self):
        """Test clearing all links"""
        model = FriendLinksModel()
        model.add_link("Link 1", "https://example.com/1")
        model.add_link("Link 2", "https://example.com/2")
        assert len(model.get_links()) == 2

        model.clear_all()
        assert len(model.get_links()) == 0

    def test_validate_url(self):
        """Test URL validation"""
        model = FriendLinksModel()
        # Should accept http and https
        assert model.validate_url("http://example.com") is True
        assert model.validate_url("https://example.com") is True
        # Should reject other protocols or empty
        assert model.validate_url("") is False
        assert model.validate_url("ftp://example.com") is False
        assert model.validate_url("example.com") is False

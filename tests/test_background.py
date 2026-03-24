"""Tests for background customization functionality"""
import pytest
import tempfile
import os
from src.core.background import BackgroundModel


class TestBackgroundModel:
    """Tests for the background model"""

    def test_create_default_model(self):
        """Test creating model with defaults"""
        model = BackgroundModel()
        settings = model.get_settings()
        assert settings["custom_image_path"] is None
        assert 0.0 <= settings["transparency"] <= 1.0
        # Default transparency should be reasonable
        assert settings["transparency"] == pytest.approx(0.8)

    def test_set_transparency(self):
        """Test setting transparency"""
        model = BackgroundModel()
        model.set_transparency(0.5)
        assert model.get_settings()["transparency"] == 0.5

    def test_transparency_clamped(self):
        """Test that transparency is clamped between 0 and 1"""
        model = BackgroundModel()
        model.set_transparency(-0.5)
        assert model.get_settings()["transparency"] == 0.0

        model.set_transparency(1.5)
        assert model.get_settings()["transparency"] == 1.0

    def test_set_custom_image(self):
        """Test setting custom image path"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'dummy')
            temp_path = f.name

        try:
            model = BackgroundModel()
            result = model.set_custom_image(temp_path)
            assert result is True
            assert model.get_settings()["custom_image_path"] == temp_path
        finally:
            os.unlink(temp_path)

    def test_set_custom_image_none_clears(self):
        """Test setting None clears custom image"""
        model = BackgroundModel()
        model.set_custom_image(None)
        assert model.get_settings()["custom_image_path"] is None

    def test_custom_image_not_exist_returns_false(self):
        """Test setting non-existent image returns False"""
        model = BackgroundModel()
        result = model.set_custom_image("/nonexistent/path/image.jpg")
        assert result is False

    def test_get_effective_opacity(self):
        """Test getting effective opacity for UI"""
        model = BackgroundModel()
        model.set_transparency(0.5)
        # Transparency of 0.8 means opacity 0.2
        # Wait: transparency 0 = fully transparent, 1 = fully opaque
        # So effective opacity is transparency value
        assert model.get_effective_opacity() == pytest.approx(0.5 * 255)

    def test_reset_to_default(self):
        """Test resetting to default settings"""
        model = BackgroundModel()
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name

        try:
            model.set_custom_image(temp_path)
            model.set_transparency(0.2)
            model.reset_to_default()

            settings = model.get_settings()
            assert settings["custom_image_path"] is None
            assert settings["transparency"] == pytest.approx(0.8)
        finally:
            os.unlink(temp_path)

    def test_has_custom_image(self):
        """Test has_custom_image returns correct bool"""
        model = BackgroundModel()
        assert not model.has_custom_image()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name

        try:
            model.set_custom_image(temp_path)
            assert model.has_custom_image()
        finally:
            os.unlink(temp_path)

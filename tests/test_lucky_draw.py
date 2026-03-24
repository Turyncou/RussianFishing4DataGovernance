"""Tests for lucky draw wheel functionality"""
import pytest
from src.ui.lucky_draw import LuckyDrawModel


class TestLuckyDrawModel:
    """Tests for the lucky draw model"""

    def test_create_empty_model(self):
        """Test creating empty model"""
        model = LuckyDrawModel()
        assert len(model.get_prizes()) == 0

    def test_add_prize(self):
        """Test adding a prize"""
        model = LuckyDrawModel()
        result = model.add_prize("一等奖", 0.05)
        assert result is True
        assert len(model.get_prizes()) == 1
        prize = model.get_prizes()[0]
        assert prize["name"] == "一等奖"
        assert prize["probability"] == 0.05

    def test_remove_prize(self):
        """Test removing a prize"""
        model = LuckyDrawModel()
        model.add_prize("一等奖", 0.05)
        model.add_prize("二等奖", 0.15)
        assert len(model.get_prizes()) == 2

        result = model.remove_prize(0)
        assert result is True
        assert len(model.get_prizes()) == 1
        assert model.get_prizes()[0]["name"] == "二等奖"

    def test_update_prize(self):
        """Test updating a prize"""
        model = LuckyDrawModel()
        model.add_prize("Old Name", 0.1)
        result = model.update_prize(0, "New Name", 0.2)
        assert result is True
        prize = model.get_prizes()[0]
        assert prize["name"] == "New Name"
        assert prize["probability"] == 0.2

    def test_total_probability_normalization(self):
        """Test that probabilities are normalized when they don't sum to 1"""
        model = LuckyDrawModel()
        model.add_prize("A", 1.0)
        model.add_prize("B", 1.0)
        # Total is 2.0, should normalize to 0.5 each
        prizes = model.get_prizes()
        total = sum(p["probability"] for p in prizes)
        assert abs(total - 1.0) < 0.001

    def test_spin_without_prizes(self):
        """Test spinning when there are no prizes returns None"""
        model = LuckyDrawModel()
        result = model.spin()
        assert result is None

    def test_spin_returns_prize(self):
        """Test spinning returns a prize"""
        model = LuckyDrawModel()
        model.add_prize("Test", 1.0)
        result = model.spin()
        assert result is not None
        assert result["name"] == "Test"

    def test_spin_distribution_statistics(self):
        """Test that spin distribution roughly matches probabilities"""
        model = LuckyDrawModel()
        model.add_prize("A", 0.5)
        model.add_prize("B", 0.5)

        counts = {"A": 0, "B": 0}
        n = 1000
        for _ in range(n):
            result = model.spin()
            counts[result["name"][0]] += 1

        # Should be roughly 50% each
        assert 400 < counts["A"] < 600
        assert 400 < counts["B"] < 600

    def test_get_angles_for_wheel(self):
        """Test that angles are calculated correctly based on probabilities"""
        model = LuckyDrawModel()
        model.add_prize("A", 0.25)
        model.add_prize("B", 0.25)
        model.add_prize("C", 0.5)
        angles = model.get_prize_angles()

        assert len(angles) == 3
        # 25% = 90 degrees, 25% = 90, 50% = 180
        assert abs(angles[0][1] - 90) < 0.1
        assert abs(angles[1][1] - 90) < 0.1
        assert abs(angles[2][1] - 180) < 0.1

    def test_validate_probabilities_valid(self):
        """Test validation with valid probabilities passes"""
        model = LuckyDrawModel()
        model.add_prize("A", 0.5)
        model.add_prize("B", 0.5)
        assert model.validate_probabilities() is True

    def test_clear_all_prizes(self):
        """Test clearing all prizes"""
        model = LuckyDrawModel()
        model.add_prize("A", 0.5)
        model.add_prize("B", 0.5)
        assert len(model.get_prizes()) == 2

        model.clear_all()
        assert len(model.get_prizes()) == 0

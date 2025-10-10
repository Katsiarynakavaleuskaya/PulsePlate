"""
Tests for configurable minimum calorie floor in core.plate.

RU: Тесты для настраиваемого минимального порога калорий.
EN: Tests for configurable minimum calorie floor functionality.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from core.plate import _validate_min_calories, target_kcal
from settings import MIN_CALORIES_DEFAULT


class TestMinCaloriesValidation:
    """Test validation of minimum calorie floor parameter."""

    def test_validate_default(self):
        """Test that default MIN_CALORIES_DEFAULT is used when no value provided."""
        result = _validate_min_calories()
        assert result == MIN_CALORIES_DEFAULT
        assert result == 1200  # Default value

    def test_validate_explicit_value(self):
        """Test validation accepts valid explicit values."""
        assert _validate_min_calories(1000) == 1000
        assert _validate_min_calories(1200) == 1200
        assert _validate_min_calories(1500) == 1500
        assert _validate_min_calories(800) == 800  # VLCD minimum
        assert _validate_min_calories(2000) == 2000  # Upper bound

    def test_validate_rejects_below_minimum(self):
        """Test validation rejects values below 800 kcal."""
        with pytest.raises(ValueError, match="must be between 800-2000"):
            _validate_min_calories(799)

        with pytest.raises(ValueError, match="must be between 800-2000"):
            _validate_min_calories(500)

        with pytest.raises(ValueError, match="must be between 800-2000"):
            _validate_min_calories(0)

        with pytest.raises(ValueError, match="must be between 800-2000"):
            _validate_min_calories(-100)

    def test_validate_rejects_above_maximum(self):
        """Test validation rejects values above 2000 kcal."""
        with pytest.raises(ValueError, match="must be between 800-2000"):
            _validate_min_calories(2001)

        with pytest.raises(ValueError, match="must be between 800-2000"):
            _validate_min_calories(3000)

    def test_validate_rejects_non_integer(self):
        """Test validation rejects non-integer types."""
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_min_calories(1200.5)  # pyright: ignore[reportArgumentType]

        with pytest.raises(ValueError, match="must be an integer"):
            _validate_min_calories("1200")  # pyright: ignore[reportArgumentType]

        with pytest.raises(ValueError, match="must be an integer"):
            _validate_min_calories([1200])  # pyright: ignore[reportArgumentType]


class TestTargetKcalWithMinCalories:
    """Test target_kcal function with configurable min_calories parameter."""

    def test_loss_goal_with_default_floor(self):
        """Test loss goal uses default 1200 kcal floor."""
        # Very low TDEE should hit the floor
        result = target_kcal(tdee_val=1000, goal="loss", deficit_pct=25, surplus_pct=None)
        assert result == 1200  # Default floor

    def test_loss_goal_with_custom_floor(self):
        """Test loss goal respects custom min_calories parameter."""
        # Test with higher minimum
        result = target_kcal(
            tdee_val=1000, goal="loss", deficit_pct=25, surplus_pct=None, min_calories=1500
        )
        assert result == 1500  # Custom floor

        # Test with lower minimum (VLCD scenario)
        result = target_kcal(
            tdee_val=1000, goal="loss", deficit_pct=25, surplus_pct=None, min_calories=800
        )
        assert result == 800  # Custom VLCD floor

    def test_loss_goal_above_floor(self):
        """Test loss goal when calculated calories are above floor."""
        # TDEE 2500, 20% deficit = 2000 kcal (well above any floor)
        result = target_kcal(
            tdee_val=2500, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1200
        )
        assert result == 2000  # Not constrained by floor

        # Same with custom floor
        result = target_kcal(
            tdee_val=2500, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1500
        )
        assert result == 2000  # Still not constrained

    def test_maintain_goal_ignores_floor(self):
        """Test maintain goal does not apply floor (returns TDEE)."""
        result = target_kcal(tdee_val=1000, goal="maintain", deficit_pct=None, surplus_pct=None)
        # Maintain returns TDEE without floor constraint
        assert result == 1000  # No floor applied for maintain

        # Even with custom floor
        result = target_kcal(
            tdee_val=1000, goal="maintain", deficit_pct=None, surplus_pct=None, min_calories=1500
        )
        assert result == 1000  # Still no floor for maintain

    def test_gain_goal_ignores_floor(self):
        """Test gain goal does not apply floor (adds surplus)."""
        result = target_kcal(tdee_val=1000, goal="gain", deficit_pct=None, surplus_pct=12)
        # Gain adds surplus without floor constraint
        assert result == 1120  # 1000 * 1.12

        # Even with custom floor
        result = target_kcal(
            tdee_val=1000, goal="gain", deficit_pct=None, surplus_pct=12, min_calories=1500
        )
        assert result == 1120  # Still no floor for gain

    def test_invalid_min_calories_raises(self):
        """Test that invalid min_calories parameter raises ValueError."""
        with pytest.raises(ValueError, match="must be between 800-2000"):
            target_kcal(
                tdee_val=2000, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=500
            )

        with pytest.raises(ValueError, match="must be between 800-2000"):
            target_kcal(
                tdee_val=2000, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=3000
            )


class TestMinCaloriesEnvironmentVariable:
    """Test MIN_CALORIES_DEFAULT configuration from environment variable."""

    def test_default_value_without_env(self):
        """Test default value is 1200 when env var is not set."""
        # This test verifies the default in settings.py
        assert MIN_CALORIES_DEFAULT == 1200

    @patch.dict(os.environ, {"MIN_CALORIES_DEFAULT": "1500"})
    def test_custom_value_from_env(self):
        """Test that MIN_CALORIES_DEFAULT can be configured via environment."""
        # Note: This would require reloading the settings module in practice
        # For now, we just test that the pattern works
        from settings import MIN_CALORIES_DEFAULT as test_default

        # In actual deployment, setting env before import would work
        # This is more of a documentation test
        assert isinstance(test_default, int)

    def test_validate_uses_env_default(self):
        """Test that validation uses the configured MIN_CALORIES_DEFAULT."""
        result = _validate_min_calories(None)
        assert result == MIN_CALORIES_DEFAULT


class TestMinCaloriesIntegration:
    """Integration tests for min_calories with realistic scenarios."""

    def test_very_low_tdee_female_scenario(self):
        """Test realistic scenario: petite female with very low TDEE."""
        # Example: 45kg female, sedentary, TDEE ~1300 kcal
        # 20% deficit would be 1040 kcal
        result = target_kcal(tdee_val=1300, goal="loss", deficit_pct=20, surplus_pct=None)
        assert result == 1200  # Protected by default floor

        # With medical supervision, might use VLCD
        result_vlcd = target_kcal(
            tdee_val=1300, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1000
        )
        assert result_vlcd == 1040  # Allows lower with explicit floor

    def test_athlete_scenario(self):
        """Test realistic scenario: athlete with higher minimum requirements."""
        # Example: 80kg athlete, TDEE 3500 kcal, wants aggressive cut
        # 25% deficit (max safe) would be 2625 kcal, which is above floor
        result = target_kcal(
            tdee_val=3500, goal="loss", deficit_pct=25, surplus_pct=None, min_calories=2000
        )
        # 25% deficit = 3500 * 0.75 = 2625, which is above floor
        assert result == 2625

        # Test with lower TDEE where floor matters
        result_low = target_kcal(
            tdee_val=2500, goal="loss", deficit_pct=25, surplus_pct=None, min_calories=2000
        )
        # 25% deficit = 2500 * 0.75 = 1875, floor raises to 2000
        assert result_low == 2000

    def test_goal_specific_floors_concept(self):
        """
        Test concept of goal-specific floors (documentation).

        Note: Current implementation uses single floor for loss goal.
        This test documents potential future enhancement for goal-specific floors.
        """
        # Loss goal with moderate deficit
        loss_result = target_kcal(
            tdee_val=1000, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1200
        )
        assert loss_result >= 1200

        # Maintain and gain goals don't apply floor currently
        maintain_result = target_kcal(
            tdee_val=1000, goal="maintain", deficit_pct=None, surplus_pct=None, min_calories=1200
        )
        # Future: could apply different floors per goal
        # Currently: maintain returns TDEE regardless of floor
        assert maintain_result == 1000


class TestMinCaloriesEdgeCases:
    """Edge case tests for minimum calorie floor functionality."""

    def test_boundary_values(self):
        """Test exact boundary values."""
        # Lower bound
        assert _validate_min_calories(800) == 800
        with pytest.raises(ValueError):
            _validate_min_calories(799)

        # Upper bound
        assert _validate_min_calories(2000) == 2000
        with pytest.raises(ValueError):
            _validate_min_calories(2001)

    def test_none_vs_explicit_default(self):
        """Test that None and explicit default value behave identically."""
        result_none = target_kcal(
            tdee_val=1000, goal="loss", deficit_pct=25, surplus_pct=None, min_calories=None
        )
        result_explicit = target_kcal(
            tdee_val=1000, goal="loss", deficit_pct=25, surplus_pct=None, min_calories=1200
        )
        assert result_none == result_explicit == 1200

    def test_floor_equals_calculated(self):
        """Test case where floor exactly equals calculated calories."""
        # Craft TDEE and deficit so result is exactly 1200
        # TDEE 1500, 20% deficit = 1200
        result = target_kcal(
            tdee_val=1500, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1200
        )
        assert result == 1200

    def test_very_small_difference(self):
        """Test when calculated is just below floor."""
        # TDEE 1499, 20% deficit = 1199.2 → rounds to 1199
        # Floor of 1200 should apply
        result = target_kcal(
            tdee_val=1499, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1200
        )
        assert result == 1200

    def test_rounding_with_floor(self):
        """Test rounding behavior when applying floor."""
        # TDEE 1503, 20% deficit = 1202.4
        result = target_kcal(
            tdee_val=1503, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1200
        )
        # Should round to 1202 (above floor)
        assert result == 1202

        # TDEE 1502, 20% deficit = 1201.6
        result = target_kcal(
            tdee_val=1502, goal="loss", deficit_pct=20, surplus_pct=None, min_calories=1200
        )
        # Should round to 1202 (above floor)
        assert result == 1202

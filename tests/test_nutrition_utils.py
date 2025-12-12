"""Tests for nutrition utility functions."""

import pytest

from core.nutrition_utils import (
    adjust_calories_for_goal,
    calculate_macro_grams,
    calculate_macro_percentages,
    calculate_protein_per_kg,
    calculate_water_intake_ml,
    detect_dietary_pattern,
    validate_macro_balance,
)


class TestCalculateMacroPercentages:
    """Test macro percentage calculations from grams."""

    def test_standard_macros(self) -> None:
        """Test calculation with standard macro amounts."""
        protein_pct, fat_pct, carbs_pct = calculate_macro_percentages(100, 50, 200)

        # Protein: 100g * 4 = 400 kcal
        # Fat: 50g * 9 = 450 kcal
        # Carbs: 200g * 4 = 800 kcal
        # Total: 1650 kcal
        assert protein_pct == 24.2  # 400/1650 * 100
        assert fat_pct == 27.3  # 450/1650 * 100
        assert carbs_pct == 48.5  # 800/1650 * 100

    def test_zero_macros(self) -> None:
        """Test with zero macro values."""
        protein_pct, fat_pct, carbs_pct = calculate_macro_percentages(0, 0, 0)

        assert protein_pct == 0.0
        assert fat_pct == 0.0
        assert carbs_pct == 0.0

    def test_high_protein_diet(self) -> None:
        """Test calculation for high protein diet."""
        protein_pct, fat_pct, carbs_pct = calculate_macro_percentages(150, 50, 100)

        # Should show protein dominance
        assert protein_pct > 30


class TestCalculateMacroGrams:
    """Test macro gram calculations from calories and percentages."""

    def test_standard_distribution(self) -> None:
        """Test calculation with standard macro distribution."""
        protein_g, fat_g, carbs_g = calculate_macro_grams(2000, 30, 25, 45)

        # Protein: 2000 * 0.30 / 4 = 150g
        # Fat: 2000 * 0.25 / 9 = 55.6g
        # Carbs: 2000 * 0.45 / 4 = 225g
        assert protein_g == 150.0
        assert fat_g == 55.6
        assert carbs_g == 225.0

    def test_percentages_sum_to_100(self) -> None:
        """Test that percentages must sum to ~100%."""
        # Should work with exact 100%
        protein_g, fat_g, carbs_g = calculate_macro_grams(2000, 40, 30, 30)
        assert protein_g > 0

        # Should work with 100.5% (within 1% tolerance)
        protein_g, fat_g, carbs_g = calculate_macro_grams(2000, 40.2, 30, 29.8)
        assert protein_g > 0

    def test_percentages_not_summing_to_100_raises_error(self) -> None:
        """Test that percentages not summing to 100% raises ValueError."""
        with pytest.raises(ValueError, match="must sum to 100%"):
            calculate_macro_grams(2000, 30, 25, 40)  # Sums to 95%


class TestValidateMacroBalance:
    """Test macronutrient balance validation."""

    def test_valid_balanced_diet(self) -> None:
        """Test validation of balanced diet within guidelines."""
        is_valid, msg = validate_macro_balance(30, 25, 45)
        assert is_valid
        assert msg == ""

    def test_protein_below_minimum(self) -> None:
        """Test rejection when protein below 10%."""
        is_valid, msg = validate_macro_balance(5, 30, 65)
        assert not is_valid
        assert "Protein" in msg
        assert "below minimum" in msg

    def test_protein_above_maximum(self) -> None:
        """Test rejection when protein above 35%."""
        is_valid, msg = validate_macro_balance(50, 25, 25)
        assert not is_valid
        assert "Protein" in msg
        assert "exceeds maximum" in msg

    def test_fat_below_minimum(self) -> None:
        """Test rejection when fat below 20%."""
        is_valid, msg = validate_macro_balance(30, 15, 55)
        assert not is_valid
        assert "Fat" in msg
        assert "below minimum" in msg

    def test_fat_above_maximum(self) -> None:
        """Test rejection when fat above 35%."""
        is_valid, msg = validate_macro_balance(20, 50, 30)
        assert not is_valid
        assert "Fat" in msg
        assert "exceeds maximum" in msg

    def test_carbs_below_minimum(self) -> None:
        """Test rejection when carbs below 45%."""
        is_valid, msg = validate_macro_balance(30, 30, 40)
        assert not is_valid
        assert "Carbs" in msg
        assert "below minimum" in msg

    def test_carbs_above_maximum(self) -> None:
        """Test rejection when carbs above 65%."""
        is_valid, msg = validate_macro_balance(10, 20, 70)
        assert not is_valid
        assert "Carbs" in msg
        assert "exceeds maximum" in msg

    def test_boundary_values_accepted(self) -> None:
        """Test that boundary values are accepted."""
        # Minimum protein (10%)
        is_valid, _ = validate_macro_balance(10, 25, 65)
        assert is_valid

        # Maximum protein (35%)
        is_valid, _ = validate_macro_balance(35, 20, 45)
        assert is_valid


class TestDetectDietaryPattern:
    """Test dietary pattern detection."""

    def test_ketogenic_diet(self) -> None:
        """Test detection of ketogenic diet."""
        pattern = detect_dietary_pattern(20, 75, 5)
        assert pattern == "ketogenic"

    def test_low_carb_diet(self) -> None:
        """Test detection of low-carb diet."""
        pattern = detect_dietary_pattern(30, 55, 15)
        assert pattern == "low_carb"

    def test_high_protein_diet(self) -> None:
        """Test detection of high protein diet."""
        pattern = detect_dietary_pattern(40, 30, 30)
        assert pattern == "high_protein"

    def test_low_fat_diet(self) -> None:
        """Test detection of low fat diet."""
        pattern = detect_dietary_pattern(25, 15, 60)
        assert pattern == "low_fat"

    def test_mediterranean_style(self) -> None:
        """Test detection of Mediterranean-style diet."""
        pattern = detect_dietary_pattern(20, 40, 40)
        assert pattern == "mediterranean"

    def test_zone_diet(self) -> None:
        """Test detection of Zone diet (30/30/40)."""
        pattern = detect_dietary_pattern(30, 30, 40)
        assert pattern == "zone"

    def test_standard_balanced_diet(self) -> None:
        """Test that standard balanced diet returns None."""
        pattern = detect_dietary_pattern(15, 30, 55)
        assert pattern is None


class TestCalculateProteinPerKg:
    """Test protein per kg body weight calculation."""

    def test_standard_intake(self) -> None:
        """Test calculation of standard protein intake."""
        protein_per_kg = calculate_protein_per_kg(150, 75)
        assert protein_per_kg == 2.0

    def test_lower_intake(self) -> None:
        """Test calculation of lower protein intake."""
        protein_per_kg = calculate_protein_per_kg(60, 75)
        assert protein_per_kg == 0.8

    def test_zero_body_weight_raises_error(self) -> None:
        """Test that zero body weight raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculate_protein_per_kg(150, 0)

    def test_negative_body_weight_raises_error(self) -> None:
        """Test that negative body weight raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculate_protein_per_kg(150, -75)


class TestAdjustCaloriesForGoal:
    """Test calorie adjustment for weight goals."""

    def test_maintain_goal(self) -> None:
        """Test that maintenance keeps calories unchanged."""
        adjusted = adjust_calories_for_goal(2000, "maintain")
        assert adjusted == 2000.0

    def test_lose_goal(self) -> None:
        """Test that lose/cut reduces calories by 500."""
        adjusted = adjust_calories_for_goal(2000, "lose")
        assert adjusted == 1500.0

        adjusted = adjust_calories_for_goal(2000, "cut")
        assert adjusted == 1500.0

    def test_gain_goal(self) -> None:
        """Test that gain/bulk increases calories by 500."""
        adjusted = adjust_calories_for_goal(2000, "gain")
        assert adjusted == 2500.0

        adjusted = adjust_calories_for_goal(2000, "bulk")
        assert adjusted == 2500.0

    def test_case_insensitive(self) -> None:
        """Test that goal is case-insensitive."""
        assert adjust_calories_for_goal(2000, "LOSE") == 1500.0
        assert adjust_calories_for_goal(2000, "Maintain") == 2000.0


class TestCalculateWaterIntakeMl:
    """Test water intake calculation."""

    def test_sedentary_activity(self) -> None:
        """Test water intake for sedentary activity."""
        water_ml = calculate_water_intake_ml(70, "sedentary")
        assert water_ml == 2100.0  # 70 * 30

    def test_moderate_activity(self) -> None:
        """Test water intake for moderate activity."""
        water_ml = calculate_water_intake_ml(70, "moderate")
        assert water_ml == 2415.0  # 70 * 30 * 1.15

    def test_active_activity(self) -> None:
        """Test water intake for active/very_active activity."""
        water_ml = calculate_water_intake_ml(70, "active")
        assert water_ml == 2730.0  # 70 * 30 * 1.30

        water_ml = calculate_water_intake_ml(70, "very_active")
        assert water_ml == 2730.0

    def test_zero_body_weight_raises_error(self) -> None:
        """Test that zero body weight raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculate_water_intake_ml(0, "moderate")

    def test_negative_body_weight_raises_error(self) -> None:
        """Test that negative body weight raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculate_water_intake_ml(-70, "moderate")

    def test_unknown_activity_uses_base(self) -> None:
        """Test that unknown activity level uses base calculation."""
        water_ml = calculate_water_intake_ml(70, "unknown")
        assert water_ml == 2100.0  # Base: 70 * 30

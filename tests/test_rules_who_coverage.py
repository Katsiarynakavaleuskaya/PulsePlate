"""
Additional tests to improve coverage for core/rules_who.py to reach 97%+.
"""

import pytest

from core.rules_who import (
    calculate_hydration_target,
    get_activity_guidelines,
    get_age_category,
    get_fiber_target,
    get_micronutrient_rda,
    get_priority_nutrients_for_profile,
    validate_macro_distribution,
)


class TestRulesWhoCoverage:
    """Additional tests to improve coverage for WHO rules."""

    def test_get_age_category_edge_cases(self):
        """Test get_age_category with edge cases."""
        # Test exactly 19 years (boundary)
        assert get_age_category(19) == "19-50"

        # Test exactly 50 years (boundary)
        assert get_age_category(50) == "19-50"

        # Test exactly 51 years (boundary)
        assert get_age_category(51) == "51+"

        # Test under 19
        assert get_age_category(18) == "under_19"

    def test_get_micronutrient_rda_fallback(self):
        """Test get_micronutrient_rda fallback behavior."""
        # Test with non-existent life stage - should fallback to adult
        result = get_micronutrient_rda("male", 30, "nonexistent")
        assert isinstance(result, dict)
        assert "iron_mg" in result

        # Test with completely unknown key - should fallback to default
        # We can't easily test this without patching since the function will always find a fallback

    def test_get_activity_guidelines_elderly(self):
        """Test get_activity_guidelines for elderly."""
        result = get_activity_guidelines(65)
        assert isinstance(result, dict)
        assert "moderate_aerobic_min" in result
        assert result["steps_daily"] == 7000

    def test_calculate_hydration_target_boundaries(self):
        """Test calculate_hydration_target with boundary values."""
        # Test minimum boundary
        result = calculate_hydration_target(10, "sedentary")  # 300ml, should be capped at 1500
        assert result == 1500

        # Test maximum boundary
        result = calculate_hydration_target(200, "very_active", "hot")  # Should be capped at 4000
        assert result == 4000

    def test_validate_macro_distribution_edge_cases(self):
        """Test validate_macro_distribution with edge cases."""
        # Test valid combinations
        assert validate_macro_distribution(20, 30, 50) is True   # Valid combination
        assert validate_macro_distribution(15, 25, 60) is True   # Valid combination

        # Test exact boundaries (must sum to 100)
        assert validate_macro_distribution(10, 25, 65) is True   # Exact minimums (10+25+65=100)
        assert validate_macro_distribution(35, 35, 30) is False  # Carbs too low (30 < 45)
        assert validate_macro_distribution(35, 35, 35) is False  # Sum not 100 (35+35+35=105)

        # Test out of range values
        assert validate_macro_distribution(9, 30, 61) is False   # Protein too low
        assert validate_macro_distribution(36, 30, 34) is False  # Protein too high
        assert validate_macro_distribution(20, 19, 61) is False  # Fat too low
        assert validate_macro_distribution(20, 36, 44) is False  # Fat too high
        assert validate_macro_distribution(20, 20, 44) is False  # Carbs too low
        assert validate_macro_distribution(20, 20, 66) is False  # Carbs too high

        # Test sum not equal to 100 (within 2% tolerance)
        assert validate_macro_distribution(20, 30, 50) is True   # Sum 100
        assert validate_macro_distribution(35, 35, 35) is False  # Sum 105, outside tolerance

    def test_get_fiber_target_various_calories(self):
        """Test get_fiber_target with various calorie values."""
        # Test with 2000 calories
        result = get_fiber_target(2000)
        assert result == 28  # 2000/1000 * 14 = 28

        # Test with 1500 calories
        result = get_fiber_target(1500)
        assert result == 21  # 1500/1000 * 14 = 21

    def test_get_priority_nutrients_for_profile_combinations(self):
        """Test get_priority_nutrients_for_profile with various combinations."""
        # Test elderly female
        result = get_priority_nutrients_for_profile("female", 70, set())
        assert isinstance(result, list)
        assert "b12_ug" in result  # Should include elderly priority
        assert "iron_mg" in result  # Should include global priority

        # Test reproductive age female
        result = get_priority_nutrients_for_profile("female", 30, set())
        assert "folate_ug" in result  # Should include women_reproductive priority

        # Test vegetarian male
        result = get_priority_nutrients_for_profile("male", 30, {"VEG"})
        assert "b12_ug" in result  # Should include vegetarian priority


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

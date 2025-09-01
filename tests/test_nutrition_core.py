"""
Comprehensive tests for nutrition_core module.

Tests cover BMR/TDEE calculations using:
- Unit tests for individual functions
- Property-based testing with Hypothesis
- Edge cases and boundary conditions
- Error handling and validation
"""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from nutrition_core import (
    PAL,
    bmr_harris,
    bmr_katch,
    bmr_mifflin,
    calculate_all_bmr,
    calculate_all_tdee,
    get_activity_descriptions,
    tdee,
)


class TestBMRMifflin:
    """Test Mifflin-St Jeor BMR calculation."""

    def test_male_calculation(self):
        """Test BMR calculation for males."""
        # Test case: 30-year-old male, 70kg, 175cm
        # Expected: 10*70 + 6.25*175 - 5*30 + 5 = 700 + 1093.75 - 150 + 5 = 1648.75
        result = bmr_mifflin(70, 175, 30, "male")
        assert result == 1648.8  # Rounded to 1 decimal

    def test_female_calculation(self):
        """Test BMR calculation for females."""
        # Test case: 25-year-old female, 60kg, 165cm
        # Expected: 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
        result = bmr_mifflin(60, 165, 25, "female")
        assert result == 1345.2  # Rounded to 1 decimal

    def test_validation_errors(self):
        """Test input validation."""
        with pytest.raises(ValueError, match="Weight, height, and age must be positive"):
            bmr_mifflin(0, 170, 30, "male")

        with pytest.raises(ValueError, match="Weight, height, and age must be positive"):
            bmr_mifflin(70, 0, 30, "male")

        with pytest.raises(ValueError, match="Weight, height, and age must be positive"):
            bmr_mifflin(70, 170, 0, "male")

        with pytest.raises(ValueError, match="Age must be realistic"):
            bmr_mifflin(70, 170, 150, "male")

    @given(
        weight=st.floats(min_value=30, max_value=200),
        height=st.floats(min_value=120, max_value=250),
        age=st.integers(min_value=1, max_value=120),
        sex=st.sampled_from(["male", "female"])
    )
    def test_mifflin_property_based(self, weight, height, age, sex):
        """Property-based test for Mifflin formula."""
        result = bmr_mifflin(weight, height, age, sex)
        assert isinstance(result, float)
        assert result > 0  # BMR should always be positive
        assert result < 5000  # Reasonable upper bound


class TestBMRHarris:
    """Test Harris-Benedict BMR calculation."""

    def test_male_calculation(self):
        """Test BMR calculation for males using Harris-Benedict."""
        # Test case: 30-year-old male, 70kg, 175cm
        # Expected: 66.5 + 13.75*70 + 5.003*175 - 6.755*30
        result = bmr_harris(70, 175, 30, "male")
        expected = 66.5 + 13.75*70 + 5.003*175 - 6.755*30
        assert abs(result - round(expected, 1)) < 0.1

    def test_female_calculation(self):
        """Test BMR calculation for females using Harris-Benedict."""
        # Test case: 25-year-old female, 60kg, 165cm
        result = bmr_harris(60, 165, 25, "female")
        expected = 655.1 + 9.563*60 + 1.850*165 - 4.676*25
        assert abs(result - round(expected, 1)) < 0.1

    @given(
        weight=st.floats(min_value=30, max_value=200),
        height=st.floats(min_value=120, max_value=250),
        age=st.integers(min_value=1, max_value=120),
        sex=st.sampled_from(["male", "female"])
    )
    def test_harris_property_based(self, weight, height, age, sex):
        """Property-based test for Harris-Benedict formula."""
        result = bmr_harris(weight, height, age, sex)
        assert isinstance(result, float)
        assert result > 0
        assert result < 5000

    def test_harris_age_validation(self):
        """Test Harris-Benedict age validation."""
        with pytest.raises(ValueError, match="Age must be realistic"):
            bmr_harris(70, 175, 150, "male")

    def test_harris_validation_errors(self):
        """Test Harris-Benedict input validation."""
        with pytest.raises(ValueError, match="Weight, height, and age must be positive values"):
            bmr_harris(0, 175, 30, "male")

        with pytest.raises(ValueError, match="Weight, height, and age must be positive values"):
            bmr_harris(70, 0, 30, "male")

        with pytest.raises(ValueError, match="Weight, height, and age must be positive values"):
            bmr_harris(70, 175, 0, "male")


class TestBMRKatch:
    """Test Katch-McArdle BMR calculation."""

    def test_katch_calculation(self):
        """Test BMR calculation using Katch-McArdle formula."""
        # Test case: 70kg with 15% body fat
        # Lean mass = 70 * (1 - 0.15) = 59.5kg
        # BMR = 370 + 21.6 * 59.5 = 370 + 1285.2 = 1655.2
        result = bmr_katch(70, 15)
        assert result == 1655.2

    def test_katch_validation(self):
        """Test Katch-McArdle validation."""
        with pytest.raises(ValueError, match="Weight must be a positive value"):
            bmr_katch(0, 15)

        with pytest.raises(ValueError, match="Body fat percentage must be between 0 and 50"):
            bmr_katch(70, -5)

        with pytest.raises(ValueError, match="Body fat percentage must be between 0 and 50"):
            bmr_katch(70, 60)

    @given(
        weight=st.floats(min_value=30, max_value=200),
        bodyfat=st.floats(min_value=5, max_value=50)
    )
    def test_katch_property_based(self, weight, bodyfat):
        """Property-based test for Katch-McArdle formula."""
        result = bmr_katch(weight, bodyfat)
        assert isinstance(result, float)
        assert result > 0
        assert result < 5000


class TestTDEE:
    """Test TDEE calculation."""

    def test_tdee_calculation(self):
        """Test TDEE calculation with different activity levels."""
        bmr = 1500.0

        # Test all activity levels
        assert tdee(bmr, "sedentary") == 1800.0  # 1500 * 1.2
        assert tdee(bmr, "light") == 2062.0      # 1500 * 1.375
        assert tdee(bmr, "moderate") == 2325.0   # 1500 * 1.55
        assert tdee(bmr, "active") == 2588.0     # 1500 * 1.725
        assert tdee(bmr, "very_active") == 2850.0 # 1500 * 1.9

    def test_tdee_validation(self):
        """Test TDEE validation."""
        with pytest.raises(ValueError, match="BMR must be a positive value"):
            tdee(0, "moderate")

        with pytest.raises(ValueError, match="Activity level must be one of"):
            tdee(1500, "invalid_activity")  # type: ignore

    @given(
        bmr=st.floats(min_value=800, max_value=4000),
        activity=st.sampled_from(list(PAL.keys()))
    )
    def test_tdee_property_based(self, bmr, activity):
        """Property-based test for TDEE calculation."""
        result = tdee(bmr, activity)
        assert isinstance(result, float)
        assert result >= bmr  # TDEE should be at least BMR
        assert result <= bmr * 2.5  # Reasonable upper bound


class TestCalculateAllBMR:
    """Test combined BMR calculations."""

    def test_calculate_all_bmr_without_bodyfat(self):
        """Test BMR calculation without body fat percentage."""
        results = calculate_all_bmr(70, 175, 30, "male")

        assert "mifflin" in results
        assert "harris" in results
        assert "katch" not in results

        assert isinstance(results["mifflin"], float)
        assert isinstance(results["harris"], float)
        assert results["mifflin"] > 0
        assert results["harris"] > 0

    def test_calculate_all_bmr_with_bodyfat(self):
        """Test BMR calculation with body fat percentage."""
        results = calculate_all_bmr(70, 175, 30, "male", 15)

        assert "mifflin" in results
        assert "harris" in results
        assert "katch" in results

        assert isinstance(results["katch"], float)
        assert results["katch"] > 0

    @given(
        weight=st.floats(min_value=40, max_value=150),
        height=st.floats(min_value=140, max_value=220),
        age=st.integers(min_value=18, max_value=80),
        sex=st.sampled_from(["male", "female"]),
        bodyfat=st.one_of(st.none(), st.floats(min_value=5, max_value=40))
    )
    def test_calculate_all_bmr_property_based(self, weight, height, age, sex, bodyfat):
        """Property-based test for combined BMR calculation."""
        results = calculate_all_bmr(weight, height, age, sex, bodyfat)

        assert isinstance(results, dict)
        assert "mifflin" in results
        assert "harris" in results

        if bodyfat is not None:
            assert "katch" in results
            assert results["katch"] > 0
        else:
            assert "katch" not in results


class TestCalculateAllTDEE:
    """Test combined TDEE calculations."""

    def test_calculate_all_tdee(self):
        """Test TDEE calculation for all BMR formulas."""
        bmr_results = {"mifflin": 1650.0, "harris": 1700.0, "katch": 1625.0}
        tdee_results = calculate_all_tdee(bmr_results, "moderate")

        assert len(tdee_results) == 3
        assert "mifflin" in tdee_results
        assert "harris" in tdee_results
        assert "katch" in tdee_results

        # Check calculations
        assert tdee_results["mifflin"] == 2558.0  # 1650 * 1.55
        assert tdee_results["harris"] == 2635.0   # 1700 * 1.55
        assert tdee_results["katch"] == 2519.0    # 1625 * 1.55


class TestActivityDescriptions:
    """Test activity level descriptions."""

    def test_get_activity_descriptions(self):
        """Test activity descriptions function."""
        descriptions = get_activity_descriptions()

        assert isinstance(descriptions, dict)
        assert len(descriptions) == 5

        expected_keys = ["sedentary", "light", "moderate", "active", "very_active"]
        for key in expected_keys:
            assert key in descriptions
            assert isinstance(descriptions[key], str)
            assert len(descriptions[key]) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimal_values(self):
        """Test with minimal valid values."""
        # Smallest reasonable person
        result = bmr_mifflin(30, 120, 1, "female")
        assert result > 0

    def test_maximal_values(self):
        """Test with maximal valid values."""
        # Largest reasonable person
        result = bmr_mifflin(200, 250, 120, "male")
        assert result > 0
        assert result < 5000

    def test_young_vs_old(self):
        """Test age impact on BMR."""
        young_bmr = bmr_mifflin(70, 175, 20, "male")
        old_bmr = bmr_mifflin(70, 175, 80, "male")

        # Older people should have lower BMR
        assert young_bmr > old_bmr

    def test_male_vs_female(self):
        """Test sex impact on BMR."""
        male_bmr = bmr_mifflin(70, 175, 30, "male")
        female_bmr = bmr_mifflin(70, 175, 30, "female")

        # Males should have higher BMR
        assert male_bmr > female_bmr

    def test_weight_impact(self):
        """Test weight impact on BMR."""
        light_bmr = bmr_mifflin(50, 175, 30, "male")
        heavy_bmr = bmr_mifflin(90, 175, 30, "male")

        # Heavier people should have higher BMR
        assert heavy_bmr > light_bmr

    def test_height_impact(self):
        """Test height impact on BMR."""
        short_bmr = bmr_mifflin(70, 150, 30, "male")
        tall_bmr = bmr_mifflin(70, 200, 30, "male")

        # Taller people should have higher BMR
        assert tall_bmr > short_bmr


class TestFormulasConsistency:
    """Test consistency between different BMR formulas."""

    def test_formulas_reasonable_difference(self):
        """Test that different BMR formulas give reasonably close results."""
        weight, height, age, sex = 70, 175, 30, "male"

        mifflin = bmr_mifflin(weight, height, age, sex)
        harris = bmr_harris(weight, height, age, sex)

        # Results should be within 20% of each other
        difference_percent = abs(mifflin - harris) / mifflin * 100
        assert difference_percent < 20

    def test_katch_with_average_bodyfat(self):
        """Test Katch-McArdle with average body fat percentages."""
        weight = 70

        # Average body fat for males: ~15%, females: ~25%
        male_katch = bmr_katch(weight, 15)
        female_katch = bmr_katch(weight, 25)

        # Male with lower body fat should have higher BMR
        assert male_katch > female_katch


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow(self):
        """Test complete BMR/TDEE calculation workflow."""
        # Calculate all BMR values
        bmr_results = calculate_all_bmr(70, 175, 30, "male", 15)

        # Calculate all TDEE values
        tdee_results = calculate_all_tdee(bmr_results, "moderate")

        # Verify workflow
        assert len(bmr_results) == 3  # mifflin, harris, katch
        assert len(tdee_results) == 3

        # All TDEE values should be higher than BMR
        for formula in bmr_results:
            assert tdee_results[formula] > bmr_results[formula]

    def test_activity_level_ordering(self):
        """Test that higher activity levels give higher TDEE."""
        bmr = 1500.0

        sedentary_tdee = tdee(bmr, "sedentary")
        light_tdee = tdee(bmr, "light")
        moderate_tdee = tdee(bmr, "moderate")
        active_tdee = tdee(bmr, "active")
        very_active_tdee = tdee(bmr, "very_active")

        # Should be in ascending order
        activity_levels = [sedentary_tdee, light_tdee, moderate_tdee, active_tdee, very_active_tdee]
        assert activity_levels == sorted(activity_levels)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

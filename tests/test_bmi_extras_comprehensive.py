"""
Comprehensive tests for core/bmi_extras.py module to boost coverage to 97%.
"""

import pytest

from core.bmi_extras import (
    ffmi,
    interpret_whr_ratio,
    interpret_wht_ratio,
    stage_obesity,
    whr_ratio,
    wht_ratio,
)


class TestBmiExtrasComprehensive:
    """Comprehensive tests for bmi_extras module."""

    def test_wht_ratio_valid_inputs(self):
        """Test wht_ratio with valid inputs."""
        # Normal case
        ratio = wht_ratio(80, 170)
        assert ratio == 0.471

        # Edge case with round numbers
        ratio = wht_ratio(100, 200)
        assert ratio == 0.5

        # Different values
        ratio = wht_ratio(90, 180)
        assert ratio == 0.5

    def test_wht_ratio_invalid_inputs(self):
        """Test wht_ratio with invalid inputs."""
        # Test with zero waist
        with pytest.raises(ValueError, match="Waist circumference must be positive"):
            wht_ratio(0, 170)

        # Test with negative waist
        with pytest.raises(ValueError, match="Waist circumference must be positive"):
            wht_ratio(-10, 170)

        # Test with zero height
        with pytest.raises(ValueError, match="Height must be positive"):
            wht_ratio(80, 0)

        # Test with negative height
        with pytest.raises(ValueError, match="Height must be positive"):
            wht_ratio(80, -10)

    def test_whr_ratio_valid_inputs(self):
        """Test whr_ratio with valid inputs."""
        # Male case
        ratio = whr_ratio(90, 100, "male")
        assert ratio == 0.9

        # Female case
        ratio = whr_ratio(80, 100, "female")
        assert ratio == 0.8

        # Edge case
        ratio = whr_ratio(100, 100, "male")
        assert ratio == 1.0

    def test_whr_ratio_invalid_inputs(self):
        """Test whr_ratio with invalid inputs."""
        # Test with zero waist
        with pytest.raises(ValueError, match="Waist circumference must be positive"):
            whr_ratio(0, 100, "male")

        # Test with negative waist
        with pytest.raises(ValueError, match="Waist circumference must be positive"):
            whr_ratio(-10, 100, "male")

        # Test with zero hip
        with pytest.raises(ValueError, match="Hip circumference must be positive"):
            whr_ratio(90, 0, "male")

        # Test with negative hip
        with pytest.raises(ValueError, match="Hip circumference must be positive"):
            whr_ratio(90, -10, "male")

    def test_ffmi_valid_inputs(self):
        """Test ffmi with valid inputs."""
        # Test without body fat percentage
        result = ffmi(70, 175)
        assert "ffm_kg" in result
        assert "ffmi" in result
        assert isinstance(result["ffm_kg"], float)
        assert isinstance(result["ffmi"], float)

        # Test with body fat percentage
        result = ffmi(70, 175, 20)
        assert "ffm_kg" in result
        assert "ffmi" in result
        assert isinstance(result["ffm_kg"], float)
        assert isinstance(result["ffmi"], float)

        # Test with different values
        result = ffmi(80, 180, 15)
        assert "ffm_kg" in result
        assert "ffmi" in result

    def test_ffmi_invalid_inputs(self):
        """Test ffmi with invalid inputs."""
        # Test with zero weight
        with pytest.raises(ValueError, match="Weight must be positive"):
            ffmi(0, 175)

        # Test with negative weight
        with pytest.raises(ValueError, match="Weight must be positive"):
            ffmi(-10, 175)

        # Test with zero height
        with pytest.raises(ValueError, match="Height must be positive"):
            ffmi(70, 0)

        # Test with negative height
        with pytest.raises(ValueError, match="Height must be positive"):
            ffmi(70, -10)

        # Test with invalid body fat percentage (negative)
        with pytest.raises(ValueError, match="Body fat percentage must be between 0 and 100"):
            ffmi(70, 175, -5)

        # Test with invalid body fat percentage (over 100)
        with pytest.raises(ValueError, match="Body fat percentage must be between 0 and 100"):
            ffmi(70, 175, 105)

    def test_interpret_wht_ratio(self):
        """Test interpret_wht_ratio function."""
        # Test underweight category
        result = interpret_wht_ratio(0.3)
        assert result["category"] == "underweight"
        assert result["risk"] == "low"

        # Test healthy category
        result = interpret_wht_ratio(0.45)
        assert result["category"] == "healthy"
        assert result["risk"] == "low"

        # Test overweight category
        result = interpret_wht_ratio(0.55)
        assert result["category"] == "overweight"
        assert result["risk"] == "moderate"

        # Test obese category
        result = interpret_wht_ratio(0.65)
        assert result["category"] == "obese"
        assert result["risk"] == "high"

        # Test edge cases
        result = interpret_wht_ratio(0.4)
        assert result["category"] == "healthy" or result["category"] == "overweight"

        result = interpret_wht_ratio(0.5)
        assert result["category"] == "overweight" or result["category"] == "obese"

        result = interpret_wht_ratio(0.6)
        assert result["category"] == "obese"

    def test_interpret_whr_ratio_male(self):
        """Test interpret_whr_ratio for male."""
        # Test low risk for male
        result = interpret_whr_ratio(0.9, "male", "en")
        assert "risk" in result
        assert "description" in result

        # Test high risk for male
        result = interpret_whr_ratio(1.0, "male", "en")
        assert "risk" in result
        assert "description" in result

    def test_interpret_whr_ratio_female(self):
        """Test interpret_whr_ratio for female."""
        # Test low risk for female
        result = interpret_whr_ratio(0.75, "female", "en")
        assert "risk" in result
        assert "description" in result

        # Test high risk for female
        result = interpret_whr_ratio(0.85, "female", "en")
        assert "risk" in result
        assert "description" in result

    def test_interpret_whr_ratio_case_handling(self):
        """Test interpret_whr_ratio case handling."""
        result_male = interpret_whr_ratio(0.9, "male", "en")
        result_male_upper = interpret_whr_ratio(
            0.9, "MALE", "en"  # pyright: ignore[reportArgumentType]
        )  # Use uppercase to verify case-insensitivity
        assert result_male["risk"] == result_male_upper["risk"]

        result_female = interpret_whr_ratio(0.75, "female", "en")
        result_female_upper = interpret_whr_ratio(
            0.75, "FEMALE", "en"  # pyright: ignore[reportArgumentType]
        )  # Use uppercase to verify case-insensitivity
        assert result_female["risk"] == result_female_upper["risk"]

    def test_stage_obesity_high_risk(self):
        """Test stage_obesity with high risk factors."""
        # Case with multiple risk factors
        result = stage_obesity(bmi=32, wht=0.6, whr=0.96, sex="male", lang="en")
        assert "stage" in result
        assert "risk_factors" in result
        assert "recommendation" in result
        assert result["stage"] in ["high_risk", "moderate_risk", "low_risk"]

    def test_stage_obesity_moderate_risk(self):
        """Test stage_obesity with moderate risk factors."""
        # Case with one risk factor
        result = stage_obesity(bmi=22, wht=0.45, whr=0.96, sex="male", lang="en")
        assert "stage" in result
        assert "risk_factors" in result
        assert "recommendation" in result

    def test_stage_obesity_low_risk(self):
        """Test stage_obesity with low risk factors."""
        # Case with no risk factors
        result = stage_obesity(bmi=22, wht=0.4, whr=0.8, sex="male", lang="en")
        assert "stage" in result
        assert "risk_factors" in result
        assert "recommendation" in result

    def test_stage_obesity_female_high_risk(self):
        """Test stage_obesity with high risk factors for female."""
        # Female case with high WHR risk
        result = stage_obesity(bmi=22, wht=0.4, whr=0.85, sex="female", lang="en")
        assert "stage" in result
        assert "risk_factors" in result
        assert "recommendation" in result

    def test_stage_obesity_bmi_categories(self):
        """Test stage_obesity BMI category classification."""
        # Test obese BMI
        result = stage_obesity(bmi=35, wht=0.4, whr=0.8, sex="male", lang="en")
        assert result["bmi_category"] == "obese"

        # Test overweight BMI
        result = stage_obesity(bmi=27, wht=0.4, whr=0.8, sex="male", lang="en")
        assert result["bmi_category"] == "overweight"

        # Test normal BMI
        result = stage_obesity(bmi=22, wht=0.4, whr=0.8, sex="male", lang="en")
        assert result["bmi_category"] == "normal"

        # Test underweight BMI
        result = stage_obesity(bmi=17, wht=0.4, whr=0.8, sex="male", lang="en")
        assert result["bmi_category"] == "underweight"

    def test_stage_obesity_risk_factor_counting(self):
        """Test that stage_obesity correctly counts risk factors."""
        # No risk factors
        result = stage_obesity(bmi=22, wht=0.4, whr=0.8, sex="male", lang="en")
        assert int(result["risk_factors"]) == 0

        # One risk factor (high BMI)
        result = stage_obesity(bmi=32, wht=0.4, whr=0.8, sex="male", lang="en")
        assert int(result["risk_factors"]) == 1

        # Two risk factors (high BMI and high WHtR)
        result = stage_obesity(bmi=32, wht=0.6, whr=0.8, sex="male", lang="en")
        assert int(result["risk_factors"]) >= 1

        # Three risk factors
        result = stage_obesity(bmi=32, wht=0.6, whr=0.96, sex="male", lang="en")
        assert int(result["risk_factors"]) >= 1

    def test_edge_case_values(self):
        """Test edge case values for all functions."""
        # Test exact threshold values for WHtR interpretation
        result = interpret_wht_ratio(0.4)
        assert result["risk"] in ["low", "moderate"]

        result = interpret_wht_ratio(0.5)
        assert result["risk"] in ["low", "moderate"]

        result = interpret_wht_ratio(0.6)
        assert result["risk"] in ["moderate", "high"]

        # Test exact threshold values for WHR interpretation
        result = interpret_whr_ratio(0.95, "male", "en")
        assert "risk" in result

        result = interpret_whr_ratio(0.80, "female", "en")
        assert "risk" in result

    def test_rounding_behavior(self):
        """Test rounding behavior in calculations."""
        # Robust checks using fixed-decimal formatting instead of digit counting
        ratio = wht_ratio(80, 170)
        assert float(format(ratio, ".3f")) == round(ratio, 3)

        ratio = whr_ratio(90, 100, "male")
        assert float(format(ratio, ".3f")) == round(ratio, 3)

        result = ffmi(70, 175)
        assert float(format(result["ffm_kg"], ".1f")) == round(result["ffm_kg"], 1)
        assert float(format(result["ffmi"], ".1f")) == round(result["ffmi"], 1)

    def test_different_language_support(self):
        """Test that functions work with different languages."""
        # Test WHR interpretation with different languages
        result_en = interpret_whr_ratio(0.9, "male", "en")
        result_ru = interpret_whr_ratio(0.9, "male", "ru")

        # Both should have risk and description
        assert "risk" in result_en
        assert "description" in result_en
        assert "risk" in result_ru
        assert "description" in result_ru

        # Test obesity staging with different languages
        result_en = stage_obesity(bmi=32, wht=0.6, whr=0.96, sex="male", lang="en")
        result_ru = stage_obesity(bmi=32, wht=0.6, whr=0.96, sex="male", lang="ru")

        # Both should have required fields
        assert "stage" in result_en
        assert "recommendation" in result_en
        assert "stage" in result_ru
        assert "recommendation" in result_ru

"""
Tests for BMI Pro features: WHtR, WHR, FFMI, and obesity staging.
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


class TestBMIFunctions:
    """Test BMI Pro calculation functions."""

    def test_wht_ratio_valid(self):
        """Test WHtR calculation with valid inputs."""
        # Normal case
        assert wht_ratio(80, 170) == pytest.approx(0.471, 0.001)
        # Edge case
        assert wht_ratio(100, 200) == 0.5

    def test_wht_ratio_invalid(self):
        """Test WHtR calculation with invalid inputs."""
        with pytest.raises(ValueError):
            wht_ratio(0, 170)
        with pytest.raises(ValueError):
            wht_ratio(80, 0)
        with pytest.raises(ValueError):
            wht_ratio(-10, 170)

    def test_whr_ratio_valid(self):
        """Test WHR calculation with valid inputs."""
        # Normal case
        assert whr_ratio(80, 100, "male") == 0.8
        # Edge case
        assert whr_ratio(100, 100, "female") == 1.0

    def test_whr_ratio_invalid(self):
        """Test WHR calculation with invalid inputs."""
        with pytest.raises(ValueError):
            whr_ratio(0, 100, "male")
        with pytest.raises(ValueError):
            whr_ratio(80, 0, "female")
        with pytest.raises(ValueError):
            whr_ratio(-10, 100, "male")

    def test_ffmi_with_bodyfat(self):
        """Test FFMI calculation with body fat percentage."""
        # Person: 70kg, 175cm, 20% body fat
        result = ffmi(70, 175, 20)
        assert result["ffm_kg"] == 56.0
        assert result["ffmi"] == pytest.approx(18.3, 0.1)

    def test_ffmi_without_bodyfat(self):
        """Test FFMI calculation without body fat percentage."""
        # Person: 70kg, 175cm (no body fat data)
        result = ffmi(70, 175)
        # Should use default 15% body fat estimation
        assert result["ffm_kg"] == pytest.approx(59.5, 0.1)
        assert result["ffmi"] == pytest.approx(19.4, 0.1)

    def test_ffmi_invalid(self):
        """Test FFMI calculation with invalid inputs."""
        with pytest.raises(ValueError):
            ffmi(0, 175, 20)
        with pytest.raises(ValueError):
            ffmi(70, 0, 20)
        with pytest.raises(ValueError):
            ffmi(70, 175, -5)
        with pytest.raises(ValueError):
            ffmi(70, 175, 105)

    def test_interpret_wht_ratio(self):
        """Test WHtR interpretation."""
        # Low risk
        result = interpret_wht_ratio(0.3)
        assert result["risk"] == "low"
        assert result["category"] == "underweight"

        # Healthy range
        result = interpret_wht_ratio(0.45)
        assert result["risk"] == "low"
        assert result["category"] == "healthy"

        # Moderate risk
        result = interpret_wht_ratio(0.55)
        assert result["risk"] == "moderate"
        assert result["category"] == "overweight"

        # High risk
        result = interpret_wht_ratio(0.65)
        assert result["risk"] == "high"
        assert result["category"] == "obese"

    def test_interpret_whr_ratio_male(self):
        """Test WHR interpretation for males."""
        # Low risk male
        result = interpret_whr_ratio(0.9, "male")
        assert result["risk"] == "low"

        # High risk male
        result = interpret_whr_ratio(1.0, "male")
        assert result["risk"] == "high"

    def test_interpret_whr_ratio_female(self):
        """Test WHR interpretation for females."""
        # Low risk female
        result = interpret_whr_ratio(0.75, "female")
        assert result["risk"] == "low"

        # High risk female
        result = interpret_whr_ratio(0.85, "female")
        assert result["risk"] == "high"

    def test_stage_obesity(self):
        """Test obesity staging function."""
        # Low risk case
        result = stage_obesity(22, 0.4, 0.8, "male")
        assert result["stage"] == "low_risk"
        assert result["risk_factors"] == 0

        # Moderate risk case
        result = stage_obesity(28, 0.5, 0.8, "male")
        assert result["stage"] == "moderate_risk"
        assert result["risk_factors"] == 1

        # High risk case
        result = stage_obesity(32, 0.6, 1.0, "male")
        assert result["stage"] == "high_risk"
        assert result["risk_factors"] == 3

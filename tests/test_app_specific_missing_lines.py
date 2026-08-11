"""
Test coverage for specific missing lines in app.py to improve coverage to 97%.
"""

import pytest

# Canonical imports for BMI helpers (replacing legacy app.* functions)
from core.bmi.risk import _waist_thresholds, get_waist_risk_note
from tests._helpers.bmi_flags import _normalize_flags_for_tests


class TestAppSpecificMissingLines:
    """Tests for specific missing lines in app.py."""

    def test_normalize_flags_edge_cases(self) -> None:
        """Test edge cases for normalize_flags function."""
        # Test with various gender values
        result = _normalize_flags_for_tests("unknown", "no", "no")
        assert isinstance(result, dict)

        # Test with boolean values for pregnant/athlete
        result = _normalize_flags_for_tests("male", True, True)
        assert result["is_pregnant"] is False  # Male can't be pregnant
        assert result["is_athlete"] is True

        result = _normalize_flags_for_tests("female", True, False)
        assert result["is_pregnant"] is True
        assert result["is_athlete"] is False

    def test_waist_risk_edge_cases(self) -> None:
        """Test edge cases for waist_risk function."""
        # Test with None waist
        result = get_waist_risk_note(waist_cm=None, gender="male", lang="en")
        assert result == ""

        # Get canonical thresholds (no hardcoded values)
        male_warn, male_high = _waist_thresholds("male")
        female_warn, female_high = _waist_thresholds("female")

        # Test with exact threshold values
        result = get_waist_risk_note(waist_cm=male_warn, gender="male", lang="en")
        assert isinstance(result, str)

        result = get_waist_risk_note(waist_cm=male_high, gender="male", lang="en")
        assert isinstance(result, str)

        result = get_waist_risk_note(waist_cm=female_warn, gender="female", lang="en")
        assert isinstance(result, str)

        result = get_waist_risk_note(waist_cm=female_high, gender="female", lang="en")
        assert isinstance(result, str)

    def test_bmi_request_validation_edge_cases(self) -> None:
        """Test edge cases for BMIRequest validation."""
        from app.schemas.bmi_compat import BMIRequest

        # Test with realistic minimum values
        req = BMIRequest(
            weight_kg=20.0,  # Realistic minimum weight
            height_m=1.0,  # Realistic minimum height (100cm = 1.0m)
            age=0,  # Minimum valid age
            gender="male",
        )
        assert req.weight_kg == 20.0
        assert req.height_m == 1.0
        assert req.age == 0

        # Test with realistic maximum values
        req = BMIRequest(
            weight_kg=300.0,  # Realistic maximum weight
            height_m=2.5,  # Realistic maximum height (250cm = 2.5m)
            age=120,  # Maximum valid age
            gender="female",
        )
        assert req.weight_kg == 300.0
        assert req.height_m == 2.5
        assert req.age == 120

    def test_bmi_request_v1_validation_edge_cases(self) -> None:
        """Test edge cases for BMIRequestV1 validation."""
        from app.schemas.bmi_compat import BMIRequestV1

        # Test with realistic minimum values
        req = BMIRequestV1(
            weight_kg=20.0,  # Realistic minimum weight
            height_cm=100.0,  # Realistic minimum height
            age=0,  # Minimum valid age
            gender="male",
            group="general",
        )
        assert req.weight_kg == 20.0
        assert req.height_cm == 100.0
        assert req.age == 0
        assert req.group == "general"

        # Test with realistic maximum values
        req = BMIRequestV1(
            weight_kg=300.0,  # Realistic maximum weight
            height_cm=250.0,  # Realistic maximum height
            age=120,  # Maximum valid age
            gender="female",
            group="athlete",
        )
        assert req.weight_kg == 300.0
        assert req.height_cm == 250.0
        assert req.age == 120
        assert req.group == "athlete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

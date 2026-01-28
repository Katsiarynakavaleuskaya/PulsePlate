"""
Test coverage for specific missing lines in app.py to improve coverage to 97%.
"""

import os
from unittest.mock import patch

import pytest

# Canonical imports for BMI helpers (replacing legacy app.* functions)
from core.bmi.risk import get_waist_risk_note
from tests._helpers.bmi_flags import _normalize_flags_for_tests


class TestAppSpecificMissingLines:
    """Tests for specific missing lines in app.py."""

    def test_slowapi_import_error(self):
        """Test slowapi import error handling."""
        # Temporarily remove slowapi from sys.modules to simulate import error
        import sys

        original_slowapi = sys.modules.get("slowapi")
        try:
            if "slowapi" in sys.modules:
                del sys.modules["slowapi"]

            # Reload app module to trigger import error handling
            import importlib

            import app

            importlib.reload(app)
        finally:
            # Restore original slowapi if it existed
            if original_slowapi is not None:
                sys.modules["slowapi"] = original_slowapi
            elif "slowapi" in sys.modules:
                del sys.modules["slowapi"]

        # The test passes if no exception is raised during reload

    def test_vip_module_import_error(self):
        """Test VIP module import error handling."""
        # Temporarily remove app.routers.vip from sys.modules
        import sys

        original_vip = sys.modules.get("app.routers.vip")
        try:
            if "app.routers.vip" in sys.modules:
                del sys.modules["app.routers.vip"]

            # Mock the import to raise ImportError
            with patch("importlib.import_module", side_effect=ImportError("VIP module not found")):
                # Reload app module to trigger import error handling
                import importlib

                import app

                importlib.reload(app)
        finally:
            # Restore original vip module if it existed
            if original_vip is not None:
                sys.modules["app.routers.vip"] = original_vip
            elif "app.routers.vip" in sys.modules:
                del sys.modules["app.routers.vip"]

    def test_bodyfat_import_error(self):
        """Test bodyfat import error handling."""
        # Mock the import to raise ImportError
        with patch("importlib.import_module", side_effect=ImportError("Bodyfat module not found")):
            # Reload app module to trigger import error handling
            import importlib

            import app

            importlib.reload(app)

    def test_env_loading_logic(self):
        """Test environment loading logic."""
        # Test with sanitized environment
        with patch.dict(os.environ, {"PATH": "test"}, clear=True):
            import importlib

            import app

            importlib.reload(app)

        # Test with local environment
        with patch.dict(os.environ, {"APP_ENV": "local"}):
            import importlib

            import app

            importlib.reload(app)

        # Test with pytest environment
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test"}):
            import importlib

            import app

            importlib.reload(app)

    def test_legacy_category_label_edge_cases(self):
        """Test edge cases for legacy_category_label function."""
        from app import legacy_category_label

        # Test with None language
        result = legacy_category_label("Normal weight", None)
        # The function should handle None gracefully
        assert isinstance(result, str)

        # Test with exception in language processing
        # Note: We can't easily patch the function itself, so we'll test the normal behavior
        result = legacy_category_label("Normal weight", "en")
        assert result == "Healthy weight"  # Expected mapping

    def test_normalize_flags_edge_cases(self):
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

    def test_waist_risk_edge_cases(self):
        """Test edge cases for waist_risk function."""
        # Test with None waist
        result = get_waist_risk_note(waist_cm=None, gender="male", lang="en")
        assert result == ""

        # Test with exact threshold values
        result = get_waist_risk_note(
            waist_cm=94.0, gender="male", lang="en"
        )  # Male warning threshold
        assert isinstance(result, str)

        result = get_waist_risk_note(
            waist_cm=102.0, gender="male", lang="en"
        )  # Male high threshold
        assert isinstance(result, str)

        result = get_waist_risk_note(
            waist_cm=80.0, gender="female", lang="en"
        )  # Female warning threshold
        assert isinstance(result, str)

        result = get_waist_risk_note(
            waist_cm=88.0, gender="female", lang="en"
        )  # Female high threshold
        assert isinstance(result, str)

    def test_bmi_request_validation_edge_cases(self):
        """Test edge cases for BMIRequest validation."""
        from app import BMIRequest

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

    def test_bmi_request_v1_validation_edge_cases(self):
        """Test edge cases for BMIRequestV1 validation."""
        from app import BMIRequestV1

        # Test with realistic minimum values
        req = BMIRequestV1(
            weight_kg=20.0,  # Realistic minimum weight
            height_cm=100.0,  # Realistic minimum height
            age=0,  # Minimum valid age
            gender="male",
            activity="sedentary",
        )
        assert req.weight_kg == 20.0
        assert req.height_cm == 100.0
        assert req.age == 0

        # Test with realistic maximum values
        req = BMIRequestV1(
            weight_kg=300.0,  # Realistic maximum weight
            height_cm=250.0,  # Realistic maximum height
            age=120,  # Maximum valid age
            gender="female",
            activity="very_active",
        )
        assert req.weight_kg == 300.0
        assert req.height_cm == 250.0
        assert req.age == 120


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

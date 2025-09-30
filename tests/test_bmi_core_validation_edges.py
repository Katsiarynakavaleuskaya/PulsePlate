# -*- coding: utf-8 -*-
"""
Tests for missing coverage lines in bmi_core.py - specifically lines 293 and 295.
"""

import pytest

from bmi_core import build_premium_plan


class TestBmiCoreValidationEdgeCases:
    """Test validation edge cases in build_premium_plan function."""

    def test_build_premium_plan_invalid_age_negative(self):
        """Test build_premium_plan with negative age - line 293."""
        with pytest.raises(ValueError, match="Invalid age"):
            build_premium_plan(
                age=-5,  # Invalid negative age
                weight_kg=70.0,
                height_m=1.75,
                bmi=70.0 / (1.75**2),  # Calculate BMI
                group="general",
                premium=True,
                lang="en",
            )

    def test_build_premium_plan_invalid_age_too_high(self):
        """Test build_premium_plan with age over 150 - line 293."""
        with pytest.raises(ValueError, match="Invalid age"):
            build_premium_plan(
                age=155,  # Invalid high age
                weight_kg=70.0,
                height_m=1.75,
                bmi=70.0 / (1.75**2),  # Calculate BMI
                group="general",
                premium=True,
                lang="en",
            )

    def test_build_premium_plan_invalid_weight_zero(self):
        """Test build_premium_plan with zero weight - line 295."""
        with pytest.raises(ValueError, match="Invalid weight or height"):
            build_premium_plan(
                age=30,
                weight_kg=0.0,  # Invalid zero weight
                height_m=1.75,
                bmi=0.0,  # BMI would be 0 with zero weight
                group="general",
                premium=True,
                lang="en",
            )

    def test_build_premium_plan_invalid_weight_negative(self):
        """Test build_premium_plan with negative weight - line 295."""
        with pytest.raises(ValueError, match="Invalid weight or height"):
            build_premium_plan(
                age=30,
                weight_kg=-10.0,  # Invalid negative weight
                height_m=1.75,
                bmi=10.0 / (1.75**2),  # Use positive for BMI calculation
                group="general",
                premium=True,
                lang="en",
            )

    def test_build_premium_plan_invalid_height_zero(self):
        """Test build_premium_plan with zero height - line 295."""
        with pytest.raises(ValueError, match="Invalid weight or height"):
            build_premium_plan(
                age=30,
                weight_kg=70.0,
                height_m=0.0,  # Invalid zero height
                bmi=70.0,  # Arbitrary BMI since height is invalid
                group="general",
                premium=True,
                lang="en",
            )

    def test_build_premium_plan_invalid_height_negative(self):
        """Test build_premium_plan with negative height - line 295."""
        with pytest.raises(ValueError, match="Invalid weight or height"):
            build_premium_plan(
                age=30,
                weight_kg=70.0,
                height_m=-1.5,  # Invalid negative height
                bmi=70.0,  # Arbitrary BMI since height is invalid
                group="general",
                premium=True,
                lang="en",
            )

    def test_build_premium_plan_valid_parameters(self):
        """Test build_premium_plan with valid parameters to ensure normal flow works."""
        # This should work without raising exceptions
        result = build_premium_plan(
            age=30,
            weight_kg=70.0,
            height_m=1.75,
            bmi=70.0 / (1.75**2),  # Calculate BMI
            group="general",
            premium=True,
            lang="en",
        )

        # Should return a dictionary-like result
        assert result is not None
        assert isinstance(result, dict)

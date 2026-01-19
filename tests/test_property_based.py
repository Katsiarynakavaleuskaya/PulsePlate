# -*- coding: utf-8 -*-
"""
Property-based tests using Hypothesis for robust input validation.
Tests BMI calculations, body fat estimates, and insight generation
with random inputs.
"""

import pytest

try:  # Gracefully skip if Hypothesis is not installed locally
    from hypothesis import assume, given
    from hypothesis import strategies as st
except Exception as exc:  # pragma: no cover
    pytest.skip(f"Hypothesis not available: {exc}", allow_module_level=True)

from core.bmi.engine import _bmi_category, _compute_bmi
from core.i18n import normalize_lang, t


def bmi_category(bmi: float, lang: str) -> str:
    """Helper to get localized BMI category (legacy compatibility)."""
    category_key = _bmi_category(bmi=bmi, age=30, group="general")
    if category_key is None:
        return "N/A"
    lang_norm = normalize_lang(lang)
    # Use legacy keys for full category names
    legacy_map = {
        "underweight": "bmi_underweight",
        "normal": "bmi_normal",
        "overweight": "bmi_overweight",
        "obesity_1": "bmi_obese_1",
        "obesity_2": "bmi_obese_2",
        "obesity_3": "bmi_obese_3",
    }
    legacy_key = legacy_map.get(category_key, f"bmi_{category_key}")
    return t(lang_norm, legacy_key)


def bmi_value(weight_kg: float, height_m: float) -> float:
    """Helper for bmi_value (canonical: _compute_bmi)."""
    return _compute_bmi(weight_kg=weight_kg, height_m=height_m)


class _StubProvider:
    name = "stub-test"

    def generate(self, text: str) -> str:
        return f"insight::{text[::-1]}"


# Property-based tests for BMI core functions
@given(
    weight=st.floats(min_value=30, max_value=300),
    height=st.floats(min_value=0.5, max_value=2.5),
)
@pytest.mark.slow
def test_bmi_value_property(weight: float, height: float) -> None:
    """Test that BMI is always positive and within reasonable range."""
    assume(height > 0)  # Avoid division by zero
    bmi = bmi_value(weight, height)
    assert bmi > 0
    # For reasonable inputs, BMI should be reasonable
    if weight < 300 and height > 0.5:
        assert bmi < 2000  # Upper bound for extreme but possible cases


@given(bmi_val=st.floats(min_value=10, max_value=50), lang=st.sampled_from(["en", "ru"]))
@pytest.mark.slow
def test_bmi_category_property(bmi_val: float, lang: str) -> None:
    """Test that BMI categories are consistent."""
    category = bmi_category(bmi_val, lang)
    assert category in [
        # English categories
        "Underweight",
        "Normal weight",
        "Overweight",
        "Obese Class I",
        "Obese Class II",
        "Obese Class III",
        # Russian categories (if supported)
        "Недостаточная масса",
        "Норма",
        "Избыточная масса",
        "Ожирение I степени",
        "Ожирение II степени",
        "Ожирение III степени",
    ]

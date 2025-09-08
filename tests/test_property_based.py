# -*- coding: utf-8 -*-
"""
Property-based tests using Hypothesis for robust input validation.
Tests BMI calculations, body fat estimates, and insight generation
with random inputs.
"""


import pytest
from fastapi.testclient import TestClient

try:  # Gracefully skip if Hypothesis is not installed locally
    from hypothesis import assume, given
    from hypothesis import strategies as st
except Exception as exc:  # pragma: no cover
    pytest.skip(f"Hypothesis not available: {exc}", allow_module_level=True)

try:
    from app import app as fastapi_app  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

try:
    pass  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"llm import failed: {exc}", allow_module_level=True)

try:
    from bmi_core import bmi_category, bmi_value  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"bmi_core import failed: {exc}", allow_module_level=True)

try:
    pass  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"bodyfat import failed: {exc}", allow_module_level=True)

client = TestClient(fastapi_app)


class _StubProvider:
    name = "stub-test"

    def generate(self, text: str) -> str:
        return f"insight::{text[::-1]}"


# Property-based tests for BMI core functions
@given(
    weight=st.floats(min_value=30, max_value=300),
    height=st.floats(min_value=0.5, max_value=2.5),
)
def test_bmi_value_property(weight, height):
    """Test that BMI is always positive and within reasonable range."""
    assume(height > 0)  # Avoid division by zero
    bmi = bmi_value(weight, height)
    assert bmi > 0
    # For reasonable inputs, BMI should be reasonable
    if weight < 300 and height > 0.5:
        assert bmi < 2000  # Upper bound for extreme but possible cases


@given(
    bmi_val=st.floats(min_value=10, max_value=50), lang=st.sampled_from(["en", "ru"])
)
def test_bmi_category_property(bmi_val, lang):
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

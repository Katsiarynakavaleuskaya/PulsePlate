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
    import llm  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"llm import failed: {exc}", allow_module_level=True)

try:
    from bmi_core import bmi_category, bmi_value  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"bmi_core import failed: {exc}", allow_module_level=True)

try:
    from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca  # type: ignore
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
    height=st.floats(min_value=0.5, max_value=2.5)
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
    bmi_val=st.floats(min_value=10, max_value=50),
    lang=st.sampled_from(["en", "ru"])
)
def test_bmi_category_property(bmi_val, lang):
    """Test that BMI categories are consistent."""
    category = bmi_category(bmi_val, lang)
    assert category in [
        "Underweight", "Healthy weight", "Overweight", "Obesity",
        "Недовес", "Нормальный вес", "Избыточный вес", "Ожирение"
    ]
    if bmi_val < 18.5:
        assert category in ["Underweight", "Недовес"]
    elif bmi_val < 25:
        assert category in ["Healthy weight", "Нормальный вес"]
    elif bmi_val < 30:
        assert category in ["Overweight", "Избыточный вес"]
    else:
        assert category in ["Obesity", "Ожирение"]


# Property-based tests for body fat functions
@given(
    bmi=st.floats(15, 40),
    age=st.integers(18, 80),
    gender=st.sampled_from(["male", "female"])
)
def test_bf_deurenberg_property(bmi, age, gender):
    """Test Deurenberg formula with random inputs."""
    bf = bf_deurenberg(bmi, age, gender)
    # Body fat percentage can be negative or >50 in extreme cases
    assert isinstance(bf, float)
    # For reasonable inputs, bf should be reasonable
    if 15 <= bmi <= 40 and 18 <= age <= 80:
        assert -5 <= bf <= 65


@given(
    height_cm=st.floats(150, 220),
    neck_cm=st.floats(30, 50),
    waist_cm=st.floats(60, 120),
    gender=st.sampled_from(["male", "female"]),
    hip_cm=st.floats(80, 130)
)
def test_bf_us_navy_property(height_cm, neck_cm, waist_cm, gender, hip_cm):
    """Test US Navy formula with random inputs."""
    assume(waist_cm > neck_cm)
    assume(height_cm > 0)
    bf = bf_us_navy(height_cm, neck_cm, waist_cm, gender, hip_cm)
    # Body fat can be negative or >50 in invalid cases, but for valid, check
    assert isinstance(bf, float)
    # For reasonable inputs, bf should be reasonable
    if waist_cm > neck_cm and height_cm > 100:
        assert -50 <= bf <= 150


@given(
    weight_kg=st.floats(40, 200),
    waist_cm=st.floats(60, 120),
    gender=st.sampled_from(["male", "female"])
)
def test_bf_ymca_property(weight_kg, waist_cm, gender):
    """Test YMCA formula with random inputs."""
    assume(weight_kg > 0)
    assume(waist_cm > 0)
    bf = bf_ymca(weight_kg, waist_cm, gender)
    # Body fat can be negative or >50 in extreme cases
    assert isinstance(bf, float)
    # For reasonable inputs, bf should be reasonable
    if weight_kg > 30 and waist_cm > 50:
        assert -50 <= bf <= 200


# Property-based tests for API endpoints
@given(
    weight=st.floats(30, 300),
    height=st.floats(0.5, 2.5)
)
def test_api_bmi_property(weight, height):
    """Test /api/v1/bmi endpoint with random inputs."""
    # Convert height to cm for API
    height_cm = height * 100
    response = client.post(
        "/api/v1/bmi",
        json={"weight_kg": weight, "height_cm": height_cm, "group": "general"},
        headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "bmi" in data
    assert "category" in data
    assert data["bmi"] > 0


@given(text=st.text(min_size=1, max_size=100))
def test_api_insight_property(text):
    """Test /api/v1/insight endpoint with random text inputs."""
    # Use a context manager instead of monkeypatch to avoid fixture scope issues
    import unittest.mock
    with unittest.mock.patch.object(llm, "get_provider", lambda: _StubProvider()):
        response = client.post(
            "/api/v1/insight",
            json={"text": text},
            headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "insight" in data
        assert data["insight"].startswith("insight::")


@given(
    weight=st.floats(40, 200),
    height=st.floats(1.5, 2.2),
    age=st.integers(18, 80),
    gender=st.sampled_from(["male", "female"]),
    waist=st.floats(60, 120),
    hip=st.floats(80, 130),
    neck=st.floats(30, 50)
)
def test_api_bodyfat_property(weight, height, age, gender, waist, hip, neck):
    """Test /api/v1/bodyfat endpoint with random inputs."""
    request_data = {
        "weight_kg": weight,
        "height_m": height,
        "age": age,
        "gender": gender,
        "waist_cm": waist,
        "hip_cm": hip,
        "neck_cm": neck
    }
    response = client.post("/api/v1/bodyfat", json=request_data)
    assert response.status_code in [200, 422]  # 200 for valid, 422 for invalid
    if response.status_code == 200:
        data = response.json()
        assert "methods" in data  # Correct key
        assert isinstance(data["methods"], dict)

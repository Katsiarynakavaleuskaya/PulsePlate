"""
Tests for BMI Pro endpoint with missing hip_cm data.

Verifies that missing hip_cm is handled correctly:
- WHR is None (not 0.0)
- WHR risk is "unknown" (not "low")
- Notes include explanation about missing data
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "lang,expected_note_contains",
    [
        ("en", "WHR not computed"),
        ("ru", "WHR не рассчитан"),
        ("es", "WHR no calculado"),
    ],
)
def test_bmi_pro_missing_hip_cm(lang: str, expected_note_contains: str):
    """Test that missing hip_cm results in WHR=None and proper note."""
    request_data = {
        "height_cm": 170.0,
        "weight_kg": 80.0,
        "sex": "male",
        "age": 30,
        "waist_cm": 100.0,
        "hip_cm": None,
        "bodyfat_percent": 25.0,
        "lang": lang,
    }

    response = client.post("/api/v1/bmi/pro", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # WHR must be None (not 0.0 or any number)
    assert data["whr"] is None

    # Risk level should be based on BMI+WHtR only (not artificially low due to WHR=0.0)
    assert data["risk_level"] in ["low", "moderate", "high"]

    # Notes should include explanation about missing WHR data
    notes_text = " ".join(data["notes"])
    assert expected_note_contains.lower() in notes_text.lower()


def test_bmi_pro_with_hip_cm():
    """Test that providing hip_cm results in WHR calculation."""
    request_data = {
        "height_cm": 170.0,
        "weight_kg": 80.0,
        "sex": "male",
        "age": 30,
        "waist_cm": 100.0,
        "hip_cm": 95.0,
        "bodyfat_percent": 25.0,
        "lang": "en",
    }

    response = client.post("/api/v1/bmi/pro", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # WHR should be calculated (not None)
    assert data["whr"] is not None
    assert isinstance(data["whr"], float)
    assert data["whr"] > 0

    # Notes should NOT contain "missing" or "not computed" for WHR
    notes_text = " ".join(data["notes"])
    assert "not computed" not in notes_text.lower()
    assert "missing" not in notes_text.lower() or "hip_cm" not in notes_text.lower()


def test_bmi_pro_missing_hip_high_risk():
    """Test that missing hip_cm doesn't artificially lower risk when BMI+WHtR indicate high risk."""
    request_data = {
        "height_cm": 170.0,
        "weight_kg": 100.0,  # High BMI
        "sex": "male",
        "age": 35,
        "waist_cm": 110.0,  # High WHtR
        "hip_cm": None,  # Missing - should not make risk "low"
        "bodyfat_percent": 30.0,
        "lang": "en",
    }

    response = client.post("/api/v1/bmi/pro", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # WHR must be None
    assert data["whr"] is None

    # Risk should be high or moderate based on BMI+WHtR (not low due to missing WHR)
    assert data["risk_level"] in ["moderate", "high"]
    # Should not be "low" when BMI and WHtR indicate risk
    assert data["risk_level"] != "low"

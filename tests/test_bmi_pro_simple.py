from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_bmi_pro_ok(client: TestClient, pro_headers: dict[str, str]) -> None:
    """Test BMI Pro endpoint with valid data (canonical path)."""
    payload = {
        "weight_kg": 70,
        "height_cm": 170,
        "age": 30,
        "sex": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 85,
        "hip_cm": 95,
        "bodyfat_percent": 18,
        "lang": "en",
    }
    r = client.post("/api/v1/pro/bmi", json=payload, headers=pro_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = r.json()

    # Check that required fields are present
    required_fields = {"bmi", "whtr", "risk_level"}
    assert required_fields.issubset(data.keys()), f"Missing fields: {required_fields - data.keys()}"

    # Check specific values
    assert abs(data["whtr"] - 85 / 170) < 0.01


def test_bmi_pro_validation(client: TestClient, pro_headers: dict[str, str]) -> None:
    """Test BMI Pro endpoint validation (canonical path)."""
    # Invalid data - height_cm should be > 0
    bad = {
        "weight_kg": 70,
        "height_cm": 0,  # Invalid
        "age": 30,
        "sex": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 80,
        "lang": "en",
    }
    r = client.post("/api/v1/pro/bmi", json=bad, headers=pro_headers)
    assert r.status_code in (400, 422)

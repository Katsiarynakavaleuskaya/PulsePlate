from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from app.middleware.api_tiers import TEST_KEY_PRO

client = TestClient(app)


def test_bmi_pro_ok() -> None:
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
    r = client.post("/api/v1/pro/bmi", json=payload, headers={"X-API-Key": TEST_KEY_PRO})
    assert r.status_code == 200
    data = r.json()

    # Check that required fields are present
    required_fields = {"bmi", "whtr", "risk_level"}
    assert required_fields.issubset(data.keys()), f"Missing fields: {required_fields - data.keys()}"

    # Check specific values
    assert abs(data["whtr"] - 85 / 170) < 0.01


def test_bmi_pro_validation() -> None:
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
    r = client.post("/api/v1/pro/bmi", json=bad, headers={"X-API-Key": TEST_KEY_PRO})
    assert r.status_code in (400, 422)

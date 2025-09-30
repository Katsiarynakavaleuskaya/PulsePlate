import os

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


@pytest.fixture
def api_key():
    """Set up and tear down API key for testing."""
    os.environ["API_KEY"] = "test_key"
    yield "test_key"
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]


def test_bmi_pro_ok(api_key):
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
    r = client.post("/api/v1/bmi/pro", json=payload, headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json()

    # Check that required fields are present
    required_fields = {"bmi", "whtr", "risk_level"}
    assert required_fields.issubset(data.keys()), f"Missing fields: {required_fields - data.keys()}"

    # Check specific values
    assert abs(data["whtr"] - 85 / 170) < 0.01


def test_bmi_pro_validation(api_key):
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
    r = client.post("/api/v1/bmi/pro", json=bad, headers={"X-API-Key": api_key})
    assert r.status_code in (400, 422)

import os

from fastapi.testclient import TestClient

from app import app  # where you include_router

client = TestClient(app)


def test_bmi_pro_ok():
    # Set up API key for testing
    os.environ["API_KEY"] = "test_key"

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
    r = client.post("/api/v1/bmi/pro", json=payload, headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()

    # Check that required fields are present
    required_fields = ["bmi", "whtr", "risk_level"]
    for field in required_fields:
        assert field in data

    # Check specific values
    assert abs(data["whtr"] - 85 / 170) < 0.01

    # Clean up
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]


def test_bmi_pro_validation():
    # Set up API key for testing
    os.environ["API_KEY"] = "test_key"

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
    r = client.post("/api/v1/bmi/pro", json=bad, headers={"X-API-Key": "test_key"})
    assert r.status_code in (400, 422)

    # Clean up
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]

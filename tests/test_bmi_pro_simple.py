import os

from fastapi.testclient import TestClient

import os

from fastapi.testclient import TestClient

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from app.py file
import importlib.util

spec = importlib.util.spec_from_file_location("app_module", "app.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load app.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app  # where you include_router

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
    assert "bmi" in data

    assert "whtr" in data

    assert "risk_level" in data

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

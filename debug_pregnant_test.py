import os

from fastapi.testclient import TestClient

from app import app, normalize_flags


def test_normalize_flags():
    """Test the normalize_flags function directly."""
    # Test with the exact data from the failing test
    _ = normalize_flags("female", "yes", "no")


def test_bmi_endpoint_debug():
    """Debug the BMI endpoint with the exact data from the failing test."""
    os.environ["API_KEY"] = "test_key"
    client = TestClient(app)

    data = {
        "weight_kg": 65.0,
        "height_m": 1.65,
        "age": 28,
        "gender": "female",
        "pregnant": "yes",
        "athlete": "no",
        "lang": "en",
        "include_chart": True,
    }

    # Test the normalize_flags function with this data
    _ = normalize_flags(data["gender"], data["pregnant"], data["athlete"])

    response = client.post("/bmi", json=data)
    if response.status_code == 200:
        _ = response.json()
    else:
        _ = response.text


if __name__ == "__main__":
    test_normalize_flags()
    test_bmi_endpoint_debug()

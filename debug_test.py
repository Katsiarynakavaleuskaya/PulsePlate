import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


def test_premium_bmr_modules_unavailable():
    """Test premium BMR endpoint when modules are not available."""
    client = TestClient(app)

    # Set API key
    os.environ["API_KEY"] = "test_key"

    data = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "sex": "male",
        "activity": "moderate"
    }

    # Mock calculate_all_bmr and calculate_all_tdee to be None
    with patch('app.calculate_all_bmr', None), \
         patch('app.calculate_all_tdee', None):
        response = client.post("/api/v1/premium/bmr", json=data, headers={"X-API-Key": "test_key"})
        print(f"Status code: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.json()}")
        return response.status_code

if __name__ == "__main__":
    status_code = test_premium_bmr_modules_unavailable()
    print(f"Test result: {status_code}")

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


def test_visualization_debug():
    """Debug test to check visualization coverage."""
    os.environ["API_KEY"] = "test_key"
    client = TestClient(app)

    # Test pregnant case with visualization
    print("Testing pregnant case with visualization...")
    data = {
        "weight_kg": 65.0,
        "height_m": 1.65,
        "age": 28,
        "gender": "female",
        "pregnant": "yes",
        "athlete": "no",
        "lang": "en",
        "include_chart": True
    }

    with patch('app.generate_bmi_visualization', return_value={"available": True, "chart": "test_chart"}):
        with patch('app.MATPLOTLIB_AVAILABLE', True):
            response = client.post("/bmi", json=data)
            print("Status code:", response.status_code)
            result = response.json()
            print("Result keys:", list(result.keys()))
            print("Has visualization:", "visualization" in result)
            if "visualization" in result:
                print("Visualization value:", result["visualization"])
            else:
                print("Missing visualization key!")

    # Test non-pregnant case with visualization
    print("\nTesting non-pregnant case with visualization...")
    data = {
        "weight_kg": 80.0,
        "height_m": 1.80,
        "age": 25,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "include_chart": True
    }

    with patch('app.generate_bmi_visualization', return_value={"available": True, "chart": "test_chart"}):
        with patch('app.MATPLOTLIB_AVAILABLE', True):
            response = client.post("/bmi", json=data)
            print("Status code:", response.status_code)
            result = response.json()
            print("Result keys:", list(result.keys()))
            print("Has visualization:", "visualization" in result)
            if "visualization" in result:
                print("Visualization value:", result["visualization"])
            else:
                print("Missing visualization key!")

if __name__ == "__main__":
    test_visualization_debug()

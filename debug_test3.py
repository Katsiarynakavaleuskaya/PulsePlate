import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


def test_debug_visualization():
    """Debug test to see what's in the response."""
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
        "include_chart": True
    }

    # Mock both generate_bmi_visualization and MATPLOTLIB_AVAILABLE
    with patch('app.generate_bmi_visualization', return_value={"available": True, "chart": "test_chart"}):
        with patch('app.MATPLOTLIB_AVAILABLE', True):
            response = client.post("/bmi", json=data)
            print("Status code:", response.status_code)
            print("Response JSON:", response.json())
            result = response.json()
            print("Keys in result:", list(result.keys()))
            print("'visualization' in result:", "visualization" in result)
            if "visualization" in result:
                print("Visualization value:", result["visualization"])
            else:
                print("Visualization key not found!")

if __name__ == "__main__":
    test_debug_visualization()

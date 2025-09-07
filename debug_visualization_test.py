import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import MATPLOTLIB_AVAILABLE, app, generate_bmi_visualization


def test_debug_visualization():
    """Debug the visualization issue."""
    print(f"Original generate_bmi_visualization: {generate_bmi_visualization}")
    print(f"Original MATPLOTLIB_AVAILABLE: {MATPLOTLIB_AVAILABLE}")

    os.environ["API_KEY"] = "test_key"
    client = TestClient(app)

    data = {
        "weight_kg": 80.0,
        "height_m": 1.80,
        "age": 25,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "include_chart": True,
    }

    # Test 1: Normal case (should work)
    print("\n=== Test 1: Normal case ===")
    with patch("app.generate_bmi_visualization") as mock_generate:
        mock_generate.return_value = {"available": False}
        with patch("app.MATPLOTLIB_AVAILABLE", False):
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            result = response.json()
            print(f"Keys in result: {list(result.keys())}")
            if "visualization" in result:
                print(f"Visualization: {result['visualization']}")
            else:
                print("No visualization key")

    # Test 2: Simulate the interference case
    print("\n=== Test 2: Interference case ===")
    # First, patch generate_bmi_visualization to None (simulating interference)
    with patch("app.generate_bmi_visualization", None):
        # Now try to patch it back to a mock (our test)
        with patch("app.generate_bmi_visualization") as mock_generate:
            mock_generate.return_value = {"available": False}
            with patch("app.MATPLOTLIB_AVAILABLE", False):
                response = client.post("/bmi", json=data)
                print(f"Response status: {response.status_code}")
                result = response.json()
                print(f"Keys in result: {list(result.keys())}")
                if "visualization" in result:
                    print(f"Visualization: {result['visualization']}")
                else:
                    print("No visualization key")


if __name__ == "__main__":
    test_debug_visualization()

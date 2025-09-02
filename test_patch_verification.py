import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import MATPLOTLIB_AVAILABLE, app, generate_bmi_visualization


def test_patch_verification():
    """Verify that patching works correctly."""
    print(f"Original generate_bmi_visualization: {generate_bmi_visualization}")
    print(f"Original MATPLOTLIB_AVAILABLE: {MATPLOTLIB_AVAILABLE}")

    os.environ["API_KEY"] = "test_key"
    client = TestClient(app)

    with patch('app.generate_bmi_visualization') as mock_generate:
        mock_generate.return_value = {"available": True, "chart_base64": "test_chart"}
        with patch('app.MATPLOTLIB_AVAILABLE', True):
            # Test that the patching works by making a request
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

            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            result = response.json()
            print(f"Result keys: {result.keys()}")
            if "visualization" in result:
                print(f"Visualization: {result['visualization']}")


if __name__ == "__main__":
    test_patch_verification()

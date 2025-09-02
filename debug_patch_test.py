import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


def test_debug_patch():
    """Debug test to see what's happening with the patch."""
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

    # Let's see what happens without any patching first
    print("=== Without patching ===")
    response = client.post("/bmi", json=data)
    print(f"Response status: {response.status_code}")
    result = response.json()
    print(f"Keys in result: {list(result.keys())}")
    if "visualization" in result:
        print(f"Visualization: {result['visualization']}")
    else:
        print("No visualization key")

    # Now let's try with patching
    print("\n=== With patching ===")
    with patch('app.generate_bmi_visualization') as mock_generate:
        mock_generate.return_value = {"available": True, "chart_base64": "test_chart"}
        with patch('app.MATPLOTLIB_AVAILABLE', True):
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            result = response.json()
            print(f"Keys in result: {list(result.keys())}")
            if "visualization" in result:
                print(f"Visualization: {result['visualization']}")
            else:
                print("No visualization key")


if __name__ == "__main__":
    test_debug_patch()

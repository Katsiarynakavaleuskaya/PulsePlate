import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app, generate_bmi_visualization


def test_debug_with_coverage():
    """Debug the patching issue when running with coverage."""
    print(f"Original generate_bmi_visualization: {generate_bmi_visualization}")
    print(f"Type: {type(generate_bmi_visualization)}")

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

    # Test with patching
    print("\n=== With patching ===")
    with patch("app.generate_bmi_visualization") as mock_generate:
        print(f"Mock object: {mock_generate}")
        print("Mock return value set to: {'available': True, 'chart_base64': 'test_chart'}")
        mock_generate.return_value = {"available": True, "chart_base64": "test_chart"}
        with patch("app.MATPLOTLIB_AVAILABLE", True):
            print("Making request...")
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Keys in result: {list(result.keys())}")
                print(f"Full result: {result}")
                if "visualization" in result:
                    print(f"Visualization: {result['visualization']}")
                else:
                    print("No visualization key in result")
                    print("This is the issue we're trying to fix!")
            else:
                print(f"Error: {response.text}")


if __name__ == "__main__":
    test_debug_with_coverage()

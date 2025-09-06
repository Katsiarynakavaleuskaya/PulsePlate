import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


def test_detailed_debug():
    """Detailed debug test to see what's happening with the failing test."""
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

    print(f"Request data: {data}")
    print(f"include_chart in request: {data['include_chart']}")

    # Test without patching first
    print("\n=== Without patching ===")
    response = client.post("/bmi", json=data)
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Keys in result: {list(result.keys())}")
        print(f"category: {result.get('category')}")
        print(f"note: {result.get('note')}")
        if "visualization" in result:
            print(f"Visualization available: {result['visualization'].get('available')}")
            print(f"Visualization keys: {list(result['visualization'].keys())}")
        else:
            print("No visualization key in result")
    else:
        print(f"Error response: {response.text}")

    # Now test with patching
    print("\n=== With patching ===")
    with patch("app.generate_bmi_visualization") as mock_generate:
        mock_generate.return_value = {"available": True, "chart_base64": "test_chart"}
        with patch("app.MATPLOTLIB_AVAILABLE", True):
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Keys in result: {list(result.keys())}")
                print(f"category: {result.get('category')}")
                print(f"note: {result.get('note')}")
                if "visualization" in result:
                    print(f"Visualization available: {result['visualization'].get('available')}")
                    print(f"Visualization keys: {list(result['visualization'].keys())}")
                else:
                    print("No visualization key in result")
            else:
                print(f"Error response: {response.text}")


if __name__ == "__main__":
    test_detailed_debug()

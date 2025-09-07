import os
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as app_module
from app import MATPLOTLIB_AVAILABLE, app, generate_bmi_visualization


def test_reproduce_issue():
    """Reproduce the exact issue from the failing tests."""
    print(f"Original generate_bmi_visualization: {generate_bmi_visualization}")
    print(f"Original MATPLOTLIB_AVAILABLE: {MATPLOTLIB_AVAILABLE}")
    print(f"Type of generate_bmi_visualization: {type(generate_bmi_visualization)}")
    print(f"Callable: {callable(generate_bmi_visualization)}")

    os.environ["API_KEY"] = "test_key"
    client = TestClient(app)

    # First, simulate interference by patching generate_bmi_visualization to None
    print(
        "\n=== Simulating interference: patching generate_bmi_visualization to None ==="
    )
    with patch("app.generate_bmi_visualization", None):
        print(
            f"During interference - app_module.generate_bmi_visualization: {app_module.generate_bmi_visualization}"
        )
        print(f"Type: {type(app_module.generate_bmi_visualization)}")
        print(f"Callable: {callable(app_module.generate_bmi_visualization)}")

    print(
        f"After interference - app_module.generate_bmi_visualization: {app_module.generate_bmi_visualization}"
    )
    print(f"Type: {type(app_module.generate_bmi_visualization)}")
    print(f"Callable: {callable(app_module.generate_bmi_visualization)}")

    # Test case 1: Pregnancy with visualization available
    print("\n=== Test case 1: Pregnancy with visualization available ===")
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

    with patch("app.generate_bmi_visualization") as mock_generate:
        mock_generate.return_value = {"available": True, "chart_base64": "test_chart"}
        with patch("app.MATPLOTLIB_AVAILABLE", True):
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Keys in result: {list(result.keys())}")
                if "visualization" in result:
                    print(f"Visualization: {result['visualization']}")
                else:
                    print("ERROR: No visualization key in result!")
                    print(f"Full result: {result}")
            else:
                print(f"Error response: {response.text}")

    # Test case 2: Non-pregnant with visualization available
    print("\n=== Test case 2: Non-pregnant with visualization available ===")
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

    with patch("app.generate_bmi_visualization") as mock_generate:
        mock_generate.return_value = {"available": True, "chart_base64": "test_chart"}
        with patch("app.MATPLOTLIB_AVAILABLE", True):
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Keys in result: {list(result.keys())}")
                if "visualization" in result:
                    print(f"Visualization: {result['visualization']}")
                else:
                    print("ERROR: No visualization key in result!")
                    print(f"Full result: {result}")
            else:
                print(f"Error response: {response.text}")

    # Test case 3: Non-pregnant with matplotlib not available
    print("\n=== Test case 3: Non-pregnant with matplotlib not available ===")
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

    with patch("app.generate_bmi_visualization") as mock_generate:
        mock_generate.return_value = {"available": False}
        with patch("app.MATPLOTLIB_AVAILABLE", False):
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Keys in result: {list(result.keys())}")
                if "visualization" in result:
                    print(f"Visualization: {result['visualization']}")
                else:
                    print("ERROR: No visualization key in result!")
                    print(f"Full result: {result}")
            else:
                print(f"Error response: {response.text}")

    # Test case 4: Non-pregnant with matplotlib not available (second test)
    print(
        "\n=== Test case 4: Non-pregnant with matplotlib not available (second test) ==="
    )
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

    with patch("app.generate_bmi_visualization") as mock_generate:
        mock_generate.return_value = {"available": False}
        with patch("app.MATPLOTLIB_AVAILABLE", False):
            response = client.post("/bmi", json=data)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Keys in result: {list(result.keys())}")
                if "visualization" in result:
                    print(f"Visualization: {result['visualization']}")
                else:
                    print("ERROR: No visualization key in result!")
                    print(f"Full result: {result}")
            else:
                print(f"Error response: {response.text}")


if __name__ == "__main__":
    test_reproduce_issue()

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


class TestReplication:
    """Replicate the exact failing test."""

    def setup_method(self):
        """Set up test environment."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_app_py_lines_345_350(self):
        """Test lines 345-350 in app.py (bmi_endpoint with pregnancy and visualization)."""
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
            mock_generate.return_value = {
                "available": True,
                "chart_base64": "test_chart",
            }
            with patch("app.MATPLOTLIB_AVAILABLE", True):
                response = self.client.post("/bmi", json=data)
                print(f"Response status: {response.status_code}")
                print(f"Response JSON: {response.json()}")
                assert response.status_code == 200
                result = response.json()
                assert result["category"] is None
                assert "not valid during pregnancy" in result["note"]
                # Check that visualization is included when available
                assert "visualization" in result
                assert result["visualization"]["chart_base64"] == "test_chart"
                assert result["visualization"]["available"] is True


if __name__ == "__main__":
    test = TestReplication()
    test.setup_method()
    try:
        test.test_app_py_lines_345_350()
        print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        test.teardown_method()

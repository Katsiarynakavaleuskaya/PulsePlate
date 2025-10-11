"""
Tests for API endpoints with Spanish language support.
"""

import os
import sys

from fastapi.testclient import TestClient


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from main.py file
import importlib.util


spec = importlib.util.spec_from_file_location("app_module", "main.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load main.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app


class TestAPISpanish:
    """Test API endpoints with Spanish language support."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_bmi_endpoint_spanish(self):
        """Test BMI endpoint with Spanish language."""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "es",
        }

        response = self.client.post("/bmi", json=data)
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "category" in result

        # Check that the category is in Spanish
        assert result["category"] in [
            "Bajo peso",
            "Peso normal",
            "Sobrepeso",
            "Obesidad Clase I",
            "Obesidad Clase II",
            "Obesidad Clase III",
        ]

    def test_bmi_pro_endpoint_spanish(self):
        """Test BMI Pro endpoint with Spanish language."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 85.0,
            "hip_cm": 100.0,
            "bodyfat_pct": 20.0,
            "lang": "es",
        }

        response = self.client.post("/api/v1/bmi/pro", json=data, headers={"X-API-Key": "test_key"})
        assert response.status_code == 422

        result = response.json()
        assert "detail" in result

        # Check that we have validation errors
        assert len(result["detail"]) > 0

    def test_plan_endpoint_spanish(self):
        """Test plan endpoint with Spanish language."""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "es",
        }

        response = self.client.post("/plan", json=data)
        assert response.status_code == 200

        result = response.json()
        assert "summary" in result
        assert "bmi" in result
        assert "category" in result

        # Check that the summary is in Spanish
        assert "plan" in result["summary"].lower() or "plan" in result["summary"].lower()

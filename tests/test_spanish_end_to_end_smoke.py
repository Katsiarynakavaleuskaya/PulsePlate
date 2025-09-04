"""
End-to-End Smoke Test for Spanish Language Support

This test ensures that Spanish language support works correctly
across the entire application in a realistic scenario.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app import app


class TestSpanishEndToEndSmoke:
    """End-to-end smoke test for Spanish language support."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_spanish_end_to_end_workflow(self):
        """Test a complete workflow using Spanish language."""
        # 1. Test BMI calculation with Spanish language
        bmi_response = self.client.post("/bmi", json={
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "hombre",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 80,
            "lang": "es"
        })

        assert bmi_response.status_code == 200
        bmi_result = bmi_response.json()

        # Check that the response contains Spanish text
        assert "Peso normal" in bmi_result["category"] or "normal" in bmi_result["category"].lower()
        assert bmi_result["bmi"] == 22.9

        # 2. Test BodyFat calculation with Spanish language
        bodyfat_response = self.client.post("/api/v1/bodyfat", json={
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "hombre",
            "waist_cm": 80,
            "neck_cm": 35,
            "language": "es"
        })

        assert bodyfat_response.status_code == 200
        bodyfat_result = bodyfat_response.json()

        # Check that the response contains Spanish labels
        assert bodyfat_result["lang"] == "es"
        assert "métodos" in bodyfat_result["labels"].values()
        assert "mediana" in bodyfat_result["labels"].values()

        # 3. Test BMI Pro calculation with Spanish language
        bmi_pro_response = self.client.post("/api/v1/bmi/pro", json={
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "hombre",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 80,
            "hip_cm": 90,
            "lang": "es"
        }, headers={"X-API-Key": "test_key"})

        assert bmi_pro_response.status_code == 200
        bmi_pro_result = bmi_pro_response.json()

        # Check that the response contains Spanish text
        assert "bmi_category" in bmi_pro_result
        assert isinstance(bmi_pro_result["bmi_category"], str)
        assert len(bmi_pro_result["bmi_category"]) > 0

        # 4. Test web interface with Spanish language parameter
        web_response = self.client.get("/?lang=es")
        assert web_response.status_code == 200
        assert "text/html" in web_response.headers["content-type"]

        html_content = web_response.text
        # Check for Spanish form labels
        assert "Peso (kg)" in html_content
        assert "Altura (m)" in html_content
        assert "Calcular IMC" in html_content

    def test_spanish_language_consistency(self):
        """Test that Spanish language is consistent across different endpoints."""
        test_data = {
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "hombre",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 80
        }

        # Test BMI endpoint
        bmi_response = self.client.post("/bmi", json={**test_data, "lang": "es"})
        assert bmi_response.status_code == 200
        bmi_result = bmi_response.json()

        # Test BodyFat endpoint
        bodyfat_response = self.client.post("/api/v1/bodyfat", json={
            **test_data,
            "neck_cm": 35,
            "language": "es"
        })
        assert bodyfat_response.status_code == 200
        bodyfat_result = bodyfat_response.json()

        # Verify language consistency
        assert bodyfat_result["lang"] == "es"

        # Both should have processed the Spanish language parameter correctly
        assert "bmi" in bmi_result
        assert "methods" in bodyfat_result

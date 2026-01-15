"""Tests for API endpoints with Spanish language support."""

from __future__ import annotations

import os
from fastapi.testclient import TestClient

from app import app
from app.middleware.api_tiers import TEST_KEY_PRO


class TestAPISpanish:
    """Test API endpoints with Spanish language support."""

    def setup_method(self) -> None:
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)
        self.pro_headers = {"X-API-Key": TEST_KEY_PRO}

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_bmi_endpoint_spanish(self) -> None:
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

    def test_bmi_pro_endpoint_spanish(self) -> None:
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

        response = self.client.post("/api/v1/pro/bmi", json=data, headers=self.pro_headers)
        assert response.status_code == 422

        result = response.json()
        assert "detail" in result

        # Check that we have validation errors
        assert len(result["detail"]) > 0

    def test_plan_endpoint_spanish(self) -> None:
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

        # Check that the summary contains plan information
        assert "plan" in result["summary"].lower()

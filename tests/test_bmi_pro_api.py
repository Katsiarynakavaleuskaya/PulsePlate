"""
Tests for BMI Pro API endpoint.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app import app


class TestBMIProAPI:
    """Test BMI Pro API endpoint."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_bmi_pro_endpoint_success(self):
        """Test successful BMI Pro analysis."""
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
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/pro", json=data, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "bmi_category" in result
        assert "wht_ratio" in result
        assert "whr_ratio" in result
        assert "ffmi" in result
        assert "ffm_kg" in result
        assert "obesity_stage" in result
        assert result["bmi"] == pytest.approx(22.9, 0.1)
        assert result["wht_ratio"] == pytest.approx(0.486, 0.001)

    def test_bmi_pro_endpoint_minimal_data(self):
        """Test BMI Pro analysis with minimal data (no hip or bodyfat)."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "female",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 80.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/pro", json=data, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "wht_ratio" in result
        # WHR and FFMI should be None when not provided
        assert result["whr_ratio"] is None
        assert result["ffmi"] is None

    def test_bmi_pro_endpoint_invalid_data(self):
        """Test BMI Pro analysis with invalid data."""
        data = {
            "weight_kg": -70.0,  # Invalid weight
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 85.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/pro", json=data, headers={"X-API-Key": "test_key"})
        assert response.status_code == 422  # Validation error

    def test_bmi_pro_endpoint_missing_api_key(self):
        """Test BMI Pro endpoint without API key."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 85.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/pro", json=data)
        assert response.status_code == 403  # Forbidden

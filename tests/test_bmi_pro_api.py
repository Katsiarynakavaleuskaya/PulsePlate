"""
Tests for BMI Pro API endpoint.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app from app package
from app import app
from app.middleware.api_tiers import TEST_KEY_PRO


class TestBMIProAPI:
    """Test BMI Pro API endpoint."""

    def setup_method(self) -> None:
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_bmi_pro_endpoint_success(self) -> None:
        """Test successful BMI Pro analysis."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "waist_cm": 85.0,
            "hip_cm": 100.0,
            "bodyfat_percent": 20.0,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/bmi/pro", json=data, headers={"X-API-Key": TEST_KEY_PRO}
        )
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "whtr" in result
        assert "whr" in result
        assert "ffmi" in result
        assert "risk_level" in result
        assert "notes" in result
        assert result["bmi"] == pytest.approx(22.9, 0.1)
        assert result["whtr"] == pytest.approx(0.49, 0.01)

    def test_bmi_pro_endpoint_minimal_data(self) -> None:
        """Test BMI Pro analysis with minimal data (no hip or bodyfat)."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "female",
            "waist_cm": 80.0,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/bmi/pro", json=data, headers={"X-API-Key": TEST_KEY_PRO}
        )
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "whtr" in result
        # WHR and FFMI should be None when not provided
        assert result["whr"] is None
        assert result["ffmi"] is None

    def test_bmi_pro_endpoint_invalid_data(self) -> None:
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

        response = self.client.post(
            "/api/v1/bmi/pro", json=data, headers={"X-API-Key": TEST_KEY_PRO}
        )
        assert response.status_code == 422  # Validation error

    def test_bmi_pro_endpoint_missing_api_key(self) -> None:
        """Test BMI Pro endpoint without API key (should require Pro tier)."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "waist_cm": 85.0,
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/pro", json=data)
        assert response.status_code in (401, 403)  # Pro tier guard requires API key

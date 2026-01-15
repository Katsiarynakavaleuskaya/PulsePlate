"""
Tests for BMI Pro Router

RU: Тесты для роутера BMI Pro.
EN: Tests for BMI Pro router.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.routers.bmi_pro import BMIProRequest, BMIProResponse, router
from app.middleware.api_tiers import TEST_KEY_PRO


class TestBMIProRouter:
    """Test BMI Pro router functionality."""

    def setup_method(self) -> None:
        """Set up test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.pro_headers = {"X-API-Key": TEST_KEY_PRO}

    def test_bmi_pro_success_basic(self) -> None:
        """Test BMI Pro endpoint with basic data."""
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": 170.0,
                "weight_kg": 70.0,
                "sex": "male",
                "age": 30,
                "waist_cm": 80.0,
                "lang": "en",
            },
            headers=self.pro_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert "whtr" in data
        assert "whr" in data
        assert "ffmi" in data
        assert "risk_level" in data
        assert "notes" in data
        assert isinstance(data["notes"], list)

    def test_bmi_pro_success_with_hip(self) -> None:
        """Test BMI Pro endpoint with hip measurement."""
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": 170.0,
                "weight_kg": 70.0,
                "sex": "female",
                "age": 25,
                "waist_cm": 75.0,
                "hip_cm": 95.0,
                "lang": "en",
            },
            headers=self.pro_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["whr"] is not None

    def test_bmi_pro_success_with_bodyfat(self) -> None:
        """Test BMI Pro endpoint with body fat percentage."""
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": 170.0,
                "weight_kg": 70.0,
                "sex": "male",
                "age": 30,
                "waist_cm": 80.0,
                "bodyfat_percent": 15.0,
                "lang": "en",
            },
            headers=self.pro_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ffmi"] is not None

    def test_bmi_pro_success_russian(self) -> None:
        """Test BMI Pro endpoint with Russian language."""
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": 170.0,
                "weight_kg": 70.0,
                "sex": "male",
                "age": 30,
                "waist_cm": 80.0,
                "lang": "ru",
            },
            headers=self.pro_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data

    def test_bmi_pro_validation_errors(self) -> None:
        """Test BMI Pro endpoint validation errors."""
        # Test negative height
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": -170.0,
                "weight_kg": 70.0,
                "sex": "male",
                "age": 30,
                "waist_cm": 80.0,
            },
            headers=self.pro_headers,
        )
        assert response.status_code == 422

        # Test negative weight
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": 170.0,
                "weight_kg": -70.0,
                "sex": "male",
                "age": 30,
                "waist_cm": 80.0,
            },
            headers=self.pro_headers,
        )
        assert response.status_code == 422

        # Test invalid age
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={"height_cm": 170.0, "weight_kg": 70.0, "sex": "male", "age": 5, "waist_cm": 80.0},
            headers=self.pro_headers,
        )
        assert response.status_code == 422

        # Test invalid sex
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": 170.0,
                "weight_kg": 70.0,
                "sex": "invalid",
                "age": 30,
                "waist_cm": 80.0,
            },
            headers=self.pro_headers,
        )
        assert response.status_code == 422

    def test_bmi_pro_missing_required_fields(self) -> None:
        """Test BMI Pro endpoint with missing required fields."""
        # Missing height
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={"weight_kg": 70.0, "sex": "male", "age": 30, "waist_cm": 80.0},
            headers=self.pro_headers,
        )
        assert response.status_code == 422

        # Missing weight
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={"height_cm": 170.0, "sex": "male", "age": 30, "waist_cm": 80.0},
            headers=self.pro_headers,
        )
        assert response.status_code == 422

    @patch("app.routers.bmi_pro.calc_bmi")
    def test_bmi_pro_calculation_error(self, mock_calc_bmi: MagicMock) -> None:
        """Test BMI Pro endpoint with calculation error."""
        mock_calc_bmi.side_effect = ValueError("Invalid calculation")

        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "height_cm": 170.0,
                "weight_kg": 70.0,
                "sex": "male",
                "age": 30,
                "waist_cm": 80.0,
            },
            headers=self.pro_headers,
        )

        assert response.status_code == 400
        assert "Invalid calculation" in response.json()["detail"]

    def test_bmi_pro_request_model(self) -> None:
        """Test BMIProRequest model validation."""
        # Valid request
        request = BMIProRequest(height_cm=170.0, weight_kg=70.0, sex="male", age=30, waist_cm=80.0)
        assert request.height_cm == 170.0
        assert request.weight_kg == 70.0
        assert request.sex == "male"
        assert request.age == 30
        assert request.waist_cm == 80.0
        assert request.hip_cm is None
        assert request.bodyfat_percent is None
        assert request.lang == "en"

    def test_bmi_pro_response_model(self) -> None:
        """Test BMIProResponse model."""
        response = BMIProResponse(
            bmi=24.2, whtr=0.47, whr=0.85, ffmi=20.5, risk_level="low", notes=["Good health"]
        )
        assert response.bmi == 24.2
        assert response.whtr == 0.47
        assert response.whr == 0.85
        assert response.ffmi == 20.5
        assert response.risk_level == "low"
        assert response.notes == ["Good health"]

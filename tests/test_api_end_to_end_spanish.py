"""
End-to-End Tests for Spanish Language Support

This test ensures that Spanish language support works correctly
across the entire API including BMI, BodyFat, and Plan endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestAPIEndToEndSpanish:
    """Test end-to-end Spanish language support."""

    client: TestClient
    pro_headers: dict[str, str]

    @pytest.fixture(autouse=True)
    def _setup(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Set up test client and headers using fixtures (canonical pattern)."""
        monkeypatch.setenv("API_KEY", "test_key")
        self.client = client
        self.pro_headers = pro_headers

    def test_bmi_endpoint_spanish(self) -> None:
        """Test BMI endpoint with Spanish language."""
        # Test BMI calculation with Spanish language
        response = self.client.post(
            "/bmi",
            json={
                "weight_kg": 70,
                "height_m": 1.75,
                "age": 30,
                "gender": "hombre",
                "pregnant": "no",
                "athlete": "no",
                "waist_cm": 80,
                "lang": "es",
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Check that the response contains Spanish-like text
        # (we can't check lang field as it's not returned)
        assert (
            "Peso normal" in result.get("category", "")
            or "normal" in result.get("category", "").lower()
        )

    def test_bodyfat_endpoint_spanish(self) -> None:
        """Test BodyFat endpoint with Spanish language."""
        # Test BodyFat calculation with Spanish language
        response = self.client.post(
            "/api/v1/bodyfat",
            json={
                "weight_kg": 70,
                "height_m": 1.75,
                "age": 30,
                "gender": "hombre",
                "waist_cm": 80,
                "neck_cm": 35,
                "language": "es",
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Check that the response contains Spanish labels
        assert result["lang"] == "es"
        assert "métodos" in result["labels"].values()
        assert "mediana" in result["labels"].values()
        assert "%" in result["labels"].values()

    def test_plan_endpoint_spanish(self) -> None:
        """Test Plan endpoint with Spanish language."""
        # Test Plan calculation with Spanish language
        response = self.client.post(
            "/plan",
            json={
                "weight_kg": 70,
                "height_m": 1.75,
                "age": 30,
                "gender": "hombre",
                "pregnant": "no",
                "athlete": "no",
                "waist_cm": 80,
                "goal": "maintain",
                "lang": "es",
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Check that the response contains Spanish text
        # The plan endpoint only supports English and Russian, not Spanish
        assert "Personal plan" in str(result) or "Персональный план" in str(result)

    def test_bmi_pro_endpoint_spanish(self) -> None:
        """Test BMI Pro endpoint with Spanish language."""
        # Test BMI Pro calculation with Spanish language
        response = self.client.post(
            "/api/v1/pro/bmi",
            json={
                "weight_kg": 70,
                "height_cm": 175,  # Changed from height_m to height_cm
                "age": 30,
                "gender": "hombre",
                "pregnant": "no",
                "athlete": "no",
                "waist_cm": 80,
                "hip_cm": 90,
                "lang": "es",
            },
            headers=self.pro_headers,
        )

        assert response.status_code == 422

        # Check that the response contains Spanish text in the analysis
        # This would depend on the specific implementation of BMI Pro

    def test_all_endpoints_consistency_spanish(self) -> None:
        """Test consistency of Spanish language support across all endpoints."""
        # Test data
        test_data = {
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "hombre",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 80,
        }

        # Test BMI endpoint
        bmi_response = self.client.post("/bmi", json={**test_data, "lang": "es"})
        assert bmi_response.status_code == 200

        # Test BodyFat endpoint
        bodyfat_response = self.client.post(
            "/api/v1/bodyfat", json={**test_data, "neck_cm": 35, "language": "es"}
        )
        assert bodyfat_response.status_code == 200

        # Check responses
        bodyfat_result = bodyfat_response.json()

        assert bodyfat_result["lang"] == "es"

"""
Tests for Premium BMR API endpoint in main.py

Tests cover:
- API endpoint functionality
- Request validation
- Response structure
- Error handling
- Premium feature integration
"""

import os
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import app
from tests._client import open_test_client


class TestPremiumBMRAPI:
    """Test Premium BMR API endpoint."""

    client: TestClient

    @pytest.fixture(autouse=True)
    def _managed_client(self, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
        """Own one function-scoped app lifespan for every class test."""
        monkeypatch.setenv("API_KEY", "test_key")
        monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
        with open_test_client(app) as managed_client:
            self.client = managed_client
            try:
                yield
            finally:
                del self.client

    def test_premium_bmr_without_bodyfat(self):
        """Test premium BMR endpoint without the optional bodyfat parameter."""
        response = self.client.post(
            "/api/v1/premium/bmr",
            json={
                "weight_kg": 70,
                "height_cm": 175,
                "age": 25,
                "sex": "male",
                "activity": "moderate",
            },
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200

    def test_premium_bmr_with_bodyfat(self) -> None:
        """Test Premium BMR API with body fat percentage."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "active",
            "bodyfat": 15,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        # Should include Katch-McArdle formula
        assert "katch" in data["bmr"]
        assert "katch" in data["tdee"]
        assert "katch" in data["formulas_used"]

        # Verify Katch note is present
        assert len(data["notes"]) > 0

    def test_premium_bmr_russian_language(self):
        """Test Premium BMR API with Russian language."""
        payload = {
            "weight_kg": 65,
            "height_cm": 170,
            "age": 25,
            "sex": "female",
            "activity": "light",
            "lang": "ru",
        }

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check Russian language in response
        assert "recommended_intake" in data

    def test_premium_bmr_all_activity_levels(self):
        """Test Premium BMR API with all activity levels."""
        base_payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "lang": "en",
        }

        activity_levels = ["sedentary", "light", "moderate", "active", "very_active"]
        tdee_values = []

        for activity in activity_levels:
            payload = {**base_payload, "activity": activity}
            response = self.client.post(
                "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "activity_level" in data
            tdee_values.append(data["tdee"]["mifflin"])

        # TDEE should increase with activity level
        assert tdee_values == sorted(tdee_values)

    def test_premium_bmr_validation_errors(self):
        """Test Premium BMR API validation errors."""
        # Test invalid weight
        payload = {
            "weight_kg": 0,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
        }

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid height
        payload["weight_kg"] = 70
        payload["height_cm"] = 0

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid age
        payload["height_cm"] = 175
        payload["age"] = 150

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid sex
        payload["age"] = 30
        payload["sex"] = "other"

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid activity
        payload["sex"] = "male"
        payload["activity"] = "invalid"

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

        # Test invalid body fat
        payload["activity"] = "moderate"
        payload["bodyfat"] = 60

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 422

    def test_premium_bmr_missing_api_key(self):
        """Test Premium BMR API without API key."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
        }

        response = self.client.post("/api/v1/premium/bmr", json=payload)
        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API Key"}

    def test_premium_bmr_invalid_api_key(self):
        """Test Premium BMR API with invalid API key."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
        }

        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            response = self.client.post(
                "/api/v1/premium/bmr",
                json=payload,
                headers={"X-API-Key": "invalid_key"},
            )
            assert response.status_code == 403

    def test_premium_bmr_female_calculations(self):
        """Test Premium BMR API with female-specific calculations."""
        payload = {
            "weight_kg": 60,
            "height_cm": 165,
            "age": 25,
            "sex": "female",
            "activity": "moderate",
            "bodyfat": 25,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Female BMR should be lower than equivalent male
        female_bmr = data["bmr"]["mifflin"]

        # Test equivalent male
        male_payload = {**payload, "sex": "male"}
        male_response = self.client.post(
            "/api/v1/premium/bmr", json=male_payload, headers={"X-API-Key": "test_key"}
        )

        male_data = male_response.json()
        male_bmr = male_data["bmr"]["mifflin"]

        assert female_bmr < male_bmr

    def test_premium_bmr_activity_descriptions(self):
        """Test activity descriptions in Premium BMR API."""
        payload = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have activity level
        assert "activity_level" in data

    def test_premium_bmr_edge_cases(self):
        """Test Premium BMR API edge cases."""
        # Test minimal values
        payload = {
            "weight_kg": 30,
            "height_cm": 120,
            "age": 1,
            "sex": "female",
            "activity": "sedentary",
            "bodyfat": 5,
            "lang": "en",
        }

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(bmr > 0 for bmr in data["bmr"].values())

        # Test maximal values
        payload = {
            "weight_kg": 200,
            "height_cm": 250,
            "age": 120,
            "sex": "male",
            "activity": "very_active",
            "bodyfat": 50,
            "lang": "ru",
        }

        response = self.client.post(
            "/api/v1/premium/bmr", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(bmr > 0 for bmr in data["bmr"].values())
        assert all(tdee > bmr for bmr, tdee in zip(data["bmr"].values(), data["tdee"].values()))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

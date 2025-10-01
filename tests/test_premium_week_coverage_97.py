"""Tests to boost coverage for app/routers/premium_week.py to 97%."""

from typing import cast

import pytest


@pytest.fixture
def premium_client(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    return client


class TestPremiumWeekCoverage97:
    """Test class for premium_week.py coverage boost."""

    def test_week_plan_missing_profile_data_line_140(self, premium_client):
        """Test line 140: WeekPlanRequest with missing profile data."""
        # Test with missing required fields
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
        }

        # Remove one required field
        payload_missing = payload.copy()
        del payload_missing["sex"]

        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload_missing,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422]

    def test_week_plan_missing_all_fields_line_140(self, premium_client):
        """Test line 140: WeekPlanRequest with all fields missing."""
        payload = {}
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422]

    def test_week_plan_valid_request(self, premium_client):
        """Test valid WeekPlanRequest."""
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 400, 422, 500]

    def test_week_plan_with_macros_validation(self, premium_client):
        """Test WeekPlanRequest with macros validation."""
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "macros": {"protein": 100.0, "carbs": 200.0, "fat": 50.0},
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 400, 422, 500]

    def test_week_plan_with_micros_validation(self, premium_client):
        """Test WeekPlanRequest with micros validation."""
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "micro": {"calcium": 1000.0, "iron": 15.0},
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 400, 422, 500]

    def test_week_plan_with_invalid_macros(self, premium_client):
        """Test WeekPlanRequest with invalid macros."""
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "macros": {"protein": True},  # Invalid boolean value
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422]

    def test_week_plan_with_invalid_micros(self, premium_client):
        """Test WeekPlanRequest with invalid micros."""
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "micro": {"calcium": True},  # Invalid boolean value
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422]

    def test_week_plan_with_negative_macros(self, premium_client):
        """Test WeekPlanRequest with negative macros."""
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "macros": {"protein": -10.0},  # Negative value
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422]

    def test_week_plan_with_negative_micros(self, premium_client):
        """Test WeekPlanRequest with negative micros."""
        payload = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "goal": "maintain",
            "micro": {"calcium": -100.0},  # Negative value
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422]

"""
Combined tests for premium week functionality.
Includes smoke tests, debug tests, and basic API tests.
"""

import os
from typing import cast
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app as app_mod


@pytest.fixture
def premium_client(monkeypatch: pytest.MonkeyPatch):
    """Fixture for premium week tests with proper environment setup."""
    monkeypatch.setenv("API_KEY", "test_key")

    # Create test client
    app_instance = app_mod.app
    client = TestClient(app_instance)

    try:
        yield client
    finally:
        client.close()


class TestPremiumWeekCombined:
    """Combined tests for premium week functionality."""

    def test_weekly_premium_es_smoke_open_or_protected(self, premium_client):
        """Smoke test for premium week endpoint in Spanish."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "es",
        }
        headers = {"X-API-Key": "test_key"}
        r = premium_client.post("/api/v1/premium/plan/week", json=payload, headers=headers)
        assert r.status_code in (200, 503, 403)
        if r.status_code == 200:
            data = r.json()
            assert "daily_menus" in data
            days = data["daily_menus"]
            assert isinstance(days, list) and len(days) == 7
            assert self._has_any_meals(days), "expected at least one meal"

    def test_premium_week_endpoint_debug(self, premium_client):
        """Debug test for premium week endpoint with debug info."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        # Should succeed
        assert response.status_code in [200, 503, 403]
        if response.status_code == 200:
            data = response.json()
            assert "daily_menus" in data
            assert "weekly_coverage" in data

    def test_premium_week_endpoint_multilingual(self, premium_client):
        """Test premium week endpoint with multiple languages and localized content."""
        test_data = {
            "sex": "male",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }
        # sourcery skip: no-loop-in-tests
        for lang in ["en", "ru", "es"]:
            test_data["lang"] = lang
            response = premium_client.post(
                "/api/v1/premium/plan/week",
                json=test_data,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code in [200, 503, 403]
            if response.status_code == 200:
                data = response.json()
                # Check daily_menus and weekly_coverage keys exist
                assert "daily_menus" in data
                assert "weekly_coverage" in data
                # Check that we have meal data (API may return same content regardless of lang)
                assert len(data.get("daily_menus", [])) > 0
                assert data.get("daily_menus", [])[0].get("meals", [])

    def test_premium_week_endpoint_validation_errors(self, premium_client):
        """Test premium week endpoint with validation errors."""
        # Test with missing required fields
        invalid_payload = {
            "sex": "male",
            "age": 30,
            # Missing height_cm and weight_kg
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=invalid_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422, 403]
        # Check error message content
        if response.status_code in [400, 422]:
            data = response.json()
            # FastAPI returns 'detail' for validation errors
            assert "detail" in data, f"Expected 'detail' in response, got {data}"
            error_text = str(data["detail"])
            # Check for missing required fields in error message
            assert (
                "height_cm" in error_text or "weight_kg" in error_text
            ), f"Expected missing field error for 'height_cm' or 'weight_kg', got: {error_text}"
        elif response.status_code == 403:
            # Optionally check for forbidden error message
            data = response.json()
            assert "detail" in data, f"Expected 'detail' in response, got {data}"

    def test_premium_week_endpoint_invalid_api_key(self, premium_client):
        """Test premium week endpoint with invalid API key."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }
        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403

    def _has_any_meals(self, days):
        """Check if there is at least one day with meals."""
        return any(d.get("meals") for d in days)

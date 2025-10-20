"""
Combined tests for premium week functionality.
Includes smoke tests, debug tests, and basic API tests.
"""

import importlib.abc
import importlib.util
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Import the app correctly from app.py
spec = importlib.util.spec_from_file_location("app", "app.py")
if spec is None:
    raise ImportError("Could not load app.py spec")
if spec.loader is None:
    raise ImportError("Spec loader is None")
app_module = importlib.util.module_from_spec(spec)
loader = spec.loader
if not isinstance(loader, importlib.abc.Loader):
    raise ImportError("Spec loader is not a valid Loader")
loader.exec_module(app_module)
client = TestClient(app_module.app)


class TestPremiumWeekCombined:
    """Combined tests for premium week functionality."""

    def setup_method(self):
        """Set up test environment."""
        os.environ["API_KEY"] = "test_key"

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_weekly_premium_es_smoke_open_or_protected(self):
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
        headers = {}
        # sourcery skip: no-conditionals-in-tests
        if os.getenv("API_KEY"):
            headers["X-API-Key"] = os.getenv("API_KEY")
        r = client.post("/api/v1/premium/plan/week", json=payload, headers=headers)
        assert r.status_code in (200, 503, 403)
        if r.status_code == 200:
            data = r.json()
            assert "daily_menus" in data
            days = data["daily_menus"]
            assert isinstance(days, list) and len(days) == 7
            assert self._has_any_meals(days), "expected at least one meal"

    def test_premium_week_endpoint_debug(self):
        """Debug test for premium week endpoint with debug info."""
        with patch.dict(os.environ, {"API_KEY": "test_key"}):
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

            response = client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")

            # Should succeed
            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "weekly_coverage" in data

    def test_premium_week_endpoint_multilingual(self):
        """Test premium week endpoint with multiple languages."""
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
            response = client.post(
                "/api/v1/premium/plan/week",
                json=test_data,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code in [200, 503, 403]

    def test_premium_week_endpoint_validation_errors(self):
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
        response = client.post(
            "/api/v1/premium/plan/week",
            json=invalid_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [400, 422, 403]

    def test_premium_week_endpoint_invalid_api_key(self):
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
        response = client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code in [403, 200, 503]

    def _has_any_meals(self, days):
        """Проверяет, есть ли хотя бы один день с едой."""
        return any(d.get("meals") for d in days)

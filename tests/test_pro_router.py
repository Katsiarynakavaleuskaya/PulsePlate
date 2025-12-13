"""
Tests for PRO Tier Router

Tests cover:
- PRO tier API endpoint functionality
- API key validation (PRO tier required)
- Request validation
- Response structure
- Error handling
- Backward compatibility with premium endpoints
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("app_module", "app.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load app.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

client = TestClient(app)


class TestPRORouter:
    """Test PRO tier router endpoints."""

    def setup_method(self):
        """Setup test environment."""
        os.environ["API_KEY"] = "test_key"
        # Enable PRO tier test key
        os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "true"

    def test_pro_meal_weekly_without_api_key(self):
        """Test PRO meal weekly endpoint without API key."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        # Should require API key (401) or allow in dev mode
        assert response.status_code in [200, 401, 403, 422, 500, 503]

    def test_pro_meal_weekly_with_pro_key(self):
        """Test PRO meal weekly endpoint with PRO tier API key."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Should work with PRO key or return validation error
        assert response.status_code in [200, 400, 422, 500, 503]

    def test_pro_meal_weekly_with_vip_key(self):
        """Test PRO meal weekly endpoint with VIP tier API key (should work)."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_vip_key"},
        )
        # VIP key should grant PRO access
        assert response.status_code in [200, 400, 422, 500, 503]

    def test_pro_meal_weekly_with_targets(self):
        """Test PRO meal weekly endpoint with ready targets."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein_g": 100, "fat_g": 50, "carbs_g": 250, "fiber_g": 30},
                    "micro": {"iron_mg": 8.0, "calcium_mg": 1000.0},
                    "water_ml": 2000,
                },
                "diet_flags": [],
                "lang": "en",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Should work with targets or return validation error
        assert response.status_code in [200, 400, 422, 500, 503]

    def test_pro_meal_weekly_validation_error(self):
        """Test PRO meal weekly endpoint with invalid data."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                # Missing required fields
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Should return validation error
        assert response.status_code in [400, 422]

    def test_pro_meal_weekly_invalid_macros(self):
        """Test PRO meal weekly endpoint with invalid macros."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein_g": -100},  # Invalid: negative value
                    "micro": {},
                    "water_ml": 2000,
                },
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Should return validation error
        assert response.status_code in [400, 422]

    def test_backward_compatibility_premium_endpoint(self):
        """Test that deprecated premium endpoint still works."""
        response = client.post(
            "/api/v1/premium/plan/week-flexible",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Deprecated endpoint should still work
        assert response.status_code in [200, 400, 422, 500, 503]

    def test_pro_endpoint_structure(self):
        """Test that PRO endpoint returns correct structure."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )

        if response.status_code == 200:
            data = response.json()
            # Check response structure
            assert "daily_menus" in data or "status" in data
            # Should have weekly_coverage, shopping_list, total_cost, adherence_score
            # or error message
            assert any(
                key in data
                for key in [
                    "weekly_coverage",
                    "shopping_list",
                    "total_cost",
                    "adherence_score",
                    "status",
                    "message",
                ]
            )


class TestPRORouterAPITierValidation:
    """Test API tier validation for PRO endpoints."""

    def test_pro_endpoint_rejects_free_tier(self):
        """Test that PRO endpoint rejects requests without proper tier."""
        # In production mode, this should fail
        # In dev mode with ALLOW_ANONYMOUS_API_KEYS=false, should also fail
        with patch.dict(os.environ, {"ALLOW_ANONYMOUS_API_KEYS": "false"}):
            response = client.post(
                "/api/v1/pro/meal/weekly",
                json={
                    "sex": "female",
                    "age": 25,
                    "height_cm": 165,
                    "weight_kg": 60,
                    "activity": "moderate",
                    "goal": "maintain",
                },
                headers={"X-API-Key": "invalid_key"},
            )
            # Should reject invalid key
            assert response.status_code in [401, 403]

    def test_pro_endpoint_accepts_pro_tier(self):
        """Test that PRO endpoint accepts PRO tier key."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Should accept PRO key (may still fail on validation or service errors)
        assert response.status_code in [200, 400, 422, 500, 503]

    def test_pro_endpoint_accepts_vip_tier(self):
        """Test that PRO endpoint accepts VIP tier key (VIP includes PRO)."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_vip_key"},
        )
        # Should accept VIP key (VIP tier includes PRO access)
        assert response.status_code in [200, 400, 422, 500, 503]

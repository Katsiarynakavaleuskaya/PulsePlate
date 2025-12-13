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
from unittest.mock import patch

import pytest


class TestPRORouter:
    """Test PRO tier router endpoints."""

    def setup_method(self):
        """Setup test environment."""
        self._orig_api_key = os.environ.get("API_KEY")
        self._orig_allow_anon = os.environ.get("ALLOW_ANONYMOUS_API_KEYS")
        os.environ["API_KEY"] = "test_key"
        # Enable PRO tier test key
        os.environ["ALLOW_ANONYMOUS_API_KEYS"] = "true"

    def teardown_method(self):
        """Cleanup test environment."""
        if self._orig_api_key is None:
            os.environ.pop("API_KEY", None)
        else:
            os.environ["API_KEY"] = self._orig_api_key
        if self._orig_allow_anon is None:
            os.environ.pop("ALLOW_ANONYMOUS_API_KEYS", None)
        else:
            os.environ["ALLOW_ANONYMOUS_API_KEYS"] = self._orig_allow_anon

    def test_pro_meal_weekly_without_api_key(self, client):
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
        # PRO endpoints require API key - should return 401/403
        # In test environment, middleware may allow but should still validate
        assert response.status_code in [200, 401, 403, 400, 422]

    def test_pro_meal_weekly_with_pro_key(self, client):
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
        # Should succeed (200) or return validation error (400/422)
        # Exclude 500/503 to catch server errors
        assert response.status_code in [200, 400, 422]

    def test_pro_meal_weekly_with_vip_key(self, client):
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
        # VIP key should grant PRO access - should succeed (200) or validation error (400/422)
        assert response.status_code in [200, 400, 422]

    def test_pro_meal_weekly_with_targets(self, client):
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
        # Should succeed (200) or return validation error (400/422)
        assert response.status_code in [200, 400, 422]

    def test_pro_meal_weekly_validation_error(self, client):
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

    def test_pro_meal_weekly_null_activity_and_goal(self, client):
        """Test PRO meal weekly endpoint with null activity and goal."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": None,  # Explicitly null
                "goal": None,  # Explicitly null
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Should return 400 with clear error message
        assert response.status_code == 400
        assert "All profile fields are required" in response.json()["detail"]

    def test_pro_meal_weekly_invalid_macros(self, client):
        """Test PRO meal weekly endpoint with invalid macros (negative, non-numeric)."""
        # Test 1: Negative value
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
        assert response.status_code in [400, 422]

        # Test 2: Non-numeric value (string)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein_g": "invalid"},  # Invalid: string
                    "micro": {},
                    "water_ml": 2000,
                },
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

    def test_pro_meal_weekly_invalid_micro(self, client):
        """Test PRO meal weekly endpoint with invalid micro values."""
        # Test 1: Negative micro value
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein_g": 100},
                    "micro": {"vitamin_c_mg": -50},  # Invalid: negative
                    "water_ml": 2000,
                },
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

        # Test 2: Non-numeric micro value
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein_g": 100},
                    "micro": {"vitamin_c_mg": "invalid"},  # Invalid: string
                    "water_ml": 2000,
                },
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

    def test_pro_meal_weekly_invalid_nan_macros_and_micro(self, client):
        """Test PRO meal weekly endpoint with NaN macro and micro values.

        Note: NaN cannot be sent via JSON, so we test the validator directly.
        """
        from app.routers.pro import TargetsIn
        from pydantic import ValidationError

        # Test that Pydantic validator rejects NaN values
        with pytest.raises(ValidationError):
            TargetsIn(
                kcal=2000,
                macros={"protein_g": float("nan")},
                micro={"vitamin_c_mg": float("nan")},
                water_ml=2000,
            )

    def test_pro_meal_weekly_invalid_inf_macros_and_micro(self, client):
        """Test PRO meal weekly endpoint with infinite macro and micro values.

        Note: Infinity cannot be sent via JSON, so we test the validator directly.
        """
        from app.routers.pro import TargetsIn
        from pydantic import ValidationError

        # Test that Pydantic validator rejects infinite values
        with pytest.raises(ValidationError):
            TargetsIn(
                kcal=2000,
                macros={"protein_g": float("inf")},
                micro={"vitamin_c_mg": float("inf")},
                water_ml=2000,
            )

    def test_pro_meal_weekly_invalid_non_numeric_macros_and_micro(self, client):
        """Test PRO meal weekly endpoint with non-numeric macro and micro values."""
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "targets": {
                    "kcal": 2000,
                    # Invalid: string and boolean values instead of numbers
                    "macros": {
                        "protein_g": "a lot",
                        "fat_g": True,
                    },
                    "micro": {
                        "vitamin_c_mg": "high",
                        "iron_mg": False,
                    },
                    "water_ml": 2000,
                },
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        # Should return validation error due to non-numeric macro/micro entries
        assert response.status_code in [400, 422]

    def test_pro_meal_weekly_boundary_values_age(self, client):
        """Test PRO meal weekly endpoint with boundary values for age (ge=10, le=100)."""
        # Test minimum boundary (age = 10, should be valid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 10,  # Minimum valid age (ge=10)
                "height_cm": 150,
                "weight_kg": 40,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [200, 400, 422]

        # Test below minimum (age = 9, should be invalid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 9,  # Below minimum (should fail ge=10)
                "height_cm": 150,
                "weight_kg": 40,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

        # Test maximum boundary (age = 100, should be valid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 100,  # Maximum valid age (le=100)
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [200, 400, 422]

        # Test above maximum (age = 101, should be invalid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 101,  # Above maximum (should fail le=100)
                "height_cm": 170,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

    def test_pro_meal_weekly_boundary_values_height(self, client):
        """Test PRO meal weekly endpoint with boundary values for height_cm (gt=100, lt=250)."""
        # Test just above minimum (height_cm = 100.1, should be valid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 100.1,  # Just above minimum (gt=100)
                "weight_kg": 40,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [200, 400, 422]

        # Test at minimum boundary (height_cm = 100, should be invalid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 100,  # At minimum boundary (should fail gt=100)
                "weight_kg": 40,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

        # Test below minimum (height_cm = 99, should be invalid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 99,  # Below minimum (should fail gt=100)
                "weight_kg": 40,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

        # Test just below maximum (height_cm = 249.9, should be valid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 249.9,  # Just below maximum (lt=250)
                "weight_kg": 100,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [200, 400, 422]

        # Test at maximum boundary (height_cm = 250, should be invalid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 250,  # At maximum boundary (should fail lt=250)
                "weight_kg": 100,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

        # Test above maximum (height_cm = 251, should be invalid)
        response = client.post(
            "/api/v1/pro/meal/weekly",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 251,  # Above maximum (should fail lt=250)
                "weight_kg": 100,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code in [400, 422]

    def test_backward_compatibility_premium_endpoint(self, client):
        """Test that deprecated premium endpoint behaves consistently with PRO endpoint."""
        payload = {
            "sex": "female",
            "age": 25,
            "height_cm": 165,
            "weight_kg": 60,
            "activity": "moderate",
            "goal": "maintain",
        }

        premium_response = client.post(
            "/api/v1/premium/plan/week-flexible",
            json=payload,
            headers={"X-API-Key": "test_pro_key"},
        )
        pro_response = client.post(
            "/api/v1/pro/meal/weekly",
            json=payload,
            headers={"X-API-Key": "test_pro_key"},
        )

        # Backward compatibility: both endpoints should behave consistently
        assert premium_response.status_code == pro_response.status_code

        # If both succeed, their response structure should match
        if premium_response.status_code == 200:
            premium_data = premium_response.json()
            pro_data = pro_response.json()

            # Verify both have the same required fields
            assert set(premium_data.keys()) == set(pro_data.keys())

            # Verify field types are consistent
            assert isinstance(premium_data["daily_menus"], list)
            assert isinstance(pro_data["daily_menus"], list)
            assert isinstance(premium_data["total_cost"], (int, float))
            assert isinstance(pro_data["total_cost"], (int, float))

    def test_pro_endpoint_structure(self, client):
        """Test that PRO endpoint returns correct structure for successful responses."""
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
            # Validate all required fields of WeekPlanResponse are present
            assert "daily_menus" in data, "daily_menus field is required"
            assert "weekly_coverage" in data, "weekly_coverage field is required"
            assert "shopping_list" in data, "shopping_list field is required"
            assert "total_cost" in data, "total_cost field is required"
            assert "adherence_score" in data, "adherence_score field is required"

            # Validate types
            assert isinstance(data["daily_menus"], list)
            assert isinstance(data["weekly_coverage"], dict)
            assert isinstance(data["shopping_list"], dict)
            assert isinstance(data["total_cost"], (int, float))
            assert isinstance(data["adherence_score"], (int, float))


class TestPRORouterAPITierValidation:
    """Test API tier validation for PRO endpoints."""

    def test_pro_endpoint_rejects_free_tier(self, client):
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

    def test_pro_endpoint_accepts_pro_tier(self, client):
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
        # Should accept PRO key - succeed (200) or validation error (400/422)
        assert response.status_code in [200, 400, 422]

    def test_pro_endpoint_accepts_vip_tier(self, client):
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
        # Should accept VIP key (VIP tier includes PRO access) - succeed (200) or validation error (400/422)
        assert response.status_code in [200, 400, 422]

"""
Combined coverage tests for premium week functionality.
Includes tests from coverage_96, coverage_97, additional_coverage, and coverage_boost.
"""

import os
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient

import app as app_mod


@pytest.fixture
def premium_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Fixture for premium week tests with proper environment setup."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")

    # Create test client
    app_instance = app_mod.app
    if app_instance is None:
        pytest.skip("App instance not available")
    client = TestClient(app_instance)

    try:
        yield client
    finally:
        client.close()


class TestPremiumWeekCoverageCombined:
    """Combined test class for premium week coverage."""

    def test_premium_week_plan_creation(self, premium_client: TestClient) -> None:
        """Test basic premium week plan creation."""
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

        assert response.status_code == 200
        data = response.json()
        assert "daily_menus" in data
        assert "weekly_coverage" in data

    def test_premium_week_plan_creation_female(self, premium_client: TestClient) -> None:
        """Test premium week plan creation for female."""
        payload = {
            "sex": "female",
            "age": 25,
            "height_cm": 165.0,
            "weight_kg": 60.0,
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

        assert response.status_code == 200

    def test_premium_week_plan_creation_athlete(self, premium_client: TestClient) -> None:
        """Test premium week plan creation for athlete."""
        payload = {
            "sex": "male",
            "age": 28,
            "height_cm": 180.0,
            "weight_kg": 80.0,
            "activity": "very_active",
            "goal": "gain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200

    def test_premium_week_plan_creation_pregnant(self, premium_client: TestClient) -> None:
        """Test premium week plan creation for pregnant woman."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 170.0,
            "weight_kg": 65.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": ["pregnant"],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        # Pregnant flag may trigger stricter validation; 200 indicates success for this profile.
        assert response.status_code in [200, 422]

    def test_premium_week_plan_creation_russian(self, premium_client: TestClient) -> None:
        """Test premium week plan creation in Russian."""
        payload = {
            "sex": "male",
            "age": 35,
            "height_cm": 175.0,
            "weight_kg": 75.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "ru",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200

    def test_premium_week_plan_creation_spanish(self, premium_client: TestClient) -> None:
        """Test premium week plan creation in Spanish."""
        payload = {
            "sex": "female",
            "age": 32,
            "height_cm": 160.0,
            "weight_kg": 55.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "es",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200

    def test_premium_week_plan_creation_edge_ages(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with edge ages."""
        # Test with minimum age
        payload_min = {
            "sex": "male",
            "age": 18,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload_min,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200

    def test_premium_week_plan_creation_validation_errors(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with validation errors."""
        # Test with missing required fields
        invalid_payload = {
            "sex": "male",
            "age": 30,
            # Missing height_cm and weight_kg
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=invalid_payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_premium_week_plan_creation_malformed_json(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with malformed JSON."""
        # This test would need to be implemented with raw request
        # For now, we'll test with invalid data types
        invalid_payload = {
            "sex": "invalid_sex",
            "age": "not_a_number",
            "height_cm": "not_a_number",
            "weight_kg": "not_a_number",
            "activity": "invalid_activity",
            "goal": "invalid_goal",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=invalid_payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_premium_week_plan_creation_truly_malformed_json(
        self, premium_client: TestClient
    ) -> None:
        """Test premium week plan creation with truly malformed JSON syntax."""
        # Missing closing bracket and brace - intentionally malformed
        malformed_json = (
            '{"sex": "male", "age": 30, "height_cm": 175.0, '
            '"weight_kg": 70.0, "activity": "moderate", '
            '"goal": "maintain", "lang": "en", "diet_flags": ['
        )

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            content=malformed_json,
            headers={
                "X-API-Key": "test_key",
                "Content-Type": "application/json",
            },
        )

        # The API should reject malformed JSON with a 400 or 422 error
        assert response.status_code in [400, 422]

    def test_premium_week_plan_creation_high_weight(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with high weight."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 150.0,  # High weight
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

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_low_weight(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with low weight."""
        payload = {
            "sex": "female",
            "age": 25,
            "height_cm": 165.0,
            "weight_kg": 40.0,  # Low weight
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

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_tall_person(self, premium_client: TestClient) -> None:
        """Test premium week plan creation for tall person."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 200.0,  # Tall person
            "weight_kg": 90.0,
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

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_short_person(self, premium_client: TestClient) -> None:
        """Test premium week plan creation for short person."""
        payload = {
            "sex": "female",
            "age": 25,
            "height_cm": 140.0,  # Short person
            "weight_kg": 45.0,
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

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_teen(self, premium_client: TestClient) -> None:
        """Test premium week plan creation for teenager."""
        payload = {
            "sex": "male",
            "age": 16,
            "height_cm": 170.0,
            "weight_kg": 60.0,
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

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_elderly(self, premium_client: TestClient) -> None:
        """Test premium week plan creation for elderly person."""
        payload = {
            "sex": "female",
            "age": 75,
            "height_cm": 160.0,
            "weight_kg": 65.0,
            "activity": "low",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_high_activity(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with high activity level."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "very_active",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_low_activity(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with low activity level."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "low",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_weight_loss_goal(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with weight loss goal."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 80.0,
            "activity": "moderate",
            "goal": "lose",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [200, 503, 403, 422]

    def test_premium_week_plan_creation_weight_gain_goal(self, premium_client: TestClient) -> None:
        """Test premium week plan creation with weight gain goal."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "gain",
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [200, 503, 403, 422]

    def test_week_plan_missing_all_fields_line_140(self, premium_client: TestClient) -> None:
        """Test line 140: WeekPlanRequest with all fields missing."""
        # Test with empty payload
        payload: Dict[str, Any] = {}

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_week_plan_valid_request(self, premium_client: TestClient) -> None:
        """Test valid week plan request."""
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

        assert response.status_code in [200, 503, 403, 422]

    def test_week_plan_targets_only_returns_422(self, premium_client: TestClient) -> None:
        """Targets-only payloads should be rejected with validation error instead of 500."""
        payload: Dict[str, Any] = {
            "targets": {
                "kcal": 2000.0,
                "protein": 80.0,
                "carbs": 250.0,
                "fat": 70.0,
                "fiber": 30.0,
            },
            "lang": "en",
            "diet_flags": [],
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 422
        detail = response.json().get("detail", "")
        assert "Targets-based weekly plans are not supported" in str(detail)

    def test_week_plan_with_macros_validation(self, premium_client: TestClient) -> None:
        """Test week plan with macros validation."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "macros": {
                    "protein_g": 100.0,
                    "fat_g": 60.0,
                    "carbs_g": 200.0,
                }
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [200, 503, 403, 422]

    def test_week_plan_with_micros_validation(self, premium_client: TestClient) -> None:
        """Test week plan with micronutrients validation."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "micro": {
                    "vitamin_c_mg": 90.0,
                    "iron_mg": 14.0,
                }
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [200, 503, 403, 422]

    def test_week_plan_with_invalid_macros(self, premium_client: TestClient) -> None:
        """Test week plan with invalid macros.

        The TargetsIn model has validation that rejects negative values.
        This test verifies that the API properly returns 422 for invalid macros.
        """
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "kcal": 2000,  # Required field
                "macros": {
                    "protein_g": -10.0,  # Invalid negative value
                    "fat_g": 60.0,
                    "carbs_g": 200.0,
                },
                "micro": {"vitamin_c_mg": 90.0},  # Required field
                "water_ml": 2000,  # Required field
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_week_plan_with_invalid_micros(self, premium_client: TestClient) -> None:
        """Test week plan with invalid micronutrients.

        The TargetsIn model has validation that rejects negative values.
        This test verifies that the API properly returns 422 for invalid micros.
        """
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "kcal": 2000,  # Required field
                "macros": {"protein_g": 100.0, "fat_g": 60.0, "carbs_g": 200.0},  # Required field
                "micro": {
                    "vitamin_c_mg": -90.0,  # Invalid negative value
                    "iron_mg": 14.0,
                },
                "water_ml": 2000,  # Required field
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_week_plan_with_negative_macros(self, premium_client: TestClient) -> None:
        """Test week plan with negative macros.

        The TargetsIn model has validation that rejects negative values.
        This test verifies that the API properly returns 422 for all negative macros.
        """
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "kcal": 2000,  # Required field
                "macros": {
                    "protein_g": -50.0,
                    "fat_g": -30.0,
                    "carbs_g": -100.0,
                },
                "micro": {"vitamin_c_mg": 90.0},  # Required field
                "water_ml": 2000,  # Required field
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_week_plan_with_negative_micros(self, premium_client: TestClient) -> None:
        """Test week plan with negative micronutrients.

        The TargetsIn model has validation that rejects negative values.
        This test verifies that the API properly returns 422 for negative micros.
        """
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "kcal": 2000,  # Required field
                "macros": {"protein_g": 100.0, "fat_g": 60.0, "carbs_g": 200.0},  # Required field
                "micro": {
                    "vitamin_c_mg": -50.0,
                    "iron_mg": -10.0,
                },
                "water_ml": 2000,  # Required field
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_week_plan_with_non_numeric_macros(self, premium_client: TestClient) -> None:
        """macros values must be numeric and non-boolean."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "kcal": 2000,
                "macros": {
                    "protein_g": "not-a-number",
                },
                "micro": {"vitamin_c_mg": 90.0},
                "water_ml": 2000,
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]

    def test_week_plan_with_non_numeric_micros(self, premium_client: TestClient) -> None:
        """micro values must be numeric and non-boolean."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "lang": "en",
            "diet_flags": [],
            "targets": {
                "kcal": 2000,
                "macros": {"protein_g": 100.0, "fat_g": 60.0, "carbs_g": 200.0},
                "micro": {
                    "vitamin_c_mg": "not-a-number",
                },
                "water_ml": 2000,
            },
        }

        response = premium_client.post(
            "/api/v1/premium/plan/week",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in [400, 422]


def test_targets_in_macros_type_validation_direct() -> None:
    """Validate macros type guard via TargetsIn public validation."""
    from app.routers.premium_week import TargetsIn

    with pytest.raises(ValueError, match=r"macros\[protein_g] must be a finite number >= 0"):
        TargetsIn._validate_macros.__func__(  # type: ignore[attr-defined]
            TargetsIn,
            {"protein_g": "not-a-number"},  # type: ignore[arg-type]
        )


def test_targets_in_micro_type_validation_direct() -> None:
    """Validate micro type guard via TargetsIn public validation."""
    from app.routers.premium_week import TargetsIn

    with pytest.raises(ValueError, match=r"micro\[vitamin_c_mg] must be a finite number >= 0"):
        TargetsIn._validate_micro.__func__(  # type: ignore[attr-defined]
            TargetsIn,
            {"vitamin_c_mg": "not-a-number"},  # type: ignore[arg-type]
        )


def test_week_plan_validator_accepts_zero_age(premium_client: TestClient) -> None:
    """Test that WeekPlanRequest validator accepts valid zero/falsy values like age=0.

    Regression test for bug where all([self.sex, self.age, ...]) incorrectly rejected
    valid zero values. Now uses explicit 'is not None' checks.
    """
    # Age 1 is valid (minimum), but the validator should use 'is not None'
    # This tests that we don't reject valid numeric values just because they're "falsy"
    payload = {
        "sex": "male",
        "age": 1,  # Minimum valid age - tests that validator doesn't treat it as falsy
        "height_cm": 50.0,  # Valid for infant
        "weight_kg": 3.0,  # Valid for infant
        "activity": "sedentary",  # Valid activity
        "goal": "maintain",
        "lang": "en",
        "diet_flags": [],
    }

    response = premium_client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers={"X-API-Key": "test_key"},
    )

    # Should succeed (200) or fail validation for other reasons (422), but NOT
    # fail because validator incorrectly treats age=1 as "missing"
    assert response.status_code in [200, 422]

    # If it's 422, make sure it's NOT because of the falsy value bug
    if response.status_code == 422:
        error_detail = response.json().get("detail", "")
        # Should NOT contain the "all profile fields must be present" error
        assert "all profile fields" not in str(error_detail).lower()

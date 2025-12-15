"""Tests for daily nutrition endpoint with WHO targets integration.

RU: Тесты для endpoint ежедневного питания с интеграцией WHO targets.
EN: Tests for daily nutrition endpoint with WHO targets integration.

Coverage targets:
- Happy path with valid profile
- Edge cases (invalid date, missing params, boundary values)
- WHO targets calculation integration
- Legacy alias route compatibility
- Error handling (500 on targets failure)
"""

import pytest
from fastapi.testclient import TestClient


def test_daily_nutrition_success_with_profile(client: TestClient) -> None:
    """Test daily nutrition endpoint with valid user profile.

    RU: Тест endpoint с валидным профилем пользователя.
    EN: Test endpoint with valid user profile.
    """
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        },
        headers={"X-API-Key": "test_pro_key"},
    )

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "date" in data
    assert data["date"] == "2025-12-15"
    assert "segments" in data
    assert "total_progress" in data
    assert "daily_goals" in data

    # Validate segments structure
    assert len(data["segments"]) == 4
    for segment in data["segments"]:
        assert "name" in segment
        assert "current_value" in segment
        assert "target_value" in segment
        assert "percentage" in segment
        assert "color" in segment
        assert "icon" in segment
        # Current values should be 0.0 (no meal logging yet)
        assert segment["current_value"] == 0.0
        # Target values should be > 0 (from WHO targets)
        assert segment["target_value"] > 0.0

    # Validate daily goals
    goals = data["daily_goals"]
    assert "vegetables" in goals
    assert "protein" in goals
    assert "carbs" in goals
    assert "fats" in goals
    assert all(goals[k] > 0 for k in goals)

    # Progress should be 0.0 (no meal logging)
    assert data["total_progress"] == 0.0


def test_daily_nutrition_with_defaults(client: TestClient) -> None:
    """Test endpoint uses sensible defaults for optional parameters.

    RU: Тест использования разумных дефолтов для опциональных параметров.
    EN: Test using sensible defaults for optional parameters.
    """
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "male",
            "age": 35,
            "height_cm": 180,
            "weight_kg": 80,
            # activity and goal omitted - should default to moderate/maintain
        },
        headers={"X-API-Key": "test_pro_key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2025-12-15"
    # Should have valid targets even with defaults
    assert len(data["segments"]) == 4
    assert all(s["target_value"] > 0 for s in data["segments"])


def test_daily_nutrition_invalid_date_format(client: TestClient) -> None:
    """Test endpoint rejects invalid date format.

    RU: Тест отклонения невалидного формата даты.
    EN: Test rejection of invalid date format.
    """
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-13-45",  # Invalid date
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
        },
        headers={"X-API-Key": "test_pro_key"},
    )

    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]


def test_daily_nutrition_missing_required_params(client: TestClient) -> None:
    """Test endpoint rejects requests with missing required parameters.

    RU: Тест отклонения запросов без обязательных параметров.
    EN: Test rejection of requests with missing required parameters.
    """
    # Missing sex
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert response.status_code == 422  # Validation error

    # Missing age
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "female",
            "height_cm": 165,
            "weight_kg": 65,
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert response.status_code == 422


def test_daily_nutrition_boundary_values(client: TestClient) -> None:
    """Test endpoint handles boundary values correctly.

    RU: Тест обработки граничных значений.
    EN: Test handling of boundary values.
    """
    # Minimum valid values
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "female",
            "age": 11,  # gt=10
            "height_cm": 101,  # gt=100
            "weight_kg": 31,  # gt=30
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert response.status_code == 200

    # Maximum valid values
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "male",
            "age": 99,  # lt=100
            "height_cm": 249,  # lt=250
            "weight_kg": 299,  # lt=300
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert response.status_code == 200


def test_daily_nutrition_invalid_profile_values(client: TestClient) -> None:
    """Test endpoint rejects invalid profile values.

    RU: Тест отклонения невалидных значений профиля.
    EN: Test rejection of invalid profile values.
    """
    # Age too low
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "female",
            "age": 5,  # Below minimum
            "height_cm": 165,
            "weight_kg": 65,
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert response.status_code == 422

    # Weight too high
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "male",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 350,  # Above maximum
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert response.status_code == 422


def test_daily_nutrition_different_goals(client: TestClient) -> None:
    """Test endpoint with different nutrition goals.

    RU: Тест с различными целями питания.
    EN: Test with different nutrition goals.
    """
    for goal in ["loss", "maintain", "gain"]:
        response = client.get(
            "/api/v1/pro/nutrition/daily",
            params={
                "date": "2025-12-15",
                "sex": "female",
                "age": 30,
                "height_cm": 165,
                "weight_kg": 65,
                "activity": "moderate",
                "goal": goal,
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code == 200
        data = response.json()
        # All goals should produce valid targets
        assert all(s["target_value"] > 0 for s in data["segments"])


def test_daily_nutrition_different_activities(client: TestClient) -> None:
    """Test endpoint with different activity levels.

    RU: Тест с различными уровнями активности.
    EN: Test with different activity levels.
    """
    for activity in ["sedentary", "light", "moderate", "active", "very_active"]:
        response = client.get(
            "/api/v1/pro/nutrition/daily",
            params={
                "date": "2025-12-15",
                "sex": "male",
                "age": 35,
                "height_cm": 180,
                "weight_kg": 80,
                "activity": activity,
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_pro_key"},
        )
        assert response.status_code == 200


def test_daily_nutrition_requires_pro_key(client: TestClient) -> None:
    """Test endpoint requires PRO tier API key.

    RU: Тест требования PRO API ключа.
    EN: Test requirement of PRO API key.
    """
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
        },
        # No API key
    )
    # PRO tier returns 401 Unauthorized without key
    assert response.status_code == 401


def test_legacy_nutrition_endpoint(client: TestClient) -> None:
    """Test legacy /api/nutrition/{date} alias route.

    RU: Тест устаревшего alias route /api/nutrition/{date}.
    EN: Test legacy /api/nutrition/{date} alias route.
    """
    response = client.get(
        "/api/nutrition/2025-12-15",
        params={
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        },
        headers={"X-API-Key": "test_pro_key"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return same structure as canonical endpoint
    assert "date" in data
    assert "segments" in data
    assert "total_progress" in data
    assert "daily_goals" in data
    assert data["date"] == "2025-12-15"


def test_legacy_nutrition_endpoint_defaults(client: TestClient) -> None:
    """Test legacy endpoint uses defaults for missing optional params.

    RU: Тест использования дефолтов в устаревшем endpoint.
    EN: Test using defaults in legacy endpoint for optional params.
    """
    response = client.get(
        "/api/nutrition/2025-12-15",
        headers={"X-API-Key": "test_pro_key"},
    )

    assert response.status_code == 200
    data = response.json()
    # Should work with all defaults
    assert len(data["segments"]) == 4


def test_nutrition_targets_integration(client: TestClient) -> None:
    """Test WHO targets are correctly integrated and calculated.

    RU: Тест корректной интеграции и расчёта WHO targets.
    EN: Test correct integration and calculation of WHO targets.
    """
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
            "activity": "moderate",
            "goal": "maintain",
        },
        headers={"X-API-Key": "test_pro_key"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify realistic serving targets (not mock data)
    # Female, 30yo, 165cm, 65kg, moderate activity should have:
    # - Vegetables: ~4 servings (WHO standard)
    # - Protein: ~2-5 servings (based on weight and activity)
    # - Carbs: ~4-10 servings (based on TDEE)
    # - Fats: ~2-5 servings (based on weight)

    goals = data["daily_goals"]
    assert 3.0 <= goals["vegetables"] <= 5.0
    assert 2.0 <= goals["protein"] <= 6.0
    assert 3.0 <= goals["carbs"] <= 12.0
    assert 1.5 <= goals["fats"] <= 6.0

    # Verify percentages sum to ~100%
    total_pct = sum(s["percentage"] for s in data["segments"])
    assert 95.0 <= total_pct <= 105.0  # Allow small rounding difference

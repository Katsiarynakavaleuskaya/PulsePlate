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

from unittest.mock import patch

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
    """Test endpoint rejects invalid date format (semantic validation).

    RU: Тест отклонения невалидного формата даты (семантическая валидация).
    EN: Test rejection of invalid date format (semantic validation).
    """
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-13-45",  # Passes regex but invalid month/day
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
        },
        headers={"X-API-Key": "test_pro_key"},
    )

    # Date.fromisoformat() raises ValueError → 400
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]


def test_daily_nutrition_invalid_semantic_date(client: TestClient) -> None:
    """Test endpoint rejects semantically invalid date (e.g., Feb 30).

    RU: Тест отклонения семантически невалидной даты (например, 30 февраля).
    EN: Test rejection of semantically invalid date (e.g., Feb 30).
    """
    response = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-02-30",  # Passes regex but invalid calendar date
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
            "age": 10,  # ge=10 (inclusive)
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
            "age": 100,  # le=100 (inclusive)
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


@pytest.mark.parametrize("goal", ["loss", "maintain", "gain"])
def test_daily_nutrition_different_goals(client: TestClient, goal: str) -> None:
    """Test endpoint with different nutrition goals.

    RU: Тест с различными целями питания.
    EN: Test with different nutrition goals.
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
            "goal": goal,
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert response.status_code == 200
    data = response.json()
    # All goals should produce valid targets
    assert all(s["target_value"] > 0 for s in data["segments"])


@pytest.mark.parametrize("activity", ["sedentary", "light", "moderate", "active", "very_active"])
def test_daily_nutrition_different_activities(client: TestClient, activity: str) -> None:
    """Test endpoint with different activity levels.

    RU: Тест с различными уровнями активности.
    EN: Test with different activity levels.
    """
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


@pytest.mark.parametrize(
    "headers, expected_status",
    [
        ({}, 401),
        ({"X-API-Key": "not_a_pro_key"}, 403),
    ],
)
def test_legacy_nutrition_endpoint_auth_guard_contract(
    client: TestClient,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    """Legacy alias must enforce tier guard and return JSON error contract."""
    response = client.get("/api/nutrition/2025-12-15", headers=headers)

    assert response.status_code == expected_status
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()
    assert isinstance(payload, dict)
    assert "detail" in payload


def test_legacy_nutrition_endpoint_hidden_from_openapi(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "/api/nutrition/{date_str}" not in schema.get("paths", {})


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


def _get_legacy_alias_metric_value() -> float:
    # prom-client API: stable, no scraping needed
    from prometheus_client import REGISTRY

    value = REGISTRY.get_sample_value(
        "legacy_alias_requests_total",
        {"alias_route": "/api/nutrition/{date_str}"},
    )
    return float(value or 0.0)


LEGACY_ALIAS_ROUTE = "/api/nutrition/{date_str}"


def _reset_legacy_alias_counter_for_tests() -> None:
    """Reset legacy alias counter to ensure deterministic tests.

    RU: Сбрасывает счётчик legacy alias для детерминизма тестов.
    EN: Resets legacy alias counter for deterministic tests.
    """
    # IMPORTANT: import by module path (avoid `from app import metrics` due to app/__init__.py shim).
    import importlib

    app_metrics = importlib.import_module("app.metrics")
    counter = getattr(app_metrics, "LEGACY_ALIAS_REQUESTS_TOTAL", None)
    if counter is None:
        pytest.skip("prometheus_client not available (legacy alias counter disabled)")

    child = counter.labels(alias_route=LEGACY_ALIAS_ROUTE)
    # prom-client internals: Counter child uses a ValueClass with .set()
    # RU: тестовая изоляция; прод-код не трогаем.
    # EN: test isolation; do not touch prod behavior.
    child._value.set(0)  # type: ignore[attr-defined]


def test_legacy_alias_increments_counter(client: TestClient) -> None:
    _reset_legacy_alias_counter_for_tests()
    before = _get_legacy_alias_metric_value()

    resp = client.get(
        "/api/nutrition/2025-12-15",
        headers={"X-API-Key": "test_pro_key"},
    )
    assert resp.status_code == 200

    after = _get_legacy_alias_metric_value()
    assert after == before + 1.0


def test_canonical_does_not_increment_legacy_counter(client: TestClient) -> None:
    _reset_legacy_alias_counter_for_tests()
    before = _get_legacy_alias_metric_value()

    resp = client.get(
        "/api/v1/pro/nutrition/daily",
        params={
            "date": "2025-12-15",
            "sex": "female",
            "age": 30,
            "height_cm": 165,
            "weight_kg": 65,
        },
        headers={"X-API-Key": "test_pro_key"},
    )
    assert resp.status_code == 200

    after = _get_legacy_alias_metric_value()
    assert after == before


def test_app_metrics_build_legacy_alias_requests_total_returns_none_on_importerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: app.metrics must handle missing prometheus_client deterministically."""
    import app.metrics as app_metrics

    monkeypatch.setattr(
        app_metrics, "_import_prometheus", lambda: (_ for _ in ()).throw(ImportError("boom"))
    )
    assert app_metrics._build_legacy_alias_requests_total() is None


def test_app_metrics_build_legacy_alias_requests_total_returns_none_on_duplicate_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard: duplicate metric registration must disable legacy counter (no crash)."""
    import app.metrics as app_metrics

    def _bad_counter(*_args: object, **_kwargs: object) -> object:
        raise ValueError("duplicate metric name")

    monkeypatch.setattr(app_metrics, "_import_prometheus", lambda: _bad_counter)
    assert app_metrics._build_legacy_alias_requests_total() is None


def test_record_legacy_alias_hit_noop_when_not_in_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """record_legacy_alias_hit must be low-cardinality (allowlist-only)."""
    import app.metrics as app_metrics

    class _ExplodeCounter:
        def labels(self, *, alias_route: str) -> object:  # pragma: no cover
            raise RuntimeError(f"labels called unexpectedly for {alias_route}")

    monkeypatch.setattr(app_metrics, "LEGACY_ALIAS_REQUESTS_TOTAL", _ExplodeCounter())
    app_metrics.record_legacy_alias_hit("/not-allowed")


def test_record_legacy_alias_hit_noop_when_counter_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """record_legacy_alias_hit must be best-effort when counter is disabled."""
    import app.metrics as app_metrics

    monkeypatch.setattr(app_metrics, "LEGACY_ALIAS_REQUESTS_TOTAL", None)
    app_metrics.record_legacy_alias_hit("/api/nutrition/{date_str}")


def test_record_legacy_alias_hit_swallows_counter_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """record_legacy_alias_hit must never raise (observability best-effort)."""
    import app.metrics as app_metrics

    class _BadChild:
        def inc(self, amount: float = 1.0) -> None:
            raise RuntimeError("boom")

    class _BadCounter:
        def labels(self, *, alias_route: str) -> _BadChild:
            assert alias_route == "/api/nutrition/{date_str}"
            return _BadChild()

    monkeypatch.setattr(app_metrics, "LEGACY_ALIAS_REQUESTS_TOTAL", _BadCounter())
    app_metrics.record_legacy_alias_hit("/api/nutrition/{date_str}")


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

    # NOTE: Ranges are coupled to current WHO/EFSA target formulas in build_nutrition_targets.
    # RU: Диапазоны привязаны к текущим формулам WHO/EFSA в build_nutrition_targets.
    # EN: If formulas change, adjust these ranges rather than removing the checks.
    goals = data["daily_goals"]
    assert 3.0 <= goals["vegetables"] <= 5.0
    assert 2.0 <= goals["protein"] <= 6.0
    assert 3.0 <= goals["carbs"] <= 12.0
    assert 1.5 <= goals["fats"] <= 6.0

    # Verify percentages sum to ~100%
    total_pct = sum(s["percentage"] for s in data["segments"])
    assert 95.0 <= total_pct <= 105.0  # Allow small rounding difference


def test_daily_nutrition_targets_calculation_failure(client: TestClient) -> None:
    """Test endpoint returns 500 when WHO targets calculation fails.

    RU: Тест возврата 500 при ошибке расчёта WHO targets.
    EN: Test 500 return when WHO targets calculation fails.
    """
    with patch("app.routers.pro.build_nutrition_targets") as mock_build:
        # Simulate internal error in targets calculation
        mock_build.side_effect = RuntimeError("Internal calculation error")

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

        assert response.status_code == 500
        # Verify generic error message (no info leak)
        assert response.json()["detail"] == "Failed to calculate nutrition targets"
        # Ensure internal error details are NOT leaked to client
        assert "Internal calculation error" not in response.json()["detail"]


def test_daily_nutrition_invalid_profile_validation(client: TestClient) -> None:
    """Test endpoint returns 400 when UserProfile validation fails.

    RU: Тест возврата 400 при ошибке валидации UserProfile.
    EN: Test 400 return when UserProfile validation fails.
    """
    with patch("app.routers.pro.UserProfile") as mock_profile:
        # Simulate validation error in UserProfile
        mock_profile.side_effect = ValueError("age must be positive")

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

        assert response.status_code == 400
        # Verify generic error message (no info leak)
        assert response.json()["detail"] == "Invalid user profile"
        # Ensure internal validation details are NOT leaked to client
        assert "age must be positive" not in response.json()["detail"]


@pytest.mark.parametrize(
    "lang,expected_name",
    [
        ("en", "Vegetables"),
        ("ru", "Овощи"),
        ("es", "Verduras"),
    ],
)
def test_daily_nutrition_localizes_segment_names(
    client: TestClient, lang: str, expected_name: str
) -> None:
    """Test endpoint returns localized segment names based on lang parameter.

    RU: Тест возврата локализованных названий сегментов на основе lang параметра.
    EN: Test endpoint returns localized segment names based on lang parameter.
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
            "lang": lang,
        },
        headers={"X-API-Key": "test_pro_key"},
    )

    assert response.status_code == 200
    data = response.json()

    # Extract all segment names
    segment_names = [s["name"] for s in data["segments"]]

    # Verify first segment (vegetables) is localized correctly
    assert (
        expected_name in segment_names
    ), f"Expected '{expected_name}' in segment names for lang={lang}, got: {segment_names}"

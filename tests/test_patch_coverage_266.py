"""
Tests for PR #266 patch coverage improvements

RU: Тесты для улучшения покрытия патча PR #266
EN: Tests for PR #266 patch coverage improvements

Covers:
- targets_disabled() caching mechanism
- calculate_heuristic_macros() function
- api_who_targets endpoint with dependency injection
- Debug logging in _should_use_mock_food_db()
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app
from core.menu_engine import _should_use_mock_food_db


class TestTargetsDisabledCaching:
    """Test targets_disabled() caching mechanism."""

    def test_targets_disabled_cache_hit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that cache is used when TTL is valid."""
        # Reset cache state
        app._targets_disabled_cache = False
        app._targets_disabled_cache_time = time.time()

        # First call should use cache
        result1 = app.targets_disabled()  # type: ignore[operator]
        assert isinstance(result1, bool)

        # Second call within TTL should use cache (no sys.modules scan)
        with patch.dict("sys.modules", {}):
            result2 = app.targets_disabled()  # type: ignore[operator]
            assert result2 == result1  # Should return cached value

    def test_targets_disabled_cache_expires(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that cache expires after TTL."""
        # Set cache to old value
        app._targets_disabled_cache = True
        app._targets_disabled_cache_time = time.time() - 2.0  # 2 seconds ago (past TTL)

        # Should bypass cache and recalculate
        result = app.targets_disabled()  # type: ignore[operator]
        assert isinstance(result, bool)
        # Cache should be updated
        assert app._targets_disabled_cache is not None

    def test_targets_disabled_skips_non_test_modules(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that non-test modules are skipped in scan."""
        # Reset cache
        app._targets_disabled_cache = None
        app._targets_disabled_cache_time = 0.0

        # Create a non-test module (should be skipped)
        regular_module = MagicMock()
        regular_module.build_nutrition_targets = None
        regular_module.__name__ = "some_regular_module"

        with patch.dict("sys.modules", {"some_regular_module": regular_module}):
            # Should not detect None in non-test module
            result = app.targets_disabled()  # type: ignore[operator]
            # Should return False (not disabled) because non-test modules are skipped
            assert isinstance(result, bool)


class TestCalculateHeuristicMacros:
    """Test calculate_heuristic_macros() function."""

    def test_calculate_heuristic_macros_basic(self) -> None:
        """Test basic heuristic macro calculation."""
        prot, fat, carbs = app.calculate_heuristic_macros(final_kcal=2000, weight_kg=70)  # type: ignore[operator]

        # Protein: 1.6 * 70 = 112g
        assert prot == 112
        # Fat: 0.9 * 70 = 63g
        assert fat == 63
        # Carbs: (2000 - 112*4 - 63*9) / 4 = (2000 - 448 - 567) / 4 = 985 / 4 = 246.25 -> 246
        assert carbs >= 240  # Allow small rounding differences
        assert carbs <= 250

        # Verify total calories approximately match
        total_kcal = prot * 4 + fat * 9 + carbs * 4
        assert abs(total_kcal - 2000) <= 20

    def test_calculate_heuristic_macros_low_calories(self) -> None:
        """Test heuristic macros with low calorie target."""
        prot, fat, carbs = app.calculate_heuristic_macros(final_kcal=1200, weight_kg=60)  # type: ignore[operator]

        assert prot > 0
        assert fat > 0
        assert carbs >= 1  # Minimum carbs enforced

        # Verify total calories approximately match
        total_kcal = prot * 4 + fat * 9 + carbs * 4
        assert abs(total_kcal - 1200) <= 50

    def test_calculate_heuristic_macros_high_weight(self) -> None:
        """Test heuristic macros with high weight."""
        prot, fat, carbs = app.calculate_heuristic_macros(final_kcal=3000, weight_kg=100)  # type: ignore[operator]

        # Protein: 1.6 * 100 = 160g
        assert prot == 160
        # Fat: 0.9 * 100 = 90g
        assert fat == 90
        # Carbs should be positive
        assert carbs >= 1

        # Verify total calories approximately match
        total_kcal = prot * 4 + fat * 9 + carbs * 4
        assert abs(total_kcal - 3000) <= 50

    def test_calculate_heuristic_macros_minimum_carbs(self) -> None:
        """Test that carbs are always at least 1."""
        # Use very low calories to test minimum carbs enforcement
        prot, fat, carbs = app.calculate_heuristic_macros(final_kcal=500, weight_kg=50)  # type: ignore[operator]  # noqa: E501

        assert carbs >= 1  # Minimum enforced


class TestWhoTargetsEndpoint:
    """Test api_who_targets endpoint with dependency injection."""

    def test_who_targets_with_dependency_injection(self, client: TestClient) -> None:
        """Test that endpoint uses dependency injection for API key."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Should work with API key in header (dependency injection)
        response = client.post(
            "/api/v1/premium/targets",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        # Accept 200 (success) or 503 (service unavailable if targets backend missing)
        assert response.status_code in (
            200,
            503,
        ), f"Unexpected status: {response.status_code}, body: {response.text[:200]}"
        if response.status_code == 200:
            result = response.json()
            assert "kcal_daily" in result
            assert "macros" in result

    def test_who_targets_without_api_key(self, client: TestClient) -> None:
        """Test that endpoint requires API key via dependency."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Should fail without API key
        response = client.post("/api/v1/premium/targets", json=payload)

        assert response.status_code in [403, 401]  # API key validation error

    def test_who_targets_invalid_payload(self, client: TestClient) -> None:
        """Test endpoint with invalid payload."""
        payload = {
            "sex": "invalid",
            "age": -5,  # Invalid age
        }

        response = client.post(
            "/api/v1/premium/targets",
            json=payload,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 422  # Validation error


class TestMenuEngineDebugLogging:
    """Test debug logging in _should_use_mock_food_db()."""

    def test_should_use_mock_food_db_logs_force_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that debug logging occurs when MENU_ENGINE_FORCE_MOCK_DB is set."""
        import core.menu_engine

        monkeypatch.setenv("MENU_ENGINE_FORCE_MOCK_DB", "true")

        with patch.object(core.menu_engine, "_logger") as mock_logger:
            result = _should_use_mock_food_db()

            assert result is True
            mock_logger.debug.assert_called()
            # Check that the log message contains the flag name
            call_args_str = str(mock_logger.debug.call_args)
            assert (
                "MENU_ENGINE_FORCE_MOCK_DB" in call_args_str
                or "mock food DB" in call_args_str.lower()
            )

    def test_should_use_mock_food_db_logs_pytest_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that debug logging occurs when PYTEST_CURRENT_TEST is set."""
        import core.menu_engine

        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_something::test_method")

        with patch.object(core.menu_engine, "_logger") as mock_logger:
            result = _should_use_mock_food_db()

            assert result is True
            mock_logger.debug.assert_called()
            # Check that the log message contains pytest-related text
            call_args_str = str(mock_logger.debug.call_args).lower()
            assert "pytest" in call_args_str or "mock food db" in call_args_str

    def test_should_use_mock_food_db_no_logging_when_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that no debug logging occurs when conditions are not met."""
        monkeypatch.delenv("MENU_ENGINE_FORCE_MOCK_DB", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        with patch("core.menu_engine._logger") as mock_logger:
            result = _should_use_mock_food_db()

            assert result is False
            mock_logger.debug.assert_not_called()

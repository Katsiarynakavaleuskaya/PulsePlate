"""
Refactored tests for app.py coverage with proper fixtures and isolation.

RU: Рефакторенные тесты для покрытия app.py с правильными фикстурами и изоляцией.
EN: Refactored tests for app.py coverage with proper fixtures and isolation.

Key improvements:
- Uses pytest fixtures instead of manual sys.modules manipulation
- Proper environment isolation without os.environ.clear()
- Real behavior verification instead of superficial checks
- Better structure and maintainability
- Parametrized tests for better performance
- Helper functions to reduce duplication
"""

from __future__ import annotations

import asyncio
import importlib
from types import ModuleType
from typing import TYPE_CHECKING, Any, AsyncContextManager, Callable, Generator, cast
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app

if TYPE_CHECKING:
    from typing_extensions import Self


# ============================================================================
# Helper functions to reduce duplication
# ============================================================================


def reload_app_with_env(
    fresh_app: ModuleType, monkeypatch: pytest.MonkeyPatch, env_vars: dict[str, str | None]
) -> ModuleType:
    """Reload app module with specified environment variables.

    RU: Перезагружает модуль app с указанными переменными окружения.
    EN: Reloads app module with specified environment variables.

    Args:
        fresh_app: The app module to reload
        monkeypatch: pytest monkeypatch fixture
        env_vars: Dictionary of environment variables to set/delete
                  Use None value to delete a variable

    Returns:
        Reloaded app module
    """
    for key, value in env_vars.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    importlib.reload(fresh_app)
    return fresh_app


# ============================================================================
# Test classes
# ============================================================================


class TestAPIKeyModes:
    """Tests for various API key modes and branches.

    RU: Тесты различных режимов API ключей и веток кода.
    EN: Tests for various API key modes and code branches.
    """

    def test_api_key_strict_mode_valid_key(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test strict mode with valid key."""
        app_module = reload_app_with_env(fresh_app, monkeypatch, {"API_KEY": "test-secret-key"})
        result = getattr(app_module, "get_api_key")("test-secret-key")
        assert result == "test-secret-key"

    def test_api_key_strict_mode_invalid_key(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test strict mode with invalid key."""
        app_module = reload_app_with_env(fresh_app, monkeypatch, {"API_KEY": "test-secret-key"})
        with pytest.raises(HTTPException) as exc_info:
            getattr(app_module, "get_api_key")("wrong-key")
        assert exc_info.value.status_code == 403
        assert "Invalid API Key" in exc_info.value.detail

    def test_api_key_strict_mode_missing_key(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test strict mode with missing key parameter."""
        app_module = reload_app_with_env(fresh_app, monkeypatch, {"API_KEY": "test-secret-key"})
        with pytest.raises(HTTPException) as exc_info:
            getattr(app_module, "get_api_key")(
                None
            )  # None is intentionally passed to test error handling
        assert exc_info.value.status_code == 403

    def test_api_key_strict_mode_pytest_test_key(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test strict mode accepts 'test' key when PYTEST_CURRENT_TEST is set."""
        app_module = reload_app_with_env(
            fresh_app,
            monkeypatch,
            {"API_KEY": "test-secret-key", "PYTEST_CURRENT_TEST": "test_something"},
        )
        # Should accept both the configured key and 'test'
        assert getattr(app_module, "get_api_key")("test-secret-key") == "test-secret-key"
        assert getattr(app_module, "get_api_key")("test") == "test"

    def test_api_key_required_mode_without_key(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test API_KEY_REQUIRED=true but API_KEY not set."""
        app_module = reload_app_with_env(
            fresh_app,
            monkeypatch,
            {
                "API_KEY": None,  # Delete
                "API_KEY_REQUIRED": "true",
                "PYTEST_CURRENT_TEST": None,  # Delete
            },
        )
        with pytest.raises(HTTPException) as exc_info:
            getattr(app_module, "get_api_key")("any-token")
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail.lower()
        assert "required" in detail and "configured" in detail

    @pytest.mark.parametrize(
        "token,expected_error",
        [
            (None, "Missing API Key"),
            ("x", "Invalid API Key"),  # Too short
            ("invalid", "Invalid API Key"),  # Forbidden token
            ("invalid_key", "Invalid API Key"),
            ("wrong", "Invalid API Key"),
            ("bad", "Invalid API Key"),
            ("null", "Invalid API Key"),
        ],
    )
    def test_api_key_lenient_mode_invalid_tokens(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
        token: str | None,
        expected_error: str,
    ) -> None:
        """Test lenient mode with various invalid tokens (parametrized for performance)."""
        app_module = reload_app_with_env(
            fresh_app,
            monkeypatch,
            {
                "API_KEY": None,  # Delete
                "API_KEY_REQUIRED": None,  # Delete
                "APP_ENV": "test",
            },
        )
        with pytest.raises(HTTPException) as exc_info:
            getattr(app_module, "get_api_key")(token)  # token can be None in parametrized test
        assert exc_info.value.status_code == 403
        assert expected_error in exc_info.value.detail

    def test_api_key_lenient_mode_valid_token(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test lenient mode with valid token."""
        app_module = reload_app_with_env(
            fresh_app,
            monkeypatch,
            {
                "API_KEY": None,  # Delete
                "API_KEY_REQUIRED": None,  # Delete
                "APP_ENV": "test",
            },
        )
        result = getattr(app_module, "get_api_key")("valid-test-token")
        assert result == "valid-test-token"

    def test_api_key_production_without_dev_mode(
        self,
        fresh_app: ModuleType,
        production_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test production environment without dev override requires configured key."""
        app_module = reload_app_with_env(
            fresh_app,
            monkeypatch,
            {
                "API_KEY": None,
                "APP_ENV": "production",
                "ALLOW_DEV_API_KEY": "false",
                "PYTEST_CURRENT_TEST": None,
            },
        )
        with pytest.raises(HTTPException) as exc_info:
            getattr(app_module, "get_api_key")("any-token")
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail.lower()
        assert "required" in detail and "configured" in detail

    def test_api_key_dev_mode_override(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test ALLOW_DEV_API_KEY=true enables dev mode even in production."""
        app_module = reload_app_with_env(
            fresh_app,
            monkeypatch,
            {
                "API_KEY": None,  # Delete
                "APP_ENV": "production",
                "ALLOW_DEV_API_KEY": "true",
                "PYTEST_CURRENT_TEST": None,  # Delete
            },
        )
        # Should accept valid tokens in dev mode
        result = getattr(app_module, "get_api_key")("valid-dev-token")
        assert result == "valid-dev-token"

    def test_api_key_mixed_modes(
        self,
        fresh_app: ModuleType,
        clean_env: Generator[None, None, None],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test mixed mode: API_KEY set but API_KEY_REQUIRED=false."""
        app_module = reload_app_with_env(
            fresh_app, monkeypatch, {"API_KEY": "configured-key", "API_KEY_REQUIRED": "false"}
        )
        # Should still use strict mode when API_KEY is set
        assert getattr(app_module, "get_api_key")("configured-key") == "configured-key"
        with pytest.raises(HTTPException):
            getattr(app_module, "get_api_key")("other-key")


class TestMetricsFallbacks:
    """Tests for metrics endpoint fallbacks.

    RU: Тесты fallback'ов метрик.
    EN: Tests for metrics endpoint fallbacks.
    """

    def test_metrics_endpoint_structure(self, client: TestClient) -> None:
        """Test /metrics endpoint returns valid response (fallback when Prometheus unavailable)."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        # When Prometheus is not available, endpoint returns JSON error message
        assert isinstance(data, dict)
        assert "error" in data
        assert "Prometheus" in data["error"]

    def test_metrics_endpoint_content_type(self, client: TestClient) -> None:
        """Test /metrics endpoint has correct content type (JSON when Prometheus unavailable)."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # When Prometheus unavailable, returns JSON
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type or "json" in content_type.lower()


class TestVisualizationFallbacks:
    """Tests for visualization fallbacks.

    RU: Тесты fallback'ов визуализации.
    EN: Tests for visualization fallbacks.
    """

    def test_bmi_without_matplotlib(
        self,
        disable_matplotlib: Generator[None, None, None],
        client: TestClient,
    ) -> None:
        """Test BMI endpoint without matplotlib."""
        response = client.post(
            "/bmi", json={"weight_kg": 70, "height_m": 1.70, "include_chart": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert isinstance(data["bmi"], (int, float))
        # Visualization should not be available
        assert (
            "visualization" not in data or data.get("visualization", {}).get("available") is False
        )

    def test_bmi_without_visualization_function(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test BMI endpoint when visualization function is None."""
        monkeypatch.setattr("app.generate_bmi_visualization", None)

        response = client.post(
            "/bmi", json={"weight_kg": 70, "height_m": 1.70, "include_chart": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        # Should not have visualization when function is None
        assert (
            "visualization" not in data or data.get("visualization", {}).get("available") is False
        )

    def test_bmi_visualization_unavailable_result(
        self, mock_visualization: MagicMock, client: TestClient
    ) -> None:
        """Test BMI when visualization returns unavailable."""
        mock_visualization.return_value = {
            "available": False,
            "message": "Visualization unavailable",
        }

        response = client.post(
            "/bmi", json={"weight_kg": 70, "height_m": 1.70, "include_chart": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data

        # Verify visualization function was called
        mock_visualization.assert_called_once()
        call_args = mock_visualization.call_args
        assert call_args is not None
        # Should have been called with BMI value and other parameters
        assert len(call_args[0]) > 0 or len(call_args[1]) > 0

    def test_bmi_visualization_available_result(
        self, mock_visualization: MagicMock, client: TestClient
    ) -> None:
        """Test BMI when visualization is available."""
        mock_visualization.return_value = {
            "available": True,
            "image_url": "data:image/png;base64,...",
            "message": "Visualization generated",
        }

        response = client.post(
            "/bmi", json={"weight_kg": 70, "height_m": 1.70, "include_chart": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data

        # Verify visualization was called and result included
        mock_visualization.assert_called_once()
        if "visualization" in data:
            viz_data = data["visualization"]
            assert viz_data.get("available") is True


class TestImportFallbacks:
    """Tests for import fallback branches.

    RU: Тесты import fallback веток.
    EN: Tests for import fallback branches.
    """

    def test_nutrition_core_fallback_function(self) -> None:
        """Test fallback function when nutrition_core is unavailable."""
        # Verify fallback function exists and works
        assert hasattr(app, "get_activity_factor")
        assert callable(app.get_activity_factor)

        # Test fallback function behavior
        result = app.get_activity_factor("moderate")
        assert isinstance(result, (int, float))
        assert result > 0

    def test_app_initialization_with_fallbacks(self) -> None:
        """Test app initializes successfully even with import fallbacks."""
        assert app.app is not None
        assert hasattr(app.app, "title")
        assert app.app.title == "PulsePlate"

    def test_utility_helpers_exposed(self) -> None:
        """Test utility helpers are available from core.utils module."""
        from core.utils import get_activity_factor, resolve_attr

        assert callable(get_activity_factor)
        assert callable(resolve_attr)


class TestLifespanFallbacks:
    """Tests for lifespan startup/shutdown branches.

    RU: Тесты lifespan startup/shutdown веток.
    EN: Tests for lifespan startup/shutdown branches.
    """

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful lifespan startup."""
        startup_called = False
        shutdown_called = False

        async def mock_startup(*_: Any, **__: Any) -> None:
            nonlocal startup_called
            startup_called = True

        async def mock_shutdown(*_: Any, **__: Any) -> None:
            nonlocal shutdown_called
            shutdown_called = True

        monkeypatch.setattr("app.start_background_updates", mock_startup)
        monkeypatch.setattr("app.stop_background_updates", mock_shutdown)

        mock_app = MagicMock()

        lifespan_func = cast(
            Callable[[Any], AsyncContextManager[Any]], getattr(app, "lifespan", None)
        )
        async with lifespan_func(mock_app):
            # Startup should have been called
            assert startup_called

        # Shutdown should have been called
        assert shutdown_called

    @pytest.mark.asyncio
    async def test_lifespan_startup_error_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test lifespan handles startup errors gracefully."""
        startup_error = Exception("Test startup error")

        async def mock_startup(*_: Any, **__: Any) -> None:
            raise startup_error

        shutdown_called = False

        async def verify_shutdown(*_: Any, **__: Any) -> None:
            nonlocal shutdown_called
            shutdown_called = True

        monkeypatch.setattr("app.start_background_updates", mock_startup)
        monkeypatch.setattr("app.stop_background_updates", verify_shutdown)

        mock_app = MagicMock()

        # Should not raise, should handle error gracefully
        lifespan_func = cast(
            Callable[[Any], AsyncContextManager[Any]], getattr(app, "lifespan", None)
        )
        async with lifespan_func(mock_app):
            pass

        # Shutdown should still be called
        assert shutdown_called

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_error_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test lifespan handles shutdown errors gracefully."""
        shutdown_error = Exception("Test shutdown error")

        async def mock_startup(*_: Any, **__: Any) -> None:
            pass

        async def mock_shutdown(*_: Any, **__: Any) -> None:
            raise shutdown_error

        monkeypatch.setattr("app.start_background_updates", mock_startup)
        monkeypatch.setattr("app.stop_background_updates", mock_shutdown)

        mock_app = MagicMock()

        # Should not raise, should handle shutdown error gracefully
        lifespan_func = cast(
            Callable[[Any], AsyncContextManager[Any]], getattr(app, "lifespan", None)
        )
        async with lifespan_func(mock_app):
            pass

        # Test completes without exception


class TestEdgeCases:
    """Tests for edge cases and basic endpoints.

    RU: Тесты edge cases и базовых эндпоинтов.
    EN: Tests for edge cases and basic endpoints.
    """

    def test_root_endpoint_structure(self, client: TestClient) -> None:
        """Test root endpoint returns valid response."""
        response = client.get("/")
        assert response.status_code == 200
        # Should return some content (could be JSON, HTML, or text)
        assert len(response.content) > 0

    def test_health_endpoint_structure(self, client: TestClient) -> None:
        """Test /health endpoint returns valid JSON structure."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        # Verify status is a string
        assert isinstance(data["status"], str)

    def test_health_endpoint_content(self, client: TestClient) -> None:
        """Test /health endpoint content details."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Should have status field
        assert data["status"] in ["ok", "healthy", "up", "running"]

    @pytest.mark.parametrize(
        "category,lang,expected",
        [
            ("Normal weight", "en", "Healthy weight"),
            ("Избыточная масса", "ru", "Избыточный вес"),
            ("Other", "en", "Other"),
            ("Unknown", "en", "Unknown"),
        ],
    )
    def test_legacy_category_label_function(self, category: str, lang: str, expected: str) -> None:
        """Test legacy_category_label function with various inputs (parametrized)."""
        result = getattr(app, "legacy_category_label")(category, lang)
        assert result == expected

    def test_get_update_scheduler_wrapper_exists(self) -> None:
        """Test get_update_scheduler wrapper function exists and is callable."""
        assert hasattr(app, "get_update_scheduler")
        assert callable(app.get_update_scheduler)

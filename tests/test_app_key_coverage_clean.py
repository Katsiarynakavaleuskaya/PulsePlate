"""
Чистые тесты для покрытия main.py недостающих веток
Фокус: API key режимы, метрики, визуализация, импорт fallbacks
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.routers.api_key import get_api_key
from tests._client import open_test_client


class TestAPIKeyModes:
    """Тесты различных режимов API ключей"""

    def test_api_key_strict_mode_valid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Строгий режим - правильный ключ"""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        # Тестируем функцию напрямую (env читается runtime)
        result = get_api_key("test-secret-key")
        assert result == "test-secret-key"

    def test_api_key_strict_mode_invalid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Строгий режим - неправильный ключ"""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        with pytest.raises(HTTPException) as exc_info:
            get_api_key("wrong-key")
        assert exc_info.value.status_code == 403

    def test_api_key_strict_mode_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Строгий режим - отсутствующий ключ"""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        with pytest.raises(HTTPException) as exc_info:
            get_api_key(None)
        assert exc_info.value.status_code == 403

    def test_api_key_required_mode_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """API_KEY_REQUIRED=true но API_KEY не установлен"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.setenv("API_KEY_REQUIRED", "true")

        with pytest.raises(HTTPException) as exc_info:
            get_api_key("any-token")
        assert exc_info.value.status_code == 403
        # Проверим что сообщение правильное (ожидается "API key required but not configured")
        assert (
            "required" in exc_info.value.detail.lower()
            and "configured" in exc_info.value.detail.lower()
        )

    def test_api_key_lenient_mode_missing_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Мягкий режим - отсутствующий токен"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

        with pytest.raises(HTTPException) as exc_info:
            get_api_key(None)
        assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_short_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Мягкий режим - слишком короткий токен"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

        with pytest.raises(HTTPException) as exc_info:
            get_api_key("x")  # Только 1 символ
        assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_forbidden_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Мягкий режим - запрещённые токены"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

        forbidden = ["invalid", "invalid_key", "wrong", "bad", "null"]

        for token in forbidden:
            with pytest.raises(HTTPException) as exc_info:
                get_api_key(token)
            assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_valid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Мягкий режим - валидный токен"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

        # В мягком режиме без API_KEY должен принимать валидные токены (длиной >= 4)
        result = get_api_key("valid-test-token")
        assert result == "valid-test-token"


class TestMetricsFallbacks:
    """Тесты fallback'ов метрик"""

    def test_metrics_endpoint_responds(self) -> None:
        """Тест, что /metrics эндпоинт отвечает (smoke test, не контролирует наличие prometheus)."""
        # Smoke test: metrics endpoint should respond with 200
        from app.main import app as main_app

        with open_test_client(main_app) as client:
            response = client.get("/metrics")
            assert response.status_code == 200
            # Should return Prometheus metrics text (not JSON)
            content = response.content.decode()
            assert "python_info" in content or "# HELP" in content or len(content) > 0

    def test_metrics_endpoint_responds_in_current_env(self) -> None:
        """Тест, что /metrics отвечает в текущей среде (smoke test, не контролирует prometheus availability)."""
        # Smoke test: metrics endpoint should respond
        from app.main import app as main_app

        with open_test_client(main_app) as client:
            response = client.get("/metrics")
            assert response.status_code == 200


class TestEdgeCases:
    """Тесты edge cases для main.py"""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Тест корневого эндпоинта"""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self, client: TestClient) -> None:
        """Тест health эндпоинта"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

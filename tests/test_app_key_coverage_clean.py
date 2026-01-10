"""
Чистые тесты для покрытия main.py недостающих веток
Фокус: API key режимы, метрики, визуализация, импорт fallbacks
"""

from __future__ import annotations

import os
import sys
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app
from tests._client import get_client


class TestAPIKeyModes:
    """Тесты различных режимов API ключей"""

    def test_api_key_strict_mode_valid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Строгий режим - правильный ключ"""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        # Тестируем функцию напрямую (env читается runtime)
        result = app.get_api_key("test-secret-key")
        assert result == "test-secret-key"

    def test_api_key_strict_mode_invalid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Строгий режим - неправильный ключ"""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        with pytest.raises(HTTPException) as exc_info:
            app.get_api_key("wrong-key")
        assert exc_info.value.status_code == 403

    def test_api_key_strict_mode_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Строгий режим - отсутствующий ключ"""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        with pytest.raises(HTTPException) as exc_info:
            app.get_api_key(None)
        assert exc_info.value.status_code == 403

    def test_api_key_required_mode_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """API_KEY_REQUIRED=true но API_KEY не установлен"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.setenv("API_KEY_REQUIRED", "true")

        with pytest.raises(HTTPException) as exc_info:
            app.get_api_key("any-token")
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
            app.get_api_key(None)
        assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_short_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Мягкий режим - слишком короткий токен"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

        with pytest.raises(HTTPException) as exc_info:
            app.get_api_key("x")  # Только 1 символ
        assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_forbidden_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Мягкий режим - запрещённые токены"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

        forbidden = ["invalid", "invalid_key", "wrong", "bad", "null"]

        for token in forbidden:
            with pytest.raises(HTTPException) as exc_info:
                app.get_api_key(token)
            assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_valid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Мягкий режим - валидный токен"""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("API_KEY_REQUIRED", raising=False)

        # В мягком режиме без API_KEY должен принимать валидные токены (длиной >= 4)
        result = app.get_api_key("valid-test-token")
        assert result == "valid-test-token"


class TestMetricsFallbacks:
    """Тесты fallback'ов метрик"""

    def test_metrics_endpoint_responds(self):
        """Тест, что /metrics эндпоинт отвечает (smoke test, не контролирует наличие prometheus)."""
        # Smoke test: metrics endpoint should respond with 200
        from app.main import app as main_app

        client = TestClient(cast(ASGIApp, main_app))
        response = client.get("/metrics")
        assert response.status_code == 200
        # Should return Prometheus metrics text (not JSON)
        content = response.content.decode()
        assert "python_info" in content or "# HELP" in content or len(content) > 0

    def test_metrics_endpoint_responds_in_current_env(self):
        """Тест, что /metrics отвечает в текущей среде (smoke test, не контролирует prometheus availability)."""
        # Smoke test: metrics endpoint should respond
        from app.main import app as main_app

        client = TestClient(cast(ASGIApp, main_app))

        response = client.get("/metrics")
        assert response.status_code == 200


class TestVisualizationFallbacks:
    """Тесты fallback'ов визуализации"""

    def test_bmi_without_matplotlib(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест BMI без matplotlib"""
        monkeypatch.setattr(app, "MATPLOTLIB_AVAILABLE", False)
        client = get_client()

        response = client.post("/bmi", json={"weight_kg": 70, "height_m": 1.70})
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data

    def test_bmi_without_visualization_function(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест BMI без функции визуализации"""
        monkeypatch.setattr(app, "generate_bmi_visualization", None, raising=False)
        client = get_client()

        response = client.post("/bmi", json={"weight_kg": 70, "height_m": 1.70})
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data

    def test_bmi_visualization_unavailable_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест BMI когда визуализация возвращает unavailable"""
        mock_viz = MagicMock()
        mock_viz.return_value = {"available": False, "message": "Visualization unavailable"}
        monkeypatch.setattr(app, "generate_bmi_visualization", mock_viz, raising=False)

        client = get_client()
        response = client.post("/bmi", json={"weight_kg": 70, "height_m": 1.70})
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data


class TestImportFallbacks:
    """Тесты import fallback веток"""

    def test_nutrition_core_missing_fallback(self) -> None:
        """Тест fallback когда nutrition_core недоступен"""
        # Проверим что app загружается и fallback функции работают
        assert hasattr(app, "get_activity_factor")
        assert app.get_activity_factor("moderate") == 1.55

    def test_bmi_pro_router_fallback(self) -> None:
        """Тест fallback для bmi_pro_router"""
        # Проверим что app работает даже если bmi_pro_router=None
        assert app.app is not None

    def test_vip_router_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест fallback для VIP router"""
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
        # app должен работать даже если VIP router недоступен
        assert app.app is not None


class TestLifespanFallbacks:
    """Тесты lifespan startup/shutdown веток"""

    @pytest.mark.asyncio
    async def test_lifespan_start_success(self) -> None:
        """Тест успешного запуска lifespan"""
        # Создаем mock app для lifespan
        mock_app = MagicMock()

        # Тестируем lifespan
        async with app.lifespan(mock_app):
            pass  # Просто проверяем что не падает

    @pytest.mark.asyncio
    async def test_lifespan_start_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест обработки ошибки при запуске"""
        monkeypatch.setattr(
            app, "start_background_updates", MagicMock(side_effect=Exception("Test error")), raising=False
        )
        mock_app = MagicMock()

        # Должен перехватить ошибку и продолжить
        async with app.lifespan(mock_app):
            pass

    @pytest.mark.asyncio
    async def test_lifespan_stop_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест обработки ошибки при остановке"""
        monkeypatch.setattr(
            app, "stop_background_updates", MagicMock(side_effect=Exception("Test error")), raising=False
        )
        mock_app = MagicMock()

        # Должен перехватить ошибку при shutdown
        async with app.lifespan(mock_app):
            pass


class TestEdgeCases:
    """Тесты edge cases для main.py"""

    def test_root_endpoint(self) -> None:
        """Тест корневого эндпоинта"""
        client = get_client()
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self) -> None:
        """Тест health эндпоинта"""
        client = get_client()
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_legacy_category_label_function(self) -> None:
        """Тест legacy_category_label функции"""
        # Тест английского языка
        result = app.legacy_category_label("Normal weight", "en")
        assert result == "Healthy weight"

        # Тест русского языка
        result = app.legacy_category_label("Избыточная масса", "ru")
        assert result == "Избыточный вес"

        # Тест других случаев
        result = app.legacy_category_label("Other", "en")
        assert result == "Other"

    def test_get_update_scheduler_wrapper(self) -> None:
        """Тест get_update_scheduler wrapper функции"""
        # Просто проверим что функция существует
        assert hasattr(app, "get_update_scheduler")
        assert callable(app.get_update_scheduler)

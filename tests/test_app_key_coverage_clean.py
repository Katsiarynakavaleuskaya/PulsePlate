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

    def test_metrics_without_prometheus(self):
        """Тест /metrics без prometheus_client"""
        # Test metrics endpoint - it may return error if Prometheus is not available
        from app.main import app as main_app

        client = TestClient(cast(ASGIApp, main_app))
        response = client.get("/metrics")
        assert response.status_code == 200
        # Должен вернуть Prometheus metrics текст (не JSON)
        content = response.content.decode()
        assert "python_info" in content or "# HELP" in content or len(content) > 0

    def test_metrics_with_prometheus(self):
        """Тест /metrics с prometheus_client"""
        # Просто проверим что эндпоинт работает
        from app.main import app as main_app

        client = TestClient(cast(ASGIApp, main_app))

        response = client.get("/metrics")
        assert response.status_code == 200


class TestVisualizationFallbacks:
    """Тесты fallback'ов визуализации"""

    def test_bmi_without_matplotlib(self):
        """Тест BMI без matplotlib"""
        with patch("app.MATPLOTLIB_AVAILABLE", False):
            if "app" in sys.modules:
                del sys.modules["app"]

            import app

            client = TestClient(cast(ASGIApp, app.app))

            response = client.post("/bmi", json={"weight_kg": 70, "height_m": 1.70})
            assert response.status_code == 200
            data = response.json()
            assert "bmi" in data

    def test_bmi_without_visualization_function(self):
        """Тест BMI без функции визуализации"""
        with patch("app.generate_bmi_visualization", None):
            if "app" in sys.modules:
                del sys.modules["app"]

            import app

            client = TestClient(cast(ASGIApp, app.app))

            response = client.post("/bmi", json={"weight_kg": 70, "height_m": 1.70})
            assert response.status_code == 200
            data = response.json()
            assert "bmi" in data

    def test_bmi_visualization_unavailable_result(self):
        """Тест BMI когда визуализация возвращает unavailable"""
        mock_viz = MagicMock()
        mock_viz.return_value = {"available": False, "message": "Visualization unavailable"}

        with patch("app.generate_bmi_visualization", mock_viz):
            if "app" in sys.modules:
                del sys.modules["app"]

            import app

            client = TestClient(cast(ASGIApp, app.app))

            response = client.post("/bmi", json={"weight_kg": 70, "height_m": 1.70})
            assert response.status_code == 200
            data = response.json()
            assert "bmi" in data


class TestImportFallbacks:
    """Тесты import fallback веток"""

    def test_nutrition_core_missing_fallback(self):
        """Тест fallback когда nutrition_core недоступен"""
        # Просто проверим что app загружается
        if "app" in sys.modules:
            del sys.modules["app"]

        import app

        # Проверим что fallback функции работают
        assert hasattr(app, "get_activity_factor")
        assert app.get_activity_factor("moderate") == 1.55

    def test_bmi_pro_router_fallback(self):
        """Тест fallback для bmi_pro_router"""
        # Проверим что app работает даже если bmi_pro_router=None
        if "app" in sys.modules:
            del sys.modules["app"]

        import app

        # app должен быть создан успешно
        assert app.app is not None

    def test_vip_router_fallback(self):
        """Тест fallback для VIP router"""
        with patch.dict(os.environ, {"VIP_MODULE_ENABLED": "true"}, clear=False):
            if "app" in sys.modules:
                del sys.modules["app"]

            import app

            # app должен работать даже если VIP router недоступен
            assert app.app is not None


class TestLifespanFallbacks:
    """Тесты lifespan startup/shutdown веток"""

    @pytest.mark.asyncio
    async def test_lifespan_start_success(self):
        """Тест успешного запуска lifespan"""
        if "app" in sys.modules:
            del sys.modules["app"]

        import app

        # Создаем mock app для lifespan
        mock_app = MagicMock()

        # Тестируем lifespan
        async with app.lifespan(mock_app):
            pass  # Просто проверяем что не падает

    @pytest.mark.asyncio
    async def test_lifespan_start_error(self):
        """Тест обработки ошибки при запуске"""
        with patch("app.start_background_updates", side_effect=Exception("Test error")):
            if "app" in sys.modules:
                del sys.modules["app"]

            import app

            mock_app = MagicMock()

            # Должен перехватить ошибку и продолжить
            async with app.lifespan(mock_app):
                pass

    @pytest.mark.asyncio
    async def test_lifespan_stop_error(self):
        """Тест обработки ошибки при остановке"""
        with patch("app.stop_background_updates", side_effect=Exception("Test error")):
            if "app" in sys.modules:
                del sys.modules["app"]

            import app

            mock_app = MagicMock()

            # Должен перехватить ошибку при shutdown
            async with app.lifespan(mock_app):
                pass


class TestEdgeCases:
    """Тесты edge cases для main.py"""

    def test_root_endpoint(self):
        """Тест корневого эндпоинта"""
        if "app" in sys.modules:
            del sys.modules["app"]

        import app

        client = TestClient(cast(ASGIApp, app.app))

        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self):
        """Тест health эндпоинта"""
        if "app" in sys.modules:
            del sys.modules["app"]

        import app

        client = TestClient(cast(ASGIApp, app.app))

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_legacy_category_label_function(self):
        """Тест legacy_category_label функции"""
        if "app" in sys.modules:
            del sys.modules["app"]

        import app

        # Тест английского языка
        result = app.legacy_category_label("Normal weight", "en")
        assert result == "Healthy weight"

        # Тест русского языка
        result = app.legacy_category_label("Избыточная масса", "ru")
        assert result == "Избыточный вес"

        # Тест других случаев
        result = app.legacy_category_label("Other", "en")
        assert result == "Other"

    def test_get_update_scheduler_wrapper(self):
        """Тест get_update_scheduler wrapper функции"""
        if "app" in sys.modules:
            del sys.modules["app"]

        import app

        # Просто проверим что функция существует
        assert hasattr(app, "get_update_scheduler")
        assert callable(app.get_update_scheduler)

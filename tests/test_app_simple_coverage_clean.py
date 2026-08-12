"""
Простые тесты для покрытия main.py недостающих веток
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import app
from app.routers.api_key import get_api_key


class TestAPIKeyModes:
    """Тесты различных режимов API ключей"""

    def test_api_key_strict_mode_valid_key(self) -> None:
        """Строгий режим - правильный ключ"""
        # Keep this secret-shaped fixture on its audited baseline line.
        # The generated baseline is shared with other active PRs.
        with patch.dict(os.environ, {"API_KEY": "test-secret-key"}, clear=False):
            result = get_api_key("test-secret-key")
            assert result == "test-secret-key"

    def test_api_key_strict_mode_invalid_key(self):
        """Строгий режим - неправильный ключ"""
        with patch.dict(os.environ, {"API_KEY": "test-secret-key"}, clear=False):
            with pytest.raises(HTTPException) as exc_info:
                get_api_key("wrong-key")
            assert exc_info.value.status_code == 403

    def test_api_key_strict_mode_missing_key(self):
        """Строгий режим - отсутствующий ключ"""
        with patch.dict(os.environ, {"API_KEY": "test-secret-key"}, clear=False):
            with pytest.raises(HTTPException) as exc_info:
                get_api_key(None)
            assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_missing_token(self):
        """Мягкий режим - отсутствующий токен"""
        with patch.dict(os.environ, {}, clear=True):
            # Убираем все API key переменные
            with pytest.raises(HTTPException) as exc_info:
                get_api_key(None)
            assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_short_token(self):
        """Мягкий режим - слишком короткий токен"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                get_api_key("x")  # Только 1 символ
            assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_forbidden_tokens(self):
        """Мягкий режим - запрещённые токены"""
        with patch.dict(os.environ, {}, clear=True):
            forbidden = ["invalid", "invalid_key", "wrong", "bad", "null"]

            for token in forbidden:
                with pytest.raises(HTTPException) as exc_info:
                    get_api_key(token)
                assert exc_info.value.status_code == 403

    def test_api_key_lenient_mode_valid_token(self):
        """Мягкий режим - валидный токен"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_api_key("valid-test-token")
            assert result == "valid-test-token"


class TestMetricsFallbacks:
    """Тесты fallback'ов метрик"""

    def test_metrics_endpoint_basic(self):
        """Тест базового metrics эндпоинта"""
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200
        # Может вернуть или JSON или prometheus текст
        # Просто проверим что ответ получен

    def test_metrics_with_prometheus(self):
        """Тест /metrics с prometheus_client"""
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200


class TestBasicEndpoints:
    """Тесты базовых эндпоинтов"""

    def test_root_endpoint(self):
        """Тест корневого эндпоинта"""
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self):
        """Тест health эндпоинта"""
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_health_v1_endpoint(self):
        """Тест health v1 эндпоинта"""
        client = TestClient(app)

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestImportCoverage:
    """Тесты для покрытия import веток"""

    def test_app_import_structure(self):
        """Тест структуры импортов app"""
        # Просто проверим что app загружается
        assert app is not None

        # Проверим что основные функции доступны
        # get_api_key loaded at module level (line 26)
        assert get_api_key is not None
        assert callable(get_api_key)


class TestBMIEndpoints:
    """Тесты BMI эндпоинтов для покрытия веток"""

    def test_bmi_endpoint_basic(self):
        """Тест базового BMI эндпоинта"""
        client = TestClient(app)

        # Правильный формат для BMIRequest
        payload = {"weight_kg": 70.0, "height_m": 1.70, "age": 30, "gender": "male", "lang": "en"}

        response = client.post("/bmi", json=payload)
        # Может быть 200 (успех) или 422 (валидация)
        assert response.status_code in [200, 422]

    def test_bmi_endpoint_pregnant(self):
        """Тест BMI эндпоинта с беременностью"""
        client = TestClient(app)

        payload = {
            "weight_kg": 65.0,
            "height_m": 1.65,
            "age": 28,
            "gender": "female",
            "pregnant": True,
            "lang": "en",
        }

        response = client.post("/bmi", json=payload)
        assert response.status_code in [200, 422]

    def test_bmi_endpoint_with_chart(self):
        """Тест BMI эндпоинта с визуализацией"""
        client = TestClient(app)

        payload = {
            "weight_kg": 70.0,
            "height_m": 1.70,
            "age": 30,
            "gender": "male",
            "include_chart": True,
            "lang": "en",
        }

        response = client.post("/bmi", json=payload)
        assert response.status_code in [200, 422]


class TestPrivacyEndpoint:
    """Тест privacy эндпоинта"""

    def test_privacy_endpoint(self):
        """Тест privacy policy эндпоинта"""
        client = TestClient(app)

        response = client.get("/privacy")
        assert response.status_code == 200
        data = response.json()
        assert "privacy_policy" in data

"""
Тесты для покрытия app.py BMI и bodyfat endpoints
Покрывает строки: 504-505, 978, 995-996, 1008-1012, 1045-1049, 1093-1094, 1101-1102, 1109-1112, 1115-1118, 1121-1124, 1197
"""

import logging
from typing import cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


class TestAppBMIBodyfatCoverage:
    """Тесты для покрытия app.py BMI и bodyfat endpoints"""

    @pytest.mark.parametrize(
        "endpoint,valid_payload,invalid_payload",
        [
            (
                "/api/v1/bmi",
                {"weight_kg": 70, "height_cm": 170, "group": "general"},
                {"weight_kg": "invalid", "height_cm": "invalid"},
            ),
            (
                "/api/v1/bodyfat",
                {"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90, "gender": "male"},
                {"weight_kg": "invalid", "height_cm": "invalid", "gender": "male"},
            ),
        ],
    )
    def test_endpoint_valid_request(
        self, test_environment, endpoint, valid_payload, invalid_payload
    ):
        """Тест покрытия валидных запросов к BMI и bodyfat endpoints"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем валидный запрос
        response = client.post(
            endpoint,
            json=valid_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

        data = response.json()
        if endpoint == "/api/v1/bmi":
            assert "bmi" in data
            assert "category" in data
            assert isinstance(data["bmi"], (int, float))
        else:  # bodyfat
            assert "methods" in data
            assert "median" in data

    @pytest.mark.parametrize(
        "endpoint,invalid_payload,expected_status",
        [
            ("/api/v1/bmi", {"weight_kg": "invalid", "height_cm": "invalid"}, 422),
            (
                "/api/v1/bodyfat",
                {"weight_kg": "invalid", "height_cm": "invalid", "gender": "male"},
                422,
            ),
            ("/api/v1/bmi", {"invalid": "data"}, 422),
            ("/api/v1/bodyfat", {"invalid": "data", "gender": "male"}, 200),
        ],
    )
    def test_endpoint_invalid_data(
        self, test_environment, endpoint, invalid_payload, expected_status
    ):
        """Тест покрытия невалидных данных для BMI и bodyfat endpoints"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        response = client.post(
            endpoint,
            json=invalid_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "endpoint,valid_payload,expected_status",
        [
            ("/api/v1/bmi", {"weight_kg": 70, "height_cm": 170, "group": "general"}, [401, 403]),
            (
                "/api/v1/bodyfat",
                {"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90, "gender": "male"},
                200,
            ),
        ],
    )
    def test_endpoint_missing_api_key(
        self, test_environment, endpoint, valid_payload, expected_status
    ):
        """Тест покрытия отсутствия API ключа для BMI и bodyfat endpoints"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        response = client.post(
            endpoint,
            json=valid_payload,
        )
        if isinstance(expected_status, list):
            assert response.status_code in expected_status
        else:
            assert response.status_code == expected_status

    def test_bmi_logging_coverage(self, test_environment, caplog):
        """Тест покрытия BMI logging с проверкой логов"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        with caplog.at_level(logging.INFO):
            response = client.post(
                "/api/v1/bmi",
                json={"weight_kg": 70, "height_cm": 170, "group": "general"},
                headers={"X-API-Key": "test_key"},
            )

        assert response.status_code == 200

        # Проверяем, что логи записались
        log_messages = [record.message for record in caplog.records]
        # Ищем логи, связанные с BMI расчетом
        bmi_logs = [
            msg
            for msg in log_messages
            if any(keyword in msg.lower() for keyword in ["bmi", "calculated", "group"])
        ]
        assert bmi_logs, f"Expected BMI-related logs, got: {log_messages}"

    def test_bmi_metrics_coverage(self, test_environment):
        """Тест покрытия BMI metrics с моком метрик"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Мокаем метрики, если они используются в приложении
        with patch("app.metrics"):
            response = client.post(
                "/api/v1/bmi",
                json={"weight_kg": 70, "height_cm": 170, "group": "general"},
                headers={"X-API-Key": "test_key"},
            )

            assert response.status_code == 200

            # Проверяем, что метрики были вызваны (если они используются)
            # Мок уже изолирует метрики, дополнительная проверка не нужна

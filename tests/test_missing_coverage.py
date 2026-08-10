# -*- coding: utf-8 -*-
"""
Тесты для покрытия недостающих строк
"""

import os

from fastapi.testclient import TestClient

from app.main import app


class TestMissingCoverage:
    """Тесты для покрытия недостающих строк"""

    def setup_method(self) -> None:
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_middleware_paths(self) -> None:
        """Тест путей middleware"""
        client = TestClient(app)

        # Тест различных эндпоинтов
        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/favicon.ico")
        assert response.status_code in (200, 204)

    def test_error_handling(self) -> None:
        """Тест обработки ошибок"""
        client = TestClient(app)

        # Тест с некорректными данными
        response = client.post("/api/v1/bmi", json={})
        assert response.status_code in (422, 403)

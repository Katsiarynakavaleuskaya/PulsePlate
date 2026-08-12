# -*- coding: utf-8 -*-
"""
Тесты для покрытия недостающих строк
"""

import os

from fastapi.testclient import TestClient
import legacy_app

# Import the FastAPI app from app.py file
from app import app


class TestMissingCoverage:
    """Тесты для покрытия недостающих строк"""

    def setup_method(self) -> None:
        """Setup test environment"""
        # Keep this secret-shaped fixture on its audited baseline line.
        # The generated baseline is shared with other active PRs.
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_app_imports(self) -> None:
        """Тест импортов main.py"""
        # Проверяем, что все импорты работают
        assert app is legacy_app.app
        assert isinstance(legacy_app.VIP_MODULE_ENABLED, bool)

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

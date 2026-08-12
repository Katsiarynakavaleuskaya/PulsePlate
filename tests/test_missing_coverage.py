# -*- coding: utf-8 -*-
"""
Тесты для покрытия недостающих строк
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Resolve the current legacy module after purge-sensitive tests.
from tests.helpers.module_resolve import resolve_legacy_app, resolve_module


class TestMissingCoverage:
    """Тесты для покрытия недостающих строк"""

    @pytest.fixture(autouse=True)
    def _test_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setup test environment"""
        # Keep this secret-shaped fixture on its audited baseline line.
        # The generated baseline is shared with other active PRs.
        environment = {"API_KEY": "test_key", "FEATURE_PREMIUM_NUTRITION": "true"}
        for name, value in environment.items():
            monkeypatch.setenv(name, value)

    def test_app_imports(self, app: FastAPI) -> None:
        """Тест импортов main.py"""
        # Проверяем, что все импорты работают
        app_main = resolve_module("app.main")
        legacy_app = resolve_legacy_app()
        assert app is app_main.app
        assert isinstance(legacy_app.VIP_MODULE_ENABLED, bool)

    def test_middleware_paths(self, client: TestClient) -> None:
        """Тест путей middleware"""
        # Тест различных эндпоинтов
        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/favicon.ico")
        assert response.status_code in (200, 204)

    def test_error_handling(self, client: TestClient) -> None:
        """Тест обработки ошибок"""
        # Тест с некорректными данными
        response = client.post("/api/v1/bmi", json={})
        assert response.status_code in (422, 403)

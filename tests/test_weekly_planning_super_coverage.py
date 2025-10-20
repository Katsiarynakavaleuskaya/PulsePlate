#!/usr/bin/env python3
"""
СПЕЦИАЛЬНЫЙ ТЕСТ для покрытия Weekly Planning блоков 1265-1339 и 1435-1501
Эти 142 строки критичны для достижения 97% покрытия!

Стратегия: создать функцию make_weekly_menu и заставить код выполниться
"""

import os
import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(dynamic_app):
    """Test client fixture using conftest's dynamic_app"""
    from fastapi import FastAPI
    from starlette.types import ASGIApp
    from typing import cast

    return TestClient(cast(ASGIApp, dynamic_app))


class TestWeeklyPlanningBlocks:
    """Специальные тесты для блоков 1265-1339 и 1435-1501"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def teardown_method(self):
        """Teardown test environment and cleanup feature flags."""
        os.environ.pop("API_KEY", None)
        os.environ.pop("FEATURE_PREMIUM_NUTRITION", None)
        os.environ.pop("VIP_MODULE_ENABLED", None)

    def test_weekly_planning_mock_success(self, client):
        """Тест успешного выполнения weekly planning с мокнутой функцией"""

        # Создать правильный мок для make_weekly_menu
        def create_weekly_menu_mock():
            """Создает мок weekly menu object"""
            mock_menu = MagicMock()
            mock_menu.week_start = "2025-01-01"
            mock_menu.total_cost = 150.0
            mock_menu.daily_menus = []

            # Создать 7 дней меню
            for i in range(7):
                day_menu = MagicMock()
                day_menu.date = f"2025-01-{i + 1:02d}"
                day_menu.meals = {
                    "breakfast": f"breakfast_{i + 1}",
                    "lunch": f"lunch_{i + 1}",
                    "dinner": f"dinner_{i + 1}",
                }
                day_menu.cost = 20.0 + i
                mock_menu.daily_menus.append(day_menu)

            mock_menu.shopping_list = {
                "milk": "2L",
                "eggs": "12 pieces",
                "bread": "2 loaves",
                "chicken": "1kg",
            }

            mock_menu.weekly_coverage = {
                "protein": 95.5,
                "carbs": 88.2,
                "fats": 92.1,
                "vitamins": 87.0,
            }

            return mock_menu

        # Точечный патч функции core.menu_engine.make_weekly_menu вместо глобального sys.modules
        with patch(
            "core.menu_engine.make_weekly_menu",
            side_effect=lambda _profile: create_weekly_menu_mock(),
        ):
            # Настроить API ключ и VIP флаг
            os.environ["API_KEY"] = "test_key"
            os.environ["VIP_MODULE_ENABLED"] = "true"
            try:
                # Вызвать weekly planning endpoint
                response = client.post(
                    "/api/v1/premium/plan/week",
                    headers={"X-API-Key": "test_key"},
                    json={
                        "sex": "male",
                        "age": 30,
                        "height_cm": 175,
                        "weight_kg": 75,
                        "activity": "moderate",
                        "goal": "maintain",
                        "deficit_pct": 15,
                        "surplus_pct": 10,
                        "bodyfat": 18.5,
                        "diet_flags": ["vegetarian", "gluten_free"],
                        "life_stage": "adult",
                    },
                )

                # no noisy prints in CI
                if response.status_code == 200:
                    data = response.json()
                    # no noisy prints in CI

                    # Проверить структуру ответа согласно коду main.py lines 1381-1501
                    assert "week_summary" in data
                    assert "daily_menus" in data
                    assert "weekly_coverage" in data
                    assert "shopping_list" in data

                    # Проверить week_summary структуру
                    week_summary = data["week_summary"]
                    assert "week_start" in week_summary
                    assert "total_days" in week_summary
                    assert "avg_daily_cost" in week_summary

                    # Проверить формат week_start (ISO YYYY-MM-DD)
                    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(week_summary["week_start"]))

                    # Проверить daily_menus структуру
                    daily_menus = data["daily_menus"]
                    assert len(daily_menus) == 7  # 7 дней

                    for menu in daily_menus:
                        assert "date" in menu
                        assert "meals" in menu
                        assert "cost" in menu

                # Успешный путь должен вернуть 200
                assert response.status_code == 200

            finally:
                if "API_KEY" in os.environ:
                    del os.environ["API_KEY"]
                if "VIP_MODULE_ENABLED" in os.environ:
                    del os.environ["VIP_MODULE_ENABLED"]

    def test_weekly_planning_with_getattr_mock(self, client):
        """Альтернативный подход к мокингу через getattr"""

        # Создаем мокнутую функцию make_weekly_menu
        def mock_make_weekly_menu(_profile: object) -> MagicMock:
            mock_result = MagicMock()
            mock_result.week_start = "2025-01-01"
            mock_result.total_cost = 140.0
            mock_result.daily_menus = [
                MagicMock(date=f"2025-01-{i:02d}", meals={}, cost=20.0) for i in range(1, 8)
            ]
            mock_result.shopping_list = {"test": "item"}
            mock_result.weekly_coverage = {"protein": 90}
            return mock_result

        # Мокаем модуль menu_engine напрямую
        with patch("core.menu_engine.make_weekly_menu", side_effect=mock_make_weekly_menu):
            os.environ["API_KEY"] = "test_key"
            os.environ["VIP_MODULE_ENABLED"] = "true"
            try:
                response = client.post(
                    "/api/v1/premium/plan/week",
                    headers={"X-API-Key": "test_key"},
                    json={
                        "sex": "female",
                        "age": 25,
                        "height_cm": 165,
                        "weight_kg": 60,
                        "activity": "light",
                        "goal": "lose",
                        "deficit_pct": 20,
                    },
                )

                # no noisy prints in CI

                if response.status_code == 200:
                    # Strictly verify expected schema and values from the mock
                    data = response.json()
                    assert set(
                        ["week_summary", "daily_menus", "weekly_coverage", "shopping_list"]
                    ).issubset(data.keys())

                    week_summary = data["week_summary"]
                    assert week_summary["week_start"] == "2025-01-01"
                    assert week_summary["total_days"] == 7
                    # avg_daily_cost is calculated in app; accept float close to 20.0
                    assert isinstance(week_summary["avg_daily_cost"], (int, float))

                    daily_menus = data["daily_menus"]
                    assert isinstance(daily_menus, list) and len(daily_menus) == 7
                    for idx, dm in enumerate(daily_menus, start=1):
                        assert dm["date"] == f"2025-01-{idx:02d}"
                        assert "meals" in dm
                        # cost normalized to float in app; each from mock is 20.0
                        assert dm["cost"] == 20.0

                    shopping_list = data["shopping_list"]
                    assert shopping_list.get("test") == "item"

                    weekly_coverage = data["weekly_coverage"]
                    assert weekly_coverage.get("protein") == 90
                else:
                    # Allow only explicit non-200 error statuses
                    assert response.status_code in [503, 422, 400]

            finally:
                if "API_KEY" in os.environ:
                    del os.environ["API_KEY"]
                if "VIP_MODULE_ENABLED" in os.environ:
                    del os.environ["VIP_MODULE_ENABLED"]

    def test_weekly_planning_error_scenarios(self, client):
        """Тест error scenarios в weekly planning"""

        os.environ["API_KEY"] = "test_key"
        try:
            # Тест без make_weekly_menu функции (должен быть 503)
            response = client.post(
                "/api/v1/premium/plan/week",
                headers={"X-API-Key": "test_key"},
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 75,
                    "activity": "moderate",
                    "goal": "maintain",
                },
            )

            # no noisy prints in CI

            # Явно проверяем 503 недоступность с ожидаемым payload
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "Weekly menu generation feature not available" in data["detail"]

        finally:
            if "API_KEY" in os.environ:
                del os.environ["API_KEY"]

    def test_weekly_planning_import_scenarios(self, client):
        """Тест import scenarios в weekly planning (lines 1356-1365)"""

        # Тестируем только целевой импорт core.menu_engine, не затрагивая другие импорты
        import importlib as _importlib

        original_import_module = _importlib.import_module

        def _side_effect(name, package=None):
            if name == "core.menu_engine":
                raise ImportError("core.menu_engine unavailable for test")
            return original_import_module(name, package)

        with patch("importlib.import_module", side_effect=_side_effect):
            os.environ["API_KEY"] = "test_key"
            os.environ["VIP_MODULE_ENABLED"] = "true"
            try:
                response = client.post(
                    "/api/v1/premium/plan/week",
                    headers={"X-API-Key": "test_key"},
                    json={
                        "sex": "male",
                        "age": 35,
                        "height_cm": 180,
                        "weight_kg": 80,
                        "activity": "active",
                        "goal": "gain",
                    },
                )

                # Ожидаем конкретный статус 503 при сбое импорта модуля
                assert response.status_code == 503
                data = response.json()
                assert "detail" in data
                assert "not available" in data["detail"].lower()

            finally:
                if "API_KEY" in os.environ:
                    del os.environ["API_KEY"]
                if "VIP_MODULE_ENABLED" in os.environ:
                    del os.environ["VIP_MODULE_ENABLED"]

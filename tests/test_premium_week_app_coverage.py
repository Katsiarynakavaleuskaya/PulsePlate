# -*- coding: utf-8 -*-
"""
Simple tests for premium week endpoint coverage in main.py

RU: Простые тесты для покрытия эндпоинта premium week в main.py
EN: Simple tests for premium week endpoint coverage in main.py
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import legacy_app
from app import app

# Common test payload for weekly menu tests (DRY)
_BASE_WEEKLY_PAYLOAD: dict = {
    "sex": "female",
    "age": 30,
    "height_cm": 165.0,
    "weight_kg": 60.0,
    "activity": "moderate",
    "goal": "maintain",
    "diet_flags": [],
    "lang": "en",
}


class TestPremiumWeekAppCoverage:
    """Test suite for premium week endpoint coverage in main.py."""

    @pytest.fixture(autouse=True)
    def _env_and_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set up test client and env with automatic cleanup."""
        monkeypatch.setenv("API_KEY", "test_key")
        monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
        self.client = TestClient(app)

    def test_api_weekly_menu_make_weekly_menu_not_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test when make_weekly_menu is not available (503 error).

        The endpoint resolves make_weekly_menu via two paths (legacy_app.py L4277-4282):
          1. getattr(sys.modules["app"], "make_weekly_menu", None)  — app module dict
          2. globals().get("make_weekly_menu")                       — legacy_app namespace

        Previous tests using ``patch("app.make_weekly_menu", ...)`` leave the real
        function in ``app.__dict__`` after cleanup (patch restores via setattr).
        We must set BOTH to None so neither path resolves a callable.
        """
        import app as app_module

        # Null out the app-level attribute (covers path 1: app.__dict__ lookup)
        monkeypatch.setattr(app_module, "make_weekly_menu", None)
        # Null out the legacy_app-level attribute (covers path 2: globals() fallback)
        monkeypatch.setattr(legacy_app, "make_weekly_menu", None)

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=_BASE_WEEKLY_PAYLOAD,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 503
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "detail" in data
        assert "not available" in data["detail"].lower()

    def test_resolver_falls_back_to_package_export_when_legacy_builder_is_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolver uses app package export when legacy builder is patched to None.

        RU: Если legacy_app.make_weekly_menu временно None, резолвер должен
        использовать canonical export из пакета `app`, если package override не задан.
        EN: If legacy_app.make_weekly_menu is temporarily None, the resolver must
        use the canonical `app` package export when no explicit package override exists.
        """
        import app as app_package

        monkeypatch.delitem(app_package.__dict__, "make_weekly_menu", raising=False)
        monkeypatch.setattr(legacy_app, "make_weekly_menu", None)

        builder = legacy_app._resolve_legacy_weekly_menu_builder()

        assert callable(builder)

    def test_resolver_returns_none_when_package_export_is_not_callable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolver returns None when neither legacy nor package export is callable.

        RU: Явно покрываем отрицательный fallback путь без business-logic изменений.
        EN: Explicitly cover the negative fallback path without changing business logic.
        """
        import app as app_package

        original_getattr = getattr(app_package, "__getattr__")

        monkeypatch.delitem(app_package.__dict__, "make_weekly_menu", raising=False)
        monkeypatch.setattr(legacy_app, "make_weekly_menu", None)

        def _package_getattr(name: str):
            if name == "make_weekly_menu":
                return None
            return original_getattr(name)

        monkeypatch.setattr(app_package, "__getattr__", _package_getattr)

        builder = legacy_app._resolve_legacy_weekly_menu_builder()

        assert builder is None

    def test_resolver_returns_none_when_package_module_is_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolver returns None when the `app` package is absent from sys.modules."""
        monkeypatch.delitem(sys.modules, "app", raising=False)
        monkeypatch.setattr(legacy_app, "make_weekly_menu", None)

        builder = legacy_app._resolve_legacy_weekly_menu_builder()

        assert builder is None

    def test_api_weekly_menu_success(self) -> None:
        """Test successful weekly menu generation."""
        # Mock make_weekly_menu to return a valid WeekMenu
        mock_week_menu = MagicMock()
        mock_week_menu.week_start = "2024-01-01"
        mock_week_menu.daily_menus = [MagicMock() for _ in range(7)]
        mock_week_menu.total_cost = 105.0

        with patch("app.make_weekly_menu", return_value=mock_week_menu):
            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=_BASE_WEEKLY_PAYLOAD,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            data = response.json()
            assert "week_summary" in data
            assert "daily_menus" in data
            assert "weekly_coverage" in data
            assert "shopping_list" in data

    def test_api_weekly_menu_exception_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test exception handling in weekly menu generation."""

        # Mock make_weekly_menu to raise an exception
        def raise_exception(*args, **kwargs):
            raise RuntimeError("Test exception: menu engine failure")

        # Use monkeypatch.setattr for both modules to ensure globals() sees the mock
        monkeypatch.setattr("app.make_weekly_menu", raise_exception)
        monkeypatch.setattr(legacy_app, "make_weekly_menu", raise_exception)

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=_BASE_WEEKLY_PAYLOAD,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 500
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "detail" in data
        assert "Weekly menu generation failed" in data["detail"]

    def test_api_weekly_menu_with_optional_fields(self) -> None:
        """Test with optional fields like deficit_pct, surplus_pct, bodyfat, life_stage."""
        payload = {
            **_BASE_WEEKLY_PAYLOAD,
            "deficit_pct": 10.0,
            "surplus_pct": 5.0,
            "bodyfat": 20.0,
            "life_stage": "adult",
            "diet_flags": ["VEG"],
        }

        # Mock make_weekly_menu to return a valid WeekMenu
        mock_week_menu = MagicMock()
        mock_week_menu.week_start = "2024-01-01"
        mock_week_menu.daily_menus = [MagicMock() for _ in range(7)]
        mock_week_menu.total_cost = 120.0

        with patch("app.make_weekly_menu", return_value=mock_week_menu):
            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            data = response.json()
            assert "week_summary" in data
            assert "daily_menus" in data

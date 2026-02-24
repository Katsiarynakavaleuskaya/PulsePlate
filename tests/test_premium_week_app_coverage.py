# -*- coding: utf-8 -*-
"""
Simple tests for premium week endpoint coverage in main.py

RU: Простые тесты для покрытия эндпоинта premium week в main.py
EN: Simple tests for premium week endpoint coverage in main.py
"""

import os
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

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        os.environ.pop("API_KEY", None)
        os.environ.pop("FEATURE_PREMIUM_NUTRITION", None)

    def test_api_weekly_menu_make_weekly_menu_not_available(self, monkeypatch: pytest.MonkeyPatch):
        """Test when make_weekly_menu is not available (503 error).

        The endpoint checks both app.make_weekly_menu (via PEP 562 __getattr__) and
        legacy_app globals(), so we need to ensure both return None.

        We mock app._LOCAL_EXPORTS to remove 'make_weekly_menu' and delete from legacy_app.
        """
        import app as app_module

        # Remove 'make_weekly_menu' from app's lazy exports so __getattr__ won't find it
        original_exports = app_module._LOCAL_EXPORTS.copy()
        monkeypatch.setattr(
            app_module,
            "_LOCAL_EXPORTS",
            {k: v for k, v in original_exports.items() if k != "make_weekly_menu"},
        )

        # Also need to handle the fallback to legacy_app in __getattr__
        # And delete from legacy_app globals
        try:
            monkeypatch.delattr(legacy_app, "make_weekly_menu")
        except AttributeError:
            pass

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=_BASE_WEEKLY_PAYLOAD,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "not available" in data["detail"].lower()

    def test_api_weekly_menu_success(self):
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
            data = response.json()
            assert "week_summary" in data
            assert "daily_menus" in data
            assert "weekly_coverage" in data
            assert "shopping_list" in data

    def test_api_weekly_menu_exception_handling(self, monkeypatch: pytest.MonkeyPatch):
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
        data = response.json()
        assert "detail" in data
        assert "Weekly menu generation failed" in data["detail"]

    def test_api_weekly_menu_with_optional_fields(self):
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
            data = response.json()
            assert "week_summary" in data
            assert "daily_menus" in data

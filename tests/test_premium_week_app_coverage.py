# -*- coding: utf-8 -*-
"""
Simple tests for premium week endpoint coverage in main.py

RU: Простые тесты для покрытия эндпоинта premium week в main.py
EN: Simple tests for premium week endpoint coverage in main.py
"""

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app import app


class TestPremiumWeekAppCoverage:
    """Test suite for premium week endpoint coverage in main.py."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_api_weekly_menu_make_weekly_menu_not_available(self):
        """Test when make_weekly_menu is not available (503 error).

        The endpoint checks both app.make_weekly_menu and legacy_app globals,
        so we need to ensure both return None to trigger the 503 response.
        """
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }

        # Mock make_weekly_menu to be None (not available) in both locations
        # The endpoint checks app.make_weekly_menu first, then falls back to globals
        with patch("app.make_weekly_menu", None), patch("legacy_app.make_weekly_menu", None):
            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "not available" in data["detail"].lower()

    def test_api_weekly_menu_success(self):
        """Test successful weekly menu generation."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }

        # Mock make_weekly_menu to return a valid WeekMenu
        mock_week_menu = MagicMock()
        mock_week_menu.week_start = "2024-01-01"
        mock_week_menu.daily_menus = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_week_menu.total_cost = 105.0

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
            assert "weekly_coverage" in data
            assert "shopping_list" in data

    def test_api_weekly_menu_exception_handling(self):
        """Test exception handling in weekly menu generation."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }

        # Mock make_weekly_menu to raise an exception
        def raise_exception(*args, **kwargs):
            raise RuntimeError("Test exception: menu engine failure")

        with patch("app.make_weekly_menu", side_effect=raise_exception):
            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Weekly menu generation failed" in data["detail"]

    def test_api_weekly_menu_with_optional_fields(self):
        """Test with optional fields like deficit_pct, surplus_pct, bodyfat, life_stage."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "deficit_pct": 10.0,
            "surplus_pct": 5.0,
            "bodyfat": 20.0,
            "life_stage": "adult",
            "diet_flags": ["VEG"],
            "lang": "en",
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

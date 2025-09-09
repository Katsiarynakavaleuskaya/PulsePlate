# -*- coding: utf-8 -*-
"""
Simple tests for premium week endpoint coverage in app.py

RU: Простые тесты для покрытия эндпоинта premium week в app.py
EN: Simple tests for premium week endpoint coverage in app.py
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app import app


class TestPremiumWeekAppCoverage:
    """Test suite for premium week endpoint coverage in app.py."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_api_weekly_menu_make_weekly_menu_not_available(self):
        """Test when make_weekly_menu is not available (503 error)."""
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

        # Mock make_weekly_menu to be None
        with patch("app.make_weekly_menu", None):
            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 503
            assert (
                "Weekly menu generation feature not available"
                in response.json()["detail"]
            )

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
        with patch("app.make_weekly_menu", side_effect=Exception("Test error")):
            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]

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

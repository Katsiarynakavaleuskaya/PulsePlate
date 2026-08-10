#!/usr/bin/env python3
"""
СПЕЦИАЛЬНЫЙ ТЕСТ для покрытия Weekly Planning блоков 1265-1339 и 1435-1501
Эти 142 строки критичны для достижения 97% покрытия!

Стратегия: создать функцию make_weekly_menu и заставить код выполниться
"""

from typing import Any, NoReturn
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

import app.routers.legacy_premium_weekly_plan as weekly_plan_router
import app.routers.vip as vip_router


def _valid_payload() -> dict[str, Any]:
    """Return one valid full-profile payload for the legacy weekly alias."""
    return {
        "sex": "female",
        "age": 30,
        "height_cm": 168.0,
        "weight_kg": 62.0,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "en",
    }


def _fake_weekly_menu_builder(
    _profile: object,
    _food_db: object = None,
    _recipe_db: object = None,
) -> dict[str, Any]:
    """Return a deterministic payload accepted by the canonical response adapter."""
    return {
        "week_start": "2026-03-09",
        "daily_menus": [
            {
                "date": "2026-03-09",
                "meals": [
                    {"title": "Breakfast", "kcal": 320},
                    {"title": "Lunch", "kcal": 610},
                ],
                "total_kcal": 930,
                "daily_cost": 11.5,
            },
            {
                "date": "2026-03-10",
                "meals": [{"title": "Dinner", "kcal": 540}],
                "total_kcal": 540,
                "daily_cost": 9.25,
            },
        ],
        "weekly_coverage": {"protein": 0.91, "fiber": 0.84},
        "shopping_list": {"oats": 400.0, "chicken": 900.0},
        "total_cost": 72.8,
        "adherence_score": 0.67,
    }


class TestWeeklyPlanningBlocks:
    """Специальные тесты для блоков 1265-1339 и 1435-1501"""

    def test_weekly_planning_mock_success(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The exact consumer binding drives the canonical success path."""
        builder = Mock(side_effect=_fake_weekly_menu_builder)
        monkeypatch.setattr(
            weekly_plan_router,
            "get_weekly_menu_builder",
            lambda: builder,
        )

        response = client.post(
            "/api/v1/premium/plan/week",
            headers={"X-API-Key": "test_key"},
            json=_valid_payload(),
        )

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["week_summary"] == {
            "week_start": "2026-03-09",
            "total_days": 2,
            "avg_daily_cost": 10.38,
        }
        assert data["daily_menus"][0]["date"] == "2026-03-09"
        assert data["daily_menus"][0]["meals"] == [
            {"title": "Breakfast", "kcal": 320},
            {"title": "Lunch", "kcal": 610},
        ]
        assert data["weekly_coverage"] == {"protein": 0.91, "fiber": 0.84}
        assert data["shopping_list"] == {"oats": 400.0, "chicken": 900.0}
        assert data["total_cost"] == 72.8
        assert data["adherence_score"] == 0.67
        builder.assert_called_once()

    def test_weekly_planning_executor_value_error_is_static_400(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The legacy alias sanitizes a canonical executor ValueError."""

        def _raise_value_error(*_args: object, **_kwargs: object) -> NoReturn:
            raise ValueError("private builder detail")

        monkeypatch.setattr(
            weekly_plan_router,
            "get_weekly_menu_builder",
            lambda: _raise_value_error,
        )

        response = client.post(
            "/api/v1/premium/plan/week",
            headers={"X-API-Key": "test_key"},
            json=_valid_payload(),
        )

        assert response.status_code == 400, response.text
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Invalid input"}
        assert "private builder detail" not in response.text

    def test_weekly_planning_builder_unavailable_is_exact_503(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unavailable canonical builder short-circuits with the exact 503."""
        executor = AsyncMock()
        monkeypatch.setattr(
            weekly_plan_router,
            "get_weekly_menu_builder",
            lambda: None,
        )
        monkeypatch.setattr(
            vip_router,
            "execute_legacy_premium_week_alias_payload",
            executor,
        )

        response = client.post(
            "/api/v1/premium/plan/week",
            headers={"X-API-Key": "test_key"},
            json=_valid_payload(),
        )

        assert response.status_code == 503, response.text
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Weekly menu generation feature not available"}
        executor.assert_not_awaited()

    def test_weekly_planning_getter_failure_is_sanitized_500(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A broken canonical getter fails closed without leaking its detail."""
        executor = AsyncMock()

        def _raise_getter_failure() -> NoReturn:
            raise RuntimeError("private getter detail")

        monkeypatch.setattr(
            weekly_plan_router,
            "get_weekly_menu_builder",
            _raise_getter_failure,
        )
        monkeypatch.setattr(
            vip_router,
            "execute_legacy_premium_week_alias_payload",
            executor,
        )

        response = client.post(
            "/api/v1/premium/plan/week",
            headers={"X-API-Key": "test_key"},
            json=_valid_payload(),
        )

        assert response.status_code == 500, response.text
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Weekly menu generation failed"}
        assert "private getter detail" not in response.text
        executor.assert_not_awaited()

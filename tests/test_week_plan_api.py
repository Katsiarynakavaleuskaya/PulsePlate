"""
Tests for Week Plan API

RU: Тесты для API недельного плана.
EN: Tests for the weekly plan API.
"""

from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app.routers.legacy_premium_weekly_plan as weekly_plan_router

_TARGETS_ONLY_DETAIL = (
    "Targets-based weekly plans are not supported on this endpoint. "
    "Provide full profile data or use /api/v1/premium/plan/week-flexible."
)


def _fake_weekly_menu_builder(_profile: object) -> dict[str, Any]:
    """Return one deterministic weekly payload through the canonical builder seam."""
    return {
        "week_start": "2026-03-09",
        "daily_menus": [
            {
                "date": "2026-03-09",
                "meals": [{"title": "Breakfast", "kcal": 320}],
                "total_kcal": 320,
                "daily_cost": 11.5,
            }
        ],
        "weekly_coverage": {"protein": 0.91},
        "shopping_list": {"oats": 400.0},
        "total_cost": 72.8,
        "adherence_score": 0.67,
    }


def test_week_plan_with_targets(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Targets-only callers receive exact migration guidance after authentication."""
    builder = Mock(side_effect=_fake_weekly_menu_builder)
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: builder,
    )

    # Test data with pre-calculated targets
    test_data = {
        "targets": {
            "kcal": 2000,
            "macros": {"protein_g": 100, "fat_g": 70, "carbs_g": 250, "fiber_g": 30},
            "micro": {
                "Fe_mg": 18.0,
                "Ca_mg": 1000.0,
                "VitD_IU": 600.0,
                "B12_ug": 2.4,
                "Folate_ug": 400.0,
                "Iodine_ug": 150.0,
                "K_mg": 3500.0,
                "Mg_mg": 400.0,
            },
        },
        "diet_flags": [],
        "lang": "en",
    }

    response = client.post(
        "/api/v1/premium/plan/week",
        json=test_data,
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 422, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": _TARGETS_ONLY_DETAIL}
    builder.assert_not_called()


def test_week_plan_with_profile(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test generating a week plan with user profile."""
    builder = Mock(side_effect=_fake_weekly_menu_builder)
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: builder,
    )

    # Test data with user profile
    test_data = {
        "sex": "female",
        "age": 30,
        "height_cm": 165,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "en",
    }

    response = client.post(
        "/api/v1/premium/plan/week",
        json=test_data,
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["week_summary"] == {
        "week_start": "2026-03-09",
        "total_days": 1,
        "avg_daily_cost": 11.5,
    }
    assert data["daily_menus"][0]["meals"] == [{"title": "Breakfast", "kcal": 320}]
    assert data["weekly_coverage"] == {"protein": 0.91}
    assert data["shopping_list"] == {"oats": 400.0}
    assert data["total_cost"] == 72.8
    assert data["adherence_score"] == 0.67
    builder.assert_called_once()


def test_week_plan_multilingual(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Targets-only migration guidance remains exact across languages."""
    builder = Mock(side_effect=_fake_weekly_menu_builder)
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: builder,
    )

    # Test data with pre-calculated targets
    targets_data = {
        "targets": {
            "kcal": 2000,
            "macros": {"protein_g": 100, "fat_g": 70, "carbs_g": 250, "fiber_g": 30},
            "micro": {
                "Fe_mg": 18.0,
                "Ca_mg": 1000.0,
                "VitD_IU": 600.0,
                "B12_ug": 2.4,
                "Folate_ug": 400.0,
                "Iodine_ug": 150.0,
                "K_mg": 3500.0,
                "Mg_mg": 400.0,
            },
        },
        "diet_flags": [],
    }

    # Test with different languages
    for lang in ["en", "ru", "es"]:
        test_data = targets_data.copy()
        test_data["lang"] = lang

        response = client.post(
            "/api/v1/premium/plan/week",
            json=test_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 422, response.text
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": _TARGETS_ONLY_DETAIL}

    builder.assert_not_called()


def test_week_plan_missing_data(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the API handles missing data correctly."""
    getter = Mock(return_value=_fake_weekly_menu_builder)
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        getter,
    )

    # Test data with missing required fields
    test_data = {"diet_flags": [], "lang": "en"}

    response = client.post(
        "/api/v1/premium/plan/week",
        json=test_data,
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 422, response.text
    assert response.headers["content-type"].startswith("application/json")
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert len(detail) == 1
    assert detail[0]["loc"] == ["body"]
    assert detail[0]["type"] == "value_error"
    assert "Either 'targets' must be provided" in detail[0]["msg"]
    getter.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])

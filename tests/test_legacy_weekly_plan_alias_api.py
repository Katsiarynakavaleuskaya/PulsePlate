"""Tests for the legacy premium weekly-plan alias shim."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import legacy_app


def _fake_weekly_menu_builder(profile: object) -> dict[str, Any]:
    """Return a deterministic weekly menu payload for alias/canonical parity tests.

    RU: Вернуть детерминированный weekly menu payload для parity тестов.
    EN: Return a deterministic weekly menu payload for alias/canonical parity tests.
    """
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


def _valid_payload() -> dict[str, Any]:
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


def test_legacy_weekly_alias_matches_canonical_vip_menu(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy premium alias must be a thin adapter over canonical VIP weekly menu logic."""

    import app as app_module
    import app.routers.vip as vip_router

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(app_module, "make_weekly_menu", _fake_weekly_menu_builder, raising=False)
    monkeypatch.setattr(legacy_app, "make_weekly_menu", _fake_weekly_menu_builder, raising=False)
    monkeypatch.setattr(vip_router, "make_weekly_menu", _fake_weekly_menu_builder, raising=False)

    vip_route = next(
        (
            route
            for route in client.app.routes
            if isinstance(route, APIRoute)
            and route.path == "/api/v1/vip/menu/weekly/plan"
            and "POST" in (route.methods or set())
        ),
        None,
    )
    assert vip_route is not None, "POST /api/v1/vip/menu/weekly/plan route not found"
    monkeypatch.setitem(
        vip_route.endpoint.__globals__,
        "make_weekly_menu",
        _fake_weekly_menu_builder,
    )

    payload = _valid_payload()
    legacy_response = client.post("/api/v1/premium/plan/week", json=payload, headers=vip_headers)
    canonical_response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=payload,
        headers=vip_headers,
    )

    assert legacy_response.status_code == 200, legacy_response.text
    assert canonical_response.status_code == 200, canonical_response.text
    assert legacy_response.headers.get("Content-Type", "").startswith("application/json")
    assert canonical_response.headers.get("Content-Type", "").startswith("application/json")

    legacy_data = legacy_response.json()
    canonical_menu = canonical_response.json()["menu"]

    assert legacy_data["daily_menus"] == canonical_menu["daily_menus"]
    assert legacy_data["weekly_coverage"] == canonical_menu["weekly_coverage"]
    assert legacy_data["shopping_list"] == canonical_menu["shopping_list"]
    assert legacy_data["total_cost"] == canonical_menu["total_cost"]
    assert legacy_data["adherence_score"] == canonical_menu["adherence_score"]
    assert legacy_data["week_summary"]["week_start"] == canonical_menu["week_start"]
    assert legacy_data["week_summary"]["total_days"] == len(canonical_menu["daily_menus"])
    assert legacy_data["week_summary"]["avg_daily_cost"] == round(
        canonical_menu["total_cost"] / len(canonical_menu["daily_menus"]), 2
    )


def test_legacy_weekly_alias_rejects_targets_only_payload_with_guidance(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Targets-only legacy payload must keep the legacy guidance contract."""

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])

    response = client.post(
        "/api/v1/premium/plan/week",
        json={
            "targets": {
                "kcal": 2000,
                "macros": {"protein_g": 120},
                "micro": {"iron_mg": 18},
                "water_ml": 2200,
            }
        },
        headers=vip_headers,
    )

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    detail = response.json()["detail"]
    assert "Targets-based weekly plans are not supported on this endpoint." in detail
    assert "/api/v1/premium/plan/week-flexible" in detail


def test_legacy_weekly_alias_returns_503_when_vip_module_disabled(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VIP feature flag must short-circuit before canonical weekly-plan delegation."""

    monkeypatch.setenv("VIP_MODULE_ENABLED", "false")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])

    response = client.post("/api/v1/premium/plan/week", json=_valid_payload(), headers=vip_headers)

    assert response.status_code == 503, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json()["detail"] == "VIP module is disabled"


def test_build_legacy_weekly_menu_response_ignores_non_dict_days() -> None:
    """Legacy adapter must skip malformed daily menu entries without crashing."""

    response = legacy_app._build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                "bad-day-entry",
                {
                    "date": "",
                    "meals": [],
                    "total_kcal": 0,
                    "daily_cost": 0,
                },
                {
                    "date": "2026-03-09",
                    "meals": "bad-meals",
                    "total_kcal": 0,
                    "daily_cost": 0,
                },
                {
                    "date": "2026-03-10",
                    "meals": [],
                    "total_kcal": 0,
                    "daily_cost": 0,
                },
            ],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 7.0,
            "adherence_score": 0.1,
        }
    )

    assert len(response.daily_menus) == 1
    assert response.daily_menus[0]["date"] == "2026-03-10"


def test_build_legacy_weekly_menu_response_rejects_bool_numeric_values() -> None:
    """Boolean-like numeric fields must fall back to defaults in the legacy adapter."""

    response = legacy_app._build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [],
            "weekly_coverage": {"protein": True, "fiber": 0.84},
            "shopping_list": {"oats": True, "rice": 250.0},
            "total_cost": True,
            "adherence_score": False,
        }
    )

    assert response.weekly_coverage == {"fiber": 0.84}
    assert response.shopping_list == {"rice": 250.0}
    assert response.total_cost == 0.0
    assert response.adherence_score == 0.0

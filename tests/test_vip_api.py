# -*- coding: utf-8 -*-
"""
VIP API Tests

RU: Тесты для VIP API эндпоинтов
EN: Tests for VIP API endpoints
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.services import fitchef_runtime
from tests._route_patch import find_route_endpoint, patch_endpoint_global

_CORE_WEEKLY_PROFILE_FIELDS = ("sex", "age", "height_cm", "weight_kg", "activity", "goal")
_INVALID_WEEKLY_PAYLOAD = {"detail": "Invalid weekly plan request payload"}


def _valid_weekly_profile_payload() -> dict[str, Any]:
    return {
        "sex": "female",
        "age": 29,
        "height_cm": 168.0,
        "weight_kg": 58.0,
        "activity": "active",
        "goal": "maintain",
    }


def test_vip_weekly_plan_openapi_publishes_required_profile_contract(
    client: TestClient,
) -> None:
    """OpenAPI mirrors the six-field schema without moving validation before auth."""

    schema = cast(FastAPI, client.app).openapi()
    request_schema = schema["paths"]["/api/v1/vip/menu/weekly/plan"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]

    assert request_schema["required"] == list(_CORE_WEEKLY_PROFILE_FIELDS)
    assert set(request_schema["properties"]) >= set(_CORE_WEEKLY_PROFILE_FIELDS)
    assert request_schema["additionalProperties"] is True


def test_vip_health(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP health endpoint returns 200"""
    r = client.get("/api/v1/vip/health", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["module"] == "vip"
    assert "features" in data


def test_deprecated_weekly_plan_handles_dict_plan(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, vip_headers: dict[str, str]
) -> None:
    captured: dict[str, object] = {"builder_calls": 0}

    def fake_make_weekly_menu(*, profile: object) -> dict[str, object]:
        captured["builder_calls"] = int(captured["builder_calls"]) + 1
        captured["profile"] = profile
        return {
            "week_start": "2026-01-01",
            "daily_menus": [],
            "weekly_coverage": {},
            "shopping_list": [],
            "total_cost": 0,
            "adherence_score": 0,
        }

    deprecated_endpoint = find_route_endpoint(
        app=client.app,
        path="/api/v1/vip/weekly-plan",
        method="POST",
    )
    # NOTE: String-based module patching (e.g. "app.routers.vip.make_weekly_menu") can be flaky
    # under dual-module / reload / shim-import behavior. Patch the registered route handler globals
    # for determinism (see docs/ENGINEERING_LESSONS.md).
    patch_endpoint_global(
        monkeypatch=monkeypatch,
        endpoint=deprecated_endpoint,
        name="make_weekly_menu",
        value=fake_make_weekly_menu,
    )

    payload = {
        "sex": "female",
        "age": 25,
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "activity": "light",
        "goal": "loss",
    }
    r = client.post("/api/v1/vip/weekly-plan", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["data"]["week_start"] == "2026-01-01"
    assert data["data"]["daily_menus"] == []
    profile = captured["profile"]
    assert captured["builder_calls"] == 1
    assert getattr(profile, "sex") == payload["sex"]
    assert getattr(profile, "age") == payload["age"]
    assert getattr(profile, "height_cm") == payload["height_cm"]
    assert getattr(profile, "weight_kg") == payload["weight_kg"]
    assert getattr(profile, "activity") == payload["activity"]
    assert getattr(profile, "goal") == payload["goal"]


@pytest.mark.parametrize("missing_field", _CORE_WEEKLY_PROFILE_FIELDS)
@pytest.mark.parametrize(
    "supplements",
    (
        {},
        {"calories": 2100},
        {"protein": 120.0},
        {"calories": 2100, "protein": 120.0},
        {"protein_g": 121.0},
        {"calories": 2100, "protein_g": 121.0},
    ),
    ids=(
        "none",
        "calories",
        "protein",
        "calories-and-protein",
        "protein-g",
        "calories-and-protein-g",
    ),
)
def test_vip_weekly_plan_rejects_each_missing_core_field_before_runtime(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
    missing_field: str,
    supplements: dict[str, Any],
) -> None:
    runtime_calls = 0

    async def unexpected_runtime_call(*args: object, **kwargs: object) -> object:
        nonlocal runtime_calls
        runtime_calls += 1
        raise AssertionError("runtime must not run for an incomplete schema payload")

    monkeypatch.setattr(
        fitchef_runtime,
        "run_weekly_plan_task",
        unexpected_runtime_call,
    )
    payload = {**_valid_weekly_profile_payload(), **supplements}
    del payload[missing_field]

    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=payload,
        headers=vip_headers,
    )

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json() == _INVALID_WEEKLY_PAYLOAD
    assert runtime_calls == 0


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sex", None),
        ("sex", ""),
        ("sex", "unknown"),
        ("age", None),
        *((field, value) for field in ("age", "height_cm", "weight_kg") for value in (True, False)),
        ("age", 0),
        ("age", 121),
        ("height_cm", None),
        ("height_cm", 0),
        ("height_cm", 301),
        ("weight_kg", None),
        ("weight_kg", 0),
        ("weight_kg", 501),
        ("activity", None),
        ("activity", ""),
        ("activity", "unknown"),
        ("goal", None),
        ("goal", ""),
        ("goal", "unknown"),
    ),
)
def test_vip_weekly_plan_rejects_invalid_http_profile_values_before_runtime(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
    field: str,
    value: object,
) -> None:
    runtime_calls = 0

    async def unexpected_runtime_call(*args: object, **kwargs: object) -> object:
        nonlocal runtime_calls
        runtime_calls += 1
        raise AssertionError("runtime must not run for an invalid schema payload")

    monkeypatch.setattr(
        fitchef_runtime,
        "run_weekly_plan_task",
        unexpected_runtime_call,
    )
    payload = _valid_weekly_profile_payload()
    payload[field] = value

    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=payload,
        headers=vip_headers,
    )

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json() == _INVALID_WEEKLY_PAYLOAD
    assert runtime_calls == 0


@pytest.mark.parametrize(
    ("age", "height_cm", "weight_kg", "expected_age", "expected_height", "expected_weight"),
    (
        ("31", "171.5", "64", 31, 171.5, 64.0),
        (31.0, 171, 64.0, 31, 171.0, 64.0),
    ),
    ids=("numeric-strings", "integer-valued-numbers"),
)
def test_vip_weekly_plan_normalizes_http_numbers_and_calls_builder_once(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
    age: object,
    height_cm: object,
    weight_kg: object,
    expected_age: int,
    expected_height: float,
    expected_weight: float,
) -> None:
    captured: dict[str, object] = {"builder_calls": 0}

    def fake_menu_builder(profile: object) -> dict[str, object]:
        captured["builder_calls"] = int(captured["builder_calls"]) + 1
        captured["profile"] = profile
        return {"days": []}

    canonical_endpoint = find_route_endpoint(
        app=client.app,
        path="/api/v1/vip/menu/weekly/plan",
        method="POST",
    )
    patch_endpoint_global(
        monkeypatch=monkeypatch,
        endpoint=canonical_endpoint,
        name="make_weekly_menu",
        value=fake_menu_builder,
    )
    payload = {
        **_valid_weekly_profile_payload(),
        "age": age,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
    }

    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=payload,
        headers=vip_headers,
    )

    assert response.status_code == 200, response.text
    profile = captured["profile"]
    assert captured["builder_calls"] == 1
    assert getattr(profile, "age") == expected_age
    assert getattr(profile, "height_cm") == expected_height
    assert getattr(profile, "weight_kg") == expected_weight


def test_vip_weekly_plan_keeps_protein_and_protein_g_supplemental(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    captured: dict[str, object] = {"builder_calls": 0}

    def fake_menu_builder(profile: object) -> dict[str, object]:
        captured["builder_calls"] = int(captured["builder_calls"]) + 1
        captured["profile"] = profile
        return {"days": []}

    canonical_endpoint = find_route_endpoint(
        app=client.app,
        path="/api/v1/vip/menu/weekly/plan",
        method="POST",
    )
    patch_endpoint_global(
        monkeypatch=monkeypatch,
        endpoint=canonical_endpoint,
        name="make_weekly_menu",
        value=fake_menu_builder,
    )
    payload = {
        **_valid_weekly_profile_payload(),
        "protein": 120.0,
        "protein_g": 121.0,
    }

    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=payload,
        headers=vip_headers,
    )

    assert response.status_code == 200, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    response_data = response.json()
    assert response_data["echo"]["protein"] == 120.0
    assert response_data["echo"]["protein_g"] == 121.0
    assert captured["builder_calls"] == 1
    profile = captured["profile"]
    assert getattr(profile, "sex") == payload["sex"]
    assert getattr(profile, "goal") == payload["goal"]
    assert not hasattr(profile, "protein")
    assert not hasattr(profile, "protein_g")


def test_vip_weekly_plan_maps_runtime_profile_error_to_static_422(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    async def rejecting_runtime(*args: object, **kwargs: object) -> object:
        raise fitchef_runtime.WeeklyProfileInputError(invalid_fields=("age",))

    monkeypatch.setattr(fitchef_runtime, "run_weekly_plan_task", rejecting_runtime)

    response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=_valid_weekly_profile_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    response_data = response.json()
    assert response_data == _INVALID_WEEKLY_PAYLOAD
    assert response_data.get("status") is None


def test_deprecated_weekly_plan_parses_malformed_json_before_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vip/weekly-plan",
        content=b"{",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json() == {"detail": "Invalid JSON payload"}


def test_deprecated_weekly_plan_auth_precedes_profile_validation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")

    response = client.post("/api/v1/vip/weekly-plan", json={})

    assert response.status_code == 403, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")


def test_deprecated_weekly_plan_rejects_omitted_goal_before_builder(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    builder_calls = 0

    def unexpected_builder(*args: object, **kwargs: object) -> object:
        nonlocal builder_calls
        builder_calls += 1
        raise AssertionError("builder must not run for incomplete input")

    deprecated_endpoint = find_route_endpoint(
        app=client.app,
        path="/api/v1/vip/weekly-plan",
        method="POST",
    )
    patch_endpoint_global(
        monkeypatch=monkeypatch,
        endpoint=deprecated_endpoint,
        name="make_weekly_menu",
        value=unexpected_builder,
    )
    payload = _valid_weekly_profile_payload()
    del payload["goal"]

    response = client.post("/api/v1/vip/weekly-plan", json=payload, headers=vip_headers)

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json() == _INVALID_WEEKLY_PAYLOAD
    assert builder_calls == 0


def test_deprecated_weekly_plan_preserves_builder_http_exception(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    def rejecting_builder(*, profile: object) -> object:
        raise HTTPException(status_code=409, detail="weekly plan conflict")

    deprecated_endpoint = find_route_endpoint(
        app=client.app,
        path="/api/v1/vip/weekly-plan",
        method="POST",
    )
    patch_endpoint_global(
        monkeypatch=monkeypatch,
        endpoint=deprecated_endpoint,
        name="make_weekly_menu",
        value=rejecting_builder,
    )

    response = client.post(
        "/api/v1/vip/weekly-plan",
        json=_valid_weekly_profile_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 409, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json() == {"detail": "weekly plan conflict"}


def test_vip_weekly_plan_echo(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    vip_headers: dict[str, str],
) -> None:
    """Test VIP weekly plan endpoint returns echo structure"""
    import app.routers.vip as vip

    monkeypatch.setattr(vip, "make_weekly_menu", None)
    payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "activity": "moderate",
        "goal": "maintain",
        "calories": 2000,
        "protein": 150,
        "goals": {"calories": 2000, "protein": 150},
        "constraints": {"diet_flags": ["VEG"]},
    }
    r = client.post("/api/v1/vip/menu/weekly/plan", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    # Check that original payload fields are present in echo
    assert data["echo"]["goals"] == payload["goals"]
    assert data["echo"]["constraints"] == payload["constraints"]


def test_vip_weekly_repair_echo(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP weekly repair endpoint returns echo structure"""
    payload = {"menu": {"days": 7, "meals": []}, "deficits": {"Ca": 200, "VitD": 100}}
    r = client.post("/api/v1/vip/menu/weekly/repair", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert data["echo"] == payload


def test_vip_module_enabled(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Ensure VIP module is enabled and the health endpoint responds with 200."""
    r = client.get("/api/v1/vip/health", headers=vip_headers)
    # VIP module is enabled, so expect 200
    assert r.status_code == 200


def test_vip_shoplist_weekly(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, vip_headers: dict[str, str]
) -> None:
    """Test VIP weekly shoplist endpoint"""

    # Enable VIP module
    def mock_is_vip_module_enabled() -> bool:
        return True

    monkeypatch.setattr(
        "app.routers.vip_shoplist.is_vip_module_enabled",
        mock_is_vip_module_enabled,
    )

    # Use new API format for vip_shoplist router
    payload = {
        "days": [
            {
                "items": [
                    {"food_id": "carrot", "qty": {"value": "100", "unit": "G"}, "form": "RAW"},
                    {"food_id": "onion", "qty": {"value": "50", "unit": "G"}, "form": "RAW"},
                    {"food_id": "milk", "qty": {"value": "200", "unit": "ML"}, "form": "RAW"},
                ],
                "packaging_rules": [
                    {
                        "food_id": "carrot",
                        "pack_size": {"value": "500", "unit": "G"},
                        "rounding": "CEIL",
                        "min_packs": 1,
                    },
                    {
                        "food_id": "onion",
                        "pack_size": {"value": "500", "unit": "G"},
                        "rounding": "CEIL",
                        "min_packs": 1,
                    },
                    {
                        "food_id": "milk",
                        "pack_size": {"value": "1000", "unit": "ML"},
                        "rounding": "CEIL",
                        "min_packs": 1,
                    },
                ],
            },
            {
                "items": [
                    {"food_id": "carrot", "qty": {"value": "150", "unit": "G"}, "form": "RAW"},
                    {"food_id": "potato", "qty": {"value": "200", "unit": "G"}, "form": "RAW"},
                ],
                "packaging_rules": [
                    {
                        "food_id": "carrot",
                        "pack_size": {"value": "500", "unit": "G"},
                        "rounding": "CEIL",
                        "min_packs": 1,
                    },
                    {
                        "food_id": "potato",
                        "pack_size": {"value": "500", "unit": "G"},
                        "rounding": "CEIL",
                        "min_packs": 1,
                    },
                ],
            },
        ]
    }

    r = client.post("/api/v1/vip/shoplist/weekly", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert "days" in data
    assert isinstance(data["days"], list)
    assert len(data["days"]) == 2


def test_vip_shoplist_daily(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, vip_headers: dict[str, str]
) -> None:
    """Test VIP daily shoplist endpoint"""

    # Enable VIP module
    def mock_is_vip_module_enabled() -> bool:
        return True

    monkeypatch.setattr(
        "app.routers.vip_shoplist.is_vip_module_enabled",
        mock_is_vip_module_enabled,
    )

    # Use new API format for vip_shoplist router
    payload = {
        "items": [
            {"food_id": "carrot", "qty": {"value": "100", "unit": "G"}, "form": "RAW"},
            {"food_id": "onion", "qty": {"value": "50", "unit": "G"}, "form": "RAW"},
            {"food_id": "milk", "qty": {"value": "200", "unit": "ML"}, "form": "RAW"},
        ],
        "packaging_rules": [
            {
                "food_id": "carrot",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "onion",
                "pack_size": {"value": "500", "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
            {
                "food_id": "milk",
                "pack_size": {"value": "1000", "unit": "ML"},
                "rounding": "CEIL",
                "min_packs": 1,
            },
        ],
    }

    r = client.post("/api/v1/vip/shoplist/daily", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert "packed" in data
    assert "unpacked" in data
    assert "analytics" in data


def test_vip_shoplist_formats(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP shoplist formats endpoint"""
    r = client.get("/api/v1/vip/shoplist/formats", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "formats" in data
    assert "locales" in data
    assert "json" in data["formats"]
    assert "csv" in data["formats"]
    assert "text" in data["formats"]
    assert "ru" in data["locales"]
    assert "en" in data["locales"]
    assert "es" in data["locales"]


def test_vip_regions(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP regions endpoint"""
    r = client.get("/api/v1/vip/regions", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "regions" in data
    assert "total_regions" in data
    assert isinstance(data["regions"], list)


def test_vip_region_search(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP region search endpoint"""
    r = client.get("/api/v1/vip/regions/es/search?query=tomato", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "query" in data
    assert "products" in data
    assert data["region"] == "es"
    assert data["query"] == "tomato"


def test_vip_region_categories(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP region categories endpoint"""
    r = client.get("/api/v1/vip/regions/es/categories", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "categories" in data
    assert "total_categories" in data
    assert data["region"] == "es"


def test_vip_region_stores(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP region stores endpoint"""
    r = client.get("/api/v1/vip/regions/es/stores", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "stores" in data
    assert "total_stores" in data
    assert data["region"] == "es"


def test_vip_region_price_comparison(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP region price comparison endpoint"""
    r = client.get("/api/v1/vip/regions/compare/tomato", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "product_name" in data
    assert "regions" in data
    assert "comparison" in data
    assert data["product_name"] == "tomato"


def test_vip_recipe_synthesize(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP recipe synthesis endpoint"""
    payload = {
        "ingredients": [
            {"name": "chicken", "amount": 300, "unit": "g"},
            {"name": "vegetables", "amount": 200, "unit": "g"},
            {"name": "oil", "amount": 20, "unit": "ml"},
        ],
        "cuisine_preference": "asian",
        "difficulty_preference": "easy",
        "servings": 4,
    }

    r = client.post("/api/v1/vip/recipes/synthesize", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "recipe" in data
    assert data["recipe"] is not None
    assert "recipe_id" in data["recipe"]
    assert "title" in data["recipe"]
    assert "ingredients" in data["recipe"]
    assert "steps" in data["recipe"]


def test_vip_recipe_weekly(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP weekly recipe synthesis endpoint"""
    payload = {
        "week_plan": {
            "days": [
                {
                    "day": "Monday",
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 200, "unit": "g"},
                                {"name": "rice", "amount": 150, "unit": "g"},
                            ]
                        }
                    ],
                },
                {
                    "day": "Tuesday",
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "salmon", "amount": 250, "unit": "g"},
                                {"name": "vegetables", "amount": 200, "unit": "g"},
                            ]
                        }
                    ],
                },
            ]
        },
        "recipes_per_day": 1,
    }

    r = client.post("/api/v1/vip/recipes/weekly", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "weekly_recipes" in data
    assert "total_recipes" in data
    assert data["total_recipes"] > 0


def test_vip_recipe_templates(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP recipe templates endpoint"""
    r = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "templates" in data
    assert "total_templates" in data
    assert isinstance(data["templates"], list)
    assert data["total_templates"] > 0


def test_vip_auto_repair_weekly(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP auto-repair weekly plan endpoint"""
    payload = {
        "week_plan": {
            "days": [
                {
                    "day": "Monday",
                    "meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}],
                }
            ]
        },
        "targets": {
            "iron_mg": [6.0, 8.0, 45.0],
            "calcium_mg": [800.0, 1000.0, 2500.0],
            "magnesium_mg": [300.0, 400.0, 700.0],
            "zinc_mg": [8.0, 11.0, 40.0],
            "potassium_mg": [3500.0, 4700.0, 5000.0],
            "iodine_ug": [130.0, 150.0, 1100.0],
            "selenium_ug": [45.0, 55.0, 400.0],
            "folate_ug": [320.0, 400.0, 1000.0],
            "b12_ug": [2.0, 2.4, 100.0],
            "vitamin_d_iu": [400.0, 600.0, 4000.0],
            "vitamin_a_ug": [600.0, 900.0, 3000.0],
            "vitamin_c_mg": [75.0, 90.0, 2000.0],
        },
        "strategy": "balanced",
        "user_preferences": {},
    }

    r = client.post("/api/v1/vip/auto-repair/weekly", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "error"
    assert data["code"] == "auto_repair_failed"
    assert "repair_result" in data
    assert data["repair_result"] is not None
    assert data["repair_result"]["status"] == "failed"
    assert data["repair_result"]["iterations"] == 1


def test_vip_auto_repair_suggestions(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP auto-repair suggestions endpoint"""
    payload = {
        "week_plan": {
            "days": [
                {
                    "day": "Monday",
                    "meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}],
                }
            ]
        },
        "targets": {
            "iron_mg": 18.0,
            "calcium_mg": 1000.0,
            "magnesium_mg": 400.0,
            "zinc_mg": 11.0,
            "potassium_mg": 3500.0,
            "iodine_ug": 150.0,
            "selenium_ug": 55.0,
            "folate_ug": 400.0,
            "b12_ug": 2.4,
            "vitamin_d_iu": 20.0,
            "vitamin_a_ug": 900.0,
            "vitamin_c_mg": 90.0,
        },
    }

    r = client.post("/api/v1/vip/auto-repair/suggestions", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "suggestions" in data
    assert "total_suggestions" in data
    assert isinstance(data["suggestions"], list)


def test_vip_auto_repair_strategies(client: TestClient, vip_headers: dict[str, str]) -> None:
    """Test VIP auto-repair strategies endpoint"""
    r = client.get("/api/v1/vip/auto-repair/strategies", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "strategies" in data
    assert "total_strategies" in data
    assert isinstance(data["strategies"], list)
    assert data["total_strategies"] == 3

    # Проверяем, что есть все три стратегии
    strategy_names = [s["name"] for s in data["strategies"]]
    assert "conservative" in strategy_names
    assert "balanced" in strategy_names
    assert "aggressive" in strategy_names

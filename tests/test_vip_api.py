# -*- coding: utf-8 -*-
"""
VIP API Tests

RU: Тесты для VIP API эндпоинтов
EN: Tests for VIP API endpoints
"""

import pytest
from fastapi.testclient import TestClient


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
    from fastapi.routing import APIRoute

    def fake_make_weekly_menu(*, profile: object) -> dict[str, object]:
        return {
            "week_start": "2026-01-01",
            "daily_menus": [],
            "weekly_coverage": {},
            "shopping_list": [],
            "total_cost": 0,
            "adherence_score": 0,
        }

    deprecated_route = next(
        (
            r
            for r in client.app.routes
            if isinstance(r, APIRoute)
            and r.path == "/api/v1/vip/weekly-plan"
            and "POST" in (r.methods or set())
        ),
        None,
    )
    assert deprecated_route is not None, "POST /api/v1/vip/weekly-plan route not found"
    # NOTE: String-based module patching (e.g. "app.routers.vip.make_weekly_menu") can be flaky
    # under dual-module / reload / shim-import behavior. Patch the registered route handler globals
    # for determinism (see docs/ENGINEERING_LESSONS.md).
    monkeypatch.setitem(
        deprecated_route.endpoint.__globals__, "make_weekly_menu", fake_make_weekly_menu
    )
    assert deprecated_route.endpoint.__globals__["make_weekly_menu"] is fake_make_weekly_menu

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
        "strategy": "balanced",
        "user_preferences": {},
    }

    r = client.post("/api/v1/vip/auto-repair/weekly", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "repair_result" in data
    assert data["repair_result"] is not None
    assert "status" in data["repair_result"]
    assert "iterations" in data["repair_result"]


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

# -*- coding: utf-8 -*-
"""
VIP API Tests

RU: Тесты для VIP API эндпоинтов
EN: Tests for VIP API endpoints
"""

import pytest
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app

# Type assertion to satisfy type checker
assert isinstance(app.app, FastAPI), "app should be FastAPI instance"

client = TestClient(cast(ASGIApp, app.app))


def test_vip_health(vip_headers):
    """Test VIP health endpoint returns 200"""
    r = client.get("/api/v1/vip/health", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["module"] == "vip"
    assert "features" in data


def test_vip_weekly_plan_echo(vip_headers):
    """Test VIP weekly plan endpoint returns echo structure"""
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


def test_vip_weekly_repair_echo(vip_headers):
    """Test VIP weekly repair endpoint returns echo structure"""
    payload = {"menu": {"days": 7, "meals": []}, "deficits": {"Ca": 200, "VitD": 100}}
    r = client.post("/api/v1/vip/menu/weekly/repair", json=payload, headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert data["echo"] == payload


def test_vip_module_enabled(vip_headers):
    """Ensure VIP module is enabled and the health endpoint responds with 200."""
    # Confirm the FastAPI app is initialised with the VIP router
    assert isinstance(app.app, FastAPI), "app should be FastAPI instance"
    client = TestClient(cast(ASGIApp, app.app))
    r = client.get("/api/v1/vip/health", headers=vip_headers)
    # VIP module is enabled, so expect 200
    assert r.status_code == 200


def test_vip_shoplist_weekly(monkeypatch):
    """Test VIP weekly shoplist endpoint"""
    import app
    from app.middleware import api_tiers

    # Enable VIP module
    def mock_is_vip_module_enabled() -> bool:
        return True

    monkeypatch.setattr(
        "app.routers.vip_shoplist.is_vip_module_enabled",
        mock_is_vip_module_enabled,
    )

    # Override VIP tier dependency
    async def mock_require_vip_tier() -> str:
        return "vip"

    app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

    try:
        client = TestClient(cast(ASGIApp, app.app))

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

        from app.middleware.api_tiers import TEST_KEY_VIP

        r = client.post(
            "/api/v1/vip/shoplist/weekly", json=payload, headers={"X-API-Key": TEST_KEY_VIP}
        )
        assert r.status_code == 200
        data = r.json()
        assert "days" in data
        assert isinstance(data["days"], list)
        assert len(data["days"]) == 2
    finally:
        app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)


def test_vip_shoplist_daily(monkeypatch):
    """Test VIP daily shoplist endpoint"""
    import app
    from app.middleware import api_tiers

    # Enable VIP module
    def mock_is_vip_module_enabled() -> bool:
        return True

    monkeypatch.setattr(
        "app.routers.vip_shoplist.is_vip_module_enabled",
        mock_is_vip_module_enabled,
    )

    # Override VIP tier dependency
    async def mock_require_vip_tier() -> str:
        return "vip"

    app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

    try:
        # Create fresh TestClient after setting dependency_overrides
        client = TestClient(cast(ASGIApp, app.app))

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

        from app.middleware.api_tiers import TEST_KEY_VIP

        r = client.post(
            "/api/v1/vip/shoplist/daily", json=payload, headers={"X-API-Key": TEST_KEY_VIP}
        )
        assert r.status_code == 200
        data = r.json()
        assert "packed" in data
        assert "unpacked" in data
        assert "analytics" in data
    finally:
        app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)


def test_vip_shoplist_formats(vip_headers):
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


def test_vip_regions(vip_headers):
    """Test VIP regions endpoint"""
    r = client.get("/api/v1/vip/regions", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "regions" in data
    assert "total_regions" in data
    assert isinstance(data["regions"], list)


def test_vip_region_search(vip_headers):
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


def test_vip_region_categories(vip_headers):
    """Test VIP region categories endpoint"""
    r = client.get("/api/v1/vip/regions/es/categories", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "categories" in data
    assert "total_categories" in data
    assert data["region"] == "es"


def test_vip_region_stores(vip_headers):
    """Test VIP region stores endpoint"""
    r = client.get("/api/v1/vip/regions/es/stores", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "stores" in data
    assert "total_stores" in data
    assert data["region"] == "es"


def test_vip_region_price_comparison(vip_headers):
    """Test VIP region price comparison endpoint"""
    r = client.get("/api/v1/vip/regions/compare/tomato", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "product_name" in data
    assert "regions" in data
    assert "comparison" in data
    assert data["product_name"] == "tomato"


def test_vip_recipe_synthesize(vip_headers):
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


def test_vip_recipe_weekly(vip_headers):
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


def test_vip_recipe_templates(vip_headers):
    """Test VIP recipe templates endpoint"""
    r = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "templates" in data
    assert "total_templates" in data
    assert isinstance(data["templates"], list)
    assert data["total_templates"] > 0


def test_vip_auto_repair_weekly(vip_headers):
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


def test_vip_auto_repair_suggestions(vip_headers):
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


def test_vip_auto_repair_strategies(vip_headers):
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

# -*- coding: utf-8 -*-
"""
VIP API Tests

RU: Тесты для VIP API эндпоинтов
EN: Tests for VIP API endpoints
"""

from typing import cast
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app
from app.routers import vip as vip_router

# Type assertion to satisfy type checker
assert isinstance(app.app, FastAPI), "app should be FastAPI instance"

client = TestClient(cast(ASGIApp, app.app))


def test_vip_health() -> None:
    """Test VIP health endpoint returns 200"""
    r = client.get("/api/v1/vip/health", headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["module"] == "vip"
    assert "features" in data


def test_vip_weekly_plan_echo() -> None:
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
    r = client.post("/api/v1/vip/menu/weekly/plan", json=payload, headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    # Check that original payload fields are present in echo
    assert data["echo"]["goals"] == payload["goals"]
    assert data["echo"]["constraints"] == payload["constraints"]


def test_vip_weekly_repair_echo() -> None:
    """Test VIP weekly repair endpoint returns echo structure"""
    payload = {"menu": {"days": 7, "meals": []}, "deficits": {"Ca": 200, "VitD": 100}}
    r = client.post(
        "/api/v1/vip/menu/weekly/repair", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert data["echo"] == payload


def test_vip_module_enabled() -> None:
    """Ensure VIP module is enabled and the health endpoint responds with 200."""
    # Confirm the FastAPI app is initialised with the VIP router
    assert isinstance(app.app, FastAPI), "app should be FastAPI instance"
    client = TestClient(cast(ASGIApp, app.app))
    r = client.get("/api/v1/vip/health", headers={"X-API-Key": "test_key"})
    # VIP module is enabled, so expect 200
    assert r.status_code == 200


def test_vip_shoplist_weekly() -> None:
    """Test VIP weekly shoplist endpoint"""
    payload = {
        "days": [
            {
                "meals": [
                    {
                        "ingredients": [
                            {"name": "Морковь", "amount": 100, "unit": "g"},
                            {"name": "Лук", "amount": 50, "unit": "g"},
                            {"name": "Молоко", "amount": 200, "unit": "ml"},
                        ]
                    }
                ]
            },
            {
                "meals": [
                    {
                        "ingredients": [
                            {"name": "Морковь", "amount": 150, "unit": "g"},
                            {"name": "Картофель", "amount": 200, "unit": "g"},
                        ]
                    }
                ]
            },
        ]
    }

    r = client.post("/api/v1/vip/shoplist/weekly", json=payload, headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert "shopping_list" in data
    assert "total_items" in data
    assert data["echo"] == payload


def test_vip_shoplist_daily() -> None:
    """Test VIP daily shoplist endpoint"""
    payload = {
        "ingredients": [
            {"name": "Морковь", "amount": 100, "unit": "g"},
            {"name": "Лук", "amount": 50, "unit": "g"},
            {"name": "Молоко", "amount": 200, "unit": "ml"},
        ]
    }

    r = client.post("/api/v1/vip/shoplist/daily", json=payload, headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert "shopping_list" in data
    assert "total_items" in data
    assert data["echo"] == payload


def test_vip_shoplist_formats() -> None:
    """Test VIP shoplist formats endpoint"""
    r = client.get("/api/v1/vip/shoplist/formats", headers={"X-API-Key": "test_key"})
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


def test_vip_regions() -> None:
    """Test VIP regions endpoint"""
    r = client.get("/api/v1/vip/regions", headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "regions" in data
    assert "total_regions" in data
    assert isinstance(data["regions"], list)


def test_vip_region_search() -> None:
    """Test VIP region search endpoint"""
    # Mock search_products to return success
    mock_product = MagicMock()
    mock_product.product_id = "123"
    mock_product.name_es = "Tomate"
    mock_product.name_en = "Tomato"
    mock_product.category = "vegetables"
    mock_product.unit = "kg"
    mock_product.typical_package_size = 1.0
    mock_product.price_eur = 2.5
    mock_product.price_usd = 2.8
    mock_product.store_chain = "Carrefour"
    mock_product.region = "ES"

    mock_search_result = MagicMock()
    mock_search_result.products = [mock_product]
    mock_search_result.total_count = 1

    # Ensure search_products is not None before patching
    # If it's None, the endpoint will return error before calling the function
    original_search_products = vip_router.search_products
    if original_search_products is None:
        # If search_products is None, we need to set it to a mock function first
        vip_router.search_products = lambda *args, **kwargs: mock_search_result

    with patch.object(vip_router, "search_products", return_value=mock_search_result):
        r = client.get(
            "/api/v1/vip/regions/es/search?query=tomato", headers={"X-API-Key": "test_key"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}. Response: {r.text}"
        data = r.json()
        assert (
            data["status"] == "success"
        ), f"Expected 'success', got '{data.get('status')}'. Full response: {data}"
        assert "region" in data
        assert "query" in data
        assert "products" in data
        assert data["region"] == "es"
        assert data["query"] == "tomato"


def test_vip_region_categories() -> None:
    """Test VIP region categories endpoint"""
    # Mock get_region_catalog to return success
    mock_catalog = MagicMock()
    mock_catalog.get_categories.return_value = ["dairy", "vegetables", "fruits"]

    # Ensure get_region_catalog is not None before patching
    original_get_region_catalog = vip_router.get_region_catalog
    if original_get_region_catalog is None:
        vip_router.get_region_catalog = lambda *args, **kwargs: mock_catalog

    with patch.object(vip_router, "get_region_catalog", return_value=mock_catalog):
        r = client.get("/api/v1/vip/regions/es/categories", headers={"X-API-Key": "test_key"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}. Response: {r.text}"
        data = r.json()
        assert (
            data["status"] == "success"
        ), f"Expected 'success', got '{data.get('status')}'. Full response: {data}"
        assert "region" in data
        assert "categories" in data
        assert "total_categories" in data
        assert data["region"] == "es"


def test_vip_region_stores() -> None:
    """Test VIP region stores endpoint"""
    r = client.get("/api/v1/vip/regions/es/stores", headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "stores" in data
    assert "total_stores" in data
    assert data["region"] == "es"


def test_vip_region_price_comparison() -> None:
    """Test VIP region price comparison endpoint"""
    r = client.get("/api/v1/vip/regions/compare/tomato", headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "product_name" in data
    assert "regions" in data
    assert "comparison" in data
    assert data["product_name"] == "tomato"


def test_vip_recipe_synthesize() -> None:
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

    r = client.post(
        "/api/v1/vip/recipes/synthesize", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "recipe" in data
    assert data["recipe"] is not None
    assert "recipe_id" in data["recipe"]
    assert "title" in data["recipe"]
    assert "ingredients" in data["recipe"]
    assert "steps" in data["recipe"]


def test_vip_recipe_weekly() -> None:
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

    r = client.post("/api/v1/vip/recipes/weekly", json=payload, headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "weekly_recipes" in data
    assert "total_recipes" in data
    assert data["total_recipes"] > 0


def test_vip_recipe_templates() -> None:
    """Test VIP recipe templates endpoint"""
    r = client.get("/api/v1/vip/recipes/templates", headers={"X-API-Key": "test_key"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "templates" in data
    assert "total_templates" in data
    assert isinstance(data["templates"], list)
    assert data["total_templates"] > 0


def test_vip_auto_repair_weekly() -> None:
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

    r = client.post(
        "/api/v1/vip/auto-repair/weekly", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "repair_result" in data
    assert data["repair_result"] is not None
    assert "status" in data["repair_result"]
    assert "iterations" in data["repair_result"]


def test_vip_auto_repair_suggestions() -> None:
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

    r = client.post(
        "/api/v1/vip/auto-repair/suggestions", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "suggestions" in data
    assert "total_suggestions" in data
    assert isinstance(data["suggestions"], list)


def test_vip_auto_repair_strategies() -> None:
    """Test VIP auto-repair strategies endpoint"""
    r = client.get("/api/v1/vip/auto-repair/strategies", headers={"X-API-Key": "test_key"})
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

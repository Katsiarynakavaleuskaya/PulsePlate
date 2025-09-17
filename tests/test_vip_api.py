# -*- coding: utf-8 -*-
"""
VIP API Tests

RU: Тесты для VIP API эндпоинтов
EN: Tests for VIP API endpoints
"""

from fastapi.testclient import TestClient
from fastapi import FastAPI

import app as app_module

# Type assertion to satisfy type checker
assert isinstance(app_module.app, FastAPI), "app should be FastAPI instance"

client = TestClient(app_module.app)


def test_vip_health():
    """Test VIP health endpoint returns 200"""
    r = client.get("/api/v1/vip/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["module"] == "vip"
    assert "features" in data


def test_vip_weekly_plan_echo():
    """Test VIP weekly plan endpoint returns echo structure"""
    payload = {
        "goals": {"calories": 2000, "protein": 150},
        "constraints": {"diet_flags": ["VEG"]},
    }
    r = client.post("/api/v1/vip/menu/weekly/plan", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert data["echo"] == payload


def test_vip_weekly_repair_echo():
    """Test VIP weekly repair endpoint returns echo structure"""
    payload = {"menu": {"days": 7, "meals": []}, "deficits": {"Ca": 200, "VitD": 100}}
    r = client.post("/api/v1/vip/menu/weekly/repair", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert data["echo"] == payload


def test_vip_module_disabled():
    """Test that VIP endpoints return 404 when module is disabled"""
    import importlib
    import os

    # Temporarily disable VIP module
    original_value = os.environ.get("VIP_MODULE_ENABLED")
    os.environ["VIP_MODULE_ENABLED"] = "false"

    try:
        # Reimport app with disabled VIP
        importlib.reload(app_module)

        assert isinstance(app_module.app, FastAPI), "app should be FastAPI instance"
        client_disabled = TestClient(app_module.app)
        r = client_disabled.get("/api/v1/vip/health")
        assert r.status_code == 404
    finally:
        # Restore original value
        if original_value is not None:
            os.environ["VIP_MODULE_ENABLED"] = original_value
        else:
            os.environ.pop("VIP_MODULE_ENABLED", None)
        # Reimport app with VIP enabled
        importlib.reload(app_module)


def test_vip_shoplist_weekly():
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

    r = client.post("/api/v1/vip/shoplist/weekly", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert "shopping_list" in data
    assert "total_items" in data
    assert data["echo"] == payload


def test_vip_shoplist_daily():
    """Test VIP daily shoplist endpoint"""
    payload = {
        "ingredients": [
            {"name": "Морковь", "amount": 100, "unit": "g"},
            {"name": "Лук", "amount": 50, "unit": "g"},
            {"name": "Молоко", "amount": 200, "unit": "ml"},
        ]
    }

    r = client.post("/api/v1/vip/shoplist/daily", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "echo" in data
    assert "shopping_list" in data
    assert "total_items" in data
    assert data["echo"] == payload


def test_vip_shoplist_formats():
    """Test VIP shoplist formats endpoint"""
    r = client.get("/api/v1/vip/shoplist/formats")
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


def test_vip_regions():
    """Test VIP regions endpoint"""
    r = client.get("/api/v1/vip/regions")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "regions" in data
    assert "total_regions" in data
    assert isinstance(data["regions"], list)


def test_vip_region_search():
    """Test VIP region search endpoint"""
    r = client.get("/api/v1/vip/regions/es/search?query=tomato")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "query" in data
    assert "products" in data
    assert data["region"] == "es"
    assert data["query"] == "tomato"


def test_vip_region_categories():
    """Test VIP region categories endpoint"""
    r = client.get("/api/v1/vip/regions/es/categories")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "categories" in data
    assert "total_categories" in data
    assert data["region"] == "es"


def test_vip_region_stores():
    """Test VIP region stores endpoint"""
    r = client.get("/api/v1/vip/regions/es/stores")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "region" in data
    assert "stores" in data
    assert "total_stores" in data
    assert data["region"] == "es"


def test_vip_region_price_comparison():
    """Test VIP region price comparison endpoint"""
    r = client.get("/api/v1/vip/regions/compare/tomato")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "product_name" in data
    assert "regions" in data
    assert "comparison" in data
    assert data["product_name"] == "tomato"


def test_vip_recipe_synthesize():
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

    r = client.post("/api/v1/vip/recipes/synthesize", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "recipe" in data
    assert data["recipe"] is not None
    assert "recipe_id" in data["recipe"]
    assert "title" in data["recipe"]
    assert "ingredients" in data["recipe"]
    assert "steps" in data["recipe"]


def test_vip_recipe_weekly():
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

    r = client.post("/api/v1/vip/recipes/weekly", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "weekly_recipes" in data
    assert "total_recipes" in data
    assert data["total_recipes"] > 0


def test_vip_recipe_templates():
    """Test VIP recipe templates endpoint"""
    r = client.get("/api/v1/vip/recipes/templates")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "templates" in data
    assert "total_templates" in data
    assert isinstance(data["templates"], list)
    assert data["total_templates"] > 0


def test_vip_auto_repair_weekly():
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

    r = client.post("/api/v1/vip/auto-repair/weekly", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "repair_result" in data
    assert data["repair_result"] is not None
    assert "status" in data["repair_result"]
    assert "iterations" in data["repair_result"]


def test_vip_auto_repair_suggestions():
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

    r = client.post("/api/v1/vip/auto-repair/suggestions", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "suggestions" in data
    assert "total_suggestions" in data
    assert isinstance(data["suggestions"], list)


def test_vip_auto_repair_strategies():
    """Test VIP auto-repair strategies endpoint"""
    r = client.get("/api/v1/vip/auto-repair/strategies")
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

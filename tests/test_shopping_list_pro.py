"""Tests for PRO Shopping List Generator endpoint.

Tests:
1. API contract validation (XOR source, preferences)
2. Core logic (extraction, aggregation, categorization)
3. Edge cases (empty data, unknown categories)
"""

import pytest
from fastapi.testclient import TestClient


def test_shopping_list_requires_plan_source(client: TestClient):
    """Verify that either weekly_plan_id or plan_data must be provided."""
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={"preferences": {}},
    )
    assert response.status_code == 400
    assert "weekly_plan_id" in response.json()["detail"]


def test_shopping_list_rejects_both_sources(client: TestClient):
    """Verify that both weekly_plan_id and plan_data cannot be provided simultaneously."""
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "weekly_plan_id": "plan_123",
            "plan_data": {},
        },
    )
    assert response.status_code == 400
    assert "Cannot provide both" in response.json()["detail"]


def test_shopping_list_stub_inline_plan(client: TestClient):
    """Verify real implementation extracts and aggregates ingredients correctly."""
    # Minimal but realistic plan_data structure
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "oatmeal_banana",
                        "grams": {
                            "oats": 80.0,
                            "banana": 120.0,
                            "milk": 200.0,
                        },
                    },
                    {
                        "title": "chicken_rice",
                        "grams": {
                            "chicken_breast": 150.0,
                            "rice": 100.0,
                        },
                    },
                ]
            }
        ]
    }

    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "plan_data": plan_data,
            "preferences": {
                "group_by": "category",
                "unit_system": "metric",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "categories" in data
    assert "total_items" in data
    assert "generated_at" in data
    assert "meta" in data

    # Validate meta
    assert data["meta"]["source"] == "inline_plan"
    assert data["meta"]["unit_system"] == "metric"
    assert isinstance(data["meta"]["warnings"], list)

    # Should have aggregated items
    assert data["total_items"] == 5  # oats, banana, milk, chicken_breast, rice
    assert len(data["categories"]) > 0

    # Verify categories have required fields
    for category in data["categories"]:
        assert "key" in category
        assert "title" in category
        assert "items" in category
        for item in category["items"]:
            assert "key" in item
            assert "name" in item
            assert "quantity" in item
            assert "unit" in item
            assert "recipe_refs" in item


def test_shopping_list_stub_plan_id(client: TestClient):
    """Verify weekly_plan_id path returns 501 (not yet implemented)."""
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "weekly_plan_id": "plan_abc123",
        },
    )
    assert response.status_code == 501
    assert "not yet implemented" in response.json()["detail"]


def test_shopping_list_preferences_defaults(client: TestClient):
    """Verify that preferences have correct defaults."""
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "plan_data": {"daily_menus": []},
            # Omit preferences to test defaults
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Default unit_system should be metric
    assert data["meta"]["unit_system"] == "metric"
    # Empty plan should trigger warning
    assert "missing_ingredients" in data["meta"]["warnings"]


def test_shopping_list_aggregates_same_ingredient(client: TestClient):
    """Test aggregation of same ingredient across multiple meals."""
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {"title": "breakfast", "grams": {"chicken_breast": 200.0}},
                    {"title": "lunch", "grams": {"chicken_breast": 150.0}},
                ]
            }
        ]
    }

    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={"plan_data": plan_data},
    )
    assert response.status_code == 200
    data = response.json()

    # Should aggregate to single item
    assert data["total_items"] == 1

    # Find chicken in categories
    chicken_item = None
    for category in data["categories"]:
        for item in category["items"]:
            if item["key"] == "chicken_breast":
                chicken_item = item
                break

    assert chicken_item is not None
    assert chicken_item["quantity"] == 350.0  # 200 + 150
    assert chicken_item["unit"] == "g"
    assert len(chicken_item["recipe_refs"]) == 2
    assert "breakfast" in chicken_item["recipe_refs"]
    assert "lunch" in chicken_item["recipe_refs"]


def test_shopping_list_empty_ingredients_warning(client: TestClient):
    """Test that empty ingredients produces warning."""
    plan_data = {"daily_menus": [{"meals": [{"title": "empty", "grams": {}}]}]}

    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={"plan_data": plan_data},
    )
    assert response.status_code == 200
    data = response.json()

    # Should have warning
    assert "missing_ingredients" in data["meta"]["warnings"]
    assert data["total_items"] == 0
    assert len(data["categories"]) == 0


def test_shopping_list_unknown_category_warning(client: TestClient):
    """Test that unknown ingredients trigger category warnings."""
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "exotic_meal",
                        "grams": {
                            "dragon_fruit_powder": 50.0,
                            "unicorn_tears": 10.0,
                        },
                    }
                ]
            }
        ]
    }

    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={"plan_data": plan_data},
    )
    assert response.status_code == 200
    data = response.json()

    # Should have warnings for unknown categories
    warnings = data["meta"]["warnings"]
    assert any("unknown_category:dragon_fruit_powder" in w for w in warnings)
    assert any("unknown_category:unicorn_tears" in w for w in warnings)


def test_shopping_list_normalizes_keys(client: TestClient):
    """Test that ingredient keys are normalized (lowercase, snake_case)."""
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "meal1",
                        "grams": {
                            "Chicken Breast": 100.0,  # Should normalize to chicken_breast
                            "  Rice  ": 150.0,  # Should normalize to rice
                        },
                    }
                ]
            }
        ]
    }

    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={"plan_data": plan_data},
    )
    assert response.status_code == 200
    data = response.json()

    # Extract all item keys
    all_keys = []
    for category in data["categories"]:
        for item in category["items"]:
            all_keys.append(item["key"])

    # Should have normalized keys
    assert "chicken_breast" in all_keys
    assert "rice" in all_keys
    # Should NOT have un-normalized versions
    assert "Chicken Breast" not in all_keys
    assert "  Rice  " not in all_keys


def test_shopping_list_edge_cases_invalid_data(client: TestClient):
    """Test extraction with invalid/malformed data structures."""
    # Test various edge cases that should be handled gracefully
    # All test cases must pass basic request validation (have plan_data key)
    test_cases = [
        # Non-list daily_menus
        {"daily_menus": "not_a_list"},
        # Non-dict day
        {"daily_menus": ["not_a_dict"]},
        # Non-list meals
        {"daily_menus": [{"meals": "not_a_list"}]},
        # Non-dict meal
        {"daily_menus": [{"meals": ["not_a_dict"]}]},
        # Non-dict grams
        {"daily_menus": [{"meals": [{"grams": "not_a_dict"}]}]},
        # Non-string ingredient key (JSON converts int key to string, but simulating via list)
        {"daily_menus": [{"meals": [{"grams": []}]}]},  # empty list instead of dict
        # Invalid quantity (non-numeric)
        {"daily_menus": [{"meals": [{"grams": {"rice": "not_a_number"}}]}]},
        # Zero quantity (should be skipped)
        {"daily_menus": [{"meals": [{"grams": {"rice": 0}}]}]},
        # Negative quantity (should be skipped)
        {"daily_menus": [{"meals": [{"grams": {"rice": -50.0}}]}]},
    ]

    for plan_data in test_cases:
        response = client.post(
            "/api/v1/pro/meal/shopping-list",
            json={"plan_data": plan_data},
        )
        # Should handle gracefully without crashing
        assert response.status_code == 200
        data = response.json()
        # Should produce valid response (might be empty)
        assert "categories" in data
        assert "meta" in data
        # Invalid/empty data should result in missing_ingredients warning
        assert "missing_ingredients" in data["meta"]["warnings"]
        assert data["total_items"] == 0


def test_shopping_list_meal_without_title(client: TestClient):
    """Test that meals without title get fallback indexed key."""
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        # No title field - should use fallback meal_0_0
                        "grams": {"rice": 100.0}
                    }
                ]
            }
        ]
    }

    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={"plan_data": plan_data},
    )
    assert response.status_code == 200
    data = response.json()

    # Find rice item
    rice_item = None
    for category in data["categories"]:
        for item in category["items"]:
            if item["key"] == "rice":
                rice_item = item
                break

    assert rice_item is not None
    # Should have fallback recipe_ref
    assert len(rice_item["recipe_refs"]) == 1
    assert rice_item["recipe_refs"][0] == "meal_0_0"


def test_shopping_list_rounding_preferences(client: TestClient):
    """Test quantity rounding based on preferences."""
    plan_data = {"daily_menus": [{"meals": [{"title": "meal1", "grams": {"rice": 123.456}}]}]}

    # Test with round_quantities=True (default)
    response1 = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "plan_data": plan_data,
            "preferences": {"round_quantities": True},
        },
    )
    assert response1.status_code == 200
    data1 = response1.json()
    rice_qty1 = None
    for cat in data1["categories"]:
        for item in cat["items"]:
            if item["key"] == "rice":
                rice_qty1 = item["quantity"]
    assert rice_qty1 == 123.5  # Rounded to 1 decimal

    # Test with round_quantities=False
    response2 = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "plan_data": plan_data,
            "preferences": {"round_quantities": False},
        },
    )
    assert response2.status_code == 200
    data2 = response2.json()
    rice_qty2 = None
    for cat in data2["categories"]:
        for item in cat["items"]:
            if item["key"] == "rice":
                rice_qty2 = item["quantity"]
    assert rice_qty2 == 123.46  # Rounded to 2 decimals

"""Tests for PRO Shopping List Generator endpoint.

Tests contract validation and stub implementation.
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
    """Verify stub implementation returns valid DTO with inline plan_data."""
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "plan_data": {
                "daily_menus": [{"meals": [{"recipes": [{"name": "Chicken", "ingredients": []}]}]}]
            },
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
    assert "stub_implementation_active" in data["meta"]["warnings"]

    # Validate categories structure
    assert isinstance(data["categories"], list)
    if data["categories"]:
        category = data["categories"][0]
        assert "key" in category
        assert "title" in category
        assert "items" in category

        if category["items"]:
            item = category["items"][0]
            assert "key" in item
            assert "name" in item
            assert "quantity" in item
            assert "unit" in item
            assert "recipe_refs" in item


def test_shopping_list_stub_plan_id(client: TestClient):
    """Verify stub implementation returns valid DTO with weekly_plan_id."""
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "weekly_plan_id": "plan_abc123",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Validate meta source
    assert data["meta"]["source"] == "weekly_plan_id"


def test_shopping_list_preferences_defaults(client: TestClient):
    """Verify that preferences have correct defaults."""
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json={
            "plan_data": {},
            # Omit preferences to test defaults
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Default unit_system should be metric
    assert data["meta"]["unit_system"] == "metric"


# TODO(#XXX): Add integration tests when core logic is implemented
# - Test ingredient aggregation
# - Test unit normalization (metric/imperial)
# - Test duplicate merging
# - Test category grouping
# - Test recipe_refs population

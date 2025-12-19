"""Tests for day shopping list DB wiring (PR-3).

RU: Тесты для интеграции БД для дневного списка покупок.
EN: Tests for day shopping list database integration.
"""

from datetime import date
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.middleware.api_tiers import require_pro_tier
from app.models.plans import DayPlan
from core.db import AsyncSessionLocal


@pytest.fixture
def client_with_pro_access(app_module: ModuleType):
    """Create test client with PRO tier access bypassed.

    Uses app_module fixture from conftest for better test isolation.
    """
    # Override PRO tier requirement for testing
    app_module.app.dependency_overrides[require_pro_tier] = lambda: "test_api_key"

    client = TestClient(app_module.app)
    yield client

    # Cleanup: remove override after test
    app_module.app.dependency_overrides.pop(require_pro_tier, None)


@pytest.mark.asyncio
async def test_fetch_day_plan_when_exists_in_db(client_with_pro_access):
    """When day plan exists in DB, fetch_day_plan returns plan_data."""
    # Seed DB with day plan
    test_date = date(2025, 12, 20)
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "oatmeal_apple",
                        "grams": {
                            "oats": 60.0,
                            "apple": 100.0,
                            "milk": 150.0,
                        },
                    }
                ]
            }
        ]
    }

    if AsyncSessionLocal is None:
        pytest.skip("Async SQLAlchemy not configured")

    async with AsyncSessionLocal() as session:
        day_plan = DayPlan(
            user_id=1,  # Assume test user ID is 1
            date=test_date,
            plan_data=plan_data,
        )
        session.add(day_plan)
        await session.commit()

    # Call endpoint
    r = client_with_pro_access.get(f"/api/v1/pro/shoplist/day?date={test_date}&lang=en")
    assert r.status_code == 200
    body = r.json()

    # Should return items (not empty)
    assert body["items"], "Expected items when plan exists in DB"
    assert body["warnings"] == []

    # Verify items have correct structure
    for item in body["items"]:
        assert item["qty"] > 0
        assert item["unit"] in {"g", "ml", "pcs", "kg", "l"}
        assert item["aisle"] in {
            "produce",
            "protein",
            "dairy",
            "pantry",
            "frozen",
            "beverages",
            "snacks",
            "other",
        }


@pytest.mark.asyncio
async def test_fetch_day_plan_when_not_in_db(client_with_pro_access):
    """When no plan in DB, fetch_day_plan returns None → empty items + warning."""
    test_date = date(2025, 12, 25)

    r = client_with_pro_access.get(f"/api/v1/pro/shoplist/day?date={test_date}&lang=en")
    assert r.status_code == 200
    body = r.json()

    # Should return empty items with warning
    assert body["items"] == []
    assert body["warnings"] == ["no_day_plan"]


@pytest.mark.asyncio
async def test_day_plan_model_creation():
    """Test creating DayPlan model instance."""
    if AsyncSessionLocal is None:
        pytest.skip("Async SQLAlchemy not configured")

    async with AsyncSessionLocal() as session:
        day_plan = DayPlan(
            user_id=1,
            date=date(2025, 12, 19),
            plan_data={"daily_menus": []},
        )
        session.add(day_plan)
        await session.commit()

    # Query back in separate session
    async with AsyncSessionLocal() as session:
        stmt = select(DayPlan).where(DayPlan.user_id == 1).where(DayPlan.date == date(2025, 12, 19))
        result = await session.execute(stmt)
        fetched = result.scalars().first()

        assert fetched is not None
        assert fetched.user_id == 1
        assert fetched.date == date(2025, 12, 19)
        assert fetched.plan_data == {"daily_menus": []}

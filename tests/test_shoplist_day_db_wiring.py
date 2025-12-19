"""Tests for day shopping list DB wiring (PR-3).

RU: Тесты для интеграции БД для дневного списка покупок.
EN: Tests for day shopping list database integration.
"""

from datetime import date
from types import ModuleType
from typing import Any, AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.middleware.api_tiers import require_pro_tier
from app.models.plans import DayPlan
from core.db import AsyncSessionLocal
from core.models import User

# Test user ID used across all tests
TEST_USER_ID = 1


@pytest.fixture(autouse=True)
def _force_async_db(monkeypatch: Any) -> None:
    """Enable async SQLAlchemy only for this test module."""
    monkeypatch.setenv("DATABASE_USE_ASYNC", "1")


@pytest.fixture
async def test_user() -> AsyncGenerator[User, None]:
    """Create test user in DB for FK constraints.

    Creates user with id=TEST_USER_ID and cleans up after test.
    """
    if AsyncSessionLocal is None:
        pytest.skip("Async SQLAlchemy not configured")

    async with AsyncSessionLocal() as session:
        # Check if user already exists
        stmt = select(User).where(User.id == TEST_USER_ID)
        result = await session.execute(stmt)
        user = result.scalars().first()

        if user is None:
            user = User(
                id=TEST_USER_ID,
                email="test@example.com",
                name="Test User",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        yield user

    # Cleanup: delete test user and related day plans in a fresh session
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(delete(DayPlan).where(DayPlan.user_id == TEST_USER_ID))
            await session.execute(delete(User).where(User.id == TEST_USER_ID))
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
def client_with_pro_access(app_module: ModuleType) -> Generator[TestClient, None, None]:
    """Create test client with PRO tier access bypassed.

    Returns pro_ctx with user_id for proper fetch_day_plan behavior.
    """
    # Override PRO tier to return dict with user_id (not just string)
    app_module.app.dependency_overrides[require_pro_tier] = lambda: {"user_id": TEST_USER_ID}

    client = TestClient(app_module.app)
    yield client

    # Cleanup: remove override after test
    app_module.app.dependency_overrides.pop(require_pro_tier, None)


@pytest.mark.asyncio
async def test_fetch_day_plan_when_exists_in_db(
    client_with_pro_access: TestClient, test_user: User
) -> None:
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
            user_id=test_user.id,
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
async def test_fetch_day_plan_when_not_in_db(
    client_with_pro_access: TestClient, test_user: User
) -> None:
    """When no plan in DB, fetch_day_plan returns None → empty items + warning."""
    _ = test_user  # Ensure user exists for FK constraint
    test_date = date(2025, 12, 25)

    r = client_with_pro_access.get(f"/api/v1/pro/shoplist/day?date={test_date}&lang=en")
    assert r.status_code == 200
    body = r.json()

    # Should return empty items with warning
    assert body["items"] == []
    assert body["warnings"] == ["no_day_plan"]


@pytest.mark.asyncio
async def test_day_plan_model_creation(test_user: User) -> None:
    """Test creating DayPlan model instance."""
    if AsyncSessionLocal is None:
        pytest.skip("Async SQLAlchemy not configured")

    test_date = date(2025, 12, 19)

    async with AsyncSessionLocal() as session:
        day_plan = DayPlan(
            user_id=test_user.id,
            date=test_date,
            plan_data={"daily_menus": []},
        )
        session.add(day_plan)
        await session.commit()

    # Query back in separate session
    async with AsyncSessionLocal() as session:
        stmt = (
            select(DayPlan).where(DayPlan.user_id == test_user.id).where(DayPlan.date == test_date)
        )
        result = await session.execute(stmt)
        fetched = result.scalars().first()

        assert fetched is not None
        assert fetched.user_id == test_user.id
        assert fetched.date == test_date
        assert fetched.plan_data == {"daily_menus": []}


@pytest.mark.asyncio
async def test_day_plan_unique_user_date_constraint(test_user: User) -> None:
    """Test that (user_id, date) uniqueness is enforced."""
    if AsyncSessionLocal is None:
        pytest.skip("Async SQLAlchemy not configured")

    test_date = date(2025, 12, 21)

    # Create first day plan
    async with AsyncSessionLocal() as session:
        day_plan_1 = DayPlan(
            user_id=test_user.id,
            date=test_date,
            plan_data={"daily_menus": []},
        )
        session.add(day_plan_1)
        await session.commit()

    # Try to create duplicate — should fail
    async with AsyncSessionLocal() as session:
        day_plan_2 = DayPlan(
            user_id=test_user.id,
            date=test_date,
            plan_data={"daily_menus": [{"meals": []}]},
        )
        session.add(day_plan_2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

"""Tests for day shopping list DB wiring (PR-3).

RU: Тесты для интеграции БД для дневного списка покупок.
EN: Tests for day shopping list database integration.
"""

from datetime import date
from types import ModuleType
from typing import TYPE_CHECKING, AsyncGenerator, Generator, cast

import pytest
from fastapi.testclient import TestClient
from requests import Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.middleware.api_tiers import require_pro_tier
from app.models import DayPlan, WeeklyPlan
import core.db as core_db
from core.models import User
from tests._client import get_client

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Test user ID used across all tests
TEST_USER_ID = 1


def _reset_async_db_state() -> None:
    """Reset async DB globals to prevent leakage across tests."""
    async_engine = getattr(core_db, "_ASYNC_ENGINE", None)
    if async_engine is not None:
        try:
            # Dispose sync side from sync context to release pooled resources.
            async_engine.sync_engine.dispose()
        except Exception:
            pass

    core_db._ASYNC_ENGINE = None
    core_db.AsyncSessionLocal = None
    core_db.async_engine = None


@pytest.fixture(autouse=True)
def _async_db_state_isolation(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Isolate env + async DB globals per test to avoid xdist/order pollution."""
    monkeypatch.setenv("DATABASE_USE_ASYNC", "1")
    _reset_async_db_state()
    try:
        yield
    finally:
        _reset_async_db_state()


def _get_async_session_local() -> "async_sessionmaker[AsyncSession]":
    """Resolve AsyncSessionLocal after forcing async DB env.

    RU: core.db chitaet env dinamicheski, poetomu snachala vystavliaem env, potom initsializiruem engine.
    EN: core.db reads env dynamically, so set env first and then initialize async engine.
    """
    # Force lazy async engine/sessionmaker initialization after env wiring.
    core_db._get_async_engine()
    session_local = getattr(core_db, "AsyncSessionLocal", None)
    async_url = core_db._get_async_database_url()
    assert session_local is not None, (
        "AsyncSessionLocal is not configured. Expected core.db to expose AsyncSessionLocal "
        "when DATABASE_USE_ASYNC=1. "
        f"Resolved async_url={async_url!r}. "
        "Fix core.db async wiring or ensure async deps are installed."
    )
    return cast("async_sessionmaker[AsyncSession]", session_local)


def _assert_json_response(response: Response) -> dict[str, object]:
    """Assert JSON content-type before body parsing and return JSON object."""
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("application/json")
    body = response.json()
    assert isinstance(body, dict)
    return cast(dict[str, object], body)


@pytest.fixture
async def test_user() -> AsyncGenerator[User, None]:
    """Create test user in DB for FK constraints.

    Creates user with id=TEST_USER_ID and cleans up after test.
    """
    async_session_local = _get_async_session_local()

    async with async_session_local() as session:
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
    async with async_session_local() as session:
        try:
            await session.execute(delete(DayPlan).where(DayPlan.user_id == TEST_USER_ID))
            await session.execute(delete(WeeklyPlan).where(WeeklyPlan.user_id == TEST_USER_ID))
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
    import app.main

    # Ensure override is attached to canonical app.main:app used by get_client().
    app_instance = app.main.app
    app_instance.dependency_overrides[require_pro_tier] = lambda: {"user_id": TEST_USER_ID}
    try:
        with get_client() as client:
            yield client
    finally:
        # Cleanup: remove override after test
        app_instance.dependency_overrides.pop(require_pro_tier, None)


@pytest.mark.asyncio
async def test_fetch_day_plan_when_exists_in_db(
    client_with_pro_access: TestClient,
    test_user: User,
) -> None:
    """When day plan exists in DB, endpoint returns items without warnings."""
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

    async_session_local = _get_async_session_local()

    async with async_session_local() as session:
        # Create weekly plan first (required for day_plan.weekly_plan_id)
        weekly_plan = WeeklyPlan(
            user_id=test_user.id,
            start_date=test_date,
            end_date=test_date,
            plan_data={},
        )
        session.add(weekly_plan)
        await session.flush()  # Get weekly_plan.id

        day_plan = DayPlan(
            user_id=test_user.id,
            weekly_plan_id=weekly_plan.id,
            date=test_date,
            plan_data=plan_data,
        )
        session.add(day_plan)
        await session.commit()

    response = client_with_pro_access.get(
        f"/api/v1/pro/shoplist/day?date={test_date}&lang=en",
    )

    assert response.status_code == 200
    body = _assert_json_response(response)
    assert body["warnings"] == []
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_fetch_day_plan_when_not_in_db(
    client_with_pro_access: TestClient, test_user: User
) -> None:
    """When no plan in DB, fetch_day_plan returns None → empty items + warning."""
    _ = test_user  # Ensure user exists for FK constraint
    test_date = date(2025, 12, 25)

    r = client_with_pro_access.get(
        f"/api/v1/pro/shoplist/day?date={test_date}&lang=en",
    )
    assert r.status_code == 200
    body = _assert_json_response(r)

    # Should return empty items with warning
    assert body["items"] == []
    assert body["warnings"] == ["no_day_plan"]


@pytest.mark.asyncio
async def test_day_plan_model_creation(test_user: User) -> None:
    """Test creating DayPlan model instance."""
    async_session_local = _get_async_session_local()

    test_date = date(2025, 12, 19)

    async with async_session_local() as session:
        # Create weekly plan first (required for day_plan.weekly_plan_id)
        weekly_plan = WeeklyPlan(
            user_id=test_user.id,
            start_date=test_date,
            end_date=test_date,
            plan_data={},
        )
        session.add(weekly_plan)
        await session.flush()  # Get weekly_plan.id

        day_plan = DayPlan(
            user_id=test_user.id,
            weekly_plan_id=weekly_plan.id,
            date=test_date,
            plan_data={"daily_menus": []},
        )
        session.add(day_plan)
        await session.commit()

    # Query back in separate session
    async with async_session_local() as session:
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
    async_session_local = _get_async_session_local()

    test_date = date(2025, 12, 21)

    # Create first day plan
    async with async_session_local() as session:
        # Create weekly plan first (required for day_plan.weekly_plan_id)
        weekly_plan = WeeklyPlan(
            user_id=test_user.id,
            start_date=test_date,
            end_date=test_date,
            plan_data={},
        )
        session.add(weekly_plan)
        await session.flush()  # Get weekly_plan.id

        day_plan_1 = DayPlan(
            user_id=test_user.id,
            weekly_plan_id=weekly_plan.id,
            date=test_date,
            plan_data={"daily_menus": []},
        )
        session.add(day_plan_1)
        await session.commit()

    # Try to create duplicate — should fail
    async with async_session_local() as session:
        # Use same weekly_plan for the duplicate attempt
        stmt = select(WeeklyPlan).where(WeeklyPlan.user_id == test_user.id)
        result = await session.execute(stmt)
        existing_weekly_plan = result.scalars().first()
        assert existing_weekly_plan is not None

        day_plan_2 = DayPlan(
            user_id=test_user.id,
            weekly_plan_id=existing_weekly_plan.id,
            date=test_date,
            plan_data={"daily_menus": [{"meals": []}]},
        )
        session.add(day_plan_2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

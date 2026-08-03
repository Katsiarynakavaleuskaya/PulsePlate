"""Tests for day shopping list DB wiring (PR-3).

RU: Тесты для интеграции БД для дневного списка покупок.
EN: Tests for day shopping list database integration.
"""

import asyncio
from contextlib import contextmanager
from datetime import date
from typing import TYPE_CHECKING, Callable, Generator, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests import Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.middleware.api_tiers import require_pro_tier
from app.models import DayPlan, WeeklyPlan
import core.db as core_db
from core.models import User
from tests._client import open_test_client

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Test user ID used across all tests
TEST_USER_ID = 1


class _ClientBodyFailure(RuntimeError):
    """Sentinel raised while a managed fixture body owns the client."""


@contextmanager
def _open_pro_client(
    app_instance: FastAPI,
    override: Callable[..., object],
) -> Generator[TestClient, None, None]:
    """Temporarily install PRO access while preserving prior override ownership."""
    overrides_owner = app_instance.dependency_overrides
    overrides_snapshot = dict(overrides_owner)
    overrides_owner[require_pro_tier] = override
    try:
        with open_test_client(app_instance) as client:
            yield client
    finally:
        app_instance.dependency_overrides = overrides_owner
        overrides_owner.clear()
        overrides_owner.update(overrides_snapshot)


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


async def _create_test_user() -> User:
    """Create and return the deterministic user required by FK constraints."""
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

        return user


async def _delete_test_user() -> None:
    """Delete the deterministic user and every plan owned by the fixture."""
    async_session_local = _get_async_session_local()

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
def test_user() -> Generator[User, None, None]:
    """Create a test user and clean up its FK-owned rows without an async pytest plugin."""
    user = asyncio.run(_create_test_user())
    try:
        yield user
    finally:
        asyncio.run(_delete_test_user())


@pytest.fixture
def client_with_pro_access() -> Generator[TestClient, None, None]:
    """Create test client with PRO tier access bypassed.

    Returns pro_ctx with user_id for proper fetch_day_plan behavior.
    """
    import app.main

    # Ensure override is attached to the same app owned by the managed client.
    app_instance = app.main.app
    with _open_pro_client(app_instance, lambda: {"user_id": TEST_USER_ID}) as client:
        yield client


@pytest.mark.parametrize("body_fails", [False, True])
def test_pro_client_restores_preexisting_override(body_fails: bool) -> None:
    """Normal and exceptional client exit restore the exact prior override."""
    app_instance = FastAPI()

    async def original_override() -> str:
        return "original"

    async def fixture_override() -> dict[str, int]:
        return {"user_id": TEST_USER_ID}

    overrides_owner = app_instance.dependency_overrides
    overrides_owner[require_pro_tier] = original_override

    if body_fails:
        with pytest.raises(_ClientBodyFailure):
            with _open_pro_client(app_instance, fixture_override):
                assert overrides_owner[require_pro_tier] is fixture_override
                raise _ClientBodyFailure("fixture body failed")
    else:
        with _open_pro_client(app_instance, fixture_override):
            assert overrides_owner[require_pro_tier] is fixture_override

    assert app_instance.dependency_overrides is overrides_owner
    assert overrides_owner == {require_pro_tier: original_override}


def test_fetch_day_plan_when_exists_in_db(
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

    async def seed_day_plan() -> None:
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

    asyncio.run(seed_day_plan())

    response = client_with_pro_access.get(
        f"/api/v1/pro/shoplist/day?date={test_date}&lang=en",
    )

    assert response.status_code == 200
    body = _assert_json_response(response)
    assert body["warnings"] == []
    assert isinstance(body["items"], list)


def test_fetch_day_plan_when_not_in_db(client_with_pro_access: TestClient, test_user: User) -> None:
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


def test_day_plan_model_creation(test_user: User) -> None:
    """Test creating DayPlan model instance."""
    test_date = date(2025, 12, 19)

    async def create_and_fetch_day_plan() -> None:
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
                plan_data={"daily_menus": []},
            )
            session.add(day_plan)
            await session.commit()

        # Query back in separate session
        async with async_session_local() as session:
            stmt = (
                select(DayPlan)
                .where(DayPlan.user_id == test_user.id)
                .where(DayPlan.date == test_date)
            )
            result = await session.execute(stmt)
            fetched = result.scalars().first()

            assert fetched is not None
            assert fetched.user_id == test_user.id
            assert fetched.date == test_date
            assert fetched.plan_data == {"daily_menus": []}

    asyncio.run(create_and_fetch_day_plan())


def test_day_plan_unique_user_date_constraint(test_user: User) -> None:
    """Test that (user_id, date) uniqueness is enforced."""
    test_date = date(2025, 12, 21)

    async def assert_unique_constraint() -> None:
        async_session_local = _get_async_session_local()

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

    asyncio.run(assert_unique_constraint())

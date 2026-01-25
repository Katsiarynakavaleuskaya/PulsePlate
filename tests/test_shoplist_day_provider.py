from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from types import SimpleNamespace
from typing import Any, AsyncContextManager, Callable, Generic, List, TypeVar

import pytest

import core.db as db
from app.core.shoplist_day import provider as provider_module

DayPlanT = TypeVar("DayPlanT")


class _FakeResult(Generic[DayPlanT]):
    """Fake SQLAlchemy result for testing."""

    def __init__(self, day_plan: DayPlanT) -> None:
        self._day_plan = day_plan

    def scalars(self) -> "_FakeResult[DayPlanT]":
        return self

    def first(self) -> DayPlanT:
        return self._day_plan


class _FakeSession(Generic[DayPlanT]):
    """Fake SQLAlchemy async session for testing."""

    def __init__(self, day_plan: DayPlanT) -> None:
        self._day_plan = day_plan
        self.statement: Any = None
        self.compiled_sql: str | None = None

    async def execute(self, stmt: Any) -> _FakeResult[DayPlanT]:
        self.statement = stmt
        # Compile SQL with literal binds for assertion
        self.compiled_sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        return _FakeResult(self._day_plan)


def _session_scope_factory(
    day_plan: DayPlanT,
    holder: List[_FakeSession[DayPlanT]],
) -> Callable[[], AsyncContextManager[_FakeSession[DayPlanT]]]:
    """Create a fake session scope factory for testing."""

    @asynccontextmanager
    async def _scope() -> AsyncIterator[_FakeSession[DayPlanT]]:
        session = _FakeSession(day_plan)
        holder.append(session)
        yield session

    return _scope


@pytest.mark.asyncio
async def test_fetch_day_plan_returns_none_without_user_id_dict() -> None:
    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 1),
        pro_ctx={"role": "pro"},
    )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_day_plan_returns_none_without_user_id_object() -> None:
    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 2),
        pro_ctx=SimpleNamespace(user_id=None),
    )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_day_plan_returns_none_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test fetch_day_plan returns None when no plan exists."""
    holder: list[_FakeSession] = []
    # Mock session_scope_async to return fake session (doesn't raise RuntimeError/ImportError)
    monkeypatch.setattr(db, "session_scope_async", _session_scope_factory(None, holder))

    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 3),
        pro_ctx=SimpleNamespace(user_id=10),
    )

    assert result is None
    assert holder and holder[0].statement is not None
    # Verify SQL query includes correct filters
    sql = holder[0].compiled_sql
    assert sql is not None
    assert "user_id" in sql
    assert "10" in sql  # user_id value
    assert "date" in sql


@pytest.mark.asyncio
async def test_fetch_day_plan_returns_plan_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch_day_plan returns plan_data when plan exists."""
    plan_data = {"daily_menus": [{"meals": []}]}
    day_plan = SimpleNamespace(plan_data=plan_data)
    holder: list[_FakeSession] = []
    # Mock session_scope_async to return fake session (doesn't raise RuntimeError/ImportError)
    monkeypatch.setattr(db, "session_scope_async", _session_scope_factory(day_plan, holder))

    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 4),
        pro_ctx=SimpleNamespace(user_id=42),
    )

    assert result == plan_data
    assert holder and holder[0].statement is not None
    # Verify SQL query includes correct filters
    sql = holder[0].compiled_sql
    assert sql is not None
    assert "user_id" in sql
    assert "42" in sql  # user_id value
    assert "2025-01-04" in sql  # date value


@pytest.mark.asyncio
async def test_fetch_day_plan_returns_none_on_async_db_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Async DB is optional: RuntimeError/ImportError should fail-soft to None."""

    def _raise_runtime_error():
        raise RuntimeError("Async SQLAlchemy is not configured")

    monkeypatch.setattr(db, "session_scope_async", _raise_runtime_error)

    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 5),
        pro_ctx=SimpleNamespace(user_id=7),
    )

    assert result is None


@pytest.mark.asyncio
async def test_fetch_day_plan_returns_none_on_async_db_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Async DB is optional: RuntimeError/ImportError should fail-soft to None."""

    def _raise_import_error():
        raise ImportError("sqlalchemy.asyncio is not available")

    monkeypatch.setattr(db, "session_scope_async", _raise_import_error)

    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 6),
        pro_ctx=SimpleNamespace(user_id=8),
    )

    assert result is None

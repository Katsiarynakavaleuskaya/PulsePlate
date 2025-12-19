from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from types import SimpleNamespace

import pytest

from app.core.shoplist_day import provider as provider_module
import core.db as db


class _FakeResult:
    def __init__(self, day_plan):
        self._day_plan = day_plan

    def scalars(self):
        return self

    def first(self):
        return self._day_plan


class _FakeSession:
    def __init__(self, day_plan):
        self._day_plan = day_plan
        self.statement = None

    async def execute(self, stmt):
        self.statement = stmt
        return _FakeResult(self._day_plan)


def _session_scope_factory(day_plan, holder):
    @asynccontextmanager
    async def _scope():
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
async def test_fetch_day_plan_returns_none_when_missing(monkeypatch) -> None:
    holder = []
    monkeypatch.setattr(db, "session_scope_async", _session_scope_factory(None, holder))

    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 3),
        pro_ctx=SimpleNamespace(user_id=10),
    )

    assert result is None
    assert holder and holder[0].statement is not None


@pytest.mark.asyncio
async def test_fetch_day_plan_returns_plan_data(monkeypatch) -> None:
    plan_data = {"daily_menus": [{"meals": []}]}
    day_plan = SimpleNamespace(plan_data=plan_data)
    holder = []
    monkeypatch.setattr(db, "session_scope_async", _session_scope_factory(day_plan, holder))

    result = await provider_module.fetch_day_plan(
        day=date(2025, 1, 4),
        pro_ctx=SimpleNamespace(user_id=42),
    )

    assert result == plan_data
    assert holder and holder[0].statement is not None

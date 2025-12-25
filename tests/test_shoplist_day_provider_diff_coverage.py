from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any, AsyncIterator

import pytest


@pytest.mark.asyncio
async def test_fetch_day_plan_imports_models_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diff-coverage: execute lazy imports in app.core.shoplist_day.provider.fetch_day_plan."""
    from app.core.shoplist_day.provider import fetch_day_plan

    class _Result:
        def scalars(self) -> "_Result":
            return self

        def first(self) -> Any:
            return None

    class _Session:
        async def execute(self, _stmt: Any) -> _Result:
            return _Result()

    @asynccontextmanager
    async def _fake_scope() -> AsyncIterator[_Session]:
        yield _Session()

    # Ensure the imported session_scope_async is our fake, so no real DB is touched.
    import core.db as core_db

    monkeypatch.setattr(core_db, "session_scope_async", _fake_scope)

    res = await fetch_day_plan(date(2025, 12, 25), {"user_id": 1})
    assert res is None

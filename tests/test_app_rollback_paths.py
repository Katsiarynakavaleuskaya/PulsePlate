"""
Targeted tests for app.py rollback_database endpoint error paths.

Covers:
- Scheduler failure scenarios
- Missing update manager
- Missing rollback function
- Rollback execution failures
"""

import asyncio

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock

from app.services import admin_operations


def test_rollback_scheduler_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_get_update_scheduler = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(
        admin_operations,
        "get_update_scheduler",
        mock_get_update_scheduler,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_operations.rollback_database("usda", "v1"))

    mock_get_update_scheduler.assert_awaited_once()
    assert exc.value.status_code == 500
    assert "could not get scheduler" in exc.value.detail


def test_rollback_no_update_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyScheduler:
        update_manager = None

    mock_get_update_scheduler = AsyncMock(return_value=DummyScheduler())
    monkeypatch.setattr(
        admin_operations,
        "get_update_scheduler",
        mock_get_update_scheduler,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_operations.rollback_database("usda", "v1"))

    mock_get_update_scheduler.assert_awaited_once()
    assert exc.value.status_code == 500
    assert "No update manager available" in exc.value.detail


def test_rollback_no_rollback_fn(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyManager:
        pass

    class DummyScheduler:
        update_manager = DummyManager()

    mock_get_update_scheduler = AsyncMock(return_value=DummyScheduler())
    monkeypatch.setattr(
        admin_operations,
        "get_update_scheduler",
        mock_get_update_scheduler,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_operations.rollback_database("usda", "v1"))

    mock_get_update_scheduler.assert_awaited_once()
    assert exc.value.status_code == 500
    assert "Rollback operation not supported" in exc.value.detail


def test_rollback_raises_inside_method(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyManager:
        async def rollback_database(self, source: str, target_version: str) -> None:
            raise RuntimeError("boom")

    class DummyScheduler:
        update_manager = DummyManager()

    mock_get_update_scheduler = AsyncMock(return_value=DummyScheduler())
    monkeypatch.setattr(
        admin_operations,
        "get_update_scheduler",
        mock_get_update_scheduler,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_operations.rollback_database("usda", "v1"))

    mock_get_update_scheduler.assert_awaited_once()
    assert exc.value.status_code == 500
    assert "Rollback operation failed" in exc.value.detail

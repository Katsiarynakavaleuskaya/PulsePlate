"""
Targeted tests for app.py rollback_database endpoint error paths.

Covers:
- Scheduler failure scenarios
- Missing update manager
- Missing rollback function
- Rollback execution failures
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock

from app.services import admin_operations
from tests.helpers.fast_update_stubs import add_persisted_version_store_stub


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


def test_rollback_raises_inside_method(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Preserve the endpoint error contract when the rollback callable raises."""

    rollback_database = AsyncMock(side_effect=RuntimeError("boom"))

    class DummyScheduler:
        update_manager = add_persisted_version_store_stub(
            SimpleNamespace(rollback_database=rollback_database),
            tmp_path,
        )

    mock_get_update_scheduler = AsyncMock(return_value=DummyScheduler())
    monkeypatch.setattr(
        admin_operations,
        "get_update_scheduler",
        mock_get_update_scheduler,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_operations.rollback_database("usda", "v1"))

    mock_get_update_scheduler.assert_awaited_once()
    rollback_database.assert_awaited_once_with("usda", "v1")
    assert exc.value.status_code == 500
    assert "Rollback operation failed" in exc.value.detail

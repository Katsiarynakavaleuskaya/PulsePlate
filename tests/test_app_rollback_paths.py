import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

import app as app_mod


@pytest.mark.asyncio
@patch("app.get_update_scheduler", new_callable=AsyncMock)
async def test_rollback_scheduler_failure(mock_get_update_scheduler: AsyncMock) -> None:
    mock_get_update_scheduler.side_effect = RuntimeError("boom")

    with pytest.raises(HTTPException) as exc:
        await app_mod.rollback_database("usda", "v1")
    mock_get_update_scheduler.assert_called_once()
    assert exc.value.status_code == 500
    assert "could not get scheduler" in exc.value.detail


@pytest.mark.asyncio
@patch("app.get_update_scheduler", new_callable=AsyncMock)
async def test_rollback_no_update_manager(mock_get_update_scheduler: AsyncMock) -> None:
    class DummyScheduler:
        update_manager = None

    mock_get_update_scheduler.return_value = DummyScheduler()
    with pytest.raises(HTTPException) as exc:
        await app_mod.rollback_database("usda", "v1")
    mock_get_update_scheduler.assert_called_once()
    assert exc.value.status_code == 500
    assert "No update manager available" in exc.value.detail


@pytest.mark.asyncio
@patch("app.get_update_scheduler", new_callable=AsyncMock)
async def test_rollback_no_rollback_fn(mock_get_update_scheduler: AsyncMock) -> None:
    class DummyManager:
        pass

    class DummyScheduler:
        update_manager = DummyManager()

    mock_get_update_scheduler.return_value = DummyScheduler()
    with pytest.raises(HTTPException) as exc:
        await app_mod.rollback_database("usda", "v1")
    mock_get_update_scheduler.assert_called_once()
    assert exc.value.status_code == 500
    assert "Rollback operation not supported" in exc.value.detail


@pytest.mark.asyncio
@patch("app.get_update_scheduler", new_callable=AsyncMock)
async def test_rollback_raises_inside_method(mock_get_update_scheduler: AsyncMock) -> None:
    class DummyManager:
        async def rollback_database(self, source: str, target_version: str) -> None:
            raise RuntimeError("boom")

    class DummyScheduler:
        update_manager = DummyManager()

    mock_get_update_scheduler.return_value = DummyScheduler()
    with pytest.raises(HTTPException) as exc:
        await app_mod.rollback_database("usda", "v1")
    mock_get_update_scheduler.assert_called_once()
    assert exc.value.status_code == 500
    assert "Rollback operation failed" in exc.value.detail

import asyncio
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.mark.asyncio
async def test_lifespan_forced_background_updates_awaitable_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover legacy_app.lifespan background-start awaitable branch."""
    from app import lifespan

    async def _start_coro(update_interval_hours: int) -> None:
        assert update_interval_hours == 24

    async def _stop_coro() -> None:
        return None

    start_mock = Mock(
        side_effect=lambda update_interval_hours=24: _start_coro(update_interval_hours)
    )
    stop_mock = Mock(side_effect=_stop_coro)

    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.delenv("DISABLE_BACKGROUND_UPDATES", raising=False)
    monkeypatch.delenv("BACKGROUND_START_TIMEOUT_SEC", raising=False)

    with (
        patch("legacy_app.init_db", return_value=None),
        patch("legacy_app.validate_template_dir", return_value=None),
        patch("legacy_app.start_background_updates", new=start_mock),
        patch("legacy_app.stop_background_updates", new=stop_mock),
        patch("app.start_background_updates", new=start_mock, create=True),
        patch("app.stop_background_updates", new=stop_mock, create=True),
    ):
        async with lifespan(MagicMock()):
            pass

    start_mock.assert_called_once_with(update_interval_hours=24)
    stop_mock.assert_called_once_with()


@pytest.mark.asyncio
async def test_lifespan_background_updates_start_timeout_cancels_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover legacy_app.lifespan timeout handling when background start hangs."""
    from app import lifespan

    event = asyncio.Event()

    async def _never_finishes() -> None:
        await event.wait()

    start_mock = Mock(side_effect=lambda update_interval_hours=24: _never_finishes())
    stop_mock = Mock(return_value=None)

    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.setenv("BACKGROUND_START_TIMEOUT_SEC", "0.001")

    with (
        patch("legacy_app.init_db", return_value=None),
        patch("legacy_app.validate_template_dir", return_value=None),
        patch("legacy_app.start_background_updates", new=start_mock),
        patch("legacy_app.stop_background_updates", new=stop_mock),
        patch("app.start_background_updates", new=start_mock, create=True),
        patch("app.stop_background_updates", new=stop_mock, create=True),
    ):
        async with lifespan(MagicMock()):
            pass

    start_mock.assert_called_once_with(update_interval_hours=24)
    stop_mock.assert_called_once_with()


@pytest.mark.asyncio
async def test_lifespan_background_updates_start_exception_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover legacy_app.lifespan exception handling when background start fails."""
    from app import lifespan

    async def _raise() -> None:
        raise RuntimeError("boom")

    start_mock = Mock(side_effect=lambda update_interval_hours=24: _raise())
    stop_mock = Mock(return_value=None)

    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.delenv("BACKGROUND_START_TIMEOUT_SEC", raising=False)

    with (
        patch("legacy_app.init_db", return_value=None),
        patch("legacy_app.validate_template_dir", return_value=None),
        patch("legacy_app.start_background_updates", new=start_mock),
        patch("legacy_app.stop_background_updates", new=stop_mock),
        patch("app.start_background_updates", new=start_mock, create=True),
        patch("app.stop_background_updates", new=stop_mock, create=True),
    ):
        async with lifespan(MagicMock()):
            pass

    start_mock.assert_called_once_with(update_interval_hours=24)
    stop_mock.assert_called_once_with()

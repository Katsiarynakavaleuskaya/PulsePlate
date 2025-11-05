from __future__ import annotations

import asyncio

import pytest

import app
import app.dependencies as app_dependencies


@pytest.mark.asyncio
async def test_lifespan_validate_template_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", lambda: None)

    def raise_runtime():
        raise RuntimeError("missing templates")

    monkeypatch.setitem(lifespan_globals, "validate_template_dir", raise_runtime)

    with pytest.raises(RuntimeError):
        async with app.lifespan(app.app):
            pass


@pytest.mark.asyncio
async def test_lifespan_validate_template_generic_error(monkeypatch: pytest.MonkeyPatch) -> None:
    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", lambda: None)

    def raise_value():
        raise ValueError("bad template state")

    monkeypatch.setitem(lifespan_globals, "validate_template_dir", raise_value)

    with pytest.raises(ValueError):
        async with app.lifespan(app.app):
            pass


@pytest.mark.asyncio
async def test_lifespan_background_update_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", lambda: None)
    monkeypatch.setitem(lifespan_globals, "validate_template_dir", lambda: None)

    async def failing_start(*args, **kwargs):
        raise RuntimeError("failure")

    async def noop_stop():
        return None

    monkeypatch.setitem(lifespan_globals, "start_background_updates", failing_start)
    monkeypatch.setitem(lifespan_globals, "stop_background_updates", noop_stop)

    # Ensure module attribute on sys.modules["app"] matches
    import sys

    sys.modules.get("app").start_background_updates = failing_start  # type: ignore[attr-defined]
    sys.modules.get("app").stop_background_updates = noop_stop  # type: ignore[attr-defined]
    if "app_module" in sys.modules:
        sys.modules["app_module"].start_background_updates = failing_start  # type: ignore[attr-defined]
        sys.modules["app_module"].stop_background_updates = noop_stop  # type: ignore[attr-defined]

    # Should suppress the failing start call and still enter context
    async with app.lifespan(app.app):
        pass

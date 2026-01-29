from __future__ import annotations

import pytest

import app


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

    # Ensure module attribute on sys.modules["app"] matches using safe monkeypatching
    import sys

    app_mod = sys.modules.get("app")
    if app_mod is not None:
        monkeypatch.setattr(app_mod, "start_background_updates", failing_start, raising=False)
        monkeypatch.setattr(app_mod, "stop_background_updates", noop_stop, raising=False)
    app_module_mod = sys.modules.get("app_module")
    if app_module_mod is not None:
        monkeypatch.setattr(
            app_module_mod, "start_background_updates", failing_start, raising=False
        )
        monkeypatch.setattr(app_module_mod, "stop_background_updates", noop_stop, raising=False)

    # Should suppress the failing start call and still enter context
    async with app.lifespan(app.app):
        pass


@pytest.mark.asyncio
async def test_lifespan_init_db_raises_calls_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover legacy_app lifespan except path (lines 458–459): init_db raises -> _attempt_db_fallback."""
    from unittest.mock import patch

    def init_db_raises() -> None:
        raise OSError("DB unreachable")

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", init_db_raises)

    with patch("core.db_fallback._attempt_db_fallback", side_effect=OSError("DB unreachable")):
        with pytest.raises(OSError, match="DB unreachable"):
            async with app.lifespan(app.app):
                pass

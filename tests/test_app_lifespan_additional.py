from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

import app
from app.bootstrap import startup_guards as bootstrap_guards
from tests.helpers.fast_update_stubs import patch_background_update_callables


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
    import legacy_app

    failing_start = AsyncMock(side_effect=RuntimeError("failure"))
    noop_stop = AsyncMock(return_value=None)

    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.delenv("DISABLE_BACKGROUND_UPDATES", raising=False)

    patch_background_update_callables(monkeypatch, start=failing_start, stop=noop_stop)

    with (
        patch.object(legacy_app, "init_db", return_value=None),
        patch.object(legacy_app, "validate_template_dir", return_value=None),
    ):
        # Should suppress the failing start call and still enter context
        async with app.lifespan(app.app):
            pass

    failing_start.assert_awaited_once_with(update_interval_hours=24)


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


@pytest.mark.asyncio
async def test_lifespan_rejects_anonymous_api_toggle_in_env_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Startup должен падать на anonymous toggle в prod-like ENVIRONMENT.

    EN: Startup must fail closed when anonymous API-key toggle is enabled in prod-like ENVIRONMENT.
    """

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(RuntimeError, match="ALLOW_ANONYMOUS_API_KEYS"):
        async with app.lifespan(app.app):
            pass


@pytest.mark.asyncio
async def test_lifespan_rejects_dev_api_toggle_in_env_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Startup должен падать на dev API toggle в staging.

    EN: Startup must fail closed when ALLOW_DEV_API_KEY is enabled in staging.
    """

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")
    monkeypatch.setenv("DEBUG", "false")

    with pytest.raises(RuntimeError, match="ALLOW_DEV_API_KEY"):
        async with app.lifespan(app.app):
            pass


@pytest.mark.asyncio
async def test_lifespan_requires_apple_shared_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Startup должен падать без Apple shared secret.

    EN: Startup must fail closed when Apple receipt verification secret is missing.
    """

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="APPLE_SHARED_SECRET"):
        async with app.lifespan(app.app):
            pass


@pytest.mark.asyncio
async def test_lifespan_requires_valid_pro_llm_monthly_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Startup должен падать при невалидной PRO LLM квоте.

    EN: Startup must fail closed when the PRO LLM quota env is invalid.
    """

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
    monkeypatch.setenv("APPLE_SHARED_SECRET", "apple-shared-secret-for-tests")
    monkeypatch.setenv("SERVER_SALT", "StrongServerSaltForTests123456789!")
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "invalid")

    with pytest.raises(RuntimeError, match="PRO_LLM_INSIGHT_REQUESTS_PER_MONTH"):
        async with app.lifespan(app.app):
            pass


@pytest.mark.asyncio
async def test_lifespan_accepts_valid_pro_llm_monthly_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Startup должен проходить с валидной PRO LLM квотой.

    EN: Startup should succeed when the PRO LLM quota env is valid.
    """

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
    monkeypatch.setenv("APPLE_SHARED_SECRET", "apple-shared-secret-for-tests")
    monkeypatch.setenv("SERVER_SALT", "StrongServerSaltForTests123456789!")
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")

    async with app.lifespan(app.app):
        pass


@pytest.mark.asyncio
async def test_lifespan_allows_missing_apple_shared_secret_in_test_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)

    async with app.lifespan(app.app):
        pass

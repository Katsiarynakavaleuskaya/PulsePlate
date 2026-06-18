from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

import app
import core.db as core_db
from app.bootstrap import startup_guards as bootstrap_guards
from app.security import rate_limit
from tests.helpers.fast_update_stubs import patch_background_update_callables


def _reset_core_db_state() -> None:
    """Reset shared DB module state before and after env-driven tests."""

    core_db.reset_db_for_tests()


def _run_lifespan_once() -> None:
    """Enter the app lifespan once without requiring a pytest async plugin."""

    async def _runner() -> None:
        async with app.lifespan(app.app):
            pass

    asyncio.run(_runner())


def test_lifespan_validate_template_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", lambda: None)

    def raise_runtime():
        raise RuntimeError("missing templates")

    monkeypatch.setitem(lifespan_globals, "validate_template_dir", raise_runtime)

    with pytest.raises(RuntimeError):
        _run_lifespan_once()


def test_lifespan_validate_template_generic_error(monkeypatch: pytest.MonkeyPatch) -> None:
    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", lambda: None)

    def raise_value():
        raise ValueError("bad template state")

    monkeypatch.setitem(lifespan_globals, "validate_template_dir", raise_value)

    with pytest.raises(ValueError):
        _run_lifespan_once()


def test_lifespan_background_update_failure(monkeypatch: pytest.MonkeyPatch) -> None:
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
        _run_lifespan_once()

    failing_start.assert_awaited_once_with(update_interval_hours=24)


def test_lifespan_init_db_raises_calls_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover legacy_app lifespan except path (lines 458–459): init_db raises -> _attempt_db_fallback."""
    from unittest.mock import patch

    def init_db_raises() -> None:
        raise OSError("DB unreachable")

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", init_db_raises)

    with patch("core.db_fallback._attempt_db_fallback", side_effect=OSError("DB unreachable")):
        with pytest.raises(OSError, match="DB unreachable"):
            _run_lifespan_once()


def test_lifespan_rejects_anonymous_api_toggle_in_env_production(
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
        _run_lifespan_once()


def test_lifespan_rejects_dev_api_toggle_in_env_staging(
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
        _run_lifespan_once()


def test_lifespan_requires_apple_shared_secret(
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
        _run_lifespan_once()


def test_lifespan_requires_valid_pro_llm_monthly_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Startup должен падать при невалидной PRO LLM квоте.

    EN: Startup must fail closed when the PRO LLM quota env is invalid.
    """

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET", "apple-shared-secret-for-tests"
    )  # pragma: allowlist secret
    monkeypatch.setenv(
        "SERVER_SALT", "StrongServerSaltForTests123456789!"
    )  # pragma: allowlist secret
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "invalid")

    with pytest.raises(RuntimeError, match="PRO_LLM_INSIGHT_REQUESTS_PER_MONTH"):
        _run_lifespan_once()


def test_lifespan_accepts_valid_pro_llm_monthly_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RU: Startup должен проходить с валидной PRO LLM квотой.

    EN: Startup should succeed when the PRO LLM quota env is valid.
    """

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "init_db", lambda: None)
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("APPLE_SHARED_SECRET", "apple-shared-secret-for-tests")
    monkeypatch.setenv("SERVER_SALT", "StrongServerSaltForTests123456789!")
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
    monkeypatch.setenv("PRIVATE_EXPORTS_ENABLED", "true")
    monkeypatch.setenv(
        "EXPORT_TOKEN_SECRET", "export-token-secret-for-tests"
    )  # pragma: allowlist secret
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db/pulseplate")
    monkeypatch.setattr(
        rate_limit,
        "_is_rate_limiting_wired_for_app",
        lambda target_app: target_app is app.app,
    )
    monkeypatch.setattr(rate_limit, "_rate_limiting_enabled", lambda: True)
    if rate_limit.limiter is not None:
        rate_limit.limiter.enabled = True

    _run_lifespan_once()


@pytest.mark.parametrize("runtime_env", ["production", "staging"])
def test_lifespan_requires_subscription_db_enabled_in_production_like_env(
    monkeypatch: pytest.MonkeyPatch,
    runtime_env: str,
) -> None:
    """Paid-route entitlement mode must fail closed without DB truth in prod/staging."""

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", runtime_env)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
    monkeypatch.setenv("APPLE_SHARED_SECRET", "apple-shared-secret-for-tests")
    monkeypatch.setenv("SERVER_SALT", "StrongServerSaltForTests123456789!")
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")

    with pytest.raises(RuntimeError, match="SUBSCRIPTION_DB_ENABLED"):
        _run_lifespan_once()


@pytest.mark.parametrize("runtime_env", ["production", "staging", "prod", "live"])
def test_lifespan_requires_database_url_in_production_like_env(
    monkeypatch: pytest.MonkeyPatch,
    runtime_env: str,
) -> None:
    """Production-like startup must fail closed when DATABASE_URL is missing."""

    _reset_core_db_state()
    try:
        lifespan_globals = app.lifespan.__wrapped__.__globals__
        monkeypatch.setitem(
            lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards
        )
        monkeypatch.setenv("ENVIRONMENT", runtime_env)
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("TESTING", "false")
        monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
        monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
        monkeypatch.setenv("API_KEY_REQUIRED", "true")
        monkeypatch.setenv("APPLE_SHARED_SECRET", "apple-shared-secret-for-tests")
        monkeypatch.setenv("SERVER_SALT", "StrongServerSaltForTests123456789!")
        monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
        monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
        monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
        monkeypatch.setenv("PRIVATE_EXPORTS_ENABLED", "true")
        monkeypatch.setenv("EXPORT_TOKEN_SECRET", "export-token-secret-for-tests")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("DB_FALLBACK_URL", raising=False)

        with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
            _run_lifespan_once()
    finally:
        _reset_core_db_state()


def test_build_engine_url_requires_database_url_in_prod_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ENVIRONMENT=prod without DATABASE_URL must fail closed."""

    from core.db import _build_engine_url

    _reset_core_db_state()
    try:
        monkeypatch.setenv("ENVIRONMENT", "prod")
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
            _build_engine_url()
    finally:
        _reset_core_db_state()


def test_build_engine_url_requires_database_url_when_app_env_is_production_like(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production-like APP_ENV without ENVIRONMENT set must still fail closed."""

    from core.db import _build_engine_url

    _reset_core_db_state()
    try:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
            _build_engine_url()
    finally:
        _reset_core_db_state()


def test_build_engine_url_treats_whitespace_database_url_as_missing_in_production_like_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace DATABASE_URL is treated as missing in production-like envs."""

    from core.db import _build_engine_url

    _reset_core_db_state()
    try:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("DATABASE_URL", "   \n\t")

        with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
            _build_engine_url()
    finally:
        _reset_core_db_state()


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///./cache/app.db",
        "sqlite+pysqlite:///./cache/app.db",
        "sqlite+aiosqlite:///./cache/app.db",
        "SQLITE:///./cache/app.db",
    ],
)
def test_build_engine_url_rejects_sqlite_database_url_in_production_like_env(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    """Production-like environments must reject SQLite DATABASE_URL variants."""

    from core.db import _build_engine_url

    _reset_core_db_state()
    try:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("DATABASE_URL", database_url)

        with pytest.raises(RuntimeError, match="SQLite DATABASE_URL is not allowed"):
            _build_engine_url()
    finally:
        _reset_core_db_state()


def test_is_sqlite_database_url_falls_back_to_scheme_check_when_make_url_fails() -> None:
    """Fallback scheme parsing must still reject dialect-qualified SQLite URLs."""

    with patch.object(core_db, "make_url", side_effect=ValueError("invalid url")):
        assert core_db._is_sqlite_database_url("SQLITE+Pysqlite:///./cache/app.db") is True


@pytest.mark.parametrize("runtime_env", ["local", "dev", "development", "test", "testing", "ci"])
def test_lifespan_allows_subscription_db_disabled_outside_production_like_env(
    monkeypatch: pytest.MonkeyPatch,
    runtime_env: str,
) -> None:
    """Local/dev/test-like environments keep non-fatal startup for DB-backed entitlement mode."""

    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", runtime_env)
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
    monkeypatch.setenv("SERVER_SALT", "StrongServerSaltForTests123456789!")
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)

    _run_lifespan_once()


def test_lifespan_allows_missing_apple_shared_secret_in_test_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifespan_globals = app.lifespan.__wrapped__.__globals__
    monkeypatch.setitem(lifespan_globals, "run_startup_guards", bootstrap_guards.run_startup_guards)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.delenv("APPLE_SHARED_SECRET", raising=False)

    _run_lifespan_once()

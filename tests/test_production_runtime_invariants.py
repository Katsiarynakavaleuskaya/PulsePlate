"""Tests for production/staging runtime invariant guards."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.bootstrap import startup_guards
from app.security import production_invariants, rate_limit, web_session
from scripts.ci.check_production_runtime_invariants import (
    _UNSAFE_FALSE_FLAG_OVERRIDES,
    _UNSAFE_TRUE_FLAG_OVERRIDES,
    run_synthetic_production_checks,
)
from settings import is_explicit_developer_env, is_raw_explicit_developer_env


class _FakeLimiter:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled


def _set_safe_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "false")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "true")
    monkeypatch.setenv(
        "SERVER_SALT", "StrongServerSaltForTests123456789!"
    )  # pragma: allowlist secret
    monkeypatch.setenv(
        "APPLE_SHARED_SECRET", "apple-shared-secret-for-tests"
    )  # pragma: allowlist secret
    monkeypatch.setenv("PRIVATE_EXPORTS_ENABLED", "true")
    monkeypatch.setenv(
        "EXPORT_TOKEN_SECRET", "export-token-secret-for-tests"
    )  # pragma: allowlist secret
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db/pulseplate")
    monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("VIP_LLM_INSIGHT_REQUESTS_PER_MONTH", "50")
    monkeypatch.setenv("ENABLE_TEST_ROUTES", "0")
    monkeypatch.setenv("ENABLE_DEBUG_ENDPOINT", "false")
    monkeypatch.setenv("METRICS_TEST_BYPASS", "false")


def _set_rate_limit_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limit, "limiter", _FakeLimiter())
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", object())
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", object())
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", {1})


def _set_runtime_env_label(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str | None,
) -> None:
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def test_raw_explicit_developer_env_does_not_use_default_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert is_explicit_developer_env() is True
    assert is_raw_explicit_developer_env() is False


@pytest.mark.parametrize(
    ("app_env", "runtime_env", "expected"),
    [
        (None, None, False),
        ("", "", False),
        (" local ", None, True),
        (None, "CI", True),
        ("dev", "testing", True),
        ("preview", None, False),
        (None, "preview", False),
        ("local", "preview", False),
        ("preview", "local", False),
        ("production", "local", False),
        ("local", "production", False),
    ],
)
def test_raw_explicit_developer_env_is_fail_closed_for_unknown_and_conflicting_labels(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str | None,
    runtime_env: str | None,
    expected: bool,
) -> None:
    _set_runtime_env_label(monkeypatch, "APP_ENV", app_env)
    _set_runtime_env_label(monkeypatch, "ENVIRONMENT", runtime_env)

    assert is_raw_explicit_developer_env() is expected


def test_web_session_does_not_own_duplicate_developer_env_allowlist() -> None:
    source = Path("app/security/web_session.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    assigned_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assigned_names.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned_names.add(node.target.id)

    assert "_DEVELOPER_COOKIE_ENVS" not in assigned_names


@pytest.mark.parametrize(
    ("app_env", "runtime_env"),
    [
        (None, None),
        ("preview", None),
        (None, "preview"),
        ("local", "preview"),
        ("preview", "local"),
        ("production", "local"),
        ("local", "production"),
        ("staging", None),
    ],
)
def test_web_session_cookie_secure_policy_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str | None,
    runtime_env: str | None,
) -> None:
    _set_runtime_env_label(monkeypatch, "APP_ENV", app_env)
    _set_runtime_env_label(monkeypatch, "ENVIRONMENT", runtime_env)
    monkeypatch.setenv("DEBUG", "false")

    assert web_session._is_secure_cookie_environment() is True


def test_production_runtime_invariants_accept_safe_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    _set_rate_limit_ready(monkeypatch)

    production_invariants.assert_production_runtime_invariants()


@pytest.mark.parametrize(
    ("env_name", "env_value", "message"),
    [
        ("DEBUG", "true", "DEBUG"),
        ("TESTING", "true", "TESTING"),
        ("ALLOW_DEV_API_KEY", "true", "ALLOW_DEV_API_KEY"),
        ("ALLOW_ANONYMOUS_API_KEYS", "true", "ALLOW_ANONYMOUS_API_KEYS"),
        ("API_KEY_REQUIRED", "false", "API_KEY_REQUIRED"),
        ("SUBSCRIPTION_DB_ENABLED", "false", "SUBSCRIPTION_DB_ENABLED"),
        ("ENABLE_TEST_ROUTES", "1", "ENABLE_TEST_ROUTES"),
        ("ENABLE_DEBUG_ENDPOINT", "true", "ENABLE_DEBUG_ENDPOINT"),
        ("METRICS_TEST_BYPASS", "true", "METRICS_TEST_BYPASS"),
    ],
)
def test_production_runtime_invariants_reject_unsafe_flags(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
    message: str,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(RuntimeError, match=message):
        production_invariants.assert_production_runtime_invariants()


def test_production_runtime_invariants_reject_disabled_private_exports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setenv("PRIVATE_EXPORTS_ENABLED", "false")

    with pytest.raises(RuntimeError, match="PRIVATE_EXPORTS_ENABLED"):
        production_invariants.assert_production_runtime_invariants()


def test_production_runtime_invariants_reject_export_secret_placeholder_for_unknown_prod_like_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    _set_rate_limit_ready(monkeypatch)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "live")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("EXPORT_TOKEN_SECRET", "__set_me__")

    with pytest.raises(RuntimeError, match="EXPORT_TOKEN_SECRET"):
        production_invariants.assert_production_runtime_invariants()


@pytest.mark.parametrize(
    ("database_url", "message"),
    [
        ("not-a-url", "valid PostgreSQL URL"),
        ("http://example.invalid/db", "PostgreSQL"),
        ("mysql://db/pulseplate", "PostgreSQL"),
        ("sqlite:///cache/app.db", "PostgreSQL"),
        ("sqlite+pysqlite:///cache/app.db", "PostgreSQL"),
        ("sqlite+aiosqlite:///cache/app.db", "PostgreSQL"),
    ],
)
def test_production_runtime_invariants_reject_non_postgres_database_url(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
    message: str,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match=message):
        production_invariants.assert_production_runtime_invariants()


def test_production_runtime_invariants_allow_explicit_local_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("SUBSCRIPTION_DB_ENABLED", "false")
    monkeypatch.delenv("SERVER_SALT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    production_invariants.assert_production_runtime_invariants()


def test_startup_guards_call_production_invariants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"value": False}

    monkeypatch.setattr(startup_guards, "require_server_salt", lambda: "salt")
    monkeypatch.setattr(startup_guards, "require_pro_llm_monthly_limit", lambda: 50)
    monkeypatch.setattr(startup_guards, "require_vip_llm_monthly_limit", lambda: 50)
    monkeypatch.setattr(startup_guards, "validate_apple_receipt_verification_config", lambda: None)
    monkeypatch.setattr(startup_guards, "validate_api_key_toggle_guard", lambda: None)
    monkeypatch.setattr(
        startup_guards,
        "_require_subscription_db_in_production_like_env",
        lambda: None,
    )

    def _record_call(*, app: object | None = None) -> None:
        called["value"] = app is sentinel_app

    monkeypatch.setattr(startup_guards, "assert_production_runtime_invariants", _record_call)

    sentinel_app = object()

    startup_guards.run_startup_guards(sentinel_app)

    assert called["value"] is True


def test_rate_limit_readiness_rejects_missing_limiter_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setattr(rate_limit, "limiter", None)

    with pytest.raises(RuntimeError, match="SlowAPI limiter"):
        rate_limit.require_rate_limiting_ready_for_production()


def test_rate_limit_readiness_rejects_testing_flag_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(rate_limit, "limiter", _FakeLimiter())
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", object())
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", object())

    with pytest.raises(RuntimeError, match="TESTING"):
        rate_limit.require_rate_limiting_ready_for_production()


def test_rate_limit_readiness_rejects_missing_exception_handler_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setattr(rate_limit, "limiter", _FakeLimiter())
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", None)
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", object())

    with pytest.raises(RuntimeError, match="SlowAPI middleware"):
        rate_limit.require_rate_limiting_ready_for_production()


def test_rate_limit_readiness_rejects_missing_middleware_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setattr(rate_limit, "limiter", _FakeLimiter())
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", object())
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", None)

    with pytest.raises(RuntimeError, match="SlowAPI middleware"):
        rate_limit.require_rate_limiting_ready_for_production()


def test_rate_limit_readiness_rejects_disabled_limiter_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setattr(rate_limit, "limiter", _FakeLimiter())
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", object())
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", object())
    monkeypatch.setattr(rate_limit, "_rate_limiting_enabled", lambda: False)
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", {1})

    with pytest.raises(RuntimeError, match="Rate limiting must be enabled"):
        rate_limit.require_rate_limiting_ready_for_production()


def test_rate_limit_readiness_does_not_mutate_limiter_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    fake_limiter = _FakeLimiter(enabled=False)
    monkeypatch.setattr(rate_limit, "limiter", fake_limiter)
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", object())
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", object())
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", {1})

    with pytest.raises(RuntimeError, match="Rate limiting must be enabled"):
        rate_limit.require_rate_limiting_ready_for_production()

    assert fake_limiter.enabled is False


def test_rate_limit_readiness_rejects_unwired_app_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_safe_production_env(monkeypatch)
    monkeypatch.setattr(rate_limit, "limiter", _FakeLimiter())
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", object())
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", object())
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()

    with pytest.raises(RuntimeError, match="wired into the FastAPI app"):
        rate_limit.require_rate_limiting_ready_for_production(app=app)


def test_wire_rate_limiting_attaches_app_limiter_handler_and_middleware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()

    rate_limit.wire_rate_limiting(app)

    assert app.state.limiter is rate_limit.limiter
    assert rate_limit.RateLimitExceeded in app.exception_handlers
    assert any(middleware.cls is rate_limit.SlowAPIMiddleware for middleware in app.user_middleware)
    assert id(app) in rate_limit._rate_limiting_wired_app_ids
    rate_limit.require_rate_limiting_ready_for_production(app=app)


def test_legacy_app_wires_rate_limiting_to_serving_app_call_site() -> None:
    module = ast.parse(Path("legacy_app.py").read_text(encoding="utf-8"))

    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "app.security.rate_limit"
        and any(alias.name == "wire_rate_limiting" for alias in node.names)
        for node in ast.walk(module)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "wire_rate_limiting"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "app"
        for node in ast.walk(module)
    )


def test_rate_limit_readiness_allows_local_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setattr(rate_limit, "limiter", None)

    rate_limit.require_rate_limiting_ready_for_production()


def test_web_session_secure_cookie_uses_canonical_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")

    assert web_session._is_secure_cookie_environment() is True


def test_web_session_cookie_is_secure_when_runtime_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("DEBUG", "false")

    assert web_session._is_secure_cookie_environment() is True


def test_web_session_cookie_remains_insecure_in_explicit_local_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEBUG", "true")

    assert web_session._is_secure_cookie_environment() is False


def test_synthetic_production_invariant_ci_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit, "limiter", _FakeLimiter())

    run_synthetic_production_checks()


def test_synthetic_ci_checker_covers_all_invariant_flag_constants() -> None:
    assert set(_UNSAFE_FALSE_FLAG_OVERRIDES) == set(production_invariants.PRODUCTION_FALSE_FLAGS)
    assert set(_UNSAFE_TRUE_FLAG_OVERRIDES) == set(production_invariants.PRODUCTION_TRUE_FLAGS)

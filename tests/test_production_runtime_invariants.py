"""Tests for production/staging runtime invariant guards."""

from __future__ import annotations

import asyncio
import ast
from pathlib import Path
import re
import runpy
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.bootstrap import http_stack
from app.bootstrap.direct_api_root import serve_legacy_bmi_calculator_web
from app.bootstrap import startup_guards
from app.middleware.csp import CSP_HEADER_NAME, CSPNonceMiddleware
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


def test_wire_rate_limiting_is_idempotent_and_rejects_partial_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()

    rate_limit.wire_rate_limiting(app)
    first_middleware = tuple(app.user_middleware)
    first_handlers = dict(app.exception_handlers)
    rate_limit.wire_rate_limiting(app)

    assert tuple(app.user_middleware) == first_middleware
    assert app.exception_handlers == first_handlers

    partial_app = FastAPI()
    partial_app.state.limiter = rate_limit.limiter
    with pytest.raises(RuntimeError, match="Partial SlowAPI"):
        rate_limit.wire_rate_limiting(partial_app)


def test_wire_rate_limiting_ignores_and_refreshes_stale_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit.limiter, "enabled", rate_limit.limiter.enabled)
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())

    enabled_app = FastAPI()
    rate_limit._rate_limiting_wired_app_ids.add(id(enabled_app))
    monkeypatch.setenv("TESTING", "false")
    rate_limit.wire_rate_limiting(enabled_app)

    assert rate_limit._classify_rate_limit_wiring(enabled_app) == "complete"
    assert id(enabled_app) in rate_limit._rate_limiting_wired_app_ids

    disabled_app = FastAPI()
    rate_limit._rate_limiting_wired_app_ids.add(id(disabled_app))
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.delenv("RATE_LIMITING_IN_TESTS", raising=False)
    rate_limit.wire_rate_limiting(disabled_app)

    assert rate_limit._classify_rate_limit_wiring(disabled_app) == "none"
    assert id(disabled_app) not in rate_limit._rate_limiting_wired_app_ids


def test_wire_rate_limiting_rolls_back_failed_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()
    original_enabled = rate_limit.limiter.enabled

    def _fail_handler_registration(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic handler failure")

    monkeypatch.setattr(app, "add_exception_handler", _fail_handler_registration)

    with pytest.raises(RuntimeError, match="synthetic handler failure"):
        rate_limit.wire_rate_limiting(app)

    assert app.user_middleware == []
    assert not hasattr(app.state, "limiter")
    assert id(app) not in rate_limit._rate_limiting_wired_app_ids
    assert rate_limit.limiter.enabled is original_enabled


def test_rate_limiting_disabled_rejects_existing_wiring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()
    rate_limit.wire_rate_limiting(app)

    monkeypatch.setenv("TESTING", "true")
    monkeypatch.delenv("RATE_LIMITING_IN_TESTS", raising=False)

    with pytest.raises(RuntimeError, match="exists while rate limiting is disabled"):
        rate_limit.wire_rate_limiting(app)


def test_wire_rate_limiting_rejects_duplicate_foreign_and_late_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())

    duplicate_app = FastAPI()
    rate_limit.wire_rate_limiting(duplicate_app)
    duplicate_app.add_middleware(rate_limit.SlowAPIMiddleware)
    with pytest.raises(RuntimeError, match="Partial SlowAPI"):
        rate_limit.wire_rate_limiting(duplicate_app)

    foreign_handler_app = FastAPI()
    foreign_handler_app.add_exception_handler(
        rate_limit.RateLimitExceeded,
        lambda request, exc: None,
    )
    with pytest.raises(RuntimeError, match="Partial SlowAPI"):
        rate_limit.wire_rate_limiting(foreign_handler_app)

    late_app = FastAPI()
    late_app.middleware_stack = late_app.build_middleware_stack()
    with pytest.raises(RuntimeError, match="after the middleware stack is built"):
        rate_limit.wire_rate_limiting(late_app)


def test_rate_limit_wiring_classification_covers_optional_and_foreign_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", None)
    monkeypatch.setattr(rate_limit, "RateLimitExceeded", None)

    assert rate_limit._slowapi_middleware_counts(app) == (0, 0)
    assert rate_limit._rate_limit_handler_state(app) == (0, False, False)

    class SlowAPIMiddleware:
        pass

    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", type("SlowAPIMiddleware", (), {}))
    app.add_middleware(SlowAPIMiddleware)

    assert rate_limit._slowapi_middleware_counts(app) == (0, 1)


def test_rate_limit_wiring_rejects_reload_equivalent_exception_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    stale_exception = type("RateLimitExceeded", (Exception,), {})
    stale_exception.__module__ = rate_limit.RateLimitExceeded.__module__
    stale_exception.__qualname__ = rate_limit.RateLimitExceeded.__qualname__
    app.state.limiter = rate_limit.limiter
    app.add_middleware(rate_limit.SlowAPIMiddleware)
    app.add_exception_handler(
        stale_exception,
        rate_limit._rate_limit_exceeded_json_handler,
    )
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", {id(app)})

    assert rate_limit.RateLimitExceeded not in app.exception_handlers
    assert rate_limit._rate_limit_handler_state(app) == (0, False, True)
    assert rate_limit._classify_rate_limit_wiring(app) == "partial"

    monkeypatch.setenv("TESTING", "false")
    with pytest.raises(RuntimeError, match="Partial SlowAPI"):
        rate_limit.wire_rate_limiting(app)


def test_rate_limit_wiring_snapshot_restores_state_and_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()
    app.state.limiter = rate_limit.limiter
    rate_limit._rate_limiting_wired_app_ids.add(id(app))
    populated_snapshot = rate_limit._capture_rate_limit_wiring(app)

    delattr(app.state, "limiter")
    rate_limit._rate_limiting_wired_app_ids.clear()
    rate_limit._restore_rate_limit_wiring(app, populated_snapshot)

    assert app.state.limiter is rate_limit.limiter
    assert id(app) in rate_limit._rate_limiting_wired_app_ids

    empty_app = FastAPI()
    empty_snapshot = rate_limit._capture_rate_limit_wiring(empty_app)
    empty_app.state.limiter = rate_limit.limiter
    rate_limit._restore_rate_limit_wiring(empty_app, empty_snapshot)

    assert not hasattr(empty_app.state, "limiter")


def test_wire_rate_limiting_rejects_unavailable_or_invalid_final_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    real_slowapi_middleware = rate_limit.SlowAPIMiddleware
    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", None)

    with pytest.raises(RuntimeError, match="middleware and exception handler are unavailable"):
        rate_limit.wire_rate_limiting(FastAPI())

    monkeypatch.setattr(rate_limit, "SlowAPIMiddleware", real_slowapi_middleware)
    calls = 0

    def _fail_final_validation(app: FastAPI) -> rate_limit.RateLimitWiringState:
        nonlocal calls
        calls += 1
        if calls == 1:
            return "none"
        return "partial"

    monkeypatch.setattr(rate_limit, "_classify_rate_limit_wiring", _fail_final_validation)

    with pytest.raises(RuntimeError, match="wiring validation failed"):
        rate_limit.wire_rate_limiting(FastAPI())


def test_application_local_dotenv_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr("settings.get_runtime_env_name", lambda: "local")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda: calls.append("load"))
    namespace = runpy.run_path("app/bootstrap/application.py", run_name="__pp_local__")
    assert (namespace["RUNTIME_ENV"], calls) == ("local", ["load"])


def test_bootstrap_rejects_extra_ws_member(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as app_main

    source = APIRouter()
    source.add_api_websocket_route(app_main._WS_ROUTE_PATHS[0], app_main.realtime_ws.ws_pro)
    source.add_api_websocket_route(app_main._WS_ROUTE_PATHS[1], app_main.realtime_ws.ws_root)
    source.add_api_websocket_route("/unexpected-ws", lambda _: None)
    monkeypatch.setattr(app_main.realtime_ws, "router", source)
    target = FastAPI()
    before = (tuple(target.routes), tuple(target.user_middleware))
    with pytest.raises(RuntimeError, match=r"^Incomplete canonical websocket route family\.$"):
        app_main.ensure_canonical_app_bootstrap(target)
    assert (tuple(target.routes), tuple(target.user_middleware)) == before


def test_canonical_http_stack_owns_rate_limiting_call_site() -> None:
    main_module = ast.parse(Path("app/main.py").read_text(encoding="utf-8"))
    legacy_module = ast.parse(Path("legacy_app.py").read_text(encoding="utf-8"))

    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "app.bootstrap.http_stack"
        and any(alias.name == "register_http_middleware_stack" for alias in node.names)
        for node in ast.walk(main_module)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "register_http_middleware_stack"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "target_app"
        for node in ast.walk(main_module)
    )
    assert not any(
        isinstance(node, ast.Name)
        and node.id in {"wire_rate_limiting", "register_http_middleware_stack"}
        for node in ast.walk(legacy_module)
    )


def _fresh_canonical_stack_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.delenv("RATE_LIMITING_IN_TESTS", raising=False)
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()
    http_stack.register_http_middleware_stack(app)
    return app


def test_canonical_http_stack_registers_exact_order_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _fresh_canonical_stack_app(monkeypatch)

    assert http_stack._owned_middleware_projection(app) == (
        "tracing",
        "request_telemetry",
        "metrics",
        "csp",
    )
    first_middleware = tuple(app.user_middleware)
    first_routes = tuple(app.routes)

    http_stack.register_http_middleware_stack(app)

    assert tuple(app.user_middleware) == first_middleware
    assert tuple(app.routes) == first_routes


def test_canonical_http_stack_preserves_enabled_slowapi_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()

    http_stack.register_http_middleware_stack(app)

    assert http_stack._owned_middleware_projection(app) == (
        "tracing",
        "request_telemetry",
        "metrics",
        "csp",
        "rate_limit",
    )
    rate_limit.require_rate_limiting_ready_for_production(app=app)


def test_http_stack_owned_middleware_classifier_is_fail_closed() -> None:
    assert http_stack._callable_key(object()) is None
    assert (
        http_stack._middleware_label(
            SimpleNamespace(
                cls=BaseHTTPMiddleware,
                kwargs=None,
                options={"dispatch": http_stack.metrics_middleware},
            )
        )
        == "metrics"
    )
    assert (
        http_stack._middleware_label(
            SimpleNamespace(cls=type("CSPNonceMiddleware", (), {}), kwargs={})
        )
        == "foreign_csp"
    )
    assert (
        http_stack._middleware_label(
            SimpleNamespace(
                cls=type(rate_limit.SlowAPIMiddleware.__name__, (), {}),
                kwargs={},
            )
        )
        == "foreign_rate_limit"
    )
    assert http_stack._middleware_label(SimpleNamespace(cls=object, kwargs={})) is None
    assert (
        http_stack._middleware_label(
            SimpleNamespace(
                cls=BaseHTTPMiddleware,
                kwargs={"dispatch": lambda request, call_next: None},
            )
        )
        is None
    )


def test_http_stack_complete_validation_rejects_missing_ancillary_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _fresh_canonical_stack_app(monkeypatch)
    expected = http_stack._expected_owned_projection()
    metrics_routes = http_stack._metrics_routes(app)
    assert len(metrics_routes) == 1
    app.router.routes.remove(metrics_routes[0])

    with pytest.raises(RuntimeError, match="/metrics route ownership"):
        http_stack._validate_complete_stack(app, expected)

    app = _fresh_canonical_stack_app(monkeypatch)
    delattr(app.state, "request_telemetry_recorder")
    with pytest.raises(RuntimeError, match="telemetry recorder"):
        http_stack._validate_complete_stack(app, expected)


def test_canonical_http_stack_rejects_partial_foreign_and_late_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.delenv("RATE_LIMITING_IN_TESTS", raising=False)
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())

    partial_app = FastAPI()
    partial_app.add_middleware(CSPNonceMiddleware)
    with pytest.raises(RuntimeError, match="partial, duplicated, foreign, or out of order"):
        http_stack.register_http_middleware_stack(partial_app)

    async def _foreign_dispatch(request: Request, call_next: Any) -> Any:
        return await call_next(request)

    _foreign_dispatch.__name__ = "metrics_middleware"
    foreign_app = FastAPI()
    foreign_app.add_middleware(BaseHTTPMiddleware, dispatch=_foreign_dispatch)
    with pytest.raises(RuntimeError, match="partial, duplicated, foreign, or out of order"):
        http_stack.register_http_middleware_stack(foreign_app)

    late_app = FastAPI()
    late_app.middleware_stack = late_app.build_middleware_stack()
    with pytest.raises(RuntimeError, match="after startup"):
        http_stack.register_http_middleware_stack(late_app)


def test_canonical_http_stack_rolls_back_every_owned_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.delenv("RATE_LIMITING_IN_TESTS", raising=False)
    monkeypatch.setattr(rate_limit, "_rate_limiting_wired_app_ids", set())
    app = FastAPI()
    original_routes = tuple(app.routes)
    original_state = dict(vars(app.state)["_state"])

    def _fail_telemetry(target_app: FastAPI) -> None:
        raise RuntimeError("synthetic telemetry failure")

    monkeypatch.setattr(http_stack, "register_request_telemetry", _fail_telemetry)

    with pytest.raises(RuntimeError, match="synthetic telemetry failure"):
        http_stack.register_http_middleware_stack(app)

    assert app.user_middleware == []
    assert tuple(app.routes) == original_routes
    assert dict(vars(app.state)["_state"]) == original_state
    assert app.middleware_stack is None


def test_canonical_bootstrap_stack_failure_preserves_global_app_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.main as app_main

    original_app = app_main.app

    def _fail_stack(target_app: FastAPI) -> None:
        raise RuntimeError("synthetic canonical stack failure")

    monkeypatch.setattr(app_main, "register_http_middleware_stack", _fail_stack)

    with pytest.raises(RuntimeError, match="synthetic canonical stack failure"):
        app_main.ensure_canonical_app_bootstrap(FastAPI())

    assert app_main.app is original_app


def test_csp_nonce_matches_legacy_bmi_html_and_streaming_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _fresh_canonical_stack_app(monkeypatch)
    app.add_api_route(
        "/legacy/bmi-calculator",
        serve_legacy_bmi_calculator_web,
        methods=["GET"],
    )

    async def _stream() -> StreamingResponse:
        async def _chunks() -> Any:
            yield b"pulse"
            yield b"plate"

        return StreamingResponse(_chunks(), media_type="text/plain")

    app.add_api_route("/stream", _stream, methods=["GET"])

    with TestClient(app) as client:
        first = client.get("/legacy/bmi-calculator")
        second = client.get("/legacy/bmi-calculator")
        streamed = client.get("/stream")
        missing = client.get("/missing")

    assert first.status_code == 200
    assert streamed.text == "pulseplate"
    nonce_match = re.search(r'nonce="([A-Za-z0-9_-]+)"', first.text)
    assert nonce_match is not None
    nonce = nonce_match.group(1)
    expected_csp = "; ".join(
        [
            "default-src 'self'",
            (
                "script-src 'self' "
                f"'nonce-{nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com"
            ),
            (
                "style-src 'self' "
                f"'nonce-{nonce}' https://fonts.googleapis.com https://cdn.jsdelivr.net"
            ),
            "img-src 'self' data: https:",
            "font-src 'self' https://fonts.gstatic.com",
            "frame-ancestors 'none'",
            "object-src 'none'",
        ]
    )
    assert first.headers[CSP_HEADER_NAME] == expected_csp
    assert f'nonce="{nonce}"' in first.text
    assert second.headers[CSP_HEADER_NAME] != first.headers[CSP_HEADER_NAME]
    assert streamed.headers[CSP_HEADER_NAME].startswith("default-src 'self'")
    assert missing.status_code == 404
    assert missing.headers[CSP_HEADER_NAME].startswith("default-src 'self'")


def test_csp_middleware_bypasses_non_http_scopes() -> None:
    observed: list[dict[str, Any]] = []

    async def _inner(scope: Any, receive: Any, send: Any) -> None:
        observed.append(dict(scope))

    async def _receive() -> dict[str, str]:
        return {"type": "websocket.disconnect"}

    async def _send(message: Any) -> None:
        raise AssertionError(f"unexpected send: {message}")

    scope: dict[str, Any] = {"type": "websocket"}
    asyncio.run(CSPNonceMiddleware(_inner)(scope, _receive, _send))

    assert observed == [{"type": "websocket"}]
    assert "state" not in scope


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

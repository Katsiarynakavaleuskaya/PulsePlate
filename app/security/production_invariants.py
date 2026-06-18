"""Fail-closed production/staging runtime invariant guards."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from app.security.rate_limit import require_rate_limiting_ready_for_production
from app.security.server_salt import require_server_salt
from settings import (
    get_export_token_secret,
    get_runtime_env_name,
    is_private_exports_enabled,
    is_production_like_env,
    is_truthy_env_var,
    validate_api_key_toggle_guard,
    validate_apple_receipt_verification_config,
)

PRODUCTION_TRUE_FLAGS = ("API_KEY_REQUIRED", "SUBSCRIPTION_DB_ENABLED")
PRODUCTION_FALSE_FLAGS = (
    "ALLOW_DEV_API_KEY",
    "ALLOW_ANONYMOUS_API_KEYS",
    "DEBUG",
    "TESTING",
    "ENABLE_TEST_ROUTES",
    "ENABLE_DEBUG_ENDPOINT",
    "METRICS_TEST_BYPASS",
)
_EXPORT_SIGNING_PLACEHOLDERS = frozenset(
    {
        "__set_me__",
        "replace_me",
        "replace_me_with_export_secret",
    }
)


def _runtime_env_label() -> str:
    """Return safe env label for error messages."""

    return get_runtime_env_name() or "unknown"


def _require_truthy_env_flags() -> None:
    """Require production/staging flags that must be explicitly enabled."""

    missing = [flag for flag in PRODUCTION_TRUE_FLAGS if not is_truthy_env_var(flag, "false")]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"{joined} must be true in production/staging environments "
            f"(current env: {_runtime_env_label()})."
        )


def _reject_truthy_env_flags() -> None:
    """Reject dev/test/debug escape hatches in production/staging."""

    invalid = [flag for flag in PRODUCTION_FALSE_FLAGS if is_truthy_env_var(flag, "false")]
    if invalid:
        joined = ", ".join(invalid)
        raise RuntimeError(
            f"{joined} must be false in production/staging environments "
            f"(current env: {_runtime_env_label()})."
        )


def _require_production_database_url() -> None:
    """Require a canonical Postgres DATABASE_URL in production/staging."""

    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required in production-like environments "
            f"(resolved env: {_runtime_env_label()})."
        )
    try:
        backend_name = make_url(database_url).get_backend_name().lower()
    except ArgumentError as exc:
        raise RuntimeError(
            "DATABASE_URL must be a valid PostgreSQL URL in production/staging "
            f"environments (current env: {_runtime_env_label()})."
        ) from exc
    if backend_name != "postgresql":
        raise RuntimeError(
            "DATABASE_URL must use PostgreSQL in production/staging environments "
            f"(current env: {_runtime_env_label()})."
        )


def _require_private_exports_enabled() -> None:
    """Require signed export links in production/staging."""

    if not is_private_exports_enabled():
        raise RuntimeError(
            "PRIVATE_EXPORTS_ENABLED must be true in production/staging environments; "
            "disabling it makes export token validation a no-op."
        )
    secret = get_export_token_secret().strip()
    if not secret or secret.lower() in _EXPORT_SIGNING_PLACEHOLDERS:
        raise RuntimeError(
            "EXPORT_TOKEN_SECRET must be set to a non-default secret in "
            "production/staging environments."
        )


def assert_production_runtime_invariants(app: Any | None = None) -> None:
    """Fail closed when production/staging runtime posture is unsafe."""

    if not is_production_like_env():
        return

    _reject_truthy_env_flags()
    _require_truthy_env_flags()
    validate_api_key_toggle_guard()
    require_server_salt()
    validate_apple_receipt_verification_config()
    _require_private_exports_enabled()
    _require_production_database_url()
    require_rate_limiting_ready_for_production(app=app)


__all__ = [
    "PRODUCTION_FALSE_FLAGS",
    "PRODUCTION_TRUE_FLAGS",
    "assert_production_runtime_invariants",
]

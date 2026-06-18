#!/usr/bin/env python3
"""Synthetic production-runtime invariant guard for CI."""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from collections.abc import Iterator, Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.security.production_invariants import (
    PRODUCTION_FALSE_FLAGS,
    PRODUCTION_TRUE_FLAGS,
    assert_production_runtime_invariants,
)
from app.security import rate_limit

_MANAGED_ENV = (
    "APP_ENV",
    "ENVIRONMENT",
    "DEBUG",
    "TESTING",
    "ALLOW_DEV_API_KEY",
    "ALLOW_ANONYMOUS_API_KEYS",
    "API_KEY_REQUIRED",
    "SUBSCRIPTION_DB_ENABLED",
    "SERVER_SALT",
    "APPLE_SHARED_SECRET",
    "PRIVATE_EXPORTS_ENABLED",
    "EXPORT_TOKEN_SECRET",
    "DATABASE_URL",
    "ENABLE_TEST_ROUTES",
    "ENABLE_DEBUG_ENDPOINT",
    "METRICS_TEST_BYPASS",
    "RATE_LIMITING_IN_TESTS",
)


@contextmanager
def _patched_env(values: Mapping[str, str | None]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in _MANAGED_ENV}
    try:
        for name in _MANAGED_ENV:
            os.environ.pop(name, None)
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _safe_production_env(**overrides: str) -> dict[str, str]:
    env = {
        "APP_ENV": "production",
        "ENVIRONMENT": "production",
        "DEBUG": "false",
        "TESTING": "false",
        "ALLOW_DEV_API_KEY": "false",  # pragma: allowlist secret
        "ALLOW_ANONYMOUS_API_KEYS": "false",  # pragma: allowlist secret
        "API_KEY_REQUIRED": "true",  # pragma: allowlist secret
        "SUBSCRIPTION_DB_ENABLED": "true",
        "SERVER_SALT": "SyntheticServerSaltForProductionInvariantCI123!",  # pragma: allowlist secret
        "APPLE_SHARED_SECRET": "synthetic-apple-shared-secret",  # pragma: allowlist secret
        "PRIVATE_EXPORTS_ENABLED": "true",
        "EXPORT_TOKEN_SECRET": "synthetic-export-token-secret",  # pragma: allowlist secret
        "DATABASE_URL": "postgresql+psycopg://db/pulseplate",
        "ENABLE_TEST_ROUTES": "0",
        "ENABLE_DEBUG_ENDPOINT": "false",
        "METRICS_TEST_BYPASS": "false",
    }
    env.update(overrides)
    return env


_UNSAFE_FALSE_FLAG_OVERRIDES = {flag: {flag: "true"} for flag in PRODUCTION_FALSE_FLAGS}
_UNSAFE_TRUE_FLAG_OVERRIDES = {flag: {flag: "false"} for flag in PRODUCTION_TRUE_FLAGS}


def _expect_pass() -> None:
    with _patched_env(_safe_production_env()):
        assert_production_runtime_invariants()


def _expect_failure(name: str, **overrides: str) -> None:
    with _patched_env(_safe_production_env(**overrides)):
        try:
            assert_production_runtime_invariants()
        except RuntimeError:
            return
    raise AssertionError(f"expected production invariant failure for {name}")


def run_synthetic_production_checks() -> None:
    """Run deterministic safe/unsafe production posture checks."""

    limiter = rate_limit.limiter
    previous_limiter_enabled = getattr(limiter, "enabled", None)
    try:
        if limiter is not None:
            limiter.enabled = True
        _expect_pass()
        for flag in PRODUCTION_FALSE_FLAGS:
            override = _UNSAFE_FALSE_FLAG_OVERRIDES[flag]
            _expect_failure(f"{flag} enabled", **override)
        for flag in PRODUCTION_TRUE_FLAGS:
            override = _UNSAFE_TRUE_FLAG_OVERRIDES[flag]
            _expect_failure(f"{flag} disabled", **override)
        _expect_failure("private exports disabled", PRIVATE_EXPORTS_ENABLED="false")
        _expect_failure("sqlite database url", DATABASE_URL="sqlite:///cache/app.db")
    finally:
        if limiter is not None and previous_limiter_enabled is not None:
            limiter.enabled = previous_limiter_enabled


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--synthetic-production",
        action="store_true",
        help="run deterministic synthetic production checks",
    )
    args = parser.parse_args()

    if not args.synthetic_production:
        parser.error("--synthetic-production is required")
    run_synthetic_production_checks()
    print("PASS: production runtime invariant synthetic checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

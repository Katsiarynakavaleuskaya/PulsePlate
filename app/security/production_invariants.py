"""Fail-closed production/staging runtime invariant guards."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import secrets
import stat
from typing import Any, Literal

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

METRICS_SCRAPE_KEY_FILE_ENV = "METRICS_SCRAPE_KEY_FILE"
DEFAULT_METRICS_SCRAPE_KEY_FILE = "/run/secrets/pulseplate_metrics_scrape_key"
METRICS_SCRAPE_KEY_AUTH_MARKER = "metrics-scrape-key"
_METRICS_SCRAPE_KEY_MIN_BYTES = 32
_METRICS_SCRAPE_KEY_MAX_BYTES = 256


@dataclass(frozen=True)
class MetricsScrapeKeyRecognition:
    """Non-leaking result of descriptor-bound scrape-key recognition."""

    marker: Literal["absent", "ready", "invalid"]
    _secret: bytes | None = field(default=None, repr=False, compare=False)

    def matches(self, candidate: str | None) -> bool:
        """Compare a request credential without exposing the recognized secret."""

        if self.marker != "ready" or self._secret is None or candidate is None:
            return False
        try:
            candidate_bytes = candidate.encode("ascii", errors="strict")
        except UnicodeEncodeError:
            return False
        return secrets.compare_digest(candidate_bytes, self._secret)


def _read_metrics_scrape_key(file_name: str) -> bytes | None:
    """Read one bounded regular file through a no-follow descriptor."""

    no_follow = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(no_follow, int) or no_follow <= 0:
        return None

    flags = os.O_RDONLY | no_follow
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(file_name, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return None

        payload = bytearray()
        while len(payload) <= _METRICS_SCRAPE_KEY_MAX_BYTES:
            try:
                chunk = os.read(
                    descriptor,
                    _METRICS_SCRAPE_KEY_MAX_BYTES + 1 - len(payload),
                )
            except InterruptedError:
                continue
            if not chunk:
                break
            payload.extend(chunk)
        return bytes(payload)
    finally:
        os.close(descriptor)


def _is_valid_metrics_scrape_key(payload: bytes) -> bool:
    """Accept exactly 32..256 printable, non-whitespace ASCII bytes."""

    if not _METRICS_SCRAPE_KEY_MIN_BYTES <= len(payload) <= _METRICS_SCRAPE_KEY_MAX_BYTES:
        return False
    return all(0x21 <= byte <= 0x7E for byte in payload)


def recognize_metrics_scrape_key() -> MetricsScrapeKeyRecognition:
    """Recognize the optional metrics-only credential without leaking its path."""

    explicit_override = METRICS_SCRAPE_KEY_FILE_ENV in os.environ
    file_name = (
        os.environ.get(METRICS_SCRAPE_KEY_FILE_ENV, "")
        if explicit_override
        else DEFAULT_METRICS_SCRAPE_KEY_FILE
    )
    if not file_name or not os.path.isabs(file_name):
        return MetricsScrapeKeyRecognition("invalid")

    try:
        payload = _read_metrics_scrape_key(file_name)
    except FileNotFoundError:
        marker: Literal["absent", "invalid"] = "invalid" if explicit_override else "absent"
        return MetricsScrapeKeyRecognition(marker)
    except (OSError, ValueError):
        return MetricsScrapeKeyRecognition("invalid")

    if payload is None or not _is_valid_metrics_scrape_key(payload):
        return MetricsScrapeKeyRecognition("invalid")
    return MetricsScrapeKeyRecognition("ready", payload)


def _require_metrics_scrape_key_ready_for_production() -> None:
    """Fail closed for invalid or app-key-equivalent production credentials."""

    recognition = recognize_metrics_scrape_key()
    if recognition.marker == "invalid":
        raise RuntimeError(
            "Metrics scrape credential configuration is invalid in production/staging."
        )
    if recognition.marker == "ready" and recognition.matches(os.getenv("API_KEY")):
        raise RuntimeError(
            "Metrics scrape credential must differ from the application API key in "
            "production/staging."
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
    _require_metrics_scrape_key_ready_for_production()
    require_server_salt()
    validate_apple_receipt_verification_config()
    _require_private_exports_enabled()
    _require_production_database_url()
    require_rate_limiting_ready_for_production(app=app)


__all__ = [
    "DEFAULT_METRICS_SCRAPE_KEY_FILE",
    "METRICS_SCRAPE_KEY_AUTH_MARKER",
    "METRICS_SCRAPE_KEY_FILE_ENV",
    "MetricsScrapeKeyRecognition",
    "PRODUCTION_FALSE_FLAGS",
    "PRODUCTION_TRUE_FLAGS",
    "assert_production_runtime_invariants",
    "recognize_metrics_scrape_key",
]

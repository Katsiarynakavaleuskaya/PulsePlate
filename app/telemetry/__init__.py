"""PulsePlate telemetry configuration and tracing exports.

RU: Пакет объединяет env-конфигурацию request telemetry и tracing exports.
EN: Package combines request telemetry env configuration with tracing exports.
"""

from __future__ import annotations

import os

from app.telemetry.genai import OPENINFERENCE_SPAN_KIND
from app.telemetry.setup import tracing_is_enabled

DEFAULT_FULL_CAPTURE_RATE = 0.015
DEFAULT_FULL_CAPTURE_RESERVOIR_PER_HOUR = 60
DEFAULT_TELEMETRY_RECORDER_MAXLEN = 200
DEFAULT_TELEMETRY_TIMEOUT_SECONDS = 2.0
DEFAULT_TELEMETRY_SALT = "pp#2026"

FEATURED_RUNTIME_FLAGS: tuple[str, ...] = (
    "FEATURE_CBT_AGENT",
    "FEATURE_FOOD_SEARCH_COMPAT_ENABLED",
    "FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED",
    "FEATURE_PREMIUM_WEEK_ENABLED",
    "FEATURE_WEBSOCKET_ENABLED",
)


def _is_truthy(value: str | None) -> bool:
    """Return True for common truthy env values."""

    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: str | None, default: float) -> float:
    """Parse float env with clamp to sane bounds."""

    try:
        parsed = float(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(0.0, min(parsed, 1.0))


def _parse_positive_int(value: str | None, default: int) -> int:
    """Parse positive integer env with safe fallback."""

    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def telemetry_full_capture_rate() -> float:
    """Return deterministic full-capture sample rate."""

    return _parse_float(
        os.getenv("TELEMETRY_FULL_CAPTURE_RATE"),
        DEFAULT_FULL_CAPTURE_RATE,
    )


def telemetry_reservoir_per_hour() -> int:
    """Return hourly reservoir budget for full captures."""

    return _parse_positive_int(
        os.getenv("TELEMETRY_FULL_CAPTURE_RESERVOIR_PER_HOUR"),
        DEFAULT_FULL_CAPTURE_RESERVOIR_PER_HOUR,
    )


def telemetry_detectors_enabled() -> bool:
    """Return whether detector-triggered capture is enabled."""

    value = os.getenv("TELEMETRY_DETECTORS_ENABLED")
    if value is None:
        return True
    return _is_truthy(value)


def telemetry_client_debug_full_enabled() -> bool:
    """Return whether X-Debug-Full is honored in non-prod envs."""

    return _is_truthy(os.getenv("TELEMETRY_CLIENT_DEBUG_FULL"))


def telemetry_vault_dir() -> str | None:
    """Return optional telemetry vault directory."""

    value = (os.getenv("TELEMETRY_VAULT_DIR") or "").strip()
    return value or None


def telemetry_vault_key() -> str | None:
    """Return optional base64-encoded telemetry vault key."""

    value = (os.getenv("TELEMETRY_VAULT_KEY") or "").strip()
    return value or None


def telemetry_sampler_salt() -> str:
    """Return sampler salt."""

    value = (os.getenv("TELEMETRY_SAMPLER_SALT") or "").strip()
    return value or DEFAULT_TELEMETRY_SALT


def telemetry_recorder_maxlen() -> int:
    """Return bounded in-memory recorder size."""

    return _parse_positive_int(
        os.getenv("TELEMETRY_RECORDER_MAXLEN"),
        DEFAULT_TELEMETRY_RECORDER_MAXLEN,
    )


def telemetry_environment() -> str:
    """Return normalized runtime environment name."""

    return (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development").strip().lower()


def is_non_prod_environment() -> bool:
    """Return True for dev/test/staging-like environments."""

    return telemetry_environment() != "production"


__all__ = [
    "DEFAULT_FULL_CAPTURE_RATE",
    "DEFAULT_FULL_CAPTURE_RESERVOIR_PER_HOUR",
    "DEFAULT_TELEMETRY_RECORDER_MAXLEN",
    "DEFAULT_TELEMETRY_TIMEOUT_SECONDS",
    "DEFAULT_TELEMETRY_SALT",
    "FEATURED_RUNTIME_FLAGS",
    "OPENINFERENCE_SPAN_KIND",
    "is_non_prod_environment",
    "telemetry_client_debug_full_enabled",
    "telemetry_detectors_enabled",
    "telemetry_environment",
    "telemetry_full_capture_rate",
    "telemetry_recorder_maxlen",
    "telemetry_reservoir_per_hour",
    "telemetry_sampler_salt",
    "telemetry_vault_dir",
    "telemetry_vault_key",
    "tracing_is_enabled",
]

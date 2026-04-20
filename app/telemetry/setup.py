"""OpenTelemetry setup helpers for PulsePlate backend tracing.

RU: Lazy и безопасная инициализация OpenTelemetry для backend tracing.
EN: Lazy and safe OpenTelemetry initialization for backend tracing.
"""

from __future__ import annotations

from importlib import import_module
import logging
import os
from threading import Lock
from types import ModuleType
from typing import Any, Callable

from app.utils.feature_flags import _is_truthy

logger = logging.getLogger(__name__)

OTEL_EXPORTER_OTLP_TRACES_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
OTEL_SDK_DISABLED_ENV = "OTEL_SDK_DISABLED"
OTEL_SERVICE_NAME_ENV = "OTEL_SERVICE_NAME"
PULSE_OBS_HMAC_KEY_ENV = "PULSE_OBS_HMAC_KEY"
DEFAULT_SERVICE_NAME = "pulseplate-api"

_Importer = Callable[[str], ModuleType]
_LOCK = Lock()
_PROVIDER: Any = None
_TEST_EXPORTER: Any = None


def _import_module(module_name: str, importer: _Importer = import_module) -> ModuleType:
    """Import a module in a patchable way."""

    return importer(module_name)


def _env_enabled() -> bool:
    """Return True when tracing should be enabled from runtime env."""

    if _is_truthy(os.getenv(OTEL_SDK_DISABLED_ENV, "false")):
        return False
    return bool((os.getenv(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT_ENV) or "").strip())


def tracing_is_enabled() -> bool:
    """Return True when tracing is enabled via env or test exporter."""

    return _TEST_EXPORTER is not None or _env_enabled()


def require_observability_hmac_key() -> str:
    """Return HMAC key used for prompt/completion fingerprints."""

    value = (os.getenv(PULSE_OBS_HMAC_KEY_ENV) or "").strip()
    if not value:
        raise RuntimeError(f"{PULSE_OBS_HMAC_KEY_ENV} is required when GenAI tracing is enabled.")
    return value


def _build_provider(*, exporter: Any | None = None) -> Any | None:
    """Create a local tracer provider or return None when OTel deps are unavailable."""

    try:
        sdk_trace = _import_module("opentelemetry.sdk.trace")
        resources = _import_module("opentelemetry.sdk.resources")
        sdk_export = _import_module("opentelemetry.sdk.trace.export")
    except ImportError:
        logger.debug("OpenTelemetry SDK packages not installed; tracing disabled")
        return None

    require_observability_hmac_key()

    resource = resources.Resource.create(
        {"service.name": os.getenv(OTEL_SERVICE_NAME_ENV, DEFAULT_SERVICE_NAME)}
    )
    provider = sdk_trace.TracerProvider(resource=resource)

    active_exporter = exporter
    if active_exporter is None:
        endpoint = (os.getenv(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT_ENV) or "").strip()
        if not endpoint:
            return None
        try:
            otlp_http = _import_module("opentelemetry.exporter.otlp.proto.http.trace_exporter")
        except ImportError:
            logger.debug("OTLP HTTP exporter package not installed; tracing disabled")
            return None
        active_exporter = otlp_http.OTLPSpanExporter(endpoint=endpoint)

    span_processor = (
        sdk_export.SimpleSpanProcessor(active_exporter)
        if exporter is not None
        else sdk_export.BatchSpanProcessor(active_exporter)
    )
    provider.add_span_processor(span_processor)
    return provider


def ensure_tracing_initialized() -> bool:
    """Initialize the local tracer provider once when tracing is enabled."""

    global _PROVIDER

    if _PROVIDER is not None:
        return True
    if not tracing_is_enabled():
        return False

    with _LOCK:
        if _PROVIDER is not None:
            return True
        provider = _build_provider(exporter=_TEST_EXPORTER)
        if provider is None:
            return False
        _PROVIDER = provider
        return True


def get_tracer(name: str) -> Any:
    """Return a tracer from the local provider or a global no-op tracer."""

    trace_api = _import_module("opentelemetry.trace")
    if ensure_tracing_initialized() and _PROVIDER is not None:
        return _PROVIDER.get_tracer(name)
    return trace_api.get_tracer(name)


def install_test_exporter(exporter: Any) -> None:
    """Install an in-memory exporter for deterministic tests."""

    global _TEST_EXPORTER, _PROVIDER
    with _LOCK:
        _TEST_EXPORTER = exporter
        _PROVIDER = None


def reset_tracing_for_tests() -> None:
    """Reset local tracing state between tests."""

    global _TEST_EXPORTER, _PROVIDER
    with _LOCK:
        provider = _PROVIDER
        _TEST_EXPORTER = None
        _PROVIDER = None
    if provider is not None:
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception:
                logger.debug("Tracer provider shutdown failed during test reset", exc_info=True)


__all__ = [
    "DEFAULT_SERVICE_NAME",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT_ENV",
    "OTEL_SDK_DISABLED_ENV",
    "OTEL_SERVICE_NAME_ENV",
    "PULSE_OBS_HMAC_KEY_ENV",
    "ensure_tracing_initialized",
    "get_tracer",
    "install_test_exporter",
    "require_observability_hmac_key",
    "reset_tracing_for_tests",
    "tracing_is_enabled",
]

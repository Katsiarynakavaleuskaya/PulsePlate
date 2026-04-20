"""Configuration tests for backend GenAI tracing."""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.telemetry.setup import (
    ensure_tracing_initialized,
    install_test_exporter,
    reset_tracing_for_tests,
)


def test_tracing_requires_hmac_key_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enabled tracing must not initialize without the HMAC fingerprint key."""

    exporter = InMemorySpanExporter()
    reset_tracing_for_tests()
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.delenv("PULSE_OBS_HMAC_KEY", raising=False)
    install_test_exporter(exporter)

    try:
        with pytest.raises(RuntimeError, match="PULSE_OBS_HMAC_KEY"):
            ensure_tracing_initialized()
    finally:
        reset_tracing_for_tests()

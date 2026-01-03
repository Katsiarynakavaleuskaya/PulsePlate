# -*- coding: utf-8 -*-
"""
Diff coverage tests for app/services/weekly_plan/safety.py.

Covers:
- error_envelope core key protection
- safe_call with *args/**kwargs
- HTTPException re-raise
- logging sanitization and fallback
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi import HTTPException

from app.services.weekly_plan.safety import safe_call, weekly_plan_error_envelope


def test_error_envelope_does_not_allow_core_key_overrides() -> None:
    """Test that extra cannot override core envelope keys."""
    env = weekly_plan_error_envelope(
        code="x",
        detail="d",
        stage="s",
        extra={
            "status": "success",  # should be ignored
            "code": "override",  # should be ignored
            "message": "override",  # should be ignored
            "detail": "override",  # should be ignored
            "error": "override",  # should be ignored
            "stage": "override",  # should be ignored
            "custom": 123,
        },
    )
    assert env["status"] == "error"
    assert env["code"] == "x"
    assert env["detail"] == "d"
    assert env["message"] == "d"
    assert env["error"] == "x"
    assert env["stage"] == "s"
    assert env["custom"] == 123


def test_safe_call_supports_args_kwargs_and_returns_value() -> None:
    """Test safe_call accepts *args/**kwargs and returns function result."""

    def add(a: int, b: int, *, c: int = 0) -> int:
        return a + b + c

    out = safe_call(
        add,
        1,
        2,
        c=3,
        map_error=lambda _e: ("boom", "no"),
        default_code="boom",
        stage="t",
        debug_ctx={"k": "v"},
    )
    assert out == 6


def test_safe_call_reraises_http_exception() -> None:
    """Test safe_call re-raises HTTPException (preserves FastAPI contract)."""

    def boom() -> None:
        raise HTTPException(status_code=400, detail="bad")

    with pytest.raises(HTTPException) as e:
        _ = safe_call(
            boom,
            map_error=lambda _e: ("x", "y"),
            default_code="x",
            stage="t",
            debug_ctx=None,
        )
    assert e.value.status_code == 400
    assert e.value.detail == "bad"


def test_safe_call_returns_envelope_on_exception_and_sanitizes_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test safe_call handles logging failures gracefully (never masks original exception)."""
    # Force logging.exception to fail when extra is passed (simulate malformed extra / reserved keys)
    calls: list[dict[str, Any]] = []

    def flaky_logging_exception(msg: str, *args: Any, **kwargs: Any) -> None:
        calls.append({"msg": msg, "kwargs": kwargs})
        if "extra" in kwargs:
            raise RuntimeError("logging failed")

    monkeypatch.setattr(logging, "exception", flaky_logging_exception)

    def boom() -> None:
        raise RuntimeError("kaput")

    out = safe_call(
        boom,
        map_error=lambda _e: ("weekly_generation_failed", "Failed to generate plan"),
        default_code="weekly_generation_failed",
        stage="generation",
        debug_ctx={
            "exc_info": True,  # reserved
            "stack_info": True,  # reserved
            "ok": object(),  # non-serializable -> should be stringified
            123: "bad_key_type",  # non-string key -> should be dropped
        },
    )

    assert isinstance(out, dict)
    assert out["status"] == "error"
    assert out["code"] == "weekly_generation_failed"
    assert out.get("stage") == "generation"

    # Ensure we did not crash because logging failed with extra
    assert calls  # at least one attempt happened


def test_safe_call_map_error_failure_falls_back_to_default() -> None:
    """Test safe_call falls back to default_code if map_error itself fails."""

    def boom() -> None:
        raise ValueError("test")

    def failing_map_error(_e: Exception) -> tuple[str, str]:
        raise RuntimeError("map_error failed")

    out = safe_call(
        boom,
        map_error=failing_map_error,
        default_code="fallback_code",
        stage="test",
    )

    assert isinstance(out, dict)
    assert out["status"] == "error"
    assert out["code"] == "fallback_code"
    assert out["detail"] == "Operation failed"


def test_safe_call_production_masking_excludes_debug_ctx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test safe_call excludes debug_ctx from production responses."""
    monkeypatch.setenv("APP_ENV", "production")

    def boom() -> None:
        raise RuntimeError("test")

    out = safe_call(
        boom,
        default_code="test_code",
        stage="test",
        debug_ctx={"secret": "value", "router": "test"},
    )

    assert isinstance(out, dict)
    assert out["status"] == "error"
    # debug_ctx should not be in response
    assert "secret" not in out
    assert "router" not in out


from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from fastapi import APIRouter, HTTPException, WebSocket
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketDisconnect

router = APIRouter(tags=["realtime"])

DEFAULT_MAX_MESSAGE_BYTES: int = 4_096
DEFAULT_WINDOW_SECONDS: int = 10
DEFAULT_MAX_MESSAGES_PER_WINDOW: int = 20
ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({"ping"})


def _is_ws_enabled() -> bool:
    """Read WebSocket feature flag at call-time.

    RU: Флаг читается при каждом запросе, чтобы monkeypatch.setenv в тестах
    работал детерминированно и без import-time freeze.
    EN: Read feature flag on each request to keep tests deterministic and avoid
    import-time freeze issues.
    """
    return os.getenv("FEATURE_WEBSOCKET_ENABLED", "false").lower() == "true"


@dataclass(frozen=True)
class WsPolicy:
    """Immutable policy for WebSocket guardrails."""

    max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES
    window_seconds: int = DEFAULT_WINDOW_SECONDS
    max_messages_per_window: int = DEFAULT_MAX_MESSAGES_PER_WINDOW
    allowed_event_types: frozenset[str] = field(default_factory=lambda: ALLOWED_EVENT_TYPES)


def _policy_from_env() -> WsPolicy:
    """Load policy from env at call-time."""

    def _get_positive_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            return default
        return value if value > 0 else default

    return WsPolicy(
        max_message_bytes=_get_positive_int("WS_MAX_MESSAGE_BYTES", DEFAULT_MAX_MESSAGE_BYTES),
        window_seconds=_get_positive_int("WS_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS),
        max_messages_per_window=_get_positive_int(
            "WS_MAX_MESSAGES_PER_WINDOW", DEFAULT_MAX_MESSAGES_PER_WINDOW
        ),
        allowed_event_types=ALLOWED_EVENT_TYPES,
    )


class TokenVerifier(Protocol):
    """Callable protocol for token/API-key verification."""

    def __call__(self, token: str) -> object: ...


def _get_token_verifier() -> TokenVerifier:
    """Wire canonical PRO auth verifier via existing api_tiers stack.

    RU: Явно маппим HTTPException в PermissionError, чтобы websocket auth
    оставался единообразно fail-closed.
    EN: Explicitly map HTTPException to PermissionError to keep websocket auth
    behavior uniformly fail-closed.
    """
    from app.middleware.api_tiers import require_pro_tier

    def _verify(token: str) -> object:
        try:
            return require_pro_tier(token)
        except HTTPException as exc:
            raise PermissionError("auth_invalid") from exc
        except Exception as exc:
            raise PermissionError("auth_invalid") from exc

    return _verify


def _extract_bearer_token(ws: WebSocket) -> str | None:
    """Extract token from Authorization header or query parameter."""
    auth = ws.headers.get("authorization", "")
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1].strip()
        if token:
            return token

    token = ws.query_params.get("token", "").strip()
    return token or None


async def _authenticate_or_close(ws: WebSocket) -> bool:
    """Authenticate websocket and close with policy code on failure."""
    token = _extract_bearer_token(ws)
    if not token:
        await ws.close(code=1008, reason="auth_required")
        return False

    try:
        verifier = _get_token_verifier()
        await run_in_threadpool(verifier, token)
        return True
    except Exception:
        await ws.close(code=1008, reason="auth_invalid")
        return False


class _BurstLimiter:
    """Per-connection sliding-window limiter."""

    def __init__(
        self,
        window_seconds: int,
        max_events: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window = window_seconds
        self._max = max_events
        self._clock = clock
        self._events: deque[float] = deque()

    def allow(self) -> bool:
        now = self._clock()
        cutoff = now - self._window

        while self._events and self._events[0] < cutoff:
            self._events.popleft()

        if len(self._events) >= self._max:
            return False

        self._events.append(now)
        return True


def _is_within_size_limit(text: str, max_bytes: int) -> bool:
    return len(text.encode("utf-8")) <= max_bytes


def _parse_message(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


@router.websocket("/ws")
async def ws_root(ws: WebSocket) -> None:
    """Secure and deterministic WebSocket endpoint."""
    await ws.accept()

    if not _is_ws_enabled():
        await ws.close(code=1008, reason="ws_disabled")
        return

    if not await _authenticate_or_close(ws):
        return

    policy = _policy_from_env()
    limiter = _BurstLimiter(
        window_seconds=policy.window_seconds,
        max_events=policy.max_messages_per_window,
    )

    try:
        while True:
            frame = await ws.receive()
            if frame.get("type") == "websocket.disconnect":
                return

            text = frame.get("text")
            if text is None:
                await ws.close(code=1008, reason="invalid_json")
                return

            if not _is_within_size_limit(text, policy.max_message_bytes):
                await ws.close(code=1008, reason="payload_too_large")
                return

            if not limiter.allow():
                await ws.close(code=1008, reason="rate_limited")
                return

            message = _parse_message(text)
            if message is None:
                await ws.close(code=1008, reason="invalid_json")
                return

            message_type = message.get("type")
            if not isinstance(message_type, str) or message_type not in policy.allowed_event_types:
                await ws.close(code=1008, reason="event_type_not_allowed")
                return

            if message_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
                continue
    except WebSocketDisconnect:
        return

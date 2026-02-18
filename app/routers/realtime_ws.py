from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections import deque
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from fastapi import APIRouter, WebSocket
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketDisconnect

router = APIRouter(tags=["realtime"])
logger = logging.getLogger(__name__)

DEFAULT_MAX_MESSAGE_BYTES: int = 4_096
DEFAULT_WINDOW_SECONDS: int = 10
DEFAULT_MAX_MESSAGES_PER_WINDOW: int = 20
DEFAULT_MAX_CONNECTIONS: int = 200
DEFAULT_IDLE_TIMEOUT_SECONDS: int = 0
PROTOCOL_VERSION: str = "1"
ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({"ping", "subscribe"})
ALLOWED_CHANNELS: frozenset[str] = frozenset({"progress"})
POLICY_CLOSE_CODE: int = 1008
REASON_WS_DISABLED: str = "ws_disabled"
REASON_AUTH_REQUIRED: str = "auth_required"
REASON_AUTH_INVALID: str = "auth_invalid"
REASON_TEXT_FRAME_REQUIRED: str = "text_frame_required"
REASON_PAYLOAD_TOO_LARGE: str = "payload_too_large"
REASON_RATE_LIMITED: str = "rate_limited"
REASON_INVALID_JSON: str = "invalid_json"
REASON_EVENT_TYPE_NOT_ALLOWED: str = "event_type_not_allowed"
REASON_UNSUPPORTED_VERSION: str = "unsupported_version"
REASON_CHANNEL_NOT_ALLOWED: str = "channel_not_allowed"
REASON_TOO_MANY_CONNECTIONS: str = "too_many_connections"
REASON_IDLE_TIMEOUT: str = "idle_timeout"


class _ActiveConnectionsTracker:
    """Thread-safe counter for per-process active websocket connections."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0

    def try_acquire(self, limit: int) -> bool:
        with self._lock:
            if self._count >= limit:
                return False
            self._count += 1
            return True

    def release(self) -> None:
        with self._lock:
            if self._count > 0:
                self._count -= 1


_active_connections = _ActiveConnectionsTracker()


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
    max_connections: int = DEFAULT_MAX_CONNECTIONS
    idle_timeout_seconds: int = DEFAULT_IDLE_TIMEOUT_SECONDS
    protocol_version: str = PROTOCOL_VERSION
    allowed_event_types: frozenset[str] = field(default_factory=lambda: ALLOWED_EVENT_TYPES)
    allowed_channels: frozenset[str] = field(default_factory=lambda: ALLOWED_CHANNELS)


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

    def _get_non_negative_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            return default
        return value if value >= 0 else default

    return WsPolicy(
        max_message_bytes=_get_positive_int("WS_MAX_MESSAGE_BYTES", DEFAULT_MAX_MESSAGE_BYTES),
        window_seconds=_get_positive_int("WS_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS),
        max_messages_per_window=_get_positive_int(
            "WS_MAX_MESSAGES_PER_WINDOW", DEFAULT_MAX_MESSAGES_PER_WINDOW
        ),
        max_connections=_get_positive_int("WS_MAX_CONNECTIONS", DEFAULT_MAX_CONNECTIONS),
        idle_timeout_seconds=_get_non_negative_int(
            "WS_IDLE_TIMEOUT_SECONDS", DEFAULT_IDLE_TIMEOUT_SECONDS
        ),
        protocol_version=PROTOCOL_VERSION,
        allowed_event_types=ALLOWED_EVENT_TYPES,
        allowed_channels=ALLOWED_CHANNELS,
    )


class TokenVerifier(Protocol):
    """Callable protocol for token/API-key verification."""

    def __call__(self, token: str) -> object: ...


def _get_token_verifier() -> TokenVerifier:
    """Wire canonical PRO auth verifier via existing api_tiers stack.

    RU: Любую ошибку в verifier маппим в PermissionError, чтобы websocket auth
    оставался единообразно fail-closed.
    EN: Map any verifier error to PermissionError to keep websocket auth
    behavior uniformly fail-closed.
    """
    from app.middleware.api_tiers import require_pro_tier

    def _verify(token: str) -> object:
        try:
            return require_pro_tier(token)
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
        logger.info("ws_policy_close", extra={"reason": REASON_AUTH_REQUIRED})
        await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_AUTH_REQUIRED)
        return False

    try:
        verifier = _get_token_verifier()
        await run_in_threadpool(verifier, token)
        return True
    except Exception:
        logger.info("ws_policy_close", extra={"reason": REASON_AUTH_INVALID})
        await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_AUTH_INVALID)
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


def _resolve_message_version(message: dict[str, Any], policy: WsPolicy) -> str | None:
    """Resolve protocol version with backward-compatible ping handling.

    RU: Для ping разрешаем отсутствие version (legacy foundation behavior),
    но нормализуем к v1 для ответа. Для остальных событий version обязателен.
    EN: For ping we allow missing version (legacy foundation behavior) and
    normalize to v1. For other events, version is required.
    """
    raw_version = message.get("version")
    if "version" in message:
        return raw_version if isinstance(raw_version, str) else None

    message_type = message.get("type")
    if message_type == "ping":
        return policy.protocol_version
    return None


def _encode_event(event: dict[str, Any]) -> str:
    """Serialize websocket event deterministically."""
    return json.dumps(event, separators=(",", ":"), sort_keys=True)


async def _receive_frame_with_idle_timeout(
    ws: WebSocket, idle_timeout_seconds: int
) -> MutableMapping[str, Any] | None:
    """Receive one frame, optionally enforcing idle timeout."""
    try:
        if idle_timeout_seconds <= 0:
            return await ws.receive()
        return await asyncio.wait_for(ws.receive(), timeout=float(idle_timeout_seconds))
    except TimeoutError:
        logger.info("ws_policy_close", extra={"reason": REASON_IDLE_TIMEOUT})
        await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_IDLE_TIMEOUT)
        return None


@router.websocket("/ws")
async def ws_root(ws: WebSocket) -> None:
    """Secure and deterministic WebSocket endpoint."""
    await ws.accept()

    if not _is_ws_enabled():
        logger.info("ws_policy_close", extra={"reason": REASON_WS_DISABLED})
        await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_WS_DISABLED)
        return

    policy = _policy_from_env()
    connection_acquired = _active_connections.try_acquire(policy.max_connections)
    if not connection_acquired:
        logger.info("ws_policy_close", extra={"reason": REASON_TOO_MANY_CONNECTIONS})
        await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_TOO_MANY_CONNECTIONS)
        return

    try:
        if not await _authenticate_or_close(ws):
            return

        limiter = _BurstLimiter(
            window_seconds=policy.window_seconds,
            max_events=policy.max_messages_per_window,
        )

        while True:
            frame = await _receive_frame_with_idle_timeout(
                ws,
                policy.idle_timeout_seconds,
            )
            if frame is None:
                return
            if frame.get("type") == "websocket.disconnect":
                return

            text = frame.get("text")
            if text is None:
                logger.info("ws_policy_close", extra={"reason": REASON_TEXT_FRAME_REQUIRED})
                await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_TEXT_FRAME_REQUIRED)
                return

            if not _is_within_size_limit(text, policy.max_message_bytes):
                logger.info("ws_policy_close", extra={"reason": REASON_PAYLOAD_TOO_LARGE})
                await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_PAYLOAD_TOO_LARGE)
                return

            if not limiter.allow():
                logger.info("ws_policy_close", extra={"reason": REASON_RATE_LIMITED})
                await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_RATE_LIMITED)
                return

            message = _parse_message(text)
            if message is None:
                logger.info("ws_policy_close", extra={"reason": REASON_INVALID_JSON})
                await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_INVALID_JSON)
                return

            message_type = message.get("type")
            if not isinstance(message_type, str) or message_type not in policy.allowed_event_types:
                logger.info("ws_policy_close", extra={"reason": REASON_EVENT_TYPE_NOT_ALLOWED})
                await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_EVENT_TYPE_NOT_ALLOWED)
                return

            version = _resolve_message_version(message, policy)
            if version != policy.protocol_version:
                logger.info(
                    "ws_policy_close",
                    extra={
                        "reason": REASON_UNSUPPORTED_VERSION,
                        "version": version,
                        "type": message_type,
                    },
                )
                await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_UNSUPPORTED_VERSION)
                return

            if message_type == "ping":
                await ws.send_text(
                    _encode_event(
                        {
                            "version": policy.protocol_version,
                            "type": "pong",
                            "server_time_ms": int(time.time() * 1000),
                        }
                    )
                )
                continue

            if message_type == "subscribe":
                channel = message.get("channel")
                if not isinstance(channel, str) or channel not in policy.allowed_channels:
                    logger.info("ws_policy_close", extra={"reason": REASON_CHANNEL_NOT_ALLOWED})
                    await ws.close(code=POLICY_CLOSE_CODE, reason=REASON_CHANNEL_NOT_ALLOWED)
                    return

                await ws.send_text(
                    _encode_event(
                        {
                            "version": policy.protocol_version,
                            "type": "subscribed",
                            "channel": channel,
                        }
                    )
                )
                continue
    except WebSocketDisconnect:
        logger.info("ws_disconnect", extra={"reason": "client_disconnected"})
        return
    finally:
        if connection_acquired:
            _active_connections.release()

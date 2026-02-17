from __future__ import annotations

import json
from collections.abc import Callable
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.routers import realtime_ws


def _accept_stub(token: str) -> object:
    return {"sub": "ws-user", "token": token}


def _deny_stub(token: str) -> object:
    raise PermissionError(f"denied token={token!r}")


@pytest.fixture()
def ws_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client configured for deterministic websocket policy tests."""
    monkeypatch.setenv("FEATURE_WEBSOCKET_ENABLED", "true")
    monkeypatch.setenv("WS_WINDOW_SECONDS", "9999")
    monkeypatch.setenv("WS_MAX_MESSAGES_PER_WINDOW", "3")
    monkeypatch.setenv("WS_MAX_MESSAGE_BYTES", "128")
    return client


def test_policy_from_env_uses_defaults_for_missing_and_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WS_MAX_MESSAGE_BYTES", raising=False)
    monkeypatch.setenv("WS_WINDOW_SECONDS", "not-an-int")
    monkeypatch.setenv("WS_MAX_MESSAGES_PER_WINDOW", "0")

    policy = realtime_ws._policy_from_env()

    assert policy.max_message_bytes == realtime_ws.DEFAULT_MAX_MESSAGE_BYTES
    assert policy.window_seconds == realtime_ws.DEFAULT_WINDOW_SECONDS
    assert policy.max_messages_per_window == realtime_ws.DEFAULT_MAX_MESSAGES_PER_WINDOW
    assert policy.max_connections == realtime_ws.DEFAULT_MAX_CONNECTIONS
    assert policy.protocol_version == realtime_ws.PROTOCOL_VERSION


def test_token_verifier_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def _require_pro_tier_stub(token: str) -> object:
        return {"token": token}

    monkeypatch.setattr("app.middleware.api_tiers.require_pro_tier", _require_pro_tier_stub)
    verifier = realtime_ws._get_token_verifier()
    result = verifier("valid-token")
    assert result == {"token": "valid-token"}


def test_token_verifier_maps_http_exception_to_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_http_exception(_token: str) -> object:
        raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr("app.middleware.api_tiers.require_pro_tier", _raise_http_exception)
    verifier = realtime_ws._get_token_verifier()
    with pytest.raises(PermissionError, match="auth_invalid"):
        verifier("bad-token")


def test_token_verifier_maps_unexpected_exception_to_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_unexpected(_token: str) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.middleware.api_tiers.require_pro_tier", _raise_unexpected)
    verifier = realtime_ws._get_token_verifier()
    with pytest.raises(PermissionError, match="auth_invalid"):
        verifier("bad-token")


def test_ws_disabled_returns_1008(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_WEBSOCKET_ENABLED", "false")
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_missing_token(ws_client: TestClient) -> None:
    with ws_client.websocket_connect("/ws") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_invalid_token(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _deny_stub)
    with ws_client.websocket_connect(
        "/ws", headers={"Authorization": "Bearer invalid-token"}
    ) as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_accepts_valid_token_and_responds_pong(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        response = json.loads(ws.receive_text())
    assert response["version"] == "1"
    assert response["type"] == "pong"
    assert isinstance(response["server_time_ms"], int)


def test_ws_accepts_token_via_query_param_and_responds_pong(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.middleware.api_tiers.require_pro_tier", lambda _token: {"sub": "ws-user"}
    )
    with ws_client.websocket_connect("/ws?token=valid-token") as ws:
        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        response = json.loads(ws.receive_text())
    assert response["version"] == "1"
    assert response["type"] == "pong"
    assert isinstance(response["server_time_ms"], int)


def test_ws_legacy_ping_without_version_is_still_supported(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        response = json.loads(ws.receive_text())
    assert response["version"] == "1"
    assert response["type"] == "pong"
    assert isinstance(response["server_time_ms"], int)


@pytest.mark.parametrize(
    "exception_factory",
    [
        lambda: HTTPException(status_code=403, detail="forbidden"),
        lambda: Exception("boom"),
    ],
)
def test_ws_maps_require_pro_tier_exceptions_to_auth_invalid(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    exception_factory: Callable[[], BaseException],
) -> None:
    def _raise(_token: str) -> object:
        raise exception_factory()

    monkeypatch.setattr("app.middleware.api_tiers.require_pro_tier", _raise)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer some-token"}) as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_oversized_payload(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text("x" * 500)
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rate_limit_closes_after_burst(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    limit = 3
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        for _ in range(limit):
            ws.send_text(json.dumps({"version": "1", "type": "ping"}))
            response = json.loads(ws.receive_text())
            assert response["version"] == "1"
            assert response["type"] == "pong"
            assert isinstance(response["server_time_ms"], int)

        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_unknown_event_type(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "unknown", "channel": "bmi"}))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_subscribe_progress_channel_returns_ack(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "subscribe", "channel": "progress"}))
        response = json.loads(ws.receive_text())
    assert response == {"version": "1", "type": "subscribed", "channel": "progress"}


def test_ws_rejects_subscribe_without_version(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"type": "subscribe", "channel": "progress"}))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_unsupported_protocol_version(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "2", "type": "ping"}))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_ping_with_non_string_version(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": 1, "type": "ping"}))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_connection_when_over_max_connections(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WS_MAX_CONNECTIONS", "1")
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)

    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        response = json.loads(ws.receive_text())
        assert response["version"] == "1"
        assert response["type"] == "pong"
        assert isinstance(response["server_time_ms"], int)

        with ws_client.websocket_connect(
            "/ws", headers={"Authorization": "Bearer valid-token"}
        ) as ws2:
            with pytest.raises(WebSocketDisconnect) as exc:
                ws2.receive_text()
        assert exc.value.code == 1008


def test_ws_rejects_subscribe_with_unknown_channel(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "subscribe", "channel": "bmi"}))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_non_json_message(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text("not-json")
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_json_array_message(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps(["ping"]))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_binary_frame_with_policy_close(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_bytes(b"\x00\x01\x02")
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


@pytest.mark.asyncio
async def test_ws_handles_websocket_disconnect_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure explicit WebSocketDisconnect path is covered and graceful."""

    class _DummyWebSocket:
        headers: dict[str, str] = {}
        query_params: dict[str, str] = {}

        async def accept(self) -> None:
            return None

        async def close(self, code: int, reason: str) -> None:
            return None

        async def receive(self) -> dict[str, str]:
            raise WebSocketDisconnect()

        async def send_text(self, _text: str) -> None:
            return None

    async def _auth_ok(_ws: object) -> bool:
        return True

    monkeypatch.setattr(realtime_ws, "_is_ws_enabled", lambda: True)
    monkeypatch.setattr(realtime_ws, "_authenticate_or_close", _auth_ok)

    await realtime_ws.ws_root(cast(WebSocket, _DummyWebSocket()))

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.routers import realtime_ws


def _accept_stub(token: str) -> object:
    return {"sub": "ws-user", "token": token}


def _deny_stub(token: str) -> object:
    raise PermissionError(f"denied token={token!r}")


@pytest.fixture()
def ws_client(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client configured for deterministic websocket policy tests."""
    monkeypatch.setenv("FEATURE_WEBSOCKET_ENABLED", "true")
    monkeypatch.setenv("WS_WINDOW_SECONDS", "9999")
    monkeypatch.setenv("WS_MAX_MESSAGES_PER_WINDOW", "3")
    monkeypatch.setenv("WS_MAX_MESSAGE_BYTES", "128")
    return TestClient(app)


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
        ws.send_text(json.dumps({"type": "ping"}))
        response = json.loads(ws.receive_text())
    assert response == {"type": "pong"}


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
            ws.send_text(json.dumps({"type": "ping"}))
            assert json.loads(ws.receive_text()) == {"type": "pong"}

        ws.send_text(json.dumps({"type": "ping"}))
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_rejects_unknown_event_type(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"type": "subscribe", "channel": "bmi"}))
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

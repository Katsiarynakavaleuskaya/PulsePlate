from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_ws_rejects_connection_without_token_when_enabled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FEATURE_WEBSOCKET_ENABLED", "true")
    with client.websocket_connect("/ws") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()
        assert exc_info.value.code == 1008


def test_ws_accepts_pro_token_and_replies_with_pong(
    client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FEATURE_WEBSOCKET_ENABLED", "true")
    token = pro_headers["X-API-Key"]
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_text(json.dumps({"type": "ping", "version": "1"}))
        payload = json.loads(websocket.receive_text())
        assert payload["type"] == "pong"
        assert payload["version"] == "1"
        assert "server_time_ms" in payload


def test_ws_rate_limit_closes_connection(
    client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FEATURE_WEBSOCKET_ENABLED", "true")
    monkeypatch.setenv("WS_MAX_MESSAGES_PER_WINDOW", "1")
    monkeypatch.setenv("WS_WINDOW_SECONDS", "30")

    token = pro_headers["X-API-Key"]
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_text(json.dumps({"type": "ping", "version": "1"}))
        json.loads(websocket.receive_text())

        websocket.send_text(json.dumps({"type": "ping", "version": "1"}))
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()
        # 1008 is the canonical close code our server uses for rate-limit violations.
        assert exc_info.value.code == 1008

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.middleware.metrics as metrics_mod
from app.routers import realtime_ws


def _accept_stub(token: str) -> object:
    return {"sub": "ws-user", "token": token}


def _deny_stub(token: str) -> object:
    raise PermissionError(f"denied token={token!r}")


class _CounterChild:
    def __init__(self, parent: "_LabeledCounter") -> None:
        self._parent = parent

    def inc(self, amount: float = 1.0) -> None:
        self._parent.value += amount


class _LabeledCounter:
    def __init__(self) -> None:
        self.value: float = 0.0
        self.label_calls: list[dict[str, str]] = []

    def labels(self, **kwargs: str) -> _CounterChild:
        self.label_calls.append(kwargs)
        return _CounterChild(self)


class _GaugeChild:
    def __init__(self, parent: "_LabeledGauge") -> None:
        self._parent = parent

    def inc(self, amount: float = 1.0) -> None:
        self._parent.value += amount

    def dec(self, amount: float = 1.0) -> None:
        self._parent.value -= amount


class _LabeledGauge:
    def __init__(self) -> None:
        self.value: float = 0.0
        self.label_calls: list[dict[str, str]] = []

    def labels(self, **kwargs: str) -> _GaugeChild:
        self.label_calls.append(kwargs)
        return _GaugeChild(self)


class _WsMetricsStub:
    def __init__(self) -> None:
        self.ws_connect_total = _LabeledCounter()
        self.ws_messages_total = _LabeledCounter()
        self.ws_active_connections = _LabeledGauge()


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
    monkeypatch.setenv("WS_IDLE_TIMEOUT_SECONDS", "invalid")

    policy = realtime_ws._policy_from_env()

    assert policy.max_message_bytes == realtime_ws.DEFAULT_MAX_MESSAGE_BYTES
    assert policy.window_seconds == realtime_ws.DEFAULT_WINDOW_SECONDS
    assert policy.max_messages_per_window == realtime_ws.DEFAULT_MAX_MESSAGES_PER_WINDOW
    assert policy.max_connections == realtime_ws.DEFAULT_MAX_CONNECTIONS
    assert policy.idle_timeout_seconds == realtime_ws.DEFAULT_IDLE_TIMEOUT_SECONDS
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


def test_ws_rejects_missing_token(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics_stub = _WsMetricsStub()
    monkeypatch.setattr(metrics_mod, "PROMETHEUS_METRICS", metrics_stub)

    with ws_client.websocket_connect("/ws") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008
    assert metrics_stub.ws_connect_total.value == 1.0
    assert metrics_stub.ws_connect_total.label_calls[-1] == {
        "path": "/api/v1/pro/ws",
        "result": "rejected",
        "reason": "auth_required",
    }


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


def test_ws_over_cap_does_not_call_auth(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WS_MAX_CONNECTIONS", "1")

    called = {"auth": 0}

    def _spy(_token: str) -> object:
        called["auth"] += 1
        return {"sub": "ws-user"}

    monkeypatch.setattr("app.middleware.api_tiers.require_pro_tier", _spy)

    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        response = json.loads(ws.receive_text())
        assert response["version"] == "1"
        assert response["type"] == "pong"
        assert isinstance(response["server_time_ms"], int)
        assert called["auth"] == 1

        called["auth"] = 0
        with ws_client.websocket_connect(
            "/ws", headers={"Authorization": "Bearer valid-token"}
        ) as ws2:
            with pytest.raises(WebSocketDisconnect) as exc:
                ws2.receive_text()
        assert exc.value.code == 1008
        assert called["auth"] == 0


def test_ws_idle_timeout_closes_connection_without_sleep(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WS_IDLE_TIMEOUT_SECONDS", "5")
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)

    async def _timeout(awaitable: Any, timeout: float) -> dict[str, Any]:
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise TimeoutError(f"idle timeout={timeout}")

    monkeypatch.setattr(realtime_ws.asyncio, "wait_for", _timeout)

    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_ws_idle_timeout_zero_disables_wait_for_branch(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WS_IDLE_TIMEOUT_SECONDS", "0")
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)

    async def _wait_for_must_not_be_called(_awaitable: Any, _timeout: float) -> dict[str, Any]:
        raise AssertionError("wait_for should not be called when idle timeout is disabled")

    monkeypatch.setattr(realtime_ws.asyncio, "wait_for", _wait_for_must_not_be_called)

    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        response = json.loads(ws.receive_text())
    assert response["version"] == "1"
    assert response["type"] == "pong"
    assert isinstance(response["server_time_ms"], int)


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


def test_ws_metrics_increment_and_active_gauge_restore(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics_stub = _WsMetricsStub()
    monkeypatch.setattr(metrics_mod, "PROMETHEUS_METRICS", metrics_stub)
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)

    with ws_client.websocket_connect("/ws", headers={"Authorization": "Bearer valid-token"}) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        response = json.loads(ws.receive_text())
        assert response["type"] == "pong"

    assert metrics_stub.ws_connect_total.value == 1.0
    assert metrics_stub.ws_messages_total.value == 2.0  # in + out for ping/pong
    assert metrics_stub.ws_active_connections.value == 0.0

    assert metrics_stub.ws_connect_total.label_calls[-1]["path"] == "/api/v1/pro/ws"
    assert metrics_stub.ws_connect_total.label_calls[-1]["result"] == "accepted"
    assert metrics_stub.ws_connect_total.label_calls[-1]["reason"] == "none"
    assert {labels["direction"] for labels in metrics_stub.ws_messages_total.label_calls[-2:]} == {
        "in",
        "out",
    }
    for labels in metrics_stub.ws_messages_total.label_calls[-2:]:
        assert labels["path"] == "/api/v1/pro/ws"
        assert labels["status"] == "ok"


def test_ws_policy_close_log_contains_bounded_fields(
    ws_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="app.routers.realtime_ws")

    with ws_client.websocket_connect("/ws") as ws:
        with pytest.raises(WebSocketDisconnect):
            ws.receive_text()

    policy_records = [r for r in caplog.records if r.msg == "ws_policy_close"]
    assert policy_records, "Expected at least one ws_policy_close record"
    record = policy_records[-1]

    assert getattr(record, "path", "") == "/api/v1/pro/ws"
    assert getattr(record, "close_code", 0) == 1008
    assert getattr(record, "reason", "") == "auth_required"


@pytest.mark.asyncio
async def test_close_with_policy_normalizes_unknown_reason(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="app.routers.realtime_ws")

    class _DummyWebSocket:
        async def close(self, code: int, reason: str) -> None:
            assert code == 1008
            assert reason == "new_unlisted_reason"

    await realtime_ws._close_with_policy(cast(WebSocket, _DummyWebSocket()), "new_unlisted_reason")

    policy_records = [r for r in caplog.records if r.msg == "ws_policy_close"]
    assert policy_records, "Expected ws_policy_close log for helper"
    assert getattr(policy_records[-1], "reason", "") == "unknown"


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

    async def _auth_ok(_ws: object, _path_label: str = "/api/v1/pro/ws") -> bool:
        return True

    monkeypatch.setattr(realtime_ws, "_is_ws_enabled", lambda: True)
    monkeypatch.setattr(realtime_ws, "_authenticate_or_close", _auth_ok)

    await realtime_ws.ws_root(cast(WebSocket, _DummyWebSocket()))


def test_canonical_ws_path_accepts_valid_token_and_responds_pong(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the canonical /api/v1/pro/ws endpoint."""
    monkeypatch.setattr(realtime_ws, "_get_token_verifier", lambda: _accept_stub)
    with ws_client.websocket_connect(
        "/api/v1/pro/ws", headers={"Authorization": "Bearer valid-token"}
    ) as ws:
        ws.send_text(json.dumps({"version": "1", "type": "ping"}))
        response = json.loads(ws.receive_text())
    assert response["version"] == "1"
    assert response["type"] == "pong"
    assert isinstance(response["server_time_ms"], int)


def test_canonical_ws_path_rejects_missing_token(
    ws_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the canonical /api/v1/pro/ws endpoint rejects missing token."""
    with ws_client.websocket_connect("/api/v1/pro/ws") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_duplicate_ws_route_detection_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that duplicate WS route registration raises RuntimeError."""
    from app.main import _assert_no_duplicate_ws_route

    # Create a mock routes list with /api/v1/pro/ws already present
    mock_routes = [type("Route", (), {"path": "/api/v1/pro/ws"})()]

    # Patch the app.routes property via __class__
    import app.main as main_mod

    original_app = main_mod.app

    class MockApp:
        @property
        def routes(self):
            return mock_routes

    monkeypatch.setattr(main_mod, "app", MockApp())

    with pytest.raises(RuntimeError, match="Duplicate /api/v1/pro/ws route detected"):
        _assert_no_duplicate_ws_route()

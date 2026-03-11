from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace

import anyio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.testclient import TestClient
from starlette.requests import Request as StarletteRequest

from app.bootstrap.telemetry import register_request_telemetry
from app.middleware.request_telemetry import (
    _clone_request_with_body,
    _clone_request_with_preview_buffer,
    _extract_tier,
    _feature_flags_from_request,
    _get_recorder,
    build_request_fingerprint,
    request_telemetry_middleware,
)
from app.telemetry.detectors import DetectorContext, evaluate_capture_detectors
from app.telemetry.reservoir import HourlyReservoir
from app.telemetry.sampler import DeterministicHashSampler
from app.telemetry.vault import (
    _minimize_scalar,
    _resolve_field_name,
    _load_vault_key,
    decrypt_capture_artifact,
)


def _make_request(query_string: bytes) -> StarletteRequest:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/pro/nutrition/daily",
        "query_string": query_string,
        "headers": [(b"content-type", b"application/json")],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
    }
    return StarletteRequest(scope, receive)


def test_request_fingerprint_is_stable_across_query_order() -> None:
    request_a = _make_request(b"b=2&a=1")
    request_b = _make_request(b"a=1&b=2")

    fingerprint_a = build_request_fingerprint(
        request_a, route_template="/api/v1/pro/nutrition/daily"
    )
    fingerprint_b = build_request_fingerprint(
        request_b, route_template="/api/v1/pro/nutrition/daily"
    )

    assert fingerprint_a == fingerprint_b


def test_deterministic_sampler_is_consistent() -> None:
    sampler = DeterministicHashSampler(rate=0.5, salt="pp#test")

    decision_one = sampler.decide(fingerprint="abc123")
    decision_two = sampler.decide(fingerprint="abc123")

    assert decision_one == decision_two
    assert sampler.get_description() == "DeterministicHashSampler(rate=0.5000)"


def test_hourly_reservoir_resets_on_next_window() -> None:
    timeline = [0.0]
    reservoir = HourlyReservoir(n=1, time_fn=lambda: timeline[0])

    assert reservoir.take() is True
    assert reservoir.take() is False

    timeline[0] = 3601.0
    assert reservoir.take() is True


def test_detector_normalizes_explicit_hits_and_schema_mismatch() -> None:
    hits = evaluate_capture_detectors(
        DetectorContext(
            status_code=200,
            response_content_type="text/plain",
            expected_response_kind="json",
            explicit_hits=(" Low_Confidence ", "low_confidence", "safety_rule"),
        )
    )

    assert hits == ("low_confidence", "safety_rule", "schema_mismatch")


def test_request_helper_paths_cover_flags_tier_and_cached_body() -> None:
    request = _make_request(b"feature_cbt_agent=1")
    request.scope["headers"] = [
        (b"content-type", b"application/json"),
        (b"feature_cbt_agent", b"true"),
        (b"x-api-tier", b"pro"),
    ]
    request.state.current_user = SimpleNamespace(tier="VIP")

    assert _feature_flags_from_request(request) == ["FEATURE_CBT_AGENT"]
    assert _extract_tier(request) == "vip"

    delattr(request.state, "current_user")
    assert _extract_tier(request) == "pro"

    app = FastAPI()
    request.scope["app"] = app
    recorder = _get_recorder(request)
    assert request.app.state.request_telemetry_recorder is recorder

    cloned_request = _clone_request_with_body(request, b'{"ok":true}')
    assert cloned_request.scope["type"] == "http"
    assert anyio.run(cloned_request.body) == b'{"ok":true}'


def test_preview_buffer_streams_request_body_without_full_buffering() -> None:
    messages = iter(
        [
            {"type": "http.request", "body": b"abcdef", "more_body": True},
            {"type": "http.request", "body": b"ghijkl", "more_body": False},
        ]
    )

    async def receive() -> dict[str, object]:
        return next(messages)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/preview-buffer",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
    }
    request = StarletteRequest(scope, receive)

    cloned_request, preview = _clone_request_with_preview_buffer(request, preview_limit=5)

    assert anyio.run(cloned_request.body) == b"abcdefghijkl"
    assert bytes(preview) == b"abcde"


def test_vault_field_resolution_and_hash_only_minimization() -> None:
    assert _resolve_field_name("root.provider_trace") == "provider_trace"
    assert _resolve_field_name("root.prompt") == "prompt"
    assert _resolve_field_name("root.health.diagnosis") == "health_profile"
    assert _resolve_field_name("root.preview.content") == "source_content"

    minimized = _minimize_scalar("Call me at 555-555-5555", field_path="root.prompt")
    assert isinstance(minimized, dict)
    assert "sha256" in minimized
    assert minimized["length"] > 0


def test_vault_key_rejects_invalid_length() -> None:
    encoded_key = base64.b64encode(b"short").decode("utf-8")

    try:
        _load_vault_key(encoded_key)
    except ValueError as exc:
        assert "TELEMETRY_VAULT_KEY must decode" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected invalid key length to fail")


def test_detector_triggered_capture_encrypts_artifact_without_raw_span_leakage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app = FastAPI()
    register_request_telemetry(app)

    encoded_key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("utf-8")
    monkeypatch.setenv("TELEMETRY_VAULT_DIR", str(tmp_path))
    monkeypatch.setenv("TELEMETRY_VAULT_KEY", encoded_key)
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RATE", "0")
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RESERVOIR_PER_HOUR", "1")
    monkeypatch.setenv("TELEMETRY_DETECTORS_ENABLED", "true")

    @app.post("/api/v1/pro/insight")
    async def insight(request: Request) -> PlainTextResponse:
        request.state.expected_response_kind = "json"
        request.state.llm_confidence = 0.1
        return PlainTextResponse("diagnosis note provider@example.com 555-123-4567")

    client = TestClient(app)
    response = client.post(
        "/api/v1/pro/insight?lang=en",
        json={"query": "My diagnosis is migraine. Email me at provider@example.com"},
        headers={"X-Client-Platform": "web"},
    )

    assert response.status_code == 200
    recorder = app.state.request_telemetry_recorder
    spans = recorder.snapshot()
    assert spans
    attrs = spans[-1]["attributes"]
    assert attrs["pp.full_capture"] is True
    assert attrs["pp.full_pointer_sha256"]
    assert "detector:low_confidence" in attrs["pp.full_capture_reasons"]
    assert "detector:schema_mismatch" in attrs["pp.full_capture_reasons"]
    assert "provider@example.com" not in str(attrs)
    assert "migraine" not in str(attrs)

    artifacts = list(tmp_path.glob("**/*.bin"))
    assert len(artifacts) == 1
    ciphertext = artifacts[0].read_bytes()
    assert b"provider@example.com" not in ciphertext
    assert b"migraine" not in ciphertext

    decrypted = decrypt_capture_artifact(
        artifact_path=str(artifacts[0]),
        encoded_key=encoded_key,
    )
    assert "request_body" not in decrypted["request"]
    assert decrypted["response"]["status_code"] == 200
    assert "content_type" in decrypted["response"]


def test_debug_full_capture_requires_non_prod_flag(tmp_path: Path, monkeypatch) -> None:
    app = FastAPI()
    register_request_telemetry(app)

    encoded_key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("utf-8")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TELEMETRY_VAULT_DIR", str(tmp_path))
    monkeypatch.setenv("TELEMETRY_VAULT_KEY", encoded_key)
    monkeypatch.setenv("TELEMETRY_CLIENT_DEBUG_FULL", "true")
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RATE", "0")
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RESERVOIR_PER_HOUR", "1")

    @app.get("/debug-capture")
    async def debug_capture() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    response = client.get("/debug-capture", headers={"X-Debug-Full": "1"})
    assert response.status_code == 200
    spans = app.state.request_telemetry_recorder.snapshot()
    attrs = spans[-1]["attributes"]
    assert attrs["pp.full_capture"] is True
    assert "debug_header" in attrs["pp.full_capture_reasons"]


def test_telemetry_fail_open_when_capture_storage_raises(tmp_path: Path, monkeypatch) -> None:
    app = FastAPI()
    register_request_telemetry(app)

    encoded_key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("utf-8")
    monkeypatch.setenv("TELEMETRY_VAULT_DIR", str(tmp_path))
    monkeypatch.setenv("TELEMETRY_VAULT_KEY", encoded_key)
    monkeypatch.setenv("TELEMETRY_CLIENT_DEBUG_FULL", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setattr(
        "app.middleware.request_telemetry.store_capture_artifact",
        lambda **_: (_ for _ in ()).throw(RuntimeError("vault down")),
    )

    @app.get("/fail-open")
    async def fail_open() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    response = client.get("/fail-open", headers={"X-Debug-Full": "1"})

    assert response.status_code == 200
    spans = app.state.request_telemetry_recorder.snapshot()
    assert len(spans) == 1
    attrs = spans[-1]["attributes"]
    assert attrs["pp.full_capture"] is False
    assert "debug_header" in attrs["pp.full_capture_reasons"]
    assert "vault_store_failed" in attrs["pp.full_capture_reasons"]


def test_telemetry_fail_open_when_vault_config_is_invalid(monkeypatch) -> None:
    app = FastAPI()
    register_request_telemetry(app)

    monkeypatch.setenv("TELEMETRY_VAULT_DIR", "/tmp/telemetry-invalid")
    monkeypatch.setenv(
        "TELEMETRY_VAULT_KEY",
        base64.b64encode(b"0123456789abcdef0123456789abcdef").decode(  # pragma: allowlist secret
            "utf-8"
        ),
    )
    monkeypatch.setenv("TELEMETRY_CLIENT_DEBUG_FULL", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RATE", "0")
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RESERVOIR_PER_HOUR", "1")
    monkeypatch.setattr(
        "app.middleware.request_telemetry.telemetry_vault_key",
        lambda: (_ for _ in ()).throw(ValueError("invalid key")),
    )

    @app.get("/invalid-key")
    async def invalid_key() -> JSONResponse:
        return JSONResponse({"ok": True})

    client = TestClient(app)
    response = client.get("/invalid-key", headers={"X-Debug-Full": "1"})

    assert response.status_code == 200
    spans = app.state.request_telemetry_recorder.snapshot()
    assert len(spans) == 1
    attrs = spans[-1]["attributes"]
    assert attrs["pp.full_capture"] is False
    assert "debug_header" in attrs["pp.full_capture_reasons"]
    assert "vault_config_failed" in attrs["pp.full_capture_reasons"]


def test_middleware_keeps_bounded_preview_in_deferred_capture_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app = FastAPI()
    register_request_telemetry(app)

    encoded_key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("utf-8")
    monkeypatch.setenv("TELEMETRY_VAULT_DIR", str(tmp_path))
    monkeypatch.setenv("TELEMETRY_VAULT_KEY", encoded_key)
    monkeypatch.setenv("TELEMETRY_CLIENT_DEBUG_FULL", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RATE", "0")
    monkeypatch.setenv("TELEMETRY_FULL_CAPTURE_RESERVOIR_PER_HOUR", "1")

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/deferred-body",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"x-debug-full", b"1"),
        ],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
        "app": app,
    }
    request = StarletteRequest(scope, receive)
    body_called = False

    async def broken_body() -> bytes:
        nonlocal body_called
        body_called = True
        raise RuntimeError("request.body should not be called")

    object.__setattr__(request, "body", broken_body)

    async def call_next(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    response = anyio.run(request_telemetry_middleware, request, call_next)

    assert response.status_code == 200
    spans = app.state.request_telemetry_recorder.snapshot()
    assert len(spans) == 1
    attrs = spans[-1]["attributes"]
    assert attrs["pp.full_capture"] is True
    assert "debug_header" in attrs["pp.full_capture_reasons"]
    assert body_called is False

    artifacts = list(tmp_path.glob("**/*.bin"))
    assert len(artifacts) == 1
    decrypted = decrypt_capture_artifact(
        artifact_path=str(artifacts[0]),
        encoded_key=encoded_key,
    )
    assert "request_body" not in decrypted["request"]

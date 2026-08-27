"""Contract, security, persistence, and privacy tests for FitChef outcomes."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
from typing import cast

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.metrics as metrics
import app.routers.fitchef_structured as fitchef_router
import app.services.fitchef_support_outcomes as outcome_service
from app.effective_routes import iter_effective_route_candidates, route_methods, route_path
from app.middleware.api_tiers import TEST_KEY_PRO, derive_subject_id_from_api_key, require_pro_tier
from app.models.fitchef_support_outcomes import FitChefSupportOutcomeEvent
from app.schemas.fitchef_coaching import FitChefSupportOutcomeRequest
from app.security.web_session import WEB_SESSION_COOKIE_NAME, issue_web_session
from app.services.fitchef_support_outcomes import (
    FITCHEF_SUPPORT_OUTCOME_SQLITE_UNIQUE_SIGNATURE,
    FITCHEF_SUPPORT_OUTCOME_UNIQUE_CONSTRAINT,
    FitChefSupportOutcomeConflictError,
    FitChefSupportOutcomeRecord,
    FitChefSupportOutcomeStoreUnavailableError,
    record_fitchef_support_outcome,
)
from core.db import get_session_factory, init_db

_URL = "/api/v1/pro/fitchef/recommend/outcome"
_VALID_PAYLOAD: dict[str, object] = {
    "schema_version": "fitchef_support_outcome_v1",
    "support_need": "daily_structure",
    "outcome": "acknowledged",
    "client_event_id": "outcome-event-0001",
}


def _json_body(response: object) -> dict[str, object]:
    headers = getattr(response, "headers")
    assert cast(str, headers.get("content-type", "")).startswith("application/json")
    return cast(dict[str, object], getattr(response, "json")())


@pytest.fixture(autouse=True)
def _outcome_table() -> None:
    engine = init_db()
    assert inspect(engine).has_table("fitchef_support_outcome_events")
    session_factory = get_session_factory()
    with session_factory() as session:
        session.execute(delete(FitChefSupportOutcomeEvent))
        session.commit()
    yield
    with session_factory() as session:
        session.execute(delete(FitChefSupportOutcomeEvent))
        session.commit()


@pytest.fixture
def outcome_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_FITCHEF_SUPPORT_OUTCOME_LEDGER", "true")


def _rows() -> list[FitChefSupportOutcomeEvent]:
    with get_session_factory()() as session:
        return list(
            session.execute(
                select(FitChefSupportOutcomeEvent).order_by(
                    FitChefSupportOutcomeEvent.subject_id.asc(),
                    FitChefSupportOutcomeEvent.client_event_id.asc(),
                )
            )
            .scalars()
            .all()
        )


def _request_from_chunks(chunks: list[bytes], *, content_type: str = "application/json") -> Request:
    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]

    async def receive() -> dict[str, object]:
        if messages:
            return messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": _URL,
            "raw_path": _URL.encode("ascii"),
            "query_string": b"",
            "headers": [(b"content-type", content_type.encode("ascii"))],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        },
        receive,
    )


def _parse_chunks(chunks: list[bytes]) -> FitChefSupportOutcomeRequest:
    return asyncio.run(
        fitchef_router._parse_fitchef_support_outcome_request(_request_from_chunks(chunks))
    )


def test_outcome_route_records_minimal_response_and_canonical_target(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
) -> None:
    response = client.post(_URL, json=_VALID_PAYLOAD, headers=pro_headers)

    assert response.status_code == 200
    assert _json_body(response) == {
        "schema_version": "fitchef_support_outcome_v1",
        "state": "recorded",
    }
    rows = _rows()
    assert len(rows) == 1
    row = rows[0]
    assert row.subject_id == derive_subject_id_from_api_key(TEST_KEY_PRO)
    assert row.target_surface == "pro_daily_plate"
    assert row.support_need == "daily_structure"
    assert row.outcome == "acknowledged"
    assert row.created_at is not None


def test_outcome_route_replays_exact_material_and_rejects_divergence(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
) -> None:
    first = client.post(_URL, json=_VALID_PAYLOAD, headers=pro_headers)
    replay = client.post(_URL, json=_VALID_PAYLOAD, headers=pro_headers)
    divergent = client.post(
        _URL,
        json={**_VALID_PAYLOAD, "outcome": "dismissed"},
        headers=pro_headers,
    )

    assert first.status_code == replay.status_code == 200
    assert _json_body(first)["state"] == "recorded"
    assert _json_body(replay)["state"] == "replayed"
    assert divergent.status_code == 409
    assert _json_body(divergent) == {"detail": "fitchef_support_outcome_idempotency_conflict"}
    assert len(_rows()) == 1
    assert _rows()[0].outcome == "acknowledged"


def test_same_event_id_is_isolated_across_subjects(
    client: TestClient,
    pro_headers: dict[str, str],
    vip_headers: dict[str, str],
    outcome_enabled: None,
) -> None:
    first = client.post(_URL, json=_VALID_PAYLOAD, headers=pro_headers)
    second = client.post(
        _URL,
        json={**_VALID_PAYLOAD, "support_need": "weekly_structure"},
        headers=vip_headers,
    )

    assert first.status_code == second.status_code == 200
    rows = _rows()
    assert len(rows) == 2
    assert {row.subject_id for row in rows} == {
        derive_subject_id_from_api_key(TEST_KEY_PRO),
        derive_subject_id_from_api_key("test_vip_key"),
    }
    assert {row.target_surface for row in rows} == {"pro_daily_plate", "pro_weekly_plan"}


def test_missing_auth_precedes_flag_and_unread_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_FITCHEF_SUPPORT_OUTCOME_LEDGER", "false")

    async def forbidden_parser(_request: Request) -> FitChefSupportOutcomeRequest:
        pytest.fail("body parser must remain unread before authentication")

    monkeypatch.setattr(fitchef_router, "_parse_fitchef_support_outcome_request", forbidden_parser)
    response = client.post(_URL, content="{", headers={"Content-Type": "text/plain"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"


def test_flag_precedes_parser_and_store(
    client: TestClient,
    pro_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_FITCHEF_SUPPORT_OUTCOME_LEDGER", "false")

    async def forbidden_parser(_request: Request) -> FitChefSupportOutcomeRequest:
        pytest.fail("disabled feature must not parse the body")

    monkeypatch.setattr(fitchef_router, "_parse_fitchef_support_outcome_request", forbidden_parser)
    response = client.post(_URL, content="{", headers=pro_headers)

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "FEATURE_FITCHEF_SUPPORT_OUTCOME_LEDGER is disabled"}


def test_invalid_header_dominates_valid_cookie(
    client: TestClient,
    outcome_enabled: None,
) -> None:
    issued = issue_web_session(api_key=TEST_KEY_PRO, tier="PRO", ttl_seconds=300)
    client.cookies.set(WEB_SESSION_COOKIE_NAME, issued.token, path="/")

    response = client.post(
        _URL,
        json=_VALID_PAYLOAD,
        headers={"X-API-Key": "invalid"},
    )

    assert response.status_code == 403
    assert _json_body(response) == {"detail": "API key does not have PRO tier access"}
    assert _rows() == []


@pytest.mark.parametrize("tier", ("PRO", "VIP"))
def test_paid_cookie_fallback_records(
    client: TestClient,
    tier: str,
    outcome_enabled: None,
) -> None:
    api_key = TEST_KEY_PRO if tier == "PRO" else "test_vip_key"
    issued = issue_web_session(api_key=api_key, tier=tier, ttl_seconds=300)
    client.cookies.set(WEB_SESSION_COOKIE_NAME, issued.token, path="/")

    response = client.post(_URL, json=_VALID_PAYLOAD)

    assert response.status_code == 200
    assert len(_rows()) == 1


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {**_VALID_PAYLOAD, "schema_version": "fitchef_support_outcome_v2"},
        {**_VALID_PAYLOAD, "support_need": "other"},
        {**_VALID_PAYLOAD, "outcome": "clicked"},
        {**_VALID_PAYLOAD, "client_event_id": "short"},
        {**_VALID_PAYLOAD, "client_event_id": "a" * 129},
        {**_VALID_PAYLOAD, "client_event_id": " invalid-event-01"},
        {**_VALID_PAYLOAD, "client_event_id": 123},
        {**_VALID_PAYLOAD, "support_need": True},
        {**_VALID_PAYLOAD, "subject_id": 7},
        {**_VALID_PAYLOAD, "target_surface": "pro_daily_plate"},
        {**_VALID_PAYLOAD, "metadata": {}},
        {**_VALID_PAYLOAD, "free_text": "private"},
    ),
)
def test_strict_payload_rejections_are_stable_422(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
    payload: dict[str, object],
) -> None:
    response = client.post(_URL, json=payload, headers=pro_headers)

    assert response.status_code == 422
    assert _json_body(response) == {"detail": "fitchef_support_outcome_validation_error"}
    assert _rows() == []


@pytest.mark.parametrize(
    "forbidden_field",
    (
        "subject_id",
        "user_id",
        "target_surface",
        "plan_id",
        "goal",
        "free_text",
        "email",
        "weight",
        "height",
        "bmi",
        "health_condition",
        "raw_error",
        "timestamp",
        "created_at",
        "metadata",
        "payload",
    ),
)
def test_every_forbidden_field_is_rejected_not_ignored(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
    forbidden_field: str,
) -> None:
    response = client.post(
        _URL,
        json={**_VALID_PAYLOAD, forbidden_field: "forbidden"},
        headers=pro_headers,
    )

    assert response.status_code == 422
    assert _json_body(response) == {"detail": "fitchef_support_outcome_validation_error"}


@pytest.mark.parametrize(
    ("content_type", "body"),
    (
        ("text/plain", json.dumps(_VALID_PAYLOAD)),
        (" application/json", json.dumps(_VALID_PAYLOAD)),
        ("application/problem+json", json.dumps(_VALID_PAYLOAD)),
        ("application/json ; charset=utf-8", json.dumps(_VALID_PAYLOAD)),
        ("application/json", "{"),
        ("application/json", "[]"),
        ("application/json", "null"),
        ("application/json", "NaN"),
    ),
)
def test_media_type_malformed_and_non_object_rejections(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
    content_type: str,
    body: str,
) -> None:
    response = client.post(
        _URL,
        content=body,
        headers={**pro_headers, "Content-Type": content_type},
    )

    assert response.status_code == 422
    assert _json_body(response) == {"detail": "fitchef_support_outcome_validation_error"}


def test_parameterized_json_media_type_is_accepted(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
) -> None:
    response = client.post(
        _URL,
        content=json.dumps(_VALID_PAYLOAD),
        headers={**pro_headers, "Content-Type": "Application/JSON;charset=utf-8"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "body",
    (
        b'{"schema_version":"fitchef_support_outcome_v1",'
        b'"support_need":"daily_structure","support_need":"weekly_structure",'
        b'"outcome":"acknowledged","client_event_id":"outcome-event-0002"}',
        b'{"schema_version":"fitchef_support_outcome_v1",'
        b'"support_need":"daily_structure","outcome":"acknowledged",'
        b'"client_event_id":"outcome-event-0003","metadata":{"x":1,"x":2}}',
        b'{"schema_version":"fitchef_support_outcome_v1",'
        b'"support_need":"daily_structure","support\\u005fneed":"weekly_structure",'
        b'"outcome":"acknowledged","client_event_id":"outcome-event-0004"}',
    ),
)
def test_duplicate_keys_at_all_levels_and_escaped_aliases_are_rejected(body: bytes) -> None:
    with pytest.raises(HTTPException) as captured:
        _parse_chunks([body])

    assert captured.value.status_code == 422
    assert captured.value.detail == "fitchef_support_outcome_validation_error"


def test_streamed_body_accepts_4096_and_rejects_4097_bytes() -> None:
    exact = asyncio.run(
        fitchef_router._read_fitchef_support_outcome_body(
            _request_from_chunks([b"a" * 2048, b"b" * 2048])
        )
    )
    assert len(exact) == 4096

    with pytest.raises(HTTPException) as captured:
        asyncio.run(
            fitchef_router._read_fitchef_support_outcome_body(
                _request_from_chunks([b"a" * 4096, b"b"])
            )
        )
    assert captured.value.status_code == 422


def test_lying_content_length_cannot_bypass_actual_stream_cap(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
) -> None:
    response = client.post(
        _URL,
        content=b"{" + b" " * 4096,
        headers={**pro_headers, "Content-Type": "application/json", "Content-Length": "1"},
    )

    assert response.status_code == 422


def test_multichunk_valid_body_and_depth_boundary() -> None:
    encoded = json.dumps(_VALID_PAYLOAD, separators=(",", ":")).encode("utf-8")
    payload = _parse_chunks([encoded[:11], encoded[11:37], encoded[37:]])
    assert payload.client_event_id == "outcome-event-0001"

    depth_four = {"a": {"b": {"c": {"d": 1}}}}
    depth_five = {"a": {"b": {"c": {"d": {"e": 1}}}}}
    assert fitchef_router._json_structural_depth(depth_four) == 4
    assert fitchef_router._json_structural_depth(depth_five) == 5


def test_exact_constraint_classifier_is_fail_closed() -> None:
    class Diagnostic:
        constraint_name = FITCHEF_SUPPORT_OUTCOME_UNIQUE_CONSTRAINT

    class PostgresOriginal(Exception):
        diag = Diagnostic()

    postgres = IntegrityError("insert", {}, PostgresOriginal())
    sqlite = IntegrityError(
        "insert",
        {},
        sqlite3.IntegrityError(FITCHEF_SUPPORT_OUTCOME_SQLITE_UNIQUE_SIGNATURE),
    )
    wrong_class = IntegrityError(
        "insert",
        {},
        RuntimeError(FITCHEF_SUPPORT_OUTCOME_SQLITE_UNIQUE_SIGNATURE),
    )
    wrong_columns = IntegrityError(
        "insert",
        {},
        sqlite3.IntegrityError(
            "UNIQUE constraint failed: fitchef_support_outcome_events.client_event_id"
        ),
    )

    assert outcome_service._is_exact_idempotency_violation(postgres) is True
    assert outcome_service._is_exact_idempotency_violation(sqlite) is True
    assert outcome_service._is_exact_idempotency_violation(wrong_class) is False
    assert outcome_service._is_exact_idempotency_violation(wrong_columns) is False


def test_post_rollback_winner_read_rebinds_rls(monkeypatch: pytest.MonkeyPatch) -> None:
    record = FitChefSupportOutcomeRecord(
        schema_version="fitchef_support_outcome_v1",
        support_need="daily_structure",
        target_surface="pro_daily_plate",
        outcome="acknowledged",
        client_event_id="outcome-race-rebind",
    )
    winner = FitChefSupportOutcomeEvent(
        id="winner",
        subject_id=17,
        schema_version=record.schema_version,
        support_need=record.support_need,
        target_surface=record.target_surface,
        outcome=record.outcome,
        client_event_id=record.client_event_id,
    )
    trace: list[str] = []

    class FakeSession:
        def add(self, _row: object) -> None:
            trace.append("add")

        def commit(self) -> None:
            trace.append("commit")
            raise IntegrityError(
                "insert",
                {},
                sqlite3.IntegrityError(FITCHEF_SUPPORT_OUTCOME_SQLITE_UNIQUE_SIGNATURE),
            )

        def rollback(self) -> None:
            trace.append("rollback")

        def close(self) -> None:
            trace.append("close")

    existing = iter((None, winner))
    monkeypatch.setattr(
        outcome_service,
        "apply_user_rls_context",
        lambda _session, *, user_id: trace.append(f"rls:{user_id}"),
    )
    monkeypatch.setattr(
        outcome_service,
        "_fetch_existing",
        lambda *_args, **_kwargs: next(existing),
    )

    state = record_fitchef_support_outcome(
        subject_id=17,
        record=record,
        session_factory=lambda: cast(Session, FakeSession()),
    )

    assert state == "replayed"
    assert trace == ["rls:17", "add", "commit", "rollback", "rls:17", "close"]


def test_unrelated_integrity_error_is_sanitized(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = "credential-params-/srv/private.sqlite"

    class FakeSession:
        def execute(self, _statement: object) -> object:
            raise IntegrityError("select", {"secret": sentinel}, RuntimeError(sentinel))

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

        def get_bind(self) -> object:
            class Dialect:
                name = "sqlite"

            class Bind:
                dialect = Dialect()

            return Bind()

    record = FitChefSupportOutcomeRecord(
        schema_version="fitchef_support_outcome_v1",
        support_need="daily_structure",
        target_surface="pro_daily_plate",
        outcome="acknowledged",
        client_event_id="outcome-store-error",
    )
    with caplog.at_level("ERROR", logger=outcome_service.__name__):
        with pytest.raises(FitChefSupportOutcomeStoreUnavailableError):
            record_fitchef_support_outcome(
                subject_id=18,
                record=record,
                session_factory=lambda: cast(Session, FakeSession()),
            )

    assert "FitChef support outcome store unavailable" in caplog.text
    assert sentinel not in caplog.text


@pytest.mark.parametrize("bootstrap_stage", ("factory_resolution", "session_construction"))
def test_factory_and_session_bootstrap_failures_are_sanitized_in_service(
    bootstrap_stage: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = f"{bootstrap_stage}-private-/srv/fitchef.sqlite"
    record = FitChefSupportOutcomeRecord(
        schema_version="fitchef_support_outcome_v1",
        support_need="daily_structure",
        target_surface="pro_daily_plate",
        outcome="acknowledged",
        client_event_id="outcome-bootstrap-error",
    )

    def fail_bootstrap() -> object:
        raise RuntimeError(sentinel)

    if bootstrap_stage == "factory_resolution":
        monkeypatch.setattr(outcome_service, "get_session_factory", fail_bootstrap)
        injected_factory = None
    else:
        injected_factory = cast(Callable[[], Session], fail_bootstrap)

    with caplog.at_level("ERROR", logger=outcome_service.__name__):
        with pytest.raises(FitChefSupportOutcomeStoreUnavailableError):
            record_fitchef_support_outcome(
                subject_id=19,
                record=record,
                session_factory=injected_factory,
            )

    assert "FitChef support outcome store unavailable" in caplog.text
    assert sentinel not in caplog.text


@pytest.mark.parametrize("bootstrap_stage", ("factory_resolution", "session_construction"))
def test_factory_and_session_bootstrap_failures_are_stable_503_at_route(
    bootstrap_stage: str,
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = f"{bootstrap_stage}-credential-/private/store.sqlite"

    def fail_bootstrap() -> object:
        raise RuntimeError(sentinel)

    if bootstrap_stage == "factory_resolution":
        monkeypatch.setattr(outcome_service, "get_session_factory", fail_bootstrap)
    else:
        monkeypatch.setattr(outcome_service, "get_session_factory", lambda: fail_bootstrap)

    with caplog.at_level("ERROR", logger=outcome_service.__name__):
        response = client.post(_URL, json=_VALID_PAYLOAD, headers=pro_headers)

    assert response.status_code == 503
    assert _json_body(response) == {"detail": "fitchef_support_outcome_store_unavailable"}
    assert sentinel.encode("utf-8") not in response.content
    assert sentinel not in caplog.text


def test_route_sanitizes_store_failure_and_metrics_only_classify_conflict(
    client: TestClient,
    pro_headers: dict[str, str],
    outcome_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_results: list[str] = []
    monkeypatch.setattr(
        fitchef_router,
        "record_fitchef_support_outcome_write",
        lambda **labels: observed_results.append(cast(str, labels["result"])),
    )

    def store_unavailable(**_kwargs: object) -> str:
        raise FitChefSupportOutcomeStoreUnavailableError("private-db-/srv/secret")

    monkeypatch.setattr(outcome_service, "record_fitchef_support_outcome", store_unavailable)
    unavailable = client.post(_URL, json=_VALID_PAYLOAD, headers=pro_headers)
    assert unavailable.status_code == 503
    assert _json_body(unavailable) == {"detail": "fitchef_support_outcome_store_unavailable"}
    assert b"private-db" not in unavailable.content
    assert observed_results == []

    def conflict(**_kwargs: object) -> str:
        raise FitChefSupportOutcomeConflictError

    monkeypatch.setattr(outcome_service, "record_fitchef_support_outcome", conflict)
    rejected = client.post(_URL, json=_VALID_PAYLOAD, headers=pro_headers)
    assert rejected.status_code == 409
    assert observed_results == ["rejected"]


def test_metric_vocabulary_is_exact_and_failure_is_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert (
        len(
            metrics.FITCHEF_SUPPORT_NEED_LABELS
            | metrics.FITCHEF_SUPPORT_OUTCOME_LABELS
            | metrics.FITCHEF_SUPPORT_OUTCOME_RESULT_LABELS
        )
        == 7
    )
    assert (
        len(metrics.FITCHEF_SUPPORT_NEED_LABELS)
        * len(metrics.FITCHEF_SUPPORT_OUTCOME_LABELS)
        * len(metrics.FITCHEF_SUPPORT_OUTCOME_RESULT_LABELS)
        == 12
    )

    class BrokenCounter:
        def labels(self, **_labels: str) -> object:
            raise RuntimeError("metric backend failed")

    monkeypatch.setattr(metrics, "FITCHEF_SUPPORT_OUTCOME_WRITES_TOTAL", BrokenCounter())
    metrics.record_fitchef_support_outcome_write(
        support_need="daily_structure",
        outcome="acknowledged",
        result="recorded",
    )
    metrics.record_fitchef_support_outcome_write(
        support_need="unknown",
        outcome="acknowledged",
        result="recorded",
    )


def test_source_router_is_one_public_mutating_pro_route() -> None:
    candidates = tuple(
        iter_effective_route_candidates(fitchef_router.support_outcome_router.routes)
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    carrier = getattr(candidate, "original_route", candidate)
    assert route_path(candidate) == _URL
    assert route_methods(candidate) == {"POST"}
    assert carrier.include_in_schema is True
    assert [dependency.call for dependency in carrier.dependant.dependencies] == [require_pro_tier]
    assert "{" not in carrier.path


def test_openapi_import_path_does_not_load_outcome_orm_or_service() -> None:
    script = """
import json
import sys
from app.main import app
app.openapi()
print(json.dumps({
    "orm": "app.models.fitchef_support_outcomes" in sys.modules,
    "service": "app.services.fitchef_support_outcomes" in sys.modules,
}))
"""
    env = dict(os.environ)
    env.update({"TESTING": "true", "APP_ENV": "test", "ENVIRONMENT": "test"})
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload == {"orm": False, "service": False}


@pytest.mark.parametrize("initialization_mode", ("sync", "async"))
def test_canonical_db_init_registers_and_creates_outcome_table_fresh(
    initialization_mode: str,
) -> None:
    script = f"""
import asyncio
import json
import os
import sys
import tempfile

with tempfile.TemporaryDirectory() as directory:
    os.environ["DATABASE_URL"] = "sqlite:///" + directory + "/canonical-init.sqlite3"
    os.environ["APP_ENV"] = "test"
    os.environ["ENVIRONMENT"] = "test"
    os.environ.pop("DATABASE_ASYNC_URL", None)
    os.environ.pop("DATABASE_USE_ASYNC", None)

    import core.db as core_db
    from sqlalchemy import inspect

    before = {{
        "model": "app.models.fitchef_support_outcomes" in sys.modules,
        "service": "app.services.fitchef_support_outcomes" in sys.modules,
    }}
    if {initialization_mode!r} == "sync":
        engine = core_db.init_db()
    else:
        asyncio.run(core_db.init_db_async())
        engine = core_db._get_raw_engine()

    print(json.dumps({{
        "before": before,
        "model_loaded": "app.models.fitchef_support_outcomes" in sys.modules,
        "service_loaded": "app.services.fitchef_support_outcomes" in sys.modules,
        "metadata": "fitchef_support_outcome_events" in core_db.Base.metadata.tables,
        "physical": inspect(engine).has_table("fitchef_support_outcome_events"),
    }}, sort_keys=True))
"""
    env = dict(os.environ)
    env.update({"TESTING": "true", "APP_ENV": "test", "ENVIRONMENT": "test"})
    env.pop("DATABASE_ASYNC_URL", None)
    env.pop("DATABASE_USE_ASYNC", None)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload == {
        "before": {"model": False, "service": False},
        "metadata": True,
        "model_loaded": True,
        "physical": True,
        "service_loaded": False,
    }


def test_migration_freezes_rls_and_reversible_ownership() -> None:
    migration = Path("alembic/versions/202608270001_add_fitchef_support_outcomes.py").read_text(
        encoding="utf-8"
    )

    assert "ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY" in migration
    assert "ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY" in migration
    assert "NULLIF(current_setting('app.current_user_id', true), '')::bigint" in migration
    assert migration.count("NULLIF(current_setting('app.current_user_id', true), '')::bigint") == 2
    assert "DROP POLICY IF EXISTS {_POLICY} ON {_TABLE}" in migration
    assert "ALTER TABLE {_TABLE} NO FORCE ROW LEVEL SECURITY" in migration
    assert "ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY" in migration
    assert "op.drop_table(_TABLE)" in migration


def test_unauthenticated_calls_do_not_consume_scoped_rate_limit() -> None:
    script = """
from app.main import app
from tests._client import open_test_client
payload = {
    "schema_version": "fitchef_support_outcome_v1",
    "support_need": "daily_structure",
    "outcome": "acknowledged",
    "client_event_id": "rate-event-0000001",
}
with open_test_client(app) as client:
    unauthenticated = client.post(
        "/api/v1/pro/fitchef/recommend/outcome",
        json=payload,
    ).status_code
    authenticated = [
        client.post(
            "/api/v1/pro/fitchef/recommend/outcome",
            json=payload,
            headers={"X-API-Key": "test_pro_key"},
        ).status_code
        for _ in range(3)
    ]
print({"unauthenticated": unauthenticated, "authenticated": authenticated})
"""
    env = dict(os.environ)
    env.update(
        {
            "TESTING": "true",
            "RATE_LIMITING_IN_TESTS": "true",
            "RATE_LIMIT_FITCHEF_SUPPORT_OUTCOME": "2/minute",
            "FEATURE_FITCHEF_SUPPORT_OUTCOME_LEDGER": "false",
            "APP_ENV": "test",
            "ENVIRONMENT": "test",
            "SERVER_SALT": "Aa1!" * 16,
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip().splitlines()[-1] == (
        "{'unauthenticated': 401, 'authenticated': [503, 503, 429]}"
    )


def test_two_session_identical_and_divergent_races(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_fetch = outcome_service._fetch_existing

    def run_race(
        records: tuple[FitChefSupportOutcomeRecord, FitChefSupportOutcomeRecord],
    ) -> list[str]:
        barrier = threading.Barrier(2)
        lock = threading.Lock()
        initial_missing_reads = 0

        def synchronized_fetch(
            *args: object, **kwargs: object
        ) -> FitChefSupportOutcomeEvent | None:
            nonlocal initial_missing_reads
            row = real_fetch(*args, **kwargs)
            should_wait = False
            if row is None:
                with lock:
                    if initial_missing_reads < 2:
                        initial_missing_reads += 1
                        should_wait = True
            if should_wait:
                barrier.wait(timeout=5)
            return row

        monkeypatch.setattr(outcome_service, "_fetch_existing", synchronized_fetch)

        def invoke(record: FitChefSupportOutcomeRecord) -> str:
            try:
                return record_fitchef_support_outcome(subject_id=404, record=record)
            except FitChefSupportOutcomeConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(invoke, records))

    identical = FitChefSupportOutcomeRecord(
        schema_version="fitchef_support_outcome_v1",
        support_need="daily_structure",
        target_surface="pro_daily_plate",
        outcome="acknowledged",
        client_event_id="race-identical-0001",
    )
    assert sorted(run_race((identical, identical))) == ["recorded", "replayed"]

    first = FitChefSupportOutcomeRecord(
        schema_version="fitchef_support_outcome_v1",
        support_need="daily_structure",
        target_surface="pro_daily_plate",
        outcome="acknowledged",
        client_event_id="race-divergent-0001",
    )
    second = FitChefSupportOutcomeRecord(
        schema_version="fitchef_support_outcome_v1",
        support_need="daily_structure",
        target_surface="pro_daily_plate",
        outcome="dismissed",
        client_event_id="race-divergent-0001",
    )
    assert sorted(run_race((first, second))) == ["conflict", "recorded"]

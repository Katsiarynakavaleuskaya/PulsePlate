"""Integration tests for nutrition log idempotency and applied tracking."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.middleware.api_tiers import derive_subject_id_from_api_key
from app.models import JSONEncodedDict, NutritionEvent
from app.routers import nutrition_log
from app.schemas.nutrition_log import MealLogRequest
from core.bayes.adherence_service import AdherenceResult
from core.db import get_session, session_scope


@pytest.fixture(autouse=True)
def _allow_anonymous_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable anonymous API keys for all tests in this module.

    This fixture runs before test_client is created, ensuring ALLOW_ANONYMOUS_API_KEYS
    is set during app initialization and middleware configuration.
    """
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")


def _headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key}


class _BrokenSession:
    def add(self, _obj: object) -> None:
        return None

    def commit(self) -> None:
        raise IntegrityError("boom", params=None, orig=Exception("boom"))

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def _broken_session_dependency() -> Generator[_BrokenSession, None, None]:
    session = _BrokenSession()
    try:
        yield session
    finally:
        session.close()


class _Diag:
    constraint_name = nutrition_log.IDEMP_CONSTRAINT


class _IdempotentOrig:
    diag = _Diag()


class _IdempotentSession:
    def add(self, _obj: object) -> None:
        return None

    def commit(self) -> None:
        raise IntegrityError("boom", params=None, orig=_IdempotentOrig())

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def _idempotent_session_dependency() -> Generator[_IdempotentSession, None, None]:
    session = _IdempotentSession()
    try:
        yield session
    finally:
        session.close()


class _ServiceStub:
    def get(self, user_id: int) -> AdherenceResult:
        return AdherenceResult(
            user_id=user_id,
            analyzer_key="v1:adherence",
            alpha=1.0,
            beta=1.0,
            n=0,
            risk_slip=0.5,
            confidence=0.35,
            needs_more_data=True,
        )


def test_meal_log_idempotent_retry(test_client: TestClient) -> None:
    api_key = "test_key_meal_idem_retry"
    client_event_id = "meal-idem-retry-1"
    payload = {"log_type": "meal_logged", "client_event_id": client_event_id}

    resp_first = test_client.post(
        "/api/v1/pro/nutrition/meal-log", json=payload, headers=_headers(api_key)
    )
    assert resp_first.status_code == 200

    resp_second = test_client.post(
        "/api/v1/pro/nutrition/meal-log", json=payload, headers=_headers(api_key)
    )
    assert resp_second.status_code == 200
    assert resp_second.json()["n"] == resp_first.json()["n"]

    subject_id = derive_subject_id_from_api_key(api_key)
    with session_scope() as session:
        events = session.scalars(
            select(NutritionEvent).where(
                NutritionEvent.subject_id == subject_id,
                NutritionEvent.source == "meal_log",
                NutritionEvent.client_event_id == client_event_id,
            )
        ).all()
        payload_data = events[0].payload if events else {}

    assert len(events) == 1
    assert payload_data is not None
    assert payload_data.get("applied") is True
    assert payload_data.get("log_type") == "meal_logged"


def test_meal_log_replay_applies_pending_event(test_client: TestClient) -> None:
    api_key = "test_key_meal_pending"
    subject_id = derive_subject_id_from_api_key(api_key)
    day = datetime.now(timezone.utc).date()
    client_event_id = "meal-idem-pending-1"

    with session_scope() as session:
        session.add(
            NutritionEvent(
                subject_id=subject_id,
                day=day,
                source="meal_log",
                event_type="meal_logged",
                client_event_id=client_event_id,
                payload={
                    "log_type": "meal_logged",
                    "adherence_score": None,
                    "applied": False,
                },
            )
        )
    # session_scope() commits on exit

    payload = {"log_type": "meal_logged", "client_event_id": client_event_id}
    resp = test_client.post(
        "/api/v1/pro/nutrition/meal-log", json=payload, headers=_headers(api_key)
    )
    assert resp.status_code == 200
    assert resp.json()["n"] >= 1

    with session_scope() as session:
        event = session.scalar(
            select(NutritionEvent).where(
                NutritionEvent.subject_id == subject_id,
                NutritionEvent.source == "meal_log",
                NutritionEvent.client_event_id == client_event_id,
            )
        )
        payload_data = event.payload if event is not None else {}

    assert event is not None
    assert payload_data is not None
    assert payload_data.get("applied") is True
    assert payload_data.get("log_type") == "meal_logged"


def test_meal_log_integrity_error_propagates(test_client: TestClient) -> None:
    api_key = "test_key_meal_integrity"

    # NOTE: Import inside test to avoid pytest-xdist module/registry side effects during collection.
    import app

    assert app.app is not None
    app.app.dependency_overrides[get_session] = _broken_session_dependency
    app.app.dependency_overrides[nutrition_log.get_adherence_service] = lambda: object()
    try:
        with pytest.raises(IntegrityError):
            test_client.post(
                "/api/v1/pro/nutrition/meal-log",
                json={"log_type": "meal_logged"},
                headers=_headers(api_key),
            )
    finally:
        app.app.dependency_overrides.pop(get_session, None)
        app.app.dependency_overrides.pop(nutrition_log.get_adherence_service, None)


def test_meal_log_idempotent_missing_event_returns_state(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    api_key = "test_key_meal_missing"
    client_event_id = "meal-idem-missing-1"

    import app

    app.app.dependency_overrides[get_session] = _idempotent_session_dependency
    app.app.dependency_overrides[nutrition_log.get_adherence_service] = _ServiceStub
    monkeypatch.setattr(nutrition_log, "_fetch_existing_event", lambda *args, **kwargs: None)
    try:
        resp = test_client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "meal_logged", "client_event_id": client_event_id},
            headers=_headers(api_key),
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == derive_subject_id_from_api_key(api_key)
    finally:
        app.app.dependency_overrides.pop(get_session, None)
        app.app.dependency_overrides.pop(nutrition_log.get_adherence_service, None)


def test_day_close_idempotent(test_client: TestClient) -> None:
    api_key = "test_key_day_close"
    day = date(2025, 12, 20)
    payload = {"day": day.isoformat(), "adherence_score": 1.0}

    resp_first = test_client.post(
        "/api/v1/pro/nutrition/day-close", json=payload, headers=_headers(api_key)
    )
    assert resp_first.status_code == 200

    resp_second = test_client.post(
        "/api/v1/pro/nutrition/day-close", json=payload, headers=_headers(api_key)
    )
    assert resp_second.status_code == 200
    assert resp_second.json()["n"] == resp_first.json()["n"]

    subject_id = derive_subject_id_from_api_key(api_key)
    with session_scope() as session:
        events = session.scalars(
            select(NutritionEvent).where(
                NutritionEvent.subject_id == subject_id,
                NutritionEvent.day == day,
                NutritionEvent.source == "day_close",
            )
        ).all()
        payload_data = events[0].payload if events else {}

    assert len(events) == 1
    assert payload_data is not None
    assert payload_data.get("applied") is True


def test_day_close_integrity_error_propagates(test_client: TestClient) -> None:
    api_key = "test_key_day_close_integrity"
    day = date(2025, 12, 21)

    import app

    app.app.dependency_overrides[get_session] = _broken_session_dependency
    app.app.dependency_overrides[nutrition_log.get_adherence_service] = _ServiceStub
    try:
        with pytest.raises(IntegrityError):
            test_client.post(
                "/api/v1/pro/nutrition/day-close",
                json={"day": day.isoformat(), "adherence_score": 0.9},
                headers=_headers(api_key),
            )
    finally:
        app.app.dependency_overrides.pop(get_session, None)
        app.app.dependency_overrides.pop(nutrition_log.get_adherence_service, None)


def test_day_close_idempotent_missing_event_returns_state(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    api_key = "test_key_day_close_missing"
    day = date(2025, 12, 22)

    import app

    app.app.dependency_overrides[get_session] = _idempotent_session_dependency
    app.app.dependency_overrides[nutrition_log.get_adherence_service] = _ServiceStub
    monkeypatch.setattr(nutrition_log, "_fetch_existing_event", lambda *args, **kwargs: None)
    try:
        resp = test_client.post(
            "/api/v1/pro/nutrition/day-close",
            json={"day": day.isoformat(), "adherence_score": 1.0},
            headers=_headers(api_key),
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == derive_subject_id_from_api_key(api_key)
    finally:
        app.app.dependency_overrides.pop(get_session, None)
        app.app.dependency_overrides.pop(nutrition_log.get_adherence_service, None)


def test_idempotency_violation_checks() -> None:
    diag_error = IntegrityError("boom", params=None, orig=_IdempotentOrig())
    assert nutrition_log._is_idempotency_violation(diag_error) is True

    msg_error = IntegrityError("boom", params=None, orig=Exception(nutrition_log.IDEMP_CONSTRAINT))
    assert nutrition_log._is_idempotency_violation(msg_error) is True


def test_mark_event_applied_is_noop_when_already_applied() -> None:
    class _NoCommitSession:
        def add(self, _obj: object) -> None:
            raise AssertionError("unexpected add")

        def commit(self) -> None:
            raise AssertionError("unexpected commit")

    event = NutritionEvent(
        subject_id=1,
        day=date(2025, 12, 23),
        source="meal_log",
        event_type="meal_logged",
        client_event_id="already-applied",
        payload={"applied": True},
    )
    nutrition_log._mark_event_applied(_NoCommitSession(), event)


def test_json_encoded_dict_handles_none() -> None:
    codec = JSONEncodedDict()
    assert codec.process_bind_param(None, None) is None
    assert codec.process_result_value(None, None) is None


def test_meal_log_slip_type(test_client: TestClient) -> None:
    """Cover slip log_type branch (lines 104-105)."""
    api_key = "test_key_meal_slip"
    payload = {"log_type": "slip"}
    resp = test_client.post(
        "/api/v1/pro/nutrition/meal-log", json=payload, headers=_headers(api_key)
    )
    assert resp.status_code == 200
    assert resp.json()["n"] >= 1


def test_meal_log_partial_type(test_client: TestClient) -> None:
    """Cover partial log_type branch with adherence_score (lines 107-113)."""
    api_key = "test_key_meal_partial"
    payload = {"log_type": "partial", "adherence_score": 0.7}
    resp = test_client.post(
        "/api/v1/pro/nutrition/meal-log", json=payload, headers=_headers(api_key)
    )
    assert resp.status_code == 200
    assert resp.json()["n"] >= 1


def test_meal_log_partial_missing_score_raises_runtime_error() -> None:
    payload = MealLogRequest.model_construct(log_type="partial", adherence_score=None)
    with pytest.raises(RuntimeError):
        nutrition_log._event_from_meal_log(payload)


def test_day_close_slip_weight(test_client: TestClient) -> None:
    """Cover day-close with score < 1.0 branch (lines 127-128)."""
    api_key = "test_key_day_close_slip"
    day = date(2025, 12, 24)
    payload = {"day": day.isoformat(), "adherence_score": 0.6}
    resp = test_client.post(
        "/api/v1/pro/nutrition/day-close", json=payload, headers=_headers(api_key)
    )
    assert resp.status_code == 200
    assert resp.json()["n"] >= 1

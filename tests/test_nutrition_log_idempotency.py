"""Integration tests for nutrition log idempotency and applied tracking."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.middleware.api_tiers import derive_subject_id_from_api_key
from app.models.events import NutritionEvent
from app.routers import nutrition_log
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
        session.commit()  # Ensure pending event is committed before API call

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


def test_meal_log_non_idempotency_integrity_error_propagates(test_client: TestClient) -> None:
    api_key = "test_key_meal_integrity"

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

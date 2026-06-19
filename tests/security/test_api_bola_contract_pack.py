from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.middleware.api_tiers import derive_subject_id_from_api_key
from app.models import NutritionEvent, RAGFeedback
from core.db import session_scope


def _headers(credential: str) -> dict[str, str]:
    return {"X-API-Key": credential}


@pytest.fixture(autouse=True)
def _allow_anonymous_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")


NutritionEventSnapshot = tuple[int, date, dict[str, object] | None]


def _delete_nutrition_events_for(*, source: str, client_event_id: str) -> None:
    with session_scope() as session:
        session.execute(
            delete(NutritionEvent).where(
                NutritionEvent.source == source,
                NutritionEvent.client_event_id == client_event_id,
            )
        )


def _nutrition_events_for(*, source: str, client_event_id: str) -> list[NutritionEventSnapshot]:
    with session_scope() as session:
        events = session.scalars(
            select(NutritionEvent)
            .where(
                NutritionEvent.source == source,
                NutritionEvent.client_event_id == client_event_id,
            )
            .order_by(NutritionEvent.subject_id)
        ).all()
        return [(event.subject_id, event.day, event.payload) for event in events]


def test_meal_log_idempotency_is_scoped_by_authenticated_subject(
    test_client: TestClient,
) -> None:
    first_key = "test_key_meal_cross_subject_a"
    second_key = "test_key_meal_cross_subject_b"
    client_event_id = "meal-cross-subject-shared-id"
    payload = {
        "log_type": "meal_logged",
        "client_event_id": client_event_id,
        "user_id": derive_subject_id_from_api_key(second_key),
        "subject_id": derive_subject_id_from_api_key(second_key),
    }
    _delete_nutrition_events_for(source="meal_log", client_event_id=client_event_id)

    first = test_client.post(
        "/api/v1/pro/nutrition/meal-log",
        json=payload,
        headers=_headers(first_key),
    )
    second = test_client.post(
        "/api/v1/pro/nutrition/meal-log",
        json=payload,
        headers=_headers(second_key),
    )

    assert first.status_code == 200
    assert second.status_code == 200

    first_subject = derive_subject_id_from_api_key(first_key)
    second_subject = derive_subject_id_from_api_key(second_key)
    events = _nutrition_events_for(source="meal_log", client_event_id=client_event_id)

    assert len(events) == 2
    assert {subject_id for subject_id, _, _ in events} == {first_subject, second_subject}
    assert {payload["applied"] for _, _, payload in events if payload is not None} == {True}


def test_day_close_idempotency_is_scoped_by_authenticated_subject(
    test_client: TestClient,
) -> None:
    first_key = "test_key_day_close_cross_subject_a"
    second_key = "test_key_day_close_cross_subject_b"
    close_day = date(2026, 1, 8)
    client_event_id = f"day-close:{close_day.isoformat()}"
    payload = {
        "day": close_day.isoformat(),
        "adherence_score": 1.0,
        "user_id": derive_subject_id_from_api_key(second_key),
        "subject_id": derive_subject_id_from_api_key(second_key),
    }
    _delete_nutrition_events_for(source="day_close", client_event_id=client_event_id)

    first = test_client.post(
        "/api/v1/pro/nutrition/day-close",
        json=payload,
        headers=_headers(first_key),
    )
    second = test_client.post(
        "/api/v1/pro/nutrition/day-close",
        json=payload,
        headers=_headers(second_key),
    )

    assert first.status_code == 200
    assert second.status_code == 200

    first_subject = derive_subject_id_from_api_key(first_key)
    second_subject = derive_subject_id_from_api_key(second_key)
    events = _nutrition_events_for(source="day_close", client_event_id=client_event_id)

    assert len(events) == 2
    assert {subject_id for subject_id, _, _ in events} == {first_subject, second_subject}
    assert {event_day for _, event_day, _ in events} == {close_day}


def test_rag_feedback_ignores_payload_owner_fields_for_persisted_subject(
    test_client: TestClient,
) -> None:
    credential = "feedback-owner-contract-credential"
    injected_user_id = derive_subject_id_from_api_key("feedback-owner-attacker-credential")

    response = test_client.post(
        "/api/v1/feedback/rag",
        json={
            "query": "How do I interpret adherence trends?",
            "user_id": injected_user_id,
            "subject_id": injected_user_id,
        },
        headers=_headers(credential),
    )

    assert response.status_code == 201
    feedback_id = response.json()["id"]
    expected_subject = derive_subject_id_from_api_key(credential)

    with session_scope() as session:
        record = session.get(RAGFeedback, feedback_id)
        assert record is not None
        assert record.user_id == expected_subject
        assert record.user_id != injected_user_id

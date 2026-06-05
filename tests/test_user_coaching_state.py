"""Tests for internal User Coaching State v1 schemas and builder."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import NutritionEvent
from app.schemas.user_coaching_state import (
    AdherenceSnapshot,
    RecentBehaviorSnapshot,
    UserCoachingStateV1,
)
from app.services import coaching_state_builder as builder_module
from app.services.coaching_state_builder import (
    RECENT_EVENT_SCAN_LIMIT,
    build_user_coaching_state,
    to_prompt_safe_context,
)
from core.bayes.adherence_model import AdherenceState
from core.bayes.adherence_service import DEFAULT_ANALYZER_KEY
from core.models import AnalyzerStateModel, User

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sqlite_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=None)


def _reset_subjects(session: Session, *user_ids: int) -> None:
    session.execute(delete(NutritionEvent).where(NutritionEvent.subject_id.in_(user_ids)))
    session.execute(delete(AnalyzerStateModel).where(AnalyzerStateModel.user_id.in_(user_ids)))
    session.execute(delete(User).where(User.id.in_(user_ids)))
    for user_id in user_ids:
        session.add(
            User(
                id=user_id,
                email=f"coaching-state-{user_id}@example.test",
                name=f"Coaching State {user_id}",
            )
        )


def _seed_adherence_state(
    session: Session,
    *,
    user_id: int,
    alpha: float,
    beta: float,
    n: int,
    state_version: int = 1,
) -> dict[str, object]:
    payload = AdherenceState(
        alpha=alpha,
        beta=beta,
        n=n,
        last_event_at="2026-06-01T12:00:00+00:00",
    ).to_payload()
    session.add(
        AnalyzerStateModel(
            user_id=user_id,
            analyzer_key=DEFAULT_ANALYZER_KEY,
            state_schema_version=1,
            state_version=state_version,
            payload=payload,
        )
    )
    return payload


def _event(
    *,
    user_id: int,
    day: date,
    event_type: str,
    created_at: datetime,
    client_event_id: str,
    payload: dict[str, object] | None = None,
) -> NutritionEvent:
    source = "day_close" if event_type == "day_closed" else "meal_log"
    return NutritionEvent(
        subject_id=user_id,
        day=day,
        source=source,
        event_type=event_type,
        client_event_id=client_event_id,
        payload=payload or {},
        created_at=created_at,
    )


def _analyzer_count(session: Session, user_id: int) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(AnalyzerStateModel)
            .where(AnalyzerStateModel.user_id == user_id)
        )
        or 0
    )


def test_builder_returns_default_state_without_creating_analyzer_row(
    configure_sqlite_database: Any,
) -> None:
    user_id = 91_001
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)

    with configure_sqlite_database.session_scope() as session:
        before_count = _analyzer_count(session, user_id)
        state = build_user_coaching_state(user_id=user_id, session=session)
        after_count = _analyzer_count(session, user_id)

    assert before_count == 0
    assert after_count == 0
    assert state.user_id == user_id
    assert state.adherence.alpha == 1.0
    assert state.adherence.beta == 1.0
    assert state.adherence.n == 0
    assert state.adherence.risk_slip == 0.5
    assert state.adherence.confidence == 0.35
    assert state.adherence.needs_more_data is True
    assert state.profile.bmi_value is None
    assert state.profile.goal_profile is None
    assert state.profile.nutrition_profile is None
    assert state.recent_behavior.scanned_event_count == 0
    assert state.next_recommended_scenario == "mascot_insight"
    assert "recent_behavior_unavailable" in state.degrade_reasons

    context = to_prompt_safe_context(state)
    context_json = json.dumps(context.model_dump(mode="json"), sort_keys=True)
    assert "user_id" not in context_json
    assert "analyzer_key" not in context_json
    assert "alpha" not in context_json
    assert "beta" not in context_json
    assert "last_" not in context_json


def test_builder_reads_existing_adherence_state_without_mutating_it(
    configure_sqlite_database: Any,
) -> None:
    user_id = 91_002
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
        expected_payload = _seed_adherence_state(
            session,
            user_id=user_id,
            alpha=8.0,
            beta=2.0,
            n=8,
            state_version=17,
        )

    with configure_sqlite_database.session_scope() as session:
        state = build_user_coaching_state(user_id=user_id, session=session)
        row = session.scalar(
            select(AnalyzerStateModel).where(
                AnalyzerStateModel.user_id == user_id,
                AnalyzerStateModel.analyzer_key == DEFAULT_ANALYZER_KEY,
            )
        )
        assert row is not None
        row_state_version = row.state_version
        row_payload = dict(row.payload)

    assert row_state_version == 17
    assert row_payload == expected_payload
    assert state.adherence.source_status == "loaded"
    assert state.adherence.alpha == 8.0
    assert state.adherence.beta == 2.0
    assert state.adherence.n == 8
    assert state.adherence.risk_slip == pytest.approx(0.2)
    assert state.adherence.confidence == 0.85
    assert state.adherence.needs_more_data is False


def test_builder_rejects_unsupported_analyzer_key_and_degrades_invalid_state(
    configure_sqlite_database: Any,
) -> None:
    unsupported_user_id = 91_003
    invalid_user_id = 91_004
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, unsupported_user_id, invalid_user_id)
        session.add(
            AnalyzerStateModel(
                user_id=invalid_user_id,
                analyzer_key=DEFAULT_ANALYZER_KEY,
                state_schema_version=1,
                state_version=3,
                payload={"alpha": -1.0, "beta": 2.0, "n": 4},
            )
        )

    with configure_sqlite_database.session_scope() as session:
        with pytest.raises(ValueError, match="unsupported analyzer_key"):
            build_user_coaching_state(
                user_id=unsupported_user_id,
                session=session,
                analyzer_key="v1:client-declared",
            )

        state = build_user_coaching_state(user_id=invalid_user_id, session=session)

    assert state.adherence.source_status == "invalid_degraded"
    assert state.adherence.alpha == 1.0
    assert state.adherence.beta == 1.0
    assert state.adherence.n == 0
    assert "adherence_state_invalid_degraded" in state.degrade_reasons


@pytest.mark.parametrize(
    "payload",
    [
        {"alpha": None, "beta": 2.0, "n": 4},
        {"alpha": 2.0, "beta": None, "n": 4},
        {"alpha": 2.0, "beta": 2.0, "n": None},
        {"alpha": "nan", "beta": 2.0, "n": 4},
        {"alpha": 2.0, "beta": "inf", "n": 4},
    ],
)
def test_builder_degrades_malformed_analyzer_payloads(
    configure_sqlite_database: Any,
    payload: dict[str, object],
) -> None:
    user_id = 91_012
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
        session.add(
            AnalyzerStateModel(
                user_id=user_id,
                analyzer_key=DEFAULT_ANALYZER_KEY,
                state_schema_version=1,
                state_version=4,
                payload=payload,
            )
        )

    with configure_sqlite_database.session_scope() as session:
        state = build_user_coaching_state(user_id=user_id, session=session)

    assert state.adherence.source_status == "invalid_degraded"
    assert state.adherence.alpha == 1.0
    assert state.adherence.beta == 1.0
    assert state.adherence.n == 0
    assert "adherence_state_invalid_degraded" in state.degrade_reasons


def test_builder_aggregates_bounded_events_without_raw_text_or_cross_user_leakage(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 91_005
    other_user_id = 91_006
    fixed_now = datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc)
    today = fixed_now.date()
    yesterday = today - timedelta(days=1)
    old_day = today - timedelta(days=8)
    monkeypatch.setattr(builder_module, "_now_utc", lambda: fixed_now)

    raw_payload: dict[str, object] = {
        "free_text": "Ada Lovelace needs therapy and diagnosis now",
        "email": "ada@example.com",
        "credential": "synthetic-credential-leak-sentinel",
        "client_event_id": "client-secret-1",
        "medical_claim": "treat diabetes",
    }
    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id, other_user_id)
        session.add_all(
            [
                _event(
                    user_id=user_id,
                    day=today,
                    event_type="meal_logged",
                    created_at=fixed_now.replace(hour=10),
                    client_event_id="meal-1",
                    payload=raw_payload,
                ),
                _event(
                    user_id=user_id,
                    day=today,
                    event_type="slip",
                    created_at=fixed_now.replace(hour=11),
                    client_event_id="slip-1",
                    payload={"free_text": "raw slip event text"},
                ),
                _event(
                    user_id=user_id,
                    day=yesterday,
                    event_type="partial",
                    created_at=fixed_now.replace(hour=12),
                    client_event_id="partial-1",
                    payload={"adherence_score": 0.7},
                ),
                _event(
                    user_id=user_id,
                    day=today,
                    event_type="day_closed",
                    created_at=fixed_now.replace(hour=13),
                    client_event_id="day-close-slip",
                    payload={"adherence_score": 0.6},
                ),
                _event(
                    user_id=user_id,
                    day=yesterday,
                    event_type="day_closed",
                    created_at=fixed_now.replace(hour=14),
                    client_event_id="day-close-adherent",
                    payload={"adherence_score": 1.0},
                ),
                _event(
                    user_id=user_id,
                    day=old_day,
                    event_type="slip",
                    created_at=fixed_now - timedelta(days=8),
                    client_event_id="old-slip",
                    payload={"free_text": "old event outside window"},
                ),
                _event(
                    user_id=other_user_id,
                    day=today,
                    event_type="slip",
                    created_at=fixed_now.replace(hour=15),
                    client_event_id="other-user-slip",
                    payload={"free_text": "other user event"},
                ),
            ]
        )

    with configure_sqlite_database.session_scope() as session:
        state = build_user_coaching_state(user_id=user_id, session=session)

    behavior = state.recent_behavior
    assert behavior.scanned_event_count == 5
    assert behavior.meal_logged_count_7d == 1
    assert behavior.slip_count_7d == 1
    assert behavior.partial_count_7d == 1
    assert behavior.day_closed_count_7d == 2
    assert behavior.day_close_slip_count_7d == 1
    assert behavior.slip_like_count_7d == 3
    assert behavior.last_meal_logged_at == _sqlite_datetime(fixed_now.replace(hour=10))
    assert behavior.last_slip_at == _sqlite_datetime(fixed_now.replace(hour=11))
    assert behavior.last_partial_at == _sqlite_datetime(fixed_now.replace(hour=12))
    assert behavior.last_slip_like_at == _sqlite_datetime(fixed_now.replace(hour=13))
    assert behavior.last_day_closed_at == _sqlite_datetime(fixed_now.replace(hour=14))
    assert behavior.last_day_closed_day == yesterday

    context = to_prompt_safe_context(state)
    state_json = json.dumps(state.model_dump(mode="json"), sort_keys=True)
    context_json = json.dumps(context.model_dump(mode="json"), sort_keys=True)
    for forbidden in (
        "Ada Lovelace",
        "ada@example.com",
        "synthetic-credential-leak-sentinel",
        "client-secret-1",
        "raw slip event text",
        "other user event",
        "therapy",
        "diagnosis",
        "treat diabetes",
        "medical_claim",
    ):
        assert forbidden not in state_json
        assert forbidden not in context_json
    assert context.recent_behavior.has_recent_activity is True
    assert context.recent_behavior.has_recent_slip_like is True
    assert context.recent_behavior.slip_like_count_7d == 3


def test_event_scan_is_capped_and_stable(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 91_007
    fixed_now = datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(builder_module, "_now_utc", lambda: fixed_now)

    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
        for index in range(RECENT_EVENT_SCAN_LIMIT + 1):
            session.add(
                _event(
                    user_id=user_id,
                    day=fixed_now.date(),
                    event_type="meal_logged",
                    created_at=fixed_now - timedelta(seconds=index),
                    client_event_id=f"capped-meal-{index}",
                    payload={"free_text": f"raw capped event {index}"},
                )
            )

    with configure_sqlite_database.session_scope() as session:
        state = build_user_coaching_state(user_id=user_id, session=session)

    assert state.recent_behavior.scanned_event_count == RECENT_EVENT_SCAN_LIMIT
    assert state.recent_behavior.meal_logged_count_7d == RECENT_EVENT_SCAN_LIMIT
    assert state.recent_behavior.events_capped is True
    assert state.recent_behavior.last_meal_logged_at == _sqlite_datetime(fixed_now)
    context = to_prompt_safe_context(state)
    assert context.recent_behavior.events_capped is True
    assert "raw capped event" not in json.dumps(context.model_dump(mode="json"))


def test_event_scan_uses_id_desc_tiebreak_for_same_created_at(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 91_008
    fixed_now = datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(builder_module, "_now_utc", lambda: fixed_now)

    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
        old_first_event = _event(
            user_id=user_id,
            day=fixed_now.date(),
            event_type="slip",
            created_at=fixed_now,
            client_event_id="same-time-low-id",
            payload={"free_text": "same timestamp lower id"},
        )
        session.add(old_first_event)
        session.flush()
        excluded_low_id = old_first_event.id
        for index in range(RECENT_EVENT_SCAN_LIMIT):
            session.add(
                _event(
                    user_id=user_id,
                    day=fixed_now.date(),
                    event_type="meal_logged",
                    created_at=fixed_now,
                    client_event_id=f"same-time-high-id-{index}",
                    payload={"free_text": f"same timestamp higher id {index}"},
                )
            )

    with configure_sqlite_database.session_scope() as session:
        state = build_user_coaching_state(user_id=user_id, session=session)
        excluded_event = session.get(NutritionEvent, excluded_low_id)

    assert excluded_event is not None
    assert state.recent_behavior.events_capped is True
    assert state.recent_behavior.scanned_event_count == RECENT_EVENT_SCAN_LIMIT
    assert state.recent_behavior.meal_logged_count_7d == RECENT_EVENT_SCAN_LIMIT
    assert state.recent_behavior.slip_count_7d == 0
    assert state.recent_behavior.slip_like_count_7d == 0


@pytest.mark.parametrize(
    ("risk_slip", "confidence", "expected_risk_bucket", "expected_confidence_bucket"),
    [
        (0.32, 0.79, "low", "low"),
        (0.33, 0.80, "moderate", "high"),
        (0.66, 0.79, "moderate", "low"),
        (0.67, 0.80, "high", "high"),
    ],
)
def test_prompt_safe_context_bucket_boundaries(
    risk_slip: float,
    confidence: float,
    expected_risk_bucket: str,
    expected_confidence_bucket: str,
) -> None:
    state = UserCoachingStateV1(
        user_id=91_009,
        assembled_at=datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc),
        adherence=AdherenceSnapshot(
            alpha=1.0,
            beta=1.0,
            n=7,
            risk_slip=risk_slip,
            confidence=confidence,
            needs_more_data=False,
        ),
    )

    context = to_prompt_safe_context(state)

    assert context.adherence.risk_bucket == expected_risk_bucket
    assert context.adherence.confidence_bucket == expected_confidence_bucket


def test_builder_rejects_invalid_user_id(configure_sqlite_database: Any) -> None:
    with configure_sqlite_database.session_scope() as session:
        with pytest.raises(ValueError, match="positive backend-derived subject id"):
            build_user_coaching_state(user_id=0, session=session)


def test_day_closed_missing_or_nonnumeric_score_is_not_slip_like(
    configure_sqlite_database: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = 91_010
    fixed_now = datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(builder_module, "_now_utc", lambda: fixed_now)

    with configure_sqlite_database.session_scope() as session:
        _reset_subjects(session, user_id)
        session.add_all(
            [
                _event(
                    user_id=user_id,
                    day=fixed_now.date(),
                    event_type="day_closed",
                    created_at=fixed_now.replace(hour=10),
                    client_event_id="day-close-missing-score",
                    payload={},
                ),
                _event(
                    user_id=user_id,
                    day=fixed_now.date(),
                    event_type="day_closed",
                    created_at=fixed_now.replace(hour=11),
                    client_event_id="day-close-nonnumeric-score",
                    payload={"adherence_score": "0.2"},
                ),
            ]
        )

    with configure_sqlite_database.session_scope() as session:
        state = build_user_coaching_state(user_id=user_id, session=session)

    assert state.recent_behavior.day_closed_count_7d == 2
    assert state.recent_behavior.day_close_slip_count_7d == 0
    assert state.recent_behavior.slip_like_count_7d == 0


def test_schema_models_are_frozen_strict_and_recompute_derived_fields() -> None:
    fixed_now = datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc)
    state = UserCoachingStateV1.model_validate(
        {
            "user_id": 91_011,
            "assembled_at": fixed_now,
            "adherence": AdherenceSnapshot(
                alpha=2.0,
                beta=8.0,
                n=10,
                risk_slip=0.8,
                confidence=0.85,
                needs_more_data=False,
            ),
            "recent_behavior": RecentBehaviorSnapshot(
                slip_like_count_7d=2,
                scanned_event_count=2,
            ),
            "available_scenarios": ("slip_support", "mascot_insight", "slip_support"),
            "coaching_urgency": 99.0,
            "next_recommended_scenario": "client_injected",
            "degrade_reasons": ("caller_injected",),
        }
    )

    assert state.available_scenarios == ("slip_support", "mascot_insight")
    assert state.coaching_urgency == pytest.approx(0.5)
    assert state.next_recommended_scenario == "slip_support"
    assert "caller_injected" not in state.degrade_reasons

    with pytest.raises(ValidationError):
        AdherenceSnapshot(alpha=0.0)
    with pytest.raises(ValidationError):
        RecentBehaviorSnapshot.model_validate({"extra_field": True})
    with pytest.raises(ValidationError):
        setattr(state, "coaching_urgency", 0.1)


def test_prompt_safe_context_recomputes_model_copy_derived_injection() -> None:
    state = UserCoachingStateV1(
        user_id=91_013,
        assembled_at=datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc),
        adherence=AdherenceSnapshot(
            alpha=1.0,
            beta=1.0,
            n=0,
            risk_slip=0.5,
            confidence=0.35,
            needs_more_data=True,
        ),
        available_scenarios=("mascot_insight",),
    )
    copied_state = state.model_copy(
        update={
            "coaching_urgency": 0.99,
            "next_recommended_scenario": "identity_loop_mapper",
        }
    )

    context = to_prompt_safe_context(copied_state)

    assert context.coaching_urgency == state.coaching_urgency
    assert context.next_recommended_scenario == "mascot_insight"


def test_service_only_files_do_not_wire_public_runtime_or_write_paths() -> None:
    target_text = "\n".join(
        [
            (REPO_ROOT / "app/schemas/user_coaching_state.py").read_text(encoding="utf-8"),
            (REPO_ROOT / "app/services/coaching_state_builder.py").read_text(encoding="utf-8"),
        ]
    )

    for forbidden in (
        "APIRouter",
        "FastAPI",
        "legacy_app",
        "fitchef_runtime",
        "semantic_cache",
        "Redis",
        "record_event(",
        "upsert_state(",
        "update_if_version_matches(",
        "session.add(",
        "session.commit(",
        "session.flush(",
    ):
        assert forbidden not in target_text

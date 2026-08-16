"""Read-only User Coaching State v1 builder."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NutritionEvent
from app.schemas.user_coaching_state import (
    AdherenceSnapshot,
    ConfidenceBucket,
    PromptSafeAdherenceContext,
    PromptSafeCoachingContext,
    PromptSafeGoalAuthorityContext,
    PromptSafeProfileSignalContext,
    PromptSafeRecentBehaviorContext,
    RecentBehaviorSnapshot,
    RiskBucket,
    UserCoachingStateV1,
)
from core.analyzer.store_sqlalchemy import SQLAlchemyAnalyzerStore
from core.bayes.adherence_service import (
    DEFAULT_ANALYZER_KEY,
    AdherenceService,
)

RECENT_BEHAVIOR_WINDOW_DAYS = 7
RECENT_EVENT_SCAN_LIMIT = 250
SUPPORTED_ANALYZER_KEYS = frozenset({DEFAULT_ANALYZER_KEY})


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _validate_analyzer_key(analyzer_key: str) -> None:
    if analyzer_key not in SUPPORTED_ANALYZER_KEYS:
        raise ValueError(f"unsupported analyzer_key: {analyzer_key}")


def _finite_float_metric(
    value: object,
    *,
    field_name: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite number")
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"{field_name} must be numeric")
    metric = float(value)
    if not math.isfinite(metric):
        raise ValueError(f"{field_name} must be finite")
    if min_value is not None and metric < min_value:
        raise ValueError(f"{field_name} must be >= {min_value}")
    if max_value is not None and metric > max_value:
        raise ValueError(f"{field_name} must be <= {max_value}")
    return metric


def _non_negative_int_metric(value: object, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a non-negative integer")
    if not isinstance(value, (int, str)):
        raise TypeError(f"{field_name} must be an integer")
    metric = int(value)
    if metric < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return metric


def _strict_raw_positive_float(value: object, *, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a raw numeric value")
    metric = float(value)
    if not math.isfinite(metric) or metric <= 0:
        raise ValueError(f"{field_name} must be a positive finite number")


def _strict_raw_non_negative_int(value: object, *, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be a raw integer")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_raw_adherence_payload(payload: object | None) -> None:
    if payload is None:
        return
    if not isinstance(payload, Mapping):
        raise TypeError("adherence payload must be an object")
    _strict_raw_positive_float(payload.get("alpha", 1.0), field_name="alpha")
    _strict_raw_positive_float(payload.get("beta", 1.0), field_name="beta")
    _strict_raw_non_negative_int(payload.get("n", 0), field_name="n")


def _build_adherence_snapshot(
    *, user_id: int, session: Session, analyzer_key: str
) -> AdherenceSnapshot:
    store = SQLAlchemyAnalyzerStore(session=session)
    service = AdherenceService(store=store)
    try:
        existing = store.get_state(user_id=user_id, analyzer_key=analyzer_key)
        _validate_raw_adherence_payload(existing.payload if existing else None)
        result = service.get(user_id=user_id, analyzer_key=analyzer_key)
        alpha = _finite_float_metric(result.alpha, field_name="alpha", min_value=0.0)
        beta = _finite_float_metric(result.beta, field_name="beta", min_value=0.0)
        n = _non_negative_int_metric(result.n, field_name="n")
        risk_slip = _finite_float_metric(
            result.risk_slip,
            field_name="risk_slip",
            min_value=0.0,
            max_value=1.0,
        )
        confidence = _finite_float_metric(
            result.confidence,
            field_name="confidence",
            min_value=0.0,
            max_value=1.0,
        )
        return AdherenceSnapshot(
            analyzer_key="v1:adherence",
            alpha=alpha,
            beta=beta,
            n=n,
            risk_slip=risk_slip,
            confidence=confidence,
            needs_more_data=result.needs_more_data,
            source_status="loaded" if n > 0 else "default",
        )
    except (TypeError, ValueError):
        return AdherenceSnapshot(source_status="invalid_degraded")


def _payload_score(payload: object) -> float | None:
    if not isinstance(payload, dict):
        return None
    raw_score = payload.get("adherence_score")
    if isinstance(raw_score, (int, float)):
        return float(raw_score)
    return None


def _event_created_at(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return None


def _build_recent_behavior_snapshot(
    *, user_id: int, session: Session, assembled_at: datetime
) -> RecentBehaviorSnapshot:
    today = assembled_at.date()
    window_start: date = today - timedelta(days=RECENT_BEHAVIOR_WINDOW_DAYS - 1)
    stmt = (
        select(
            NutritionEvent.event_type,
            NutritionEvent.day,
            NutritionEvent.payload,
            NutritionEvent.created_at,
        )
        .where(
            NutritionEvent.subject_id == user_id,
            NutritionEvent.day >= window_start,
            NutritionEvent.day <= today,
        )
        .order_by(NutritionEvent.created_at.desc(), NutritionEvent.id.desc())
        .limit(RECENT_EVENT_SCAN_LIMIT + 1)
    )
    fetched_rows = list(session.execute(stmt))
    events_capped = len(fetched_rows) > RECENT_EVENT_SCAN_LIMIT
    rows = fetched_rows[:RECENT_EVENT_SCAN_LIMIT]

    meal_logged_count = 0
    slip_count = 0
    partial_count = 0
    day_closed_count = 0
    day_close_slip_like_count = 0
    last_meal_logged_at: datetime | None = None
    last_slip_at: datetime | None = None
    last_partial_at: datetime | None = None
    last_slip_like_at: datetime | None = None
    last_day_closed_at: datetime | None = None
    last_day_closed_day: date | None = None

    for event_type, day_value, payload, created_at in rows:
        created = _event_created_at(created_at)
        if event_type == "meal_logged":
            meal_logged_count += 1
            if last_meal_logged_at is None:
                last_meal_logged_at = created
        elif event_type == "slip":
            slip_count += 1
            if last_slip_at is None:
                last_slip_at = created
            if last_slip_like_at is None:
                last_slip_like_at = created
        elif event_type == "partial":
            partial_count += 1
            if last_partial_at is None:
                last_partial_at = created
            if last_slip_like_at is None:
                last_slip_like_at = created
        elif event_type == "day_closed":
            day_closed_count += 1
            if last_day_closed_at is None:
                last_day_closed_at = created
            if isinstance(day_value, date) and last_day_closed_day is None:
                last_day_closed_day = day_value
            score = _payload_score(payload)
            if score is not None and score < 1.0:
                day_close_slip_like_count += 1
                if last_slip_like_at is None:
                    last_slip_like_at = created

    return RecentBehaviorSnapshot(
        window_days=RECENT_BEHAVIOR_WINDOW_DAYS,
        meal_logged_count_7d=meal_logged_count,
        slip_count_7d=slip_count,
        partial_count_7d=partial_count,
        day_closed_count_7d=day_closed_count,
        day_close_slip_count_7d=day_close_slip_like_count,
        slip_like_count_7d=slip_count + partial_count + day_close_slip_like_count,
        scanned_event_count=len(rows),
        event_scan_limit=RECENT_EVENT_SCAN_LIMIT,
        events_capped=events_capped,
        last_meal_logged_at=last_meal_logged_at,
        last_slip_at=last_slip_at,
        last_partial_at=last_partial_at,
        last_slip_like_at=last_slip_like_at,
        last_day_closed_at=last_day_closed_at,
        last_day_closed_day=last_day_closed_day,
    )


def build_user_coaching_state(
    user_id: int,
    session: Session,
    analyzer_key: str = DEFAULT_ANALYZER_KEY,
) -> UserCoachingStateV1:
    """Build a read-only internal coaching state from backend truth."""

    if user_id < 1:
        raise ValueError("user_id must be a positive backend-derived subject id")
    _validate_analyzer_key(analyzer_key)

    assembled_at = _now_utc()
    return UserCoachingStateV1(
        user_id=user_id,
        assembled_at=assembled_at,
        adherence=_build_adherence_snapshot(
            user_id=user_id,
            session=session,
            analyzer_key=analyzer_key,
        ),
        recent_behavior=_build_recent_behavior_snapshot(
            user_id=user_id,
            session=session,
            assembled_at=assembled_at,
        ),
    )


def _risk_bucket(risk_slip: float) -> RiskBucket:
    if risk_slip < 0.33:
        return "low"
    if risk_slip < 0.67:
        return "moderate"
    return "high"


def _confidence_bucket(confidence: float) -> ConfidenceBucket:
    return "high" if confidence >= 0.8 else "low"


def to_prompt_safe_context(state: UserCoachingStateV1) -> PromptSafeCoachingContext:
    """Return a static allowlist projection without identifiers or raw text."""

    safe_state = UserCoachingStateV1.model_validate(state.model_dump(mode="python"))
    adherence = safe_state.adherence
    behavior = safe_state.recent_behavior
    return PromptSafeCoachingContext(
        adherence=PromptSafeAdherenceContext(
            risk_slip=adherence.risk_slip,
            confidence=adherence.confidence,
            needs_more_data=adherence.needs_more_data,
            observation_count=adherence.n,
            risk_bucket=_risk_bucket(adherence.risk_slip),
            confidence_bucket=_confidence_bucket(adherence.confidence),
        ),
        recent_behavior=PromptSafeRecentBehaviorContext(
            window_days=behavior.window_days,
            meal_logged_count_7d=behavior.meal_logged_count_7d,
            slip_like_count_7d=behavior.slip_like_count_7d,
            day_closed_count_7d=behavior.day_closed_count_7d,
            has_recent_activity=behavior.scanned_event_count > 0,
            has_recent_slip_like=behavior.slip_like_count_7d > 0,
            events_capped=behavior.events_capped,
        ),
        profile=PromptSafeProfileSignalContext(
            bmi_value=safe_state.profile.bmi_value,
            bmi_group=safe_state.profile.bmi_group,
            goal_profile=safe_state.profile.goal_profile,
            goal_direction=safe_state.profile.goal_direction,
            nutrition_profile=safe_state.profile.nutrition_profile,
            nutrition_goal=safe_state.profile.nutrition_goal,
            data_status=safe_state.profile.data_status,
        ),
        goal=PromptSafeGoalAuthorityContext(
            status=safe_state.goal.status,
            source=safe_state.goal.source,
            data_status=safe_state.goal.data_status,
        ),
        coaching_urgency=safe_state.coaching_urgency,
        next_recommended_scenario=safe_state.next_recommended_scenario,
    )


__all__ = [
    "RECENT_BEHAVIOR_WINDOW_DAYS",
    "RECENT_EVENT_SCAN_LIMIT",
    "SUPPORTED_ANALYZER_KEYS",
    "build_user_coaching_state",
    "to_prompt_safe_context",
]

"""Read-only User Coaching State v1 builder."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NutritionEvent
from app.schemas.user_coaching_state import (
    AdherenceSnapshot,
    ConfidenceBucket,
    PromptSafeAdherenceContext,
    PromptSafeCoachingContext,
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


def _build_adherence_snapshot(
    *, user_id: int, session: Session, analyzer_key: str
) -> AdherenceSnapshot:
    service = AdherenceService(store=SQLAlchemyAnalyzerStore(session=session))
    try:
        result = service.get(user_id=user_id, analyzer_key=analyzer_key)
    except ValueError:
        return AdherenceSnapshot(source_status="invalid_degraded")

    return AdherenceSnapshot(
        analyzer_key="v1:adherence",
        alpha=result.alpha,
        beta=result.beta,
        n=result.n,
        risk_slip=result.risk_slip,
        confidence=result.confidence,
        needs_more_data=result.needs_more_data,
        source_status="loaded" if result.n > 0 else "default",
    )


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

    adherence = state.adherence
    behavior = state.recent_behavior
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
            bmi_value=state.profile.bmi_value,
            bmi_group=state.profile.bmi_group,
            goal_profile=state.profile.goal_profile,
            goal_direction=state.profile.goal_direction,
            nutrition_profile=state.profile.nutrition_profile,
            nutrition_goal=state.profile.nutrition_goal,
            data_status=state.profile.data_status,
        ),
        coaching_urgency=state.coaching_urgency,
        next_recommended_scenario=state.next_recommended_scenario,
    )


__all__ = [
    "RECENT_BEHAVIOR_WINDOW_DAYS",
    "RECENT_EVENT_SCAN_LIMIT",
    "SUPPORTED_ANALYZER_KEYS",
    "build_user_coaching_state",
    "to_prompt_safe_context",
]

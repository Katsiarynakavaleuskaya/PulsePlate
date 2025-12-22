"""Nutrition logging endpoints (meal/day).

RU: PRO эндпоинты логирования (meal-log / day-close), которые обновляют байесовскую микромодель adherence.
EN: PRO nutrition logging endpoints that feed the adherence micro-model.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.middleware.api_tiers import CurrentUser, get_current_user, require_pro_tier
from app.models.events import NutritionEvent
from app.routers.bayes_adherence import get_adherence_service
from app.schemas.bayes_adherence import AdherenceResponse
from app.schemas.nutrition_log import DayCloseRequest, MealLogRequest
from app.services.nutrition_events_collector import collect_day_events
from core.bayes.adherence_adapter import DomainEvent
from core.bayes.adherence_service import AdherenceService
from core.db import get_session

router = APIRouter(
    prefix="/api/v1/pro/nutrition",
    tags=["pro", "nutrition-log"],
    dependencies=[Depends(require_pro_tier)],
)

# Idempotency constraint name for narrowed IntegrityError handling
IDEMP_CONSTRAINT = "uq_nutrition_events_idempotency"


def _is_idempotency_violation(err: IntegrityError) -> bool:
    """Check if IntegrityError is specifically an idempotency constraint violation.

    RU: Проверить, что IntegrityError связан именно с idempotency constraint.
    EN: Check if IntegrityError is from the idempotency constraint.

    This prevents treating other constraint violations (FK, check, etc.) as idempotent replays.
    """
    # Postgres (psycopg): check diag.constraint_name
    orig = getattr(err, "orig", None)
    diag = getattr(orig, "diag", None)
    if diag and getattr(diag, "constraint_name", None) == IDEMP_CONSTRAINT:
        return True

    # SQLite: check constraint name in error message
    return IDEMP_CONSTRAINT in str(orig) or IDEMP_CONSTRAINT in str(err)


def _event_from_meal_log(payload: MealLogRequest) -> DomainEvent:
    """Map MealLogRequest to DomainEvent.

    RU: Маппинг payload -> DomainEvent.
    EN: Map payload -> DomainEvent.
    """

    if payload.log_type == "meal_logged":
        return DomainEvent(name="meal_logged", weight=1.0)

    if payload.log_type == "slip":
        return DomainEvent(name="slip", weight=1.0)

    # partial
    score = payload.adherence_score
    if score is None:
        # This should be prevented by MealLogRequest validator; treat as server error if it happens.
        raise RuntimeError("adherence_score must be provided when log_type='partial'")
    weight = max(0.01, 1.0 - score)
    return DomainEvent(name="slip", weight=weight)


def _event_from_day_close(payload: DayCloseRequest) -> DomainEvent:
    """Map DayCloseRequest to DomainEvent.

    RU: Маппинг закрытия дня в событие adherence.
    EN: Map day-close payload to adherence event.
    """

    score = payload.adherence_score
    if score >= 1.0:
        return DomainEvent(name="meal_logged", weight=1.0)

    weight = max(0.01, 1.0 - score)
    return DomainEvent(name="slip", weight=weight)


@router.post("/meal-log", response_model=AdherenceResponse, summary="Log meal event (PRO)")
def log_meal(
    payload: MealLogRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdherenceService = Depends(get_adherence_service),
    session: Session = Depends(get_session),
) -> AdherenceResponse:
    """Log a meal event and update adherence micro-model.

    RU: Логировать событие приёма пищи и обновить микромодель adherence.
    EN: Log a meal event and update adherence micro-model.

    Idempotency: If client_event_id is provided and matches an existing event,
    returns success without re-processing.
    """

    subject_id = current_user.user_id
    # Use UTC to avoid timezone edge cases at day boundaries
    day = datetime.now(timezone.utc).date()

    # Write event to append-only log (idempotent if client_event_id provided)
    try:
        event_record = NutritionEvent(
            subject_id=subject_id,
            day=day,
            source="meal_log",
            event_type=payload.log_type,  # meal_logged | slip | partial
            client_event_id=payload.client_event_id,
            payload={
                "log_type": payload.log_type,
                "adherence_score": payload.adherence_score,
            },
        )
        session.add(event_record)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        # Narrowed idempotency check: only treat as replay if it's the idempotency constraint
        if payload.client_event_id and _is_idempotency_violation(e):
            # Event already exists; return current adherence state without re-processing
            result = service.get(subject_id)
            return AdherenceResponse.model_validate(result, from_attributes=True)
        else:
            # Other IntegrityError (FK, check, etc.) or no client_event_id - propagate
            raise

    # Update adherence micro-model (sync call, FastAPI handles threadpool)
    event = _event_from_meal_log(payload)
    result = service.record_domain_event(subject_id, event)
    return AdherenceResponse.model_validate(result, from_attributes=True)


@router.post("/day-close", response_model=AdherenceResponse, summary="Close day (PRO)")
def close_day(
    payload: DayCloseRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdherenceService = Depends(get_adherence_service),
    session: Session = Depends(get_session),
) -> AdherenceResponse:
    """Close a day and finalize adherence via event collector.

    RU: Закрыть день и финализировать adherence через коллектор событий.
    EN: Close a day and finalize adherence via event collector.

    This is the sole canonical trigger for adherence finalization.
    Idempotent: repeated calls for same day return existing state without re-finalization.
    """

    subject_id = current_user.user_id
    day = payload.day

    # Deterministic client_event_id for idempotency
    client_event_id = f"day-close:{day.isoformat()}"

    # Write day_closed event to append-only log (idempotent)
    already_closed = False

    try:
        event_record = NutritionEvent(
            subject_id=subject_id,
            day=day,
            source="day_close",
            event_type="day_closed",
            client_event_id=client_event_id,
            payload={
                "adherence_score": payload.adherence_score,
            },
        )
        session.add(event_record)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        # Narrowed idempotency check: only treat as replay if it's the idempotency constraint
        if _is_idempotency_violation(e):
            # Day already closed - skip re-finalization, return current state
            already_closed = True
        else:
            # Other IntegrityError (FK, check, etc.) - propagate
            raise

    # Collect day events for finalization context
    collected = collect_day_events(session, subject_id, day)

    # Finalize adherence only if this is the first closure (sync call, FastAPI handles threadpool)
    if not already_closed:
        event = _event_from_day_close(payload)
        result = service.record_domain_event(subject_id, event)
    else:
        # Already closed - retrieve current adherence state without re-processing
        result = service.get(subject_id)

    return AdherenceResponse.model_validate(result, from_attributes=True)

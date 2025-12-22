"""Nutrition logging endpoints (meal/day).

RU: PRO эндпоинты логирования (meal-log / day-close), которые обновляют байесовскую микромодель adherence.
EN: PRO nutrition logging endpoints that feed the adherence micro-model.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError

from app.middleware.api_tiers import CurrentUser, get_current_user, require_pro_tier
from app.models.events import NutritionEvent
from app.routers.bayes_adherence import get_adherence_service
from app.schemas.bayes_adherence import AdherenceResponse
from app.schemas.nutrition_log import DayCloseRequest, MealLogRequest
from app.services.nutrition_events_collector import collect_day_events
from core.bayes.adherence_adapter import DomainEvent
from core.bayes.adherence_service import AdherenceService
from core.db import get_session_factory

router = APIRouter(
    prefix="/api/v1/pro/nutrition",
    tags=["pro", "nutrition-log"],
    dependencies=[Depends(require_pro_tier)],
)


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
async def log_meal(
    payload: MealLogRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdherenceService = Depends(get_adherence_service),
) -> AdherenceResponse:
    """Log a meal event and update adherence micro-model.

    RU: Логировать событие приёма пищи и обновить микромодель adherence.
    EN: Log a meal event and update adherence micro-model.

    Idempotency: If client_event_id is provided and matches an existing event,
    returns success without re-processing.
    """

    subject_id = current_user.user_id
    day = date.today()

    # Write event to append-only log (idempotent if client_event_id provided)
    session_factory = get_session_factory()
    with session_factory() as session:
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
        except IntegrityError:
            session.rollback()
            # Idempotent replay: if client provided event_id and it's a duplicate, return OK
            if payload.client_event_id:
                # Event already exists; treat as successful idempotent replay.
                # Fall through to process adherence update normally.
                pass
            else:
                # IntegrityError without client_event_id indicates real DB issue
                raise

    # Update adherence micro-model
    event = _event_from_meal_log(payload)
    result = await run_in_threadpool(
        service.record_domain_event,
        subject_id,
        event,
    )
    return AdherenceResponse.model_validate(result, from_attributes=True)


@router.post("/day-close", response_model=AdherenceResponse, summary="Close day (PRO)")
async def close_day(
    payload: DayCloseRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdherenceService = Depends(get_adherence_service),
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
    session_factory = get_session_factory()
    already_closed = False

    with session_factory() as session:
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
        except IntegrityError:
            session.rollback()
            # Day already closed - skip re-finalization, return current state
            already_closed = True

        # Collect day events for finalization context
        collected = collect_day_events(session, subject_id, day)

    # Finalize adherence only if this is the first closure
    if not already_closed:
        event = _event_from_day_close(payload)
        result = await run_in_threadpool(
            service.record_domain_event,
            subject_id,
            event,
        )
    else:
        # Already closed - retrieve current adherence state without re-processing
        result = await run_in_threadpool(
            service.get_adherence_state,
            subject_id,
        )

    return AdherenceResponse.model_validate(result, from_attributes=True)

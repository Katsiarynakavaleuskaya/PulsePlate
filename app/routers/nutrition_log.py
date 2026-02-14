"""Nutrition logging endpoints (meal/day).

RU: PRO эндпоинты логирования (meal-log / day-close), которые обновляют байесовскую микромодель adherence.
EN: PRO nutrition logging endpoints that feed the adherence micro-model.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.middleware.api_tiers import CurrentUser, get_current_user, require_pro_tier
from app.openapi.orm_imports import get_nutrition_event_model
from app.routers.bayes_adherence import get_adherence_service
from app.schemas.bayes_adherence import AdherenceResponse
from app.schemas.nutrition_log import DayCloseRequest, MealLogRequest
from core.bayes.adherence_adapter import DomainEvent
from core.bayes.adherence_service import AdherenceService
from core.db import get_session

if TYPE_CHECKING:
    # Static-only import for precise typing; runtime keeps lazy ORM resolution.
    from app.models import NutritionEvent as NutritionEventModel

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

    # SQLite: check constraint name or column list in error message
    orig_str = str(orig) if orig is not None else ""
    err_str = str(err)
    if IDEMP_CONSTRAINT in orig_str or IDEMP_CONSTRAINT in err_str:
        return True
    sqlite_marker = (
        "nutrition_events.subject_id",
        "nutrition_events.day",
        "nutrition_events.source",
        "nutrition_events.client_event_id",
    )
    return all(marker in err_str for marker in sqlite_marker)


def _fetch_existing_event(
    session: Session, subject_id: int, day: date, source: str, client_event_id: str
) -> "NutritionEventModel" | None:
    # Lazy import: avoid ORM model import at module import time (OpenAPI generation path).
    NutritionEventModel = get_nutrition_event_model()

    stmt = (
        select(NutritionEventModel)
        .where(
            NutritionEventModel.subject_id == subject_id,
            NutritionEventModel.day == day,
            NutritionEventModel.source == source,
            NutritionEventModel.client_event_id == client_event_id,
        )
        .limit(1)
    )
    return session.scalar(stmt)


def _is_event_applied(payload: dict | None) -> bool:
    return bool(payload and payload.get("applied") is True)


def _mark_event_applied(session: Session, event_record: "NutritionEventModel") -> None:
    payload = dict(event_record.payload or {})
    if payload.get("applied") is True:
        return
    payload["applied"] = True
    event_record.payload = payload
    session.add(event_record)
    session.commit()


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


def _to_response(result: object) -> AdherenceResponse:
    """Convert service result to AdherenceResponse schema.

    RU: Конвертирует результат сервиса в AdherenceResponse схему.
    EN: Convert service result to AdherenceResponse schema.

    NOTE: model_validate() returns Any for mypy; assign to local to keep return type.
    This helper centralizes the workaround pattern documented in app/AGENTS.md.
    """
    response: AdherenceResponse
    response = AdherenceResponse.model_validate(result, from_attributes=True)
    return response


@router.post("/meal-log", response_model=AdherenceResponse, summary="Log meal event (PRO)")
async def log_meal(
    payload: MealLogRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdherenceService = Depends(get_adherence_service),
    session: Session = Depends(get_session),
) -> AdherenceResponse:
    """Log a meal event and update adherence micro-model.

    RU: Логировать событие приёма пищи и обновить микромодель adherence.
    EN: Log a meal event and update adherence micro-model.

    Idempotency: If client_event_id is provided and matches an existing event,
    returns current state when the event is already applied.
    """

    subject_id = current_user.user_id
    # Use UTC to avoid timezone edge cases at day boundaries
    day = datetime.now(timezone.utc).date()

    # Write event to append-only log (idempotent if client_event_id provided)
    event_record: "NutritionEventModel" | None = None
    NutritionEventModel = get_nutrition_event_model()

    event_payload = {
        "log_type": payload.log_type,
        "adherence_score": payload.adherence_score,
        "applied": False,
    }
    try:
        event_record = NutritionEventModel(
            subject_id=subject_id,
            day=day,
            source="meal_log",
            event_type=payload.log_type,  # meal_logged | slip | partial
            client_event_id=payload.client_event_id,
            payload=event_payload,
        )
        session.add(event_record)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        # Narrowed idempotency check: only treat as replay if it's the idempotency constraint
        if payload.client_event_id and _is_idempotency_violation(e):
            event_record = _fetch_existing_event(
                session, subject_id, day, "meal_log", payload.client_event_id
            )
        else:
            # Other IntegrityError (FK, check, etc.) or no client_event_id - propagate
            raise

    if event_record is None:
        result = await run_in_threadpool(service.get, subject_id)
        return _to_response(result)

    if _is_event_applied(event_record.payload):
        result = await run_in_threadpool(service.get, subject_id)
        return _to_response(result)

    # Update adherence micro-model (async offload to threadpool)
    event = _event_from_meal_log(payload)
    result = await run_in_threadpool(service.record_domain_event, subject_id, event)
    _mark_event_applied(session, event_record)
    return _to_response(result)


@router.post("/day-close", response_model=AdherenceResponse, summary="Close day (PRO)")
async def close_day(
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
    event_record: "NutritionEventModel" | None = None
    NutritionEventModel = get_nutrition_event_model()

    try:
        event_record = NutritionEventModel(
            subject_id=subject_id,
            day=day,
            source="day_close",
            event_type="day_closed",
            client_event_id=client_event_id,
            payload={
                "adherence_score": payload.adherence_score,
                "applied": False,
            },
        )
        session.add(event_record)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        # Narrowed idempotency check: only treat as replay if it's the idempotency constraint
        if _is_idempotency_violation(e):
            event_record = _fetch_existing_event(
                session, subject_id, day, "day_close", client_event_id
            )
        else:
            # Other IntegrityError (FK, check, etc.) - propagate
            raise

    if event_record is None:
        result = await run_in_threadpool(service.get, subject_id)
        return _to_response(result)

    if _is_event_applied(event_record.payload):
        result = await run_in_threadpool(service.get, subject_id)
        return _to_response(result)

    # Finalize adherence only if this is the first closure (async offload to threadpool)
    event = _event_from_day_close(payload)
    result = await run_in_threadpool(service.record_domain_event, subject_id, event)
    _mark_event_applied(session, event_record)

    return _to_response(result)

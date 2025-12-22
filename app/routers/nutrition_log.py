"""Nutrition logging endpoints (meal/day).

RU: PRO эндпоинты логирования (meal-log / day-close), которые обновляют байесовскую микромодель adherence.
EN: PRO nutrition logging endpoints that feed the adherence micro-model.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.middleware.api_tiers import CurrentUser, get_current_user, require_pro_tier
from app.routers.bayes_adherence import get_adherence_service
from app.schemas.bayes_adherence import AdherenceResponse
from app.schemas.nutrition_log import DayCloseRequest, MealLogRequest
from core.bayes.adherence_adapter import DomainEvent
from core.bayes.adherence_service import AdherenceService

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
    """

    event = _event_from_meal_log(payload)
    result = await run_in_threadpool(
        service.record_domain_event,
        current_user.user_id,
        event,
    )
    return AdherenceResponse.model_validate(result, from_attributes=True)


@router.post("/day-close", response_model=AdherenceResponse, summary="Close day (PRO)")
async def close_day(
    payload: DayCloseRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AdherenceService = Depends(get_adherence_service),
) -> AdherenceResponse:
    """Close a day and update adherence micro-model.

    RU: Закрыть день и обновить микромодель adherence.
    EN: Close a day and update adherence micro-model.
    """

    event = _event_from_day_close(payload)
    result = await run_in_threadpool(
        service.record_domain_event,
        current_user.user_id,
        event,
    )
    return AdherenceResponse.model_validate(result, from_attributes=True)

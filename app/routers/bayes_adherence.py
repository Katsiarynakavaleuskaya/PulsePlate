"""Bayesian adherence API endpoints.

RU: API эндпоинты для байесовской модели adherence.
EN: Bayesian adherence API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.middleware.api_tiers import get_pro_subject_id, require_pro_tier
from app.schemas.bayes_adherence import AdherenceEventRequest, AdherenceResponse
from core.analyzer.store_cache import TTLCacheAnalyzerStore
from core.analyzer.store_sqlalchemy import SQLAlchemyAnalyzerStore
from core.bayes.adherence_service import AdherenceService
from core.db import get_session

router = APIRouter(
    prefix="/api/v1/bayes/adherence",
    tags=["bayes"],
    dependencies=[Depends(require_pro_tier)],  # Router-level PRO protection
)


def get_adherence_service(session: Session = Depends(get_session)) -> AdherenceService:
    """Dependency providing AdherenceService with TTL-cached store.

    Args:
        session: SQLAlchemy session (injected by FastAPI)

    Returns:
        AdherenceService instance
    """
    base_store = SQLAlchemyAnalyzerStore(session=session)
    store = TTLCacheAnalyzerStore(inner=base_store, ttl_seconds=30.0)
    return AdherenceService(store=store)


@router.post(
    "/event",
    response_model=AdherenceResponse,
    summary="Record adherence event (PRO/VIP)",
)
def record_event(
    payload: AdherenceEventRequest,
    subject_id: int = Depends(get_pro_subject_id),
    service: AdherenceService = Depends(get_adherence_service),
) -> AdherenceResponse:
    """Record an adherence event (meal_logged or slip).

    RU: Записать событие adherence (успех или срыв).
    EN: Record an adherence event (success or slip).

    Args:
        payload: Event data (event_type, weight)
        subject_id: Subject ID derived from authenticated API key
        service: AdherenceService dependency

    Returns:
        Updated adherence metrics

    Security:
        subject_id is derived from API key to prevent horizontal privilege escalation.
        Each API key has isolated Bayesian state.
    """
    result = service.record_event(
        user_id=subject_id,
        event_type=payload.event_type,
        weight=payload.weight,
        analyzer_key=payload.analyzer_key,
    )
    return AdherenceResponse(**result.__dict__)


@router.get(
    "/risk",
    response_model=AdherenceResponse,
    summary="Get adherence slip risk (PRO/VIP)",
)
def get_risk(
    subject_id: int = Depends(get_pro_subject_id),
    analyzer_key: str = Query("v1:adherence", min_length=3, max_length=64),
    service: AdherenceService = Depends(get_adherence_service),
) -> AdherenceResponse:
    """Get current adherence slip risk and confidence.

    RU: Получить текущий риск срыва и уверенность модели.
    EN: Get current slip risk and model confidence.

    Args:
        subject_id: Subject ID derived from authenticated API key
        analyzer_key: Analyzer key (default: v1:adherence)
        service: AdherenceService dependency

    Returns:
        Current adherence metrics

    Security:
        subject_id is derived from API key to prevent horizontal privilege escalation.
    """
    result = service.get(user_id=subject_id, analyzer_key=analyzer_key)
    return AdherenceResponse(**result.__dict__)

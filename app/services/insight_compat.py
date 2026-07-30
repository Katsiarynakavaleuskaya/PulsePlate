"""Compatibility adapter for the retained Insight callables."""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import HTTPException, status

from app.schemas.insight import InsightRequest, InsightResponse, RAGSourceItem
from app.security.agent_input_guard import require_safe_ai_agent_input
from app.security.llm_monthly_quota import attempt_consume_vip_llm_monthly_quota
from app.services.insight_application_service import (
    execute_insight_request as _execute_insight_request_via_service,
)
from app.utils.feature_flags import is_insight_enabled
from core.ai import (
    DirectInsightProviderStub,
    InsightProviderLoadError,
    InsightTransparencyUnavailableError,
    load_insight_provider as _core_load_insight_provider,
    require_ai_generated_insight_notice as _core_require_ai_generated_insight_notice,
)
from core.insight.llm_provider_loader import load_llm_get_provider as _load_llm_get_provider

INSIGHT_TEMP_UNAVAILABLE_MESSAGE = "Insight is temporarily unavailable. Please try again later."
logger = logging.getLogger(__name__)

_DirectInsightProviderStub = DirectInsightProviderStub


def _load_insight_provider() -> Any:
    """Load the configured provider with the stable compatibility error contract."""
    try:
        return _core_load_insight_provider(provider_factory_loader=_load_llm_get_provider)
    except InsightProviderLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _require_ai_generated_insight_notice() -> tuple[str, str]:
    """Return required transparency metadata or fail closed."""
    try:
        notice = _core_require_ai_generated_insight_notice()
    except InsightTransparencyUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return notice.surface_id, notice.wellness_boundary


def _enforce_vip_llm_monthly_quota(vip_key: str) -> None:
    """Enforce the VIP monthly hard quota before any provider call."""
    if not attempt_consume_vip_llm_monthly_quota(vip_key):
        raise HTTPException(status_code=429, detail="quota_exceeded")


async def _execute_insight_request(
    req: InsightRequest,
    *,
    route_path: str,
    user_tier: str,
    subject_id: int | None = None,
) -> InsightResponse:
    """Delegate Insight execution to the existing application service."""
    return cast(
        InsightResponse,
        await _execute_insight_request_via_service(
            req,
            route_path=route_path,
            user_tier=user_tier,
            subject_id=subject_id,
            input_guard=require_safe_ai_agent_input,
            provider_loader=_load_insight_provider,
            transparency_loader=_require_ai_generated_insight_notice,
            direct_provider_factory=_DirectInsightProviderStub,
            response_factory=InsightResponse,
            source_item_factory=RAGSourceItem,
        ),
    )


async def insight_v1(
    req: InsightRequest,
    *,
    subject_id: int | None = None,
) -> InsightResponse:
    """Generate an Insight response for the retained v1 callable."""
    if not is_insight_enabled():
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")

    try:
        return await _execute_insight_request(
            req,
            route_path="/api/v1/insight",
            user_tier="VIP",
            subject_id=subject_id,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Insight provider call failed (/api/v1/insight)")
        raise HTTPException(status_code=503, detail=INSIGHT_TEMP_UNAVAILABLE_MESSAGE) from None


async def insight(req: InsightRequest) -> InsightResponse:
    """Generate an Insight response for the retained legacy callable."""
    if not is_insight_enabled():
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")

    try:
        return await _execute_insight_request(
            req,
            route_path="/insight",
            user_tier="VIP",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Insight provider call failed (/insight)")
        raise HTTPException(status_code=503, detail=INSIGHT_TEMP_UNAVAILABLE_MESSAGE) from None


__all__ = [
    "INSIGHT_TEMP_UNAVAILABLE_MESSAGE",
    "_DirectInsightProviderStub",
    "_enforce_vip_llm_monthly_quota",
    "_execute_insight_request",
    "_load_insight_provider",
    "_require_ai_generated_insight_notice",
    "insight",
    "insight_v1",
]

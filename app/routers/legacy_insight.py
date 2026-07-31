"""Canonical ownership for the retained hidden Insight routes.

The handlers enforce route-level security policy and delegate compatibility
execution through ``app.services.insight_compat``. Reusable orchestration stays
in ``app.services.insight_application_service``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.middleware.api_tiers import derive_subject_id_from_api_key, require_vip_tier
from app.schemas.insight import InsightRequest, InsightResponse
from app.security import agent_input_guard
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)
from app.services import insight_compat
from app.utils.feature_flags import is_explicit_truthy_env_var

LEGACY_INSIGHT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/insight", "POST", False),
    ("/insight", "POST", False),
)

router = APIRouter()


@router.post(
    "/api/v1/insight",
    response_model=InsightResponse,
    responses=RATE_LIMIT_429_RESPONSES,
    include_in_schema=False,
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def insight_v1_route(
    request: Request,
    req: InsightRequest,
    vip_key: str = Depends(require_vip_tier),
) -> InsightResponse:
    if not is_explicit_truthy_env_var("FEATURE_INSIGHT"):
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")
    agent_input_guard.require_safe_ai_agent_input(req.text)
    insight_compat._require_ai_generated_insight_notice()
    await run_in_threadpool(insight_compat._enforce_vip_llm_monthly_quota, vip_key)
    subject_id = derive_subject_id_from_api_key(vip_key)
    return await insight_compat.insight_v1(req, subject_id=subject_id)


@router.post(
    "/insight",
    include_in_schema=False,
    deprecated=True,
    response_model=InsightResponse,
    responses=RATE_LIMIT_429_RESPONSES,
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def insight_route(
    request: Request,
    req: InsightRequest,
    vip_key: str = Depends(require_vip_tier),
) -> InsightResponse:
    if not is_explicit_truthy_env_var("FEATURE_INSIGHT"):
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")
    agent_input_guard.require_safe_ai_agent_input(req.text)
    insight_compat._require_ai_generated_insight_notice()
    await run_in_threadpool(insight_compat._enforce_vip_llm_monthly_quota, vip_key)
    return await insight_compat.insight(req)

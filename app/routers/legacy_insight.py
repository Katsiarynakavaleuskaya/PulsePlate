"""Legacy insight route ownership.

Hidden VIP-guarded compatibility insight routes remain thin adapters for the
legacy execution path. Route registration ownership moved out of
``legacy_app.py``; orchestration stays in ``app/services/insight_application_service.py``
via legacy_app compat callables.
"""

from __future__ import annotations

import os

import legacy_app as _legacy
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.middleware.api_tiers import derive_subject_id_from_api_key, require_vip_tier
from legacy_app import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)

LEGACY_INSIGHT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/insight", "POST", False),
    ("/insight", "POST", False),
)

router = APIRouter()


@router.post(
    "/api/v1/insight",
    response_model=_legacy.InsightResponse,
    responses=RATE_LIMIT_429_RESPONSES,
    include_in_schema=False,
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def insight_v1_route(
    request: Request,
    req: _legacy.InsightRequest,
    vip_key: str = Depends(require_vip_tier),
) -> _legacy.InsightResponse:
    if not _legacy._is_truthy(os.getenv("FEATURE_INSIGHT", "false")):
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")
    _legacy.require_safe_ai_agent_input(req.text)
    _legacy._require_ai_generated_insight_notice()
    await run_in_threadpool(_legacy._enforce_vip_llm_monthly_quota, vip_key)
    subject_id = derive_subject_id_from_api_key(vip_key)
    return await _legacy.insight_v1(req, subject_id=subject_id)


@router.post(
    "/insight",
    include_in_schema=False,
    deprecated=True,
    response_model=_legacy.InsightResponse,
    responses=RATE_LIMIT_429_RESPONSES,
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def insight_route(
    request: Request,
    req: _legacy.InsightRequest,
    vip_key: str = Depends(require_vip_tier),
) -> _legacy.InsightResponse:
    if not _legacy._is_truthy(os.getenv("FEATURE_INSIGHT", "false")):
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")
    _legacy.require_safe_ai_agent_input(req.text)
    _legacy._require_ai_generated_insight_notice()
    await run_in_threadpool(_legacy._enforce_vip_llm_monthly_quota, vip_key)
    return await _legacy.insight(req)

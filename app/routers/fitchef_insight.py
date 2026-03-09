"""FitChef mascot insight router.

RU: Тонкий VIP-only router для mascot coaching surface.
EN: Thin VIP-only router for the mascot coaching surface.
"""

from __future__ import annotations

import logging
import os
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.api_tiers import require_vip_tier
from app.schemas.fitchef import FitChefMascotInsightInput, FitChefMascotInsightTaskEnvelope
from app.schemas.fitchef_coaching import (
    FitChefCoachingErrorResponse,
    FitChefCoachingRequest,
    FitChefCoachingSourceItem,
    FitChefMascotInsightResponse,
)
from app.security.agent_control_plane import normalize_execution_mode, require_execution_mode
from app.security.agent_input_guard import require_safe_ai_agent_input
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)
from app.services import fitchef_runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/insight", tags=["fitchef", "insight", "vip"])

FITCHEF_MASCOT_FLAG_ENV = "FEATURE_FITCHEF_MASCOT"
FITCHEF_MASCOT_EXECUTION_MODE_ENV = "FITCHEF_MASCOT_EXECUTION_MODE"
FitChefMascotMode = Literal["auto-safe", "review-required", "blocked"]


def _is_fitchef_mascot_enabled() -> bool:
    """Return whether the mascot insight feature is enabled."""

    return os.getenv(FITCHEF_MASCOT_FLAG_ENV, "false").lower() in {"1", "true", "yes", "on"}


@router.post(
    "/fitchef",
    response_model=FitChefMascotInsightResponse,
    responses={
        200: {"description": "FitChef mascot coaching insight generated"},
        400: {"description": "Unsafe AI input blocked", "model": FitChefCoachingErrorResponse},
        403: {"description": "VIP tier required", "model": FitChefCoachingErrorResponse},
        429: {"description": "Rate limit exceeded or monthly quota exhausted"},
        503: {
            "description": "Feature disabled or provider unavailable",
            "model": FitChefCoachingErrorResponse,
        },
        504: {"description": "LLM provider call timed out", "model": FitChefCoachingErrorResponse},
        **RATE_LIMIT_429_RESPONSES,
    },
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def fitchef_mascot_insight(
    payload: FitChefCoachingRequest,
    request: Request,
    vip_key: str = Depends(require_vip_tier),
) -> FitChefMascotInsightResponse:
    """Generate VIP-only mascot coaching insight via the FitChef runtime."""

    if not _is_fitchef_mascot_enabled():
        raise HTTPException(status_code=503, detail="FEATURE_FITCHEF_MASCOT is disabled")

    try:
        execution_mode = cast(
            FitChefMascotMode,
            normalize_execution_mode(os.getenv(FITCHEF_MASCOT_EXECUTION_MODE_ENV)),
        )
        require_execution_mode(execution_mode)
    except RuntimeError as exc:
        logger.error("FitChef mascot execution mode misconfigured", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="agent_execution_mode_misconfigured",
        ) from exc
    except PermissionError:
        detail = f"agent_execution_{execution_mode.replace('-', '_')}"
        raise HTTPException(status_code=503, detail=detail)

    safe_query = require_safe_ai_agent_input(payload.query)
    task = FitChefMascotInsightTaskEnvelope(
        mode=execution_mode,
        input=FitChefMascotInsightInput(
            safe_query=safe_query,
            api_key=vip_key,
            endpoint=str(request.url.path),
            method=request.method,
        ),
    )
    result = await fitchef_runtime.run_mascot_insight_task(task)
    response: FitChefMascotInsightResponse = FitChefMascotInsightResponse(
        message=result.message,
        sources=[
            FitChefCoachingSourceItem(
                file=item.file,
                preview=item.preview,
                score=item.score,
            )
            for item in result.sources
        ],
        confidence=result.confidence,
        warnings=result.warnings,
        action_items=result.action_items,
        quota_state=result.quota_state,
        transparency_notice_id=result.transparency_notice_id,
        wellness_boundary=result.wellness_boundary,
    )
    return response

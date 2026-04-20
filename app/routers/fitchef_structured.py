"""FitChef structured coaching router.

RU: Тонкий router для bounded structured FitChef coaching surfaces.
EN: Thin router for bounded structured FitChef coaching surfaces.
"""

from __future__ import annotations

import logging
import os
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.api_tiers import require_pro_tier
from app.schemas.fitchef import (
    FitChefDistortionSimulatorInput,
    FitChefDistortionSimulatorTaskEnvelope,
)
from app.schemas.fitchef_coaching import (
    FitChefCoachingErrorResponse,
    FitChefCoachingSourceItem,
    FitChefDistortionSimulatorRequest,
    FitChefDistortionSimulatorResponse,
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

router = APIRouter(tags=["pro", "fitchef", "coaching", "structured"])

FITCHEF_STRUCTURED_FLAG_ENV = "FEATURE_FITCHEF_STRUCTURED_COACH"
FITCHEF_STRUCTURED_EXECUTION_MODE_ENV = "FITCHEF_STRUCTURED_COACH_EXECUTION_MODE"
FitChefStructuredMode = Literal["auto-safe", "review-required", "blocked"]


def _is_fitchef_structured_enabled() -> bool:
    """Return whether structured FitChef coaching is enabled."""

    return os.getenv(FITCHEF_STRUCTURED_FLAG_ENV, "false").lower() in {"1", "true", "yes", "on"}


def _require_fitchef_structured_mode() -> FitChefStructuredMode:
    """Resolve and validate the structured-coach execution mode."""

    raw_execution_mode = os.getenv(FITCHEF_STRUCTURED_EXECUTION_MODE_ENV)
    try:
        execution_mode = cast(
            FitChefStructuredMode,
            normalize_execution_mode(raw_execution_mode),
        )
    except RuntimeError as exc:
        logger.error("FitChef structured execution mode misconfigured", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="agent_execution_mode_misconfigured",
        ) from exc

    try:
        require_execution_mode(execution_mode)
    except PermissionError:
        detail = f"agent_execution_{execution_mode.replace('-', '_')}"
        raise HTTPException(status_code=503, detail=detail)
    return execution_mode


@router.post(
    "/api/v1/pro/fitchef/explain",
    response_model=FitChefDistortionSimulatorResponse,
    responses={
        200: {"description": "FitChef distortion simulator generated"},
        400: {"description": "Unsafe AI input blocked", "model": FitChefCoachingErrorResponse},
        401: {"description": "API key required", "model": FitChefCoachingErrorResponse},
        403: {"description": "PRO tier required", "model": FitChefCoachingErrorResponse},
        503: {
            "description": "Feature disabled or provider unavailable",
            "model": FitChefCoachingErrorResponse,
        },
        504: {"description": "LLM provider call timed out", "model": FitChefCoachingErrorResponse},
        **RATE_LIMIT_429_RESPONSES,
    },
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def fitchef_distortion_simulator(
    payload: FitChefDistortionSimulatorRequest,
    request: Request,
    pro_key: str = Depends(require_pro_tier),
) -> FitChefDistortionSimulatorResponse:
    """Generate the bounded PRO distortion-simulator surface."""

    if not _is_fitchef_structured_enabled():
        raise HTTPException(status_code=503, detail="FEATURE_FITCHEF_STRUCTURED_COACH is disabled")

    execution_mode = _require_fitchef_structured_mode()
    task = FitChefDistortionSimulatorTaskEnvelope(
        mode=execution_mode,
        input=FitChefDistortionSimulatorInput(
            safe_situation=require_safe_ai_agent_input(payload.situation),
            safe_automatic_thought=require_safe_ai_agent_input(payload.automatic_thought),
            safe_emotion=require_safe_ai_agent_input(payload.emotion),
            safe_goal=(
                require_safe_ai_agent_input(payload.goal)
                if payload.goal is not None and payload.goal.strip()
                else None
            ),
            api_key=pro_key,
            endpoint=str(request.url.path),
            method=request.method,
        ),
    )
    result = await fitchef_runtime.run_distortion_simulator_task(task)
    return FitChefDistortionSimulatorResponse(
        scenario="distortion_simulator",
        distortion_labels=result.distortion_labels,
        why_it_matches=result.why_it_matches,
        evidence_for=result.evidence_for,
        evidence_against=result.evidence_against,
        balanced_reframe=result.balanced_reframe,
        next_small_action=result.next_small_action,
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
        quota_state=result.quota_state,
        transparency_notice_id=result.transparency_notice_id,
        wellness_boundary=result.wellness_boundary,
    )

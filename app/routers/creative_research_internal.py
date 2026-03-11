"""Hidden internal creative research pilot router.

RU: Internal-only router for the bounded creative research pilot.
EN: Internal-only router for the bounded creative research pilot.
"""

from __future__ import annotations

import logging
import os
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.middleware.api_tiers import require_vip_tier
from app.schemas.creative_research import (
    CreativeResearchPilotErrorResponse,
    CreativeResearchPilotInput,
    CreativeResearchPilotRequest,
    CreativeResearchPilotResult,
    CreativeResearchPilotTaskEnvelope,
)
from app.security.agent_control_plane import normalize_execution_mode, require_execution_mode
from app.security.agent_input_guard import require_safe_ai_agent_input
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)
from app.services.creative_research_runtime import run_creative_research_pilot_task
from app.telemetry.genai import agent_span
from app.utils.feature_flags import is_creative_research_pilot_enabled

logger = logging.getLogger(__name__)

# Sanctioned namespace exception: this pilot stays under /internal because it is
# operator-only, hidden from public OpenAPI, and not part of the public VIP API surface.
router = APIRouter(prefix="/api/v1/internal/creative-research", include_in_schema=False)

CREATIVE_RESEARCH_EXECUTION_MODE_ENV = "CREATIVE_RESEARCH_EXECUTION_MODE"
CreativeResearchExecutionMode = Literal["auto-safe", "review-required", "blocked"]


def _creative_research_feature_flags() -> dict[str, bool]:
    """Return deterministic feature-flag snapshot for tracing."""

    return {"creative_research_pilot": is_creative_research_pilot_enabled()}


@router.post(
    "/pilot",
    include_in_schema=False,
    response_model=CreativeResearchPilotResult,
    responses={
        200: {"description": "Creative research pilot result generated"},
        400: {
            "description": "Unsafe agent input blocked",
            "model": CreativeResearchPilotErrorResponse,
        },
        403: {"description": "VIP tier required", "model": CreativeResearchPilotErrorResponse},
        429: {"description": "Rate limit exceeded or monthly quota exhausted"},
        503: {
            "description": "Pilot disabled or provider unavailable",
            "model": CreativeResearchPilotErrorResponse,
        },
        504: {
            "description": "LLM provider call timed out",
            "model": CreativeResearchPilotErrorResponse,
        },
        **RATE_LIMIT_429_RESPONSES,
    },
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def creative_research_pilot(
    request_body: CreativeResearchPilotRequest,
    request: Request,
    vip_key: str = Depends(require_vip_tier),
) -> CreativeResearchPilotResult:
    """Run the internal-only creative research pilot."""

    if not is_creative_research_pilot_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FEATURE_CREATIVE_RESEARCH_PILOT is disabled",
        )

    try:
        execution_mode = cast(
            CreativeResearchExecutionMode,
            normalize_execution_mode(os.getenv(CREATIVE_RESEARCH_EXECUTION_MODE_ENV)),
        )
        require_execution_mode(execution_mode)
    except RuntimeError as exc:
        logger.error("Creative research execution mode misconfigured", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="agent_execution_mode_misconfigured",
        ) from exc
    except PermissionError:
        detail = f"agent_execution_{execution_mode.replace('-', '_')}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    safe_prompt_seed = require_safe_ai_agent_input(request_body.prompt_seed)
    safe_reference_corpus = [
        require_safe_ai_agent_input(item) for item in request_body.reference_corpus
    ]
    task = CreativeResearchPilotTaskEnvelope(
        mode=execution_mode,
        input=CreativeResearchPilotInput(
            prompt_seed=safe_prompt_seed,
            reference_corpus=safe_reference_corpus,
            candidate_count=request_body.candidate_count,
            api_key=vip_key,
            endpoint=str(request.url.path),
            method=request.method,
        ),
    )
    with agent_span(
        "creative research pilot",
        user_tier="VIP",
        route=str(request.url.path),
        feature_flags=_creative_research_feature_flags(),
    ):
        return await run_creative_research_pilot_task(task)

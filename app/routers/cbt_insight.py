"""
CBT Insight Router - PRO tier-gated endpoint for CBT-powered insights.

Uses RAG with agent-specific corpus filtering (docs/cbt/, docs/psychology/)
to provide CBT-informed responses via LLM.

Feature-gated via FEATURE_CBT_AGENT environment variable.
"""

from __future__ import annotations

import logging
import os
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from pydantic import BaseModel, Field

from app.middleware.api_tiers import require_pro_tier
from app.routers.api_key import api_key_header
from app.schemas.fitchef import FitChefCoachInsightInput, FitChefCoachInsightTaskEnvelope
from app.security.agent_control_plane import normalize_execution_mode, require_execution_mode
from app.security.agent_input_guard import require_safe_ai_agent_input
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)
from app.services import fitchef_runtime
from app.telemetry.genai import agent_span

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pro/cbt", tags=["CBT", "pro"])

CBT_EXECUTION_MODE_ENV = "CBT_AGENT_EXECUTION_MODE"
CBTExecutionMode = Literal["auto-safe", "review-required", "blocked"]
CBTQuotaState = Literal["not_consumed", "consumed"]


# ---------------------------------------------------------------------------
# Feature flag helper
# ---------------------------------------------------------------------------


def _is_cbt_agent_enabled() -> bool:
    """Check if CBT agent feature is enabled via environment variable."""
    return os.getenv("FEATURE_CBT_AGENT", "false").lower() in {"1", "true", "yes", "on"}


def _cbt_feature_flag_state() -> dict[str, bool]:
    """Return deterministic feature-flag snapshot for CBT tracing."""

    return {
        "cbt_agent": _is_cbt_agent_enabled(),
        "rag": os.getenv("FEATURE_RAG", "false").lower() in {"1", "true", "yes", "on"},
        "rag_vector": os.getenv("FEATURE_RAG_VECTOR", "false").lower()
        in {"1", "true", "yes", "on"},
    }


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class CBTInsightRequest(BaseModel):
    """Request schema for CBT insight endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User query for CBT-informed insight",
    )


class CBTSourceItem(BaseModel):
    """Single source from CBT corpus in response."""

    chunk_id: str
    file: str
    preview: str
    score: float


class CBTInsightResponse(BaseModel):
    """Response schema for CBT insight endpoint."""

    insight: str = Field(..., description="CBT-informed response from LLM")
    rag_used: bool = Field(..., description="Whether RAG context was used")
    sources: list[CBTSourceItem] = Field(
        ...,
        description="CBT corpus sources used for context",
    )
    confidence: float = Field(..., description="RAG retrieval confidence score")
    uncertainty: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Uncertainty score derived from confidence",
    )
    warnings: list[str] = Field(
        ...,
        description="Operational or retrieval warnings",
    )
    mode: CBTExecutionMode = Field(
        ...,
        description="Resolved agent execution mode",
    )
    quota_state: CBTQuotaState = Field(
        ...,
        description="Monthly quota state before provider call",
    )
    automated_analysis: bool = Field(
        default=True,
        description="Whether the response was generated through automated wellness analysis",
    )
    transparency_notice_id: str = Field(
        default="ai_generated_insight",
        description="Canonical transparency registry id for this AI surface",
    )
    wellness_boundary: str = Field(
        default="Wellness coaching only; not therapy, diagnosis, or clinical decision support.",
        description="High-level wellness boundary for this AI surface",
    )


@router.post(
    "/insight",
    response_model=CBTInsightResponse,
    responses={
        400: {"description": "Unsafe agent input blocked"},
        200: {"description": "CBT insight generated successfully"},
        401: {"description": "API key required for PRO tier access"},
        403: {"description": "API key does not have PRO tier access"},
        422: {"description": "Validation error in request"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "CBT agent feature disabled or unavailable"},
        504: {"description": "LLM provider call timed out"},
        **RATE_LIMIT_429_RESPONSES,
    },
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def cbt_insight(
    request: CBTInsightRequest,
    raw_request: Request,
    _api_key: str = Security(api_key_header),
    _tier: str = Depends(require_pro_tier),
) -> CBTInsightResponse:
    """Generate CBT-informed insight using RAG and LLM.

    Retrieves relevant context from CBT corpus (docs/cbt/, docs/psychology/)
    and generates a supportive response using LLM.

    Requires PRO tier API key.
    """
    # Check feature flag
    if not _is_cbt_agent_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CBT agent feature is not enabled",
        )

    try:
        execution_mode = cast(
            CBTExecutionMode,
            normalize_execution_mode(os.getenv(CBT_EXECUTION_MODE_ENV)),
        )
        require_execution_mode(execution_mode)
    except RuntimeError as exc:
        logger.error("CBT execution mode misconfigured", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="agent_execution_mode_misconfigured",
        ) from exc
    except PermissionError:
        detail = f"agent_execution_{execution_mode.replace('-', '_')}"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    safe_query = require_safe_ai_agent_input(request.query)
    task = FitChefCoachInsightTaskEnvelope(
        mode=execution_mode,
        input=FitChefCoachInsightInput(
            safe_query=safe_query,
            api_key=_api_key,
            endpoint=str(raw_request.url.path),
            method=raw_request.method,
        ),
    )
    with agent_span(
        "cbt insight agent",
        user_tier="PRO",
        route=str(raw_request.url.path),
        feature_flags=_cbt_feature_flag_state(),
    ):
        result = await fitchef_runtime.run_coach_insight_task(task)
    response = CBTInsightResponse(
        insight=result.insight,
        rag_used=result.rag_used,
        sources=[
            CBTSourceItem(
                chunk_id=item.chunk_id,
                file=item.file,
                preview=item.preview,
                score=item.score,
            )
            for item in result.sources
        ],
        confidence=result.confidence,
        uncertainty=result.uncertainty,
        warnings=result.warnings,
        mode=result.mode,
        quota_state=result.quota_state,
        automated_analysis=result.automated_analysis,
        transparency_notice_id=result.transparency_notice_id,
        wellness_boundary=result.wellness_boundary,
    )
    return response

"""
CBT Insight Router - PRO tier-gated endpoint for CBT-powered insights.

Uses RAG with agent-specific corpus filtering (docs/cbt/, docs/psychology/)
to provide CBT-informed responses via LLM.

Feature-gated via FEATURE_CBT_AGENT environment variable.
"""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.middleware.api_tiers import derive_subject_id_from_api_key, require_pro_tier
from app.routers.api_key import api_key_header
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pro/cbt", tags=["CBT", "pro"])

# LLM provider call timeout (seconds) - prevents unbounded requests
LLM_TIMEOUT_SECONDS: float = 60.0


# ---------------------------------------------------------------------------
# Feature flag helper
# ---------------------------------------------------------------------------


def _is_cbt_agent_enabled() -> bool:
    """Check if CBT agent feature is enabled via environment variable."""
    return os.getenv("FEATURE_CBT_AGENT", "false").lower() in {"1", "true", "yes", "on"}


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
    rag_used: bool = Field(default=False, description="Whether RAG context was used")
    sources: list[CBTSourceItem] = Field(
        default_factory=list,
        description="CBT corpus sources used for context",
    )
    confidence: float = Field(default=0.0, description="RAG retrieval confidence score")


# ---------------------------------------------------------------------------
# CBT prompt builder
# ---------------------------------------------------------------------------


def _build_cbt_prompt(query: str, rag_context: str) -> str:
    """Build CBT-informed prompt for LLM with RAG context.

    The system prompt establishes the CBT coaching role and boundaries.
    """
    system_prompt = """You are a supportive wellness coach using evidence-based CBT (Cognitive Behavioral Therapy) principles. Your role is to:

1. Help users identify and challenge unhelpful thought patterns
2. Suggest practical CBT techniques (thought records, cognitive restructuring)
3. Encourage self-compassion and gradual progress
4. Focus on nutrition and wellness goals

IMPORTANT BOUNDARIES:
- You are NOT a therapist and cannot provide therapy or diagnose conditions
- Avoid medical advice; suggest consulting professionals for health concerns
- If someone expresses crisis/self-harm thoughts, encourage them to seek professional help
- Use non-judgmental, supportive language

Respond with practical, actionable suggestions based on CBT principles."""

    if rag_context:
        return f"""{system_prompt}

RELEVANT CBT KNOWLEDGE:
{rag_context}

USER QUESTION:
{query}

Provide a helpful, CBT-informed response:"""
    else:
        return f"""{system_prompt}

USER QUESTION:
{query}

Provide a helpful, CBT-informed response:"""


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/insight",
    response_model=CBTInsightResponse,
    responses={
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

    # Retrieve RAG context with CBT corpus filtering
    rag_context_str = ""
    sources: list[CBTSourceItem] = []
    confidence = 0.0
    rag_used = False

    try:
        from core.rag.vector_rag import retrieve_context_structured

        rag_ctx = await run_in_threadpool(
            retrieve_context_structured,
            request.query,
            max_chunks=5,
            agent_id="cbt-agent",
            user_tier="PRO",
            subject_id=derive_subject_id_from_api_key(_api_key),
        )

        if rag_ctx.chunks:
            rag_used = True
            confidence = rag_ctx.confidence

            # Build context string from chunks
            context_parts = []
            for chunk in rag_ctx.chunks:
                context_parts.append(f"[{chunk.file}]\n{chunk.content}")
                sources.append(
                    CBTSourceItem(
                        chunk_id=chunk.chunk_id,
                        file=chunk.file,
                        preview=(
                            chunk.content[:200] + "..."
                            if len(chunk.content) > 200
                            else chunk.content
                        ),
                        score=chunk.score,
                    )
                )
            rag_context_str = "\n\n".join(context_parts)

    except Exception:
        logger.warning("RAG retrieval failed for CBT insight", exc_info=True)
        # Continue without RAG context

    # Build prompt with RAG context
    prompt = _build_cbt_prompt(request.query, rag_context_str)

    # Generate insight via LLM
    try:
        from llm import get_provider

        provider = get_provider()
        insight_text = await asyncio.wait_for(
            run_in_threadpool(provider.generate, prompt),
            timeout=LLM_TIMEOUT_SECONDS,
        )

        if not insight_text:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider returned empty response",
            )

    except ImportError:
        logger.error("LLM provider not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider not available",
        )
    except asyncio.TimeoutError:
        logger.error("LLM provider call timed out after %s seconds", LLM_TIMEOUT_SECONDS)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLM provider call timed out",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM generation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate CBT insight",
        )

    return CBTInsightResponse(
        insight=insight_text,
        rag_used=rag_used,
        sources=sources,
        confidence=confidence,
    )

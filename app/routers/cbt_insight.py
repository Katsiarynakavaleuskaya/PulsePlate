"""
CBT Insight Router - PRO tier-gated endpoint for CBT-powered insights.

Uses RAG with agent-specific corpus filtering (docs/cbt/, docs/psychology/)
to provide CBT-informed responses via LLM.

Feature-gated via FEATURE_CBT_AGENT environment variable.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.middleware.api_tiers import derive_subject_id_from_api_key, require_pro_tier
from app.routers.api_key import api_key_header
from app.security.agent_control_plane import (
    AUDIT_SIGNING_KEY_ENV,
    normalize_execution_mode,
    persist_audit_envelope,
    require_execution_mode,
    require_policy_allow,
    sign_audit_envelope,
)
from app.security.agent_input_guard import require_safe_ai_agent_input
from app.security.llm_monthly_quota import attempt_consume_llm_monthly_quota
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)
from app.security.server_salt import require_server_salt
from core.data_sanitizer import sanitize_rag_markdown
from core.pii_redaction import redact_pii_from_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pro/cbt", tags=["CBT", "pro"])

# LLM provider call timeout (seconds) - prevents unbounded requests
LLM_TIMEOUT_SECONDS: float = 60.0
CBT_EXECUTION_MODE_ENV = "CBT_AGENT_EXECUTION_MODE"
CBT_POLICY_ALLOWLIST = {
    ("rag.retrieve", "corpus://cbt-agent"),
    ("llm.generate", "provider://default"),
}
CBTExecutionMode = Literal["auto-safe", "review-required", "blocked"]
CBTQuotaState = Literal["not_consumed", "consumed"]


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
    return f"""{system_prompt}

USER QUESTION:
{query}

Provide a helpful, CBT-informed response:"""


def _sha256_hex(value: str) -> str:
    """Return deterministic sha256 hex digest for audit-safe metadata."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _persist_privileged_action_audit(
    *,
    action: str,
    target: str,
    mode: str,
    endpoint: str,
    metadata: dict[str, object],
) -> None:
    """Run policy gate and persist a signed audit envelope before privileged work."""

    decision = require_policy_allow(action, target, allowlist=CBT_POLICY_ALLOWLIST)
    audit_metadata = {
        "endpoint": endpoint,
        "mode": mode,
        **metadata,
    }
    signing_secret = (os.getenv(AUDIT_SIGNING_KEY_ENV) or "").strip() or require_server_salt()
    envelope = sign_audit_envelope(
        decision,
        metadata=audit_metadata,
        secret=signing_secret,
    )
    persist_audit_envelope(envelope, metadata=audit_metadata)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


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

    # Retrieve RAG context with CBT corpus filtering
    rag_context_str = ""
    sources: list[CBTSourceItem] = []
    confidence = 0.0
    rag_used = False
    quota_state: CBTQuotaState = "not_consumed"
    warnings: list[str] = []
    redaction_applied = False
    sanitization_applied = False

    try:
        await run_in_threadpool(
            _persist_privileged_action_audit,
            action="rag.retrieve",
            target="corpus://cbt-agent",
            mode=execution_mode,
            endpoint=str(raw_request.url.path),
            metadata={
                "method": raw_request.method,
                "query_hash": _sha256_hex(safe_query),
                "query_length": len(safe_query),
            },
        )
    except (PermissionError, RuntimeError) as exc:
        logger.error("RAG privileged-action gate failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="rag_retrieval_unavailable",
        ) from exc

    try:
        from core.rag.vector_rag import retrieve_context_structured

        rag_ctx = await run_in_threadpool(
            retrieve_context_structured,
            safe_query,
            max_chunks=5,
            agent_id="cbt-agent",
            user_tier="PRO",
            subject_id=derive_subject_id_from_api_key(_api_key),
        )

        if rag_ctx.chunks:
            # Build context string from chunks
            context_parts = []
            for chunk in rag_ctx.chunks:
                sanitized_chunk = sanitize_rag_markdown(chunk.content)
                if sanitized_chunk != chunk.content:
                    sanitization_applied = True
                sanitized_content = redact_pii_from_text(sanitized_chunk) or ""
                if sanitized_content != sanitized_chunk:
                    redaction_applied = True
                if not sanitized_content.strip():
                    continue
                context_parts.append(f"[{chunk.file}]\n{sanitized_content}")
                sources.append(
                    CBTSourceItem(
                        chunk_id=chunk.chunk_id,
                        file=chunk.file,
                        preview=(
                            sanitized_content[:200] + "..."
                            if len(sanitized_content) > 200
                            else sanitized_content
                        ),
                        score=chunk.score,
                    )
                )
            if context_parts:
                rag_used = True
                confidence = rag_ctx.confidence
                rag_context_str = "\n\n".join(context_parts)

    except Exception:
        logger.warning("RAG retrieval failed for CBT insight", exc_info=True)
        warnings.append("rag_retrieval_failed")
        # Continue without RAG context

    if sanitization_applied:
        warnings.append("source_content_sanitized")

    if redaction_applied:
        warnings.append("source_content_redacted")

    # Build prompt with RAG context
    prompt = _build_cbt_prompt(safe_query, rag_context_str)

    # Generate insight via LLM
    try:
        await run_in_threadpool(
            _persist_privileged_action_audit,
            action="llm.generate",
            target="provider://default",
            mode=execution_mode,
            endpoint=str(raw_request.url.path),
            metadata={
                "method": raw_request.method,
                "prompt_hash": _sha256_hex(prompt),
                "prompt_length": len(prompt),
                "rag_used": rag_used,
                "source_count": len(sources),
            },
        )
    except (PermissionError, RuntimeError) as exc:
        logger.error("LLM privileged-action gate failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="llm_generation_unavailable",
        ) from exc
    try:
        allowed = await run_in_threadpool(
            attempt_consume_llm_monthly_quota,
            _api_key,
            tier="PRO",
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="quota_exceeded"
            )
        quota_state = "consumed"

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

    bounded_confidence = min(max(confidence, 0.0), 1.0)
    return CBTInsightResponse(
        insight=insight_text,
        rag_used=rag_used,
        sources=sources,
        confidence=bounded_confidence,
        uncertainty=round(max(0.0, 1.0 - bounded_confidence), 4),
        warnings=warnings,
        mode=execution_mode,
        quota_state=quota_state,
    )

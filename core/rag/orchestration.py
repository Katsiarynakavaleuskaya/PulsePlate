"""RAG orchestration — retrieval + philosophy validation pipeline.

Encapsulates the RAG retrieval → validation → prompt building flow so that
``legacy_app.py`` remains a thin proxy (AGENTS.md policy).

Feature-gated via ``FEATURE_PHILOSOPHY_VALIDATION``.

On any internal exception the orchestrator returns empty result (fail-safe).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from starlette.concurrency import run_in_threadpool

if TYPE_CHECKING:
    from core.rag.contracts import RAGChunk

logger = logging.getLogger(__name__)


@dataclass
class RAGOrchestrationResult:
    """Result of RAG retrieval + validation pipeline."""

    chunks: list["RAGChunk"]
    """Filtered chunks that passed validation (empty if none survived)."""

    formatted_prompt: str
    """Prompt text with RAG context included (or original if no chunks)."""

    rag_actually_used: bool
    """True if chunks contributed to the prompt (not just retrieved)."""

    confidence: Optional[float]
    """Mean score of filtered chunks (None if no chunks used)."""

    hops: int
    """Number of retrieval hops from RAG context."""

    latency_ms: int
    """RAG retrieval latency in milliseconds."""

    warnings: list[str] = field(default_factory=list)
    """Validation warnings (weasel words, medical boundary matches)."""

    chunks_retrieved: int = 0
    """Total chunks retrieved before validation."""

    chunks_filtered: int = 0
    """Number of chunks removed by validation."""


def _empty_result(prompt_input: str) -> RAGOrchestrationResult:
    """Return empty orchestration result (fail-safe fallback)."""
    return RAGOrchestrationResult(
        chunks=[],
        formatted_prompt=prompt_input,
        rag_actually_used=False,
        confidence=None,
        hops=0,
        latency_ms=0,
        warnings=[],
        chunks_retrieved=0,
        chunks_filtered=0,
    )


async def retrieve_and_validate_rag(
    prompt_input: str,
    max_chunks: int = 3,
) -> RAGOrchestrationResult:
    """Orchestrate RAG retrieval + philosophy validation.

    Retrieves chunks via vector RAG, applies philosophy validation if enabled,
    and builds the formatted prompt with RAG context.

    Parameters
    ----------
    prompt_input:
        User query text for RAG retrieval.
    max_chunks:
        Maximum chunks to retrieve (default 3).

    Returns
    -------
    RAGOrchestrationResult
        Contains filtered chunks, formatted prompt, and metadata.
        On any failure returns empty result (fail-safe).

    Notes
    -----
    - Feature flag ``FEATURE_PHILOSOPHY_VALIDATION`` controls validation
    - Lazy imports preserve fail-safe behavior (missing modules don't crash)
    - Confidence is recalculated from filtered chunks when validation enabled
    """
    try:
        return await _run_orchestration(prompt_input, max_chunks)
    except Exception:
        logger.warning(
            "RAG orchestration failed; returning empty result",
            exc_info=True,
        )
        return _empty_result(prompt_input)


async def _run_orchestration(
    prompt_input: str,
    max_chunks: int,
) -> RAGOrchestrationResult:
    """Execute RAG retrieval + validation pipeline."""
    # Lazy imports to preserve fail-safe behavior (missing modules don't crash)
    from core.rag.formatting import format_rag_chunks_for_prompt
    from core.rag.vector_rag import retrieve_context_structured

    # Retrieve chunks
    rag_ctx = await run_in_threadpool(
        retrieve_context_structured, prompt_input, max_chunks=max_chunks
    )

    if not rag_ctx.chunks:
        return RAGOrchestrationResult(
            chunks=[],
            formatted_prompt=prompt_input,
            rag_actually_used=False,
            confidence=None,
            hops=rag_ctx.hops,
            latency_ms=rag_ctx.latency_ms,
            warnings=[],
            chunks_retrieved=0,
            chunks_filtered=0,
        )

    # Check philosophy validation flag
    from app.utils.feature_flags import is_philosophy_validation_enabled

    philo_enabled = is_philosophy_validation_enabled()
    warnings: list[str] = []
    chunks_to_use = rag_ctx.chunks
    chunks_filtered = 0

    if philo_enabled:
        from core.rag.validation import validate_rag_chunks

        val_result = validate_rag_chunks(rag_ctx.chunks)
        chunks_to_use = val_result.filtered_chunks
        chunks_filtered = val_result.rejected_count
        warnings = val_result.warnings

        for w in warnings:
            logger.debug("rag_validation: %s", w)

    # If no chunks survived validation
    if not chunks_to_use:
        return RAGOrchestrationResult(
            chunks=[],
            formatted_prompt=prompt_input,
            rag_actually_used=False,
            confidence=None,
            hops=rag_ctx.hops,
            latency_ms=rag_ctx.latency_ms,
            warnings=warnings,
            chunks_retrieved=len(rag_ctx.chunks),
            chunks_filtered=chunks_filtered,
        )

    # Calculate confidence
    if philo_enabled:
        confidence: Optional[float] = round(
            sum(c.score for c in chunks_to_use) / len(chunks_to_use),
            4,
        )
    else:
        confidence = round(rag_ctx.confidence, 4)

    # Build formatted prompt with RAG context
    from core.insight.safety import redact_rag_context_for_insight

    raw_context = format_rag_chunks_for_prompt(chunks_to_use)
    redacted_context = redact_rag_context_for_insight(raw_context)
    formatted_prompt = _build_prompt_with_context(prompt_input, redacted_context)

    return RAGOrchestrationResult(
        chunks=chunks_to_use,
        formatted_prompt=formatted_prompt,
        rag_actually_used=True,
        confidence=confidence,
        hops=rag_ctx.hops,
        latency_ms=rag_ctx.latency_ms,
        warnings=warnings,
        chunks_retrieved=len(rag_ctx.chunks),
        chunks_filtered=chunks_filtered,
    )


def _build_prompt_with_context(text: str, context: Optional[str]) -> str:
    """Build prompt with RAG context prefix.

    Mirrors logic from legacy_app._build_insight_prompt but without
    the INSIGHT_TEXT_MAX_LENGTH truncation (caller handles that).
    """
    if not context:
        return text
    return f"Context:\n{context}\n\nQuestion: {text}\nAnswer:"

"""RAG orchestration — retrieval + philosophy validation pipeline.

Encapsulates the RAG retrieval → validation → prompt building flow so that
``legacy_app.py`` remains a thin proxy (AGENTS.md policy).

Feature-gated via ``FEATURE_PHILOSOPHY_VALIDATION``.

On any internal exception the orchestrator returns empty result (fail-safe).
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, SupportsFloat, cast

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

    recursive_executed: bool = False
    """True when the recursive retrieval path actually executed."""


def _empty_result(
    prompt_input: str,
    *,
    recursive_executed: bool = False,
) -> RAGOrchestrationResult:
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
        recursive_executed=recursive_executed,
    )


def _normalize_confidence_value(value: object) -> float | None:
    """Return a finite rounded confidence value or ``None`` for malformed input."""

    if isinstance(value, (str, bytes, bytearray, int, float)):
        candidate: SupportsFloat | str | bytes | bytearray = value
    elif hasattr(value, "__float__"):
        candidate = cast(SupportsFloat, value)
    else:
        return None

    try:
        numeric = float(candidate)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return round(numeric, 4)


def _mean_chunk_score(chunks: list["RAGChunk"]) -> float | None:
    """Return the mean of valid chunk scores, ignoring malformed values."""

    normalized_scores = [
        normalized
        for chunk in chunks
        if (normalized := _normalize_confidence_value(chunk.score)) is not None
    ]
    if not normalized_scores:
        return None
    return round(sum(normalized_scores) / len(normalized_scores), 4)


def _resolve_confidence(
    *,
    chunks_to_use: list["RAGChunk"],
) -> float | None:
    """Resolve final confidence from the chunks that actually reach the output."""

    return _mean_chunk_score(chunks_to_use)


async def retrieve_and_validate_rag(
    prompt_input: str,
    max_chunks: int = 3,
    *,
    philo_validation_enabled: bool = False,
    recursive_rag_enabled: bool = False,
    subject_id: int | None = None,
) -> RAGOrchestrationResult:
    """Orchestrate RAG retrieval + philosophy validation.

    Retrieves chunks via vector/recursive RAG, applies philosophy validation
    when required, and builds the formatted prompt with RAG context.

    Parameters
    ----------
    prompt_input:
        User query text for RAG retrieval.
    max_chunks:
        Maximum chunks to retrieve (default 3).
    philo_validation_enabled:
        Whether to run philosophy validation on chunks (feature flag).
    recursive_rag_enabled:
        Whether to run recursive multi-hop retrieval path.
    subject_id:
        Authenticated tenant/user identifier for personalized retrieval.
        Pass a concrete value for tenant-scoped `user_knowledge` access.
        Passing `None` is fail-closed: vector retrieval must not read
        tenant-scoped data and the pipeline falls back to non-personal
        retrieval only.

    Returns
    -------
    RAGOrchestrationResult
        Contains filtered chunks, formatted prompt, and metadata.
        On any failure returns empty result (fail-safe).

    Notes
    -----
    - Caller passes feature flag state (keeps core/ decoupled from app/)
    - Lazy imports preserve fail-safe behavior (missing modules don't crash)
    - Confidence is always derived from the chunks that reach the output
    - `recursive_rag_enabled` and `philo_validation_enabled` do not weaken
      tenant isolation; both paths propagate the same `subject_id`
    """
    return await _run_orchestration(
        prompt_input,
        max_chunks,
        philo_validation_enabled,
        recursive_rag_enabled,
        subject_id,
    )


async def _run_orchestration(
    prompt_input: str,
    max_chunks: int,
    philo_enabled: bool,
    recursive_enabled: bool,
    subject_id: int | None,
) -> RAGOrchestrationResult:
    """Execute RAG retrieval + validation pipeline."""
    recursive_executed = False
    try:
        # Lazy imports to preserve fail-safe behavior (missing modules don't crash)
        from core.rag.formatting import format_rag_chunks_for_prompt

        if recursive_enabled:
            from app.utils.feature_flags import is_recursive_rag_optimization_enabled
            from core.rag.recursive_retrieval import retrieve_recursive_context_structured

            optimization_enabled = is_recursive_rag_optimization_enabled()
            rag_ctx = await asyncio.to_thread(
                retrieve_recursive_context_structured,
                prompt_input,
                max_chunks=max_chunks,
                subject_id=subject_id,
                philo_validation_enabled=False,
                optimization_enabled=optimization_enabled,
            )
            recursive_executed = True
        else:
            from core.rag.vector_rag import retrieve_context_structured

            rag_ctx = await asyncio.to_thread(
                retrieve_context_structured,
                prompt_input,
                max_chunks=max_chunks,
                subject_id=subject_id,
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
                recursive_executed=recursive_executed,
            )

        warnings: list[str] = []
        chunks_to_use = rag_ctx.chunks
        chunks_filtered = 0

        if philo_enabled:
            from core.rag.philosophy_pipeline import run_pipeline

            pipeline_result = run_pipeline(rag_ctx.chunks, query=prompt_input)
            chunks_to_use = pipeline_result.filtered_chunks
            chunks_filtered = len(rag_ctx.chunks) - len(pipeline_result.filtered_chunks)
            warnings = pipeline_result.warnings

            for w in warnings:
                logger.debug("rag_pipeline: %s", w)

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
                recursive_executed=recursive_executed,
            )

        confidence = _resolve_confidence(
            chunks_to_use=chunks_to_use,
        )

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
            recursive_executed=recursive_executed,
        )
    except Exception:
        logger.warning(
            "RAG orchestration failed; returning empty result",
            exc_info=True,
        )
        return _empty_result(
            prompt_input,
            recursive_executed=recursive_executed,
        )


def _build_prompt_with_context(text: str, context: Optional[str]) -> str:
    """Build prompt with RAG context prefix.

    Mirrors logic from legacy_app._build_insight_prompt but without
    the INSIGHT_TEXT_MAX_LENGTH truncation (caller handles that).
    """
    if not context:
        return text
    return f"Context:\n{context}\n\nQuestion: {text}\nAnswer:"

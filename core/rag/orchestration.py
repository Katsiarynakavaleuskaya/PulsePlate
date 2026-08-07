"""RAG orchestration — retrieval + mandatory baseline validation pipeline.

Encapsulates the RAG retrieval → validation → prompt building flow so that
``legacy_app.py`` remains a thin proxy (AGENTS.md policy).

``FEATURE_PHILOSOPHY_VALIDATION`` controls advisory post-Stage-1 enrichment;
baseline validation is always applied to final request-local retrieval chunks.

On any internal exception the orchestrator returns empty result (fail-safe).
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Sequence, SupportsFloat, cast

if TYPE_CHECKING:
    from core.knowledge.contracts import KnowledgeFactCandidate
    from core.knowledge.policy import KnowledgePolicy
    from core.rag.contracts import RecursiveOptimizationHints
    from core.verification.contracts import VerificationBundle

from core.rag.contracts import RAGChunk, RAGContext, RAGDegradedReason

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

    degraded_reason: RAGDegradedReason | None = None
    """Deterministic internal degraded-path reason (not part of public API)."""

    knowledge_candidates: list["KnowledgeFactCandidate"] = field(default_factory=list)
    """Internal-only promotion candidates derived from validated evidence."""

    knowledge_candidates_canonical: bool = False
    """True only when candidates come from the canonical validated orchestration path."""

    verification_bundle: "VerificationBundle | None" = None
    """Canonical pre-generation verification bundle for internal write admission."""

    verification_calls: int = 0
    """Recursive verification call count observed during retrieval."""


def _empty_result(
    prompt_input: str,
    *,
    recursive_executed: bool = False,
    degraded_reason: RAGDegradedReason | None = None,
    verification_bundle: "VerificationBundle | None" = None,
    verification_calls: int = 0,
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
        degraded_reason=degraded_reason,
        verification_bundle=verification_bundle,
        verification_calls=verification_calls,
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


def _copy_rag_chunks(chunks: Sequence[RAGChunk]) -> list[RAGChunk]:
    """Return primitive-equivalent copies for mutable helper boundaries."""

    return [
        RAGChunk(
            chunk_id=chunk.chunk_id,
            file=chunk.file,
            content=chunk.content,
            score=chunk.score,
            hop=chunk.hop,
        )
        for chunk in chunks
    ]


def _has_context_text(value: object) -> bool:
    """Return whether a context payload is a non-empty string."""

    return isinstance(value, str) and bool(value.strip())


def _non_rag_result(
    prompt_input: str,
    *,
    rag_ctx_hops: int,
    rag_ctx_latency_ms: int,
    warnings: list[str],
    chunks_retrieved: int,
    chunks_filtered: int,
    recursive_executed: bool,
    degraded_reason: RAGDegradedReason,
    verification_bundle: "VerificationBundle | None" = None,
    verification_calls: int = 0,
) -> RAGOrchestrationResult:
    """Return a non-RAG result when no usable context survives to output."""

    return RAGOrchestrationResult(
        chunks=[],
        formatted_prompt=prompt_input,
        rag_actually_used=False,
        confidence=None,
        hops=rag_ctx_hops,
        latency_ms=rag_ctx_latency_ms,
        warnings=warnings,
        chunks_retrieved=chunks_retrieved,
        chunks_filtered=chunks_filtered,
        recursive_executed=recursive_executed,
        degraded_reason=degraded_reason,
        verification_bundle=verification_bundle,
        verification_calls=verification_calls,
    )


async def retrieve_and_validate_rag(
    prompt_input: str,
    max_chunks: int = 3,
    *,
    philo_validation_enabled: bool = False,
    recursive_rag_enabled: bool = False,
    optimization_enabled: bool = False,
    recursive_optimization_hints: "RecursiveOptimizationHints | None" = None,
    subject_id: int | None = None,
    knowledge_policy: "KnowledgePolicy | None" = None,
) -> RAGOrchestrationResult:
    """Orchestrate RAG retrieval + philosophy validation.

    Retrieves chunks via vector/recursive RAG, always applies baseline
    validation, optionally enriches validation diagnostics, and builds the
    formatted prompt with RAG context.

    Parameters
    ----------
    prompt_input:
        User query text for RAG retrieval.
    max_chunks:
        Maximum chunks to retrieve (default 3).
    philo_validation_enabled:
        Whether to run advisory post-Stage-1 enrichment (feature flag).
    recursive_rag_enabled:
        Whether to run recursive multi-hop retrieval path.
    optimization_enabled:
        Enables recursive optimization behavior when recursive retrieval runs.
    recursive_optimization_hints:
        Optional prepared recursive optimization constraints forwarded to
        recursive retrieval. Defaults to `None` and has no effect unless
        `optimization_enabled` is true.
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
        optimization_enabled,
        recursive_optimization_hints,
        subject_id,
        knowledge_policy,
    )


async def _run_orchestration(
    prompt_input: str,
    max_chunks: int,
    philo_enabled: bool,
    recursive_enabled: bool,
    optimization_enabled: bool,
    recursive_optimization_hints: "RecursiveOptimizationHints | None",
    subject_id: int | None,
    knowledge_policy: "KnowledgePolicy | None",
) -> RAGOrchestrationResult:
    """Execute RAG retrieval + validation pipeline."""
    recursive_executed = False
    rag_ctx: RAGContext | None = None
    warnings: list[str] = []
    chunks_filtered = 0
    verification_calls = 0
    enrichment_completed = False
    try:
        # Lazy imports to preserve fail-safe behavior (missing modules don't crash)
        from core.rag.formatting import (
            _prepare_final_rag_chunk_snapshot,
            format_rag_chunks_for_prompt,
        )

        if recursive_enabled:
            from core.rag.recursive_retrieval import retrieve_recursive_context_structured

            rag_ctx = await asyncio.to_thread(
                retrieve_recursive_context_structured,
                prompt_input,
                max_chunks=max_chunks,
                subject_id=subject_id,
                philo_validation_enabled=False,
                optimization_enabled=optimization_enabled,
                optimization_hints=recursive_optimization_hints,
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

        if rag_ctx is None:
            logger.warning(
                "RAG orchestration produced no retrieval context; returning empty result",
            )
            return _empty_result(
                prompt_input,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.ORCHESTRATION_EXCEPTION,
            )

        verification_calls = _extract_recursive_verification_calls(rag_ctx)

        from core.rag.philosophy_pipeline import run_pipeline

        pipeline_result = run_pipeline(
            rag_ctx.chunks,
            query=prompt_input,
            enrichment_enabled=philo_enabled,
        )
        pipeline_survivors = _copy_rag_chunks(pipeline_result.filtered_chunks)
        chunks_filtered = max(0, len(rag_ctx.chunks) - len(pipeline_survivors))
        warnings = list(pipeline_result.warnings)

        # If no chunks survived validation
        if not pipeline_survivors:
            degraded_reason = getattr(rag_ctx, "degraded_reason", None) or (
                RAGDegradedReason.RETRIEVAL_EMPTY
                if not rag_ctx.chunks
                else RAGDegradedReason.ALL_CHUNKS_FILTERED
            )
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=degraded_reason,
                verification_bundle=_build_orchestration_verification_bundle(
                    knowledge_policy=knowledge_policy,
                    confidence=None,
                    degraded_reason=degraded_reason,
                    rag_actually_used=False,
                    enrichment_completed=enrichment_completed,
                    recursive_executed=recursive_executed,
                    verification_calls=verification_calls,
                    chunks=(),
                    prompt_input=prompt_input,
                    verification_hops=rag_ctx.hops,
                ),
                verification_calls=verification_calls,
            )

        chunks_to_use, had_sanitized_survivor = _prepare_final_rag_chunk_snapshot(
            _copy_rag_chunks(pipeline_survivors)
        )
        chunks_filtered = max(0, len(rag_ctx.chunks) - len(chunks_to_use))
        enrichment_completed = (
            bool(chunks_to_use) and pipeline_result.post_stage1_enrichment_completed
        )

        def _degraded_verification_bundle(
            degraded_reason: RAGDegradedReason,
        ) -> VerificationBundle:
            """Build empty admission truth for post-retrieval degradation branches."""

            return _build_orchestration_verification_bundle(
                knowledge_policy=knowledge_policy,
                confidence=None,
                degraded_reason=degraded_reason,
                rag_actually_used=False,
                enrichment_completed=enrichment_completed,
                recursive_executed=recursive_executed,
                verification_calls=verification_calls,
                chunks=(),
                prompt_input=prompt_input,
                verification_hops=rag_ctx.hops,
            )

        if not had_sanitized_survivor:
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.FORMATTED_CONTEXT_EMPTY,
                verification_bundle=_degraded_verification_bundle(
                    RAGDegradedReason.FORMATTED_CONTEXT_EMPTY
                ),
                verification_calls=verification_calls,
            )
        if not chunks_to_use:
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.REDACTED_CONTEXT_EMPTY,
                verification_bundle=_degraded_verification_bundle(
                    RAGDegradedReason.REDACTED_CONTEXT_EMPTY
                ),
                verification_calls=verification_calls,
            )

        confidence = _resolve_confidence(
            chunks_to_use=chunks_to_use,
        )

        # Build formatted prompt with RAG context
        from core.insight.safety import redact_rag_context_for_insight

        raw_context = format_rag_chunks_for_prompt(_copy_rag_chunks(chunks_to_use))
        if not isinstance(raw_context, str):
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED,
                verification_bundle=_degraded_verification_bundle(
                    RAGDegradedReason.FORMATTED_CONTEXT_MALFORMED
                ),
                verification_calls=verification_calls,
            )
        if not raw_context.strip():
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.FORMATTED_CONTEXT_EMPTY,
                verification_bundle=_degraded_verification_bundle(
                    RAGDegradedReason.FORMATTED_CONTEXT_EMPTY
                ),
                verification_calls=verification_calls,
            )
        redacted_context = redact_rag_context_for_insight(raw_context)
        if not isinstance(redacted_context, str):
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.REDACTED_CONTEXT_MALFORMED,
                verification_bundle=_degraded_verification_bundle(
                    RAGDegradedReason.REDACTED_CONTEXT_MALFORMED
                ),
                verification_calls=verification_calls,
            )
        if not redacted_context.strip():
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.REDACTED_CONTEXT_EMPTY,
                verification_bundle=_degraded_verification_bundle(
                    RAGDegradedReason.REDACTED_CONTEXT_EMPTY
                ),
                verification_calls=verification_calls,
            )
        formatted_prompt = _build_prompt_with_context(prompt_input, redacted_context)
        verification_bundle = _build_orchestration_verification_bundle(
            knowledge_policy=knowledge_policy,
            confidence=confidence,
            degraded_reason=getattr(rag_ctx, "degraded_reason", None),
            rag_actually_used=True,
            enrichment_completed=enrichment_completed,
            recursive_executed=recursive_executed,
            verification_calls=verification_calls,
            chunks=chunks_to_use,
            prompt_input=prompt_input,
            prompt_text=formatted_prompt,
            verification_hops=rag_ctx.hops,
        )
        knowledge_candidates_canonical = (
            bool(chunks_to_use)
            and enrichment_completed
            and getattr(rag_ctx, "degraded_reason", None) is None
            and not recursive_executed
            and verification_bundle.admission_allowed
        )
        knowledge_candidates: list["KnowledgeFactCandidate"] = []
        if knowledge_candidates_canonical:
            try:
                knowledge_candidates = _build_knowledge_candidates(
                    chunks_to_use=_copy_rag_chunks(chunks_to_use),
                    confidence=confidence,
                    degraded_reason=None,
                    subject_id=subject_id,
                    knowledge_policy=knowledge_policy,
                    verification_bundle=verification_bundle,
                )
            except Exception:
                logger.warning(
                    "Knowledge candidate construction failed; preserving validated RAG response"
                )
                knowledge_candidates = []
                knowledge_candidates_canonical = False

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
            degraded_reason=getattr(rag_ctx, "degraded_reason", None),
            knowledge_candidates=knowledge_candidates,
            knowledge_candidates_canonical=knowledge_candidates_canonical,
            verification_bundle=verification_bundle,
            verification_calls=verification_calls,
        )
    except Exception:
        logger.warning("RAG orchestration failed; returning empty result")
        if rag_ctx is not None:
            return _non_rag_result(
                prompt_input,
                rag_ctx_hops=rag_ctx.hops,
                rag_ctx_latency_ms=rag_ctx.latency_ms,
                warnings=warnings,
                chunks_retrieved=len(rag_ctx.chunks),
                chunks_filtered=chunks_filtered,
                recursive_executed=recursive_executed,
                degraded_reason=RAGDegradedReason.POST_RETRIEVAL_ORCHESTRATION_EXCEPTION,
                verification_bundle=_build_orchestration_verification_bundle(
                    knowledge_policy=knowledge_policy,
                    confidence=None,
                    degraded_reason=RAGDegradedReason.POST_RETRIEVAL_ORCHESTRATION_EXCEPTION,
                    rag_actually_used=False,
                    enrichment_completed=enrichment_completed,
                    recursive_executed=recursive_executed,
                    verification_calls=verification_calls,
                    chunks=(),
                    prompt_input=prompt_input,
                    verification_hops=rag_ctx.hops,
                ),
                verification_calls=verification_calls,
            )
        return _empty_result(
            prompt_input,
            recursive_executed=recursive_executed,
            degraded_reason=RAGDegradedReason.ORCHESTRATION_EXCEPTION,
        )


def _build_prompt_with_context(text: str, context: Optional[str]) -> str:
    """Build prompt with RAG context prefix.

    Mirrors logic from legacy_app._build_insight_prompt but without
    the INSIGHT_TEXT_MAX_LENGTH truncation (caller handles that).
    """
    if not context:
        return text
    return f"Context:\n{context}\n\nQuestion: {text}\nAnswer:"


def _build_knowledge_candidates(
    *,
    chunks_to_use: list["RAGChunk"],
    confidence: float | None,
    degraded_reason: RAGDegradedReason | None,
    subject_id: int | None,
    knowledge_policy: "KnowledgePolicy | None",
    verification_bundle: "VerificationBundle | None",
) -> list["KnowledgeFactCandidate"]:
    """Build internal knowledge candidates from validated evidence or fail closed."""

    if knowledge_policy is None:
        return []

    from core.knowledge.promotion import build_knowledge_promotion_candidates

    candidates: list["KnowledgeFactCandidate"] = build_knowledge_promotion_candidates(
        chunks=chunks_to_use,
        confidence=confidence,
        degraded_reason=None if degraded_reason is None else degraded_reason.value,
        subject_id=subject_id,
        knowledge_policy=knowledge_policy,
        verification_bundle=verification_bundle,
    )
    return candidates


def _extract_recursive_verification_calls(rag_ctx: RAGContext | None) -> int:
    """Return recursive verification call count from optimization diagnostics."""

    optimization_stats = getattr(rag_ctx, "optimization_stats", None)
    if not isinstance(optimization_stats, dict):
        return 0
    value = optimization_stats.get("verification_calls", 0)
    return value if type(value) is int and value >= 0 else 0


def _build_orchestration_verification_bundle(
    *,
    knowledge_policy: "KnowledgePolicy | None",
    confidence: float | None,
    degraded_reason: RAGDegradedReason | None,
    rag_actually_used: bool,
    enrichment_completed: bool,
    recursive_executed: bool,
    verification_calls: int,
    chunks: Sequence["RAGChunk"],
    prompt_input: str | None = None,
    prompt_text: str | None = None,
    verification_hops: int = 0,
) -> "VerificationBundle":
    """Materialize the canonical pre-generation verification bundle."""

    from core.verification.registry import (
        build_rag_verification_bundle,
        build_verification_provenance,
    )

    evidence_refs = tuple(f"{chunk.file}:{chunk.chunk_id}" for chunk in chunks)
    provenance = build_verification_provenance(
        input_text=prompt_input,
        prompt_text=prompt_text,
        context_items=tuple(chunk.content for chunk in chunks),
        prompt_char_count=None if prompt_text is None else len(prompt_text),
        prompt_trimmed=False if prompt_text is not None else None,
        prompt_original_char_count=None if prompt_text is None else len(prompt_text),
        prompt_final_char_count=None if prompt_text is None else len(prompt_text),
        prompt_trim_limit=None,
        prompt_trimmed_char_count=0 if prompt_text is not None else None,
        verification_hops=verification_hops,
        verification_calls=verification_calls,
    )
    return build_rag_verification_bundle(
        knowledge_policy=knowledge_policy,
        confidence=confidence,
        degraded_reason=degraded_reason,
        rag_actually_used=rag_actually_used,
        philo_validation_enabled=enrichment_completed,
        recursive_executed=recursive_executed,
        verification_calls=verification_calls,
        evidence_refs=evidence_refs,
        provenance=provenance,
    )

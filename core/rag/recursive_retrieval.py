"""Deterministic recursive RAG retrieval (C3 bounded follow-through).

Performs multi-hop retrieval with deterministic query refinement and
bounded verification passes. No LLM calls are made in the loop.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Dict, Iterable, List, cast

from core.data_sanitizer import sanitize_rag_markdown
from core.rag.contracts import OptimizationStats, OptimizationStopReason, RAGChunk, RAGContext
from core.rag.rag_constants import (
    MAX_HOP_VECTOR_CACHE_ENTRIES,
    MAX_RAG_HOPS,
    MAX_REFINEMENT_PASSES,
    MAX_SOURCES_IN_RESPONSE,
    MAX_VERIFICATION_QUERIES,
    MIN_CONFIDENCE_GAIN_PER_HOP,
    RAG_PIPELINE_TIMEOUT_SEC,
)

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\w\-]+", re.UNICODE)
_STOPWORDS = {
    "the",
    "and",
    "that",
    "this",
    "with",
    "from",
    "what",
    "when",
    "where",
    "which",
    "about",
    "into",
    "your",
    "have",
    "will",
    "для",
    "что",
    "это",
    "как",
    "или",
    "при",
    "если",
    "где",
    "когда",
    "так",
}


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _compute_confidence(chunks: List[RAGChunk]) -> float:
    if not chunks:
        return 0.0
    return float(round(sum(chunk.score for chunk in chunks) / len(chunks), 4))


def _rank_chunks(chunks: Iterable[RAGChunk], limit: int) -> List[RAGChunk]:
    ranked = sorted(chunks, key=lambda chunk: (-chunk.score, chunk.chunk_id))
    return ranked[:limit]


def _make_optimization_stats() -> OptimizationStats:
    """Build deterministic optimization diagnostics for a single request.

    RU: Диагностика нужна для локального benchmark evidence и не меняет API ответ.
    EN: Diagnostics are local benchmark evidence only and do not change the API response.
    """
    return {
        "enabled": True,
        "refinement_cache_hits": 0,
        "cache_hits": 0,
        "hop_vector_cache_hits": 0,
        "hop_vector_retrieve_calls": 0,
        "verification_calls": 0,
        "stop_reason": OptimizationStopReason.COMPLETED,
        "early_stop_no_query_change": False,
        "early_stop_no_new_chunks": False,
        "early_stop_low_confidence_gain": False,
        "early_stop_latency_budget": False,
    }


def _increment_stat(stats: OptimizationStats, key: str, amount: int = 1) -> None:
    mutable_stats = cast(dict[str, object], stats)
    current = mutable_stats.get(key, 0)
    if isinstance(current, bool):
        numeric_current = int(current)
    elif isinstance(current, int):
        numeric_current = current
    else:
        numeric_current = 0
    mutable_stats[key] = numeric_current + amount


def _set_stop_reason(
    stats: OptimizationStats | None,
    reason: OptimizationStopReason,
    *,
    early_stop_key: str | None = None,
) -> None:
    """Update stop reason only for the enabled optimization path.

    RU: При выключенном optimization path диагностика не создаётся вовсе.
    EN: Diagnostics are attached only when the optimization path is enabled.
    """
    if stats is None:
        return
    mutable_stats = cast(dict[str, object], stats)
    mutable_stats["stop_reason"] = reason
    if early_stop_key is not None:
        mutable_stats[early_stop_key] = True


def _refine_query(
    query: str,
    chunks: List[RAGChunk],
    *,
    token_cache: dict[tuple[str, str], list[str]] | None = None,
    stats: OptimizationStats | None = None,
) -> str:
    """Build deterministic refined query using frequent informative tokens."""
    query_tokens = set(_tokenize(query))
    frequencies: Dict[str, int] = {}

    for chunk in chunks:
        cache_key = (chunk.chunk_id, chunk.content)
        cached_tokens: list[str] | None = None
        if token_cache is not None:
            cached_tokens = token_cache.get(cache_key)
        if cached_tokens is None:
            sanitized_content = sanitize_rag_markdown(chunk.content)
            cached_tokens = [
                token
                for token in _tokenize(sanitized_content)
                if len(token) >= 4 and token not in _STOPWORDS
            ]
            if token_cache is not None:
                token_cache[cache_key] = cached_tokens
        elif stats is not None:
            _increment_stat(stats, "refinement_cache_hits")
            _increment_stat(stats, "cache_hits")
        for token in cached_tokens:
            if len(token) < 4:
                continue
            if token in query_tokens or token in _STOPWORDS:
                continue
            frequencies[token] = frequencies.get(token, 0) + 1

    if not frequencies:
        return query

    top_tokens = sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:2]
    additions = [token for token, _ in top_tokens]
    if not additions:
        return query
    return f"{query} {' '.join(additions)}".strip()


def _query_changed_materially(previous_query: str, refined_query: str) -> bool:
    """Return True only when refinement adds new semantic tokens."""
    if refined_query.strip() == previous_query.strip():
        return False
    return set(_tokenize(refined_query)) != set(_tokenize(previous_query))


def _apply_verification(
    *,
    chunks: List[RAGChunk],
    query: str,
    agent_id: str | None,
    philo_validation_enabled: bool,
) -> List[RAGChunk]:
    """Apply deterministic chunk verification pipeline."""
    from core.rag.validation import validate_rag_chunks

    validated: List[RAGChunk] = validate_rag_chunks(chunks, agent_id=agent_id).filtered_chunks

    if not philo_validation_enabled or not validated:
        return validated

    from core.rag.philosophy_pipeline import run_pipeline

    filtered: List[RAGChunk] = run_pipeline(validated, query=query).filtered_chunks
    return filtered


def _normalize_hop_vector_cache_query(query: str) -> str:
    """Deterministic normalization for hop-level vector memo keys."""
    return " ".join(query.split()).strip().lower()


def _hop_vector_cache_key(
    query: str,
    limit: int,
    agent_id: str | None,
    user_tier: str | None,
    subject_id: int | None,
) -> tuple[str, int, str, str, int | None]:
    """Cache key dimensions must match ``retrieve_context_structured`` call semantics."""
    return (
        _normalize_hop_vector_cache_query(query),
        limit,
        agent_id or "",
        user_tier or "",
        subject_id,
    )


def _retrieve_context_structured(
    query: str,
    *,
    max_chunks: int,
    agent_id: str | None,
    user_tier: str | None,
    subject_id: int | None,
) -> RAGContext:
    """Lazy import of vector RAG so import-time failures stay outside this module.

    RU: Ошибки импорта `vector_rag` не должны ломать загрузку `recursive_retrieval`.
    EN: Keeps recursive retrieval importable when the vector stack is optional or broken.
    """
    import core.rag.vector_rag as vector_rag_mod

    return cast(
        RAGContext,
        vector_rag_mod.retrieve_context_structured(
            query,
            max_chunks=max_chunks,
            agent_id=agent_id,
            user_tier=user_tier,
            subject_id=subject_id,
        ),
    )


def _copy_rag_context_snapshot(ctx: RAGContext) -> RAGContext:
    """Return an isolated copy so hop wrapping cannot mutate cached vector rows."""
    return RAGContext(
        query=ctx.query,
        refined_queries=list(ctx.refined_queries),
        chunks=[
            RAGChunk(
                chunk_id=c.chunk_id,
                file=c.file,
                content=c.content,
                score=c.score,
                hop=c.hop,
            )
            for c in ctx.chunks
        ],
        confidence=ctx.confidence,
        hops=ctx.hops,
        latency_ms=ctx.latency_ms,
        agent_id=ctx.agent_id,
        user_tier=ctx.user_tier,
        optimization_stats=None,
    )


class _FifoBoundedHopVectorCache:
    """FIFO-bounded request-scoped cache for vector ``RAGContext`` snapshots."""

    __slots__ = ("_data", "_max_entries", "_order")

    def __init__(self, max_entries: int) -> None:
        self._max_entries = max(1, max_entries)
        self._order: list[tuple[str, int, str, str, int | None]] = []
        self._data: dict[tuple[str, int, str, str, int | None], RAGContext] = {}

    def get_copy(self, key: tuple[str, int, str, str, int | None]) -> RAGContext | None:
        if key not in self._data:
            return None
        return _copy_rag_context_snapshot(self._data[key])

    def put(self, key: tuple[str, int, str, str, int | None], ctx: RAGContext) -> RAGContext:
        """Store an isolated snapshot and return it (avoid second snapshot from raw ctx)."""
        snap = _copy_rag_context_snapshot(ctx)
        if key in self._data:
            self._data[key] = snap
            return snap
        if len(self._order) >= self._max_entries:
            oldest = self._order.pop(0)
            self._data.pop(oldest, None)
        self._order.append(key)
        self._data[key] = snap
        return snap


def _retrieve_vector_for_recursive_hop(
    *,
    current_query: str,
    limit: int,
    agent_id: str | None,
    user_tier: str | None,
    subject_id: int | None,
    hop_vector_cache: _FifoBoundedHopVectorCache | None,
    optimization_stats: OptimizationStats | None,
) -> RAGContext:
    """Vector retrieve with optional request-scoped hop memo (optimization path only)."""
    if hop_vector_cache is None:
        return _retrieve_context_structured(
            current_query,
            max_chunks=limit,
            agent_id=agent_id,
            user_tier=user_tier,
            subject_id=subject_id,
        )
    key = _hop_vector_cache_key(current_query, limit, agent_id, user_tier, subject_id)
    cached = hop_vector_cache.get_copy(key)
    if cached is not None:
        if optimization_stats is not None:
            _increment_stat(optimization_stats, "hop_vector_cache_hits")
        return cached
    ctx = _retrieve_context_structured(
        current_query,
        max_chunks=limit,
        agent_id=agent_id,
        user_tier=user_tier,
        subject_id=subject_id,
    )
    if optimization_stats is not None:
        _increment_stat(optimization_stats, "hop_vector_retrieve_calls")
    stored_snap = hop_vector_cache.put(key, ctx)
    return _copy_rag_context_snapshot(stored_snap)


def retrieve_recursive_context_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
    *,
    philo_validation_enabled: bool = False,
    optimization_enabled: bool = False,
) -> RAGContext:
    """Retrieve context with bounded recursive refinement.

    Args:
        query: User query.
        max_chunks: Chunk limit requested by caller.
        agent_id: Optional agent corpus key.
        user_tier: Optional tier marker.
        philo_validation_enabled: Apply philosophy pipeline during verification.
    """
    start_ts = time.perf_counter()
    current_query = query
    refined_queries: List[str] = [query]
    merged_chunks: Dict[str, RAGChunk] = {}
    verification_queries = 0
    previous_confidence = 0.0
    hops_done = 0
    limit = max(1, min(max_chunks, MAX_SOURCES_IN_RESPONSE))
    optimization_stats = _make_optimization_stats() if optimization_enabled else None
    refinement_token_cache: dict[tuple[str, str], list[str]] | None = (
        {} if optimization_enabled else None
    )
    hop_vector_cache: _FifoBoundedHopVectorCache | None = (
        _FifoBoundedHopVectorCache(MAX_HOP_VECTOR_CACHE_ENTRIES) if optimization_enabled else None
    )

    try:
        for hop in range(1, MAX_RAG_HOPS + 1):
            elapsed_sec = time.perf_counter() - start_ts
            if elapsed_sec >= RAG_PIPELINE_TIMEOUT_SEC:
                _set_stop_reason(
                    optimization_stats,
                    OptimizationStopReason.LATENCY_BUDGET,
                    early_stop_key="early_stop_latency_budget",
                )
                logger.debug(
                    "Recursive retrieval timeout; breaking at hop=%d elapsed_ms=%d",
                    hop,
                    int(elapsed_sec * 1000),
                )
                break

            hops_done = hop
            hop_ctx = _retrieve_vector_for_recursive_hop(
                current_query=current_query,
                limit=limit,
                agent_id=agent_id,
                user_tier=user_tier,
                subject_id=subject_id,
                hop_vector_cache=hop_vector_cache,
                optimization_stats=optimization_stats,
            )
            if not hop_ctx.chunks:
                if hop > 1:
                    _set_stop_reason(optimization_stats, OptimizationStopReason.EMPTY_HOP)
                break

            hop_chunks = [
                RAGChunk(
                    chunk_id=chunk.chunk_id,
                    file=chunk.file,
                    content=chunk.content,
                    score=chunk.score,
                    hop=hop,
                )
                for chunk in hop_ctx.chunks
            ]

            if verification_queries < MAX_VERIFICATION_QUERIES:
                verification_queries += 1
                if optimization_stats is not None:
                    _increment_stat(optimization_stats, "verification_calls")
                hop_chunks = _apply_verification(
                    chunks=hop_chunks,
                    query=current_query,
                    agent_id=agent_id,
                    philo_validation_enabled=philo_validation_enabled,
                )

            if not hop_chunks:
                _set_stop_reason(optimization_stats, OptimizationStopReason.NO_USABLE_CHUNKS)
                break

            candidate_chunks = dict(merged_chunks)
            introduced_new_chunks = False
            improved_existing_chunks = False
            repeated_evidence_only = False
            for chunk in hop_chunks:
                existing = candidate_chunks.get(chunk.chunk_id)
                if existing is None:
                    introduced_new_chunks = True
                    candidate_chunks[chunk.chunk_id] = chunk
                    continue
                if chunk.score > existing.score:
                    improved_existing_chunks = True
                    candidate_chunks[chunk.chunk_id] = chunk

            repeated_evidence_only = (
                optimization_enabled
                and hop > 1
                and not introduced_new_chunks
                and not improved_existing_chunks
            )

            ranked_chunks = _rank_chunks(candidate_chunks.values(), limit)
            confidence = _compute_confidence(ranked_chunks)
            confidence_gain = confidence - previous_confidence

            merged_chunks = candidate_chunks
            previous_confidence = confidence

            if (
                optimization_enabled
                and (time.perf_counter() - start_ts) >= RAG_PIPELINE_TIMEOUT_SEC
            ):
                _set_stop_reason(
                    optimization_stats,
                    OptimizationStopReason.LATENCY_BUDGET,
                    early_stop_key="early_stop_latency_budget",
                )
                break

            if len(refined_queries) - 1 >= MAX_REFINEMENT_PASSES:
                _set_stop_reason(optimization_stats, OptimizationStopReason.REFINEMENT_BUDGET)
                break

            refined_query = _refine_query(
                current_query,
                hop_chunks,
                token_cache=refinement_token_cache,
                stats=optimization_stats,
            )
            if optimization_enabled and not _query_changed_materially(current_query, refined_query):
                if repeated_evidence_only:
                    _set_stop_reason(
                        optimization_stats,
                        OptimizationStopReason.NO_NEW_USABLE_CHUNKS,
                        early_stop_key="early_stop_no_new_chunks",
                    )
                else:
                    _set_stop_reason(
                        optimization_stats,
                        OptimizationStopReason.NO_MATERIAL_QUERY_CHANGE,
                        early_stop_key="early_stop_no_query_change",
                    )
                break
            if hop > 1 and confidence_gain < MIN_CONFIDENCE_GAIN_PER_HOP:
                if repeated_evidence_only:
                    _set_stop_reason(
                        optimization_stats,
                        OptimizationStopReason.NO_NEW_USABLE_CHUNKS,
                        early_stop_key="early_stop_no_new_chunks",
                    )
                else:
                    _set_stop_reason(
                        optimization_stats,
                        OptimizationStopReason.LOW_CONFIDENCE_GAIN,
                        early_stop_key="early_stop_low_confidence_gain",
                    )
                break
            if not optimization_enabled and refined_query == current_query:
                break
            refined_queries.append(refined_query)
            current_query = refined_query
    except Exception:
        if merged_chunks:
            logger.warning(
                "Recursive retrieval failed after partial success; returning best partial context",
                exc_info=True,
            )
            final_chunks = _rank_chunks(merged_chunks.values(), limit)
            return RAGContext(
                query=query,
                refined_queries=refined_queries,
                chunks=final_chunks,
                confidence=_compute_confidence(final_chunks),
                hops=max(1, hops_done),
                latency_ms=int((time.perf_counter() - start_ts) * 1000),
                agent_id=agent_id,
                user_tier=user_tier,
                optimization_stats=optimization_stats,
            )
        logger.warning(
            "Recursive retrieval failed; returning safe empty context",
            exc_info=True,
        )
        return RAGContext(
            query=query,
            refined_queries=[query],
            chunks=[],
            confidence=0.0,
            hops=max(1, hops_done),
            latency_ms=int((time.perf_counter() - start_ts) * 1000),
            agent_id=agent_id,
            user_tier=user_tier,
            optimization_stats=optimization_stats,
        )

    final_chunks = _rank_chunks(merged_chunks.values(), limit)
    return RAGContext(
        query=query,
        refined_queries=refined_queries,
        chunks=final_chunks,
        confidence=_compute_confidence(final_chunks),
        hops=max(1, hops_done),
        latency_ms=int((time.perf_counter() - start_ts) * 1000),
        agent_id=agent_id,
        user_tier=user_tier,
        optimization_stats=optimization_stats,
    )

"""Deterministic recursive RAG retrieval (W1 core-only).

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
        "retrieval_cache_hits": 0,
        "refinement_cache_hits": 0,
        "cache_hits": 0,
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
    retrieval_cache: (
        dict[tuple[str, int, str | None, str | None, int | None], RAGContext] | None
    ) = ({} if optimization_enabled else None)
    refinement_token_cache: dict[tuple[str, str], list[str]] | None = (
        {} if optimization_enabled else None
    )

    try:
        from core.rag.vector_rag import retrieve_context_structured

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
            retrieval_cache_key = (current_query, limit, agent_id, user_tier, subject_id)
            if retrieval_cache is not None and retrieval_cache_key in retrieval_cache:
                hop_ctx = retrieval_cache[retrieval_cache_key]
                if optimization_stats is not None:
                    _increment_stat(optimization_stats, "retrieval_cache_hits")
                    _increment_stat(optimization_stats, "cache_hits")
            else:
                hop_ctx = retrieve_context_structured(
                    current_query,
                    max_chunks=limit,
                    agent_id=agent_id,
                    user_tier=user_tier,
                    subject_id=subject_id,
                )
                if retrieval_cache is not None:
                    retrieval_cache[retrieval_cache_key] = hop_ctx
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
            for chunk in hop_chunks:
                existing = candidate_chunks.get(chunk.chunk_id)
                if existing is None:
                    introduced_new_chunks = True
                    candidate_chunks[chunk.chunk_id] = chunk
                    continue
                if chunk.score > existing.score:
                    improved_existing_chunks = True
                    candidate_chunks[chunk.chunk_id] = chunk

            if (
                optimization_enabled
                and hop > 1
                and not introduced_new_chunks
                and not improved_existing_chunks
            ):
                _set_stop_reason(
                    optimization_stats,
                    OptimizationStopReason.NO_NEW_USABLE_CHUNKS,
                    early_stop_key="early_stop_no_new_chunks",
                )
                break

            ranked_chunks = _rank_chunks(candidate_chunks.values(), limit)
            confidence = _compute_confidence(ranked_chunks)

            if hop > 1 and (confidence - previous_confidence) < MIN_CONFIDENCE_GAIN_PER_HOP:
                _set_stop_reason(
                    optimization_stats,
                    OptimizationStopReason.LOW_CONFIDENCE_GAIN,
                    early_stop_key="early_stop_low_confidence_gain",
                )
                break

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
                _set_stop_reason(
                    optimization_stats,
                    OptimizationStopReason.NO_MATERIAL_QUERY_CHANGE,
                    early_stop_key="early_stop_no_query_change",
                )
                break
            if not optimization_enabled and refined_query == current_query:
                break
            refined_queries.append(refined_query)
            current_query = refined_query
    except Exception:
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

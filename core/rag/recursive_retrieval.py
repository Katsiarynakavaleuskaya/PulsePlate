"""Deterministic recursive RAG retrieval (W1 core-only).

Performs multi-hop retrieval with deterministic query refinement and
bounded verification passes. No LLM calls are made in the loop.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Dict, Iterable, List

from core.rag.contracts import RAGChunk, RAGContext
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
    return round(sum(chunk.score for chunk in chunks) / len(chunks), 4)


def _rank_chunks(chunks: Iterable[RAGChunk], limit: int) -> List[RAGChunk]:
    ranked = sorted(chunks, key=lambda chunk: (-chunk.score, chunk.chunk_id))
    return ranked[:limit]


def _refine_query(query: str, chunks: List[RAGChunk]) -> str:
    """Build deterministic refined query using frequent informative tokens."""
    query_tokens = set(_tokenize(query))
    frequencies: Dict[str, int] = {}

    for chunk in chunks:
        for token in _tokenize(chunk.content):
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


def _apply_verification(
    *,
    chunks: List[RAGChunk],
    query: str,
    agent_id: str | None,
    philo_validation_enabled: bool,
) -> List[RAGChunk]:
    """Apply deterministic chunk verification pipeline."""
    from core.rag.validation import validate_rag_chunks

    validated = validate_rag_chunks(chunks, agent_id=agent_id).filtered_chunks

    if not philo_validation_enabled or not validated:
        return validated

    from core.rag.philosophy_pipeline import run_pipeline

    return run_pipeline(validated, query=query).filtered_chunks


def retrieve_recursive_context_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    *,
    philo_validation_enabled: bool = False,
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

    try:
        from core.rag.vector_rag import retrieve_context_structured

        for hop in range(1, MAX_RAG_HOPS + 1):
            if (time.perf_counter() - start_ts) >= RAG_PIPELINE_TIMEOUT_SEC:
                break

            hops_done = hop
            hop_ctx = retrieve_context_structured(
                current_query,
                max_chunks=limit,
                agent_id=agent_id,
                user_tier=user_tier,
            )
            if not hop_ctx.chunks:
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
                hop_chunks = _apply_verification(
                    chunks=hop_chunks,
                    query=current_query,
                    agent_id=agent_id,
                    philo_validation_enabled=philo_validation_enabled,
                )

            if not hop_chunks:
                break

            candidate_chunks = dict(merged_chunks)
            for chunk in hop_chunks:
                existing = candidate_chunks.get(chunk.chunk_id)
                if existing is None or chunk.score > existing.score:
                    candidate_chunks[chunk.chunk_id] = chunk

            ranked_chunks = _rank_chunks(candidate_chunks.values(), limit)
            confidence = _compute_confidence(ranked_chunks)

            if hop > 1 and (confidence - previous_confidence) < MIN_CONFIDENCE_GAIN_PER_HOP:
                break

            merged_chunks = candidate_chunks
            previous_confidence = confidence

            if len(refined_queries) - 1 >= MAX_REFINEMENT_PASSES:
                break

            refined_query = _refine_query(current_query, hop_chunks)
            if refined_query == current_query:
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
    )

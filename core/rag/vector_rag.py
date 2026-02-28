"""Vector-based RAG retrieval using pgvector cosine similarity.

Feature-gated via ``FEATURE_RAG_VECTOR``.  When enabled, queries
user_knowledge embeddings via cosine similarity; on any failure (or when
disabled) falls back transparently to Jaccard retrieval in simple_rag.

Dialect-aware:
- PostgreSQL: native pgvector ``<=>`` cosine distance operator.
- SQLite (tests): application-level cosine similarity on JSON-encoded vectors.

See: docs/contracts/RAG_CONTRACT.md (§3, §4 SLA budget)
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from typing import TYPE_CHECKING, Any

from app.utils.feature_flags import is_rag_vector_enabled
from core.rag.contracts import RAGChunk, RAGContext
from core.rag.rag_constants import (
    EMBEDDING_DIMENSIONS,
    MAX_CHUNK_SIZE_CHARS,
    MAX_SOURCES_IN_RESPONSE,
    MIN_VECTOR_SCORE,
)

if TYPE_CHECKING:
    from providers.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton embedding provider (lazy, thread-safe)
# ---------------------------------------------------------------------------

_embedding_provider: EmbeddingProvider | None = None
_embedding_provider_lock = threading.Lock()


def _get_embedding_provider() -> EmbeddingProvider:
    """Return the singleton embedding provider, created lazily (thread-safe)."""
    global _embedding_provider
    if _embedding_provider is None:
        with _embedding_provider_lock:
            if _embedding_provider is None:
                from providers.embeddings import SentenceTransformerEmbeddings

                _embedding_provider = SentenceTransformerEmbeddings()
    return _embedding_provider


def reset_embedding_provider() -> None:
    """Reset the cached embedding provider (for tests)."""
    global _embedding_provider
    _embedding_provider = None


# ---------------------------------------------------------------------------
# Application-level cosine similarity (SQLite fallback)
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns 0.0 for zero-norm vectors.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Vector retrieval (dialect-aware)
# ---------------------------------------------------------------------------


def _retrieve_vector_postgres(
    query_embedding: list[float],
    limit: int,
    session: Any,
) -> list[tuple[Any, float]]:
    """Retrieve similar rows via pgvector cosine distance operator."""
    from sqlalchemy import text

    # Format embedding explicitly into pgvector's canonical text form
    # instead of relying on str(list) which may have inconsistent formatting.
    qvec_text = "[" + ",".join(str(x) for x in query_embedding) + "]"

    stmt = text(
        "SELECT id, content, source, "
        "1 - (embedding <=> :qvec::vector) AS similarity "
        "FROM user_knowledge "
        "WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> :qvec::vector "
        "LIMIT :lim"
    )
    rows = session.execute(stmt, {"qvec": qvec_text, "lim": limit}).fetchall()
    return [(row, row.similarity) for row in rows]


def _retrieve_vector_sqlite(
    query_embedding: list[float],
    limit: int,
    session: Any,
) -> list[tuple[Any, float]]:
    """Retrieve similar rows via application-level cosine (SQLite tests)."""
    from sqlalchemy import text

    rows = session.execute(
        text(
            "SELECT id, content, source, embedding FROM user_knowledge WHERE embedding IS NOT NULL"
        )
    ).fetchall()

    scored: list[tuple[Any, float]] = []

    if len(query_embedding) != EMBEDDING_DIMENSIONS:
        logger.error(
            "Query embedding length %d != expected %d",
            len(query_embedding),
            EMBEDDING_DIMENSIONS,
        )
        return []

    for row in rows:
        try:
            stored = json.loads(row.embedding)
            if len(stored) != EMBEDDING_DIMENSIONS:
                continue
            sim = _cosine_similarity(query_embedding, stored)
            scored.append((row, sim))
        except (json.JSONDecodeError, TypeError):
            continue

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def _retrieve_vector_from_db(
    query: str,
    max_chunks: int,
    agent_id: str | None,
    user_tier: str | None,
) -> RAGContext:
    """Core vector retrieval: encode query, search DB, return RAGContext."""
    start = time.perf_counter()

    provider = _get_embedding_provider()
    query_vectors = provider.encode([query])
    if not query_vectors:
        return _empty_context(query, agent_id, user_tier, start)
    query_embedding = query_vectors[0]

    from core.db import session_scope

    with session_scope() as session:
        dialect = session.bind.dialect.name if session.bind else "sqlite"
        limit = max(1, min(max_chunks, MAX_SOURCES_IN_RESPONSE))

        if dialect == "postgresql":
            results = _retrieve_vector_postgres(query_embedding, limit, session)
        else:
            results = _retrieve_vector_sqlite(query_embedding, limit, session)

    # Filter by minimum score and build RAGChunks
    chunks: list[RAGChunk] = []
    for i, (row, similarity) in enumerate(results, 1):
        if similarity < MIN_VECTOR_SCORE:
            continue
        chunks.append(
            RAGChunk(
                chunk_id=f"uk:{row.id}:{i}",
                file=row.source or "user_knowledge",
                content=str(row.content)[:MAX_CHUNK_SIZE_CHARS],
                score=round(similarity, 4),
                hop=1,
            )
        )

    confidence = sum(c.score for c in chunks) / len(chunks) if chunks else 0.0
    latency_ms = int((time.perf_counter() - start) * 1000)

    return RAGContext(
        query=query,
        refined_queries=[query],
        chunks=chunks,
        confidence=confidence,
        hops=1,
        latency_ms=latency_ms,
        agent_id=agent_id,
        user_tier=user_tier,
    )


def _empty_context(
    query: str,
    agent_id: str | None,
    user_tier: str | None,
    start: float,
) -> RAGContext:
    """Return an empty RAGContext (no results)."""
    return RAGContext(
        query=query,
        refined_queries=[query],
        chunks=[],
        confidence=0.0,
        hops=1,
        latency_ms=int((time.perf_counter() - start) * 1000),
        agent_id=agent_id,
        user_tier=user_tier,
    )


# ---------------------------------------------------------------------------
# Public API — same signature as simple_rag.retrieve_context_structured
# ---------------------------------------------------------------------------


def retrieve_context_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
) -> RAGContext:
    """Vector retrieval with automatic fallback to Jaccard.

    When ``FEATURE_RAG_VECTOR`` is enabled, attempts cosine similarity
    search on user_knowledge embeddings.  On any failure (missing
    embeddings, DB error, provider error) falls back to Jaccard-based
    ``simple_rag.retrieve_context_structured``.

    Returns: RAGContext per RAG_CONTRACT.md §3.
    """
    if is_rag_vector_enabled():
        try:
            ctx = _retrieve_vector_from_db(query, max_chunks, agent_id, user_tier)
            # If vector found results, return them
            if ctx.chunks:
                return ctx
            # No vector results — fall through to Jaccard
            logger.debug("Vector retrieval returned no chunks; falling back to Jaccard")
        except Exception:
            logger.warning(
                "Vector retrieval failed; falling back to Jaccard",
                exc_info=True,
            )

    # Fallback to Jaccard
    from core.rag.simple_rag import retrieve_context_structured as _jaccard_retrieve

    return _jaccard_retrieve(query, max_chunks=max_chunks, agent_id=agent_id, user_tier=user_tier)

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
from core.data_sanitizer import sanitize_rag_markdown
from core.db_rls import apply_user_rls_context
from core.rag.contracts import AGENT_CORPUS_MAP, RAGChunk, RAGContext
from core.rag.rag_constants import (
    EMBEDDING_DIMENSIONS,
    MAX_CHUNK_SIZE_CHARS,
    MAX_SOURCES_IN_RESPONSE,
    MIN_VECTOR_SCORE,
)

if TYPE_CHECKING:
    from providers.embeddings import EmbeddingProvider
    from sqlalchemy.sql.selectable import TableClause

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


def _user_knowledge_table() -> TableClause:
    """Return a lightweight SQLAlchemy table descriptor for ``user_knowledge``."""

    from sqlalchemy import column, table

    return table(
        "user_knowledge",
        column("id"),
        column("content"),
        column("source"),
        column("embedding"),
        column("user_id"),
    )


def _escape_like_prefix(prefix: str) -> str:
    """Escape SQL LIKE wildcards in a corpus prefix before appending ``%``."""

    escaped_prefix = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped_prefix}%"


def _has_expected_embedding_dimensions(query_embedding: list[float]) -> bool:
    """Return whether a query embedding matches the configured vector size."""

    if len(query_embedding) != EMBEDDING_DIMENSIONS:
        logger.error(
            "Query embedding length %d != expected %d",
            len(query_embedding),
            EMBEDDING_DIMENSIONS,
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Vector retrieval (dialect-aware)
# ---------------------------------------------------------------------------


def _retrieve_vector_postgres(
    query_embedding: list[float],
    limit: int,
    session: Any,
    subject_id: int,
    corpus_prefixes: list[str] | None = None,
) -> list[tuple[Any, float]]:
    """Retrieve similar rows via pgvector cosine distance operator.

    If corpus_prefixes is provided, filters results to rows where source
    starts with one of the given prefixes (agent-specific corpus filtering).
    """
    from pgvector.sqlalchemy import VECTOR
    from sqlalchemy import BigInteger, Integer, String, bindparam, cast, or_, select

    user_knowledge = _user_knowledge_table()

    vector_type = VECTOR(EMBEDDING_DIMENSIONS)
    qvec_param = bindparam("qvec", type_=vector_type)
    qvec_vector = cast(qvec_param, vector_type)
    limit_param = bindparam("lim", type_=Integer())
    similarity = (1 - user_knowledge.c.embedding.op("<=>")(qvec_vector)).label("similarity")

    stmt = (
        select(
            user_knowledge.c.id,
            user_knowledge.c.content,
            user_knowledge.c.source,
            similarity,
        )
        .where(
            user_knowledge.c.embedding.is_not(None),
            user_knowledge.c.user_id == bindparam("subject_id", type_=BigInteger()),
        )
        .order_by(similarity.desc())
        .limit(limit_param)
    )

    params: dict[str, Any] = {
        "qvec": query_embedding,
        "lim": limit,
        "subject_id": subject_id,
    }

    if corpus_prefixes:
        prefix_conditions = []
        for i, prefix in enumerate(corpus_prefixes):
            param_name = f"prefix_{i}"
            prefix_conditions.append(
                user_knowledge.c.source.like(
                    bindparam(param_name, type_=String()),
                    escape="\\",
                )
            )
            params[param_name] = _escape_like_prefix(prefix)
        if prefix_conditions:
            stmt = stmt.where(or_(*prefix_conditions))

    rows = session.execute(stmt, params).fetchall()
    return [(row, row.similarity) for row in rows]


def _retrieve_vector_sqlite(
    query_embedding: list[float],
    limit: int,
    session: Any,
    subject_id: int,
    corpus_prefixes: list[str] | None = None,
) -> list[tuple[Any, float]]:
    """Retrieve similar rows via application-level cosine (SQLite tests).

    If corpus_prefixes is provided, filters results to rows where source
    starts with one of the given prefixes (agent-specific corpus filtering).
    """
    from sqlalchemy import BigInteger, String, bindparam, or_, select

    user_knowledge = _user_knowledge_table()

    stmt = select(
        user_knowledge.c.id,
        user_knowledge.c.content,
        user_knowledge.c.source,
        user_knowledge.c.embedding,
    ).where(
        user_knowledge.c.embedding.is_not(None),
        user_knowledge.c.user_id == bindparam("subject_id", type_=BigInteger()),
    )

    params: dict[str, Any] = {"subject_id": subject_id}

    if corpus_prefixes:
        prefix_conditions = []
        for i, prefix in enumerate(corpus_prefixes):
            param_name = f"prefix_{i}"
            prefix_conditions.append(
                user_knowledge.c.source.like(
                    bindparam(param_name, type_=String()),
                    escape="\\",
                )
            )
            params[param_name] = _escape_like_prefix(prefix)
        if prefix_conditions:
            stmt = stmt.where(or_(*prefix_conditions))

    rows = session.execute(stmt, params).fetchall()

    scored: list[tuple[Any, float]] = []

    if not _has_expected_embedding_dimensions(query_embedding):
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
    subject_id: int | None,
) -> RAGContext:
    """Core vector retrieval: encode query, search DB, return RAGContext.

    If agent_id is in AGENT_CORPUS_MAP, filters retrieval to that agent's
    corpus paths. Otherwise, queries all indexed content.
    """
    start = time.perf_counter()

    if subject_id is None:
        logger.debug("Vector retrieval skipped because subject_id is missing")
        return _empty_context(query, agent_id, user_tier, start)

    # Get corpus prefixes for agent-specific filtering
    corpus_prefixes = AGENT_CORPUS_MAP.get(agent_id) if agent_id else None

    provider = _get_embedding_provider()
    query_vectors = provider.encode([query])
    if not query_vectors:
        return _empty_context(query, agent_id, user_tier, start)
    query_embedding = query_vectors[0]
    if not _has_expected_embedding_dimensions(query_embedding):
        return _empty_context(query, agent_id, user_tier, start)

    from core.db import session_scope

    with session_scope() as session:
        apply_user_rls_context(session, user_id=subject_id)
        dialect = session.bind.dialect.name if session.bind else "sqlite"
        limit = max(1, min(max_chunks, MAX_SOURCES_IN_RESPONSE))

        if dialect == "postgresql":
            results = _retrieve_vector_postgres(
                query_embedding,
                limit,
                session,
                subject_id=subject_id,
                corpus_prefixes=corpus_prefixes,
            )
        else:
            results = _retrieve_vector_sqlite(
                query_embedding,
                limit,
                session,
                subject_id=subject_id,
                corpus_prefixes=corpus_prefixes,
            )

    # Filter by minimum score and build RAGChunks
    chunks: list[RAGChunk] = []
    for i, (row, similarity) in enumerate(results, 1):
        if similarity < MIN_VECTOR_SCORE:
            continue
        sanitized_content = sanitize_rag_markdown(str(row.content))[:MAX_CHUNK_SIZE_CHARS].strip()
        if not sanitized_content:
            continue
        chunks.append(
            RAGChunk(
                chunk_id=f"uk:{row.id}:{i}",
                file=row.source or "user_knowledge",
                content=sanitized_content,
                score=round(similarity, 4),
                hop=1,
            )
        )

    # Log warning if agent-specific corpus expected but no results found
    if corpus_prefixes and not chunks:
        logger.warning(
            "No vector results for agent_id=%s with corpus_prefixes=%s",
            agent_id,
            corpus_prefixes,
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
    subject_id: int | None = None,
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
            ctx = _retrieve_vector_from_db(
                query,
                max_chunks,
                agent_id,
                user_tier,
                subject_id,
            )
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

    fallback_ctx: RAGContext = _jaccard_retrieve(
        query,
        max_chunks=max_chunks,
        agent_id=agent_id,
        user_tier=user_tier,
    )
    return fallback_ctx

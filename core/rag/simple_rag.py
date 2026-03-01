"""
Simple RAG (Retrieval-Augmented Generation) helper without external deps.

RU: Простейший RAG: индексирует локальные .md файлы и даёт топ-k релевантных
фрагментов по ключевым словам. Никаких внешних зависимостей и сети.

Назначение: использовать как добавочный контекст для /insight при флаге
FEATURE_RAG=on.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Iterable, List, Tuple

from core.rag.contracts import AGENT_CORPUS_MAP, RAGChunk, RAGContext
from core.rag.rag_constants import (
    MAX_CHUNK_SIZE_CHARS,
    MAX_SOURCES_IN_RESPONSE,
    MIN_CHUNK_SCORE,
)

ROOT = Path(os.getenv("PROJECT_ROOT", ".")).resolve()
DOC_GLOBS = ["*.md"]
MAX_FILE_SIZE = 256 * 1024  # bytes, skip very large files
_INDEX: List[Tuple[str, str]] | None = None  # list of (source, chunk)
logger = logging.getLogger(__name__)


_WORD_RE = re.compile(r"[\w\-]+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def _chunk(text: str, max_chars: int = 800) -> List[str]:
    # split by paragraphs, then merge small ones up to max_chars
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    out: List[str] = []
    buf = ""
    for p in paras:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= max_chars:
            buf = f"{buf}\n\n{p}"
        else:
            out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out


def _iter_docs() -> Iterable[Path]:
    doc_dir = ROOT
    for pattern in DOC_GLOBS:
        for p in doc_dir.glob(pattern):
            if p.is_file():
                yield p
    # Prefer a docs/ folder if present
    docs = ROOT / "docs"
    if docs.exists():
        for pattern in DOC_GLOBS:
            for p in docs.rglob(pattern):
                if p.is_file():
                    yield p


def _build_index() -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    for path in _iter_docs():
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as read_err:
            # Handle any read errors (OSError, UnicodeDecodeError, RuntimeError, etc.)
            logger.debug("Skipping %s during index build: %s", path, read_err)
            continue
        for ch in _chunk(text):
            if ch:
                items.append((str(path), ch))
    return items


def _get_index() -> List[Tuple[str, str]]:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def invalidate_index() -> None:
    global _INDEX
    _INDEX = None


def _score(query: str, text: str) -> float:
    # Simple Jaccard on word sets, with small bonus for exact substring hits
    q = set(_tokenize(query))
    t = set(_tokenize(text))
    if not q or not t:
        return 0.0
    inter = len(q & t)
    union = len(q | t)
    base = inter / union if union else 0.0
    if query.lower() in text.lower():
        base += 0.1
    return base


def retrieve_context(query: str, max_chunks: int = 3) -> str:
    """Return top-k relevant chunks concatenated with brief headers."""
    items = _get_index()
    if not items:
        return ""
    scored = sorted(
        ((src, ch, _score(query, ch)) for src, ch in items), key=lambda x: x[2], reverse=True
    )
    top = [x for x in scored[: max(1, max_chunks)] if x[2] > 0]
    if not top:
        return ""
    parts = []
    for src, ch, sc in top:
        parts.append(f"# Source: {Path(src).name} (score={sc:.2f})\n{ch}")
    return "\n\n".join(parts)


def retrieve_context_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
) -> RAGContext:
    """
    Return RAG retrieval result as RAGContext per RAG_CONTRACT.md §3.

    Backward-compatible with retrieve_context: same index and scoring;
    use this when response needs sources, confidence, hops, latency_ms.

    If agent_id is in AGENT_CORPUS_MAP, filters retrieval to that agent's
    corpus paths. Otherwise, queries all indexed content.
    """
    start = time.perf_counter()
    items = _get_index()
    refined: list[str] = [query]

    # Get corpus prefixes for agent-specific filtering
    corpus_prefixes = AGENT_CORPUS_MAP.get(agent_id) if agent_id else None

    # Filter items by corpus prefixes if specified
    if corpus_prefixes:
        filtered_items = [
            (src, ch)
            for src, ch in items
            if any(src.startswith(prefix) for prefix in corpus_prefixes)
        ]
        if not filtered_items and items:
            logger.warning(
                "No items match corpus_prefixes=%s for agent_id=%s",
                corpus_prefixes,
                agent_id,
            )
        items = filtered_items

    if not items:
        return RAGContext(
            query=query,
            refined_queries=refined,
            chunks=[],
            confidence=0.0,
            hops=1,
            latency_ms=int((time.perf_counter() - start) * 1000),
            agent_id=agent_id,
            user_tier=user_tier,
        )
    scored = sorted(
        ((src, ch, _score(query, ch)) for src, ch in items), key=lambda x: x[2], reverse=True
    )
    limit = max(1, min(max_chunks, MAX_SOURCES_IN_RESPONSE))
    top = [x for x in scored[:limit] if x[2] >= MIN_CHUNK_SCORE]
    chunks = [
        RAGChunk(
            chunk_id=f"{Path(src).relative_to(ROOT) if Path(src).is_relative_to(ROOT) else Path(src).name}:{i}",
            file=(
                str(Path(src).relative_to(ROOT))
                if Path(src).is_relative_to(ROOT)
                else Path(src).name
            ),
            content=ch[:MAX_CHUNK_SIZE_CHARS],
            score=sc,
            hop=1,
        )
        for i, (src, ch, sc) in enumerate(top, 1)
    ]
    confidence = sum(c.score for c in chunks) / len(chunks) if chunks else 0.0
    latency_ms = int((time.perf_counter() - start) * 1000)
    return RAGContext(
        query=query,
        refined_queries=refined,
        chunks=chunks,
        confidence=confidence,
        hops=1,
        latency_ms=latency_ms,
        agent_id=agent_id,
        user_tier=user_tier,
    )


# ---------------------------------------------------------------------------
# Thin facades – satisfy test imports for rag feature key
# ---------------------------------------------------------------------------


class RAGEngine:
    """Thin facade for RAG operations."""

    def __init__(self) -> None:
        pass

    def query(self, query: str, max_chunks: int = 3) -> str:
        return retrieve_context(query, max_chunks=max_chunks)


class SimpleRAG:
    """Thin facade with .query() method."""

    def __init__(self) -> None:
        pass

    def query(self, query: str, max_chunks: int = 3) -> str:
        return retrieve_context(query or "", max_chunks=max_chunks)


def _score_chunk(query_tokens: list[str], chunk_tokens: list[str]) -> float:
    """Jaccard similarity between two token lists."""
    q = set(query_tokens)
    c = set(chunk_tokens)
    if not q or not c:
        return 0.0
    return len(q & c) / len(q | c)


def create_embeddings(texts: list[str]) -> list[list[str]]:
    """Create token-based embeddings (thin: tokenizes each text)."""
    return [_tokenize(text) for text in texts]


def similarity_search(query: str, docs: list[str], top_k: int = 3) -> list[str]:
    """Search docs by similarity to query."""
    if not docs:
        return []
    results: list[tuple[float, str]] = []
    q_tokens = _tokenize(query)
    for doc in docs:
        for ch in _chunk(doc):
            c_tokens = _tokenize(ch)
            sc = _score_chunk(q_tokens, c_tokens)
            results.append((sc, ch))
    results.sort(key=lambda x: x[0], reverse=True)
    return [ch for _, ch in results[:top_k]]


def update_knowledge_base(text: str) -> None:
    """Update knowledge base (invalidates index)."""
    invalidate_index()


def add_knowledge(text: str) -> None:
    """Add knowledge to index (invalidates for rebuild)."""
    invalidate_index()


def query_knowledge_base(query: str | None, max_chunks: int = 3) -> str:
    """Query knowledge base. Handles None query."""
    return retrieve_context(query or "", max_chunks=max_chunks)


def search_knowledge(query: str, max_chunks: int = 3) -> list[str]:
    """Search knowledge and return list of chunk strings."""
    result = retrieve_context(query, max_chunks=max_chunks)
    if not result:
        return []
    return [chunk.strip() for chunk in result.split("\n\n") if chunk.strip()]

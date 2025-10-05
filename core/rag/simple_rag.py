"""
Simple RAG (Retrieval-Augmented Generation) helper without external deps.

RU: Простейший RAG: индексирует локальные .md файлы и даёт топ-k релевантных
фрагментов по ключевым словам. Никаких внешних зависимостей и сети.

Назначение: использовать как добавочный контекст для /insight при флаге
FEATURE_RAG=on.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(os.getenv("PROJECT_ROOT", ".")).resolve()
DOC_GLOBS = ["*.md"]
MAX_FILE_SIZE = 256 * 1024  # bytes, skip very large files
_INDEX: List[Tuple[str, str]] | None = None  # list of (source, chunk)


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
        except Exception:
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


def get_rag_stats() -> dict:
    """Get RAG system statistics."""
    items = _get_index()
    total_chunks = len(items)
    sources = {}
    for src, _ in items:
        src_name = Path(src).name
        sources[src_name] = sources.get(src_name, 0) + 1

    return {"total_chunks": total_chunks, "sources": sources, "index_loaded": _INDEX is not None}


def retrieve_context(query: str, max_chunks: int = 3) -> str:
    """Return top-k relevant chunks concatenated with brief headers."""
    items = _get_index()
    if not items:
        return ""

    # Enhanced scoring with multiple factors
    scored = []
    query_lower = query.lower()
    query_words = set(_tokenize(query))

    for src, ch in items:
        chunk_lower = ch.lower()
        chunk_words = set(_tokenize(ch))

        # Base keyword matching score
        base_score = _score(query, ch)

        # Boost for exact phrase matches
        if query_lower in chunk_lower:
            base_score += 0.3

        # Boost for word overlap (Jaccard similarity)
        if query_words and chunk_words:
            intersection = len(query_words & chunk_words)
            union = len(query_words | chunk_words)
            if union > 0:
                jaccard = intersection / union
                base_score += jaccard * 0.2

        scored.append((src, ch, base_score))

    scored.sort(key=lambda x: x[2], reverse=True)
    top = [x for x in scored[: max(1, max_chunks)] if x[2] > 0]

    if not top:
        return ""

    parts = []
    for src, ch, sc in top:
        parts.append(f"# Source: {Path(src).name} (score={sc:.2f})\n{ch}")
    return "\n\n".join(parts)

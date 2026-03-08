"""RAG formatting helpers — prompt building and source-item construction.

Moved out of ``legacy_app.py`` so it stays a thin proxy (AGENTS.md policy).
"""

from __future__ import annotations

from typing import TypedDict

from core.data_sanitizer import sanitize_rag_markdown
from core.insight.safety import redact_rag_context_for_insight
from core.rag.contracts import RAGChunk


class RAGSourceDict(TypedDict):
    """Typed dict for RAG source items returned by build_rag_source_dicts."""

    chunk_id: str
    file: str
    preview: str
    score: float


def format_rag_chunks_for_prompt(chunks: list[RAGChunk]) -> str:
    """Concatenate RAGChunk objects into a prompt-ready string with source headers."""
    parts: list[str] = []
    for ch in chunks:
        sanitized_content = sanitize_rag_markdown(ch.content).strip()
        if not sanitized_content:
            continue
        parts.append(f"# Source: {ch.file} (score={ch.score:.2f})\n{sanitized_content}")
    return "\n\n".join(parts)


def build_rag_source_dicts(chunks: list[RAGChunk]) -> list[RAGSourceDict]:
    """Build source-item dicts from RAGChunks with redacted previews.

    Returns plain dicts so the caller (``legacy_app.py``) can wrap them in
    ``RAGSourceItem`` without introducing a core→legacy import.
    """
    items: list[RAGSourceDict] = []
    for ch in chunks:
        sanitized_content = sanitize_rag_markdown(ch.content).strip()
        if not sanitized_content:
            continue
        preview = redact_rag_context_for_insight(sanitized_content)
        items.append(
            RAGSourceDict(
                chunk_id=ch.chunk_id,
                file=ch.file,
                preview=preview[:200] if preview else "",
                score=round(ch.score, 4),
            )
        )
    return items

"""RAG formatting helpers — prompt building and source-item construction.

Moved out of ``legacy_app.py`` so it stays a thin proxy (AGENTS.md policy).
"""

from __future__ import annotations

from typing import Any

from core.insight.safety import redact_rag_context_for_insight


def format_rag_chunks_for_prompt(chunks: list[Any]) -> str:
    """Concatenate RAGChunk objects into a prompt-ready string with source headers."""
    parts: list[str] = []
    for ch in chunks:
        parts.append(f"# Source: {ch.file} (score={ch.score:.2f})\n{ch.content}")
    return "\n\n".join(parts)


def build_rag_source_dicts(chunks: list[Any]) -> list[dict[str, Any]]:
    """Build source-item dicts from RAGChunks with redacted previews.

    Returns plain dicts so the caller (``legacy_app.py``) can wrap them in
    ``RAGSourceItem`` without introducing a core→legacy import.
    """
    items: list[dict[str, Any]] = []
    for ch in chunks:
        preview = redact_rag_context_for_insight(ch.content)
        items.append(
            {
                "chunk_id": ch.chunk_id,
                "file": ch.file,
                "preview": preview[:200] if preview else "",
                "score": round(ch.score, 4),
            }
        )
    return items

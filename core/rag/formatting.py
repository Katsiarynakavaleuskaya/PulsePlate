"""RAG formatting helpers — prompt building and source-item construction.

Moved out of ``legacy_app.py`` so it stays a thin proxy (AGENTS.md policy).
"""

from __future__ import annotations

import unicodedata
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


_FORBIDDEN_RAG_METADATA_CATEGORIES = frozenset({"Cc", "Cf", "Cn", "Cs", "Zl", "Zp"})
_VISIBLE_RAG_METADATA_MAJOR_CATEGORIES = frozenset({"L", "N", "P", "S"})
_VISIBLE_RAG_METADATA_EXACT_CATEGORIES = frozenset({"Co"})


def _is_safe_rag_metadata(value: object) -> bool:
    """Return whether metadata is bounded, visible, exact built-in text."""

    if not isinstance(value, str) or type(value) is not str:
        return False
    if not 1 <= len(value) <= 256 or not value.strip():
        return False
    categories = tuple(unicodedata.category(character) for character in value)
    return all(
        category not in _FORBIDDEN_RAG_METADATA_CATEGORIES for category in categories
    ) and any(
        category[0] in _VISIBLE_RAG_METADATA_MAJOR_CATEGORIES
        or category in _VISIBLE_RAG_METADATA_EXACT_CATEGORIES
        for category in categories
    )


def _prepare_final_rag_chunk_snapshot(
    chunks: list[RAGChunk],
) -> tuple[list[RAGChunk], bool]:
    """Return one final sanitized/redacted snapshot and pre-redaction viability."""

    final_chunks: list[RAGChunk] = []
    had_sanitized_survivor = False
    for chunk in chunks:
        if not (_is_safe_rag_metadata(chunk.chunk_id) and _is_safe_rag_metadata(chunk.file)):
            continue
        sanitized_content = sanitize_rag_markdown(chunk.content).strip()
        if not sanitized_content:
            continue
        had_sanitized_survivor = True
        redacted_content = redact_rag_context_for_insight(sanitized_content).strip()
        if not redacted_content:
            continue
        final_chunks.append(
            RAGChunk(
                chunk_id=chunk.chunk_id,
                file=chunk.file,
                content=redacted_content,
                score=chunk.score,
                hop=chunk.hop,
            )
        )
    return final_chunks, had_sanitized_survivor


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

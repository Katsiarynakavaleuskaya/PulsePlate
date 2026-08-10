"""Bounded request-local compaction for final validated RAG carriers."""

from __future__ import annotations

from core.rag.contracts import RAGChunk


def _chunks_are_exactly_equal(left: RAGChunk, right: RAGChunk) -> bool:
    """Compare every primitive carrier field with exact runtime type semantics."""

    left_values = (left.chunk_id, left.file, left.content, left.score, left.hop)
    right_values = (right.chunk_id, right.file, right.content, right.score, right.hop)
    return all(
        type(left_value) is type(right_value) and left_value == right_value
        for left_value, right_value in zip(left_values, right_values, strict=True)
    )


def _copy_chunk(chunk: RAGChunk) -> RAGChunk:
    """Return a new primitive-equivalent carrier."""

    return RAGChunk(
        chunk_id=chunk.chunk_id,
        file=chunk.file,
        content=chunk.content,
        score=chunk.score,
        hop=chunk.hop,
    )


def _first_occurrence_representatives(chunks: list[RAGChunk]) -> list[RAGChunk]:
    """Return the ordered representative sequence for exact carrier classes."""

    representatives: list[RAGChunk] = []
    for chunk in chunks:
        if any(_chunks_are_exactly_equal(chunk, seen) for seen in representatives):
            continue
        representatives.append(_copy_chunk(chunk))
    return representatives


def _is_exact_compaction_result(
    original: list[RAGChunk],
    candidate: list[RAGChunk],
    removed_count: object,
) -> bool:
    """Validate the full ordered exact-carrier postcondition."""

    if isinstance(removed_count, bool) or not isinstance(removed_count, int):
        return False
    expected = _first_occurrence_representatives(original)
    return (
        removed_count == len(original) - len(expected)
        and len(candidate) == len(expected)
        and all(
            _chunks_are_exactly_equal(candidate_chunk, expected_chunk)
            for candidate_chunk, expected_chunk in zip(candidate, expected, strict=True)
        )
    )


def compact_exact_duplicate_chunks(chunks: list[RAGChunk]) -> tuple[list[RAGChunk], int]:
    """Remove only exact duplicate carriers, preserving first occurrence and order.

    The request-local chunk count is bounded by retrieval configuration, so a
    direct equality scan keeps the contract obvious and avoids hashing evidence
    content or collapsing distinct provenance.
    """

    compacted = _first_occurrence_representatives(chunks)
    return compacted, len(chunks) - len(compacted)


__all__ = ["compact_exact_duplicate_chunks"]

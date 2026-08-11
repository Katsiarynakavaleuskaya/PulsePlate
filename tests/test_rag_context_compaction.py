"""Tests for the bounded exact-carrier RAG compaction helper."""

from __future__ import annotations

from dataclasses import fields

from core.rag.context_compaction import compact_exact_duplicate_chunks
from core.rag.contracts import RAGChunk


def _chunk(
    *,
    chunk_id: str = "chunk-1",
    file: str = "docs/example.md",
    content: str = "Balanced meals support everyday wellness.",
    score: float = 0.8,
    hop: int = 1,
) -> RAGChunk:
    return RAGChunk(
        chunk_id=chunk_id,
        file=file,
        content=content,
        score=score,
        hop=hop,
    )


def test_empty_input_returns_new_empty_list() -> None:
    raw: list[RAGChunk] = []

    compacted, removed = compact_exact_duplicate_chunks(raw)

    assert compacted == []
    assert compacted is not raw
    assert removed == 0


def test_exact_duplicates_collapse_to_first_occurrence_without_aliasing() -> None:
    first = _chunk()
    duplicate = _chunk()
    trailing = _chunk(chunk_id="chunk-2", content="A second evidence carrier.")
    raw = [first, duplicate, trailing]
    original_values = [
        (chunk.chunk_id, chunk.file, chunk.content, chunk.score, chunk.hop) for chunk in raw
    ]

    compacted, removed = compact_exact_duplicate_chunks(raw)

    assert removed == 1
    assert compacted == [first, trailing]
    assert compacted[0] is not first
    assert compacted[1] is not trailing
    assert [
        (chunk.chunk_id, chunk.file, chunk.content, chunk.score, chunk.hop) for chunk in raw
    ] == original_values


def test_every_primitive_field_participates_in_exact_identity() -> None:
    baseline = _chunk()
    variants = [
        _chunk(chunk_id="chunk-other"),
        _chunk(file="docs/other.md"),
        _chunk(content="Different content."),
        _chunk(score=0.7),
        _chunk(hop=2),
    ]

    compacted, removed = compact_exact_duplicate_chunks([baseline, *variants])

    assert removed == 0
    assert compacted == [baseline, *variants]


def test_compaction_field_sentinel_matches_frozen_rag_chunk_contract() -> None:
    """A new carrier field must not silently bypass exact compaction identity."""

    assert tuple(field.name for field in fields(RAGChunk)) == (
        "chunk_id",
        "file",
        "content",
        "score",
        "hop",
    )


def test_same_content_with_distinct_evidence_reference_is_preserved() -> None:
    first = _chunk(chunk_id="chunk-a", file="docs/a.md")
    second = _chunk(chunk_id="chunk-b", file="docs/b.md")

    compacted, removed = compact_exact_duplicate_chunks([first, second])

    assert removed == 0
    assert [chunk.chunk_id for chunk in compacted] == ["chunk-a", "chunk-b"]


def test_nan_scores_remain_distinct_and_ordered() -> None:
    first = _chunk(score=float("nan"))
    second = _chunk(score=float("nan"))

    compacted, removed = compact_exact_duplicate_chunks([first, second])

    assert removed == 0
    assert len(compacted) == 2
    assert compacted[0].chunk_id == first.chunk_id
    assert compacted[1].chunk_id == second.chunk_id


def test_equal_numeric_values_with_distinct_runtime_types_are_not_duplicates() -> None:
    integer_score = _chunk(score=1)
    float_score = _chunk(score=1.0)

    compacted, removed = compact_exact_duplicate_chunks([integer_score, float_score])

    assert removed == 0
    assert len(compacted) == 2
    assert type(compacted[0].score) is int
    assert type(compacted[1].score) is float


def test_equal_hop_values_with_bool_and_int_types_are_not_duplicates() -> None:
    boolean_hop = _chunk(hop=True)
    integer_hop = _chunk(hop=1)

    compacted, removed = compact_exact_duplicate_chunks([boolean_hop, integer_hop])

    assert removed == 0
    assert len(compacted) == 2
    assert type(compacted[0].hop) is bool
    assert type(compacted[1].hop) is int

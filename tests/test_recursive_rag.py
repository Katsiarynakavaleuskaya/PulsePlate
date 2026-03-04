"""Tests for deterministic recursive retrieval (core/rag/recursive_retrieval.py)."""

from __future__ import annotations

from typing import Any

import pytest

from core.rag.contracts import RAGChunk, RAGContext
from core.rag.philosophy_pipeline import PipelineResult
from core.rag.recursive_retrieval import retrieve_recursive_context_structured
from core.rag.validation import ValidationResult


def _ctx(query: str, chunks: list[RAGChunk], confidence: float = 0.6) -> RAGContext:
    return RAGContext(
        query=query,
        refined_queries=[query],
        chunks=chunks,
        confidence=confidence,
        hops=1,
        latency_ms=10,
    )


def test_recursive_retrieval_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same input must produce identical refined_queries/chunks ordering."""
    import core.rag.recursive_retrieval as recursive

    monkeypatch.setattr(recursive, "MAX_RAG_HOPS", 3)
    monkeypatch.setattr(recursive, "MAX_REFINEMENT_PASSES", 3)
    monkeypatch.setattr(recursive, "MAX_VERIFICATION_QUERIES", 0)
    monkeypatch.setattr(recursive, "MIN_CONFIDENCE_GAIN_PER_HOP", -1.0)

    def _fake_retrieve(query: str, **_: Any) -> RAGContext:
        if "fiber protein" in query.lower():
            return _ctx(query, [], confidence=0.0)
        return _ctx(
            query,
            [
                RAGChunk(
                    chunk_id="doc:1",
                    file="doc.md",
                    content="Fiber protein vegetables improve satiety.",
                    score=0.8,
                )
            ],
            confidence=0.8,
        )

    monkeypatch.setattr("core.rag.vector_rag.retrieve_context_structured", _fake_retrieve)

    r1 = retrieve_recursive_context_structured("What should I eat?")
    r2 = retrieve_recursive_context_structured("What should I eat?")

    assert r1.refined_queries == r2.refined_queries
    assert [c.chunk_id for c in r1.chunks] == [c.chunk_id for c in r2.chunks]
    assert r1.confidence == r2.confidence
    assert r1.hops == r2.hops


def test_recursive_respects_hops_and_refinement_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recursive loop respects MAX_RAG_HOPS and MAX_REFINEMENT_PASSES."""
    import core.rag.recursive_retrieval as recursive

    monkeypatch.setattr(recursive, "MAX_RAG_HOPS", 2)
    monkeypatch.setattr(recursive, "MAX_REFINEMENT_PASSES", 1)
    monkeypatch.setattr(recursive, "MAX_VERIFICATION_QUERIES", 0)
    monkeypatch.setattr(recursive, "MIN_CONFIDENCE_GAIN_PER_HOP", -1.0)

    def _fake_retrieve(query: str, **_: Any) -> RAGContext:
        token = f"signal{len(query)}"
        chunk = RAGChunk(
            chunk_id=f"doc:{len(query)}",
            file="doc.md",
            content=f"{token} nutrition guidance for meal planning",
            score=0.7,
        )
        return _ctx(query, [chunk], confidence=0.7)

    monkeypatch.setattr("core.rag.vector_rag.retrieve_context_structured", _fake_retrieve)

    result = retrieve_recursive_context_structured("meal plan")
    assert result.hops <= 2
    assert len(result.refined_queries) <= 2


def test_recursive_respects_verification_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verification functions are bounded by MAX_VERIFICATION_QUERIES."""
    import core.rag.recursive_retrieval as recursive

    monkeypatch.setattr(recursive, "MAX_RAG_HOPS", 3)
    monkeypatch.setattr(recursive, "MAX_REFINEMENT_PASSES", 3)
    monkeypatch.setattr(recursive, "MAX_VERIFICATION_QUERIES", 1)
    monkeypatch.setattr(recursive, "MIN_CONFIDENCE_GAIN_PER_HOP", -1.0)

    calls = {"validate": 0, "pipeline": 0}

    def _fake_retrieve(query: str, **_: Any) -> RAGContext:
        token = f"refine{len(query)}"
        return _ctx(
            query,
            [
                RAGChunk(
                    chunk_id=f"id-{len(query)}",
                    file="doc.md",
                    content=f"{token} fiber proteins and vegetables",
                    score=0.8,
                )
            ],
            confidence=0.8,
        )

    def _fake_validate(chunks: list[RAGChunk], agent_id: str | None = None) -> ValidationResult:
        del agent_id
        calls["validate"] += 1
        return ValidationResult(
            passed=True,
            filtered_chunks=chunks,
            warnings=[],
            rejected_count=0,
            validation_latency_ms=1,
        )

    def _fake_pipeline(chunks: list[RAGChunk], query: str) -> PipelineResult:
        del query
        calls["pipeline"] += 1
        return PipelineResult(
            filtered_chunks=chunks,
            stage_results=[],
            warnings=[],
            total_latency_ms=1.0,
        )

    monkeypatch.setattr("core.rag.vector_rag.retrieve_context_structured", _fake_retrieve)
    monkeypatch.setattr("core.rag.validation.validate_rag_chunks", _fake_validate)
    monkeypatch.setattr("core.rag.philosophy_pipeline.run_pipeline", _fake_pipeline)

    retrieve_recursive_context_structured("recursion", philo_validation_enabled=True)
    assert calls["validate"] == 1
    assert calls["pipeline"] == 1


def test_recursive_early_stop_on_low_confidence_gain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second hop stops when confidence gain is below threshold."""
    import core.rag.recursive_retrieval as recursive

    monkeypatch.setattr(recursive, "MAX_RAG_HOPS", 4)
    monkeypatch.setattr(recursive, "MAX_REFINEMENT_PASSES", 4)
    monkeypatch.setattr(recursive, "MAX_VERIFICATION_QUERIES", 0)
    monkeypatch.setattr(recursive, "MIN_CONFIDENCE_GAIN_PER_HOP", 0.25)

    def _fake_retrieve(query: str, **_: Any) -> RAGContext:
        token = f"growth{len(query)}"
        return _ctx(
            query,
            [
                RAGChunk(
                    chunk_id=f"stable-{len(query)}",
                    file="doc.md",
                    content=f"{token} balanced diet basics",
                    score=0.5,
                )
            ],
            confidence=0.5,
        )

    monkeypatch.setattr("core.rag.vector_rag.retrieve_context_structured", _fake_retrieve)
    result = retrieve_recursive_context_structured("diet")

    assert result.hops == 2
    assert result.confidence == 0.5


def test_recursive_fail_safe_on_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Internal retrieval failure must return safe empty context."""

    def _boom(*_: Any, **__: Any) -> RAGContext:
        raise RuntimeError("boom")

    monkeypatch.setattr("core.rag.vector_rag.retrieve_context_structured", _boom)

    result = retrieve_recursive_context_structured("safe fallback")
    assert result.chunks == []
    assert result.confidence == 0.0
    assert result.hops >= 1

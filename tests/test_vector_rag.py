"""Tests for core/rag/vector_rag.py — vector retrieval and Jaccard fallback.

All tests mock the embedding provider to avoid model download.
DB operations use SQLite (test default).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock

import pytest

from core.rag.contracts import RAGChunk, RAGContext

# ---------------------------------------------------------------------------
# Fake RAG context for Jaccard fallback verification
# ---------------------------------------------------------------------------


@dataclass
class _FakeChunk:
    chunk_id: str
    file: str
    content: str
    score: float
    hop: int = 1


@dataclass
class _FakeContext:
    query: str
    refined_queries: list[str]
    chunks: list[_FakeChunk]
    confidence: float
    hops: int
    latency_ms: int
    agent_id: Optional[str] = None
    user_tier: Optional[str] = None


def _fake_jaccard(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
) -> _FakeContext:
    return _FakeContext(
        query=query,
        refined_queries=[query],
        chunks=[_FakeChunk("j:1", "doc.md", "jaccard result", 0.5)],
        confidence=0.5,
        hops=1,
        latency_ms=5,
        agent_id=agent_id,
        user_tier=user_tier,
    )


class TestCosineSimility:
    """Unit tests for _cosine_similarity helper."""

    def test_identical_vectors(self) -> None:
        from core.rag.vector_rag import _cosine_similarity

        v = [1.0, 0.0, 0.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        from core.rag.vector_rag import _cosine_similarity

        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        from core.rag.vector_rag import _cosine_similarity

        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self) -> None:
        from core.rag.vector_rag import _cosine_similarity

        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_both_zero_returns_zero(self) -> None:
        from core.rag.vector_rag import _cosine_similarity

        assert _cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


class TestVectorRetrievalFallback:
    """Vector retrieval falls back to Jaccard when disabled or on failure."""

    def test_flag_off_uses_jaccard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """FEATURE_RAG_VECTOR=false must use Jaccard retrieval."""
        monkeypatch.setenv("FEATURE_RAG_VECTOR", "false")

        import core.rag.vector_rag as vector_rag

        monkeypatch.setattr("core.rag.vector_rag.is_rag_vector_enabled", lambda: False)
        monkeypatch.setattr("core.rag.simple_rag.retrieve_context_structured", _fake_jaccard)

        ctx = vector_rag.retrieve_context_structured("test query")
        assert isinstance(ctx, _FakeContext)
        assert ctx.chunks[0].chunk_id == "j:1"
        assert ctx.chunks[0].content == "jaccard result"

    def test_flag_on_vector_error_falls_back_to_jaccard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Vector failure must fall back to Jaccard (no 500)."""
        monkeypatch.setenv("FEATURE_RAG_VECTOR", "true")

        import core.rag.vector_rag as vector_rag

        monkeypatch.setattr("core.rag.vector_rag.is_rag_vector_enabled", lambda: True)
        monkeypatch.setattr(
            "core.rag.vector_rag._retrieve_vector_from_db",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("DB down")),
        )
        monkeypatch.setattr("core.rag.simple_rag.retrieve_context_structured", _fake_jaccard)

        ctx = vector_rag.retrieve_context_structured("test query")
        assert isinstance(ctx, _FakeContext)
        assert ctx.chunks[0].chunk_id == "j:1"

    def test_flag_on_empty_vector_results_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If vector returns no chunks, fall back to Jaccard."""
        import core.rag.vector_rag as vector_rag

        empty_ctx = RAGContext(
            query="q",
            refined_queries=["q"],
            chunks=[],
            confidence=0.0,
            hops=1,
            latency_ms=1,
        )

        monkeypatch.setattr("core.rag.vector_rag.is_rag_vector_enabled", lambda: True)
        monkeypatch.setattr(
            "core.rag.vector_rag._retrieve_vector_from_db",
            lambda *a, **k: empty_ctx,
        )
        monkeypatch.setattr("core.rag.simple_rag.retrieve_context_structured", _fake_jaccard)

        ctx = vector_rag.retrieve_context_structured("test query")
        assert isinstance(ctx, _FakeContext)
        assert ctx.chunks[0].chunk_id == "j:1"


class TestVectorRetrievalSQLite:
    """Test vector retrieval using SQLite (application-level cosine)."""

    def test_retrieve_vector_sqlite_scores_correctly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_retrieve_vector_sqlite returns rows scored by cosine similarity."""
        from core.rag import vector_rag

        # Use 3-dim for test simplicity
        monkeypatch.setattr(vector_rag, "EMBEDDING_DIMENSIONS", 3)

        query_vec = [1.0, 0.0, 0.0]

        class _Row:
            def __init__(self, id: int, content: str, source: str, embedding: str) -> None:
                self.id = id
                self.content = content
                self.source = source
                self.embedding = embedding

        rows = [
            _Row(1, "similar doc", "src1", json.dumps([0.9, 0.1, 0.0])),
            _Row(2, "less similar", "src2", json.dumps([0.1, 0.9, 0.0])),
            _Row(3, "bad embedding", "src3", "not-json"),
        ]

        fake_session = MagicMock()
        fake_session.execute.return_value.fetchall.return_value = rows

        results = vector_rag._retrieve_vector_sqlite(query_vec, 5, fake_session)

        # Should have 2 valid results (3rd row has bad JSON)
        assert len(results) == 2
        # First result should be most similar
        assert results[0][0].id == 1
        assert results[0][1] > results[1][1]

    def test_retrieve_vector_sqlite_limits_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.rag import vector_rag

        monkeypatch.setattr(vector_rag, "EMBEDDING_DIMENSIONS", 3)

        query_vec = [1.0, 0.0, 0.0]

        class _Row:
            def __init__(self, id: int, embedding: str) -> None:
                self.id = id
                self.content = f"doc {id}"
                self.source = "src"
                self.embedding = embedding

        rows = [_Row(i, json.dumps([1.0, 0.0, 0.0])) for i in range(10)]

        fake_session = MagicMock()
        fake_session.execute.return_value.fetchall.return_value = rows

        results = vector_rag._retrieve_vector_sqlite(query_vec, 3, fake_session)
        assert len(results) == 3

    def test_retrieve_vector_sqlite_skips_wrong_dimensions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.rag import vector_rag

        monkeypatch.setattr(vector_rag, "EMBEDDING_DIMENSIONS", 3)

        query_vec = [1.0, 0.0, 0.0]

        class _Row:
            def __init__(self, id: int, embedding: str) -> None:
                self.id = id
                self.content = "doc"
                self.source = "src"
                self.embedding = embedding

        rows = [
            _Row(1, json.dumps([1.0, 0.0])),  # wrong dim (2 instead of 3)
        ]

        fake_session = MagicMock()
        fake_session.execute.return_value.fetchall.return_value = rows

        results = vector_rag._retrieve_vector_sqlite(query_vec, 5, fake_session)
        assert len(results) == 0


class TestEmptyContext:
    """Test _empty_context helper."""

    def test_empty_context_fields(self) -> None:
        import time

        from core.rag.vector_rag import _empty_context

        start = time.perf_counter()
        ctx = _empty_context("test", "agent-1", "PRO", start)
        assert isinstance(ctx, RAGContext)
        assert ctx.query == "test"
        assert ctx.chunks == []
        assert ctx.confidence == 0.0
        assert ctx.hops == 1
        assert ctx.agent_id == "agent-1"
        assert ctx.user_tier == "PRO"


class TestResetEmbeddingProvider:
    """Test singleton reset for test isolation."""

    def test_reset_clears_provider(self) -> None:
        from core.rag import vector_rag

        vector_rag._embedding_provider = "something"
        vector_rag.reset_embedding_provider()
        assert vector_rag._embedding_provider is None

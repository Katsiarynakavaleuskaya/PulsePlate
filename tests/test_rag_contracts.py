"""
Tests for RAG contract types and constants per RAG_CONTRACT.md §3–§4.

Covers: RAGChunk, RAGContext, rag_constants, retrieve_context_structured.
"""

from __future__ import annotations

import pytest

from core.rag.contracts import RAGChunk, RAGContext
from core.rag.rag_constants import (
    MAX_CHUNK_SIZE_CHARS,
    MAX_CHUNKS_PER_HOP,
    MAX_RAG_HOPS,
    MAX_SOURCES_IN_RESPONSE,
    MIN_CHUNK_SCORE,
    RAG_PIPELINE_TIMEOUT_SEC,
)


class TestRAGChunk:
    """RAGChunk dataclass per RAG_CONTRACT §3."""

    def test_rag_chunk_default_hop(self) -> None:
        c = RAGChunk(chunk_id="a", file="f.md", content="x", score=0.5)
        assert c.hop == 1

    def test_rag_chunk_explicit_hop(self) -> None:
        c = RAGChunk(chunk_id="b", file="g.md", content="y", score=0.8, hop=2)
        assert c.hop == 2


class TestRAGContext:
    """RAGContext dataclass per RAG_CONTRACT §3."""

    def test_rag_context_minimal(self) -> None:
        ctx = RAGContext(
            query="q",
            refined_queries=["q"],
            chunks=[],
            confidence=0.0,
            hops=1,
            latency_ms=10,
        )
        assert ctx.agent_id is None
        assert ctx.user_tier is None

    def test_rag_context_with_agent_tier(self) -> None:
        ctx = RAGContext(
            query="q",
            refined_queries=["q", "q2"],
            chunks=[],
            confidence=0.5,
            hops=2,
            latency_ms=100,
            agent_id="cbt-agent",
            user_tier="PRO",
        )
        assert ctx.agent_id == "cbt-agent"
        assert ctx.user_tier == "PRO"


class TestRAGConstants:
    """Constants per RAG_CONTRACT §4."""

    def test_budget_constants_values(self) -> None:
        assert MAX_RAG_HOPS == 3
        assert MAX_CHUNKS_PER_HOP == 5
        assert MAX_SOURCES_IN_RESPONSE == 5
        assert RAG_PIPELINE_TIMEOUT_SEC == 10
        assert MIN_CHUNK_SCORE == 0.1
        assert MAX_CHUNK_SIZE_CHARS == 800


class TestRetrieveContextStructured:
    """retrieve_context_structured returns RAGContext."""

    def test_retrieve_context_structured_empty_index(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.rag import simple_rag

        monkeypatch.setattr(simple_rag, "_get_index", lambda: [])
        from core.rag.simple_rag import retrieve_context_structured

        ctx = retrieve_context_structured("any query")
        assert isinstance(ctx, RAGContext)
        assert ctx.query == "any query"
        assert ctx.chunks == []
        assert ctx.confidence == 0.0
        assert ctx.hops == 1
        assert ctx.latency_ms >= 0
        assert ctx.refined_queries == ["any query"]

    def test_retrieve_context_structured_with_agent_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from core.rag import simple_rag

        monkeypatch.setattr(simple_rag, "_get_index", lambda: [])
        from core.rag.simple_rag import retrieve_context_structured

        ctx = retrieve_context_structured("query", agent_id="insight-default", user_tier="FREE")
        assert ctx.agent_id == "insight-default"
        assert ctx.user_tier == "FREE"

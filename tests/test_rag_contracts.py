"""Tests for core.rag.contracts and core.rag.rag_constants (RAG contract types)."""

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


def test_rag_chunk_dataclass() -> None:
    """RAGChunk has required fields and default hop=1."""
    ch = RAGChunk(
        chunk_id="c1",
        file="docs/foo.md",
        content="Some text",
        score=0.85,
    )
    assert ch.chunk_id == "c1"
    assert ch.file == "docs/foo.md"
    assert ch.content == "Some text"
    assert ch.score == 0.85
    assert ch.hop == 1

    ch2 = RAGChunk(chunk_id="c2", file="f", content="x", score=0.1, hop=2)
    assert ch2.hop == 2


def test_rag_context_dataclass() -> None:
    """RAGContext has required fields and optional agent_id/user_tier."""
    ctx = RAGContext(
        query="q",
        refined_queries=["q"],
        chunks=[],
        confidence=0.0,
        hops=1,
        latency_ms=50,
    )
    assert ctx.query == "q"
    assert ctx.refined_queries == ["q"]
    assert ctx.chunks == []
    assert ctx.confidence == 0.0
    assert ctx.hops == 1
    assert ctx.latency_ms == 50
    assert ctx.agent_id is None
    assert ctx.user_tier is None

    ctx2 = RAGContext(
        query="q2",
        refined_queries=[],
        chunks=[],
        confidence=0.9,
        hops=2,
        latency_ms=100,
        agent_id="cbt-agent",
        user_tier="VIP",
    )
    assert ctx2.agent_id == "cbt-agent"
    assert ctx2.user_tier == "VIP"


def test_rag_constants_values() -> None:
    """Constants match RAG_CONTRACT.md §4."""
    assert MAX_RAG_HOPS == 3
    assert MAX_CHUNKS_PER_HOP == 5
    assert MAX_SOURCES_IN_RESPONSE == 5
    assert RAG_PIPELINE_TIMEOUT_SEC == 10
    assert MIN_CHUNK_SCORE == 0.1
    assert MAX_CHUNK_SIZE_CHARS == 800

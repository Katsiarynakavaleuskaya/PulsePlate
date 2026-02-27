"""
RAG internal contract types per docs/contracts/RAG_CONTRACT.md §3.

RAGChunk and RAGContext are passed between agents and used to build
Insight response fields (sources, confidence, hops, latency_ms).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RAGChunk:
    """Single retrieved chunk with provenance and score."""

    chunk_id: str
    file: str
    content: str
    score: float
    hop: int = 1


@dataclass
class RAGContext:
    """Full RAG retrieval result for agent/response pipeline."""

    query: str
    refined_queries: list[str]
    chunks: list[RAGChunk]
    confidence: float
    hops: int
    latency_ms: int
    agent_id: Optional[str] = None
    user_tier: Optional[str] = None

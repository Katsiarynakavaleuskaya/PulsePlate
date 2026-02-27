"""
RAG contract types: RAGChunk and RAGContext (per docs/contracts/RAG_CONTRACT.md §3).

RU: Внутренний контракт агента — структуры, передаваемые между RAG и LLM/агентами.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RAGChunk:
    """Single retrieved chunk with metadata."""

    chunk_id: str
    file: str
    content: str
    score: float
    hop: int = 1


@dataclass
class RAGContext:
    """Context produced by retrieval, passed to agents/LLM."""

    query: str
    refined_queries: list[str]
    chunks: list[RAGChunk]
    confidence: float
    hops: int
    latency_ms: int
    agent_id: Optional[str] = None
    user_tier: Optional[str] = None

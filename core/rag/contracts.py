"""
RAG internal contract types per docs/contracts/RAG_CONTRACT.md §3.

RAGChunk and RAGContext are passed between agents and used to build
Insight response fields (sources, confidence, hops, latency_ms).

AGENT_CORPUS_MAP defines corpus paths per agent for filtered retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Agent Corpus Mapping (per RAG_CONTRACT.md §6)
# ---------------------------------------------------------------------------

AGENT_CORPUS_MAP: dict[str, list[str]] = {
    "cbt-agent": ["docs/cbt/", "docs/psychology/"],
}
"""Maps agent_id to list of corpus path prefixes for filtered retrieval."""


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

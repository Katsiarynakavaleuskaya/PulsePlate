"""
RAG internal contract types per docs/contracts/RAG_CONTRACT.md §3.

RAGChunk and RAGContext are passed between agents and used to build
Insight response fields (sources, confidence, hops, latency_ms).

AGENT_CORPUS_MAP defines corpus paths per agent for filtered retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, TypedDict

# ---------------------------------------------------------------------------
# Agent Corpus Mapping (per RAG_CONTRACT.md §6)
# ---------------------------------------------------------------------------

AGENT_CORPUS_MAP: dict[str, list[str]] = {
    "cbt-agent": ["docs/cbt/", "docs/psychology/"],
}
"""Maps agent_id to list of corpus path prefixes for filtered retrieval."""


class OptimizationStopReason(str, Enum):
    """Deterministic stop reasons for recursive runtime optimization."""

    COMPLETED = "completed"
    EMPTY_HOP = "empty_hop"
    LATENCY_BUDGET = "latency_budget"
    LOW_CONFIDENCE_GAIN = "low_confidence_gain"
    NO_MATERIAL_QUERY_CHANGE = "no_material_query_change"
    NO_NEW_USABLE_CHUNKS = "no_new_usable_chunks"
    NO_USABLE_CHUNKS = "no_usable_chunks"
    REFINEMENT_BUDGET = "refinement_budget"


class OptimizationStats(TypedDict):
    """Internal optimization diagnostics for a single recursive request."""

    enabled: bool
    retrieval_cache_hits: int
    refinement_cache_hits: int
    cache_hits: int
    verification_calls: int
    stop_reason: OptimizationStopReason
    early_stop_no_query_change: bool
    early_stop_no_new_chunks: bool
    early_stop_low_confidence_gain: bool
    early_stop_latency_budget: bool


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
    optimization_stats: OptimizationStats | None = None

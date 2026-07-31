"""Canonical request and response schemas for Insight compatibility routes."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

INSIGHT_TEXT_MAX_LENGTH = 2000


class InsightRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=INSIGHT_TEXT_MAX_LENGTH)


class RAGSourceItem(BaseModel):
    """Single RAG source in Insight response per RAG_CONTRACT.md §2."""

    chunk_id: str
    file: str
    preview: str
    score: float


class InsightResponse(BaseModel):
    """Insight response payload per RAG_CONTRACT.md §2.

    RU: Явная модель ответа нужна для стабильного OpenAPI и генерации типов фронтенда.
    EN: Explicit response model keeps OpenAPI stable and enables TS type generation.

    New RAG/runtime fields are optional with safe defaults so old clients keep
    working without changes.
    """

    provider: str = Field(..., min_length=1)
    insight: str = Field(..., min_length=1)
    sources: list[RAGSourceItem] = Field(default_factory=list)
    confidence: Optional[float] = None
    rag_used: bool = False
    hops: int = 0
    latency_ms: int = 0
    route_type: Optional[str] = None
    depth_used: int = 0
    verification_rate: Optional[float] = None
    falsifiability_rate: Optional[float] = None
    contradiction_count: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    optimization_applied: bool = False
    automated_analysis: bool = False
    transparency_notice_id: Optional[str] = None
    wellness_boundary: Optional[str] = None


__all__ = [
    "INSIGHT_TEXT_MAX_LENGTH",
    "InsightRequest",
    "InsightResponse",
    "RAGSourceItem",
]

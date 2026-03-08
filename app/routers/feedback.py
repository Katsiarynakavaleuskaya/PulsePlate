"""RAG Feedback collection endpoints.

Collects user feedback on RAG responses for quality improvement.
Tier: FREE (feedback collection benefits all users, requires any valid API key).

See:
- docs/contracts/RAG_CONTRACT.md (§7 Feedback Schema)
- docs/db/rag_feedback_schema.md
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from sqlalchemy.orm import Session

from fastapi import Security

from app.middleware.api_tiers import (
    CurrentUser,
    derive_subject_id_from_api_key,
    api_key_header,
)
from core.compliance import minimize_free_text, sanitize_chunk_preview
from core.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class RAGChunkInput(BaseModel):
    """Input schema for a retrieved chunk in feedback."""

    chunk_id: Optional[str] = Field(None, max_length=256)
    file: Optional[str] = Field(None, max_length=512)
    preview: Optional[str] = Field(None, max_length=2000)
    score: Optional[float] = Field(None, ge=0.0, le=1.0)


class RAGFeedbackRequest(BaseModel):
    """Request schema for submitting RAG feedback."""

    agent_id: Optional[str] = Field(None, max_length=64)
    query: str = Field(..., min_length=1, max_length=10000)
    retrieved_chunks: Optional[List[RAGChunkInput]] = Field(None, max_length=50)
    llm_response: Optional[str] = Field(None, max_length=50000)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_correction: Optional[str] = Field(None, max_length=50000)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    hops: Optional[int] = Field(None, ge=0)

    @field_validator("query")
    @classmethod
    def minimize_query(cls, value: str) -> str:
        """Minimize raw user query after contract validation."""
        minimized = minimize_free_text(value, field_name="query")
        return minimized or ""

    @field_validator("llm_response", "user_correction")
    @classmethod
    def redact_pii(cls, value: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Minimize free-form text fields before storage."""
        if value is None:
            return None
        field_name: str = str(info.field_name or "llm_response")
        minimized: Optional[str]
        minimized = minimize_free_text(value, field_name=field_name)
        return minimized


class RAGFeedbackResponse(BaseModel):
    """Response schema for feedback submission."""

    id: int
    message: str = "Feedback submitted successfully"


async def get_feedback_user(
    x_api_key: Optional[str] = Security(api_key_header),
) -> CurrentUser:
    """Get user context for feedback submission.

    Accepts any valid API key (not tier-specific) to enable feedback
    collection from all users.

    Raises:
        HTTPException 401: If no API key provided
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required for feedback submission",
        )
    user_id = derive_subject_id_from_api_key(x_api_key)
    return CurrentUser(user_id=user_id, api_key=x_api_key)


@router.post(
    "/rag",
    response_model=RAGFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit RAG feedback",
    description="Submit feedback on a RAG response for quality improvement.",
)
def submit_rag_feedback(
    feedback: RAGFeedbackRequest,
    current_user: CurrentUser = Depends(get_feedback_user),
    db: Session = Depends(get_session),
) -> RAGFeedbackResponse:
    """
    Submit feedback on a RAG (Retrieval-Augmented Generation) response.

    **Security**: PII in llm_response and user_correction is automatically
    redacted and minimized before storage.

    **Fields**:
    - **query**: User's original query (required)
    - **retrieved_chunks**: List of retrieved document chunks with scores
    - **llm_response**: LLM response text (PII auto-redacted)
    - **user_rating**: 1-5 satisfaction rating
    - **user_correction**: User's corrected/expected response (PII auto-redacted)
    - **confidence**: RAG confidence score (0.0-1.0)
    - **hops**: Number of retrieval hops used
    """
    # Convert chunks to serializable format
    chunks_data: Optional[List[Dict[str, Any]]] = None
    if feedback.retrieved_chunks:
        chunks_data = [
            {
                "chunk_id": c.chunk_id,
                "file": c.file,
                "preview": sanitize_chunk_preview(c.preview),
                "score": c.score,
            }
            for c in feedback.retrieved_chunks
        ]

    from app.models import RAGFeedback  # lazy import per OpenAPI generation policy

    record = RAGFeedback(
        user_id=current_user.user_id,
        agent_id=feedback.agent_id,
        query=feedback.query,
        retrieved_chunks=chunks_data,
        llm_response=feedback.llm_response,  # Already minimized by validator
        user_rating=feedback.user_rating,
        user_correction=feedback.user_correction,  # Already minimized by validator
        confidence=feedback.confidence,
        hops=feedback.hops,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "RAG feedback submitted",
        extra={
            "feedback_id": record.id,
            "agent_id": feedback.agent_id,
            "has_rating": feedback.user_rating is not None,
            "has_correction": feedback.user_correction is not None,
        },
    )

    return RAGFeedbackResponse(id=record.id)

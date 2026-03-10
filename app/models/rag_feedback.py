"""RAG feedback storage models.

Tracks user feedback on RAG responses for quality improvement and stores
user-contributed knowledge for VIP personalization.

Migration from RAG_CONTRACT.md schema (§7):
- Uses Integer PK (not UUID) to align with existing tables
- Uses BigInteger subject principal for user-bound isolation
- PostgreSQL RLS policies enabled via transaction-local session context
- JSONB via JSONEncodedDict for SQLite compatibility

See: docs/contracts/RAG_CONTRACT.md, docs/db/rag_feedback_schema.md
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.db import Base
from app.models.events import JSONEncodedDict


class RAGFeedback(Base):
    """User feedback on RAG responses.

    Stores user ratings, corrections, and metadata about RAG interactions
    to enable recursive learning and quality improvement.

    Security:
    - PostgreSQL RLS isolates rows by authenticated user_id
    - Application-layer filtering remains as defense in depth
    - PII redacted before storage via core.pii_redaction.redact_pii_from_text()

    Fields:
    - query: Minimized user query text
    - retrieved_chunks: JSON array of {chunk_id, file, preview, score}
    - llm_response: Minimized LLM response text
    - user_rating: 1-5 satisfaction rating
    - user_correction: User's corrected/expected response (PII redacted)
    - confidence: RAG confidence score (0.0-1.0)
    - hops: Number of retrieval hops used
    """

    __tablename__ = "rag_feedback"
    __table_args__ = (
        CheckConstraint("user_rating BETWEEN 1 AND 5", name="ck_rag_feedback_rating"),
        CheckConstraint("confidence BETWEEN 0.0 AND 1.0", name="ck_rag_feedback_confidence"),
        CheckConstraint("hops >= 0", name="ck_rag_feedback_hops"),
        Index("idx_rag_feedback_user_created", "user_id", "created_at"),
        Index(
            "idx_rag_feedback_agent",
            "agent_id",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)

    # JSONB for Postgres, TEXT for SQLite (via JSONEncodedDict)
    # Stores: [{chunk_id: str, file: str, preview: str, score: float}]
    retrieved_chunks: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONEncodedDict, nullable=True
    )

    # Minimization/redaction applied before storage
    llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    user_correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hops: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class UserKnowledge(Base):
    """User-contributed knowledge for VIP personalization.

    Stores user-specific content that can be used for personalized RAG retrieval.
    VIP-only feature for building personalized knowledge base.

    Note: embedding column requires pgvector extension on Postgres.
    On SQLite (tests), embeddings are stored as TEXT/JSON (not searchable).

    Security:
    - PostgreSQL RLS isolates rows by authenticated user_id
    - Application-layer filtering remains as defense in depth
    - Content should not contain PII without user consent

    Future enhancements (tracked in BACKLOG_LEDGER):
    - Vector similarity search API
    - Embedding generation pipeline
    - IVFFlat/HNSW index for production
    """

    __tablename__ = "user_knowledge"
    __table_args__ = (
        Index("idx_user_knowledge_user", "user_id"),
        Index("idx_user_knowledge_source", "source"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Embedding vector for semantic search
    # On Postgres with pgvector: VECTOR(768) (after migration 202602280003)
    # On SQLite (tests): TEXT storing JSON array; app-level cosine in vector_rag.py
    # See: core/rag/vector_rag.py for dialect-aware retrieval
    embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

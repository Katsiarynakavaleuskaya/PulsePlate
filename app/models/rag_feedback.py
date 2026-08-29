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

from collections.abc import MutableMapping
from datetime import datetime
import json
import math
from numbers import Real
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
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine, UserDefinedType

from core.db import Base
from app.models.events import JSONEncodedDict


class _FallbackVectorType(UserDefinedType):
    """Minimal PostgreSQL VECTOR type when the optional binding is absent."""

    cache_ok = True

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim

    def get_col_spec(self, **_: object) -> str:
        return "VECTOR" if self.dim is None else f"VECTOR({self.dim})"


def _select_vector_type_factory(
    installed_factory: type[UserDefinedType] | None,
    import_error: BaseException | None,
) -> type[UserDefinedType]:
    """Select the installed owner or the fallback for a truly absent package."""

    if installed_factory is not None:
        if import_error is not None:
            raise RuntimeError("postgresql_vector_factory_ambiguous")
        return installed_factory
    if isinstance(import_error, ModuleNotFoundError) and import_error.name == "pgvector":
        return _FallbackVectorType
    if import_error is not None:
        raise import_error
    raise RuntimeError("postgresql_vector_factory_missing_without_import_error")


def _register_vector_type_owner(
    registry: MutableMapping[str, object],
    selected_factory: type[UserDefinedType],
) -> type[UserDefinedType]:
    """Register one exact vector owner without replacing another owner."""

    existing = registry.get("vector")
    if existing is None:
        registry["vector"] = selected_factory
        return selected_factory
    if existing is selected_factory:
        return selected_factory
    raise RuntimeError("postgresql_vector_registry_owner_incompatible")


_vector_type_factory: type[UserDefinedType]
try:
    from pgvector.sqlalchemy import VECTOR as _InstalledVectorType
except ModuleNotFoundError as exc:  # pragma: no cover - optional base runtime profile
    _vector_type_factory = _select_vector_type_factory(None, exc)
else:
    _vector_type_factory = _select_vector_type_factory(_InstalledVectorType, None)

_vector_type_factory = _register_vector_type_owner(ischema_names, _vector_type_factory)


def _reject_embedding_constant(value: str) -> object:
    raise ValueError(f"vector_embedding_non_finite:{value}")


def _normalize_vector_values(value: object, *, dimensions: int) -> list[float]:
    """Return one exact finite vector or fail closed."""

    candidate = value
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate, parse_constant=_reject_embedding_constant)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("vector_embedding_invalid_json") from exc
    elif not isinstance(candidate, (list, tuple)):
        to_list = getattr(candidate, "tolist", None)
        if not callable(to_list):
            raise ValueError("vector_embedding_invalid_container")
        candidate = to_list()

    if not isinstance(candidate, (list, tuple)):
        raise ValueError("vector_embedding_invalid_container")
    if len(candidate) != dimensions:
        raise ValueError("vector_embedding_wrong_dimension")

    normalized: list[float] = []
    for item in candidate:
        if isinstance(item, bool) or not isinstance(item, Real):
            raise ValueError("vector_embedding_non_numeric")
        try:
            numeric = float(item)
        except (OverflowError, TypeError, ValueError) as exc:
            raise ValueError("vector_embedding_non_finite") from exc
        if not math.isfinite(numeric):
            raise ValueError("vector_embedding_non_finite")
        normalized.append(numeric)
    return normalized


class _VectorText(TypeDecorator[str]):
    """Keep the ORM string contract while binding VECTOR(768) on PostgreSQL."""

    impl = Text
    cache_ok = True
    dimensions = 768

    def __init__(
        self,
        vector_type_factory: type[UserDefinedType] = _vector_type_factory,
    ) -> None:
        super().__init__()
        self._selected_vector_type_factory = vector_type_factory

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[object]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(self._selected_vector_type_factory(self.dimensions))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: str | None, dialect: Dialect) -> object | None:
        if value is None:
            return None
        if dialect.name != "postgresql":
            if not isinstance(value, str):
                raise ValueError("vector_embedding_sqlite_value_must_be_text")
            return value
        if not isinstance(value, str):
            raise ValueError("vector_embedding_postgresql_value_must_be_text")
        normalized = _normalize_vector_values(value, dimensions=self.dimensions)
        if self._selected_vector_type_factory is _FallbackVectorType:
            return json.dumps(normalized, separators=(",", ":"))
        return normalized

    def process_result_value(self, value: object | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if dialect.name != "postgresql":
            if not isinstance(value, str):
                raise ValueError("vector_embedding_sqlite_result_must_be_text")
            return value
        normalized = _normalize_vector_values(value, dimensions=self.dimensions)
        return json.dumps(normalized, separators=(",", ":"))


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
        Index("idx_rag_feedback_user_id", "user_id"),
        Index("idx_rag_feedback_user_created", "user_id", "created_at"),
        Index(
            "idx_rag_feedback_agent",
            "agent_id",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
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
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Embedding vector for semantic search
    # On Postgres with pgvector: VECTOR(768) (after migration 202602280003)
    # On SQLite (tests): TEXT storing JSON array; app-level cosine in vector_rag.py
    # See: core/rag/vector_rag.py for dialect-aware retrieval
    embedding: Mapped[Optional[str]] = mapped_column(
        _VectorText(_vector_type_factory),
        nullable=True,
    )

    source: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

"""Internal DSAR helper services for direct-user artifacts.

RU: Внутренние DSAR-хелперы для support-led export/delete прямых user-bound артефактов.
EN: Internal DSAR helpers for support-led export/delete of direct user-bound artifacts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from core.db_rls import apply_user_rls_context

logger = logging.getLogger(__name__)


def _serialize_timestamp(value: datetime | None) -> str | None:
    """Return an ISO timestamp with explicit UTC fallback for naive datetimes."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.isoformat()


def export_direct_user_artifacts(*, session: Session, user_id: int) -> dict[str, object]:
    """Export direct-user SQL artifacts for internal support-led DSAR handling."""

    from app.models.rag_feedback import RAGFeedback, UserKnowledge
    from core.models import User

    apply_user_rls_context(session, user_id=user_id)
    user = session.get(User, user_id)
    feedback_rows = (
        session.execute(
            select(RAGFeedback).where(RAGFeedback.user_id == user_id).order_by(RAGFeedback.id.asc())
        )
        .scalars()
        .all()
    )
    knowledge_rows = (
        session.execute(
            select(UserKnowledge)
            .where(UserKnowledge.user_id == user_id)
            .order_by(UserKnowledge.id.asc())
        )
        .scalars()
        .all()
    )

    user_payload = None
    if user is not None:
        user_payload = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": _serialize_timestamp(user.created_at),
        }

    return {
        "user_id": user_id,
        "artifacts": {
            "account_user_record": user_payload,
            "rag_feedback": [
                {
                    "id": row.id,
                    "agent_id": row.agent_id,
                    "query": row.query,
                    "retrieved_chunks": row.retrieved_chunks,
                    "llm_response": row.llm_response,
                    "user_rating": row.user_rating,
                    "user_correction": row.user_correction,
                    "confidence": row.confidence,
                    "hops": row.hops,
                    "created_at": _serialize_timestamp(row.created_at),
                }
                for row in feedback_rows
            ],
            "user_knowledge": [
                {
                    "id": row.id,
                    "content": row.content,
                    "embedding": row.embedding,
                    "source": row.source,
                    "created_at": _serialize_timestamp(row.created_at),
                }
                for row in knowledge_rows
            ],
        },
        "artifact_counts": {
            "account_user_record": 1 if user_payload is not None else 0,
            "rag_feedback": len(feedback_rows),
            "user_knowledge": len(knowledge_rows),
        },
    }


def build_direct_user_deletion_plan(*, session: Session, user_id: int) -> dict[str, object]:
    """Return the bounded DSAR deletion plan for direct-user artifacts."""

    from app.models.rag_feedback import RAGFeedback, UserKnowledge
    from core.models import User

    apply_user_rls_context(session, user_id=user_id)
    user_exists = session.get(User, user_id) is not None
    feedback_count = session.execute(
        select(func.count()).select_from(RAGFeedback).where(RAGFeedback.user_id == user_id)
    ).scalar_one()
    knowledge_count = session.execute(
        select(func.count()).select_from(UserKnowledge).where(UserKnowledge.user_id == user_id)
    ).scalar_one()

    return {
        "user_id": user_id,
        "artifacts": {
            "account_user_record": {
                "present": user_exists,
                "helper_action": "manual_existing_user_delete_flow",
                "notes": "Account-row deletion stays on the dedicated user deletion path, not this helper.",
            },
            "rag_feedback": {
                "present_count": feedback_count,
                "helper_action": "delete_now",
            },
            "user_knowledge": {
                "present_count": knowledge_count,
                "helper_action": "delete_now",
            },
        },
    }


def delete_direct_user_artifacts(*, session: Session, user_id: int) -> dict[str, object]:
    """Delete bounded direct-user SQL artifacts for support-led DSAR handling."""

    from app.models.rag_feedback import RAGFeedback, UserKnowledge
    from core.models import User

    apply_user_rls_context(session, user_id=user_id)
    user_exists = session.get(User, user_id) is not None
    try:
        feedback_result = session.execute(
            delete(RAGFeedback).where(RAGFeedback.user_id == user_id).returning(RAGFeedback.id)
        )
        knowledge_result = session.execute(
            delete(UserKnowledge)
            .where(UserKnowledge.user_id == user_id)
            .returning(UserKnowledge.id)
        )
        feedback_deleted = len(feedback_result.scalars().all())
        knowledge_deleted = len(knowledge_result.scalars().all())
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("DSAR direct-user artifact delete failed")
        raise

    pending_manual_artifacts: list[str] = []
    if user_exists:
        pending_manual_artifacts.append("account_user_record")

    return {
        "user_id": user_id,
        "deleted": {
            "account_user_record": 0,
            "rag_feedback": feedback_deleted,
            "user_knowledge": knowledge_deleted,
        },
        "deleted_any": any((feedback_deleted, knowledge_deleted)),
        "pending_manual_artifacts": pending_manual_artifacts,
    }

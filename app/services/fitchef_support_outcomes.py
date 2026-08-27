"""Race-safe persistence for client-reported FitChef support outcomes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.fitchef_support_outcomes import FitChefSupportOutcomeEvent
from core.db import get_session_factory
from core.db_rls import apply_user_rls_context

logger = logging.getLogger(__name__)

FITCHEF_SUPPORT_OUTCOME_UNIQUE_CONSTRAINT = "uq_fitchef_support_outcome_subject_event"
FITCHEF_SUPPORT_OUTCOME_SQLITE_UNIQUE_SIGNATURE = (
    "UNIQUE constraint failed: "
    "fitchef_support_outcome_events.subject_id, "
    "fitchef_support_outcome_events.client_event_id"
)

FitChefSupportOutcomeWriteState = Literal["recorded", "replayed"]


class FitChefSupportOutcomeConflictError(RuntimeError):
    """The idempotency key is already bound to different closed material."""


class FitChefSupportOutcomeStoreUnavailableError(RuntimeError):
    """The outcome store could not safely complete the requested operation."""


@dataclass(frozen=True, slots=True)
class FitChefSupportOutcomeRecord:
    """Closed material admitted by the HTTP boundary."""

    schema_version: str
    support_need: str
    target_surface: str
    outcome: str
    client_event_id: str


def _closed_material(row: FitChefSupportOutcomeEvent) -> tuple[str, str, str, str]:
    return (
        row.schema_version,
        row.support_need,
        row.target_surface,
        row.outcome,
    )


def _record_material(record: FitChefSupportOutcomeRecord) -> tuple[str, str, str, str]:
    return (
        record.schema_version,
        record.support_need,
        record.target_surface,
        record.outcome,
    )


def _fetch_existing(
    session: Session,
    *,
    subject_id: int,
    client_event_id: str,
) -> FitChefSupportOutcomeEvent | None:
    statement = select(FitChefSupportOutcomeEvent).where(
        FitChefSupportOutcomeEvent.subject_id == subject_id,
        FitChefSupportOutcomeEvent.client_event_id == client_event_id,
    )
    row: FitChefSupportOutcomeEvent | None = session.execute(statement).scalar_one_or_none()
    return row


def _resolve_existing(
    existing: FitChefSupportOutcomeEvent,
    *,
    record: FitChefSupportOutcomeRecord,
) -> FitChefSupportOutcomeWriteState:
    if _closed_material(existing) == _record_material(record):
        return "replayed"
    raise FitChefSupportOutcomeConflictError


def _is_exact_idempotency_violation(error: IntegrityError) -> bool:
    """Recognize only the named Postgres constraint or exact SQLite signature."""

    original = getattr(error, "orig", None)
    diagnostic = getattr(original, "diag", None)
    if (
        diagnostic is not None
        and getattr(diagnostic, "constraint_name", None)
        == FITCHEF_SUPPORT_OUTCOME_UNIQUE_CONSTRAINT
    ):
        return True

    return (
        type(original).__module__ == "sqlite3"
        and type(original).__name__ == "IntegrityError"
        and str(original) == FITCHEF_SUPPORT_OUTCOME_SQLITE_UNIQUE_SIGNATURE
    )


def _store_unavailable() -> FitChefSupportOutcomeStoreUnavailableError:
    logger.error("FitChef support outcome store unavailable")
    return FitChefSupportOutcomeStoreUnavailableError()


def _rollback_session_safely(session: Session) -> bool:
    """Rollback without leaking or replacing the stable store boundary."""

    try:
        session.rollback()
    except Exception:
        logger.error("FitChef support outcome store rollback failed")
        return False
    return True


def record_fitchef_support_outcome(
    *,
    subject_id: int,
    record: FitChefSupportOutcomeRecord,
    session_factory: Callable[[], Session] | None = None,
) -> FitChefSupportOutcomeWriteState:
    """Insert once, replay identical material, and reject divergent reuse."""

    if subject_id <= 0:
        raise ValueError("subject_id must be a positive integer")

    session: Session | None = None
    try:
        resolved_factory = session_factory or get_session_factory()
        session = resolved_factory()
        apply_user_rls_context(session, user_id=subject_id)
        existing = _fetch_existing(
            session,
            subject_id=subject_id,
            client_event_id=record.client_event_id,
        )
        if existing is not None:
            return _resolve_existing(existing, record=record)

        session.add(
            FitChefSupportOutcomeEvent(
                id=str(uuid4()),
                subject_id=subject_id,
                schema_version=record.schema_version,
                support_need=record.support_need,
                target_surface=record.target_surface,
                outcome=record.outcome,
                client_event_id=record.client_event_id,
            )
        )
        session.commit()
        return "recorded"
    except FitChefSupportOutcomeConflictError:
        raise
    except IntegrityError as error:
        if session is None or not _rollback_session_safely(session):
            raise _store_unavailable() from None
        if not _is_exact_idempotency_violation(error):
            raise _store_unavailable() from None
        try:
            apply_user_rls_context(session, user_id=subject_id)
            winner = _fetch_existing(
                session,
                subject_id=subject_id,
                client_event_id=record.client_event_id,
            )
        except Exception:
            _rollback_session_safely(session)
            raise _store_unavailable() from None
        if winner is None:
            raise _store_unavailable() from None
        return _resolve_existing(winner, record=record)
    except Exception:
        if session is not None:
            _rollback_session_safely(session)
        raise _store_unavailable() from None
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                logger.error("FitChef support outcome store close failed")


__all__ = [
    "FITCHEF_SUPPORT_OUTCOME_SQLITE_UNIQUE_SIGNATURE",
    "FITCHEF_SUPPORT_OUTCOME_UNIQUE_CONSTRAINT",
    "FitChefSupportOutcomeConflictError",
    "FitChefSupportOutcomeRecord",
    "FitChefSupportOutcomeStoreUnavailableError",
    "FitChefSupportOutcomeWriteState",
    "record_fitchef_support_outcome",
]

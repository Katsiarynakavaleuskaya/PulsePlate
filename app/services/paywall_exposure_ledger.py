"""Paywall exposure ledger service.

RU: Узкий append-only сервис для paywall instrumentation и server-authored upgrade events.
EN: Narrow append-only service for paywall instrumentation and server-authored upgrade events.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.paywall_analytics import PaywallExposureLedger
from app.schemas.paywall_analytics import PaywallExposureEventName
from core.db import get_session_factory
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.payments_activation import NormalizedActivation

_SERVER_ACTIVATION_TRIGGER_REASON = "activation_flow"


@dataclass(frozen=True)
class PaywallExposureAuthContext:
    """Optional authenticated context attached to a ledger event."""

    subject_id: int | None = None
    auth_source: str | None = None
    tier_snapshot: str | None = None


@dataclass(frozen=True)
class PaywallExposureRecordInput:
    """Normalized ledger record input."""

    client_event_id: str
    exposure_id: str
    event_name: PaywallExposureEventName
    source_surface: str
    trigger_reason: str
    via: str | None = None
    metadata: dict[str, Any] | None = None


def _utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _get_existing_by_client_event_id(
    session: Session,
    *,
    client_event_id: str,
) -> PaywallExposureLedger | None:
    """Return existing ledger row for deterministic idempotency."""

    statement = select(PaywallExposureLedger).where(
        PaywallExposureLedger.client_event_id == client_event_id,
    )
    row: PaywallExposureLedger | None = session.execute(statement).scalar_one_or_none()
    return row


def _detach_row(session: Session, row: PaywallExposureLedger) -> PaywallExposureLedger:
    """Detach ORM row so callers can inspect it after session close."""

    session.expunge(row)
    return row


def record_paywall_exposure_event(
    *,
    record: PaywallExposureRecordInput,
    auth_context: PaywallExposureAuthContext | None = None,
) -> tuple[PaywallExposureLedger, bool]:
    """Persist one paywall ledger event with client_event_id idempotency."""

    resolved_auth = auth_context or PaywallExposureAuthContext()
    session_factory = get_session_factory()
    session = session_factory()
    try:
        existing = _get_existing_by_client_event_id(
            session,
            client_event_id=record.client_event_id,
        )
        if existing is not None:
            return _detach_row(session, existing), False

        row = PaywallExposureLedger(
            id=str(uuid4()),
            created_at=_utc_now(),
            event_name=record.event_name.value,
            source_surface=record.source_surface,
            trigger_reason=record.trigger_reason,
            via=record.via,
            exposure_id=record.exposure_id,
            client_event_id=record.client_event_id,
            subject_id=resolved_auth.subject_id,
            auth_source=resolved_auth.auth_source,
            tier_snapshot=resolved_auth.tier_snapshot,
            metadata_json=record.metadata,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _detach_row(session, row), True
    except IntegrityError:
        session.rollback()
        existing = _get_existing_by_client_event_id(
            session,
            client_event_id=record.client_event_id,
        )
        if existing is not None:
            return _detach_row(session, existing), False
        raise
    finally:
        session.close()


def _stable_server_event_id(*, idempotency_key: str, event_name: PaywallExposureEventName) -> str:
    """Build bounded deterministic ids for server-authored activation events."""

    payload = f"{idempotency_key}:{event_name.value}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:32]
    return f"activation_{event_name.value}_{digest}"


def _stable_activation_exposure_id(*, idempotency_key: str) -> str:
    """Build bounded deterministic activation lineage id."""

    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:32]
    return f"activation_{digest}"


def _activation_metadata(
    *,
    normalized: NormalizedActivation,
) -> dict[str, Any]:
    """Build minimal, non-sensitive activation metadata for ledger rows."""

    return {
        "payment_source": normalized.source.value,
        "subscription_tier": normalized.tier.value,
        "subscription_status": normalized.status.value,
        "platform": normalized.platform.value,
        "source_reference": normalized.source_reference,
        "product_id": normalized.product_id,
        "external_txn_id": normalized.external_txn_id,
        "reconcile_status": normalized.reconcile_status.value,
        "requested_plan": normalized.requested_plan.value if normalized.requested_plan else None,
    }


def record_activation_lifecycle_event(
    *,
    event_name: PaywallExposureEventName,
    normalized: NormalizedActivation,
    subject_id: int,
) -> tuple[PaywallExposureLedger, bool]:
    """Persist server-authored activation lifecycle events deterministically."""

    record = PaywallExposureRecordInput(
        client_event_id=_stable_server_event_id(
            idempotency_key=normalized.idempotency_key,
            event_name=event_name,
        ),
        exposure_id=_stable_activation_exposure_id(idempotency_key=normalized.idempotency_key),
        event_name=event_name,
        source_surface=normalized.source.value,
        trigger_reason=_SERVER_ACTIVATION_TRIGGER_REASON,
        via=normalized.platform.value,
        metadata=_activation_metadata(normalized=normalized),
    )
    auth_context = PaywallExposureAuthContext(
        subject_id=subject_id,
        auth_source="server",
        tier_snapshot=normalized.tier.value.upper(),
    )
    return record_paywall_exposure_event(record=record, auth_context=auth_context)

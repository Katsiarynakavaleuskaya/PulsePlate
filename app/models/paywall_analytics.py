"""Paywall exposure ledger models.

RU: Durable ledger для paywall exposure / upgrade lifecycle instrumentation.
EN: Durable ledger for paywall exposure / upgrade lifecycle instrumentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class PaywallExposureLedger(Base):
    """Append-only paywall instrumentation ledger row."""

    __tablename__ = "paywall_exposure_ledger"
    __table_args__ = (
        UniqueConstraint(
            "client_event_id",
            name="uq_paywall_exposure_ledger_client_event_id",
        ),
        Index("ix_paywall_exposure_ledger_event_name_created_at", "event_name", "created_at"),
        Index(
            "ix_paywall_exposure_ledger_source_surface_created_at",
            "source_surface",
            "created_at",
        ),
        Index(
            "ix_paywall_exposure_ledger_trigger_reason_created_at",
            "trigger_reason",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    event_name: Mapped[str] = mapped_column(String(32), nullable=False)
    source_surface: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    via: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exposure_id: Mapped[str] = mapped_column(String(128), nullable=False)
    client_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    auth_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tier_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
        nullable=True,
    )

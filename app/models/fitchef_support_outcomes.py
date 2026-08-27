"""Append-only FitChef support-outcome ledger model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class FitChefSupportOutcomeEvent(Base):
    """Credential-subject-scoped client-reported support outcome."""

    __tablename__ = "fitchef_support_outcome_events"
    __table_args__ = (
        UniqueConstraint(
            "subject_id",
            "client_event_id",
            name="uq_fitchef_support_outcome_subject_event",
        ),
        Index(
            "ix_fitchef_support_outcomes_subject_created_at",
            "subject_id",
            "created_at",
        ),
        CheckConstraint(
            "schema_version = 'fitchef_support_outcome_v1'",
            name="ck_fitchef_support_outcome_schema_version",
        ),
        CheckConstraint(
            "support_need IN ('daily_structure', 'weekly_structure')",
            name="ck_fitchef_support_outcome_support_need",
        ),
        CheckConstraint(
            "target_surface IN ('pro_daily_plate', 'pro_weekly_plan')",
            name="ck_fitchef_support_outcome_target_surface",
        ),
        CheckConstraint(
            "outcome IN ('acknowledged', 'dismissed')",
            name="ck_fitchef_support_outcome_outcome",
        ),
        CheckConstraint(
            "((support_need = 'daily_structure' AND target_surface = 'pro_daily_plate') "
            "OR (support_need = 'weekly_structure' AND target_surface = 'pro_weekly_plan'))",
            name="ck_fitchef_support_outcome_compatible_pair",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    support_need: Mapped[str] = mapped_column(String(32), nullable=False)
    target_surface: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    client_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

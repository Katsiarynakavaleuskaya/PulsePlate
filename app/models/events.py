"""Event models for nutrition logging and day finalization.

RU: Модели событий для логирования питания и финализации дней.
EN: Event models for nutrition logging and day finalization with idempotency.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.db import Base


class NutritionEvent(Base):
    """Append-only event log for nutrition tracking.

    RU: Журнал событий питания с поддержкой идемпотентности.
    EN: Nutrition event log with idempotency support via client_event_id.

    Events from meal-log and day-close are normalized into this canonical envelope.
    Day-close is the sole canonical trigger for adherence finalization.
    """

    __tablename__ = "nutrition_events"
    __table_args__ = (
        # Idempotency: same client_event_id from same subject+source = duplicate
        UniqueConstraint(
            "subject_id",
            "source",
            "client_event_id",
            name="uq_nutrition_events_idempotency",
            # NOTE: SQLite doesn't support partial unique indexes, so this constraint
            # applies even when client_event_id is NULL. For proper idempotency,
            # clients MUST provide client_event_id.
        ),
        Index("ix_nutrition_events_subject_day", "subject_id", "day"),
        Index("ix_nutrition_events_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # 'meal_log' | 'day_close'
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'meal_logged' | 'day_closed'
    client_event_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(
        postgresql.JSONB(astext_type=String()).with_variant(String(), "sqlite"),
        nullable=False,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

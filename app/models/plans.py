"""SQLAlchemy models for weekly and day plans."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.db import Base


class WeeklyPlan(Base):
    """Weekly meal plan storage.

    RU: Хранение недельных планов питания.
    EN: Storage for weekly meal plans.
    """

    __tablename__ = "weekly_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    plan_data: Mapped[Dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    day_plans: Mapped[list["DayPlan"]] = relationship(
        "DayPlan", back_populates="weekly_plan", cascade="all, delete-orphan"
    )

    __table_args__ = (CheckConstraint("start_date <= end_date", name="ck_weekly_plan_date_order"),)


class DayPlan(Base):
    """Day meal plan storage.

    RU: Хранение дневных планов питания.
    EN: Storage for daily meal plans.
    """

    __tablename__ = "day_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekly_plan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=True, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plan_data: Mapped[Dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    weekly_plan: Mapped["WeeklyPlan | None"] = relationship(
        "WeeklyPlan", back_populates="day_plans"
    )

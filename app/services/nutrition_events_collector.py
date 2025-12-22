"""Nutrition events collector for day-close finalization.

RU: Коллектор событий питания для финализации дня.
EN: Collects nutrition events for a given subject+day to support adherence finalization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.events import NutritionEvent


@dataclass
class CollectedDayEvents:
    """Aggregated events for a single day.

    RU: Агрегированные события за один день.
    EN: Summary of nutrition events for adherence finalization.
    """

    meals_logged_count: int
    has_day_closed: bool


def collect_day_events(session: Session, subject_id: int, day: date) -> CollectedDayEvents:
    """Collect and aggregate nutrition events for a specific subject and day.

    RU: Собрать и агрегировать события питания для пользователя и дня.
    EN: Aggregate nutrition events to determine day closure status and meal counts.

    Args:
        session: Database session
        subject_id: User ID from authentication
        day: Target date to collect events for

    Returns:
        CollectedDayEvents with meal count and closure status
    """
    # Count meal_logged events
    meals_logged_count = (
        session.scalar(
            select(func.count())
            .select_from(NutritionEvent)
            .where(
                NutritionEvent.subject_id == subject_id,
                NutritionEvent.day == day,
                NutritionEvent.event_type == "meal_logged",
            )
        )
        or 0
    )

    # Check if day has been closed
    has_day_closed = (
        session.scalar(
            select(func.count())
            .select_from(NutritionEvent)
            .where(
                NutritionEvent.subject_id == subject_id,
                NutritionEvent.day == day,
                NutritionEvent.event_type == "day_closed",
            )
        )
        > 0
    )

    return CollectedDayEvents(
        meals_logged_count=int(meals_logged_count),
        has_day_closed=bool(has_day_closed),
    )

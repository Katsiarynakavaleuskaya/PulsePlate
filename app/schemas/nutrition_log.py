"""Schemas for meal/day logging endpoints.

RU: Схемы для эндпоинтов логирования приёмов пищи и закрытия дня.
EN: Schemas for meal/day logging endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


MealType = Literal["breakfast", "lunch", "dinner", "snack"]
MealLogType = Literal["meal_logged", "slip", "partial"]


class MealLogRequest(BaseModel):
    """Log a meal-related event.

    RU: Логировать событие приёма пищи.
    EN: Log a meal event.
    """

    occurred_at: Optional[datetime] = None
    meal_type: Optional[MealType] = None
    log_type: MealLogType = "meal_logged"
    adherence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class DayCloseRequest(BaseModel):
    """Close a day with an adherence score.

    RU: Закрыть день с оценкой выполнения.
    EN: Close day with adherence score.
    """

    day: date
    adherence_score: float = Field(..., ge=0.0, le=1.0)

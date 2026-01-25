"""Schemas for meal/day logging endpoints.

RU: Схемы для эндпоинтов логирования приёмов пищи и закрытия дня.
EN: Schemas for meal/day logging endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# NOTE: This API exposes a simplified MealType subset for LOG0 MVP.
# core.meal_types.MealType contains additional snack variants (second_snack, etc.)
# that are not yet supported at the API boundary.
MealType = Literal["breakfast", "lunch", "dinner", "snack"]
MealLogType = Literal["meal_logged", "slip", "partial"]


class MealLogRequest(BaseModel):
    """Log a meal-related event.

    RU: Логировать событие приёма пищи.
    EN: Log a meal event.
    """

    # Note: occurred_at and meal_type are accepted for forward compatibility but
    # are not used in current adherence scoring.
    occurred_at: Optional[datetime] = None
    meal_type: Optional[MealType] = None
    log_type: MealLogType = "meal_logged"
    adherence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    client_event_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Client-provided idempotency key (recommended for mobile retries)",
    )

    @model_validator(mode="after")
    def _validate_partial_requires_score(self) -> "MealLogRequest":
        """Ensure adherence_score is provided when log_type='partial'.

        RU: Для log_type='partial' adherence_score обязателен.
        EN: For log_type='partial', adherence_score is required.
        """
        if self.log_type == "partial" and self.adherence_score is None:
            raise ValueError("adherence_score is required when log_type='partial'")
        return self


class DayCloseRequest(BaseModel):
    """Close a day with an adherence score.

    RU: Закрыть день с оценкой выполнения.
    EN: Close day with adherence score.
    """

    day: date
    adherence_score: float = Field(..., ge=0.0, le=1.0)

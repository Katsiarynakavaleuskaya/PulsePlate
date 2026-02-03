"""Nutrition target schemas (Pydantic).

RU: Pydantic-схемы для nutrition targets (без ORM / SQLAlchemy).
EN: Pydantic schemas for nutrition targets (no ORM / SQLAlchemy).

IMPORTANT:
- This module must stay import-safe (no SQLAlchemy, no Base/metadata side-effects).
- Routers may import these schemas at module import time (OpenAPI generation path).
"""

from __future__ import annotations

import math
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


def _validate_numeric_dict(v: Dict[str, float], field_name: str) -> Dict[str, float]:
    """Shared numeric-dict validator.

    RU: Общая проверка словаря чисел >= 0 и finite.
    EN: Shared validator for numeric dict values (finite, >= 0).
    """

    for key, val in v.items():
        # bool is subclass of int -> exclude explicitly
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"{field_name}[{key}] must be a finite number >= 0")
        val_f = float(val)
        if not math.isfinite(val_f) or val_f < 0:
            raise ValueError(f"{field_name}[{key}] must be a finite number >= 0")
    return v


class TargetsIn(BaseModel):
    """Nutrition targets input model.

    RU: Входная схема таргетов питания (используется в PRO/Premium эндпоинтах).
    EN: Input schema for nutrition targets (used by PRO/Premium endpoints).
    """

    kcal: int = Field(..., gt=500, lt=6000)
    macros: Dict[str, float]
    micro: Dict[str, float]
    water_ml: int = Field(0, ge=0)
    activity_week: Optional[Dict[str, int]] = None

    @field_validator("macros")
    @classmethod
    def _validate_macros(cls, v: Dict[str, float]) -> Dict[str, float]:
        return _validate_numeric_dict(v, "macros")

    @field_validator("micro")
    @classmethod
    def _validate_micro(cls, v: Dict[str, float]) -> Dict[str, float]:
        return _validate_numeric_dict(v, "micro")

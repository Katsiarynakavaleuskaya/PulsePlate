"""Nutrition target schemas (Pydantic).

RU: Pydantic-схемы для nutrition targets (без ORM / SQLAlchemy).
EN: Pydantic schemas for nutrition targets (no ORM / SQLAlchemy).

IMPORTANT:
- This module must stay import-safe (no SQLAlchemy, no Base/metadata side-effects).
- Routers may import these schemas at module import time (OpenAPI generation path).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


def _validate_numeric_dict(v: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    """RU: Проверка словаря чисел (finite, >=0), bool запрещён.
    EN: Validate numeric dict values (finite, >=0), bool is forbidden.
    """

    for key, val in v.items():
        # bool is a subclass of int -> must reject explicitly (before Pydantic coercion).
        if isinstance(val, bool):
            raise ValueError(f"{field_name}[{key}] must be a finite number >= 0")
        try:
            num = float(val)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name}[{key}] must be a finite number >= 0") from None
        if not math.isfinite(num) or num < 0:
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

    @field_validator("macros", mode="before")
    @classmethod
    def _validate_macros(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return _validate_numeric_dict(v, "macros")

    @field_validator("micro", mode="before")
    @classmethod
    def _validate_micro(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return _validate_numeric_dict(v, "micro")

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
        """Validate macros are finite numbers >= 0.

        RU: Проверяем, что macros содержат конечные числа >= 0.
        EN: Ensure macros contain finite numbers >= 0.
        """

        for key, val in v.items():
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"macros[{key}] must be a finite number >= 0")

            if not math.isfinite(val) or val < 0:
                raise ValueError(f"macros[{key}] must be a finite number >= 0")
        return v

    @field_validator("micro")
    @classmethod
    def _validate_micro(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate micros are finite numbers >= 0.

        RU: Проверяем, что micro содержат конечные числа >= 0.
        EN: Ensure micro contains finite numbers >= 0.
        """

        for key, val in v.items():
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"micro[{key}] must be a finite number >= 0")

            if not math.isfinite(val) or val < 0:
                raise ValueError(f"micro[{key}] must be a finite number >= 0")
        return v

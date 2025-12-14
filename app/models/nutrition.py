"""Shared nutrition models for PRO and Premium routers."""

import math
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class TargetsIn(BaseModel):
    """Nutrition targets input model.

    Used by both PRO and Premium tier endpoints for nutrition target validation.
    """

    kcal: int = Field(..., gt=500, lt=6000)
    macros: Dict[str, float]
    micro: Dict[str, float]
    water_ml: int = Field(0, ge=0)
    activity_week: Optional[Dict[str, int]] = None

    @field_validator("macros")
    @classmethod
    def _validate_macros(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate macros are finite numbers >= 0."""
        for key, val in v.items():
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"macros[{key}] must be a finite number >= 0")

            if not math.isfinite(val) or val < 0:
                raise ValueError(f"macros[{key}] must be a finite number >= 0")
        return v

    @field_validator("micro")
    @classmethod
    def _validate_micro(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate micros are finite numbers >= 0."""
        for key, val in v.items():
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"micro[{key}] must be a finite number >= 0")

            if not math.isfinite(val) or val < 0:
                raise ValueError(f"micro[{key}] must be a finite number >= 0")
        return v

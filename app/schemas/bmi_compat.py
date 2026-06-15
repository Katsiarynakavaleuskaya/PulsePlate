"""Legacy BMI compatibility request schemas.

These models preserve historical `/bmi`, `/plan`, and `/api/v1/bmi` input
normalization while route ownership moves out of ``legacy_app.py``.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field, StrictFloat, model_validator

from core.bmi.engine import _DEFAULT_YES_VALUES as _CANONICAL_YES_VALUES_BASE
from core.i18n import Language

_YES_VALUES_BASE: set[str] = set(_CANONICAL_YES_VALUES_BASE)
_YES_VALUES_PREGNANT: set[str] = _YES_VALUES_BASE | {"pregnant", "беременна", "беременная"}
_YES_VALUES_ATHLETE: set[str] = _YES_VALUES_BASE | {"спортсмен", "athlete"}


class BMIRequest(BaseModel):
    weight_kg: float = Field(..., gt=0)
    height_m: float = Field(..., gt=0)
    age: int = Field(30, ge=0, le=120)
    gender: str = "male"
    pregnant: Union[str, bool] = "no"
    athlete: Union[str, bool] = "no"
    waist_cm: Optional[float] = Field(None, gt=0)
    lang: Language = "ru"
    premium: Optional[bool] = False
    include_chart: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def _normalize_values(
        cls, values: dict[str, Any] | "BMIRequest"
    ) -> dict[str, Any] | "BMIRequest":  # sourcery skip: use-contextlib-suppress
        if not isinstance(values, dict):
            return values
        if "weight_kg" not in values and "weight" in values:
            try:
                values["weight_kg"] = float(values["weight"])
            except (TypeError, ValueError):
                pass
        if "height_m" not in values:
            raw_height = values.get("height_m") or values.get("height") or values.get("height_cm")
            if raw_height is not None:
                try:
                    height_val = float(raw_height)
                except (TypeError, ValueError):
                    height_val = None
                if height_val is not None:
                    values["height_m"] = height_val / 100.0 if height_val > 10 else height_val
        if "gender" not in values and "sex" in values:
            values["gender"] = values["sex"]

        gender_value = values.get("gender")
        if isinstance(gender_value, str):
            normalized = gender_value.strip().lower()
            mapping = {
                "male": "male",
                "муж": "male",
                "м": "male",
                "hombre": "male",
                "m": "male",
                "man": "male",
                "female": "female",
                "жен": "female",
                "ж": "female",
                "mujer": "female",
                "f": "female",
                "woman": "female",
            }
            values["gender"] = mapping.get(normalized, normalized)

        pregnant_value = values.get("pregnant")
        if isinstance(pregnant_value, str):
            values["pregnant"] = pregnant_value.strip().lower() in _YES_VALUES_PREGNANT

        athlete_value = values.get("athlete")
        if isinstance(athlete_value, str):
            values["athlete"] = athlete_value.strip().lower() in _YES_VALUES_ATHLETE

        if "with_visualization" in values:
            raw_visualization = values.get("with_visualization")
            include_chart = False
            if isinstance(raw_visualization, str):
                normalized_visualization = raw_visualization.strip().lower()
                if normalized_visualization in {"yes", "y", "да", "si", "sí", "true", "1", "on"}:
                    include_chart = True
                elif normalized_visualization in {"no", "n", "нет", "false", "0", "off"}:
                    include_chart = False
                else:
                    include_chart = bool(normalized_visualization)
            else:
                include_chart = bool(raw_visualization)
            values["include_chart"] = include_chart
        return values

    @model_validator(mode="after")
    def _validate_gender(self) -> "BMIRequest":
        if self.gender not in {"male", "female", "unknown"}:
            raise ValueError("gender must be 'male', 'female', or 'unknown'")
        return self

    @model_validator(mode="after")
    def validate_realistic_values(self) -> "BMIRequest":
        from core.bmi.engine import _compute_bmi

        bmi = _compute_bmi(weight_kg=self.weight_kg, height_m=self.height_m)

        if bmi < 10.0:
            raise ValueError("Weight is unrealistically low for the given height")
        if bmi > 100.0:
            raise ValueError(f"Weight is unrealistically high for the given height (BMI={bmi:.1f})")

        return self


class BMIRequestV1(BaseModel):
    weight_kg: StrictFloat = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    group: str = "general"
    age: int = Field(default=30, ge=0, le=120)
    gender: str = "male"
    pregnant: Union[str, bool] = "no"
    athlete: Union[str, bool] = "no"
    waist_cm: Optional[float] = Field(None, gt=0)
    lang: Language = "en"

    @model_validator(mode="after")
    def validate_realistic_values(self) -> "BMIRequestV1":
        from core.bmi.engine import _compute_bmi

        height_m = self.height_cm / 100.0
        bmi = _compute_bmi(weight_kg=self.weight_kg, height_m=height_m)

        if bmi < 10.0:
            raise ValueError("Weight is unrealistically low for the given height")
        if bmi > 100.0:
            raise ValueError("Weight is unrealistically high for the given height")

        return self

    @model_validator(mode="before")
    @classmethod
    def _normalize_values(
        cls, values: dict[str, Any] | "BMIRequestV1"
    ) -> dict[str, Any] | "BMIRequestV1":
        if not isinstance(values, dict):
            return values

        for key in ["gender", "pregnant", "athlete", "lang"]:
            if key in values and isinstance(values[key], str):
                values[key] = values[key].strip().lower()
        return values

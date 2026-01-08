# -*- coding: utf-8 -*-
"""
BMI Schemas

RU: Схемы для расчета BMI через единый engine.
EN: Schemas for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

import math
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.i18n import Language

RiskLevel = Literal["low", "moderate", "high"]


class BMIRangeSpec(BaseModel):
    """BMI range with i18n key."""

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(..., description="i18n key for range label")
    from_: float = Field(..., alias="from", description="Range start (inclusive)")
    to: float = Field(..., description="Range end (exclusive)")

    @model_validator(mode="after")
    def validate_range(self) -> "BMIRangeSpec":
        if self.from_ >= self.to:
            raise ValueError(f"Range start ({self.from_}) must be less than end ({self.to})")
        return self


class BMIMarkerSpec(BaseModel):
    """BMI marker position."""

    value: float = Field(..., description="Current BMI value", examples=[23.4, 25.0, 18.5])


class BMIScaleV1Spec(BaseModel):
    """BMI scale visualization spec v1."""

    kind: Literal["bmi_scale_v1"] = "bmi_scale_v1"
    bmi: float = Field(..., description="BMI value", examples=[23.4, 25.0, 18.5])
    min: float = Field(0.0, description="Scale minimum", examples=[0.0])
    max: float = Field(60.0, description="Scale maximum", examples=[60.0])
    ranges: list[BMIRangeSpec] = Field(
        ...,
        description="BMI ranges with i18n keys",
        examples=[
            [
                {"key": "bmi.underweight", "from": 0, "to": 18.5},
                {"key": "bmi.normal", "from": 18.5, "to": 25},
                {"key": "bmi.overweight", "from": 25, "to": 30},
                {"key": "bmi.obesity", "from": 30, "to": 60},
            ]
        ],
    )
    marker: BMIMarkerSpec = Field(..., description="Current BMI marker", examples=[{"value": 23.4}])

    @model_validator(mode="after")
    def validate_scale(self) -> "BMIScaleV1Spec":
        """Validate scale constraints and consistency."""
        # Ensure min < max
        if self.min >= self.max:
            raise ValueError(f"Scale minimum ({self.min}) must be less than maximum ({self.max})")

        # Ensure bmi is within scale bounds
        if not (self.min <= self.bmi <= self.max):
            raise ValueError(
                f"BMI value ({self.bmi}) must be between min ({self.min}) and max ({self.max})"
            )

        # Ensure marker.value equals bmi (consistency check)
        # Use math.isclose to handle float precision artifacts
        if not math.isclose(self.marker.value, self.bmi, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError(f"Marker value ({self.marker.value}) must equal BMI ({self.bmi})")

        return self


class WaistRiskResultSchema(BaseModel):
    """
    RU: API-схема для сериализованного WaistRiskResult (domain dataclass).
    EN: API schema for serialized WaistRiskResult (domain dataclass).
    """

    wht_ratio: float | None = Field(
        None,
        description="Waist-to-Height Ratio (WHtR) used for this assessment, if available.",
        examples=[0.47, 0.52, None],
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Waist-related risk level derived from the WHtR.",
        examples=["moderate"],
    )
    notes: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Additional notes providing context for the waist risk assessment.",
        examples=[("Increased waist-related risk",)],
    )


# --- Local normalization helpers (schema-level, MUST NOT import core.bmi.engine) ---
# These helpers ensure schema validation aligns with engine normalization semantics
# without creating import cycles.

_MALE_EXACT: Final[set[str]] = {"male", "m", "man", "м"}
_FEMALE_EXACT: Final[set[str]] = {"female", "f", "woman", "w", "ж"}

# Keep prefixes aligned with engine semantics: "starts with" for common language stems
_MALE_PREFIXES: Final[tuple[str, ...]] = ("муж", "hombre")
_FEMALE_PREFIXES: Final[tuple[str, ...]] = ("жен", "mujer")

_TRUE_STRINGS: Final[set[str]] = {"yes", "y", "true", "1", "да", "д", "истина", "si", "sí"}
_FALSE_STRINGS: Final[set[str]] = {"no", "n", "false", "0", "нет", "н", "ложь"}


def _normalize_ws_lower(s: str | None) -> str:
    """Normalize string: trim whitespace and convert to lowercase."""
    return (s or "").strip().lower()


def _is_male_gender_token(gender: str | None) -> bool:
    """
    RU: Определяет, является ли gender токен мужским (для инвариантов).
    EN: Determines if gender token is male (for invariants).

    Matches engine's _normalize_gender() prefix-based logic.
    """
    g = _normalize_ws_lower(gender)
    if not g:
        return False
    return (g in _MALE_EXACT) or any(g.startswith(prefix) for prefix in _MALE_PREFIXES)


def _is_female_gender_token(gender: str | None) -> bool:
    """
    RU: Определяет, является ли gender токен женским (для инвариантов).
    EN: Determines if gender token is female (for invariants).

    Matches engine's _normalize_gender() prefix-based logic.
    """
    g = _normalize_ws_lower(gender)
    if not g:
        return False
    return (g in _FEMALE_EXACT) or any(g.startswith(prefix) for prefix in _FEMALE_PREFIXES)


def _normalize_bool_flag_local(v: str | bool | None) -> bool:
    """
    Local boolean normalization for schema validation only.

    RU: Локальная нормализация boolean для валидации схемы.
    EN: Local boolean normalization for schema validation.

    Goal: match engine's user-facing behavior enough to enforce hard invariants.
    Unknown tokens are treated as False (safe default for invariant checks).

    Args:
        v: String, bool, or None

    Returns:
        bool: True if v is truthy (bool True or recognized truthy string), False otherwise
    """
    if isinstance(v, bool):
        return v
    s = _normalize_ws_lower(v if isinstance(v, str) else None)
    if not s:
        return False
    if s in _TRUE_STRINGS:
        return True
    if s in _FALSE_STRINGS:
        return False
    # Unknown token -> treat as False (safe default for invariant checks)
    return False


class BMICalculateRequest(BaseModel):
    """
    RU: Запрос для расчета BMI через единый engine.
    EN: Request for BMI calculation via unified engine.

    FREE tier endpoint (no API key required).
    """

    weight_kg: float = Field(
        ...,
        gt=0,
        description="Weight in kilograms. Must be positive.",
        examples=[65.5, 70.0, 80.3],
    )

    height_cm: float = Field(
        ...,
        gt=0,
        description="Height in centimeters. Must be positive.",
        examples=[170.0, 175.5, 180.0],
    )

    age: int = Field(
        ...,
        ge=1,
        le=120,
        description="Age in years. Range: 1-120.",
        examples=[25, 30, 45, 65],
    )

    gender: str = Field(
        default="male",
        description="Gender: 'male' or 'female'. Will be normalized by engine.",
        examples=["male", "female", "муж", "жен"],
    )

    pregnant: str | bool = Field(
        default="no",
        description=(
            "Pregnancy status. Accepts: 'yes'/'no' (string) or True/False (bool). "
            "Will be normalized to bool by engine."
        ),
        examples=["no", "yes", False, True],
    )

    athlete: str | bool = Field(
        default="no",
        description=(
            "Athlete status. Accepts: 'yes'/'no' (string) or True/False (bool). "
            "Will be normalized to bool by engine."
        ),
        examples=["no", "yes", False, True],
    )

    waist_cm: float | None = Field(
        None,
        gt=0,
        description=(
            "Waist circumference in centimeters (optional). "
            "If provided, enables WHtR and waist risk assessment."
        ),
        examples=[80.0, 90.5, None],
    )

    lang: Language = Field(
        default="en",
        description="Language for localized responses: 'ru', 'en', or 'es'.",
        examples=["en", "ru", "es"],
    )

    @model_validator(mode="after")
    def validate_gender_pregnant(self) -> "BMICalculateRequest":
        """
        RU: Валидация: мужчина не может быть беременным (жёсткий инвариант).
        EN: Validation: males cannot be pregnant (hard invariant).

        Gender normalization matches engine's _normalize_gender() logic:
        - Exact matches: "male", "m", "man", "м"
        - Prefix-based: "муж*" (RU), "hombre*" (ES) - matches engine's startswith()

        Raises:
            ValueError: If gender is male and pregnant is True
        """
        pregnant_bool = _normalize_bool_flag_local(self.pregnant)

        # We intentionally use "male detection" rather than "female detection":
        # If the token looks male (including prefixes), pregnancy must be rejected.
        if _is_male_gender_token(self.gender) and pregnant_bool:
            raise ValueError("Pregnancy is only applicable to females")

        return self


class NumericRangeSchema(BaseModel):
    """Numeric BMI target range schema."""

    min: float = Field(..., description="Range minimum (inclusive)", examples=[18.5])
    max: float = Field(..., description="Range maximum (inclusive)", examples=[25.0])

    @model_validator(mode="after")
    def validate_range(self) -> "NumericRangeSchema":
        """
        RU: Валидация: min должен быть меньше или равен max.
        EN: Validation: min must be less than or equal to max.
        """
        if self.min > self.max:
            raise ValueError(
                f"Range minimum ({self.min}) must be less than or equal to maximum ({self.max})"
            )
        return self


# TargetRangeSchema: Union of NumericRangeSchema or qualitative string
# We use a type alias for clarity, but Pydantic will handle Union validation
TargetRangeSchema = NumericRangeSchema | Literal["age_appropriate_growth", "prenatal_guidelines"]


class BMIInterpretationV1Schema(BaseModel):
    """
    BMI Interpretation v1 schema (i18n keys only).

    RU: Схема интерпретации BMI v1 (только i18n ключи).
    EN: BMI interpretation v1 schema (i18n keys only).
    """

    goal_direction: Literal["maintain", "reduce", "increase", "medical_review"] = Field(
        ...,
        description="Goal direction for BMI management.",
        examples=["maintain"],
    )

    target_range: (
        NumericRangeSchema | Literal["age_appropriate_growth", "prenatal_guidelines"] | None
    ) = Field(
        None,
        description="Target range (numeric or qualitative). None for medical_review cases.",
        examples=[{"min": 18.5, "max": 25.0}, "age_appropriate_growth", None],
    )

    risk_flags: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Risk flags (i18n keys only).",
        examples=[("bmi.interpretation.risk.extreme_value",)],
    )

    priority_notes: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Priority notes (i18n keys only).",
        examples=[("bmi.interpretation.priority.stability_first",)],
    )

    disclaimers: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Disclaimers (i18n keys only).",
        examples=[("bmi.interpretation.disclaimer.general",)],
    )


class BMICalculateResponse(BaseModel):
    """
    RU: Ответ с результатами расчета BMI через единый engine.
    EN: Response with BMI calculation results via unified engine.

    Note: `category` может быть `None` для беременных и детей/подростков
    (это не ошибка, а медицинский дисклеймер).
    """

    bmi: float = Field(
        ...,
        description="Calculated BMI value (weight_kg / (height_m ** 2)).",
        examples=[22.5, 25.3, 18.7],
    )

    category: str | None = Field(
        None,
        description=(
            "BMI category (localized). "
            "None for users in 'pregnant', 'too_young', 'child' or 'teen' age bands "
            "- not an error, medical disclaimer. "
            "BMI categories are not provided during pregnancy or for users in "
            "'too_young', 'child' and 'teen' age bands."
        ),
        examples=["normal", "overweight", None],
    )

    group: str = Field(
        ...,
        description=(
            "User group determined by auto_group(): "
            "'general', 'athlete', 'elderly', 'child', 'teen', 'too_young', 'pregnant'."
        ),
        examples=["general", "athlete", "elderly"],
    )

    group_display: str = Field(
        ...,
        description="Localized display name for the group.",
        examples=["General", "Athlete", "Elderly"],
    )

    interpretation: str = Field(
        ...,
        description="Localized interpretation text for the BMI value in the context of the group.",
        examples=["Your BMI is within the normal range for your age group."],
    )

    wht_ratio: float | None = Field(
        None,
        description="Waist-to-Height Ratio (WHtR). Calculated only if waist_cm was provided.",
        examples=[0.47, 0.52, None],
    )

    waist_risk: WaistRiskResultSchema | None = Field(
        None,
        description=(
            "Waist risk assessment result. Present only if waist_cm was provided "
            "and risk was calculated."
        ),
        examples=[
            {
                "wht_ratio": 0.52,
                "risk_level": "moderate",
                "notes": ("Increased waist-related risk",),
            },
            None,
        ],
    )

    notes: list[str] = Field(
        default_factory=list,
        description=(
            "Aggregated notes (currently only from waist_risk.notes). Empty list if no notes."
        ),
        examples=[[], ["Increased waist-related risk"]],
    )

    age_band: Literal["too_young", "child", "teen", "adult", "elderly"] = Field(
        ...,
        description=(
            "Age band for UI differentiation: "
            "'too_young' (<12), 'child' (12-14), 'teen' (15-18), "
            "'adult' (19-59), 'elderly' (>=60)."
        ),
        examples=["adult", "teen", "elderly"],
    )

    visualization: BMIScaleV1Spec | None = Field(
        None,
        description="Optional BMI scale visualization spec (v1). Frontend should render this if available.",
    )

    interpretation_v1: BMIInterpretationV1Schema | None = Field(
        None,
        description=(
            "Optional structured interpretation (v1). i18n keys only. "
            "None only for too_young. "
            "Pregnancy always returns structured interpretation (goal=medical_review, target=prenatal_guidelines). "
            "Pregnant+athlete includes additional athlete disclaimers."
        ),
        examples=[
            {
                "goal_direction": "maintain",
                "target_range": {"min": 18.5, "max": 25.0},
                "risk_flags": [],
                "priority_notes": [],
                "disclaimers": ["bmi.interpretation.disclaimer.general"],
            },
            None,
        ],
    )

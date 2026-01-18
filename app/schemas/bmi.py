# -*- coding: utf-8 -*-
"""
BMI Schemas

RU: Схемы для расчета BMI через единый engine.
EN: Schemas for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

import math
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class SoftPaywallMessage(BaseModel):
    """
    Text-only soft paywall message.

    IMPORTANT:
    - This is NOT medical advice, only wellness positioning.
    - No BMI-dependent logic should influence this object.
    """

    lang: Literal["ru", "en", "es"] = Field(..., description="Language code")

    title_key: str = Field(..., description="i18n key for title")
    body_key: str = Field(..., description="i18n key for body text")
    cta_key: str = Field(..., description="i18n key for CTA label")

    default_title: str = Field(..., description="Localized fallback title")
    default_body: str = Field(..., description="Localized fallback body")
    default_cta: str = Field(..., description="Localized fallback CTA label")


class SoftPaywallAvailability(BaseModel):
    """PRO tier availability status."""

    pro_available: bool = Field(..., description="Whether PRO is available at runtime")
    reason_key: str | None = Field(
        default=None, description="Optional i18n key if PRO is unavailable"
    )


class SoftPaywallHook(BaseModel):
    """
    Soft paywall hook: metadata for clients to render a light PRO CTA.

    NOTE:
    - Backend contract only. No UI decisions here.
    - Must be injected in adapter/router layer only.
    """

    id: str = Field(..., description="Stable hook identifier")
    kind: Literal["cta"] = Field(default="cta")
    position: Literal["post_result"] = Field(default="post_result")
    priority: int = Field(default=50, ge=0, le=100)

    message: SoftPaywallMessage
    availability: SoftPaywallAvailability
    target: Literal["pro_paywall"] = Field(default="pro_paywall")


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


class BMICalculateRequest(BaseModel):
    model_config = {"extra": "forbid"}  # Reject extra fields (e.g., hip_cm in FREE tier)
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

    gender: str | None = Field(
        default=None,
        description="Gender: 'male' or 'female'. Will be normalized by engine.",
        examples=["male", "female", "муж", "жен", None],
    )

    pregnant: str | bool = Field(
        default=False,
        description=(
            "Pregnancy status. Accepts: 'yes'/'no' (string) or True/False (bool). "
            "Will be normalized to bool by engine."
        ),
        examples=["no", "yes", False, True],
    )

    @field_validator("gender", mode="before")
    @classmethod
    def _normalize_gender_token(cls, v: str | None) -> str | None:
        """
        RU: Нормализует gender токены в "male" | "female" | None.
        EN: Normalizes gender tokens to "male" | "female" | None.

        Exact tokens are normalized before invariant checks to ensure schema↔engine parity.
        """
        if v is None:
            return None
        s = _normalize_ws_lower(v)
        if not s:
            return None
        # Exact tokens (must match engine contract)
        if s in _FEMALE_EXACT:
            return "female"
        if s in _MALE_EXACT:
            return "male"
        # Prefix-based tokens (RU/ES startswith parity)
        if any(s.startswith(prefix) for prefix in _FEMALE_PREFIXES):
            return "female"
        if any(s.startswith(prefix) for prefix in _MALE_PREFIXES):
            return "male"
        # Unknown token: return as-is (will be handled by engine fallback)
        return s

    @field_validator("pregnant", mode="before")
    @classmethod
    def _normalize_pregnant(cls, v: str | bool | None) -> bool:
        """
        RU: Нормализует pregnant в bool.
        EN: Normalizes pregnant to bool.
        """
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        s = _normalize_ws_lower(v if isinstance(v, str) else None)
        if not s:
            return False
        if s in _TRUE_STRINGS:
            return True
        if s in _FALSE_STRINGS:
            return False
        # Unknown token -> treat as False (safe default)
        return False

    athlete: str | bool = Field(
        default=False,
        description=(
            "Athlete status. Accepts: 'yes'/'no' (string) or True/False (bool). "
            "Will be normalized to bool by schema."
        ),
        examples=["no", "yes", False, True],
    )

    @field_validator("athlete", mode="before")
    @classmethod
    def _normalize_athlete(cls, v: str | bool | None) -> bool:
        """
        RU: Нормализует athlete в bool.
        EN: Normalizes athlete to bool.
        """
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        s = _normalize_ws_lower(v if isinstance(v, str) else None)
        if not s:
            return False
        if s in _TRUE_STRINGS:
            return True
        if s in _FALSE_STRINGS:
            return False
        # Unknown token -> treat as False (safe default)
        return False

    waist_cm: float | None = Field(
        default=None,
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
    def _apply_pregnancy_invariant(self) -> "BMICalculateRequest":
        """
        RU: Применяет инвариант беременности: мягкая нормализация (не 422).
        EN: Applies pregnancy invariant: soft normalization (no 422).

        Rules:
        - If pregnant=True and gender=None → auto-set gender="female" (pregnant implies female)
        - If pregnant=True and gender="male" → coerce pregnant=False (pipeline robustness)

        This keeps the BMI pipeline robust: male+pregnant doesn't break /plan or /bmi endpoints.
        """
        if self.pregnant:
            if self.gender is None:
                # pregnant задаёт смысл пола
                self.gender = "female"
            elif self.gender == "male":
                # устойчивость пайплайна: не 422, а мягкая нормализация
                self.pregnant = False
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

    model_config = {"extra": "forbid"}  # Reject extra fields (e.g., whr in FREE tier)

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
        default=None,
        description="Optional BMI scale visualization spec (v1). Frontend should render this if available.",
    )

    interpretation_v1: BMIInterpretationV1Schema | None = Field(
        default=None,
        description=(
            "Optional structured interpretation (v1). i18n keys only. "
            "Currently may be None while wiring is in progress. "
            "Planned behavior: None only for too_young; pregnancy returns "
            "structured interpretation (goal=medical_review, target=prenatal_guidelines), "
            "and pregnant+athlete includes additional athlete disclaimers."
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

    soft_paywall: SoftPaywallHook | None = Field(
        default=None,
        description="Optional soft paywall hook for PRO tier upsell (wellness positioning only).",
    )


class BMICalculateProRequest(BMICalculateRequest):
    """
    PRO tier BMI calculation request (extends FREE with hip_cm for WHR).

    RU: Запрос расчета BMI для PRO уровня (расширяет FREE с hip_cm для WHR).
    EN: PRO tier BMI calculation request (extends FREE with hip_cm for WHR).
    """

    # Override gender field: type is str | None (for input), but model validator guarantees str after validation
    # This ensures WHR/waist risk thresholds are always calculated with valid gender
    gender: str | None = Field(
        default=None,
        description="Gender: 'male' or 'female'. Normalized by schema validator. Guaranteed to be str after validation.",
        examples=["male", "female", "муж", "жен", None],
    )

    hip_cm: float | None = Field(
        default=None,
        gt=0,
        description=(
            "Hip circumference in centimeters (optional, PRO tier only). "
            "If provided along with waist_cm, enables WHR (Waist-to-Hip Ratio) calculation."
        ),
        examples=[95.0, 100.5, None],
    )

    @field_validator("gender", mode="before")
    @classmethod
    def _coerce_gender_pro(cls, v: object) -> str | None:
        """
        RU: Нормализует gender токены для PRO tier (возвращает str | None для pregnancy invariant).
        EN: Normalizes gender tokens for PRO tier (returns str | None for pregnancy invariant).

        Rules:
        - Valid tokens → normalized via parent's _normalize_gender_token logic
        - None / empty / invalid → None (will be handled by _apply_pro_gender_invariant)
        - Unknown tokens → None (will default to "male" after pregnancy check)

        Note: Returns None to allow pregnancy invariant to set gender="female" if pregnant=True.
        Final guarantee of str (not None) happens in _apply_pro_gender_invariant.
        """
        # None or empty → None (will be handled by model validator)
        if v is None:
            return None
        if not isinstance(v, str):
            return None

        s = _normalize_ws_lower(v)
        if not s:
            return None

        # Use parent's normalization logic for known tokens
        if s in _FEMALE_EXACT:
            return "female"
        if s in _MALE_EXACT:
            return "male"
        if any(s.startswith(prefix) for prefix in _FEMALE_PREFIXES):
            return "female"
        if any(s.startswith(prefix) for prefix in _MALE_PREFIXES):
            return "male"

        # Unknown token → None (will default to "male" after pregnancy check)
        return None

    @model_validator(mode="after")
    def _apply_pro_gender_invariant(self) -> "BMICalculateProRequest":
        """
        RU: Применяет инварианты gender и беременности для PRO tier: гарантирует str (не None).
        EN: Applies gender and pregnancy invariants for PRO tier: guarantees str (not None).

        Rules:
        - First apply pregnancy invariant (may set gender="female" if pregnant=True and gender=None)
        - If gender is still None after pregnancy check → default to "male" (safe default for WHR/waist risk thresholds)
        - If pregnant=True and gender="male" → coerce pregnant=False (pipeline robustness)

        This ensures router receives str, eliminating need for assert/fallback in router layer.
        """
        # Apply pregnancy invariant first (may set gender="female" if pregnant)
        if self.pregnant:
            if self.gender is None:
                self.gender = "female"
            elif self.gender == "male":
                # устойчивость пайплайна: не 422, а мягкая нормализация
                self.pregnant = False

        # Ensure gender is never None after all normalizations
        if self.gender is None:
            self.gender = "male"

        return self


class BMICalculateProResponse(BMICalculateResponse):
    """
    PRO tier BMI calculation response (extends FREE with whr).

    RU: Ответ расчета BMI для PRO уровня (расширяет FREE с whr).
    EN: PRO tier BMI calculation response (extends FREE with whr).
    """

    whr: float | None = Field(
        None,
        description=(
            "Waist-to-Hip Ratio (WHR, PRO tier only). "
            "Calculated only if both waist_cm and hip_cm were provided and >0."
        ),
        examples=[0.80, 0.95, None],
    )

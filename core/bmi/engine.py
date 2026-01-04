"""
BMI Engine Orchestrator

RU: Единый engine для расчета BMI (canonical source of truth).
EN: Unified engine for BMI calculation (canonical source of truth).

This module will be fully implemented in PR-455.
Currently provides a stub implementation for development/testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeAlias

from core.i18n import Language, normalize_lang

if TYPE_CHECKING:
    from core.bmi.risk import WaistRiskResult

AgeBand: TypeAlias = Literal["too_young", "child", "teen", "adult", "elderly"]

# RU: Константы доменной валидации для WHtR (parity с legacy).
# EN: Domain validation constants for WHtR (legacy parity).
_MIN_HEIGHT_M = 0.5
_MAX_HEIGHT_M = 3.0
_MAX_WAIST_CM = 300.0

_DEFAULT_YES_VALUES: set[str] = {
    "yes",
    "y",
    "true",
    "1",
    "да",
    "д",
    "истина",
    "si",
    "sí",
}


def _normalize_gender(gender: str) -> str:
    """
    RU: Нормализует gender к 'male'/'female' с parity по legacy.
    EN: Normalize gender to 'male'/'female' with legacy parity.

    Legacy nuance: uses startswith("жен") / startswith("mujer").
    """
    g = (gender or "").strip().lower()

    # Female (RU/ES startswith parity)
    if g == "female" or g.startswith("жен") or g.startswith("mujer"):
        return "female"

    # Male variants
    if g == "male" or g.startswith("муж"):
        return "male"

    # Fallback: legacy-compatible default
    return "male"


def _normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool:
    """
    RU: Нормализует флаг yes/no (pregnant/athlete и т.п.) в bool.
    EN: Normalize yes/no-ish flag to bool.

    IMPORTANT:
    - Commit 1: без regex для athlete (оставляем на Commit 2 в _auto_group()).
      Это уменьшает дублирование и риск расхождений.
    """
    if isinstance(value, bool):
        return value

    if not isinstance(value, str):
        return False

    s = value.strip().lower()
    if not s:
        return False

    allowed = yes_values if yes_values is not None else _DEFAULT_YES_VALUES
    return s in allowed


def _normalize_lang(lang: str) -> Language:
    """
    RU: Используем canonical normalize_lang из core.i18n (не дублируем).
    EN: Use canonical core.i18n.normalize_lang() (no duplication).
    """
    return normalize_lang(lang)


def _age_band(age: int) -> AgeBand:
    """
    RU: Возрастные диапазоны — канон из TODO/Qoder.
    EN: Age bands — canonical from TODO/Qoder.

    NOTE: age 19 inclusive is 'teen'; adult starts at 20.
    """
    if age < 12:
        return "too_young"
    if 12 <= age < 13:
        return "child"
    if 13 <= age <= 19:
        return "teen"
    if 19 < age < 60:
        return "adult"
    return "elderly"


def _compute_bmi(weight_kg: float, height_m: float) -> float:
    """
    RU: BMI = weight_kg / (height_m ** 2), округление до 1 знака (legacy parity).
    EN: BMI = weight_kg / (height_m ** 2), rounded to 1 decimal (legacy parity).

    Domain bounds validation (10..100) делаем в orchestrator (Commit 3), не здесь.
    """
    if weight_kg <= 0:
        raise ValueError("weight_kg must be positive")
    if height_m <= 0:
        raise ValueError("height_m must be positive")

    bmi = weight_kg / (height_m**2)
    return round(bmi, 1)


def _compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
    """
    RU: WHtR = (waist_cm / 100.0) / height_m, округление до 2 знаков.
    EN: WHtR = (waist_cm / 100.0) / height_m, rounded to 2 decimals.

    Fail-soft parity:
    - invalid height or waist -> None
    - try/except for safety
    """
    if waist_cm is None:
        return None

    # Height validation (legacy parity)
    if height_m <= _MIN_HEIGHT_M or height_m > _MAX_HEIGHT_M:
        return None

    # Waist validation (legacy parity)
    if waist_cm <= 0 or waist_cm > _MAX_WAIST_CM:
        return None

    try:
        ratio = (waist_cm / 100.0) / height_m
        return round(ratio, 2)
    except (ZeroDivisionError, OverflowError):
        return None


@dataclass(frozen=True)
class BMICalculateResult:
    """Stub result dataclass for BMI calculation."""

    bmi: float
    category: str | None
    group: str
    group_display: str
    interpretation: str
    wht_ratio: float | None
    waist_risk: WaistRiskResult | None
    notes: tuple[str, ...]
    age_band: AgeBand


def calculate_bmi_result(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    pregnant: bool,
    athlete: bool,
    waist_cm: float | None,
    lang: str,
) -> BMICalculateResult:
    """
    RU: Рассчитывает BMI через единый engine (stub).
    EN: Calculate BMI via unified engine (stub).

    This is a placeholder implementation.
    Full implementation will be added in PR-455 (engine implementation).

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: Gender ("male"/"female")
        pregnant: Pregnant flag (bool, normalized by router)
        athlete: Athlete flag (bool, normalized by router)
        waist_cm: Waist circumference in cm (optional)
        lang: Language code ("ru"/"en"/"es")

    Returns:
        BMICalculateResult: BMI calculation result (stub)

    Raises:
        NotImplementedError: Always (stub implementation)
    """
    raise NotImplementedError(
        "BMI engine is not yet implemented. This will be available after PR-455."
    )

# -*- coding: utf-8 -*-
"""
RU: Оценка риска по окружности талии (legacy thresholds).
EN: Waist-circumference risk assessment (legacy thresholds).

IMPORTANT:
- No FastAPI/Pydantic imports here.
- No I/O, env, time, random.
- Keep behavior stable (golden tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from core.bmi.engine import _compute_wht_ratio


RiskLevel = Literal["low", "moderate", "high"]

# BMI thresholds (canonical source of truth)
BMI_NORMAL_MIN: Final[float] = 18.5
BMI_OVERWEIGHT_THRESHOLD: Final[float] = 25.0
BMI_OBESE_THRESHOLD: Final[float] = 30.0

# WHR thresholds for Pro tier (sex-specific health risk)
WHR_MALE_HIGH_RISK: Final[float] = 0.95
WHR_FEMALE_HIGH_RISK: Final[float] = 0.80

# WHR thresholds for Free/Simple tier (simplified thresholds)
WHR_SIMPLE_MALE_HIGH_RISK: Final[float] = 0.90
WHR_SIMPLE_FEMALE_HIGH_RISK: Final[float] = 0.85

# BMI threshold for very high risk (Free/Simple tier staging)
BMI_VERY_HIGH_THRESHOLD: Final[float] = 35.0


# Localized messages for waist risk assessment
_MESSAGES: dict[tuple[RiskLevel, str], str] = {
    ("moderate", "ru"): "Повышенный риск по талии",
    ("high", "ru"): "Высокий риск по талии",
    ("moderate", "en"): "Increased waist-related risk",
    ("high", "en"): "High waist-related risk",
    ("moderate", "es"): "Riesgo aumentado relacionado con la cintura",
    ("high", "es"): "Alto riesgo relacionado con la cintura",
}


@dataclass(frozen=True)
class WaistRiskResult:
    """
    RU: Результат оценки риска по талии.
    EN: Waist risk assessment result.
    """

    wht_ratio: float | None
    risk_level: RiskLevel
    notes: tuple[str, ...]


def _norm_lang(lang: str) -> str:
    """
    RU: Нормализация языка. Unknown -> en (fail-soft).
    EN: Normalize language. Unknown -> en (fail-soft).
    """
    val = (lang or "").strip().lower()
    return val if val in {"ru", "en", "es"} else "en"


def _norm_gender(gender: str) -> str:
    """
    RU: Нормализация пола для порогов талии. Unknown -> male (fail-soft).
    EN: Normalize gender for waist thresholds. Unknown -> male (fail-soft).
    """
    g = (gender or "").strip().lower()
    if g in {"female", "f", "woman", "w", "жен", "женщина"}:
        return "female"
    if g in {"male", "m", "man", "муж", "мужчина"}:
        return "male"
    return "male"


def _waist_thresholds(gender: str) -> tuple[float, float]:
    """
    RU: Каноничные пороги талии по полу (warn, high). Single source of truth.
    EN: Canonical waist thresholds by gender (warn, high). Single source of truth.

    Returns:
        (warn_threshold, high_threshold) in cm
    """
    g = _norm_gender(gender)
    return (94.0, 102.0) if g == "male" else (80.0, 88.0)


def _waist_risk_level(waist_cm: float, gender: str) -> RiskLevel:
    """
    RU: Определяет уровень риска по талии (без WHtR).
    EN: Determines waist risk level (no WHtR).
    """
    warn, high = _waist_thresholds(gender)
    if waist_cm >= high:
        return "high"
    if waist_cm >= warn:
        return "moderate"
    return "low"


def get_waist_risk_note(waist_cm: float | None, gender: str, lang: str) -> str:
    """
    RU: Возвращает локализованную строку риска по талии (без WHtR).
    EN: Returns localized waist risk note string (no WHtR).

    COMPAT: Used by legacy_app.waist_risk() proxy.

    Args:
        waist_cm: Waist circumference in cm. If None -> returns "".
        gender: "male"/"female" (will be normalized).
        lang: "ru"/"en"/"es" (will be normalized).

    Returns:
        Localized risk message or empty string if low/no risk.
    """
    if waist_cm is None:
        return ""

    level = _waist_risk_level(waist_cm, gender)
    if level == "low":
        return ""

    lang_norm = _norm_lang(lang)
    return _MESSAGES.get((level, lang_norm), _MESSAGES[(level, "en")])


def calculate_waist_risk(
    waist_cm: float | None,
    height_m: float,
    gender: str,
    lang: str,
) -> WaistRiskResult | None:
    """
    RU: Вычисляет риск по окружности талии.
    EN: Calculate waist-circumference risk.

    Args:
        waist_cm: Waist circumference in cm. If None -> returns None.
        height_m: Height in meters (used only for WHtR; fail-soft).
        gender: "male"/"female" (will be normalized).
        lang: "ru"/"en"/"es" (will be normalized).

    Returns:
        WaistRiskResult | None
    """
    if waist_cm is None:
        return None

    lang_norm = _norm_lang(lang)
    risk_level = _waist_risk_level(waist_cm, gender)

    # Get localized message for non-low risk levels
    if risk_level != "low":
        msg = _MESSAGES.get((risk_level, lang_norm), _MESSAGES[(risk_level, "en")])
        notes: tuple[str, ...] = (msg,)
    else:
        notes = ()

    wht_ratio = _compute_wht_ratio(waist_cm, height_m)

    return WaistRiskResult(wht_ratio=wht_ratio, risk_level=risk_level, notes=notes)

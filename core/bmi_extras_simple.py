"""
BMI Pro: Advanced metrics and risk assessment functions (simplified version).

This module implements professional-level BMI analysis including:
- Waist-to-Height Ratio (WHtR) and risk categories
- Waist-to-Hip Ratio (WHR) with sex-specific thresholds
- Fat-Free Mass Index (FFMI) calculation
- Obesity staging based on multiple metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Import i18n functionality
from core.i18n import Language, t

Sex = Literal["female", "male"]

@dataclass(frozen=True)
class BMIProCard:
    """RU: Расширенная карточка BMI (поясничные метрики и риск).
    EN: Extended BMI card with circumferences and risk staging.
    """
    bmi: float
    whtr: float
    whr: float | None
    ffmi: float | None
    risk_level: Literal["low", "moderate", "high"]
    notes: list[str]

def wht_ratio(waist_cm: float, height_cm: float) -> float:
    """Waist-to-Height Ratio (WHtR)"""
    if waist_cm <= 0 or height_cm <= 0:
        raise ValueError("waist_cm and height_cm must be positive")
    return round(waist_cm / height_cm, 2)

def whr_ratio(waist_cm: float, hip_cm: float) -> float:
    """Waist-to-Hip Ratio (WHR)"""
    if waist_cm <= 0 or hip_cm <= 0:
        raise ValueError("waist_cm and hip_cm must be positive")
    return round(waist_cm / hip_cm, 2)

def ffmi(value_weight_kg: float, height_cm: float, bodyfat_percent: float) -> float:
    """Fat-Free Mass Index (по Кэтчу-МакАрдлу идее: FFM = weight * (1 - bf%/100))"""
    if value_weight_kg <= 0 or height_cm <= 0:
        raise ValueError("weight_kg and height_cm must be positive")
    if not (0 <= bodyfat_percent <= 60):
        raise ValueError("bodyfat_percent out of range")
    ffm = value_weight_kg * (1 - bodyfat_percent / 100.0)
    h_m = height_cm / 100.0
    return round(ffm / (h_m * h_m), 1)

def stage_obesity(
    *, bmi: float, whtr: float, whr: float | None, sex: Sex, lang: Language = "en"
) -> tuple[str, list[str]]:
    """RU: Мягкое стадирование риска по BMI+WHtR(+WHR).
       EN: Light risk staging using BMI+WHtR(+WHR).
    """
    notes: list[str] = []
    # Базово по WHtR (≈>0.5 — повышенный риск)
    if whtr < 0.5:
        risk = "low"
    elif whtr < 0.6:
        risk = "moderate"
        notes.append(t(lang, "risk_moderate_central_fat"))
    else:
        risk = "high"
        notes.append(t(lang, "risk_high_central_fat"))

    # Корректировка по WHR (пороги зависят от пола)
    if whr is not None:
        thr = 0.9 if sex == "male" else 0.85
        if whr >= thr:
            notes.append(t(lang, "risk_high_whr", threshold=thr))
            risk = "high" if risk == "moderate" else risk

    # Доп. акцент по очень высокому BMI
    if bmi >= 35:
        notes.append(t(lang, "risk_high_bmi"))
        risk = "high"
    elif bmi >= 30 and risk == "low":
        risk = "moderate"
        notes.append(t(lang, "risk_moderate_bmi"))

    return risk, notes

"""
BMI Extras: Advanced metrics and risk assessment functions.

This module implements BMI analysis with two explicit product tiers:

Pro Tier (Paid - PRO subscription):
- Rounding: 3 decimal places
- WHR thresholds: 0.95 (male) / 0.80 (female) - stricter
- FFMI: Supports estimate mode (0.85 default if bodyfat_pct not provided)
- Return formats: Dict for staging, comprehensive interpretation
- Functions: wht_ratio(), whr_ratio(waist, hip, sex), ffmi(), stage_obesity(), interpret_*()

Free/Simple Tier (Free - no subscription):
- Rounding: 2 decimal places
- WHR thresholds: 0.90 (male) / 0.85 (female) - simplified
- FFMI: Requires bodyfat_pct (no estimate mode)
- Return formats: Tuple for staging, simplified response
- Functions: wht_ratio_simple(), whr_ratio_simple(waist, hip), ffmi_simple(), stage_obesity_simple(), BMIProCard

Product Policy: Different tiers serve different user needs. Free tier provides basic calculations;
Pro tier provides detailed analysis with sex-specific thresholds and comprehensive staging.
"""

from dataclasses import dataclass
from typing import Dict, Literal, Optional

# Import i18n functionality
from core.i18n import Language, t

Sex = Literal["female", "male"]


def wht_ratio(waist_cm: float, height_cm: float) -> float:
    """Calculate Waist-to-Height Ratio (WHtR).

    WHtR is a better predictor of health risks than BMI alone.

    Args:
        waist_cm: Waist circumference in centimeters
        height_cm: Height in centimeters

    Returns:
        WHtR value (waist/height ratio)

    Raises:
        ValueError: If waist or height is <= 0
    """
    if waist_cm <= 0:
        raise ValueError("Waist circumference must be positive")
    if height_cm <= 0:
        raise ValueError("Height must be positive")

    return round(waist_cm / height_cm, 3)


def whr_ratio(waist_cm: float, hip_cm: float, sex: Literal["male", "female"]) -> float:
    """Calculate Waist-to-Hip Ratio (WHR).

    Sex-specific thresholds for health risk assessment.

    Args:
        waist_cm: Waist circumference in centimeters
        hip_cm: Hip circumference in centimeters
        sex: Biological sex ("male" or "female")

    Returns:
        WHR value (waist/hip ratio)

    Raises:
        ValueError: If waist or hip is <= 0
    """
    if waist_cm <= 0:
        raise ValueError("Waist circumference must be positive")
    if hip_cm <= 0:
        raise ValueError("Hip circumference must be positive")

    return round(waist_cm / hip_cm, 3)


def ffmi(
    weight_kg: float, height_cm: float, bodyfat_pct: Optional[float] = None
) -> Dict[str, float]:
    """Calculate Fat-Free Mass Index (FFMI).

    FFMI is a normalized measure of lean body mass that accounts for height.

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        bodyfat_pct: Body fat percentage (optional)

    Returns:
        Dictionary with FFM (kg) and FFMI values

    Raises:
        ValueError: If weight or height is <= 0, or bodyfat_pct is invalid
    """
    if weight_kg <= 0:
        raise ValueError("Weight must be positive")
    if height_cm <= 0:
        raise ValueError("Height must be positive")
    if bodyfat_pct is not None and (bodyfat_pct < 0 or bodyfat_pct > 100):
        raise ValueError("Body fat percentage must be between 0 and 100")

    # Calculate fat-free mass
    if bodyfat_pct is not None:
        ffm = weight_kg * (1 - bodyfat_pct / 100)
    else:
        # If no body fat percentage provided, estimate using BMI
        height_m = height_cm / 100
        # Simplified estimation: assume 15% body fat for average adult
        ffm = weight_kg * 0.85

    # Calculate FFMI (normalize to height)
    height_m = height_cm / 100
    ffmi_value = ffm / (height_m**2)

    return {"ffm_kg": round(ffm, 1), "ffmi": round(ffmi_value, 1)}


def interpret_wht_ratio(wht_ratio_value: float, lang: Language = "en") -> Dict[str, str]:
    """Interpret WHtR value according to health risk categories.

    Args:
        wht_ratio_value: Calculated WHtR value
        lang: Language for descriptions

    Returns:
        Dictionary with risk category and description
    """
    if wht_ratio_value < 0.4:
        return {
            "category": "underweight",
            "risk": "low",
            "description": "Low health risk",
        }
    elif wht_ratio_value < 0.5:
        return {
            "category": "healthy",
            "risk": "low",
            "description": "Healthy weight range",
        }
    elif wht_ratio_value < 0.6:
        return {
            "category": "overweight",
            "risk": "moderate",
            "description": "Moderate health risk",
        }
    else:
        return {"category": "obese", "risk": "high", "description": "High health risk"}


def interpret_whr_ratio(
    whr_ratio_value: float, sex: Literal["male", "female"], lang: str
) -> Dict[str, str]:
    """Interpret WHR value according to sex-specific health risk thresholds.

    Args:
        whr_ratio_value: Calculated WHR value
        sex: Biological sex ("male" or "female")
        lang: Language for descriptions

    Returns:
        Dictionary with risk category and description
    """
    # Sex-specific thresholds for increased health risk
    if sex.lower() == "male":
        if whr_ratio_value < 0.95:
            risk_level = "low"
            description = t(lang, "risk_low_health")  # type: ignore
        else:
            risk_level = "high"
            description = t(lang, "risk_high_android_shape")  # type: ignore
    else:  # female
        if whr_ratio_value < 0.80:
            risk_level = "low"
            description = t(lang, "risk_low_health")  # type: ignore
        else:
            risk_level = "high"
            description = t(lang, "risk_high_android_shape")  # type: ignore

    return {"risk": risk_level, "description": description}


def stage_obesity(
    bmi: float, wht: float, whr: float, sex: Literal["male", "female"], lang: str
) -> Dict[str, str]:
    """Stage obesity based on multiple metrics.

    Combines BMI, WHtR, and WHR for comprehensive risk assessment.

    Args:
        bmi: Body Mass Index
        wht: Waist-to-Height Ratio
        whr: Waist-to-Hip Ratio
        sex: Biological sex
        lang: Language for recommendations

    Returns:
        Dictionary with staging information and recommendations
    """
    # Get individual risk assessments
    wht_interpretation = interpret_wht_ratio(wht, lang)  # type: ignore
    whr_interpretation = interpret_whr_ratio(whr, sex, lang)

    # Determine overall staging
    risk_factors = 0
    if bmi >= 30:  # Obese
        risk_factors += 1
    if wht >= 0.5:  # High WHtR risk
        risk_factors += 1
    if (sex == "male" and whr >= 0.95) or (sex == "female" and whr >= 0.80):  # High WHR risk
        risk_factors += 1

    if risk_factors >= 2:
        stage = "high_risk"
        recommendation = t(lang, "recommendation_consult_healthcare")  # type: ignore
    elif risk_factors == 1:
        stage = "moderate_risk"
        recommendation = t(lang, "recommendation_monitor_health")  # type: ignore
    else:
        stage = "low_risk"
        recommendation = t(lang, "recommendation_maintain_habits")  # type: ignore

    if bmi >= 30:
        bmi_category = "obese"
    elif bmi >= 25:
        bmi_category = "overweight"
    elif bmi >= 18.5:
        bmi_category = "normal"
    else:
        bmi_category = "underweight"

    return {
        "stage": stage,
        "risk_factors": str(risk_factors),
        "recommendation": recommendation,
        "bmi_category": bmi_category,
        "wht_risk": wht_interpretation["risk"],
        "whr_risk": whr_interpretation["risk"],
    }


def stage_obesity_optional_whr(
    bmi: float,
    wht: float,
    whr: Optional[float],
    sex: Literal["male", "female"],
    lang: str,
) -> Dict[str, str]:
    """Stage obesity based on multiple metrics with optional WHR.

    PRO tier staging that handles missing WHR data correctly.
    If WHR is missing, do NOT treat it as low risk; mark WHR as "unknown"
    and exclude from risk_factors calculation.

    Args:
        bmi: Body Mass Index
        wht: Waist-to-Height Ratio
        whr: Waist-to-Hip Ratio (optional - None if hip_cm not provided)
        sex: Biological sex
        lang: Language for recommendations

    Returns:
        Dictionary with staging information and recommendations
    """
    # Get WHtR interpretation (always available)
    wht_interpretation = interpret_wht_ratio(wht, lang)  # type: ignore

    # WHR interpretation - only if data available
    whr_risk = "unknown"
    if whr is not None:
        whr_interpretation = interpret_whr_ratio(whr, sex, lang)
        whr_risk = whr_interpretation["risk"]

    # Determine overall staging - only count WHR if data available
    risk_factors = 0
    if bmi >= 30:  # Obese
        risk_factors += 1
    if wht >= 0.5:  # High WHtR risk
        risk_factors += 1
    if whr is not None:
        # Only count WHR risk factor if we have actual data
        if (sex == "male" and whr >= 0.95) or (sex == "female" and whr >= 0.80):
            risk_factors += 1

    if risk_factors >= 2:
        stage = "high_risk"
        recommendation = t(lang, "recommendation_consult_healthcare")  # type: ignore
    elif risk_factors == 1:
        stage = "moderate_risk"
        recommendation = t(lang, "recommendation_monitor_health")  # type: ignore
    else:
        stage = "low_risk"
        recommendation = t(lang, "recommendation_maintain_habits")  # type: ignore

    if bmi >= 30:
        bmi_category = "obese"
    elif bmi >= 25:
        bmi_category = "overweight"
    elif bmi >= 18.5:
        bmi_category = "normal"
    else:
        bmi_category = "underweight"

    return {
        "stage": stage,
        "risk_factors": str(risk_factors),
        "recommendation": recommendation,
        "bmi_category": bmi_category,
        "wht_risk": wht_interpretation["risk"],
        "whr_risk": whr_risk,
    }


# ============================================================================
# Free/Simple Tier - Simplified versions for basic BMI calculations
# ============================================================================
#
# Product Policy:
# - Free tier: Simplified thresholds, 2 decimal places, basic risk assessment
# - Pro tier: Stricter sex-specific thresholds, 3 decimal places, comprehensive staging
#
# Rationale: Different rounding and thresholds serve different product tiers.
# Free users get simplified calculations; Pro users get detailed analysis.
# ============================================================================


@dataclass(frozen=True)
class BMIProCard:
    """RU: Расширенная карточка BMI (поясничные метрики и риск).
    EN: Extended BMI card with circumferences and risk staging.
    """

    bmi: float
    whtr: float
    whr: Optional[float]
    ffmi: Optional[float]
    risk_level: Literal["low", "moderate", "high"]
    notes: list[str]


def wht_ratio_simple(waist_cm: float, height_cm: float) -> float:
    """Waist-to-Height Ratio (WHtR) - Free/Simple tier.

    Product Policy: Free tier uses 2 decimal places (simplified precision).
    Pro tier uses 3 decimal places (see wht_ratio()).

    Args:
        waist_cm: Waist circumference in centimeters
        height_cm: Height in centimeters

    Returns:
        WHtR value rounded to 2 decimal places

    Raises:
        ValueError: If waist or height is <= 0
    """
    if waist_cm <= 0 or height_cm <= 0:
        raise ValueError("waist_cm and height_cm must be positive")
    return round(waist_cm / height_cm, 2)


def whr_ratio_simple(waist_cm: float, hip_cm: float) -> float:
    """Waist-to-Hip Ratio (WHR) - Free/Simple tier.

    Product Policy: Free tier uses simplified calculation (no sex-specific thresholds).
    Pro tier uses sex-specific thresholds (see whr_ratio()).

    Rounding: 2 decimal places (Free tier policy).

    Args:
        waist_cm: Waist circumference in centimeters
        hip_cm: Hip circumference in centimeters

    Returns:
        WHR value rounded to 2 decimal places

    Raises:
        ValueError: If waist or hip is <= 0
    """
    if waist_cm <= 0 or hip_cm <= 0:
        raise ValueError("waist_cm and hip_cm must be positive")
    return round(waist_cm / hip_cm, 2)


def ffmi_simple(value_weight_kg: float, height_cm: float, bodyfat_percent: float) -> float:
    """Fat-Free Mass Index (FFMI) - Simple tier.

    Args:
        value_weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        bodyfat_percent: Body fat percentage (required, 0-60)

    Returns:
        FFMI value rounded to 1 decimal place

    Raises:
        ValueError: If weight, height, or bodyfat_percent is invalid
    """
    if value_weight_kg <= 0 or height_cm <= 0:
        raise ValueError("weight_kg and height_cm must be positive")
    if not (0 <= bodyfat_percent <= 60):
        raise ValueError("bodyfat_percent out of range")
    ffm = value_weight_kg * (1 - bodyfat_percent / 100.0)
    h_m = height_cm / 100.0
    return round(ffm / (h_m * h_m), 1)


def stage_obesity_simple(
    *, bmi: float, whtr: float, whr: Optional[float], sex: Sex, lang: Language = "en"
) -> tuple[str, list[str]]:
    """RU: Мягкое стадирование риска по BMI+WHtR(+WHR) - Free/Simple tier.
    EN: Light risk staging using BMI+WHtR(+WHR) - Free/Simple tier.

    Product Policy: Free tier uses simplified thresholds:
    - WHR thresholds: 0.90 (male) / 0.85 (female) - simplified
    - Pro tier uses stricter thresholds: 0.95 (male) / 0.80 (female)

    Returns: Tuple format (risk_level, notes_list) for simple tier compatibility.
    Pro tier returns Dict format (see stage_obesity()).

    Args:
        bmi: Body Mass Index
        whtr: Waist-to-Height Ratio
        whr: Optional Waist-to-Hip Ratio
        sex: Biological sex ("male" or "female")
        lang: Language for messages

    Returns:
        Tuple of (risk_level, notes_list)
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

    # Корректировка по WHR (Free tier: simplified thresholds)
    if whr is not None:
        thr = 0.9 if sex == "male" else 0.85  # Free tier thresholds
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

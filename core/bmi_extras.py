"""
BMI Pro: Advanced metrics and risk assessment functions.

This module implements professional-level BMI analysis including:
- Waist-to-Height Ratio (WHtR) and risk categories
- Waist-to-Hip Ratio (WHR) with sex-specific thresholds
- Fat-Free Mass Index (FFMI) calculation
- Obesity staging based on multiple metrics
"""

from typing import Dict, Literal, Optional

# Import i18n functionality
from core.i18n import Language, t


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
    weight_kg: float,
    height_cm: float,
    bodyfat_pct: Optional[float] = None
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
    ffmi_value = ffm / (height_m ** 2)

    return {
        "ffm_kg": round(ffm, 1),
        "ffmi": round(ffmi_value, 1)
    }


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
            "description": t(lang, "risk_low_health")
        }
    elif wht_ratio_value < 0.5:
        return {
            "category": "healthy",
            "risk": "low",
            "description": t(lang, "risk_healthy_weight")
        }
    elif wht_ratio_value < 0.6:
        return {
            "category": "overweight",
            "risk": "moderate",
            "description": t(lang, "risk_moderate_health")
        }
    else:
        return {
            "category": "obese",
            "risk": "high",
            "description": t(lang, "risk_high_health")
        }


def interpret_whr_ratio(
    whr_ratio_value: float,
    sex: Literal["male", "female"],
    lang: Language = "en"
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
            description = t(lang, "risk_low_health")
        else:
            risk_level = "high"
            description = t(lang, "risk_high_android_shape")
    else:  # female
        if whr_ratio_value < 0.80:
            risk_level = "low"
            description = t(lang, "risk_low_health")
        else:
            risk_level = "high"
            description = t(lang, "risk_high_android_shape")

    return {
        "risk": risk_level,
        "description": description
    }


def stage_obesity(
    bmi: float,
    wht: float,
    whr: float,
    sex: Literal["male", "female"],
    lang: Language = "en"
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
    wht_interpretation = interpret_wht_ratio(wht, lang)
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
        recommendation = t(lang, "recommendation_consult_healthcare")
    elif risk_factors == 1:
        stage = "moderate_risk"
        recommendation = t(lang, "recommendation_monitor_health")
    else:
        stage = "low_risk"
        recommendation = t(lang, "recommendation_maintain_habits")

    bmi_category = (
        "obese" if bmi >= 30 else
        "overweight" if bmi >= 25 else
        "normal" if bmi >= 18.5 else
        "underweight"
    )

    return {
        "stage": stage,
        "risk_factors": str(risk_factors),
        "recommendation": recommendation,
        "bmi_category": bmi_category,
        "wht_risk": wht_interpretation["risk"],
        "whr_risk": whr_interpretation["risk"]
    }

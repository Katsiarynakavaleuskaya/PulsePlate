# -*- coding: utf-8 -*-
"""
BMI Visualization Service

RU: Сервис для генерации spec визуализации BMI.
EN: Service for generating BMI visualization spec.

This is an API adapter, not domain logic.
"""

from app.schemas.bmi import BMIScaleV1Spec, BMIRangeSpec, BMIMarkerSpec


def _range(key: str, start: float, end: float) -> BMIRangeSpec:
    """Create BMIRangeSpec using direct constructor.

    Pydantic v2 with populate_by_name=True accepts from_= parameter at runtime.
    Type checkers may not fully understand this, but mypy doesn't flag it as an error.
    """
    return BMIRangeSpec(key=key, from_=start, to=end)


def build_bmi_scale_v1(bmi: float) -> BMIScaleV1Spec:
    """
    Build BMI scale v1 spec for frontend rendering.

    Uses fixed thresholds (0-60) regardless of group.
    Group-specific interpretation is handled separately in category/interpretation fields.

    Args:
        bmi: BMI value (will be rounded to 1 decimal)

    Returns:
        BMIScaleV1Spec with fixed scale 0-60 and WHO standard thresholds
    """
    # Fixed thresholds (WHO standard)
    # Use helper function to create ranges (alias "from" appears in JSON via model_dump(by_alias=True))
    ranges = [
        _range("bmi.underweight", 0.0, 18.5),
        _range("bmi.normal", 18.5, 25.0),
        _range("bmi.overweight", 25.0, 30.0),
        _range("bmi.obesity", 30.0, 60.0),
    ]

    rounded_bmi = round(bmi, 1)

    return BMIScaleV1Spec(
        kind="bmi_scale_v1",
        bmi=rounded_bmi,
        min=0.0,
        max=60.0,
        ranges=ranges,
        marker=BMIMarkerSpec(value=rounded_bmi),
    )

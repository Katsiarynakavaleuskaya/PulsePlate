# -*- coding: utf-8 -*-
"""
BMI Visualization Service

RU: Сервис для генерации spec визуализации BMI.
EN: Service for generating BMI visualization spec.

This is an API adapter, not domain logic.
"""

from app.schemas.bmi import BMIScaleV1Spec, BMIRangeSpec, BMIMarkerSpec


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
    # Use model_validate with dict to handle alias "from" correctly
    # (alias appears in JSON via model_dump(by_alias=True) in router)
    ranges = [
        BMIRangeSpec.model_validate({"key": "bmi.underweight", "from": 0.0, "to": 18.5}),
        BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 18.5, "to": 25.0}),
        BMIRangeSpec.model_validate({"key": "bmi.overweight", "from": 25.0, "to": 30.0}),
        BMIRangeSpec.model_validate({"key": "bmi.obesity", "from": 30.0, "to": 60.0}),
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


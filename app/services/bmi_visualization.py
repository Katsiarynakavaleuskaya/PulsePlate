# -*- coding: utf-8 -*-
"""
BMI Visualization Service

RU: Сервис для генерации spec визуализации BMI.
EN: Service for generating BMI visualization spec.

This is an API adapter, not domain logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.bmi import BMIScaleV1Spec, BMIRangeSpec, BMIMarkerSpec

if TYPE_CHECKING:
    from core.bmi.engine import BMICalculateResult


def _range(key: str, start: float, end: float) -> BMIRangeSpec:
    """Create BMIRangeSpec using model_validate for type-checker compatibility."""
    # NOTE: model_validate() returns Any for mypy; assign to local to keep return type
    result: BMIRangeSpec = BMIRangeSpec.model_validate({"key": key, "from": start, "to": end})
    return result


def build_bmi_scale_v1(
    result: BMICalculateResult,
    scale_min: float = 0.0,
    scale_max: float = 60.0,
) -> BMIScaleV1Spec | None:
    """
    Build BMI scale v1 spec using core thresholds for the user's group.

    Args:
        result: BMICalculateResult from core engine
        scale_min: Minimum BMI for visualization scale (default 0.0)
        scale_max: Maximum BMI for visualization scale (default 60.0)

    Returns:
        BMIScaleV1Spec if visualization should be shown, None for groups
        where category=None (too_young, child, teen, pregnant).

        Aligns visualization availability with BMICategory semantics:
        category=None groups → visualization: null (not misleading adult ranges).
    """
    from core.bmi.engine import get_bmi_visual_ranges

    # Get ranges from core (returns None for category=None groups)
    ranges_data = get_bmi_visual_ranges(
        group=result.group,  # Now correctly typed as BMIGroup
        age_band=result.age_band,
        scale_min=scale_min,
        scale_max=scale_max,
    )

    if ranges_data is None:
        return None

    # Convert to BMIRangeSpec
    ranges = [_range(i18n_key, start, end) for start, end, i18n_key in ranges_data]

    rounded_bmi = round(result.bmi, 1)

    return BMIScaleV1Spec(
        kind="bmi_scale_v1",
        bmi=rounded_bmi,
        min=scale_min,
        max=scale_max,
        ranges=ranges,
        marker=BMIMarkerSpec(value=rounded_bmi),
    )

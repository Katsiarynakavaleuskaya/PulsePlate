"""Nutrition recommendation schemas (Pydantic v2).

RU: Pydantic-схемы для эндпоинтов рекомендаций по питанию.
EN: Pydantic schemas for nutrition recommendation endpoints.

IMPORTANT:
- This module must stay import-safe (no SQLAlchemy, no Base/metadata side-effects).
- Routers may import these schemas at module import time (OpenAPI generation path).
"""

from __future__ import annotations

from math import isfinite
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProfileInput(BaseModel):
    """Reusable profile input for nutrition endpoints.

    RU: Входные данные профиля для эндпоинтов питания.
    EN: Reusable profile input shared across nutrition endpoints.
    """

    age: int = Field(..., ge=18, le=120, description="Age in years (adults only)")
    gender: Literal["female", "male"] = Field(..., description="Biological sex")
    weight_kg: float = Field(..., ge=30.0, le=300.0, description="Body weight in kg")
    height_cm: float = Field(..., ge=100.0, le=250.0, description="Height in cm")
    activity_level: Literal["low", "light", "moderate", "high", "very_high"] = Field(
        ..., description="Physical activity level"
    )


class NutrientRecommendationsResponse(BaseModel):
    """FREE endpoint response: basic nutrient recommendations.

    RU: Ответ для бесплатного эндпоинта рекомендаций по питанию.
    EN: Response for the free nutrient recommendations endpoint.
    """

    kcal_daily: int = Field(..., description="Target daily calories (kcal)")
    macros: dict[str, int] = Field(
        ..., description="Macronutrient targets: protein_g, fat_g, carbs_g, fiber_g"
    )
    water_ml_daily: int = Field(..., description="Daily water intake target (ml)")
    micros: dict[str, float] = Field(..., description="Priority micronutrient targets (WHO/EFSA)")
    activity: dict[str, int] = Field(
        ...,
        description="Activity targets: moderate_aerobic_min, vigorous_aerobic_min, strength_sessions, steps_daily",
    )


class NutrientCoverageItem(BaseModel):
    """Per-nutrient coverage assessment.

    RU: Оценка покрытия одного нутриента.
    EN: Coverage assessment for a single nutrient.
    """

    consumed: float = Field(..., description="Actual consumed amount")
    target: float = Field(..., description="Target amount")
    coverage_percent: float = Field(
        ..., ge=0.0, le=200.0, description="Percentage of target met (capped at 200%)"
    )
    status: Literal["deficient", "adequate", "excess"] = Field(
        ..., description="Coverage status category"
    )
    unit: str = Field(..., description="Unit of measurement (g, mg, etc.)")


class NutrientCoverageSummary(BaseModel):
    """Summary statistics for nutrient coverage.

    RU: Сводная статистика покрытия нутриентов.
    EN: Summary statistics for nutrient coverage scoring.
    """

    total_nutrients: int = Field(..., description="Total nutrients scored")
    adequate_count: int = Field(..., description="Nutrients with adequate coverage")
    deficient_count: int = Field(..., description="Nutrients with deficient coverage")
    excess_count: int = Field(..., description="Nutrients with excess coverage")
    overall_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall nutrition score (0-100)"
    )


class NutrientCoverageRequest(BaseModel):
    """PRO endpoint request: nutrient coverage scoring.

    RU: Запрос для PRO эндпоинта оценки покрытия нутриентов.
    EN: Request for PRO nutrient coverage scoring endpoint.
    """

    profile: ProfileInput
    consumed: dict[str, float] = Field(
        ..., min_length=1, description="Consumed nutrient amounts keyed by nutrient name"
    )

    @field_validator("consumed")
    @classmethod
    def _validate_consumed_values(cls, v: dict[str, float]) -> dict[str, float]:
        bad = [k for k, val in v.items() if (not isfinite(val)) or val < 0]
        if bad:
            raise ValueError(f"consumed values must be finite and >= 0; invalid keys: {bad}")
        return v


class NutrientCoverageResponse(BaseModel):
    """PRO endpoint response: nutrient coverage scoring.

    RU: Ответ для PRO эндпоинта оценки покрытия нутриентов.
    EN: Response for PRO nutrient coverage scoring endpoint.
    """

    coverage: dict[str, NutrientCoverageItem] = Field(
        ..., description="Per-nutrient coverage details"
    )
    summary: NutrientCoverageSummary = Field(..., description="Aggregate coverage statistics")

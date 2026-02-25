"""FREE router: nutrient recommendations.

RU: Бесплатный эндпоинт рекомендаций по питанию.
EN: Free-tier endpoint for basic nutrient recommendations.

Thin adapter: delegates to ``core.recommendations.get_nutrient_recommendations()``.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.schemas.nutrition_recommendations import NutrientRecommendationsResponse

router = APIRouter(tags=["nutrition"])


@router.get(
    "/api/v1/nutrition/recommendations",
    response_model=NutrientRecommendationsResponse,
    summary="Basic nutrient recommendations (FREE)",
)
def get_recommendations(
    age: int = Query(..., ge=1, le=120, description="Age in years"),
    gender: Literal["female", "male"] = Query(..., description="Biological sex"),
    weight_kg: float = Query(..., ge=30.0, le=300.0, description="Body weight in kg"),
    height_cm: float = Query(..., ge=100.0, le=250.0, description="Height in cm"),
    activity_level: Literal["low", "light", "moderate", "high", "very_high"] = Query(
        ..., description="Physical activity level"
    ),
) -> NutrientRecommendationsResponse:
    """Return WHO-based nutrition recommendations for the given profile.

    RU: Возвращает рекомендации по питанию на основе норм ВОЗ.
    EN: Returns personalized nutrition recommendations based on WHO standards.
    """
    from core.recommendations import get_nutrient_recommendations

    result = get_nutrient_recommendations(
        age=age,
        gender=gender,
        weight_kg=weight_kg,
        height_cm=height_cm,
        activity_level=activity_level,
    )
    return NutrientRecommendationsResponse(**result)

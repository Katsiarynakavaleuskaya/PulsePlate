"""PRO router: nutrition insights (coverage scoring).

RU: PRO эндпоинт для оценки покрытия нутриентов.
EN: PRO-tier endpoint for nutrient coverage scoring.

Thin adapter: delegates to ``core.recommendations`` functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from app.middleware.api_tiers import require_pro_tier
from app.schemas.nutrition_recommendations import (
    NutrientCoverageItem,
    NutrientCoverageRequest,
    NutrientCoverageResponse,
    NutrientCoverageSummary,
    ProfileInput,
)

if TYPE_CHECKING:
    from core.targets import Activity, NutrientCoverage, UserProfile

router = APIRouter(
    prefix="/api/v1/pro/nutrition",
    tags=["pro", "nutrition"],
    dependencies=[Depends(require_pro_tier)],
)

_ACTIVITY_MAP: dict[str, Activity] = {
    "low": "sedentary",
    "light": "light",
    "moderate": "moderate",
    "high": "active",
    "very_high": "very_active",
}


def _profile_from_input(inp: ProfileInput) -> UserProfile:
    """Convert Pydantic ProfileInput to core UserProfile dataclass.

    RU: Конвертирует ProfileInput в UserProfile (замороженный датакласс).
    EN: Thin adapter — maps API activity levels to core Activity literals.
    """
    from core.targets import UserProfile as _UserProfile

    return _UserProfile(
        sex=inp.gender,
        age=inp.age,
        weight_kg=inp.weight_kg,
        height_cm=inp.height_cm,
        activity=_ACTIVITY_MAP[inp.activity_level],
        goal="maintain",
    )


@router.post(
    "/coverage",
    response_model=NutrientCoverageResponse,
    summary="Nutrient coverage scoring (PRO)",
)
def score_coverage(req: NutrientCoverageRequest) -> NutrientCoverageResponse:
    """Score nutrient coverage against WHO-based targets.

    RU: Оценивает покрытие нутриентов в рационе относительно целей ВОЗ.
    EN: Scores actual nutrient intake against personalized WHO targets.
    """
    from core.recommendations import build_nutrition_targets, score_nutrient_coverage

    profile = _profile_from_input(req.profile)
    targets = build_nutrition_targets(profile)
    raw_coverage: dict[str, NutrientCoverage] = score_nutrient_coverage(req.consumed, targets)

    # Transform NutrientCoverage dataclasses to schema items
    items: dict[str, NutrientCoverageItem] = {}
    for name, cov in raw_coverage.items():
        items[name] = NutrientCoverageItem(
            consumed=cov.consumed_amount,
            target=cov.target_amount,
            coverage_percent=cov.coverage_percent,
            status=cov.status,
            unit=cov.unit,
        )

    # Build summary
    total = len(items)
    adequate = sum(1 for i in items.values() if i.status == "adequate")
    deficient = sum(1 for i in items.values() if i.status == "deficient")
    excess = sum(1 for i in items.values() if i.status == "excess")
    avg_coverage = sum(i.coverage_percent for i in items.values()) / total if total else 0.0
    overall_score = min(100.0, round(avg_coverage, 1))

    summary = NutrientCoverageSummary(
        total_nutrients=total,
        adequate_count=adequate,
        deficient_count=deficient,
        excess_count=excess,
        overall_score=overall_score,
    )

    return NutrientCoverageResponse(coverage=items, summary=summary)

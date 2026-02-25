"""PRO router: nutrition insights (coverage, deficiency recs, micro targets, safety).

RU: PRO эндпоинты для анализа питания: покрытие, дефициты, микроцели, безопасность.
EN: PRO-tier endpoints for nutrition analysis: coverage, deficiency recs, micro targets, safety.

Thin adapter: delegates to ``core.recommendations`` functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from app.middleware.api_tiers import require_pro_tier
from app.schemas.nutrition_recommendations import (
    DeficiencyRecommendationsRequest,
    DeficiencyRecommendationsResponse,
    MicronutrientDetail,
    MicronutrientTargetsRequest,
    MicronutrientTargetsResponse,
    NutrientCoverageItem,
    NutrientCoverageRequest,
    NutrientCoverageResponse,
    NutrientCoverageSummary,
    ProfileInput,
    SafetyCheckRequest,
    SafetyCheckResponse,
    TargetsSummary,
)

if TYPE_CHECKING:
    from core.targets import Activity, MicronutrientTargets, NutrientCoverage, UserProfile

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
        goal=inp.goal or "maintain",
        diet_flags=set(inp.diet_flags),
        life_stage=inp.life_stage or "adult",
        deficit_pct=inp.deficit_pct,
        surplus_pct=inp.surplus_pct,
        bodyfat=inp.bodyfat,
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


# ---------------------------------------------------------------------------
# Unit map for micronutrient-targets endpoint
# ---------------------------------------------------------------------------

_MICRO_UNIT_MAP: dict[str, str] = {
    "iron_mg": "mg",
    "calcium_mg": "mg",
    "magnesium_mg": "mg",
    "zinc_mg": "mg",
    "potassium_mg": "mg",
    "iodine_ug": "mcg",
    "selenium_ug": "mcg",
    "folate_ug": "mcg",
    "b12_ug": "mcg",
    "vitamin_d_iu": "IU",
    "vitamin_a_ug": "mcg",
    "vitamin_c_mg": "mg",
}


@router.post(
    "/deficiency-recommendations",
    response_model=DeficiencyRecommendationsResponse,
    summary="Food-based deficiency recommendations (PRO)",
)
def deficiency_recommendations(
    req: DeficiencyRecommendationsRequest,
) -> DeficiencyRecommendationsResponse:
    """Generate food-based recommendations for deficient nutrients.

    RU: Формирует рекомендации по продуктам для устранения дефицитов.
    EN: Generates food-first recommendations for nutrients below threshold.
    """
    from core.recommendations import (
        build_nutrition_targets,
        generate_deficiency_recommendations,
        score_nutrient_coverage,
    )

    profile = _profile_from_input(req.profile)
    targets = build_nutrition_targets(profile)
    coverage: dict[str, NutrientCoverage] = score_nutrient_coverage(req.consumed, targets)
    recs = generate_deficiency_recommendations(coverage, profile, lang=req.lang)

    deficient_count = sum(1 for c in coverage.values() if c.status == "deficient")
    profile_summary = (
        f"{profile.sex}, {profile.age}y, {profile.weight_kg}kg, "
        f"{profile.height_cm}cm, {profile.activity}"
    )

    return DeficiencyRecommendationsResponse(
        recommendations=recs,
        deficient_count=deficient_count,
        profile_summary=profile_summary,
    )


@router.post(
    "/micronutrient-targets",
    response_model=MicronutrientTargetsResponse,
    summary="Extended micronutrient targets with ranges (PRO)",
)
def micronutrient_targets(req: MicronutrientTargetsRequest) -> MicronutrientTargetsResponse:
    """Build extended micronutrient targets with min/target/max ranges.

    RU: Расширенные микроцели с диапазонами (мин/цель/макс) на основе ВОЗ.
    EN: Extended micro targets with min/target/max ranges per WHO/EFSA/DRI.
    """
    from core.recommendations import build_micronutrient_targets

    profile = _profile_from_input(req.profile)
    mt: MicronutrientTargets = build_micronutrient_targets(profile)

    nutrients: dict[str, MicronutrientDetail] = {}
    for name, unit in _MICRO_UNIT_MAP.items():
        vals: tuple[float, float, float] = getattr(mt, name)
        nutrients[name] = MicronutrientDetail(
            min=vals[0],
            target=vals[1],
            max=vals[2],
            unit=unit,
            priority=mt.priority_nutrients.get(name),
        )

    return MicronutrientTargetsResponse(
        nutrients=nutrients,
        deficiency_threshold=mt.deficiency_threshold,
    )


@router.post(
    "/safety-check",
    response_model=SafetyCheckResponse,
    summary="Safety validation of nutrition targets (PRO)",
)
def safety_check(req: SafetyCheckRequest) -> SafetyCheckResponse:
    """Validate calculated nutrition targets against safety bounds.

    RU: Проверяет безопасность рассчитанных целей (калории, белок, гидратация).
    EN: Validates safety of calculated targets (calories, protein, hydration).
    """
    from core.recommendations import build_nutrition_targets, validate_targets_safety

    profile = _profile_from_input(req.profile)
    targets = build_nutrition_targets(profile)

    if targets.kcal_daily <= 0:
        protein_pct = 0.0
        warnings = ["Invalid kcal_daily value; protein_pct set to 0.0"]
    else:
        warnings = validate_targets_safety(targets)
        protein_pct = round((targets.macros.protein_g * 4) / targets.kcal_daily * 100, 1)

    return SafetyCheckResponse(
        is_safe=len(warnings) == 0,
        warnings=warnings,
        targets_summary=TargetsSummary(
            kcal_daily=targets.kcal_daily,
            protein_pct=protein_pct,
            water_ml_daily=targets.water_ml_daily,
        ),
    )

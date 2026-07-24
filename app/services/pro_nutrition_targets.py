"""Canonical application service for PRO nutrition targets and nutrient gaps."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from typing import Any, cast

from fastapi import HTTPException, status

import core.recommendations as nutrition_recommendations
import core.targets as nutrition_targets
from app.schemas.premium_contracts import (
    NutrientGapsRequest,
    NutrientGapsResponse,
    WHOTargetsRequest,
    WHOTargetsResponse,
    build_who_targets_ui_labels,
)
from app.services.intervention_trigger_engine import build_targets_next_action
from core.bmr import FALLBACK_BMR_KCAL_PER_KG_PER_DAY
from core.i18n import normalize_lang
from core.nutrition_utils import alias_micros, clamp_daily_kcal, ensure_priority_micros
from core.utils import get_activity_factor

logger = logging.getLogger(__name__)

WHO_TARGETS_UNAVAILABLE_DETAIL = "WHO nutrition targets feature not available"
WHO_TARGETS_CALCULATION_FAILED_DETAIL = "WHO targets calculation failed"
WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL = "WHO targets safety validation failed"
INVALID_TARGETS_INPUT_DETAIL = "Invalid nutrition targets input"
NUTRIENT_GAPS_UNAVAILABLE_DETAIL = "Nutrient gap analysis feature not available"
NUTRITION_TARGETS_UNAVAILABLE_DETAIL = "Nutrition targets calculation feature not available"
NUTRIENT_GAPS_FAILED_DETAIL = "Nutrient gap analysis failed"
INVALID_NUTRIENT_GAPS_INPUT_DETAIL = "Invalid nutrient gap input"

LifeStageWarningFactory = Callable[
    [int, nutrition_targets.LifeStage, str],
    list[dict[str, str]],
]
TargetsBuilder = Callable[
    [nutrition_targets.UserProfile],
    nutrition_targets.NutritionTargets,
]
NutrientGapsAnalyzer = Callable[
    [nutrition_targets.NutritionTargets, dict[str, float]],
    dict[str, dict[str, Any]],
]

_DEFAULT_LIFE_STAGE_MESSAGES: dict[str, dict[str, str]] = {
    "teen": {
        "ru": "Подростковая группа: используйте специализированные нормы.",
        "en": "Teen life stage: use age-appropriate references.",
        "es": "Etapa adolescente: use referencias apropiadas para la edad.",
    },
    "pregnant": {
        "ru": "Беременность: нормы отличаются; обратитесь к специализированным рекомендациям.",
        "en": "Pregnancy: requirements differ; consult specialized guidelines.",
        "es": "Embarazo: los requisitos difieren; consulte guías especializadas.",
    },
    "lactating": {
        "ru": "Лактация: повышенные потребности в нутриентах.",
        "en": "Lactation: increased nutrient requirements.",
        "es": "Lactancia: requisitos de nutrientes aumentados.",
    },
    "elderly": {
        "ru": "51+: возможна иная потребность в микронутриентах.",
        "en": "Age 51+: micronutrient needs may differ.",
        "es": "51+: las necesidades de micronutrientes pueden diferir.",
    },
    "child": {
        "ru": "Детский возраст: используйте педиатрические нормы.",
        "en": "Child age: use pediatric references.",
        "es": "Edad infantil: use referencias pediátricas.",
    },
}


def _build_user_profile(req: WHOTargetsRequest) -> nutrition_targets.UserProfile:
    """Project the stable API request into the canonical core profile."""

    return nutrition_targets.UserProfile(
        sex=req.sex,
        age=req.age,
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        activity=req.activity,
        goal=req.goal,
        deficit_pct=req.deficit_pct,
        surplus_pct=req.surplus_pct,
        bodyfat=req.bodyfat,
        diet_flags=set(req.diet_flags or []),
        life_stage=req.life_stage,
    )


def _validate_consumed_nutrients(consumed_nutrients: dict[str, float]) -> None:
    """Reject negative or non-finite intake before invoking core calculations."""

    if any(not (math.isfinite(value) and value >= 0) for value in consumed_nutrients.values()):
        logger.warning("Rejected invalid consumed nutrient input")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_NUTRIENT_GAPS_INPUT_DETAIL,
        )


def _resolve_nutrient_gaps_analyzer() -> NutrientGapsAnalyzer | None:
    """Resolve the optional gaps backend without coupling targets startup to it."""

    from core.menu_engine import analyze_nutrient_gaps

    return cast(NutrientGapsAnalyzer | None, analyze_nutrient_gaps)


def fallback_targets_response(
    req: WHOTargetsRequest,
    *,
    reason: str,
    include_extra_iodine: bool = False,
    life_stage_warning_factory: LifeStageWarningFactory | None = None,
    include_generic_life_stage_note: bool = False,
) -> WHOTargetsResponse:
    """Build the established bounded response when target calculation is unavailable."""

    warning_factory = life_stage_warning_factory or nutrition_targets._life_stage_warnings
    normalized_lang = normalize_lang(req.lang)

    base_bmr = FALLBACK_BMR_KCAL_PER_KG_PER_DAY * req.weight_kg
    activity_factor = get_activity_factor(req.activity)
    tdee = int(base_bmr * activity_factor)

    if req.goal == "loss":
        pct = req.deficit_pct if req.deficit_pct is not None else 15.0
        kcal_daily = int(tdee * (1.0 - pct / 100.0))
    elif req.goal == "gain":
        pct = req.surplus_pct if req.surplus_pct is not None else 10.0
        kcal_daily = int(tdee * (1.0 + pct / 100.0))
    else:
        kcal_daily = tdee
    kcal_daily = clamp_daily_kcal(kcal_daily)

    protein_g = int(round(1.6 * req.weight_kg))
    fat_g = int(round(0.9 * req.weight_kg))
    used_kcal = protein_g * 4 + fat_g * 9
    carbs_g = max(0, int(round((kcal_daily - used_kcal) / 4)))

    priority_micros: dict[str, float] = {
        "iron_mg": 8.0 if req.sex == "male" else 18.0,
        "calcium_mg": 1000.0,
        "vitamin_c_mg": 90.0 if req.sex == "male" else 75.0,
        "folate_ug": 400.0,
        "vitamin_d_iu": 600.0,
        "magnesium_mg": 400.0,
        "potassium_mg": 3500.0,
        "b12_ug": 2.4,
    }
    if include_extra_iodine:
        priority_micros["iodine_ug"] = 150.0
    priority_micros = ensure_priority_micros(alias_micros(priority_micros))

    life_stage_code = (req.life_stage or "").lower()
    factory_warnings: list[dict[str, str]] = []
    try:
        factory_warnings = warning_factory(req.age, req.life_stage, normalized_lang)
    except Exception:
        logger.exception("Life-stage warning generation failed; using stable fallback copy")

    if not factory_warnings and life_stage_code in _DEFAULT_LIFE_STAGE_MESSAGES:
        message_map = _DEFAULT_LIFE_STAGE_MESSAGES[life_stage_code]
        factory_warnings = [
            {
                "code": life_stage_code,
                "message": message_map.get(normalized_lang, message_map["en"]),
            }
        ]

    warnings = list(factory_warnings)
    if req.life_stage in ("pregnant", "lactating"):
        if not warnings and include_generic_life_stage_note:
            warnings.append(
                {
                    "code": "life_stage",
                    "message": "Special nutrition considerations apply",
                }
            )

    special_life_stage = life_stage_code in {
        "pregnant",
        "lactating",
        "teen",
        "child",
        "elderly",
    }
    if special_life_stage and reason:
        has_life_stage_warning = any(warning.get("code") == "life_stage" for warning in warnings)
        if not has_life_stage_warning:
            warnings.append({"code": "life_stage", "message": reason})

    next_best_action = build_targets_next_action(kcal_daily=kcal_daily)
    return WHOTargetsResponse(
        kcal_daily=kcal_daily,
        macros={
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carbs_g": carbs_g,
            "fiber_g": 25,
        },
        water_ml=int(req.weight_kg * 35),
        priority_micros=priority_micros,
        activity_weekly={
            "moderate_aerobic_min": 150,
            "strength_sessions": 2,
            "steps_daily": 8000,
        },
        calculation_date=time.strftime("%Y-%m-%d"),
        warnings=warnings,
        ui_labels=build_who_targets_ui_labels(req.lang),
        next_best_action=next_best_action,
    )


def validate_targets_safety_warnings(
    targets: nutrition_targets.NutritionTargets,
) -> list[str]:
    """Run the shared required safety validator and fail closed on invalid behavior."""

    try:
        warnings = nutrition_recommendations.validate_targets_safety(targets)
    except Exception:
        logger.exception("WHO targets safety validation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL,
        ) from None

    if not isinstance(warnings, list) or not all(isinstance(warning, str) for warning in warnings):
        logger.error("WHO targets safety validator returned an invalid response shape")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL,
        )
    return warnings


def generate_who_targets_response(
    req: WHOTargetsRequest,
    *,
    allow_backend_fallback: bool = True,
    targets_builder: TargetsBuilder | None = None,
) -> WHOTargetsResponse:
    """Generate canonical WHO targets with bounded fallback and safe errors."""

    normalized_lang = normalize_lang(req.lang)
    try:
        builder = (
            targets_builder
            if targets_builder is not None
            else nutrition_recommendations.build_nutrition_targets
        )
        if not callable(builder):
            if not allow_backend_fallback:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=WHO_TARGETS_UNAVAILABLE_DETAIL,
                )
            return fallback_targets_response(
                req,
                reason=(
                    "WHO targets fallback used because the calculation backend " "is unavailable."
                ),
                include_generic_life_stage_note=True,
            )

        try:
            profile = _build_user_profile(req)
        except ValueError:
            logger.exception("Invalid WHO targets profile input")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_TARGETS_INPUT_DETAIL,
            ) from None

        try:
            targets = builder(profile)
        except ValueError:
            logger.warning(
                "WHO target calculation rejected the profile; using bounded fallback",
                exc_info=True,
            )
            return fallback_targets_response(
                req,
                reason="WHO targets fallback used because profile validation failed.",
                include_extra_iodine=True,
            )
        except ImportError:
            logger.warning("WHO target calculation dependency is unavailable", exc_info=True)
            if not allow_backend_fallback:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=WHO_TARGETS_UNAVAILABLE_DETAIL,
                ) from None
            return fallback_targets_response(
                req,
                reason=(
                    "WHO targets fallback used because the calculation backend " "is unavailable."
                ),
                include_generic_life_stage_note=True,
            )
        except Exception:
            logger.exception("Unexpected WHO target calculation failure")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=WHO_TARGETS_CALCULATION_FAILED_DETAIL,
            ) from None

        life_stage_warnings = nutrition_targets._life_stage_warnings(
            age=req.age,
            life_stage=req.life_stage,
            lang=normalized_lang,
        )
        for warning in validate_targets_safety_warnings(targets):
            life_stage_warnings.append({"code": "safety", "message": warning})

        kcal_daily = clamp_daily_kcal(targets.kcal_daily)
        return WHOTargetsResponse(
            kcal_daily=kcal_daily,
            macros={
                "protein_g": targets.macros.protein_g,
                "fat_g": targets.macros.fat_g,
                "carbs_g": targets.macros.carbs_g,
                "fiber_g": targets.macros.fiber_g,
            },
            water_ml=targets.water_ml_daily,
            priority_micros=ensure_priority_micros(
                alias_micros(dict(targets.micros.get_priority_nutrients()))
            ),
            activity_weekly={
                "moderate_aerobic_min": targets.activity.moderate_aerobic_min,
                "strength_sessions": targets.activity.strength_sessions,
                "steps_daily": targets.activity.steps_daily,
            },
            calculation_date=targets.calculation_date,
            warnings=life_stage_warnings,
            ui_labels=build_who_targets_ui_labels(req.lang),
            next_best_action=build_targets_next_action(kcal_daily=kcal_daily),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected WHO targets response failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=WHO_TARGETS_CALCULATION_FAILED_DETAIL,
        ) from None


def analyze_nutrient_gaps_response(req: NutrientGapsRequest) -> NutrientGapsResponse:
    """Analyze nutrient gaps with direct core ownership and localized food guidance."""

    try:
        _validate_consumed_nutrients(req.consumed_nutrients)

        analyzer = _resolve_nutrient_gaps_analyzer()
        if not callable(analyzer):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=NUTRIENT_GAPS_UNAVAILABLE_DETAIL,
            )

        builder = nutrition_recommendations.build_nutrition_targets
        if not callable(builder):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=NUTRITION_TARGETS_UNAVAILABLE_DETAIL,
            )

        try:
            profile = _build_user_profile(req.user_profile)
        except ValueError:
            logger.exception("Invalid nutrient gap profile input")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_NUTRIENT_GAPS_INPUT_DETAIL,
            ) from None

        try:
            targets = builder(profile)
        except ValueError:
            logger.exception("Nutrient target calculation rejected the profile")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_NUTRIENT_GAPS_INPUT_DETAIL,
            ) from None

        gaps = analyzer(targets, req.consumed_nutrients)
        coverage = nutrition_recommendations.score_nutrient_coverage(
            req.consumed_nutrients,
            targets,
        )
        food_recommendations = nutrition_recommendations.generate_deficiency_recommendations(
            coverage,
            profile,
            normalize_lang(req.user_profile.lang),
        )

        adequate_nutrients = sum(
            1 for nutrient in coverage.values() if nutrient.coverage_percent >= 80
        )
        adherence_score = adequate_nutrients / len(coverage) * 100 if coverage else 0.0
        return NutrientGapsResponse(
            gaps=gaps,
            food_recommendations=food_recommendations,
            adherence_score=round(adherence_score, 1),
        )
    except HTTPException:
        raise
    except ImportError:
        logger.exception("Nutrient gap analysis dependency is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=NUTRIENT_GAPS_UNAVAILABLE_DETAIL,
        ) from None
    except Exception:
        logger.exception("Unexpected nutrient gap analysis failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=NUTRIENT_GAPS_FAILED_DETAIL,
        ) from None

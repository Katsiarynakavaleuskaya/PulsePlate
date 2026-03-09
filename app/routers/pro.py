"""
PRO Tier Router

RU: Роутер для PRO уровня подписки - продвинутые функции питания.
EN: Router for PRO subscription tier - advanced nutrition features.

This router provides PRO tier endpoints optimized for iOS mobile app integration.
All endpoints require PRO tier API key validation via require_pro_tier middleware.

Endpoints:
- /api/v1/pro/meal/weekly - Weekly meal plan (macros only)
- /api/v1/pro/nutrition/targets - WHO-based nutrition goals
- /api/v1/pro/nutrition/daily - Daily nutrition tracking (Plate view)
"""

import logging
from datetime import date as Date
from typing import Any, Dict, List, Literal, Optional, Union, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.middleware.api_tiers import require_pro_tier
from app.schemas.nutrition_targets import TargetsIn
from app.schemas.weekly_plan import (
    WeeklyMealPlanResponse,
    require_weekly_plan_payload_shape,
    normalize_weekly_plan_payload,
)
from app.services.weekly_plan.pipeline import run_weekly_pipeline_guarded

from core.food_db_new import FoodDB
from core.meal_i18n import Language, translate_nutrition_segment
from core.recipe_db_new import RecipeDB
from core.recommendations import build_nutrition_targets
from core.targets import UserProfile
from core.weekly_plan_new import build_week

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pro", tags=["pro"])

# --- Plate serving conversion constants ---
# RU: Конвертация грамм макросов в "servings" для визуализации тарелки.
# EN: Convert macro grams into approximate servings for plate visualization.
PROTEIN_GRAMS_PER_SERVING = 25.0
CARBS_GRAMS_PER_SERVING = 30.0
FATS_GRAMS_PER_SERVING = 10.0

# RU: Минимальная рекомендация ВОЗ по овощам (в servings).
# EN: WHO minimum daily recommendation for vegetables (servings).
VEGETABLES_SERVINGS_WHO_STANDARD = 4.0

# RU/EN: Централизованная конфигурация сегментов (цвет/иконка)
SEGMENT_STYLE: Dict[str, Dict[str, str]] = {
    "vegetables": {"color": "green", "icon": "leaf.fill"},
    "protein": {"color": "red", "icon": "fish.fill"},
    "carbs": {"color": "orange", "icon": "grain.fill"},
    "fats": {"color": "yellow", "icon": "drop.fill"},
}


# Cache database instances for performance
_food_db_cache: Optional[FoodDB] = None
_recipe_db_cache: Optional[RecipeDB] = None
_food_db_cache_source: object | None = None
_recipe_db_cache_source: object | None = None


def get_food_db() -> FoodDB:
    """Get cached FoodDB instance."""
    global _food_db_cache, _food_db_cache_source
    if _food_db_cache is None or _food_db_cache_source is not FoodDB:
        _food_db_cache = FoodDB("data/food_db_new.csv")
        _food_db_cache_source = FoodDB
    return _food_db_cache


def get_recipe_db() -> RecipeDB:
    """Get cached RecipeDB instance."""
    global _recipe_db_cache, _recipe_db_cache_source
    if _recipe_db_cache is None or _recipe_db_cache_source is not RecipeDB:
        fooddb = get_food_db()
        _recipe_db_cache = RecipeDB("data/recipes_new.csv", fooddb)
        _recipe_db_cache_source = RecipeDB
    return _recipe_db_cache


class ProWeekPlanRequest(BaseModel):
    """Request model for weekly meal plan generation.

    Supports two modes:
    - Mode A: Provide ready targets
    - Mode B: Quick profile (fallback)
    """

    model_config = ConfigDict(title="ProWeekPlanRequest")

    # Mode A: Provide ready targets
    targets: Optional[TargetsIn] = None
    # Mode B: Quick profile (fallback)
    sex: Optional[Literal["female", "male"]] = None
    age: Optional[int] = Field(None, gt=10, lt=90)
    height_cm: Optional[int] = Field(None, gt=100, lt=220)
    weight_kg: Optional[int] = Field(None, gt=30, lt=300)
    activity: Optional[Literal["sedentary", "light", "moderate", "active", "very_active"]] = (
        "moderate"
    )
    goal: Optional[Literal["loss", "maintain", "gain"]] = "maintain"
    diet_flags: List[str] = Field(default_factory=list)
    lang: Language = "en"


ProWeekPlanResponse = WeeklyMealPlanResponse


class NutritionSegmentData(BaseModel):
    """Single nutrition segment (e.g., Vegetables, Protein, Carbs, Fats)."""

    name: str = Field(..., description="Segment name (e.g., 'Vegetables')")
    current_value: float = Field(..., ge=0.0, description="Current servings consumed")
    target_value: float = Field(..., ge=0.0, description="Target servings for the day")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of plate (0-100)")
    color: str = Field(..., description="Color identifier (e.g., 'green', 'red')")
    icon: str = Field(..., description="SF Symbol icon name (e.g., 'leaf.fill')")


class DailyGoals(BaseModel):
    """Daily nutrition goals."""

    vegetables: float = Field(..., ge=0.0, description="Target vegetable servings")
    protein: float = Field(..., ge=0.0, description="Target protein servings")
    carbs: float = Field(..., ge=0.0, description="Target carbohydrate servings")
    fats: float = Field(..., ge=0.0, description="Target fat servings")


class DailyNutritionResponse(BaseModel):
    """Daily nutrition data for Plate view."""

    date: str = Field(..., description="Date in ISO 8601 format (YYYY-MM-DD)")
    segments: List[NutritionSegmentData] = Field(
        ..., description="Nutrition segments for plate visualization"
    )
    total_progress: float = Field(..., ge=0, le=1, description="Overall daily progress (0.0-1.0)")
    daily_goals: DailyGoals = Field(..., description="Daily nutrition goals")


def _missing_profile_detail(field: str) -> str:
    """Generate error detail with legacy prefix + field-specific hint.

    TODO: Add i18n support via t(lang, "translation_key") for multilingual error messages.
    """
    return f"Missing user profile data (Missing required field: {field})"


def _is_complete_targets(d: Dict[str, Any]) -> bool:
    """Check if targets dict has all required keys and non-empty micro/macros.

    Note: activity_week is optional but validated if present.
    """
    required_keys = {"kcal", "macros", "micro", "water_ml"}
    if not required_keys.issubset(d.keys()):
        return False
    if not isinstance(d.get("macros"), dict):
        return False
    if not isinstance(d.get("micro"), dict):
        return False
    # If activity_week is present, it must be a dict
    if "activity_week" in d and d.get("activity_week") is not None:
        if not isinstance(d["activity_week"], dict):
            return False
    # micro must not be empty, otherwise core may produce unexpected results
    if not d.get("micro"):
        return False
    # macros must not be empty, for consistency with micro validation
    if not d.get("macros"):
        return False
    return True


# TODO(#286): Deduplicate estimate_targets_minimal by moving it into app/services/nutrition_targets.py
# Keep parity between /api/v1/pro/meal/weekly and deprecated /api/v1/premium/plan/week-flexible.
def estimate_targets_minimal(
    sex: Literal["female", "male"],
    age: int,
    height_cm: float,
    weight_kg: float,
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"],
    goal: Literal["loss", "maintain", "gain"],
) -> Dict[str, Any]:
    """Estimate nutrition targets from user profile.

    WARNING: This function is duplicated in premium_week.py to maintain backward compatibility.
    Any changes here MUST be mirrored in premium_week.py until extraction is complete.

    Args:
        sex: Biological sex
        age: Age in years
        height_cm: Height in centimeters
        weight_kg: Weight in kilograms
        activity: Activity level
        goal: Nutrition goal

    Returns:
        Dictionary with nutrition targets (kcal, macros, micro, water, activity)
    """
    # Create a UserProfile object
    profile = UserProfile(
        sex=sex,
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity=activity,
        goal=goal,
    )

    # Build nutrition targets using existing WHO-based system
    targets = build_nutrition_targets(profile)

    # Convert to the format expected by the weekly plan generator
    return {
        "kcal": targets.kcal_daily,
        "macros": {
            "protein_g": targets.macros.protein_g,
            "fat_g": targets.macros.fat_g,
            "carbs_g": targets.macros.carbs_g,
            "fiber_g": targets.macros.fiber_g,
        },
        "micro": targets.micros.get_priority_nutrients(),
        "water_ml": targets.water_ml_daily,
        "activity_week": {
            "moderate_aerobic_min": targets.activity.moderate_aerobic_min,
            "vigorous_aerobic_min": targets.activity.vigorous_aerobic_min,
            "strength_sessions": targets.activity.strength_sessions,
            "steps_daily": targets.activity.steps_daily,
        },
    }


@router.post(
    "/meal/weekly",
    response_model=ProWeekPlanResponse,
    dependencies=[Depends(require_pro_tier)],
    summary="Generate weekly meal plan (PRO tier)",
    description="""
    Generate weekly meal plan with PRO tier features.

    RU: Генерация недельного плана питания с функциями PRO уровня.
    EN: Generate weekly meal plan with PRO tier features.

    Requires: PRO tier API key in X-API-Key header

    Features:
    - WHO-based nutrition targets
    - Macro and micronutrient planning
    - Dietary restrictions support
    - Weekly shopping list
    - Cost estimation
    """,
)
async def generate_week_plan(req: ProWeekPlanRequest) -> Union[ProWeekPlanResponse, JSONResponse]:
    """Generate weekly meal plan with PRO tier features.

    Args:
        req: ProWeekPlanRequest with targets or user profile

    Returns:
        ProWeekPlanResponse with daily menus, coverage, shopping list, and metrics

    Raises:
        HTTPException: 400 if profile data is missing or invalid
    """
    # Get cached database instances
    fooddb = get_food_db()
    recipedb = get_recipe_db()

    # Get targets (treat partial/empty targets as "missing" and fall back to profile derivation)
    targets_from_request: Dict[str, Any] = (
        req.targets.model_dump(exclude_none=True) if req.targets is not None else {}
    )

    if _is_complete_targets(targets_from_request):
        targets: Dict[str, Any] = targets_from_request
    else:
        # Fallback: derive from profile, otherwise 400 (DRY error messages with helper)
        if req.sex is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("sex"))
        if req.age is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("age"))
        if req.height_cm is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("height_cm"))
        if req.weight_kg is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("weight_kg"))
        # activity/goal have defaults but can be explicitly set to null
        if req.activity is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("activity"))
        if req.goal is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("goal"))

        # After all None checks above, types are narrowed to non-None
        targets = estimate_targets_minimal(
            sex=req.sex,
            age=req.age,
            height_cm=float(req.height_cm),
            weight_kg=float(req.weight_kg),
            activity=req.activity,
            goal=req.goal,
        )

    # Hard guard: never pass None/malformed targets to core
    if not isinstance(targets, dict):
        raise HTTPException(status_code=400, detail="Unable to derive targets")
    if not _is_complete_targets(targets):
        raise HTTPException(status_code=400, detail="Unable to derive targets")

    # Build week (generation stage) + postprocess (pipeline with ordering guard)
    from core.menu_engine_new import PlateDayTargets

    # Wrap ProWeekPlanResponse constructor to match postprocess_fn signature
    def _postprocess_week(week: Dict[str, Any]) -> ProWeekPlanResponse:
        validated_week = require_weekly_plan_payload_shape(week)
        normalized_week = normalize_weekly_plan_payload(validated_week)
        return ProWeekPlanResponse(**normalized_week)

    result = run_weekly_pipeline_guarded(
        generation_fn=build_week,
        postprocess_fn=_postprocess_week,
        generation_kwargs={
            "targets": cast(PlateDayTargets, targets),
            "diet_flags": req.diet_flags,
            "lang": req.lang,
            "fooddb": fooddb,
            "recipedb": recipedb,
        },
        postprocess_kwargs={},
        generation_map_error=lambda _e: ("weekly_generation_failed", "Failed to generate plan"),
        generation_default_code="weekly_generation_failed",
        postprocess_map_error=lambda _e: (
            "weekly_postprocess_failed",
            "Failed to build weekly plan response",
        ),
        postprocess_default_code="weekly_postprocess_failed",
        generation_debug_ctx={
            "router": "pro",
            "path": "/api/v1/pro/meal/weekly",
        },
        postprocess_debug_ctx={
            "router": "pro",
            "path": "/api/v1/pro/meal/weekly",
        },
    )

    # Pipeline returns either error envelope or postprocess result
    if isinstance(result, dict) and result.get("status") == "error":
        # IMPORTANT: bypass response_model validation
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=result)

    if not isinstance(result, ProWeekPlanResponse):
        raise TypeError(
            "Expected ProWeekPlanResponse from weekly pipeline, "
            f"got type={type(result).__name__} value={result!r}"
        )
    return result


@router.get(
    "/nutrition/daily",
    response_model=DailyNutritionResponse,
    dependencies=[Depends(require_pro_tier)],
    summary="Get daily nutrition data (PRO tier)",
    description="""
    Get daily nutrition tracking data for Plate view based on WHO targets.

    RU: Получить данные по питанию за день для визуализации тарелки на основе таргетов ВОЗ.
    EN: Get daily nutrition tracking data for Plate view based on WHO targets.

    Requires: PRO tier API key in X-API-Key header

    Features:
    - WHO/USDA-based personalized targets
    - Plate segment visualization
    - Overall progress tracking

    Query Parameters:
    - date: Date in YYYY-MM-DD format (required)
    - sex: Biological sex (required)
    - age: Age in years (required)
    - height_cm: Height in centimeters (required)
    - weight_kg: Weight in kilograms (required)
    - activity: Activity level (optional, default: moderate)
    - goal: Nutrition goal (optional, default: maintain)
    - lang: Language for localized segment names (optional, default: en)

    Note: Current consumption values (current_value) are 0.0 until meal logging is implemented.
    """,
)
async def get_daily_nutrition(
    date_str: str = Query(
        ...,
        alias="date",
        description="Date in ISO 8601 format (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    # RU: Обязательные параметры профиля пользователя
    # EN: Required user profile parameters
    sex: Literal["female", "male"] = Query(..., description="Biological sex"),
    age: int = Query(..., ge=10, le=100, description="Age in years (10-100 inclusive)"),
    height_cm: float = Query(..., gt=100, lt=250, description="Height in centimeters"),
    weight_kg: float = Query(..., gt=30, lt=300, description="Weight in kilograms"),
    # RU: Опциональные параметры с разумными дефолтами
    # EN: Optional parameters with sensible defaults
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = Query(
        "moderate", description="Activity level"
    ),
    goal: Literal["loss", "maintain", "gain"] = Query("maintain", description="Nutrition goal"),
    # RU: Язык интерфейса для локализованных названий сегментов
    # EN: Interface language for localized segment names
    lang: Language = Query("en", description="Language for localized content"),
) -> DailyNutritionResponse:
    """Get daily nutrition data for Plate visualization using WHO targets engine.

    RU: Получить данные питания за день с использованием WHO/USDA таргетов.
    EN: Get daily nutrition data using WHO/USDA targets engine.

    Args:
        date_str: Date string in YYYY-MM-DD format
        sex: Biological sex (female/male)
        age: Age in years (10-100 inclusive)
        height_cm: Height in centimeters (100-250)
        weight_kg: Weight in kilograms (30-300)
        activity: Activity level (sedentary/light/moderate/active/very_active)
        goal: Nutrition goal (loss/maintain/gain)
        lang: Language for localized segment names (en/ru/es)

    Returns:
        DailyNutritionResponse with WHO-based targets and segments

    Raises:
        HTTPException: 400 if date format is invalid or profile validation fails

    Note:
        Current intake values (current_value, total_progress) are 0.0 until
        meal logging/HealthKit integration is implemented. Targets are calculated
        using WHO/USDA/EFSA evidence-based recommendations.
    """
    # Validate date format
    # RU: Валидация формата даты
    # EN: Validate date format
    try:
        Date.fromisoformat(date_str)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid date format: {date_str}. Expected YYYY-MM-DD"
        ) from e

    # Build user profile for WHO targets calculation
    # RU: Создание профиля пользователя для расчёта WHO таргетов
    # EN: Build user profile for WHO targets calculation
    try:
        profile = UserProfile(
            sex=sex,
            age=age,
            height_cm=height_cm,
            weight_kg=weight_kg,
            activity=activity,
            goal=goal,
        )
    except ValueError as e:
        # Log validation details for debugging
        # RU: Логируем детали валидации для отладки
        # EN: Log validation details for debugging
        logger.warning("Invalid user profile for daily nutrition: %s", str(e))
        # Return generic error message to client (avoid info leak)
        # RU: Возвращаем общее сообщение об ошибке клиенту (избегаем утечки информации)
        # EN: Return generic error message to client (avoid info leak)
        raise HTTPException(status_code=400, detail="Invalid user profile") from e

    # Calculate WHO-based nutrition targets
    # RU: Расчёт целевых значений питания на основе рекомендаций ВОЗ
    # EN: Calculate WHO-based nutrition targets
    try:
        targets = build_nutrition_targets(profile)
    except Exception as e:
        # Log internal error details for debugging
        # RU: Логируем внутренние детали ошибки для отладки
        # EN: Log internal error details for debugging
        logger.exception("Failed to calculate nutrition targets for profile: %s", profile)
        # Return generic error message to client (avoid info leak)
        # RU: Возвращаем общее сообщение об ошибке клиенту (избегаем утечки информации)
        # EN: Return generic error message to client (avoid info leak)
        raise HTTPException(status_code=500, detail="Failed to calculate nutrition targets") from e

    # Convert WHO targets to Plate segments using conversion constants
    # RU: Преобразование WHO таргетов в сегменты тарелки с использованием констант
    # EN: Convert WHO targets to Plate segments using conversion constants
    vegetables_servings = VEGETABLES_SERVINGS_WHO_STANDARD
    protein_servings = round(targets.macros.protein_g / PROTEIN_GRAMS_PER_SERVING, 1)
    carbs_servings = round(targets.macros.carbs_g / CARBS_GRAMS_PER_SERVING, 1)
    fats_servings = round(targets.macros.fat_g / FATS_GRAMS_PER_SERVING, 1)

    # Calculate percentages for visual plate representation
    # RU: Расчёт процентов для визуализации тарелки
    # EN: Calculate percentages for visual plate representation
    total_servings = vegetables_servings + protein_servings + carbs_servings + fats_servings

    # RU: total_servings не должен быть 0 (vegetables_servings=4.0), но страхуемся от деления на 0
    # EN: total_servings should never be 0 (vegetables_servings=4.0), but guard against division by zero
    denom = total_servings if total_servings > 0 else 1.0

    veg_pct = (vegetables_servings / denom) * 100
    protein_pct = (protein_servings / denom) * 100
    carbs_pct = (carbs_servings / denom) * 100
    fats_pct = (fats_servings / denom) * 100

    # Build segments using centralized configuration and i18n
    # RU: Формирование сегментов с использованием централизованной конфигурации и i18n
    # EN: Build segments using centralized configuration and i18n
    segments_data = [
        ("vegetables", vegetables_servings, round(veg_pct, 1)),
        ("protein", protein_servings, round(protein_pct, 1)),
        ("carbs", carbs_servings, round(carbs_pct, 1)),
        ("fats", fats_servings, round(fats_pct, 1)),
    ]

    return DailyNutritionResponse(
        date=date_str,
        segments=[
            NutritionSegmentData(
                name=translate_nutrition_segment(lang, key),
                current_value=0.0,  # TODO: Integrate with meal logging
                target_value=target,
                percentage=pct,
                color=SEGMENT_STYLE[key]["color"],
                icon=SEGMENT_STYLE[key]["icon"],
            )
            for key, target, pct in segments_data
        ],
        total_progress=0.0,  # TODO: Calculate from actual meal logging
        daily_goals=DailyGoals(
            vegetables=vegetables_servings,
            protein=protein_servings,
            carbs=carbs_servings,
            fats=fats_servings,
        ),
    )

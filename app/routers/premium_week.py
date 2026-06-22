"""
Premium Week Plan Router

RU: Роутер для генерации недельного плана питания.
EN: Router for generating weekly meal plans.

⚠️ DEPRECATED: This router is deprecated. Use app.routers.pro instead.
All endpoints in this router are deprecated and will be removed in v2.0.
Please migrate to /api/v1/pro/* endpoints.
"""

import logging
from threading import Event
from typing import Any, Dict, List, Literal, Optional, TypeAlias, Union, cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.middleware.api_tiers import require_pro_tier
from app.schemas.nutrition_targets import TargetsIn
from app.schemas.weekly_plan import (
    WeeklyMealPlanResponse,
    require_weekly_plan_payload_shape,
    normalize_weekly_plan_payload,
)
from app.services import nutrition_targets as nutrition_targets_service
from app.services.intervention_trigger_engine import build_weekly_plan_next_action
from app.services.weekly_plan.pipeline import run_weekly_pipeline_guarded

from core.food_db_new import FoodDB
from core.meal_i18n import Language
from core.recipe_db_new import RecipeDB
from core.weekly_plan_new import build_week

router = APIRouter(prefix="/api/v1/premium", tags=["premium"])

# Deprecation warning logged only once to avoid log spam (thread-safe)
_deprecation_logged = Event()

logger = logging.getLogger(__name__)

# Cache database instances for performance (shared with pro.py pattern)
_premium_food_db_cache: Optional[FoodDB] = None
_premium_recipe_db_cache: Optional[RecipeDB] = None
_premium_food_db_cache_source: object | None = None
_premium_recipe_db_cache_source: object | None = None
_premium_recipe_db_food_source: object | None = None


def _get_food_db() -> FoodDB:
    """Get cached FoodDB instance for premium router."""
    global _premium_food_db_cache, _premium_food_db_cache_source
    if _premium_food_db_cache is None or _premium_food_db_cache_source is not FoodDB:
        _premium_food_db_cache = FoodDB("data/food_db_new.csv")
        _premium_food_db_cache_source = FoodDB
    return _premium_food_db_cache


def _get_recipe_db() -> RecipeDB:
    """Get cached RecipeDB instance for premium router."""
    global _premium_recipe_db_cache, _premium_recipe_db_cache_source, _premium_recipe_db_food_source
    fooddb = _get_food_db()
    if (
        _premium_recipe_db_cache is None
        or _premium_recipe_db_cache_source is not RecipeDB
        or _premium_recipe_db_food_source is not fooddb
    ):
        _premium_recipe_db_cache = RecipeDB("data/recipes_new.csv", fooddb)
        _premium_recipe_db_cache_source = RecipeDB
        _premium_recipe_db_food_source = fooddb
    return _premium_recipe_db_cache


class PremiumWeekPlanRequest(BaseModel):
    # режим A: передают готовые targets
    targets: Optional[TargetsIn] = None
    # режим B: быстрый профиль (fallback)
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

    model_config = ConfigDict(title="PremiumWeekPlanRequest")


PremiumWeekPlanResponse: TypeAlias = WeeklyMealPlanResponse


def _missing_profile_detail(field: str) -> str:
    """Generate error detail with legacy prefix + field-specific hint.

    TODO: Add i18n support via t(lang, "translation_key") for multilingual error messages.
    """
    return f"Missing user profile data (Missing required field: {field})"


@router.post(
    "/plan/week-flexible",
    response_model=PremiumWeekPlanResponse,
    dependencies=[Depends(require_pro_tier)],
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/meal/weekly",
        "x-migration-path": "Migrate to /api/v1/pro/meal/weekly (same contract)",
    },
    summary="[DEPRECATED] Generate weekly meal plan",
    description="""
    ⚠️ **DEPRECATED**: This endpoint is deprecated and will be removed in v2.0.

    Please use `/api/v1/pro/meal/weekly` instead.

    Migration guide:
    - Update your API client to use `/api/v1/pro/meal/weekly`
    - Request/response format remains the same
    - API key validation remains the same (PRO tier required)

    Original description:
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
async def generate_week_plan(
    req: PremiumWeekPlanRequest,
) -> Union[PremiumWeekPlanResponse, JSONResponse]:
    """
    [DEPRECATED] Generate weekly meal plan with PRO tier features.

    This endpoint is deprecated. Use /api/v1/pro/meal/weekly instead.
    """
    # Log deprecation warning only once to avoid log spam (thread-safe)
    if not _deprecation_logged.is_set():
        logger.warning(
            "DEPRECATED endpoint /api/v1/premium/plan/week-flexible was called. "
            "Use /api/v1/pro/meal/weekly instead."
        )
        _deprecation_logged.set()
    # Get cached database instances
    fooddb = _get_food_db()
    recipedb = _get_recipe_db()

    # Get targets (treat partial/empty targets as "missing" and fall back to profile derivation)
    targets_from_request: Dict[str, Any] = (
        req.targets.model_dump(exclude_none=True) if req.targets is not None else {}
    )

    if nutrition_targets_service.is_complete_planning_targets(targets_from_request):
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
        targets = cast(
            Dict[str, Any],
            nutrition_targets_service.estimate_targets_from_profile(
                sex=req.sex,
                age=req.age,
                height_cm=float(req.height_cm),
                weight_kg=float(req.weight_kg),
                activity=req.activity,
                goal=req.goal,
            ),
        )

    # Hard guard: never pass None/malformed targets to core
    if not isinstance(targets, dict):
        raise HTTPException(status_code=400, detail="Unable to derive targets")
    if not nutrition_targets_service.is_complete_planning_targets(targets):
        raise HTTPException(status_code=400, detail="Unable to derive targets")

    # 2) Построить неделю (generation stage) + postprocess (pipeline with ordering guard)
    from core.menu_engine_new import PlateDayTargets

    # Wrap PremiumWeekPlanResponse constructor to match postprocess_fn signature
    def _postprocess_week(week: dict[str, Any]) -> PremiumWeekPlanResponse:
        validated_week = require_weekly_plan_payload_shape(week)
        normalized_week = normalize_weekly_plan_payload(validated_week)
        return PremiumWeekPlanResponse(**normalized_week)

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
            "router": "premium_week",
            "path": "/api/v1/premium/plan/week-flexible",
        },
        postprocess_debug_ctx={
            "router": "premium_week",
            "path": "/api/v1/premium/plan/week-flexible",
            "deprecated": True,
        },
    )

    # Pipeline returns either error envelope or postprocess result
    if isinstance(result, dict) and result.get("status") == "error":
        # IMPORTANT: bypass response_model validation
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=result)

    if not isinstance(result, WeeklyMealPlanResponse):
        raise TypeError(f"Expected PremiumWeekPlanResponse, got {type(result).__name__}")

    result.next_best_action = build_weekly_plan_next_action(
        daily_menu_count=len(result.daily_menus)
    )
    return result

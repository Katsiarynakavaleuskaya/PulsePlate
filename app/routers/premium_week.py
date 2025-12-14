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
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.api_tiers import require_pro_tier
from app.models.nutrition import TargetsIn

from core.food_db_new import FoodDB
from core.meal_i18n import Language
from core.recipe_db_new import RecipeDB
from core.recommendations import build_nutrition_targets
from core.targets import UserProfile
from core.weekly_plan_new import build_week

router = APIRouter(prefix="/api/v1/premium", tags=["premium"])

# Deprecation warning logged only once to avoid log spam (thread-safe)
_deprecation_logged = Event()

logger = logging.getLogger(__name__)

# Cache database instances for performance (shared with pro.py pattern)
_premium_food_db_cache: Optional[FoodDB] = None
_premium_recipe_db_cache: Optional[RecipeDB] = None


def _get_food_db() -> FoodDB:
    """Get cached FoodDB instance for premium router."""
    global _premium_food_db_cache
    if _premium_food_db_cache is None:
        _premium_food_db_cache = FoodDB("data/food_db_new.csv")
    return _premium_food_db_cache


def _get_recipe_db() -> RecipeDB:
    """Get cached RecipeDB instance for premium router."""
    global _premium_recipe_db_cache
    if _premium_recipe_db_cache is None:
        _premium_recipe_db_cache = RecipeDB("data/recipes_new.csv", _get_food_db())
    return _premium_recipe_db_cache


class WeekPlanRequest(BaseModel):
    # режим A: передают готовые targets
    targets: Optional[TargetsIn] = None
    # режим B: быстрый профиль (fallback)
    sex: Optional[Literal["female", "male"]] = None
    age: Optional[int] = Field(None, gt=10, lt=90)
    height_cm: Optional[int] = Field(None, gt=100, lt=220)
    weight_kg: Optional[int] = Field(None, gt=30, lt=300)
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = "moderate"
    goal: Literal["loss", "maintain", "gain"] = "maintain"
    diet_flags: List[str] = Field(default_factory=list)
    lang: Language = "en"


class WeekPlanResponse(BaseModel):
    daily_menus: List[Dict]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float
    adherence_score: float


# TODO(#286): Deduplicate estimate_targets_minimal by moving it into app/services/nutrition_targets.py
# Keep parity between /api/v1/pro/meal/weekly and deprecated /api/v1/premium/plan/week-flexible.
def estimate_targets_minimal(
    sex: Literal["female", "male"],
    age: int,
    height_cm: float,
    weight_kg: float,
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"],
    goal: Literal["loss", "maintain", "gain"],
) -> dict:
    """Temporary function to estimate targets from user profile (DEPRECATED endpoint).

    WARNING: This function is duplicated in pro.py to maintain backward compatibility.
    Any changes here MUST be mirrored in pro.py until extraction is complete.
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
    "/plan/week-flexible",
    response_model=WeekPlanResponse,
    dependencies=[Depends(require_pro_tier)],
    deprecated=True,
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
async def generate_week_plan(req: WeekPlanRequest) -> WeekPlanResponse:
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

    # Get targets
    if req.targets:
        targets = req.targets.model_dump()
    else:
        # Validate required profile fields (explicit checks for better error messages)
        if req.sex is None:
            raise HTTPException(status_code=400, detail="Missing required field: sex")
        if req.age is None:
            raise HTTPException(status_code=400, detail="Missing required field: age")
        if req.height_cm is None:
            raise HTTPException(status_code=400, detail="Missing required field: height_cm")
        if req.weight_kg is None:
            raise HTTPException(status_code=400, detail="Missing required field: weight_kg")

        # After None checks above, mypy narrows Optional -> concrete types
        targets = estimate_targets_minimal(
            sex=req.sex,
            age=req.age,
            height_cm=float(req.height_cm),
            weight_kg=float(req.weight_kg),
            activity=req.activity,
            goal=req.goal,
        )

    # 2) Построить неделю
    week = build_week(targets, req.diet_flags, req.lang, fooddb, recipedb)
    return WeekPlanResponse(**week)

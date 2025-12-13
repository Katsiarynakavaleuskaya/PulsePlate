"""
Premium Week Plan Router

RU: Роутер для генерации недельного плана питания.
EN: Router for generating weekly meal plans.

⚠️ DEPRECATED: This router is deprecated. Use app.routers.pro instead.
All endpoints in this router are deprecated and will be removed in v2.0.
Please migrate to /api/v1/pro/* endpoints.
"""

import logging
import math
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.middleware.api_tiers import require_pro_tier

from core.food_db_new import FoodDB
from core.meal_i18n import Language
from core.recipe_db_new import RecipeDB
from core.recommendations import build_nutrition_targets
from core.targets import UserProfile
from core.weekly_plan_new import build_week

router = APIRouter(prefix="/api/v1/premium", tags=["premium"])

# Deprecation warning will be logged on every call, not at import time
# to avoid spamming logs on every startup
logger = logging.getLogger(__name__)


class TargetsIn(BaseModel):
    kcal: int = Field(..., gt=500, lt=6000)
    macros: Dict[str, float]
    micro: Dict[str, float]
    water_ml: int = Field(0, ge=0)
    activity_week: Optional[Dict[str, int]] = None

    @field_validator("macros")
    @classmethod
    def _validate_macros(cls, v: Dict[str, float]) -> Dict[str, float]:
        # Ensure all values are finite numbers >= 0
        for key, val in v.items():
            # Check if value is a numeric type (int or float)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"macros[{key}] must be a finite number >= 0")

            # Check if value is finite (not NaN or Infinity) and non-negative
            if not math.isfinite(val) or val < 0:
                raise ValueError(f"macros[{key}] must be a finite number >= 0")
        return v

    @field_validator("micro")
    @classmethod
    def _validate_micro(cls, v: Dict[str, float]) -> Dict[str, float]:
        # Ensure all values are finite numbers >= 0
        for key, val in v.items():
            # Check if value is a numeric type (int or float)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"micro[{key}] must be a finite number >= 0")

            # Check if value is finite (not NaN or Infinity) and non-negative
            if not math.isfinite(val) or val < 0:
                raise ValueError(f"micro[{key}] must be a finite number >= 0")
        return v


class WeekPlanRequest(BaseModel):
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


class WeekPlanResponse(BaseModel):
    daily_menus: List[Dict]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float
    adherence_score: float


def estimate_targets_minimal(
    sex: Literal["female", "male"],
    age: int,
    height_cm: float,
    weight_kg: float,
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"],
    goal: Literal["loss", "maintain", "gain"],
) -> dict:
    """Temporary function to estimate targets from user profile."""
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
async def generate_week_plan(req: WeekPlanRequest):
    """
    [DEPRECATED] Generate weekly meal plan with PRO tier features.

    This endpoint is deprecated. Use /api/v1/pro/meal/weekly instead.
    """
    # Log deprecation warning on first use (not at import time)
    logger.warning(
        "DEPRECATED endpoint /api/v1/premium/plan/week-flexible was called. "
        "Use /api/v1/pro/meal/weekly instead."
    )
    # 0) Загрузка БД (можно держать как синглтоны)
    fooddb = FoodDB("data/food_db_new.csv")
    recipedb = RecipeDB("data/recipes_new.csv", fooddb)

    # 1) Получить targets
    if req.targets:
        targets = req.targets.model_dump()
    else:
        # временный расчет через твой bmi_core (BMR/TDEE + макросы + микро-таблица)
        if not all([req.sex, req.age, req.height_cm, req.weight_kg]):
            raise HTTPException(status_code=400, detail="Missing user profile data")

        # Ensure all required fields are present
        if not all([req.sex, req.age, req.height_cm, req.weight_kg, req.activity, req.goal]):
            raise HTTPException(status_code=400, detail="All profile fields are required")

        targets = estimate_targets_minimal(
            sex=req.sex,  # type: ignore
            age=req.age,  # type: ignore
            height_cm=req.height_cm,  # type: ignore
            weight_kg=req.weight_kg,  # type: ignore
            activity=req.activity,  # type: ignore
            goal=req.goal,  # type: ignore
        )
        if not targets:
            raise HTTPException(status_code=400, detail="Unable to derive targets")

    # 2) Построить неделю
    week = build_week(targets, req.diet_flags, req.lang, fooddb, recipedb)
    return WeekPlanResponse(**week)

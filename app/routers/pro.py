"""
PRO Tier Router

RU: Роутер для PRO уровня подписки - продвинутые функции питания.
EN: Router for PRO subscription tier - advanced nutrition features.

This router provides PRO tier endpoints optimized for iOS mobile app integration.
All endpoints require PRO tier API key validation via require_pro_tier middleware.

Endpoints:
- /api/v1/pro/meal/weekly - Weekly meal plan (macros only)
- /api/v1/pro/nutrition/targets - WHO-based nutrition goals
"""

from typing import Any, Dict, List, Literal, Optional

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

router = APIRouter(prefix="/api/v1/pro", tags=["pro"])


# Cache database instances for performance
_food_db_cache: Optional[FoodDB] = None
_recipe_db_cache: Optional[RecipeDB] = None


def get_food_db() -> FoodDB:
    """Get cached FoodDB instance."""
    global _food_db_cache
    if _food_db_cache is None:
        _food_db_cache = FoodDB("data/food_db_new.csv")
    return _food_db_cache


def get_recipe_db() -> RecipeDB:
    """Get cached RecipeDB instance."""
    global _recipe_db_cache
    if _recipe_db_cache is None:
        _recipe_db_cache = RecipeDB("data/recipes_new.csv", get_food_db())
    return _recipe_db_cache


class WeekPlanRequest(BaseModel):
    """Request model for weekly meal plan generation.

    Supports two modes:
    - Mode A: Provide ready targets
    - Mode B: Quick profile (fallback)
    """

    # Mode A: Provide ready targets
    targets: Optional[TargetsIn] = None
    # Mode B: Quick profile (fallback)
    sex: Optional[Literal["female", "male"]] = None
    age: Optional[int] = Field(None, gt=10, lt=90)
    height_cm: Optional[int] = Field(None, gt=100, lt=220)
    weight_kg: Optional[int] = Field(None, gt=30, lt=300)
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = "moderate"
    goal: Literal["loss", "maintain", "gain"] = "maintain"
    diet_flags: List[str] = Field(default_factory=list)
    lang: Language = "en"


class WeekPlanResponse(BaseModel):
    """Response model for weekly meal plan."""

    daily_menus: List[Dict]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float
    adherence_score: float


def _is_complete_targets(d: Dict[str, Any]) -> bool:
    """Check if targets dict has all required keys and non-empty micro/macros."""
    required_keys = {"kcal", "macros", "micro", "water_ml", "activity_week"}
    if not required_keys.issubset(d.keys()):
        return False
    if not isinstance(d.get("macros"), dict):
        return False
    if not isinstance(d.get("micro"), dict):
        return False
    # micro must not be empty, otherwise core may produce unexpected results
    if not d.get("micro"):
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
) -> dict:
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
    response_model=WeekPlanResponse,
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
async def generate_week_plan(req: WeekPlanRequest) -> WeekPlanResponse:
    """Generate weekly meal plan with PRO tier features.

    Args:
        req: WeekPlanRequest with targets or user profile

    Returns:
        WeekPlanResponse with daily menus, coverage, shopping list, and metrics

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
        # Fallback: derive from profile, otherwise 400 (keep legacy message for tests)
        if req.sex is None or req.age is None or req.height_cm is None or req.weight_kg is None:
            raise HTTPException(status_code=400, detail="Missing user profile data")
        # activity/goal have defaults but can be explicitly set to null
        if req.activity is None or req.goal is None:
            raise HTTPException(status_code=400, detail="Missing user profile data")

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

    # Build week
    week = build_week(targets, req.diet_flags, req.lang, fooddb, recipedb)
    return WeekPlanResponse(**week)

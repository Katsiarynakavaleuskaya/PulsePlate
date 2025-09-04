"""
Premium Week Plan Router

RU: Роутер для генерации недельного плана питания.
EN: Router for generating weekly meal plans.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, confloat, conint

from core.food_db_new import FoodDB
from core.meal_i18n import Language
from core.recipe_db_new import RecipeDB
from core.recommendations import build_nutrition_targets
from core.targets import UserProfile
from core.weekly_plan_new import build_week

router = APIRouter(prefix="/api/v1/premium/plan", tags=["premium"])

class TargetsIn(BaseModel):
    kcal: conint(gt=500, lt=6000)
    macros: Dict[str, confloat(ge=0)]
    micro: Dict[str, confloat(ge=0)]
    water_ml: Optional[conint(ge=0)] = 0
    activity_week: Optional[Dict[str, conint(ge=0)]] = None

class WeekPlanRequest(BaseModel):
    # режим A: передают готовые targets
    targets: Optional[TargetsIn] = None
    # режим B: быстрый профиль (fallback)
    sex: Optional[str] = None
    age: Optional[conint(gt=10, lt=90)] = None
    height_cm: Optional[conint(gt=100, lt=220)] = None
    weight_kg: Optional[conint(gt=30, lt=300)] = None
    activity: Optional[str] = "moderate"
    goal: Optional[str] = "maintain"
    diet_flags: List[str] = Field(default_factory=list)
    lang: Language = "en"

class WeekPlanResponse(BaseModel):
    days: List[Dict]
    weekly_coverage: Dict[str, float]
    shopping_list: List[Dict]

def estimate_targets_minimal(sex: str, age: int, height_cm: float, weight_kg: float,
                           activity: str, goal: str) -> dict:
    """Temporary function to estimate targets from user profile."""
    # Create a UserProfile object
    profile = UserProfile(
        sex=sex,
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity=activity,
        goal=goal
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
            "fiber_g": targets.macros.fiber_g
        },
        "micro": targets.micros.get_priority_nutrients(),
        "water_ml": targets.water_ml_daily,
        "activity_week": {
            "moderate_aerobic_min": targets.activity.moderate_aerobic_min,
            "vigorous_aerobic_min": targets.activity.vigorous_aerobic_min,
            "strength_sessions": targets.activity.strength_sessions,
            "steps_daily": targets.activity.steps_daily
        }
    }

@router.post("/week", response_model=WeekPlanResponse)
async def generate_week_plan(req: WeekPlanRequest):
    # 0) Загрузка БД (можно держать как синглтоны)
    fooddb = FoodDB("data/food_db_new.csv")
    recipedb = RecipeDB("data/recipes_new.csv", fooddb)

    # 1) Получить targets
    if req.targets:
        targets = req.targets.dict()
    else:
        # временный расчет через твой bmi_core (BMR/TDEE + макросы + микро-таблица)
        if not all([req.sex, req.age, req.height_cm, req.weight_kg]):
            raise HTTPException(status_code=400, detail="Missing user profile data")

        targets = estimate_targets_minimal(
            sex=req.sex, age=req.age, height_cm=req.height_cm,
            weight_kg=req.weight_kg, activity=req.activity, goal=req.goal
        )
        if not targets:
            raise HTTPException(status_code=400, detail="Unable to derive targets")

    # 2) Построить неделю
    week = build_week(targets, req.diet_flags, req.lang, fooddb, recipedb)
    return WeekPlanResponse(**week)

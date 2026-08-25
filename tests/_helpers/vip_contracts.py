"""Shared VIP response contract assertions for tests."""

from __future__ import annotations

from typing import Any, Literal, Mapping, TypedDict


class WeeklyRecipeIngredientPayload(TypedDict):
    """One strict weekly-recipe ingredient fixture."""

    name: str
    amount: float
    unit: str


class WeeklyRecipeMealPayload(TypedDict):
    """One strict weekly-recipe meal fixture."""

    ingredients: list[WeeklyRecipeIngredientPayload]


class WeeklyRecipeDayPayload(TypedDict):
    """One strict weekly-recipe day fixture."""

    day: str
    meals: list[WeeklyRecipeMealPayload]


class WeeklyRecipePlanPayload(TypedDict):
    """One strict weekly-recipe plan fixture."""

    days: list[WeeklyRecipeDayPayload]


class WeeklyRecipesRequestPayload(TypedDict):
    """Concrete request accepted by ``WeeklyRecipesRequest``."""

    week_plan: WeeklyRecipePlanPayload
    recipes_per_day: int


class AutoRepairIngredientPayload(TypedDict):
    """One strict auto-repair ingredient fixture."""

    name: str


class AutoRepairMealNutrientsPayload(TypedDict):
    """Complete explicit nutrient evidence for one auto-repair meal."""

    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fiber_g: float
    iron_mg: float
    calcium_mg: float
    magnesium_mg: float
    zinc_mg: float
    potassium_mg: float
    iodine_ug: float
    selenium_ug: float
    folate_ug: float
    b12_ug: float
    vitamin_d_iu: float
    vitamin_a_ug: float
    vitamin_c_mg: float


class AutoRepairMealPayload(TypedDict):
    """One strict auto-repair meal fixture."""

    ingredients: list[AutoRepairIngredientPayload]
    nutrients: AutoRepairMealNutrientsPayload


class AutoRepairDayPayload(TypedDict):
    """One strict auto-repair day fixture."""

    day: str
    meals: list[AutoRepairMealPayload]


class AutoRepairWeekPlanPayload(TypedDict):
    """One strict auto-repair week-plan fixture."""

    days: list[AutoRepairDayPayload]


class AutoRepairTargetRangesPayload(TypedDict):
    """The complete deterministic twelve-target triplet map."""

    iron_mg: list[float]
    calcium_mg: list[float]
    magnesium_mg: list[float]
    zinc_mg: list[float]
    potassium_mg: list[float]
    iodine_ug: list[float]
    selenium_ug: list[float]
    folate_ug: list[float]
    b12_ug: list[float]
    vitamin_d_iu: list[float]
    vitamin_a_ug: list[float]
    vitamin_c_mg: list[float]


class AutoRepairProfilePayload(TypedDict):
    """Explicit profile authority for a strict auto-repair request."""

    sex: Literal["male"]
    age: int
    height_cm: float
    weight_kg: float
    activity: Literal["moderate"]
    goal: Literal["maintain"]
    deficit_pct: float | None
    surplus_pct: float | None
    bodyfat: float | None
    region: str
    timezone: str
    diet_flags: list[str]
    life_stage: Literal["adult"]
    medical_conditions: list[str]


class AutoRepairMacroTargetsPayload(TypedDict):
    """Canonical daily macro targets for the auto-repair fixture."""

    protein_g: int
    fat_g: int
    carbs_g: int
    fiber_g: int


class AutoRepairActivityTargetsPayload(TypedDict):
    """Canonical activity targets for the auto-repair fixture."""

    moderate_aerobic_min: int
    vigorous_aerobic_min: int
    strength_sessions: int
    steps_daily: int


class AutoRepairDailyTargetsPayload(TypedDict):
    """Canonical daily targets for the auto-repair fixture."""

    kcal_daily: int
    macros: AutoRepairMacroTargetsPayload
    water_ml_daily: int
    activity: AutoRepairActivityTargetsPayload
    calculation_date: str


class AutoRepairWeeklyRequestPayload(TypedDict):
    """Concrete request accepted by ``AutoRepairWeeklyRequest``."""

    week_plan: AutoRepairWeekPlanPayload
    targets: AutoRepairTargetRangesPayload
    profile: AutoRepairProfilePayload
    daily_targets: AutoRepairDailyTargetsPayload
    strategy: Literal["balanced"]
    user_preferences: dict[str, object]


def build_weekly_recipes_request_payload(
    *,
    ingredient_name: str = "chicken",
    amount: float = 100.0,
) -> WeeklyRecipesRequestPayload:
    """Build one fresh deterministic request for weekly recipe synthesis."""

    return {
        "week_plan": {
            "days": [
                {
                    "day": "Monday",
                    "meals": [
                        {
                            "ingredients": [
                                {
                                    "name": ingredient_name,
                                    "amount": amount,
                                    "unit": "g",
                                }
                            ]
                        }
                    ],
                }
            ]
        },
        "recipes_per_day": 1,
    }


def build_auto_repair_weekly_request_payload() -> AutoRepairWeeklyRequestPayload:
    """Build one fresh, already-compliant deterministic auto-repair request."""

    return {
        "week_plan": {
            "days": [
                {
                    "day": "Monday",
                    "meals": [
                        {
                            "ingredients": [{"name": "rice"}],
                            "nutrients": {
                                "kcal": 1800.0,
                                "protein_g": 100.0,
                                "fat_g": 60.0,
                                "carbs_g": 215.0,
                                "fiber_g": 30.0,
                                "iron_mg": 8.0,
                                "calcium_mg": 1000.0,
                                "magnesium_mg": 400.0,
                                "zinc_mg": 11.0,
                                "potassium_mg": 4700.0,
                                "iodine_ug": 150.0,
                                "selenium_ug": 55.0,
                                "folate_ug": 400.0,
                                "b12_ug": 2.4,
                                "vitamin_d_iu": 600.0,
                                "vitamin_a_ug": 900.0,
                                "vitamin_c_mg": 90.0,
                            },
                        }
                    ],
                }
            ]
        },
        "targets": {
            "iron_mg": [6.0, 8.0, 45.0],
            "calcium_mg": [800.0, 1000.0, 2500.0],
            "magnesium_mg": [300.0, 400.0, 700.0],
            "zinc_mg": [8.0, 11.0, 40.0],
            "potassium_mg": [3500.0, 4700.0, 5000.0],
            "iodine_ug": [130.0, 150.0, 1100.0],
            "selenium_ug": [45.0, 55.0, 400.0],
            "folate_ug": [320.0, 400.0, 1000.0],
            "b12_ug": [2.0, 2.4, 100.0],
            "vitamin_d_iu": [400.0, 600.0, 4000.0],
            "vitamin_a_ug": [600.0, 900.0, 3000.0],
            "vitamin_c_mg": [75.0, 90.0, 2000.0],
        },
        "profile": {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "deficit_pct": None,
            "surplus_pct": None,
            "bodyfat": None,
            "region": "BY",
            "timezone": "UTC",
            "diet_flags": [],
            "life_stage": "adult",
            "medical_conditions": [],
        },
        "daily_targets": {
            "kcal_daily": 1800,
            "macros": {
                "protein_g": 100,
                "fat_g": 60,
                "carbs_g": 215,
                "fiber_g": 30,
            },
            "water_ml_daily": 2000,
            "activity": {
                "moderate_aerobic_min": 150,
                "vigorous_aerobic_min": 75,
                "strength_sessions": 2,
                "steps_daily": 8000,
            },
            "calculation_date": "2026-08-25",
        },
        "strategy": "balanced",
        "user_preferences": {},
    }


def assert_json_response_payload(response: Any) -> Any:
    """Assert JSON content type before parsing a TestClient response."""

    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


def assert_vip_shoplist_formats_contract(payload: Mapping[str, Any]) -> None:
    """Assert the static VIP shoplist formats response contract."""

    assert payload["status"] == "success"
    assert payload["formats"] == ["json", "csv", "text"]
    assert payload["locales"] == ["ru", "en", "es"]


def assert_vip_shoplist_formats_response(response: Any) -> None:
    """Assert the static VIP shoplist formats response from TestClient."""

    payload = assert_json_response_payload(response)
    assert_vip_shoplist_formats_contract(payload)

from typing import Any, cast

from core.food_db_new import FoodDB
from core.menu_engine_new import DayPlan, build_plate_day
from core.recipe_db_new import RecipeDB


class FFood:
    per_g = 100.0
    protein_g = 1.0
    fat_g = 0.0
    carbs_g = 0.0
    fiber_g = 0.0
    micros: dict[str, float] = {}


class FDB:
    def pick_booster_for(self, mk: str, diet_flags: list[str]) -> str | None:  # noqa: D401
        return None

    def get_food(self, name: str) -> FFood:
        return FFood()

    def get_translated_food_name(self, name: str, lang: str) -> str:
        return name


class RDB:
    def pick_base_recipe(self, diet_flags: list[str], i: int) -> Any:
        # Minimal recipe object with attributes used by codepath via scale function
        return {"name": "base"}

    def scale_recipe_to_kcal(self, r: Any, kcal_goal: int, lang: str, prefer_fiber: bool = True):
        # Return minimal object with fields accessed by build_plate_day
        class M:
            title = "meal"
            title_translated = "meal"
            grams: dict[str, float] = {}
            kcal = kcal_goal
            macros = {"protein_g": 10.0, "fat_g": 1.0, "carbs_g": 5.0, "fiber_g": 2.0}
            micros: dict[str, float] = {}
            # Provide price_est so build_plate_day can propagate into out_meals
            price_est = "12.5" if kcal_goal != 420 else "not_a_number"

        return M()


def test_total_cost_handles_string_values():
    targets = {
        "kcal": 1200,
        "micro": {
            k: 10.0 for k in __import__("core.food_db_new", fromlist=["MICRO_KEYS"]).MICRO_KEYS
        },
    }
    plan: DayPlan = build_plate_day(targets, [], "en", cast(FoodDB, FDB()), cast(RecipeDB, RDB()))
    # Inject price as a string and invalid string; verify float field present
    if plan.meals:
        plan.meals[0]["price_est"] = "12.5"
        if len(plan.meals) > 1:
            plan.meals[1]["price_est"] = "not_a_number"
    assert isinstance(plan.total_cost, float)

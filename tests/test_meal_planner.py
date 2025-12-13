"""
Tests for meal_planner.py - Meal Planning Logic

Test coverage: 97%+ target
"""

import pytest

from typing import Any, Dict, List, Optional

from core.meal_planner import (
    DailyMealPlan,
    MealPlan,
    WeeklyMealPlan,
    create_daily_meal_plan,
    create_meal_plan,
    create_weekly_meal_plan,
)


class MockRecipeDB:
    """Mock recipe database for testing."""

    def __init__(self, recipes: Optional[List[Dict[str, Any]]] = None) -> None:
        self.recipes: List[Dict[str, Any]] = recipes or []

    def pick_base_recipe(self, diet_flags: List[str], meal_index: int) -> Optional[Dict[str, Any]]:
        """Legacy interface."""
        if self.recipes and meal_index < len(self.recipes):
            return self.recipes[meal_index]
        return None


class TestCreateMealPlan:
    """Test create_meal_plan function."""

    def test_create_meal_plan_basic(self) -> None:
        """Test basic meal plan creation."""
        meal = create_meal_plan("breakfast", 500)

        assert meal.name == "breakfast"
        assert meal.kcal_target == 500
        assert meal.recipe_name is not None

    def test_create_meal_plan_fallback(self) -> None:
        """Test fallback meal creation when no recipe DB."""
        meal = create_meal_plan("lunch", 700)

        assert meal.name == "lunch"
        assert meal.kcal_target == 700
        assert "Balanced lunch" in meal.recipe_name
        assert "protein_g" in meal.macros
        assert "carbs_g" in meal.macros
        assert "fat_g" in meal.macros

    def test_create_meal_plan_with_diet_flags(self) -> None:
        """Test meal creation with dietary restrictions affects macros."""
        vegan_meal = create_meal_plan("dinner", 600, diet_flags={"VEGAN"})
        keto_meal = create_meal_plan("dinner", 600, diet_flags={"KETO"})

        assert vegan_meal.name == "dinner"
        assert vegan_meal.kcal_target == 600
        # KETO should have very low carbs (< 10% of calories)
        keto_carbs_kcal = keto_meal.macros["carbs_g"] * 4
        assert keto_carbs_kcal / 600 < 0.15  # Should be well under 15%

    def test_create_meal_plan_breakfast_macros(self) -> None:
        """Test breakfast has higher carb ratio."""
        meal = create_meal_plan("breakfast", 500)

        # Breakfast should be higher in carbs (50% vs 40% for other meals)
        carbs_ratio = meal.macros["carbs_g"] * 4 / 500
        assert carbs_ratio >= 0.45  # Around 50% ±5%

    def test_create_meal_plan_snack_smaller(self) -> None:
        """Test snack has appropriate macros."""
        meal = create_meal_plan("snack", 200)

        assert meal.name == "snack"
        assert meal.macros["protein_g"] > 0
        assert meal.macros["carbs_g"] > 0

    def test_create_meal_plan_with_recipe_db(self) -> None:
        """Test meal creation with mock recipe database."""
        mock_recipe = {
            "name": "Oatmeal Bowl",
            "ingredients": {"oats": 50, "banana": 100},
            "macros": {"protein_g": 10, "carbs_g": 60, "fat_g": 5, "fiber_g": 8},
            "micros": {"iron_mg": 3.5},
            "cost": 2.50,
            "kcal": 300,
            "flags": ["VEG", "GF"],
        }

        mock_db = MockRecipeDB([mock_recipe])
        meal = create_meal_plan("breakfast", 500, recipe_db=mock_db)

        assert meal.recipe_name == "Oatmeal Bowl"
        assert meal.ingredients == {"oats": 50, "banana": 100}
        assert meal.estimated_cost == 2.50


class TestCreateDailyMealPlan:
    """Test create_daily_meal_plan function."""

    def test_create_daily_plan_basic(self) -> None:
        """Test basic daily plan creation."""
        plan = create_daily_meal_plan(2000)

        assert plan.day == 1
        assert plan.total_kcal == 2000
        assert len(plan.meals) == 4  # Default 4 meals

    def test_create_daily_plan_3_meals(self) -> None:
        """Test daily plan with 3 meals."""
        plan = create_daily_meal_plan(2000, num_meals=3)

        assert len(plan.meals) == 3

    def test_create_daily_plan_meal_names(self) -> None:
        """Test that all expected meals are present."""
        plan = create_daily_meal_plan(2000, num_meals=4)

        meal_names = [meal.name for meal in plan.meals]
        assert "breakfast" in meal_names
        assert "lunch" in meal_names
        assert "dinner" in meal_names
        assert "snack" in meal_names

    def test_create_daily_plan_calorie_distribution(self) -> None:
        """Test calories are distributed correctly."""
        plan = create_daily_meal_plan(2000)

        # Sum of meal targets should equal total
        total_meal_kcal = sum(meal.kcal_target for meal in plan.meals)
        assert abs(total_meal_kcal - 2000) <= 5  # Allow small rounding

    def test_create_daily_plan_macro_aggregation(self) -> None:
        """Test macros are aggregated correctly."""
        plan = create_daily_meal_plan(2000)

        assert "protein_g" in plan.total_macros
        assert "carbs_g" in plan.total_macros
        assert "fat_g" in plan.total_macros
        assert "fiber_g" in plan.total_macros

        # All macros should be positive
        assert plan.total_macros["protein_g"] > 0
        assert plan.total_macros["carbs_g"] > 0
        assert plan.total_macros["fat_g"] > 0

    def test_create_daily_plan_with_diet_flags(self) -> None:
        """Test daily plan respects diet flags and affects macros."""
        keto_plan = create_daily_meal_plan(2000, diet_flags={"KETO"})
        regular_plan = create_daily_meal_plan(2000)

        assert len(keto_plan.meals) > 0
        # KETO should have significantly fewer carbs than regular
        assert keto_plan.total_macros["carbs_g"] < regular_plan.total_macros["carbs_g"]

    def test_create_daily_plan_with_recipe_db(self) -> None:
        """Test daily plan with recipe database."""
        mock_recipes = [
            {
                "name": "Breakfast Bowl",
                "kcal": 500,
                "macros": {"protein_g": 20, "carbs_g": 70, "fat_g": 15, "fiber_g": 10},
                "ingredients": {},
                "cost": 2.5,
            }
        ]

        mock_db = MockRecipeDB(mock_recipes)
        plan = create_daily_meal_plan(2000, recipe_db=mock_db)

        # At least one meal should use the recipe
        recipe_names = [meal.recipe_name for meal in plan.meals]
        assert any("Breakfast Bowl" in str(name) for name in recipe_names)
        # Daily total_cost should include recipe costs
        assert plan.total_cost > 0.0


class TestCreateWeeklyMealPlan:
    """Test create_weekly_meal_plan function."""

    def test_create_weekly_plan_basic(self) -> None:
        """Test basic weekly plan creation."""
        plan = create_weekly_meal_plan(2000)

        assert len(plan.days) == 7
        # Average will be close to 2000 (variation causes small differences)
        assert abs(plan.average_kcal - 2000) <= 20

    def test_create_weekly_plan_day_numbers(self) -> None:
        """Test days are numbered 1-7."""
        plan = create_weekly_meal_plan(2000)

        day_numbers = [day.day for day in plan.days]
        assert day_numbers == [1, 2, 3, 4, 5, 6, 7]

    def test_create_weekly_plan_variation(self) -> None:
        """Test weekly plan has calorie variation."""
        plan = create_weekly_meal_plan(2000)

        # Should have different calorie targets on different days
        kcal_targets = [day.total_kcal for day in plan.days]

        # Not all days should be exactly 2000 (due to variation)
        assert len(set(kcal_targets)) > 1

    def test_create_weekly_plan_average_correct(self) -> None:
        """Test average calories is correct."""
        plan = create_weekly_meal_plan(2000)

        total_kcal = sum(day.total_kcal for day in plan.days)
        calculated_avg = total_kcal // 7

        assert abs(calculated_avg - plan.average_kcal) <= 1

    def test_create_weekly_plan_shopping_list(self) -> None:
        """Test shopping list is generated."""
        plan = create_weekly_meal_plan(2000)

        assert isinstance(plan.shopping_list, dict)

    def test_create_weekly_plan_with_diet_flags(self) -> None:
        """Test weekly plan with dietary restrictions."""
        plan = create_weekly_meal_plan(2000, diet_flags={"VEGAN"})

        assert len(plan.days) == 7

    def test_create_weekly_plan_3_meals_per_day(self) -> None:
        """Test weekly plan with 3 meals per day."""
        plan = create_weekly_meal_plan(2000, num_meals=3)

        # All days should have 3 meals
        for day in plan.days:
            assert len(day.meals) == 3

    def test_weekly_total_cost_aggregates_daily_costs(self) -> None:
        """Weekly total_cost should equal sum of daily total_cost values."""

        class CostRecipeDB:
            def get_recipes_by_category(self, categories: List[str]) -> List[Dict[str, Any]]:
                return [
                    {
                        "name": "Any Meal",
                        "kcal": 500,
                        "macros": {
                            "protein_g": 20,
                            "carbs_g": 60,
                            "fat_g": 15,
                            "fiber_g": 8,
                        },
                        "ingredients": {},
                        "cost": 3.0,
                        "flags": [],
                    }
                ]

        plan = create_weekly_meal_plan(2000, recipe_db=CostRecipeDB())

        assert plan.total_cost == pytest.approx(sum(day.total_cost for day in plan.days))
        assert plan.total_cost > 0.0


class TestMealPlanDataclass:
    """Test MealPlan dataclass."""

    def test_meal_plan_creation(self) -> None:
        """Test creating MealPlan object."""
        meal = MealPlan(name="breakfast", kcal_target=500)

        assert meal.name == "breakfast"
        assert meal.kcal_target == 500
        assert meal.recipe_name is None
        assert meal.ingredients == {}
        assert meal.macros == {}

    def test_meal_plan_with_all_fields(self) -> None:
        """Test MealPlan with all fields populated."""
        meal = MealPlan(
            name="lunch",
            kcal_target=700,
            recipe_name="Quinoa Bowl",
            ingredients={"quinoa": 100, "chickpeas": 150},
            macros={"protein_g": 25, "carbs_g": 80, "fat_g": 15, "fiber_g": 12},
            micros={"iron_mg": 4.5},
            boosters=[{"name": "Spinach", "amount": 50}],
            estimated_cost=5.50,
        )

        assert meal.name == "lunch"
        assert meal.recipe_name == "Quinoa Bowl"
        assert meal.estimated_cost == 5.50
        assert len(meal.ingredients) == 2


class TestDailyMealPlanDataclass:
    """Test DailyMealPlan dataclass."""

    def test_daily_plan_creation(self) -> None:
        """Test creating DailyMealPlan object."""
        meals = [
            MealPlan(name="breakfast", kcal_target=500),
            MealPlan(name="lunch", kcal_target=700),
        ]

        plan = DailyMealPlan(day=1, total_kcal=1200, meals=meals)

        assert plan.day == 1
        assert plan.total_kcal == 1200
        assert len(plan.meals) == 2

    def test_daily_plan_with_all_fields(self) -> None:
        """Test DailyMealPlan with all fields."""
        meals = [MealPlan(name="breakfast", kcal_target=500)]

        plan = DailyMealPlan(
            day=1,
            total_kcal=500,
            meals=meals,
            total_macros={"protein_g": 20, "carbs_g": 60, "fat_g": 15, "fiber_g": 8},
            total_micros={"iron_mg": 3.0},
            micro_coverage={"iron_mg": 85.0},
            tips=["Drink water", "Include greens"],
            total_cost=10.50,
        )

        assert len(plan.tips) == 2
        assert plan.total_cost == 10.50
        assert "iron_mg" in plan.micro_coverage


class TestWeeklyMealPlanDataclass:
    """Test WeeklyMealPlan dataclass."""

    def test_weekly_plan_creation(self) -> None:
        """Test creating WeeklyMealPlan object."""
        days = [DailyMealPlan(day=i, total_kcal=2000, meals=[]) for i in range(1, 8)]

        plan = WeeklyMealPlan(days=days, average_kcal=2000)

        assert len(plan.days) == 7
        assert plan.average_kcal == 2000

    def test_weekly_plan_with_shopping_list(self) -> None:
        """Test WeeklyMealPlan with shopping list."""
        days = [DailyMealPlan(day=1, total_kcal=2000, meals=[])]

        plan = WeeklyMealPlan(
            days=days,
            average_kcal=2000,
            shopping_list={"oats": 500, "banana": 700},
            total_cost=50.00,
        )

        assert len(plan.shopping_list) == 2
        assert plan.shopping_list["oats"] == 500
        assert plan.total_cost == 50.00


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_create_meal_plan_zero_calories(self) -> None:
        """Test meal creation with zero calories."""
        meal = create_meal_plan("breakfast", 0)

        assert meal.kcal_target == 0

    def test_create_daily_plan_very_low_calories(self) -> None:
        """Test daily plan with very low calories."""
        plan = create_daily_meal_plan(800)

        assert plan.total_kcal == 800
        assert len(plan.meals) > 0

    def test_create_daily_plan_very_high_calories(self) -> None:
        """Test daily plan with very high calories."""
        plan = create_daily_meal_plan(5000)

        assert plan.total_kcal == 5000

    def test_create_weekly_plan_empty_diet_flags(self) -> None:
        """Test weekly plan with empty diet flags."""
        plan = create_weekly_meal_plan(2000, diet_flags=set())

        assert len(plan.days) == 7

    def test_meal_plan_none_recipe_db(self) -> None:
        """Test meal creation with None recipe_db."""
        meal = create_meal_plan("lunch", 700, recipe_db=None)

        assert meal.recipe_name is not None  # Should have fallback


class TestShoppingListGeneration:
    """Test shopping list generation logic."""

    def test_shopping_list_aggregates_ingredients(self) -> None:
        """Test shopping list combines ingredients from multiple days with real recipes."""
        from core.meal_planner import _generate_shopping_list, DailyMealPlan, MealPlan

        # Create meals with overlapping ingredients
        meal1 = MealPlan(
            name="breakfast",
            kcal_target=500,
            recipe_name="Oatmeal",
            macros={"protein_g": 10, "carbs_g": 60, "fat_g": 8, "fiber_g": 10},
            ingredients={"oats": 50, "milk": 200, "banana": 100},
        )
        meal2 = MealPlan(
            name="breakfast",
            kcal_target=500,
            recipe_name="Smoothie",
            macros={"protein_g": 15, "carbs_g": 50, "fat_g": 10, "fiber_g": 8},
            ingredients={"milk": 150, "banana": 150, "berries": 100},  # milk and banana overlap
        )

        day1 = DailyMealPlan(day=1, total_kcal=500, meals=[meal1], total_macros={}, total_cost=0.0)
        day2 = DailyMealPlan(day=2, total_kcal=500, meals=[meal2], total_macros={}, total_cost=0.0)

        shopping_list = _generate_shopping_list([day1, day2])

        # Verify aggregation: milk should be 200 + 150 = 350
        assert shopping_list["milk"] == 350
        # banana should be 100 + 150 = 250
        assert shopping_list["banana"] == 250
        # oats and berries only appear once
        assert shopping_list["oats"] == 50
        assert shopping_list["berries"] == 100

    def test_shopping_list_empty_for_no_ingredients(self) -> None:
        """Test shopping list is empty when meals have no ingredients."""
        from core.meal_planner import _generate_shopping_list, DailyMealPlan, MealPlan

        meal = MealPlan(
            name="fallback",
            kcal_target=500,
            recipe_name="Balanced meal",
            macros={"protein_g": 20, "carbs_g": 60, "fat_g": 15, "fiber_g": 10},
            ingredients={},  # No ingredients
        )
        day = DailyMealPlan(day=1, total_kcal=500, meals=[meal], total_macros={}, total_cost=0.0)

        shopping_list = _generate_shopping_list([day])

        # Should be empty dict
        assert shopping_list == {}


class TestRecipeSelection:
    """Test recipe selection logic."""

    def test_recipe_selected_by_meal_type(self) -> None:
        """Test recipes are selected based on meal type."""
        breakfast_recipe = {
            "name": "Oatmeal",
            "kcal": 500,
            "macros": {"protein_g": 15, "carbs_g": 70, "fat_g": 10, "fiber_g": 10},
            "flags": ["breakfast", "VEG"],
        }

        mock_db = MockRecipeDB([breakfast_recipe])
        meal = create_meal_plan("breakfast", 500, recipe_db=mock_db)

        assert meal.recipe_name == "Oatmeal"

    def test_recipe_respects_diet_flags(self) -> None:
        """Test recipe selection respects dietary flags and creates appropriate fallback."""
        vegan_meal = create_meal_plan("lunch", 700, diet_flags={"VEGAN"})
        keto_meal = create_meal_plan("lunch", 700, diet_flags={"KETO"})

        assert vegan_meal.name == "lunch"
        # KETO meal should have lower carbs than VEGAN meal
        assert keto_meal.macros["carbs_g"] < vegan_meal.macros["carbs_g"]


class TestMacroDistribution:
    """Test macro distribution in fallback meals."""

    def test_breakfast_higher_carbs(self) -> None:
        """Test breakfast fallback has higher carb percentage."""
        meal = create_meal_plan("breakfast", 500)

        carbs_kcal = meal.macros["carbs_g"] * 4
        carbs_pct = carbs_kcal / 500

        assert carbs_pct >= 0.45  # Should be ~50% carbs

    def test_dinner_balanced(self) -> None:
        """Test dinner fallback is balanced."""
        meal = create_meal_plan("dinner", 600)

        protein_kcal = meal.macros["protein_g"] * 4
        carbs_kcal = meal.macros["carbs_g"] * 4
        fat_kcal = meal.macros["fat_g"] * 9

        protein_pct = protein_kcal / 600
        carbs_pct = carbs_kcal / 600
        fat_pct = fat_kcal / 600

        # Should be roughly balanced (30/40/30)
        assert 0.25 <= protein_pct <= 0.35
        assert 0.35 <= carbs_pct <= 0.45
        assert 0.25 <= fat_pct <= 0.35

    def test_snack_balanced(self) -> None:
        """Test snack fallback has balanced macros."""
        meal = create_meal_plan("snack", 200)

        # Snack should have reasonable amounts of all macros
        assert meal.macros["protein_g"] > 10
        assert meal.macros["carbs_g"] > 15
        assert meal.macros["fat_g"] > 5

    def test_keto_fallback_has_very_low_carbs(self) -> None:
        """KETO fallback meals should be very low in carbs and high in fat."""
        meal = create_meal_plan("dinner", 600, diet_flags={"KETO"})

        protein_kcal = meal.macros["protein_g"] * 4
        carbs_kcal = meal.macros["carbs_g"] * 4
        fat_kcal = meal.macros["fat_g"] * 9

        carbs_pct = carbs_kcal / 600
        fat_pct = fat_kcal / 600

        assert carbs_pct <= 0.10 + 0.02  # allow small rounding slack
        assert fat_pct >= 0.65  # high fat emphasis

    def test_low_carb_fallback_reduces_carbs_vs_default(self) -> None:
        """LOW_CARB fallback should have fewer carbs than default dinner."""
        default_meal = create_meal_plan("dinner", 600)
        low_carb_meal = create_meal_plan("dinner", 600, diet_flags={"LOW_CARB"})

        assert low_carb_meal.macros["carbs_g"] < default_meal.macros["carbs_g"]

    def test_pick_recipe_with_list_db(self) -> None:
        """Test _select_recipe_for_meal with recipe_db as a list (covers lines 147-150)."""
        from core.meal_planner import _select_recipe_for_meal

        recipe_list = [
            {
                "name": "Vegan Salad",
                "kcal": 400,
                "flags": ["VEGAN"],
                "macros": {"protein_g": 10, "carbs_g": 50, "fat_g": 15},
            },
        ]

        recipe = _select_recipe_for_meal("lunch", 400, {"VEGAN"}, recipe_list)
        assert recipe is not None
        assert recipe["name"] == "Vegan Salad"

    def test_pick_recipe_with_dict_db(self) -> None:
        """Test _select_recipe_for_meal with recipe_db as a dict (covers lines 147-150)."""
        from core.meal_planner import _select_recipe_for_meal

        recipe_dict = {
            "salad": {
                "name": "Green Salad",
                "kcal": 350,
                "flags": ["VEGAN"],
            },
        }

        recipe = _select_recipe_for_meal("dinner", 350, {"VEGAN"}, recipe_dict)
        assert recipe is not None

    def test_pick_recipe_no_compatible(self) -> None:
        """Test _select_recipe_for_meal returns None when no compatible recipes (covers line 171)."""
        from core.meal_planner import _select_recipe_for_meal

        recipe_list = [{"name": "Chicken Soup", "kcal": 400, "flags": []}]

        recipe = _select_recipe_for_meal("lunch", 400, {"VEGAN"}, recipe_list)
        assert recipe is None

    def test_convert_recipe_to_dict_with_object(self) -> None:
        """Test _convert_recipe_to_dict with recipe object (covers lines 179-191)."""
        from core.meal_planner import _convert_recipe_to_dict
        from dataclasses import dataclass

        @dataclass
        class RecipeObj:
            name: str
            kcal: int
            macros: dict
            ingredients: dict

        recipe_obj = RecipeObj(
            name="Test Recipe",
            kcal=500,
            macros={"protein_g": 20, "carbs_g": 60, "fat_g": 15},
            ingredients={"chicken": 150, "rice": 200},
        )

        result = _convert_recipe_to_dict(recipe_obj)
        assert result["name"] == "Test Recipe"
        assert result["kcal"] == 500
        assert "macros" in result
        assert "ingredients" in result

    def test_generate_shopping_list_aggregation(self) -> None:
        """Test _generate_shopping_list aggregates ingredients (covers lines 368-371)."""
        from core.meal_planner import _generate_shopping_list, DailyMealPlan, MealPlan

        meal1 = MealPlan(
            name="breakfast",
            kcal_target=500,
            recipe_name="Oatmeal",
            macros={"protein_g": 10, "carbs_g": 60, "fat_g": 8, "fiber_g": 10},
            ingredients={"oats": 50, "milk": 200},
        )
        meal2 = MealPlan(
            name="lunch",
            kcal_target=600,
            recipe_name="Salad",
            macros={"protein_g": 15, "carbs_g": 40, "fat_g": 12, "fiber_g": 8},
            ingredients={"lettuce": 100, "chicken": 150},
        )

        day1 = DailyMealPlan(
            day=1,
            total_kcal=1100,
            meals=[meal1, meal2],
            total_macros={"protein_g": 25, "carbs_g": 100, "fat_g": 20, "fiber_g": 18},
            total_cost=5.0,
        )

        meal3 = MealPlan(
            name="breakfast",
            kcal_target=500,
            recipe_name="Eggs",
            macros={"protein_g": 20, "carbs_g": 10, "fat_g": 15, "fiber_g": 2},
            ingredients={"eggs": 2, "milk": 100},  # milk overlaps with day1
        )

        day2 = DailyMealPlan(
            day=2,
            total_kcal=500,
            meals=[meal3],
            total_macros={"protein_g": 20, "carbs_g": 10, "fat_g": 15, "fiber_g": 2},
            total_cost=3.0,
        )

        shopping_list = _generate_shopping_list([day1, day2])

        # Should aggregate milk: 200 + 100 = 300
        assert shopping_list["milk"] == 300
        assert shopping_list["oats"] == 50
        assert shopping_list["chicken"] == 150
        assert shopping_list["lettuce"] == 100
        assert shopping_list["eggs"] == 2

    def test_select_recipe_exception_handling(self) -> None:
        """Test _select_recipe_for_meal exception handling (covers lines 153-154)."""
        from core.meal_planner import _select_recipe_for_meal

        # Object that raises TypeError during iteration
        class BadRecipeDB:
            def __iter__(self):
                raise TypeError("Cannot iterate this object")

        recipe = _select_recipe_for_meal("lunch", 500, {"VEGAN"}, BadRecipeDB())
        assert recipe is None  # Should catch exception and return None

    def test_convert_recipe_missing_micros(self) -> None:
        """Test _convert_recipe_to_dict with object WITH micros attr (covers line 187)."""
        from core.meal_planner import _convert_recipe_to_dict
        from dataclasses import dataclass

        @dataclass
        class RecipeWithMicros:
            name: str
            kcal: int
            macros: dict
            ingredients: dict
            micros: dict  # HAS micros attribute

        recipe_obj = RecipeWithMicros(
            name="Nutrient Recipe",
            kcal=400,
            macros={"protein_g": 15, "carbs_g": 50, "fat_g": 10},
            ingredients={"rice": 200},
            micros={"iron_mg": 5.0, "calcium_mg": 100},
        )

        result = _convert_recipe_to_dict(recipe_obj)
        assert "micros" in result  # Should include micros (line 187)
        assert result["micros"]["iron_mg"] == 5.0
        assert result["name"] == "Nutrient Recipe"

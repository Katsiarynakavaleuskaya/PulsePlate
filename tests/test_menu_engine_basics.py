"""
Basic tests for core.menu_engine module

RU: Базовые тесты для модуля движка генерации меню.
EN: Basic tests for menu generation engine module.
"""

from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from core.menu_engine import (
    DayMenu,
    FoodItem,
    Recipe,
    WeekMenu,
    _get_default_food_db,
    _get_default_recipe_db,
    make_daily_menu,
)
from core.targets import UserProfile


class TestDataClasses:
    """Test basic dataclass functionality."""

    def test_food_item_creation(self):
        """Test creating FoodItem object."""
        food = FoodItem(
            name="Apple",
            nutrients_per_100g={"carbs_g": 13.8, "protein_g": 0.3},
            cost_per_100g=1.5,
            tags=["FRUIT", "LOW_CALORIE"],
            availability_regions=["BY", "RU"],
        )

        assert food.name == "Apple"
        assert food.nutrients_per_100g["carbs_g"] == 13.8
        assert food.cost_per_100g == 1.5
        assert "FRUIT" in food.tags
        assert "BY" in food.availability_regions

    def test_recipe_creation(self):
        """Test creating Recipe object."""
        recipe = Recipe(
            name="Simple Omelette",
            ingredients={"eggs": 100, "butter": 10},
            servings=1,
            preparation_time_min=5,
            difficulty="easy",
            tags=["PROTEIN", "QUICK"],
            instructions=["Beat eggs", "Cook in butter"],
        )

        assert recipe.name == "Simple Omelette"
        assert recipe.ingredients["eggs"] == 100
        assert recipe.servings == 1
        assert recipe.preparation_time_min == 5
        assert recipe.difficulty == "easy"
        assert "PROTEIN" in recipe.tags
        assert len(recipe.instructions) == 2

    def test_recipe_calculate_nutrients_per_serving(self):
        """Test calculating nutrients per serving from ingredients."""
        # Create test food database
        food_db = {
            "eggs": FoodItem(
                name="Eggs",
                nutrients_per_100g={"protein_g": 12.6, "fat_g": 9.5},
                cost_per_100g=2.0,
                tags=[],
                availability_regions=["BY"],
            ),
            "butter": FoodItem(
                name="Butter",
                nutrients_per_100g={"protein_g": 0.9, "fat_g": 81.1},
                cost_per_100g=5.0,
                tags=[],
                availability_regions=["BY"],
            ),
        }

        recipe = Recipe(
            name="Omelette",
            ingredients={"eggs": 100, "butter": 10},  # 100g eggs + 10g butter
            servings=1,
            preparation_time_min=5,
            difficulty="easy",
            tags=["PROTEIN"],
            instructions=["Cook"],
        )

        nutrients = recipe.calculate_nutrients_per_serving(food_db)

        # Expected: (12.6 * 100/100) + (0.9 * 10/100) = 12.6 + 0.09 = 12.69
        assert abs(nutrients["protein_g"] - 12.69) < 0.01
        # Expected: (9.5 * 100/100) + (81.1 * 10/100) = 9.5 + 8.11 = 17.61
        assert abs(nutrients["fat_g"] - 17.61) < 0.01

    def test_recipe_calculate_nutrients_with_missing_ingredient(self):
        """Test calculating nutrients when ingredient is missing from food_db."""
        food_db = {
            "eggs": FoodItem(
                name="Eggs",
                nutrients_per_100g={"protein_g": 12.6},
                cost_per_100g=2.0,
                tags=[],
                availability_regions=["BY"],
            )
        }

        recipe = Recipe(
            name="Omelette",
            ingredients={"eggs": 100, "missing_ingredient": 50},
            servings=1,
            preparation_time_min=5,
            difficulty="easy",
            tags=[],
            instructions=[],
        )

        nutrients = recipe.calculate_nutrients_per_serving(food_db)

        # Should only include nutrients from eggs, ignore missing ingredient
        assert nutrients["protein_g"] == 12.6

    def test_recipe_calculate_nutrients_multiple_servings(self):
        """Test calculating nutrients per serving with multiple servings."""
        food_db = {
            "rice": FoodItem(
                name="Rice",
                nutrients_per_100g={"carbs_g": 80.0, "protein_g": 7.0},
                cost_per_100g=1.0,
                tags=[],
                availability_regions=["BY"],
            )
        }

        recipe = Recipe(
            name="Rice Bowl",
            ingredients={"rice": 200},  # 200g rice total
            servings=2,  # 2 servings
            preparation_time_min=20,
            difficulty="easy",
            tags=[],
            instructions=["Cook rice"],
        )

        nutrients = recipe.calculate_nutrients_per_serving(food_db)

        # Expected per serving: (80 * 200/100) / 2 = 160 / 2 = 80
        assert nutrients["carbs_g"] == 80.0
        # Expected per serving: (7 * 200/100) / 2 = 14 / 2 = 7
        assert nutrients["protein_g"] == 7.0

    def test_day_menu_creation(self):
        """Test creating DayMenu object."""
        day_menu = DayMenu(
            date="2024-01-01",
            meals=[{"meal": "breakfast"}, {"meal": "lunch"}],
            total_nutrients={"protein_g": 50.0, "carbs_g": 200.0},
            targets=MagicMock(),
            coverage={"protein": {"coverage": 0.8}},
            recommendations=["Add more vegetables"],
            estimated_cost=15.50,
        )

        assert day_menu.date == "2024-01-01"
        assert len(day_menu.meals) == 2
        assert day_menu.total_nutrients["protein_g"] == 50.0
        assert day_menu.estimated_cost == 15.50
        assert "Add more vegetables" in day_menu.recommendations

    def test_week_menu_creation(self):
        """Test creating WeekMenu object."""
        week_menu = WeekMenu(
            week_start="2024-01-01",
            daily_menus=[MagicMock(), MagicMock()],
            weekly_coverage={"protein": 0.85, "iron": 0.70},
            shopping_list={"chicken": 500, "rice": 1000},
            total_cost=105.75,
            adherence_score=82.5,
        )

        assert week_menu.week_start == "2024-01-01"
        assert len(week_menu.daily_menus) == 2
        assert week_menu.weekly_coverage["protein"] == 0.85
        assert week_menu.shopping_list["chicken"] == 500
        assert week_menu.total_cost == 105.75
        assert week_menu.adherence_score == 82.5


class TestDefaultDatabases:
    """Test default database functions."""

    def test_get_default_food_db_fallback(self):
        """Test getting default food database with fallback data."""
        # Mock the async functionality to force fallback
        with patch("core.menu_engine.get_unified_food_db", side_effect=Exception("Async error")):
            food_db = _get_default_food_db()

            assert isinstance(food_db, dict)
            assert len(food_db) > 0
            assert "chicken_breast" in food_db

            # Test food item structure
            chicken = food_db["chicken_breast"]
            assert isinstance(chicken, FoodItem)
            assert chicken.name == "Chicken Breast (Mock)"
            assert "protein_g" in chicken.nutrients_per_100g
            assert chicken.cost_per_100g > 0
            assert isinstance(chicken.tags, list)
            assert isinstance(chicken.availability_regions, list)

    def test_get_default_food_db_with_running_loop(self):
        """Test getting default food database when event loop is running."""
        # Mock asyncio.get_running_loop to simulate running loop
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            food_db = _get_default_food_db()

            # Should fall back to mock data when loop is running
            assert isinstance(food_db, dict)
            assert "chicken_breast" in food_db

    def test_get_default_recipe_db(self):
        """Test getting default recipe database."""
        recipe_db = _get_default_recipe_db()

        assert isinstance(recipe_db, dict)
        assert len(recipe_db) > 0

        # Check that all values are Recipe objects
        for recipe_name, recipe in recipe_db.items():
            assert isinstance(recipe, Recipe)
            assert recipe.name is not None
            assert isinstance(recipe.ingredients, dict)
            assert recipe.servings > 0
            assert recipe.preparation_time_min >= 0
            assert recipe.difficulty in ["easy", "medium", "hard"]
            assert isinstance(recipe.tags, list)
            assert isinstance(recipe.instructions, list)


class TestMakeDailyMenuBasic:
    """Test basic functionality of make_daily_menu."""

    @pytest.fixture
    def mock_profile(self):
        """Create a mock user profile."""
        return UserProfile(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            goal="maintain",
            activity="moderate",
            deficit_pct=20,
            surplus_pct=20,
            diet_flags=set(),
        )

    @pytest.fixture
    def simple_food_db(self):
        """Create a simple food database for testing."""
        return {
            "apple": FoodItem(
                name="Apple",
                nutrients_per_100g={
                    "carbs_g": 13.8,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "vitamin_c_mg": 4.6,
                },
                cost_per_100g=1.5,
                tags=["FRUIT"],
                availability_regions=["BY", "RU"],
            ),
            "chicken": FoodItem(
                name="Chicken",
                nutrients_per_100g={
                    "protein_g": 23.0,
                    "fat_g": 3.6,
                    "carbs_g": 0.0,
                    "iron_mg": 0.7,
                },
                cost_per_100g=3.0,
                tags=["PROTEIN"],
                availability_regions=["BY", "RU"],
            ),
        }

    @pytest.fixture
    def simple_recipe_db(self):
        """Create a simple recipe database for testing."""
        return {
            "grilled_chicken": Recipe(
                name="Grilled Chicken",
                ingredients={"chicken": 150},
                servings=1,
                preparation_time_min=15,
                difficulty="easy",
                tags=["PROTEIN", "LOW_CARB"],
                instructions=["Season chicken", "Grill for 15 minutes"],
            )
        }

    def test_make_daily_menu_basic(
        self,
        mock_profile,
        simple_food_db,
        simple_recipe_db,
    ):
        """Exercise daily menu generation with concrete data."""
        result = make_daily_menu(
            profile=mock_profile,
            food_db=simple_food_db,
            recipe_db=simple_recipe_db,
            target_date="2024-01-01",
        )

        assert isinstance(result, DayMenu)
        assert result.date == "2024-01-01"
        assert isinstance(result.meals, list)
        assert len(result.meals) >= 1
        assert isinstance(result.total_nutrients, dict)
        assert isinstance(result.estimated_cost, float)

    def test_make_daily_menu_with_defaults(self, mock_profile):
        """Test daily menu generation when defaults are used."""
        result = make_daily_menu(profile=mock_profile)

        assert isinstance(result, DayMenu)
        assert result.date == "today"
        assert isinstance(result.meals, list)
        assert isinstance(result.total_nutrients, dict)
        assert isinstance(result.estimated_cost, float)


class TestUtilityFunctions:
    """Test utility functions that can be tested in isolation."""

    def test_food_item_to_dict(self):
        """Test converting FoodItem to dict (using asdict)."""
        food = FoodItem(
            name="Test Food",
            nutrients_per_100g={"protein_g": 10.0},
            cost_per_100g=2.0,
            tags=["TEST"],
            availability_regions=["BY"],
        )

        food_dict = asdict(food)

        assert food_dict["name"] == "Test Food"
        assert food_dict["nutrients_per_100g"]["protein_g"] == 10.0
        assert food_dict["cost_per_100g"] == 2.0
        assert food_dict["tags"] == ["TEST"]
        assert food_dict["availability_regions"] == ["BY"]

    def test_recipe_to_dict(self):
        """Test converting Recipe to dict (using asdict)."""
        recipe = Recipe(
            name="Test Recipe",
            ingredients={"ingredient1": 100},
            servings=2,
            preparation_time_min=10,
            difficulty="easy",
            tags=["TEST"],
            instructions=["Step 1"],
        )

        recipe_dict = asdict(recipe)

        assert recipe_dict["name"] == "Test Recipe"
        assert recipe_dict["ingredients"]["ingredient1"] == 100
        assert recipe_dict["servings"] == 2
        assert recipe_dict["preparation_time_min"] == 10
        assert recipe_dict["difficulty"] == "easy"
        assert recipe_dict["tags"] == ["TEST"]
        assert recipe_dict["instructions"] == ["Step 1"]

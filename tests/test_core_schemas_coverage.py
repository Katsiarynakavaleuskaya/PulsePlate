# -*- coding: utf-8 -*-
"""
Test coverage for core/schemas.py

RU: Тесты покрытия для core/schemas.py
EN: Test coverage for core/schemas.py
"""

import pytest

from core.schemas import (
    FoodItem,
    FoodSearchRequest,
    Recipe,
    RecipeIngredient,
    RecipePreviewRequest,
    RecipePreviewResponse,
    RecipeSearchRequest,
)


class TestCoreSchemasCoverage:
    """Test suite for core/schemas.py coverage."""

    def test_food_item_creation(self):
        """Test FoodItem creation with all fields."""
        food = FoodItem(
            id="test_food_001",
            canonical_name="Test Apple",
            group="fruits",
            per_g=100.0,
            kcal=52.0,
            protein_g=0.3,
            fat_g=0.2,
            carbs_g=14.0,
            fiber_g=2.4,
            Fe_mg=0.1,
            Ca_mg=6.0,
            K_mg=107.0,
            Mg_mg=5.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=3.0,
            Iodine_ug=0.0,
            flags=["VEG", "GF"],
            brand="Test Brand",
            gtin="1234567890123",
            fdc_id="12345",
            source="USDA",
            source_priority=1,
            version_date="2024-01-01",
            price_per_100g=0.50,
        )

        assert food.id == "test_food_001"
        assert food.canonical_name == "Test Apple"
        assert food.group == "fruits"
        assert food.kcal == 52.0
        assert food.flags == ["VEG", "GF"]
        assert food.brand == "Test Brand"

    def test_food_item_minimal(self):
        """Test FoodItem creation with minimal required fields."""
        food = FoodItem(
            id="minimal_food",
            canonical_name="Minimal Food",
            group="other",
            kcal=100.0,
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=15.0,
            source="TEST",
            version_date="2024-01-01",
        )

        assert food.id == "minimal_food"
        assert food.per_g == 100.0  # default
        assert food.fiber_g == 0.0  # default
        assert food.flags == []  # default
        assert food.brand is None  # default

    def test_recipe_ingredient_creation(self):
        """Test RecipeIngredient creation."""
        ingredient = RecipeIngredient(
            food_id="test_food_001",
            grams=150.0,
        )

        assert ingredient.food_id == "test_food_001"
        assert ingredient.grams == 150.0

    def test_recipe_ingredient_validation(self):
        """Test RecipeIngredient validation."""
        # Test positive grams
        ingredient = RecipeIngredient(food_id="test", grams=100.0)
        assert ingredient.grams == 100.0

        # Test zero grams should fail
        with pytest.raises(ValueError):
            RecipeIngredient(food_id="test", grams=0.0)

        # Test negative grams should fail
        with pytest.raises(ValueError):
            RecipeIngredient(food_id="test", grams=-10.0)

    def test_recipe_creation(self):
        """Test Recipe creation with all fields."""
        ingredients = [
            RecipeIngredient(food_id="food1", grams=100.0),
            RecipeIngredient(food_id="food2", grams=200.0),
        ]

        recipe = Recipe(
            recipe_id="test_recipe_001",
            title="Test Recipe",
            locale="en",
            yield_total_g=300.0,
            servings=2,
            ingredients=ingredients,
            steps=["Step 1", "Step 2"],
            tags=["healthy", "quick"],
            allergens=["nuts"],
            cost_total=5.0,
            cost_per_serv=2.5,
            nutrients_per_serv={"kcal": 250.0, "protein_g": 15.0},
            source="TEST",
            version_date="2024-01-01",
        )

        assert recipe.recipe_id == "test_recipe_001"
        assert recipe.title == "Test Recipe"
        assert recipe.servings == 2
        assert len(recipe.ingredients) == 2
        assert recipe.tags == ["healthy", "quick"]

    def test_recipe_minimal(self):
        """Test Recipe creation with minimal required fields."""
        ingredients = [RecipeIngredient(food_id="food1", grams=100.0)]

        recipe = Recipe(
            recipe_id="minimal_recipe",
            title="Minimal Recipe",
            yield_total_g=100.0,
            servings=1,
            ingredients=ingredients,
            source="TEST",
            version_date="2024-01-01",
        )

        assert recipe.recipe_id == "minimal_recipe"
        assert recipe.locale == "en"  # default
        assert recipe.steps == []  # default
        assert recipe.tags == []  # default
        assert recipe.cost_total == 0.0  # default

    def test_recipe_validation(self):
        """Test Recipe validation."""
        # Test positive yield_total_g
        ingredients = [RecipeIngredient(food_id="food1", grams=100.0)]
        recipe = Recipe(
            recipe_id="test",
            title="Test",
            yield_total_g=100.0,
            servings=1,
            ingredients=ingredients,
            source="TEST",
            version_date="2024-01-01",
        )
        assert recipe.yield_total_g == 100.0

        # Test zero yield_total_g should fail
        with pytest.raises(ValueError):
            Recipe(
                recipe_id="test",
                title="Test",
                yield_total_g=0.0,
                servings=1,
                ingredients=ingredients,
                source="TEST",
                version_date="2024-01-01",
            )

        # Test positive servings
        recipe = Recipe(
            recipe_id="test",
            title="Test",
            yield_total_g=100.0,
            servings=2,
            ingredients=ingredients,
            source="TEST",
            version_date="2024-01-01",
        )
        assert recipe.servings == 2

        # Test zero servings should fail
        with pytest.raises(ValueError):
            Recipe(
                recipe_id="test",
                title="Test",
                yield_total_g=100.0,
                servings=0,
                ingredients=ingredients,
                source="TEST",
                version_date="2024-01-01",
            )

    def test_food_search_request_creation(self):
        """Test FoodSearchRequest creation."""
        request = FoodSearchRequest(
            query="apple",
            group="fruits",
            flags=["VEG", "GF"],
            limit=50,
            offset=10,
        )

        assert request.query == "apple"
        assert request.group == "fruits"
        assert request.flags == ["VEG", "GF"]
        assert request.limit == 50
        assert request.offset == 10

    def test_food_search_request_defaults(self):
        """Test FoodSearchRequest with default values."""
        request = FoodSearchRequest()

        assert request.query is None
        assert request.group is None
        assert request.flags is None
        assert request.limit == 20  # default
        assert request.offset == 0  # default

    def test_food_search_request_validation(self):
        """Test FoodSearchRequest validation."""
        # Test valid limit
        request = FoodSearchRequest(limit=50)
        assert request.limit == 50

        # Test limit too low should fail
        with pytest.raises(ValueError):
            FoodSearchRequest(limit=0)

        # Test limit too high should fail
        with pytest.raises(ValueError):
            FoodSearchRequest(limit=101)

        # Test valid offset
        request = FoodSearchRequest(offset=10)
        assert request.offset == 10

        # Test negative offset should fail
        with pytest.raises(ValueError):
            FoodSearchRequest(offset=-1)

    def test_recipe_search_request_creation(self):
        """Test RecipeSearchRequest creation."""
        request = RecipeSearchRequest(
            query="pasta",
            diet="vegetarian",
            max_kcal=500.0,
            tags=["quick", "healthy"],
            limit=30,
            offset=5,
        )

        assert request.query == "pasta"
        assert request.diet == "vegetarian"
        assert request.max_kcal == 500.0
        assert request.tags == ["quick", "healthy"]
        assert request.limit == 30
        assert request.offset == 5

    def test_recipe_search_request_defaults(self):
        """Test RecipeSearchRequest with default values."""
        request = RecipeSearchRequest()

        assert request.query is None
        assert request.diet is None
        assert request.max_kcal is None
        assert request.tags is None
        assert request.limit == 20  # default
        assert request.offset == 0  # default

    def test_recipe_preview_request_creation(self):
        """Test RecipePreviewRequest creation."""
        ingredients = [
            RecipeIngredient(food_id="food1", grams=100.0),
            RecipeIngredient(food_id="food2", grams=200.0),
        ]

        request = RecipePreviewRequest(
            title="Preview Recipe",
            ingredients=ingredients,
            servings=3,
            locale="ru",
        )

        assert request.title == "Preview Recipe"
        assert len(request.ingredients) == 2
        assert request.servings == 3
        assert request.locale == "ru"

    def test_recipe_preview_request_defaults(self):
        """Test RecipePreviewRequest with default locale."""
        ingredients = [RecipeIngredient(food_id="food1", grams=100.0)]

        request = RecipePreviewRequest(
            title="Test Recipe",
            ingredients=ingredients,
            servings=1,
        )

        assert request.locale == "en"  # default

    def test_recipe_preview_response_creation(self):
        """Test RecipePreviewResponse creation."""
        response = RecipePreviewResponse(
            title="Response Recipe",
            servings=2,
            total_weight_g=400.0,
            cost_total=8.0,
            cost_per_serv=4.0,
            nutrients_per_serv={"kcal": 300.0, "protein_g": 20.0},
            missing_ingredients=["unknown_food"],
        )

        assert response.title == "Response Recipe"
        assert response.servings == 2
        assert response.total_weight_g == 400.0
        assert response.cost_total == 8.0
        assert response.cost_per_serv == 4.0
        assert response.nutrients_per_serv == {"kcal": 300.0, "protein_g": 20.0}
        assert response.missing_ingredients == ["unknown_food"]

    def test_recipe_preview_response_defaults(self):
        """Test RecipePreviewResponse with default missing_ingredients."""
        response = RecipePreviewResponse(
            title="Test Recipe",
            servings=1,
            total_weight_g=200.0,
            cost_total=4.0,
            cost_per_serv=4.0,
            nutrients_per_serv={"kcal": 200.0},
        )

        assert response.missing_ingredients == []  # default

    def test_schema_serialization(self):
        """Test schema serialization to dict."""
        food = FoodItem(
            id="serialize_test",
            canonical_name="Serialize Test",
            group="test",
            kcal=100.0,
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=15.0,
            source="TEST",
            version_date="2024-01-01",
        )

        # Test to dict (using new Pydantic v2 method)
        food_dict = food.model_dump()
        assert food_dict["id"] == "serialize_test"
        assert food_dict["canonical_name"] == "Serialize Test"
        assert food_dict["kcal"] == 100.0

    def test_schema_json_serialization(self):
        """Test schema JSON serialization."""
        food = FoodItem(
            id="json_test",
            canonical_name="JSON Test",
            group="test",
            kcal=100.0,
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=15.0,
            source="TEST",
            version_date="2024-01-01",
        )

        # Test to JSON (using new Pydantic v2 method)
        food_json = food.model_dump_json()
        assert '"id":"json_test"' in food_json  # No spaces in compact JSON
        assert '"canonical_name":"JSON Test"' in food_json
        assert '"kcal":100.0' in food_json

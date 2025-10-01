"""
Tests for core.schemas module
Validation tests for Pydantic models
"""

import pytest
from pydantic import ValidationError

import core.schemas as schemas


def test_food_item_valid():
    """Test FoodItem model with valid data"""
    food = schemas.FoodItem(
        id="apple_001",
        canonical_name="red apple",
        group="fruits",
        kcal=52.0,
        protein_g=0.3,
        fat_g=0.2,
        carbs_g=14.0,
        source="USDA",
        version_date="2023-01-01",
    )

    assert food.id == "apple_001"
    assert food.canonical_name == "red apple"
    assert food.group == "fruits"
    assert food.kcal == 52.0
    assert food.protein_g == 0.3
    assert food.fat_g == 0.2
    assert food.carbs_g == 14.0
    assert food.per_g == 100.0  # Default value
    assert food.fiber_g == 0.0  # Default value
    assert food.source == "USDA"
    assert food.version_date == "2023-01-01"


def test_food_item_with_optional_fields():
    """Test FoodItem with optional micronutrient fields"""
    food = schemas.FoodItem(
        id="fortified_cereal",
        canonical_name="fortified breakfast cereal",
        group="grains",
        kcal=350.0,
        protein_g=8.0,
        fat_g=2.0,
        carbs_g=70.0,
        fiber_g=10.0,
        Fe_mg=18.0,
        Ca_mg=150.0,
        VitD_IU=40.0,
        B12_ug=6.0,
        flags=["FORTIFIED", "GF"],
        brand="TestBrand",
        source="Brand",
        version_date="2023-01-01",
    )

    assert food.fiber_g == 10.0
    assert food.Fe_mg == 18.0
    assert food.Ca_mg == 150.0
    assert food.VitD_IU == 40.0
    assert food.B12_ug == 6.0
    assert "FORTIFIED" in food.flags
    assert "GF" in food.flags
    assert food.brand == "TestBrand"


def test_food_item_required_fields():
    """Test that required fields are enforced"""
    with pytest.raises(ValidationError):
        schemas.FoodItem()  # Missing required fields

    with pytest.raises(ValidationError):
        schemas.FoodItem(
            id="test",
            canonical_name="test food",
            # Missing other required fields
        )


def test_recipe_ingredient_valid():
    """Test RecipeIngredient model"""
    ingredient = schemas.RecipeIngredient(food_id="apple_001", grams=150.0)

    assert ingredient.food_id == "apple_001"
    assert ingredient.grams == 150.0


def test_recipe_ingredient_validation():
    """Test RecipeIngredient validation"""
    # Test positive grams requirement
    with pytest.raises(ValidationError):
        schemas.RecipeIngredient(food_id="test", grams=0.0)  # Should be > 0

    with pytest.raises(ValidationError):
        schemas.RecipeIngredient(food_id="test", grams=-10.0)  # Should be > 0


def test_recipe_valid():
    """Test Recipe model with valid data"""
    ingredients = [
        schemas.RecipeIngredient(food_id="apple_001", grams=200.0),
        schemas.RecipeIngredient(food_id="oats_001", grams=50.0),
    ]

    recipe = schemas.Recipe(
        recipe_id="apple_oatmeal",
        title="Apple Oatmeal",
        yield_total_g=250.0,
        servings=2,
        ingredients=ingredients,
        steps=["Mix ingredients", "Cook for 5 minutes"],
        tags=["breakfast", "healthy"],
        source="homemade",
        version_date="2023-01-01",
    )

    assert recipe.recipe_id == "apple_oatmeal"
    assert recipe.title == "Apple Oatmeal"
    assert recipe.yield_total_g == 250.0
    assert recipe.servings == 2
    assert len(recipe.ingredients) == 2
    assert recipe.ingredients[0].food_id == "apple_001"
    assert recipe.ingredients[1].food_id == "oats_001"
    assert len(recipe.steps) == 2
    assert "breakfast" in recipe.tags
    assert recipe.locale == "en"  # Default value


def test_recipe_validation():
    """Test Recipe validation rules"""
    # Test minimum ingredients requirement
    with pytest.raises(ValidationError):
        schemas.Recipe(
            recipe_id="empty",
            title="Empty Recipe",
            yield_total_g=100.0,
            servings=1,
            ingredients=[],  # Should have min_length=1
            source="test",
            version_date="2023-01-01",
        )

    # Test positive servings requirement
    with pytest.raises(ValidationError):
        schemas.Recipe(
            recipe_id="invalid",
            title="Invalid Recipe",
            yield_total_g=100.0,
            servings=0,  # Should be > 0
            ingredients=[schemas.RecipeIngredient(food_id="test", grams=50.0)],
            source="test",
            version_date="2023-01-01",
        )

    # Test positive yield requirement
    with pytest.raises(ValidationError):
        schemas.Recipe(
            recipe_id="invalid",
            title="Invalid Recipe",
            yield_total_g=0.0,  # Should be > 0
            servings=1,
            ingredients=[schemas.RecipeIngredient(food_id="test", grams=50.0)],
            source="test",
            version_date="2023-01-01",
        )


def test_food_search_request():
    """Test FoodSearchRequest model"""
    # Test with all fields
    request = schemas.FoodSearchRequest(
        query="apple", group="fruits", flags=["ORGANIC"], limit=50, offset=10
    )

    assert request.query == "apple"
    assert request.group == "fruits"
    assert request.flags == ["ORGANIC"]
    assert request.limit == 50
    assert request.offset == 10

    # Test with defaults
    request_default = schemas.FoodSearchRequest()
    assert request_default.query is None
    assert request_default.group is None
    assert request_default.flags is None
    assert request_default.limit == 20  # Default
    assert request_default.offset == 0  # Default


def test_food_search_request_validation():
    """Test FoodSearchRequest validation"""
    # Test limit bounds
    with pytest.raises(ValidationError):
        schemas.FoodSearchRequest(limit=0)  # Should be >= 1

    with pytest.raises(ValidationError):
        schemas.FoodSearchRequest(limit=200)  # Should be <= 100

    # Test offset bounds
    with pytest.raises(ValidationError):
        schemas.FoodSearchRequest(offset=-1)  # Should be >= 0


def test_recipe_search_request():
    """Test RecipeSearchRequest model"""
    request = schemas.RecipeSearchRequest(
        query="pasta",
        diet="vegetarian",
        max_kcal=500.0,
        tags=["dinner", "italian"],
        limit=30,
        offset=5,
    )

    assert request.query == "pasta"
    assert request.diet == "vegetarian"
    assert request.max_kcal == 500.0
    assert request.tags == ["dinner", "italian"]
    assert request.limit == 30
    assert request.offset == 5


def test_recipe_preview_request():
    """Test RecipePreviewRequest model"""
    ingredients = [
        schemas.RecipeIngredient(food_id="pasta_001", grams=100.0),
        schemas.RecipeIngredient(food_id="tomato_001", grams=50.0),
    ]

    request = schemas.RecipePreviewRequest(
        title="Simple Pasta", ingredients=ingredients, servings=2, locale="en"
    )

    assert request.title == "Simple Pasta"
    assert len(request.ingredients) == 2
    assert request.servings == 2
    assert request.locale == "en"


def test_recipe_preview_request_validation():
    """Test RecipePreviewRequest validation"""
    # Test minimum ingredients requirement
    with pytest.raises(ValidationError):
        schemas.RecipePreviewRequest(
            title="Empty", ingredients=[], servings=1  # Should have min_length=1
        )

    # Test positive servings requirement
    with pytest.raises(ValidationError):
        schemas.RecipePreviewRequest(
            title="Invalid",
            ingredients=[schemas.RecipeIngredient(food_id="test", grams=50.0)],
            servings=0,  # Should be > 0
        )


def test_recipe_preview_response():
    """Test RecipePreviewResponse model"""
    response = schemas.RecipePreviewResponse(
        title="Test Recipe",
        servings=2,
        total_weight_g=300.0,
        cost_total=5.50,
        cost_per_serv=2.75,
        nutrients_per_serv={"kcal": 250.0, "protein_g": 15.0},
        missing_ingredients=["exotic_spice"],
    )

    assert response.title == "Test Recipe"
    assert response.servings == 2
    assert response.total_weight_g == 300.0
    assert response.cost_total == 5.50
    assert response.cost_per_serv == 2.75
    assert response.nutrients_per_serv["kcal"] == 250.0
    assert response.nutrients_per_serv["protein_g"] == 15.0
    assert "exotic_spice" in response.missing_ingredients


def test_recipe_preview_response_defaults():
    """Test RecipePreviewResponse with default values"""
    response = schemas.RecipePreviewResponse(
        title="Minimal Recipe",
        servings=1,
        total_weight_g=100.0,
        cost_total=2.00,
        cost_per_serv=2.00,
        nutrients_per_serv={"kcal": 100.0},
    )

    assert response.missing_ingredients == []  # Default empty list


@pytest.mark.parametrize(
    "model_class,valid_data",
    [
        (
            schemas.FoodItem,
            {
                "id": "test",
                "canonical_name": "test food",
                "group": "test",
                "kcal": 100.0,
                "protein_g": 5.0,
                "fat_g": 2.0,
                "carbs_g": 15.0,
                "source": "test",
                "version_date": "2023-01-01",
            },
        ),
        (schemas.RecipeIngredient, {"food_id": "test", "grams": 100.0}),
        (schemas.FoodSearchRequest, {}),
        (schemas.RecipeSearchRequest, {}),
    ],
)
def test_model_instantiation(model_class, valid_data):
    """Test that all models can be instantiated with valid data"""
    instance = model_class(**valid_data)
    assert instance is not None


def test_nested_model_validation():
    """Test validation of nested models"""
    # Test Recipe with invalid RecipeIngredient
    with pytest.raises(ValidationError):
        schemas.Recipe(
            recipe_id="test",
            title="Test Recipe",
            yield_total_g=100.0,
            servings=1,
            ingredients=[
                schemas.RecipeIngredient(food_id="valid", grams=50.0),
                {"food_id": "invalid", "grams": -10.0},  # Invalid grams
            ],
            source="test",
            version_date="2023-01-01",
        )


def test_default_values():
    """Test that default values are properly set"""
    # FoodItem defaults
    food = schemas.FoodItem(
        id="test",
        canonical_name="test",
        group="test",
        kcal=100.0,
        protein_g=5.0,
        fat_g=2.0,
        carbs_g=15.0,
        source="test",
        version_date="2023-01-01",
    )

    assert food.per_g == 100.0
    assert food.fiber_g == 0.0
    assert food.Fe_mg == 0.0
    assert food.Ca_mg == 0.0
    assert food.flags == []
    assert food.brand is None

    # Recipe defaults
    recipe = schemas.Recipe(
        recipe_id="test",
        title="test",
        yield_total_g=100.0,
        servings=1,
        ingredients=[schemas.RecipeIngredient(food_id="test", grams=50.0)],
        source="test",
        version_date="2023-01-01",
    )

    assert recipe.locale == "en"
    assert recipe.steps == []
    assert recipe.tags == []
    assert recipe.allergens == []
    assert recipe.cost_total == 0.0
    assert recipe.nutrients_per_serv == {}


def test_field_types():
    """Test that fields have correct types"""
    food = schemas.FoodItem(
        id="test",
        canonical_name="test",
        group="test",
        kcal=100,
        protein_g=5,
        fat_g=2,
        carbs_g=15,  # Using int values
        source="test",
        version_date="2023-01-01",
    )

    # Should convert to float
    assert isinstance(food.kcal, float)
    assert isinstance(food.protein_g, float)
    assert isinstance(food.fat_g, float)
    assert isinstance(food.carbs_g, float)


def test_model_serialization():
    """Test that models can be serialized"""
    food = schemas.FoodItem(
        id="test",
        canonical_name="test",
        group="test",
        kcal=100.0,
        protein_g=5.0,
        fat_g=2.0,
        carbs_g=15.0,
        source="test",
        version_date="2023-01-01",
    )

    # Test dict conversion
    food_dict = food.model_dump()
    assert isinstance(food_dict, dict)
    assert food_dict["id"] == "test"
    assert food_dict["kcal"] == 100.0

    # Test JSON serialization
    food_json = food.model_dump_json()
    assert isinstance(food_json, str)
    assert "test" in food_json

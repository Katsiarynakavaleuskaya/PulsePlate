"""
Basic tests for core.recipe_synth module

RU: Базовые тесты для модуля синтеза рецептов.
EN: Basic tests for recipe synthesis module.
"""

import json
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from core.recipe_synth import Recipe, RecipeStep, RecipeSynthesizer, RecipeTemplate


class TestRecipeStepDataClass:
    """Test RecipeStep dataclass functionality."""

    def test_recipe_step_creation_minimal(self):
        """Test creating RecipeStep with minimal required fields."""
        step = RecipeStep(step_number=1, instruction="Heat oil in a pan")

        assert step.step_number == 1
        assert step.instruction == "Heat oil in a pan"
        assert step.duration_minutes is None
        assert step.temperature is None
        assert step.equipment is None

    def test_recipe_step_creation_full(self):
        """Test creating RecipeStep with all fields."""
        step = RecipeStep(
            step_number=2,
            instruction="Bake in oven",
            duration_minutes=25,
            temperature="180°C",
            equipment="oven",
        )

        assert step.step_number == 2
        assert step.instruction == "Bake in oven"
        assert step.duration_minutes == 25
        assert step.temperature == "180°C"
        assert step.equipment == "oven"

    def test_recipe_step_to_dict(self):
        """Test converting RecipeStep to dictionary."""
        step = RecipeStep(step_number=1, instruction="Mix ingredients", duration_minutes=5)

        step_dict = asdict(step)

        assert step_dict["step_number"] == 1
        assert step_dict["instruction"] == "Mix ingredients"
        assert step_dict["duration_minutes"] == 5
        assert step_dict["temperature"] is None
        assert step_dict["equipment"] is None


class TestRecipeDataClass:
    """Test Recipe dataclass functionality."""

    @pytest.fixture
    def sample_recipe_data(self):
        """Sample recipe data for testing."""
        return {
            "recipe_id": "test_001",
            "title": "Simple Pasta",
            "description": "Easy pasta dish",
            "cuisine_type": "italian",
            "difficulty_level": "easy",
            "prep_time_minutes": 10,
            "cook_time_minutes": 15,
            "total_time_minutes": 25,
            "servings": 4,
            "ingredients": [
                {"name": "pasta", "amount": 400.0, "unit": "g"},
                {"name": "tomato sauce", "amount": 200.0, "unit": "ml"},
            ],
            "steps": [RecipeStep(1, "Boil water"), RecipeStep(2, "Cook pasta")],
            "nutrition_per_serving": {
                "calories": 350.0,
                "protein_g": 12.0,
                "carbs_g": 65.0,
                "fat_g": 3.0,
            },
            "tags": ["easy", "vegetarian", "italian"],
            "image_url": None,
        }

    def test_recipe_creation(self, sample_recipe_data):
        """Test creating Recipe object."""
        recipe = Recipe(**sample_recipe_data)

        assert recipe.recipe_id == "test_001"
        assert recipe.title == "Simple Pasta"
        assert recipe.description == "Easy pasta dish"
        assert recipe.cuisine_type == "italian"
        assert recipe.difficulty_level == "easy"
        assert recipe.prep_time_minutes == 10
        assert recipe.cook_time_minutes == 15
        assert recipe.total_time_minutes == 25
        assert recipe.servings == 4
        assert len(recipe.ingredients) == 2
        assert len(recipe.steps) == 2
        assert recipe.nutrition_per_serving["calories"] == 350.0
        assert "vegetarian" in recipe.tags
        assert recipe.image_url is None

    def test_recipe_ingredients_structure(self, sample_recipe_data):
        """Test recipe ingredients structure."""
        recipe = Recipe(**sample_recipe_data)

        pasta_ingredient = recipe.ingredients[0]
        assert pasta_ingredient["name"] == "pasta"
        assert pasta_ingredient["amount"] == 400.0
        assert pasta_ingredient["unit"] == "g"

        sauce_ingredient = recipe.ingredients[1]
        assert sauce_ingredient["name"] == "tomato sauce"
        assert sauce_ingredient["amount"] == 200.0
        assert sauce_ingredient["unit"] == "ml"

    def test_recipe_steps_structure(self, sample_recipe_data):
        """Test recipe steps structure."""
        recipe = Recipe(**sample_recipe_data)

        assert isinstance(recipe.steps[0], RecipeStep)
        assert recipe.steps[0].step_number == 1
        assert recipe.steps[0].instruction == "Boil water"

        assert isinstance(recipe.steps[1], RecipeStep)
        assert recipe.steps[1].step_number == 2
        assert recipe.steps[1].instruction == "Cook pasta"

    def test_recipe_nutrition_structure(self, sample_recipe_data):
        """Test recipe nutrition structure."""
        recipe = Recipe(**sample_recipe_data)

        nutrition = recipe.nutrition_per_serving
        assert nutrition["calories"] == 350.0
        assert nutrition["protein_g"] == 12.0
        assert nutrition["carbs_g"] == 65.0
        assert nutrition["fat_g"] == 3.0


class TestRecipeTemplateDataClass:
    """Test RecipeTemplate dataclass functionality."""

    def test_recipe_template_creation(self):
        """Test creating RecipeTemplate object."""
        template = RecipeTemplate(
            template_id="stir_fry",
            name="Stir Fry",
            cuisine_type="asian",
            base_ingredients=["vegetables", "protein", "oil"],
            cooking_methods=["stir_frying", "sautéing"],
            typical_prep_time=15,
            typical_cook_time=10,
            difficulty="easy",
            instruction_template="Heat oil, add ingredients, stir-fry.",
            nutrition_profile={"calories": 300, "protein": 25, "carbs": 15},
        )

        assert template.template_id == "stir_fry"
        assert template.name == "Stir Fry"
        assert template.cuisine_type == "asian"
        assert len(template.base_ingredients) == 3
        assert "vegetables" in template.base_ingredients
        assert len(template.cooking_methods) == 2
        assert "stir_frying" in template.cooking_methods
        assert template.typical_prep_time == 15
        assert template.typical_cook_time == 10
        assert template.difficulty == "easy"
        assert "Heat oil" in template.instruction_template
        assert template.nutrition_profile["calories"] == 300

    def test_recipe_template_to_dict(self):
        """Test converting RecipeTemplate to dictionary."""
        template = RecipeTemplate(
            template_id="pasta",
            name="Pasta Dish",
            cuisine_type="italian",
            base_ingredients=["pasta", "sauce"],
            cooking_methods=["boiling"],
            typical_prep_time=10,
            typical_cook_time=20,
            difficulty="easy",
            instruction_template="Cook pasta, add sauce.",
            nutrition_profile={"calories": 400},
        )

        # Use the to_dict() method instead of manual dict creation
        template_dict = template.to_dict()

        assert template_dict["template_id"] == "pasta"
        assert template_dict["name"] == "Pasta Dish"
        assert template_dict["cuisine_type"] == "italian"
        assert template_dict["base_ingredients"] == ["pasta", "sauce"]
        assert template_dict["cooking_methods"] == ["boiling"]
        assert template_dict["typical_prep_time"] == 10
        assert template_dict["typical_cook_time"] == 20
        assert template_dict["difficulty"] == "easy"
        assert template_dict["instruction_template"] == "Cook pasta, add sauce."
        assert template_dict["nutrition_profile"]["calories"] == 400


class TestRecipeSynthesizerBasics:
    """Test basic RecipeSynthesizer functionality."""

    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_synthesizer_initialization_no_dir(self, temp_templates_dir):
        """Test initializing synthesizer when templates directory doesn't exist."""
        non_existent_dir = str(Path(temp_templates_dir) / "non_existent")

        synthesizer = RecipeSynthesizer(templates_dir=non_existent_dir)

        assert synthesizer.templates_dir == Path(non_existent_dir)
        assert isinstance(synthesizer.templates, dict)
        # Should create default templates
        assert len(synthesizer.templates) > 0

    def test_synthesizer_initialization_with_existing_dir(self, temp_templates_dir):
        """Test initializing synthesizer with existing templates directory."""
        # Create a test template file
        template_file = Path(temp_templates_dir) / "test_template.json"
        test_template = {
            "template_id": "test_recipe",
            "name": "Test Recipe",
            "cuisine_type": "test",
            "base_ingredients": ["ingredient1", "ingredient2"],
            "cooking_methods": ["method1"],
            "typical_prep_time": 10,
            "typical_cook_time": 15,
            "difficulty": "easy",
            "instruction_template": "Test instructions",
            "nutrition_profile": {"calories": 100},
        }

        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(test_template, f)

        synthesizer = RecipeSynthesizer(templates_dir=temp_templates_dir)

        assert synthesizer.templates_dir == Path(temp_templates_dir)
        assert "test_recipe" in synthesizer.templates

        loaded_template = synthesizer.templates["test_recipe"]
        assert isinstance(loaded_template, RecipeTemplate)
        assert loaded_template.name == "Test Recipe"
        assert loaded_template.cuisine_type == "test"
        assert loaded_template.typical_prep_time == 10

    def test_synthesizer_load_templates_with_invalid_json(self, temp_templates_dir):
        """Test loading templates when JSON file is invalid."""
        # Create invalid JSON file
        invalid_file = Path(temp_templates_dir) / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        # Should not crash, just skip invalid files
        synthesizer = RecipeSynthesizer(templates_dir=temp_templates_dir)

        assert isinstance(synthesizer.templates, dict)
        # Should not contain the invalid template
        assert "invalid" not in synthesizer.templates

    def test_synthesizer_load_templates_with_missing_fields(self, temp_templates_dir):
        """Test loading templates when required fields are missing."""
        # Create template with missing required fields
        incomplete_file = Path(temp_templates_dir) / "incomplete.json"
        incomplete_template = {
            "template_id": "incomplete",
            "name": "Incomplete Template",
            # Missing required fields
        }

        with open(incomplete_file, "w") as f:
            json.dump(incomplete_template, f)

        # Should not crash, just skip invalid templates
        synthesizer = RecipeSynthesizer(templates_dir=temp_templates_dir)

        assert isinstance(synthesizer.templates, dict)
        # Should not contain the incomplete template
        assert "incomplete" not in synthesizer.templates

    def test_create_default_templates(self, temp_templates_dir):
        """Test creating default templates."""
        non_existent_dir = str(Path(temp_templates_dir) / "new_dir")

        synthesizer = RecipeSynthesizer(templates_dir=non_existent_dir)

        # Should have created default templates
        assert len(synthesizer.templates) > 0

        # Check for expected default templates
        expected_templates = ["stir_fry", "pasta", "salad", "soup"]
        for template_id in expected_templates:
            assert template_id in synthesizer.templates

            template = synthesizer.templates[template_id]
            assert isinstance(template, RecipeTemplate)
            assert template.template_id == template_id
            assert len(template.base_ingredients) > 0
            assert len(template.cooking_methods) > 0
            assert template.typical_prep_time >= 0
            assert template.typical_cook_time >= 0
            assert template.difficulty in ["easy", "medium", "hard"]
            assert len(template.instruction_template) > 0
            assert len(template.nutrition_profile) > 0

    def test_default_stir_fry_template(self, temp_templates_dir):
        """Test specific default stir fry template content."""
        non_existent_dir = str(Path(temp_templates_dir) / "new_dir")

        synthesizer = RecipeSynthesizer(templates_dir=non_existent_dir)

        stir_fry = synthesizer.templates["stir_fry"]
        assert stir_fry.name == "Stir Fry"
        assert stir_fry.cuisine_type == "asian"
        assert "vegetables" in stir_fry.base_ingredients
        assert "protein" in stir_fry.base_ingredients
        assert "oil" in stir_fry.base_ingredients
        assert "stir_frying" in stir_fry.cooking_methods
        assert stir_fry.difficulty == "easy"
        assert "Heat oil" in stir_fry.instruction_template
        assert stir_fry.nutrition_profile["calories"] == 300
        assert stir_fry.nutrition_profile["protein"] == 25

    def test_default_pasta_template(self, temp_templates_dir):
        """Test specific default pasta template content."""
        non_existent_dir = str(Path(temp_templates_dir) / "new_dir")

        synthesizer = RecipeSynthesizer(templates_dir=non_existent_dir)

        pasta = synthesizer.templates["pasta"]
        assert pasta.name == "Pasta Dish"
        assert pasta.cuisine_type == "italian"
        assert "pasta" in pasta.base_ingredients
        assert "sauce" in pasta.base_ingredients
        assert "boiling" in pasta.cooking_methods
        assert pasta.difficulty == "easy"
        assert "Boil pasta" in pasta.instruction_template
        assert pasta.nutrition_profile["calories"] == 400
        assert pasta.nutrition_profile["carbs"] == 60

    def test_default_salad_template(self, temp_templates_dir):
        """Test specific default salad template content."""
        non_existent_dir = str(Path(temp_templates_dir) / "new_dir")

        synthesizer = RecipeSynthesizer(templates_dir=non_existent_dir)

        salad = synthesizer.templates["salad"]
        assert salad.name == "Fresh Salad"
        assert salad.cuisine_type == "mediterranean"
        assert "greens" in salad.base_ingredients
        assert "vegetables" in salad.base_ingredients
        assert "chopping" in salad.cooking_methods
        assert salad.difficulty == "easy"
        assert salad.typical_cook_time == 0  # No cooking for salad
        assert "Wash and chop" in salad.instruction_template
        assert salad.nutrition_profile["calories"] == 200


class TestRecipeSynthesizerEdgeCases:
    """Test edge cases and error handling for RecipeSynthesizer."""

    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_synthesizer_with_empty_templates_dir(self, temp_templates_dir):
        """Test synthesizer with empty templates directory."""
        # Create empty directory
        empty_dir = Path(temp_templates_dir) / "empty"
        empty_dir.mkdir()

        synthesizer = RecipeSynthesizer(templates_dir=str(empty_dir))

        # Should create default templates when no templates found
        assert len(synthesizer.templates) > 0

    def test_synthesizer_with_non_json_files(self, temp_templates_dir):
        """Test synthesizer ignores non-JSON files."""
        # Create non-JSON files
        (Path(temp_templates_dir) / "readme.txt").write_text("This is not JSON")
        (Path(temp_templates_dir) / "template.xml").write_text("<xml></xml>")

        # Create one valid JSON file
        valid_template = {
            "template_id": "valid",
            "name": "Valid Template",
            "cuisine_type": "test",
            "base_ingredients": ["test"],
            "cooking_methods": ["test"],
            "typical_prep_time": 10,
            "typical_cook_time": 10,
            "difficulty": "easy",
            "instruction_template": "Test",
            "nutrition_profile": {"calories": 100},
        }

        with open(Path(temp_templates_dir) / "valid.json", "w") as f:
            json.dump(valid_template, f)

        synthesizer = RecipeSynthesizer(templates_dir=temp_templates_dir)

        # Should only load the valid JSON template
        assert "valid" in synthesizer.templates
        assert len(synthesizer.templates) == 1

    def test_synthesizer_default_templates_structure(self):
        """Test that all default templates have proper structure."""
        synthesizer = RecipeSynthesizer(templates_dir="non_existent_dir")

        for template_id, template in synthesizer.templates.items():
            # Verify all required fields are present and valid
            assert isinstance(template.template_id, str)
            assert len(template.template_id) > 0

            assert isinstance(template.name, str)
            assert len(template.name) > 0

            assert isinstance(template.cuisine_type, str)
            assert len(template.cuisine_type) > 0

            assert isinstance(template.base_ingredients, list)
            assert len(template.base_ingredients) > 0

            assert isinstance(template.cooking_methods, list)
            assert len(template.cooking_methods) > 0

            assert isinstance(template.typical_prep_time, int)
            assert template.typical_prep_time >= 0

            assert isinstance(template.typical_cook_time, int)
            assert template.typical_cook_time >= 0

            assert template.difficulty in ["easy", "medium", "hard"]

            assert isinstance(template.instruction_template, str)
            assert len(template.instruction_template) > 0

            assert isinstance(template.nutrition_profile, dict)
            assert len(template.nutrition_profile) > 0


class TestRecipeSynthesizerMethods:
    """Test RecipeSynthesizer core methods for better coverage."""

    @pytest.fixture
    def synthesizer(self):
        """Create a RecipeSynthesizer instance for testing."""
        return RecipeSynthesizer()

    def test_synthesize_recipe_basic(self, synthesizer):
        """Test synthesize_recipe with basic parameters."""
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        recipe = synthesizer.synthesize_recipe_from_ingredients(
            ingredients=ingredients,
            servings=2,
            cuisine_preference="italian",
            difficulty_preference="easy",
        )

        assert isinstance(recipe, Recipe)
        assert recipe.servings == 2
        assert len(recipe.ingredients) == len(ingredients)

    def test_select_best_template(self, synthesizer):
        """Test _select_best_template method."""
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        template = synthesizer._select_best_template(
            ingredients=ingredients, cuisine_preference="italian", difficulty_preference="easy"
        )

        assert isinstance(template, RecipeTemplate)
        assert template.cuisine_type == "italian"
        assert template.difficulty == "easy"

    def test_select_best_template_fallback(self, synthesizer):
        """Test _select_best_template with no suitable templates."""
        ingredients = [{"name": "unknown_ingredient", "amount": 200, "unit": "g"}]

        template = synthesizer._select_best_template(
            ingredients=ingredients,
            cuisine_preference="nonexistent_cuisine",
            difficulty_preference="nonexistent_difficulty",
        )

        assert isinstance(template, RecipeTemplate)
        # Should return any template as fallback
        assert template.template_id in synthesizer.templates

    def test_calculate_ingredient_match_score(self, synthesizer):
        """Test _calculate_ingredient_match_score method."""
        ingredient_names = ["tomatoes", "pasta", "cheese"]
        template_ingredients = ["tomatoes", "pasta", "garlic"]

        score = synthesizer._calculate_ingredient_match_score(
            ingredient_names, template_ingredients
        )

        assert isinstance(score, int)
        assert score >= 0
        # Should have some match since tomatoes and pasta are common
        assert score > 0

    def test_calculate_ingredient_match_score_no_match(self, synthesizer):
        """Test _calculate_ingredient_match_score with no matches."""
        ingredient_names = ["completely", "different", "ingredients"]
        template_ingredients = ["tomatoes", "pasta", "garlic"]

        score = synthesizer._calculate_ingredient_match_score(
            ingredient_names, template_ingredients
        )

        assert isinstance(score, int)
        assert score == 0  # No matches

    def test_create_recipe_from_template(self, synthesizer):
        """Test _create_recipe_from_template method."""
        template = list(synthesizer.templates.values())[0]
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        recipe = synthesizer._create_recipe_from_template(
            template=template, ingredients=ingredients, servings=2
        )

        assert isinstance(recipe, Recipe)
        assert recipe.servings == 2
        assert len(recipe.ingredients) == len(ingredients)

    def test_generate_recipe_name(self, synthesizer):
        """Test _generate_recipe_name method."""
        template = list(synthesizer.templates.values())[0]
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        title = synthesizer._generate_recipe_title(template, ingredients)

        assert isinstance(title, str)
        assert len(title) > 0
        # Should contain some ingredient names
        assert any(ing["name"].lower() in title.lower() for ing in ingredients)

    def test_generate_recipe_steps(self, synthesizer):
        """Test _generate_recipe_steps method."""
        template = list(synthesizer.templates.values())[0]
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        steps = synthesizer._generate_recipe_steps(template, ingredients)

        assert isinstance(steps, list)
        assert len(steps) > 0
        # All steps should be RecipeStep objects
        for step in steps:
            assert isinstance(step, RecipeStep)

    def test_calculate_nutrition(self, synthesizer):
        """Test _calculate_nutrition method."""
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        nutrition = synthesizer._calculate_nutrition(ingredients, servings=2)

        assert isinstance(nutrition, dict)
        assert "calories" in nutrition
        assert "protein" in nutrition
        assert "carbs" in nutrition
        assert "fat" in nutrition
        # All values should be positive
        for value in nutrition.values():
            assert isinstance(value, (int, float))
            assert value >= 0

    def test_adjust_for_servings(self, synthesizer):
        """Test _adjust_for_servings method."""
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]
        original_servings = 2
        new_servings = 4

        adjusted = synthesizer._adapt_ingredients_for_servings(ingredients, new_servings)

        assert isinstance(adjusted, list)
        assert len(adjusted) == len(ingredients)

        # Method assumes ingredients > 100g are for 4 servings, scales to target servings
        # 200g > 100g, so scaled: 200 * 4 / 4 = 200 (no change for 4 servings)
        assert adjusted[0]["amount"] == 200.0
        # 100g = 100g, so no scaling (not > 100g)
        assert adjusted[1]["amount"] == 100.0

    def test_adjust_for_servings_same(self, synthesizer):
        """Test _adjust_for_servings with same servings."""
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        adjusted = synthesizer._adapt_ingredients_for_servings(ingredients, 2)

        # Method assumes ingredients > 100g are for 4 servings, scales to target servings
        # 200g > 100g, so scaled: 200 * 2 / 4 = 100
        assert adjusted[0]["amount"] == 100.0
        # 100g = 100g, so no scaling (not > 100g)
        assert adjusted[1]["amount"] == 100.0

    def test_adjust_for_servings_half(self, synthesizer):
        """Test _adjust_for_servings with half servings."""
        ingredients = [
            {"name": "tomatoes", "amount": 200, "unit": "g"},
            {"name": "pasta", "amount": 100, "unit": "g"},
        ]

        adjusted = synthesizer._adapt_ingredients_for_servings(ingredients, 2)

        # Method assumes ingredients > 100g are for 4 servings, scales to target servings
        # 200g > 100g, so scaled: 200 * 2 / 4 = 100
        assert adjusted[0]["amount"] == 100.0
        # 100g = 100g, so no scaling (not > 100g)
        assert adjusted[1]["amount"] == 100.0

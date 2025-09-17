# -*- coding: utf-8 -*-
"""
Tests for Sprint 4: Recipe Synthesis functionality

RU: Тесты для функциональности синтеза рецептов
EN: Tests for recipe synthesis functionality
"""

from pathlib import Path
from unittest.mock import mock_open, patch

from core.recipe_synth import (
    Recipe,
    RecipeStep,
    RecipeSynthesizer,
    RecipeTemplate,
    get_recipe_synthesizer,
    synthesize_recipe_from_ingredients,
    synthesize_recipes_for_week,
)


class TestRecipeStep:
    """Тесты для класса RecipeStep"""

    def test_recipe_step_creation(self):
        """Тест создания шага рецепта"""
        step = RecipeStep(
            step_number=1,
            instruction="Heat oil in a pan",
            duration_minutes=5,
            temperature="Medium",
            equipment="Large Pan",
        )

        assert step.step_number == 1
        assert step.instruction == "Heat oil in a pan"
        assert step.duration_minutes == 5
        assert step.temperature == "Medium"
        assert step.equipment == "Large Pan"


class TestRecipe:
    """Тесты для класса Recipe"""

    def test_recipe_creation(self):
        """Тест создания рецепта"""
        ingredients = [
            {"name": "Tomato", "amount": 200, "unit": "g"},
            {"name": "Onion", "amount": 100, "unit": "g"},
        ]

        steps = [RecipeStep(1, "Chop vegetables", 10), RecipeStep(2, "Cook in pan", 15)]

        recipe = Recipe(
            recipe_id="test_001",
            title="Test Recipe",
            description="A test recipe",
            cuisine_type="international",
            difficulty_level="easy",
            prep_time_minutes=10,
            cook_time_minutes=15,
            total_time_minutes=25,
            servings=4,
            ingredients=ingredients,
            steps=steps,
            nutrition_per_serving={
                "calories": 150,
                "protein": 5,
                "carbs": 20,
                "fat": 6,
            },
            tags=["vegetarian", "healthy"],
        )

        assert recipe.recipe_id == "test_001"
        assert recipe.title == "Test Recipe"
        assert recipe.cuisine_type == "international"
        assert recipe.difficulty_level == "easy"
        assert recipe.servings == 4
        assert len(recipe.ingredients) == 2
        assert len(recipe.steps) == 2
        assert recipe.nutrition_per_serving["calories"] == 150


class TestRecipeTemplate:
    """Тесты для класса RecipeTemplate"""

    def test_recipe_template_creation(self):
        """Тест создания шаблона рецепта"""
        template = RecipeTemplate(
            template_id="stir_fry",
            name="Stir Fry",
            cuisine_type="asian",
            base_ingredients=["vegetables", "protein", "oil"],
            cooking_methods=["stir_frying"],
            typical_prep_time=15,
            typical_cook_time=10,
            difficulty="easy",
            instruction_template="Heat oil and cook ingredients",
            nutrition_profile={"calories": 300, "protein": 25},
        )

        assert template.template_id == "stir_fry"
        assert template.name == "Stir Fry"
        assert template.cuisine_type == "asian"
        assert len(template.base_ingredients) == 3
        assert template.difficulty == "easy"
        assert template.nutrition_profile["calories"] == 300


class TestRecipeSynthesizer:
    """Тесты для класса RecipeSynthesizer"""

    def test_init_with_default_templates_dir(self):
        """Тест инициализации с директорией по умолчанию"""
        synthesizer = RecipeSynthesizer()

        assert synthesizer.templates_dir == Path("data/recipe_templates")
        assert isinstance(synthesizer.templates, dict)
        assert len(synthesizer.templates) > 0  # Должны быть шаблоны по умолчанию

    def test_init_with_custom_templates_dir(self):
        """Тест инициализации с пользовательской директорией"""
        synthesizer = RecipeSynthesizer("custom/templates")

        assert synthesizer.templates_dir == Path("custom/templates")
        assert isinstance(synthesizer.templates, dict)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_load_templates_from_file(self, mock_json_load, mock_file, mock_exists):
        """Тест загрузки шаблонов из файла"""
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "template_id": "test_template",
            "name": "Test Template",
            "cuisine_type": "test",
            "base_ingredients": ["ingredient1"],
            "cooking_methods": ["method1"],
            "typical_prep_time": 10,
            "typical_cook_time": 5,
            "difficulty": "easy",
            "instruction_template": "Test instruction",
            "nutrition_profile": {"calories": 200},
        }

        synthesizer = RecipeSynthesizer()

        # Проверяем, что шаблон загрузился
        assert "test_template" in synthesizer.templates

    def test_select_best_template(self):
        """Тест выбора лучшего шаблона"""
        synthesizer = RecipeSynthesizer()

        ingredients = [
            {"name": "chicken", "amount": 300, "unit": "g"},
            {"name": "vegetables", "amount": 200, "unit": "g"},
        ]

        template = synthesizer._select_best_template(ingredients, "asian", "easy")

        assert template is not None
        assert isinstance(template, RecipeTemplate)

    def test_calculate_ingredient_match_score(self):
        """Тест вычисления оценки совпадения ингредиентов"""
        synthesizer = RecipeSynthesizer()

        ingredient_names = ["chicken", "vegetables", "oil"]
        template_ingredients = ["protein", "vegetables", "oil"]

        score = synthesizer._calculate_ingredient_match_score(
            ingredient_names, template_ingredients
        )

        assert score >= 0
        assert score <= len(template_ingredients)

    def test_adapt_ingredients_for_servings(self):
        """Тест адаптации ингредиентов под количество порций"""
        synthesizer = RecipeSynthesizer()

        ingredients = [
            {"name": "chicken", "amount": 400, "unit": "g"},
            {"name": "rice", "amount": 200, "unit": "g"},
        ]

        adapted = synthesizer._adapt_ingredients_for_servings(ingredients, 2)

        assert len(adapted) == 2
        # Проверяем, что количество изменилось
        assert adapted[0]["amount"] == 200  # 400 * 2 / 4 = 200
        assert adapted[1]["amount"] == 100  # 200 * 2 / 4 = 100

    def test_generate_recipe_steps(self):
        """Тест генерации шагов рецепта"""
        synthesizer = RecipeSynthesizer()

        template = RecipeTemplate(
            template_id="test",
            name="Test",
            cuisine_type="test",
            base_ingredients=["ingredient1"],
            cooking_methods=["method1"],
            typical_prep_time=10,
            typical_cook_time=5,
            difficulty="easy",
            instruction_template="Step 1. Step 2. Step 3.",
            nutrition_profile={"calories": 200},
        )

        ingredients = [{"name": "test", "amount": 100, "unit": "g"}]

        steps = synthesizer._generate_recipe_steps(template, ingredients)

        assert len(steps) >= 1
        assert all(isinstance(step, RecipeStep) for step in steps)
        assert all(step.step_number > 0 for step in steps)

    def test_estimate_step_duration(self):
        """Тест оценки продолжительности шага"""
        synthesizer = RecipeSynthesizer()

        template = RecipeTemplate(
            template_id="test",
            name="Test",
            cuisine_type="test",
            base_ingredients=["ingredient1"],
            cooking_methods=["method1"],
            typical_prep_time=10,
            typical_cook_time=5,
            difficulty="easy",
            instruction_template="Test",
            nutrition_profile={"calories": 200},
        )

        # Тест различных типов инструкций
        assert synthesizer._estimate_step_duration("Marinate for 30 minutes", template) == 30
        assert synthesizer._estimate_step_duration("Simmer for 20 minutes", template) == 20
        assert synthesizer._estimate_step_duration("Grill the meat", template) == 10
        assert synthesizer._estimate_step_duration("Chop vegetables", template) == 5
        assert synthesizer._estimate_step_duration("Add salt", template) == 2

    def test_extract_temperature(self):
        """Тест извлечения информации о температуре"""
        synthesizer = RecipeSynthesizer()

        assert synthesizer._extract_temperature("Heat on high heat") == "High"
        assert synthesizer._extract_temperature("Cook on medium heat") == "Medium"
        assert synthesizer._extract_temperature("Simmer on low heat") == "Low"
        assert synthesizer._extract_temperature("Preheat the oven") == "Preheated"
        assert synthesizer._extract_temperature("Add ingredients") is None

    def test_extract_equipment(self):
        """Тест извлечения информации об оборудовании"""
        synthesizer = RecipeSynthesizer()

        assert synthesizer._extract_equipment("Heat oil in a wok") == "Wok or Large Pan"
        assert synthesizer._extract_equipment("Boil water in a pot") == "Large Pot"
        assert synthesizer._extract_equipment("Grill the meat") == "Grill"
        assert synthesizer._extract_equipment("Mix in a bowl") == "Large Bowl"
        assert synthesizer._extract_equipment("Add ingredients") is None

    def test_calculate_nutrition(self):
        """Тест вычисления питательной ценности"""
        synthesizer = RecipeSynthesizer()

        ingredients = [
            {"name": "chicken breast", "amount": 200, "unit": "g"},
            {"name": "tomato", "amount": 100, "unit": "g"},
            {"name": "olive oil", "amount": 20, "unit": "ml"},
        ]

        nutrition = synthesizer._calculate_nutrition(ingredients, 2)

        assert "calories" in nutrition
        assert "protein" in nutrition
        assert "carbs" in nutrition
        assert "fat" in nutrition
        assert all(isinstance(v, (int, float)) for v in nutrition.values())

    def test_generate_tags(self):
        """Тест генерации тегов"""
        synthesizer = RecipeSynthesizer()

        template = RecipeTemplate(
            template_id="test",
            name="Test",
            cuisine_type="asian",
            base_ingredients=["ingredient1"],
            cooking_methods=["method1"],
            typical_prep_time=10,
            typical_cook_time=5,
            difficulty="easy",
            instruction_template="Test",
            nutrition_profile={"calories": 200},
        )

        ingredients = [
            {"name": "chicken", "amount": 200, "unit": "g"},
            {"name": "vegetables", "amount": 100, "unit": "g"},
        ]

        tags = synthesizer._generate_tags(template, ingredients)

        assert "asian" in tags
        assert "easy" in tags
        assert "protein-rich" in tags
        assert "vegetarian" in tags

    def test_generate_recipe_title(self):
        """Тест генерации названия рецепта"""
        synthesizer = RecipeSynthesizer()

        template = RecipeTemplate(
            template_id="stir_fry",
            name="Stir Fry",
            cuisine_type="asian",
            base_ingredients=["ingredient1"],
            cooking_methods=["method1"],
            typical_prep_time=10,
            typical_cook_time=5,
            difficulty="easy",
            instruction_template="Test",
            nutrition_profile={"calories": 200},
        )

        ingredients = [
            {"name": "chicken breast", "amount": 200, "unit": "g"},
            {"name": "vegetables", "amount": 100, "unit": "g"},
        ]

        title = synthesizer._generate_recipe_title(template, ingredients)

        assert "Chicken Breast" in title
        assert "Stir Fry" in title

    def test_generate_recipe_description(self):
        """Тест генерации описания рецепта"""
        synthesizer = RecipeSynthesizer()

        template = RecipeTemplate(
            template_id="test",
            name="Test Recipe",
            cuisine_type="italian",
            base_ingredients=["ingredient1"],
            cooking_methods=["method1"],
            typical_prep_time=10,
            typical_cook_time=5,
            difficulty="medium",
            instruction_template="Test",
            nutrition_profile={"calories": 200},
        )

        ingredients = [
            {"name": "ingredient1", "amount": 100, "unit": "g"},
            {"name": "ingredient2", "amount": 200, "unit": "g"},
        ]

        description = synthesizer._generate_recipe_description(template, ingredients)

        assert "medium" in description
        assert "italian" in description
        assert "2 fresh ingredients" in description

    def test_synthesize_recipe_from_ingredients(self):
        """Тест синтеза рецепта из ингредиентов"""
        synthesizer = RecipeSynthesizer()

        ingredients = [
            {"name": "chicken", "amount": 300, "unit": "g"},
            {"name": "vegetables", "amount": 200, "unit": "g"},
            {"name": "oil", "amount": 20, "unit": "ml"},
        ]

        recipe = synthesizer.synthesize_recipe_from_ingredients(ingredients, "asian", "easy", 4)

        assert isinstance(recipe, Recipe)
        assert recipe.recipe_id.startswith("synth_")
        assert recipe.servings == 4
        assert recipe.difficulty_level == "easy"
        assert len(recipe.ingredients) == 3
        assert len(recipe.steps) > 0
        assert "calories" in recipe.nutrition_per_serving

    def test_synthesize_recipes_for_week(self):
        """Тест синтеза рецептов для недели"""
        synthesizer = RecipeSynthesizer()

        week_plan = {
            "days": [
                {
                    "day": "Monday",
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 200, "unit": "g"},
                                {"name": "rice", "amount": 150, "unit": "g"},
                            ]
                        }
                    ],
                },
                {
                    "day": "Tuesday",
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "salmon", "amount": 250, "unit": "g"},
                                {"name": "vegetables", "amount": 200, "unit": "g"},
                            ]
                        }
                    ],
                },
            ]
        }

        weekly_recipes = synthesizer.synthesize_recipes_for_week(week_plan, 1)

        assert "Monday" in weekly_recipes
        assert "Tuesday" in weekly_recipes
        assert len(weekly_recipes["Monday"]) == 1
        assert len(weekly_recipes["Tuesday"]) == 1
        assert all(isinstance(recipe, Recipe) for recipe in weekly_recipes["Monday"])
        assert all(isinstance(recipe, Recipe) for recipe in weekly_recipes["Tuesday"])


class TestConvenienceFunctions:
    """Тесты для удобных функций"""

    @patch("core.recipe_synth._recipe_synthesizer")
    def test_get_recipe_synthesizer(self, mock_synthesizer):
        """Тест получения глобального синтезатора"""
        mock_synthesizer_instance = RecipeSynthesizer()
        mock_synthesizer.return_value = mock_synthesizer_instance

        synthesizer = get_recipe_synthesizer()

        assert synthesizer is not None

    @patch("core.recipe_synth.get_recipe_synthesizer")
    def test_synthesize_recipe_from_ingredients_function(self, mock_get_synthesizer):
        """Тест функции синтеза рецепта"""
        from unittest.mock import MagicMock

        mock_synthesizer = MagicMock()
        mock_synthesizer.synthesize_recipe_from_ingredients.return_value = Recipe(
            recipe_id="test",
            title="Test Recipe",
            description="Test",
            cuisine_type="test",
            difficulty_level="easy",
            prep_time_minutes=10,
            cook_time_minutes=5,
            total_time_minutes=15,
            servings=4,
            ingredients=[],
            steps=[],
            nutrition_per_serving={},
            tags=[],
        )
        mock_get_synthesizer.return_value = mock_synthesizer

        ingredients = [{"name": "test", "amount": 100, "unit": "g"}]
        recipe = synthesize_recipe_from_ingredients(ingredients)

        assert isinstance(recipe, Recipe)
        assert recipe.recipe_id == "test"

    @patch("core.recipe_synth.get_recipe_synthesizer")
    def test_synthesize_recipes_for_week_function(self, mock_get_synthesizer):
        """Тест функции синтеза рецептов для недели"""
        from unittest.mock import MagicMock

        mock_synthesizer = MagicMock()
        mock_synthesizer.synthesize_recipes_for_week.return_value = {
            "Monday": [
                Recipe(
                    recipe_id="test",
                    title="Test Recipe",
                    description="Test",
                    cuisine_type="test",
                    difficulty_level="easy",
                    prep_time_minutes=10,
                    cook_time_minutes=5,
                    total_time_minutes=15,
                    servings=4,
                    ingredients=[],
                    steps=[],
                    nutrition_per_serving={},
                    tags=[],
                )
            ]
        }
        mock_get_synthesizer.return_value = mock_synthesizer

        week_plan = {"days": [{"day": "Monday", "meals": []}]}
        weekly_recipes = synthesize_recipes_for_week(week_plan)

        assert "Monday" in weekly_recipes
        assert len(weekly_recipes["Monday"]) == 1


class TestIntegration:
    """Интеграционные тесты"""

    def test_full_recipe_synthesis_workflow(self):
        """Тест полного рабочего процесса синтеза рецепта"""
        synthesizer = RecipeSynthesizer()

        ingredients = [
            {"name": "chicken breast", "amount": 400, "unit": "g"},
            {"name": "broccoli", "amount": 300, "unit": "g"},
            {"name": "garlic", "amount": 20, "unit": "g"},
            {"name": "olive oil", "amount": 30, "unit": "ml"},
            {"name": "soy sauce", "amount": 20, "unit": "ml"},
        ]

        # Синтезируем рецепт
        recipe = synthesizer.synthesize_recipe_from_ingredients(ingredients, "asian", "easy", 4)

        # Проверяем результат
        assert isinstance(recipe, Recipe)
        assert recipe.recipe_id.startswith("synth_")
        assert recipe.servings == 4
        assert recipe.difficulty_level == "easy"
        assert len(recipe.ingredients) == 5
        assert len(recipe.steps) > 0
        assert recipe.total_time_minutes == recipe.prep_time_minutes + recipe.cook_time_minutes

        # Проверяем питательную ценность
        nutrition = recipe.nutrition_per_serving
        assert "calories" in nutrition
        assert "protein" in nutrition
        assert "carbs" in nutrition
        assert "fat" in nutrition
        assert all(v >= 0 for v in nutrition.values())  # Может быть 0 для некоторых значений

        # Проверяем теги
        assert len(recipe.tags) > 0
        assert "easy" in recipe.tags
        assert "protein-rich" in recipe.tags

    def test_weekly_recipe_synthesis_workflow(self):
        """Тест полного рабочего процесса синтеза рецептов для недели"""
        synthesizer = RecipeSynthesizer()

        week_plan = {
            "days": [
                {
                    "day": "Monday",
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 200, "unit": "g"},
                                {"name": "rice", "amount": 150, "unit": "g"},
                                {"name": "vegetables", "amount": 100, "unit": "g"},
                            ]
                        }
                    ],
                },
                {
                    "day": "Tuesday",
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "salmon", "amount": 250, "unit": "g"},
                                {"name": "quinoa", "amount": 120, "unit": "g"},
                                {"name": "spinach", "amount": 80, "unit": "g"},
                            ]
                        }
                    ],
                },
                {
                    "day": "Wednesday",
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "tofu", "amount": 200, "unit": "g"},
                                {"name": "noodles", "amount": 100, "unit": "g"},
                                {"name": "bell peppers", "amount": 150, "unit": "g"},
                            ]
                        }
                    ],
                },
            ]
        }

        # Синтезируем рецепты для недели
        weekly_recipes = synthesizer.synthesize_recipes_for_week(week_plan, 1)

        # Проверяем результат
        assert len(weekly_recipes) == 3
        assert "Monday" in weekly_recipes
        assert "Tuesday" in weekly_recipes
        assert "Wednesday" in weekly_recipes

        # Проверяем каждый день
        for day, recipes in weekly_recipes.items():
            assert len(recipes) == 1
            recipe = recipes[0]
            assert isinstance(recipe, Recipe)
            assert recipe.servings == 4
            assert len(recipe.ingredients) > 0
            assert len(recipe.steps) > 0
            assert recipe.total_time_minutes > 0

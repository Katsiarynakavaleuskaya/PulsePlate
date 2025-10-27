# -*- coding: utf-8 -*-
"""
RU: Модуль для синтеза рецептов на основе недельных планов питания.
EN: Module for recipe synthesis based on weekly meal plans.

Sprint 4: Recipe Synth под меню
"""

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class RecipeStep:
    """Шаг рецепта"""

    step_number: int
    instruction: str
    duration_minutes: Optional[int] = None
    temperature: Optional[str] = None
    equipment: Optional[str] = None


@dataclass
class Recipe:
    """Рецепт"""

    recipe_id: str
    title: str
    description: str
    cuisine_type: str
    difficulty_level: str  # easy, medium, hard
    prep_time_minutes: int
    cook_time_minutes: int
    total_time_minutes: int
    servings: int
    ingredients: List[Dict[str, Union[str, float]]]
    steps: List[RecipeStep]
    nutrition_per_serving: Dict[str, float]
    tags: List[str]
    image_url: Optional[str] = None


@dataclass
class RecipeTemplate:
    """Шаблон рецепта"""

    def __init__(
        self,
        template_id: str,
        name: str,
        cuisine_type: str,
        base_ingredients: List[str],
        cooking_methods: List[str],
        typical_prep_time: int,
        typical_cook_time: int,
        difficulty: str,
        instruction_template: str,
        nutrition_profile: Dict[str, float],
    ):
        self.template_id = template_id
        self.name = name
        self.cuisine_type = cuisine_type
        self.base_ingredients = base_ingredients
        self.cooking_methods = cooking_methods
        self.typical_prep_time = typical_prep_time
        self.typical_cook_time = typical_cook_time
        self.difficulty = difficulty
        self.instruction_template = instruction_template
        self.nutrition_profile = nutrition_profile


class RecipeSynthesizer:
    """Синтезатор рецептов"""

    def __init__(self, templates_dir: str = "data/recipe_templates"):
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, RecipeTemplate] = {}
        self._load_templates()

    def _load_templates(self):
        """Загружает шаблоны рецептов"""
        if not self.templates_dir.exists():
            self._create_default_templates()
            return

        template_files = list(self.templates_dir.glob("*.json"))
        if not template_files:
            # If directory exists but has no templates, create defaults
            self._create_default_templates()
            return

        for template_file in template_files:
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template_data = json.load(f)
                    template = RecipeTemplate(**template_data)
                    self.templates[template.template_id] = template
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")

    def _create_default_templates(self):
        """Создает шаблоны рецептов по умолчанию"""
        default_templates: List[Dict[str, Any]] = [
            {
                "template_id": "stir_fry",
                "name": "Stir Fry",
                "cuisine_type": "asian",
                "base_ingredients": [
                    "vegetables",
                    "protein",
                    "oil",
                    "garlic",
                    "ginger",
                ],
                "cooking_methods": ["stir_frying", "sautéing"],
                "typical_prep_time": 15,
                "typical_cook_time": 10,
                "difficulty": "easy",
                "instruction_template": (
                    "Heat oil in a wok or large pan. Add garlic and ginger, stir for 30 seconds. "
                    "Add protein and cook until done. Add vegetables and stir-fry for 3-5 minutes. "
                    "Season with soy sauce and serve."
                ),
                "nutrition_profile": {
                    "calories": 300,
                    "protein": 25,
                    "carbs": 15,
                    "fat": 15,
                },
            },
            {
                "template_id": "pasta",
                "name": "Pasta Dish",
                "cuisine_type": "italian",
                "base_ingredients": ["pasta", "sauce", "cheese", "herbs"],
                "cooking_methods": ["boiling", "simmering"],
                "typical_prep_time": 10,
                "typical_cook_time": 20,
                "difficulty": "easy",
                "instruction_template": (
                    "Boil pasta according to package instructions. Meanwhile, prepare sauce. "
                    "Drain pasta and combine with sauce. Add cheese and herbs. Serve immediately."
                ),
                "nutrition_profile": {
                    "calories": 400,
                    "protein": 15,
                    "carbs": 60,
                    "fat": 12,
                },
            },
            {
                "template_id": "salad",
                "name": "Fresh Salad",
                "cuisine_type": "mediterranean",
                "base_ingredients": ["greens", "vegetables", "dressing", "nuts"],
                "cooking_methods": ["chopping", "mixing"],
                "typical_prep_time": 20,
                "typical_cook_time": 0,
                "difficulty": "easy",
                "instruction_template": (
                    "Wash and chop all vegetables. Combine greens and vegetables in a large bowl. "
                    "Add dressing and toss gently. Top with nuts and serve."
                ),
                "nutrition_profile": {
                    "calories": 200,
                    "protein": 8,
                    "carbs": 20,
                    "fat": 12,
                },
            },
            {
                "template_id": "soup",
                "name": "Hearty Soup",
                "cuisine_type": "international",
                "base_ingredients": ["broth", "vegetables", "protein", "herbs"],
                "cooking_methods": ["simmering", "boiling"],
                "typical_prep_time": 15,
                "typical_cook_time": 30,
                "difficulty": "medium",
                "instruction_template": (
                    "Heat broth in a large pot. Add vegetables and protein. "
                    "Simmer for 20-30 minutes until vegetables are tender. "
                    "Season with herbs and spices. Serve hot."
                ),
                "nutrition_profile": {
                    "calories": 250,
                    "protein": 20,
                    "carbs": 25,
                    "fat": 8,
                },
            },
            {
                "template_id": "grilled_protein",
                "name": "Grilled Protein",
                "cuisine_type": "american",
                "base_ingredients": ["protein", "marinade", "vegetables"],
                "cooking_methods": ["grilling", "marinating"],
                "typical_prep_time": 30,
                "typical_cook_time": 15,
                "difficulty": "medium",
                "instruction_template": (
                    "Marinate protein for at least 30 minutes. Preheat grill. "
                    "Grill protein for 6-8 minutes per side. Grill vegetables alongside. "
                    "Rest protein before serving."
                ),
                "nutrition_profile": {
                    "calories": 350,
                    "protein": 35,
                    "carbs": 10,
                    "fat": 18,
                },
            },
        ]

        for template_data in default_templates:
            template = RecipeTemplate(
                template_id=template_data["template_id"],
                name=template_data["name"],
                cuisine_type=template_data["cuisine_type"],
                base_ingredients=template_data["base_ingredients"],
                cooking_methods=template_data["cooking_methods"],
                typical_prep_time=template_data["typical_prep_time"],
                typical_cook_time=template_data["typical_cook_time"],
                difficulty=template_data["difficulty"],
                instruction_template=template_data["instruction_template"],
                nutrition_profile=template_data["nutrition_profile"],
            )
            self.templates[template.template_id] = template

    def synthesize_recipe_from_ingredients(
        self,
        ingredients: List[Dict[str, Union[str, float]]],
        cuisine_preference: str = "international",
        difficulty_preference: str = "easy",
        servings: int = 4,
    ) -> Recipe:
        """
        Синтезирует рецепт на основе списка ингредиентов

        Args:
            ingredients: Список ингредиентов с количеством
            cuisine_preference: Предпочтение кухни
            difficulty_preference: Предпочтение сложности
            servings: Количество порций

        Returns:
            Синтезированный рецепт
        """
        # Выбираем подходящий шаблон
        template = self._select_best_template(
            ingredients, cuisine_preference, difficulty_preference
        )

        # Создаем рецепт на основе шаблона
        recipe = self._create_recipe_from_template(template, ingredients, servings)

        return recipe

    def _select_best_template(
        self,
        ingredients: List[Dict[str, Union[str, float]]],
        cuisine_preference: str,
        difficulty_preference: str,
    ) -> RecipeTemplate:
        """Выбирает лучший шаблон для ингредиентов"""
        ingredient_names = [str(ing.get("name", "")).lower() for ing in ingredients]

        # Фильтруем шаблоны по предпочтениям
        suitable_templates = []
        for template in self.templates.values():
            if template.cuisine_type == cuisine_preference or cuisine_preference == "international":
                if template.difficulty == difficulty_preference:
                    suitable_templates.append(template)

        if not suitable_templates:
            # Если нет подходящих, берем любой
            suitable_templates = list(self.templates.values())

        # Выбираем шаблон с наибольшим совпадением ингредиентов
        best_template = None
        best_score = 0

        for template in suitable_templates:
            score = self._calculate_ingredient_match_score(
                ingredient_names, template.base_ingredients
            )
            if score > best_score:
                best_score = score
                best_template = template

        return best_template or list(self.templates.values())[0]

    def _calculate_ingredient_match_score(
        self, ingredient_names: List[str], template_ingredients: List[str]
    ) -> int:
        """Вычисляет оценку совпадения ингредиентов"""
        score = 0
        for template_ing in template_ingredients:
            for ing_name in ingredient_names:
                if template_ing.lower() in ing_name or ing_name in template_ing.lower():
                    score += 1
                    break
        return score

    def _create_recipe_from_template(
        self,
        template: RecipeTemplate,
        ingredients: List[Dict[str, Union[str, float]]],
        servings: int,
    ) -> Recipe:
        """Создает рецепт на основе шаблона"""
        recipe_id = f"synth_{template.template_id}_{random.randint(1000, 9999)}"  # nosec B311

        # Адаптируем ингредиенты под количество порций
        adapted_ingredients = self._adapt_ingredients_for_servings(ingredients, servings)

        # Создаем шаги рецепта
        steps = self._generate_recipe_steps(template, adapted_ingredients)

        # Вычисляем питательную ценность
        nutrition = self._calculate_nutrition(adapted_ingredients, servings)

        # Создаем теги
        tags = self._generate_tags(template, adapted_ingredients)

        recipe = Recipe(
            recipe_id=recipe_id,
            title=self._generate_recipe_title(template, adapted_ingredients),
            description=self._generate_recipe_description(template, adapted_ingredients),
            cuisine_type=template.cuisine_type,
            difficulty_level=template.difficulty,
            prep_time_minutes=template.typical_prep_time,
            cook_time_minutes=template.typical_cook_time,
            total_time_minutes=template.typical_prep_time + template.typical_cook_time,
            servings=servings,
            ingredients=adapted_ingredients,
            steps=steps,
            nutrition_per_serving=nutrition,
            tags=tags,
        )

        return recipe

    def _adapt_ingredients_for_servings(
        self, ingredients: List[Dict[str, Union[str, float]]], target_servings: int
    ) -> List[Dict[str, Union[str, float]]]:
        """Адаптирует ингредиенты под количество порций"""
        adapted = []
        for ing in ingredients:
            adapted_ing = ing.copy()
            # Простая логика: если количество больше 100g, считаем что это на 4 порции
            amount = ing.get("amount", 0)
            if isinstance(amount, (int, float)) and amount > 100:
                adapted_ing["amount"] = round(amount * target_servings / 4, 1)
            adapted.append(adapted_ing)
        return adapted

    def _generate_recipe_steps(
        self, template: RecipeTemplate, ingredients: List[Dict[str, Union[str, float]]]
    ) -> List[RecipeStep]:
        """Генерирует шаги рецепта"""
        steps = []

        # Разбиваем инструкцию на шаги
        instruction_parts = template.instruction_template.split(". ")

        for i, part in enumerate(instruction_parts, 1):
            if part.strip():
                # Добавляем точку в конец если её нет
                if not part.endswith("."):
                    part += "."

                step = RecipeStep(
                    step_number=i,
                    instruction=part.strip(),
                    duration_minutes=self._estimate_step_duration(part, template),
                    temperature=self._extract_temperature(part),
                    equipment=self._extract_equipment(part),
                )
                steps.append(step)

        return steps

    def _estimate_step_duration(self, instruction: str, template: RecipeTemplate) -> int:
        """Оценивает продолжительность шага"""
        instruction_lower = instruction.lower()

        if any(word in instruction_lower for word in ["marinate", "rest"]):
            return 30
        elif any(word in instruction_lower for word in ["simmer", "boil"]):
            return 20
        elif any(word in instruction_lower for word in ["grill", "cook"]):
            return 10
        elif any(word in instruction_lower for word in ["chop", "cut", "slice"]):
            return 5
        else:
            return 2

    def _extract_temperature(self, instruction: str) -> Optional[str]:
        """Извлекает информацию о температуре"""
        instruction_lower = instruction.lower()

        if "high heat" in instruction_lower:
            return "High"
        elif "medium heat" in instruction_lower:
            return "Medium"
        elif "low heat" in instruction_lower:
            return "Low"
        elif "preheat" in instruction_lower:
            return "Preheated"

        return None

    def _extract_equipment(self, instruction: str) -> Optional[str]:
        """Извлекает информацию об оборудовании"""
        instruction_lower = instruction.lower()

        if "wok" in instruction_lower or "pan" in instruction_lower:
            return "Wok or Large Pan"
        elif "pot" in instruction_lower:
            return "Large Pot"
        elif "grill" in instruction_lower:
            return "Grill"
        elif "bowl" in instruction_lower:
            return "Large Bowl"

        return None

    def _calculate_nutrition(
        self, ingredients: List[Dict[str, Union[str, float]]], servings: int
    ) -> Dict[str, float]:
        """Вычисляет питательную ценность на порцию"""
        # Упрощенная логика расчета питательной ценности
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0

        for ing in ingredients:
            amount = ing.get("amount", 0)
            if isinstance(amount, (int, float)):
                # Примерные значения на 100g
                if (
                    "meat" in str(ing.get("name", "")).lower()
                    or "chicken" in str(ing.get("name", "")).lower()
                ):
                    total_calories += amount * 2.5  # 250 cal per 100g
                    total_protein += amount * 0.25  # 25g protein per 100g
                elif (
                    "vegetable" in str(ing.get("name", "")).lower()
                    or "tomato" in str(ing.get("name", "")).lower()
                ):
                    total_calories += amount * 0.2  # 20 cal per 100g
                    total_carbs += amount * 0.04  # 4g carbs per 100g
                elif (
                    "pasta" in str(ing.get("name", "")).lower()
                    or "rice" in str(ing.get("name", "")).lower()
                ):
                    total_calories += amount * 3.5  # 350 cal per 100g
                    total_carbs += amount * 0.75  # 75g carbs per 100g
                elif "oil" in str(ing.get("name", "")).lower():
                    total_calories += amount * 9  # 900 cal per 100g
                    total_fat += amount * 1  # 100g fat per 100g

        return {
            "calories": round(total_calories / servings, 1),
            "protein": round(total_protein / servings, 1),
            "carbs": round(total_carbs / servings, 1),
            "fat": round(total_fat / servings, 1),
        }

    def _generate_tags(
        self, template: RecipeTemplate, ingredients: List[Dict[str, Union[str, float]]]
    ) -> List[str]:
        """Генерирует теги для рецепта"""
        tags = [template.cuisine_type, template.difficulty]

        # Добавляем теги на основе ингредиентов
        ingredient_names = [str(ing.get("name", "")).lower() for ing in ingredients]

        if any("vegetable" in name for name in ingredient_names):
            tags.append("vegetarian")
        if any("meat" in name or "chicken" in name for name in ingredient_names):
            tags.append("protein-rich")
        if any("spice" in name or "herb" in name for name in ingredient_names):
            tags.append("spicy")

        return list(set(tags))  # Убираем дубликаты

    def _generate_recipe_title(
        self, template: RecipeTemplate, ingredients: List[Dict[str, Union[str, float]]]
    ) -> str:
        """Генерирует название рецепта"""
        # Берем основной ингредиент
        main_ingredient = None
        for ing in ingredients:
            name = str(ing.get("name", "")).lower()
            if any(word in name for word in ["chicken", "beef", "salmon", "tofu"]):
                main_ingredient = str(ing.get("name", "")).title()
                break

        if main_ingredient:
            return f"{main_ingredient} {template.name}"
        else:
            return f"Delicious {template.name}"

    def _generate_recipe_description(
        self, template: RecipeTemplate, ingredients: List[Dict[str, Union[str, float]]]
    ) -> str:
        """Генерирует описание рецепта"""
        ingredient_count = len(ingredients)
        return (
            f"A {template.difficulty} {template.cuisine_type} recipe with "
            f"{ingredient_count} fresh ingredients. Perfect for a healthy and delicious meal."
        )

    def synthesize_recipes_for_week(
        self, week_plan: Dict, recipes_per_day: int = 1
    ) -> Dict[str, List[Recipe]]:
        """
        Синтезирует рецепты для недельного плана

        Args:
            week_plan: Недельный план питания
            recipes_per_day: Количество рецептов в день

        Returns:
            Словарь {day: [recipes]}
        """
        weekly_recipes = {}

        if "days" in week_plan:
            for day in week_plan["days"]:
                day_name = day.get("day", "Monday")
                meals = day.get("meals", [])

                day_recipes = []
                for meal in meals[:recipes_per_day]:  # Ограничиваем количество рецептов
                    if "ingredients" in meal:
                        recipe = self.synthesize_recipe_from_ingredients(
                            meal["ingredients"],
                            cuisine_preference="international",
                            difficulty_preference="easy",
                            servings=4,
                        )
                        day_recipes.append(recipe)

                weekly_recipes[day_name] = day_recipes

        return weekly_recipes


# Глобальный экземпляр синтезатора
_recipe_synthesizer = None


def get_recipe_synthesizer() -> RecipeSynthesizer:
    """Получает глобальный экземпляр синтезатора рецептов"""
    global _recipe_synthesizer
    if _recipe_synthesizer is None:
        _recipe_synthesizer = RecipeSynthesizer()
    return _recipe_synthesizer


# Удобные функции для быстрого доступа
def synthesize_recipe_from_ingredients(
    ingredients: List[Dict[str, Union[str, float]]],
    cuisine_preference: str = "international",
    difficulty_preference: str = "easy",
    servings: int = 4,
) -> Recipe:
    """Синтезирует рецепт на основе ингредиентов"""
    synthesizer = get_recipe_synthesizer()
    return synthesizer.synthesize_recipe_from_ingredients(
        ingredients, cuisine_preference, difficulty_preference, servings
    )


def synthesize_recipes_for_week(
    week_plan: Dict, recipes_per_day: int = 1
) -> Dict[str, List[Recipe]]:
    """Синтезирует рецепты для недельного плана"""
    synthesizer = get_recipe_synthesizer()
    return synthesizer.synthesize_recipes_for_week(week_plan, recipes_per_day)

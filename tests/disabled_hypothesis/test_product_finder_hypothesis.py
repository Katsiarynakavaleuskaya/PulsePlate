# -*- coding: utf-8 -*-
# flake8: noqa: W503,W504
"""
RU: Hypothesis тесты для системы автоматического поиска продуктов.
EN: Hypothesis tests for automatic product search system.
"""

import asyncio
import json
import logging

from hypothesis import given, settings
from hypothesis import strategies as st

from core.food_apis.unified_db import UnifiedFoodItem, get_unified_food_db
from core.food_db import FoodItem
from core.product_finder import ProductFinder, ProductSearchResult
from core.recipe_db import parse_recipe_db


def unified_to_food_item(unified_item: UnifiedFoodItem) -> FoodItem:
    """
    RU: Конвертирует UnifiedFoodItem в FoodItem.
    EN: Converts UnifiedFoodItem to FoodItem.

    Maps nutrients from unified format to FoodItem format with proper
    field mappings and default values.

    Args:
        unified_item: The UnifiedFoodItem to convert

    Returns:
        FoodItem with mapped nutrients and properties
    """
    nutrients = unified_item.nutrients_per_100g
    return FoodItem(
        name=unified_item.name,
        unit_per=100,
        unit="g",
        protein_g=nutrients.get("protein_g", 0.0),
        fat_g=nutrients.get("fat_g", 0.0),
        carbs_g=nutrients.get("carbs_g", 0.0),
        fiber_g=nutrients.get("fiber_g", 0.0),
        Fe_mg=nutrients.get("iron_mg", 0.0),
        Ca_mg=nutrients.get("calcium_mg", 0.0),
        VitD_IU=nutrients.get("vitamin_d_iu", 0.0),
        B12_ug=nutrients.get("b12_ug", 0.0),
        Folate_ug=nutrients.get("folate_ug", 0.0),
        Iodine_ug=nutrients.get("iodine_ug", 0.0),
        K_mg=nutrients.get("potassium_mg", 0.0),
        Mg_mg=nutrients.get("magnesium_mg", 0.0),
        price_per_unit=unified_item.cost_per_100g,
        flags=set(unified_item.tags),
    )


class TestProductFinderHypothesis:
    """Test automatic product finder with Hypothesis."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.finder = ProductFinder()

        async def _build_food_db() -> dict[str, FoodItem]:
            unified_db = await get_unified_food_db()
            common_foods = await unified_db.get_common_foods_database()
            food_db_local: dict[str, FoodItem] = {}
            for key, unified_item in common_foods.items():
                food_db_local[key] = unified_to_food_item(unified_item)
            return food_db_local

        try:
            food_db = asyncio.run(_build_food_db())
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            logging.exception("Failed to build food DB for tests: %s", exc)
            raise

        self.recipes = parse_recipe_db("data/recipes_extended.csv", food_db=food_db)

    def test_find_missing_products_hypothesis(self) -> None:
        """Test finding missing products from recipe ingredients."""
        # Получаем все ингредиенты из рецептов
        all_ingredients = []
        for recipe in self.recipes.values():
            all_ingredients.extend(recipe.ingredients.keys())

        # Находим недостающие продукты
        missing_products = self.finder.find_missing_products(all_ingredients)

        # Должны найти недостающие продукты
        assert len(missing_products) > 0

        # Проверяем, что найденные продукты действительно отсутствуют
        for product in missing_products:
            assert isinstance(product, str)
            assert len(product) > 0

    @given(
        product_name=st.text(
            min_size=2,
            max_size=20,
            alphabet=st.characters(
                min_codepoint=ord("а"),
                max_codepoint=ord("я"),
                whitelist_categories=("Lu", "Ll"),
            ),
        )
    )
    @settings(deadline=None)
    def test_similar_names_hypothesis(self, product_name: str) -> None:
        """Test similar name detection with Hypothesis."""
        if not product_name:
            return

        # Тестируем с различными вариантами названия
        variations = [
            product_name.lower(),
            product_name.upper(),
            product_name.replace(" ", "_"),
            product_name.replace("_", " "),
        ]

        for variation in variations:
            if variation:
                # Проверяем, что функция не падает
                result = self.finder._similar_names(product_name, variation)
                assert isinstance(result, bool)

    @given(
        search_name=st.sampled_from(
            [
                "Бананы",
                "Молоко",
                "Яйца",
                "Сыр",
                "Картофель",
                "Морковь",
                "Лук",
                "Брокколи",
                "Салат",
                "Творог",
            ]
        )
    )
    @settings(deadline=None)
    def test_search_product_hypothesis(self, search_name: str) -> None:
        """Test product search with Hypothesis."""
        result = self.finder.search_product(search_name)

        # Проверяем структуру результата
        assert isinstance(result, ProductSearchResult)
        assert result.product_name == search_name
        assert isinstance(result.found, bool)

        if result.found:
            assert result.source is not None
            assert result.food_record is not None
            assert result.confidence > 0.0
        else:
            assert result.error_message is not None

    @given(
        confidence1=st.floats(min_value=0.0, max_value=1.0),
        confidence2=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(deadline=None)
    def test_confidence_calculation_hypothesis(
        self, confidence1: float, confidence2: float
    ) -> None:
        """Test confidence calculation with Hypothesis."""
        # Тестируем с различными названиями
        test_cases = [
            ("Молоко", "milk"),
            ("Яйца", "eggs"),
            ("Сыр", "cheese"),
            ("Бананы", "banana"),
            ("Картофель", "potato"),
        ]

        for name1, name2 in test_cases:
            confidence = self.finder._calculate_confidence(name1, name2)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0

    def test_auto_expand_database_integration(self) -> None:
        """Test automatic database expansion integration."""
        # Получаем все ингредиенты из рецептов
        all_ingredients = []
        for recipe in self.recipes.values():
            all_ingredients.extend(recipe.ingredients.keys())

        # Запускаем автоматическое расширение
        results = self.finder.auto_expand_database(all_ingredients)

        # Проверяем результаты
        assert isinstance(results, dict)
        assert len(results) > 0

        # Проверяем, что все результаты - булевы значения
        for product, success in results.items():
            assert isinstance(product, str)
            assert isinstance(success, bool)

    def test_product_finder_initialization(self) -> None:
        """Test product finder initialization."""
        finder = ProductFinder()

        # Проверяем, что все компоненты инициализированы
        assert finder.usda_adapter is not None
        assert finder.off_adapter is not None
        assert finder.food_db is not None
        assert len(finder.food_db) > 0

    def test_missing_products_detection(self) -> None:
        """Test missing products detection accuracy."""
        # Тестируем с известными недостающими продуктами
        test_ingredients = [
            "Бананы",
            "Молоко",
            "Яйца",
            "Сыр",
            "Картофель",
            "Морковь",
            "Лук",
            "Брокколи",
            "Салат",
            "Творог",
        ]

        missing_products = self.finder.find_missing_products(test_ingredients)

        # Должны найти большинство из тестовых ингредиентов
        assert len(missing_products) > 0

        # Проверяем, что найденные продукты действительно отсутствуют
        for product in missing_products:
            assert product in test_ingredients

    def test_search_result_structure(self) -> None:
        """Test search result data structure."""
        # Тестируем с реальным продуктом
        result = self.finder.search_product("Молоко")

        # Проверяем все поля
        assert hasattr(result, "product_name")
        assert hasattr(result, "found")
        assert hasattr(result, "source")
        assert hasattr(result, "food_record")
        assert hasattr(result, "confidence")
        assert hasattr(result, "error_message")

        # Проверяем типы данных
        assert isinstance(result.product_name, str)
        assert isinstance(result.found, bool)

        if result.source is not None:
            assert isinstance(result.source, str)
            assert result.source in ["USDA", "OFF"]

        if result.food_record is not None:
            assert hasattr(result.food_record, "name")
            assert hasattr(result.food_record, "protein_g")
            assert hasattr(result.food_record, "fat_g")
            assert hasattr(result.food_record, "carbs_g")

        if result.confidence is not None:
            assert isinstance(result.confidence, float)
            assert 0.0 <= result.confidence <= 1.0

        if result.error_message is not None:
            assert isinstance(result.error_message, str)

    def test_database_expansion_workflow(self) -> None:
        """Test complete database expansion workflow."""
        # Получаем небольшой набор ингредиентов для тестирования
        test_ingredients = ["Молоко", "Яйца", "Сыр"]

        # Запускаем поиск недостающих продуктов
        missing_products = self.finder.find_missing_products(test_ingredients)

        # Проверяем, что система работает
        assert isinstance(missing_products, list)

        # Тестируем поиск для каждого недостающего продукта
        for product in missing_products[:2]:  # Ограничиваем для тестирования
            result = self.finder.search_product(product)
            assert isinstance(result, ProductSearchResult)
            assert result.product_name == product

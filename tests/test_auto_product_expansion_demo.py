# -*- coding: utf-8 -*-
"""
RU: Демонстрационный тест автоматического расширения базы продуктов.
EN: Demo test for automatic product database expansion.

Этот тест демонстрирует, как система автоматически находит и добавляет
недостающие продукты в базу данных.
"""

import shutil
from pathlib import Path

from core.product_finder import ProductFinder
from core.recipe_db import parse_recipe_db


class TestAutoProductExpansionDemo:
    """Demo test for automatic product expansion."""

    def test_auto_expansion_demo(self):
        """Demo test showing automatic product expansion workflow."""
        # Создаем временную копию базы данных для тестирования
        original_db_path = Path("data/food_db.csv")
        temp_db_path = Path("data/food_db_temp.csv")

        # Копируем оригинальную базу
        shutil.copy2(original_db_path, temp_db_path)

        try:
            # Создаем поисковик продуктов
            finder = ProductFinder()

            # Загружаем рецепты
            recipes = parse_recipe_db("data/recipes_extended.csv")

            # Получаем все ингредиенты
            all_ingredients = []
            for recipe in recipes.values():
                all_ingredients.extend(recipe.ingredients.keys())

            # Убираем дубликаты
            unique_ingredients = list(set(all_ingredients))

            print(f"📚 Всего уникальных ингредиентов: {len(unique_ingredients)}")

            # Находим недостающие продукты
            missing_products = finder.find_missing_products(unique_ingredients)

            print(f"❌ Недостающих продуктов: {len(missing_products)}")
            print("Недостающие продукты:")
            for i, product in enumerate(missing_products, 1):
                print(f"  {i}. {product}")

            # Демонстрируем поиск для нескольких продуктов
            demo_products = missing_products[:5]  # Берем первые 5

            print(f"\n🔍 Демонстрация поиска для {len(demo_products)} продуктов:")

            for product in demo_products:
                print(f"\nПоиск: {product}")
                result = finder.search_product(product)

                print(f"  Найден: {result.found}")
                if result.found:
                    print(f"  Источник: {result.source}")
                    print(f"  Уверенность: {result.confidence:.2f}")
                    if result.food_record:
                        print(f"  Название: {result.food_record.name}")
                        print(f"  Белок: {result.food_record.protein_g}g")
                        print(f"  Жиры: {result.food_record.fat_g}g")
                        print(f"  Углеводы: {result.food_record.carbs_g}g")
                else:
                    print(f"  Ошибка: {result.error_message}")

            # Показываем текущее состояние базы данных
            print(f"\n📊 Текущая база данных содержит {len(finder.food_db)} продуктов")

            # Демонстрируем, как бы работало автоматическое расширение
            print("\n🚀 Демонстрация автоматического расширения:")
            print("(В реальной системе это добавило бы найденные продукты в базу)")

            successful_searches = 0
            for product in demo_products:
                result = finder.search_product(product)
                if result.found:
                    successful_searches += 1
                    print(f"  ✅ {product} - найден в {result.source}")
                else:
                    print(f"  ❌ {product} - не найден")

            print(
                f"\n📈 Результат: {successful_searches}/{len(demo_products)} продуктов найдено"
            )

            # Проверяем, что система работает корректно
            assert len(unique_ingredients) > 0
            assert len(missing_products) > 0
            assert len(finder.food_db) > 0

            print("\n✅ Демонстрация завершена успешно!")

        finally:
            # Восстанавливаем оригинальную базу данных
            if temp_db_path.exists():
                temp_db_path.unlink()

    def test_missing_products_detection_accuracy(self):
        """Test accuracy of missing products detection."""
        finder = ProductFinder()
        recipes = parse_recipe_db("data/recipes_extended.csv")

        # Получаем все ингредиенты
        all_ingredients = []
        for recipe in recipes.values():
            all_ingredients.extend(recipe.ingredients.keys())

        unique_ingredients = list(set(all_ingredients))

        # Находим недостающие продукты
        missing_products = finder.find_missing_products(unique_ingredients)

        # Проверяем, что система корректно определяет недостающие продукты
        assert len(missing_products) > 0

        # Проверяем, что найденные продукты действительно отсутствуют в базе
        food_names = {food.name.lower() for food in finder.food_db.values()}

        for missing_product in missing_products:
            found_in_db = False
            for food_name in food_names:
                if (
                    missing_product.lower() in food_name
                    or food_name in missing_product.lower()
                    or finder._similar_names(missing_product, food_name)
                ):
                    found_in_db = True
                    break

            # Продукт должен быть действительно отсутствующим
            assert (
                not found_in_db
            ), f"Product {missing_product} should be missing but found in database"

    def test_product_search_workflow(self):
        """Test complete product search workflow."""
        finder = ProductFinder()

        # Тестируем поиск с различными названиями
        test_products = ["Молоко", "Яйца", "Сыр", "Бананы", "Картофель"]

        for product in test_products:
            result = finder.search_product(product)

            # Проверяем структуру результата
            assert hasattr(result, "product_name")
            assert hasattr(result, "found")
            assert hasattr(result, "source")
            assert hasattr(result, "food_record")
            assert hasattr(result, "confidence")
            assert hasattr(result, "error_message")

            assert result.product_name == product
            assert isinstance(result.found, bool)

            if result.found:
                assert result.source is not None
                assert result.food_record is not None
                assert result.confidence > 0.0
            else:
                assert result.error_message is not None

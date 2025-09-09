#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RU: Скрипт для автоматического расширения базы данных продуктов.
EN: Script for automatic expansion of product database.

Этот скрипт анализирует рецепты, находит недостающие продукты
и автоматически добавляет их в базу данных из бесплатных источников.
"""

import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.product_finder import ProductFinder
from core.recipe_db import parse_recipe_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function for automatic database expansion."""
    logger.info("🚀 Starting automatic database expansion")

    try:
        # Инициализируем поисковик продуктов
        finder = ProductFinder()
        logger.info("✅ Product finder initialized")

        # Загружаем рецепты
        recipes = parse_recipe_db("data/recipes_extended.csv")
        logger.info(f"📚 Loaded {len(recipes)} recipes")

        # Получаем все ингредиенты из рецептов
        all_ingredients = []
        for recipe in recipes.values():
            all_ingredients.extend(recipe.ingredients.keys())

        logger.info(f"🥘 Found {len(all_ingredients)} unique ingredients")

        # Находим недостающие продукты
        missing_products = finder.find_missing_products(all_ingredients)
        logger.info(f"❌ Found {len(missing_products)} missing products")

        if not missing_products:
            logger.info("🎉 All products are already in the database!")
            return

        # Показываем недостающие продукты
        logger.info("📋 Missing products:")
        for i, product in enumerate(missing_products, 1):
            logger.info(f"  {i}. {product}")

        # Запускаем автоматическое расширение
        logger.info("🔍 Starting product search and addition...")
        results = finder.auto_expand_database(all_ingredients)

        # Показываем результаты
        logger.info("📊 Expansion results:")
        successful = 0
        failed = 0

        for product, success in results.items():
            if success:
                logger.info(f"  ✅ {product} - Added successfully")
                successful += 1
            else:
                logger.info(f"  ❌ {product} - Failed to add")
                failed += 1

        logger.info(f"📈 Summary: {successful} successful, {failed} failed")

        # Показываем статистику базы данных
        updated_food_db = finder.food_db
        logger.info(f"📊 Database now contains {len(updated_food_db)} products")

        logger.info("🎉 Automatic database expansion completed!")

    except Exception as e:
        logger.error(f"💥 Error during database expansion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

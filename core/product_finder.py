# -*- coding: utf-8 -*-
"""
RU: Система автоматического поиска и добавления недостающих продуктов.
EN: Automatic product search and addition system.

Этот модуль предоставляет функциональность для поиска недостающих продуктов
в бесплатных источниках данных и автоматического добавления их в базу данных.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .food_db import FoodItem, parse_food_db
from .food_sources.base import FoodRecord
from .food_sources.off import OFFAdapter
from .food_sources.usda import USDAAdapter

logger = logging.getLogger(__name__)


@dataclass
class ProductSearchResult:
    """
    RU: Результат поиска продукта.
    EN: Product search result.
    """

    product_name: str
    found: bool
    source: Optional[str] = None
    food_record: Optional[FoodRecord] = None
    confidence: float = 0.0
    error_message: Optional[str] = None


class ProductFinder:
    """
    RU: Класс для поиска недостающих продуктов в различных источниках.
    EN: Class for finding missing products in various sources.
    """

    def __init__(self):
        """Initialize the product finder."""
        self.usda_adapter = USDAAdapter()
        self.off_adapter = OFFAdapter()
        self.food_db = parse_food_db("data/food_db.csv")

    def find_missing_products(self, recipe_ingredients: List[str]) -> List[str]:
        """
        RU: Найти продукты, которые отсутствуют в базе данных.
        EN: Find products that are missing from the database.

        Args:
            recipe_ingredients: Список ингредиентов из рецептов

        Returns:
            Список недостающих продуктов
        """
        missing_products = []
        food_names = {food.name.lower() for food in self.food_db.values()}

        for ingredient in recipe_ingredients:
            found = False
            for food_name in food_names:
                if (
                    ingredient.lower() in food_name
                    or food_name in ingredient.lower()
                    or self._similar_names(ingredient, food_name)
                ):
                    found = True
                    break

            if not found:
                missing_products.append(ingredient)

        return missing_products

    def _similar_names(self, name1: str, name2: str) -> bool:
        """
        RU: Проверить, похожи ли названия продуктов.
        EN: Check if product names are similar.

        Args:
            name1: Первое название
            name2: Второе название

        Returns:
            True, если названия похожи
        """
        # Простая проверка на схожесть названий
        name1_clean = name1.lower().replace(" ", "").replace("_", "")
        name2_clean = name2.lower().replace(" ", "").replace("_", "")

        # Проверяем, содержит ли одно название другое
        if name1_clean in name2_clean or name2_clean in name1_clean:
            return True

        # Проверяем общие слова
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        common_words = words1.intersection(words2)

        return len(common_words) > 0

    def search_product(self, product_name: str) -> ProductSearchResult:
        """
        RU: Поиск продукта в различных источниках.
        EN: Search for a product in various sources.

        Args:
            product_name: Название продукта для поиска

        Returns:
            Результат поиска
        """
        logger.info(f"Searching for product: {product_name}")

        # Сначала пробуем USDA
        try:
            usda_result = self._search_in_usda(product_name)
            if usda_result.found:
                return usda_result
        except Exception as e:
            logger.warning(f"USDA search failed for {product_name}: {e}")

        # Затем пробуем Open Food Facts
        try:
            off_result = self._search_in_off(product_name)
            if off_result.found:
                return off_result
        except Exception as e:
            logger.warning(f"OFF search failed for {product_name}: {e}")

        # Если ничего не найдено, возвращаем отрицательный результат
        return ProductSearchResult(
            product_name=product_name,
            found=False,
            error_message="Product not found in any source",
        )

    def _search_in_usda(self, product_name: str) -> ProductSearchResult:
        """
        RU: Поиск продукта в USDA базе данных.
        EN: Search for product in USDA database.

        Args:
            product_name: Название продукта

        Returns:
            Результат поиска
        """
        try:
            # Получаем все продукты из USDA
            usda_foods = self.usda_adapter.normalize()

            # Ищем наиболее подходящий продукт
            best_match = None
            best_confidence = 0.0

            for food in usda_foods:
                confidence = self._calculate_confidence(product_name, food.name)
                if confidence > best_confidence and confidence > 0.3:
                    best_match = food
                    best_confidence = confidence

            if best_match:
                return ProductSearchResult(
                    product_name=product_name,
                    found=True,
                    source="USDA",
                    food_record=best_match,
                    confidence=best_confidence,
                )

        except Exception as e:
            logger.error(f"Error searching in USDA: {e}")

        return ProductSearchResult(
            product_name=product_name, found=False, error_message="USDA search failed"
        )

    def _search_in_off(self, product_name: str) -> ProductSearchResult:
        """
        RU: Поиск продукта в Open Food Facts.
        EN: Search for product in Open Food Facts.

        Args:
            product_name: Название продукта

        Returns:
            Результат поиска
        """
        try:
            # Получаем все продукты из OFF
            off_foods = self.off_adapter.normalize()

            # Ищем наиболее подходящий продукт
            best_match = None
            best_confidence = 0.0

            for food in off_foods:
                confidence = self._calculate_confidence(product_name, food.name)
                if confidence > best_confidence and confidence > 0.3:
                    best_match = food
                    best_confidence = confidence

            if best_match:
                return ProductSearchResult(
                    product_name=product_name,
                    found=True,
                    source="OFF",
                    food_record=best_match,
                    confidence=best_confidence,
                )

        except Exception as e:
            logger.error(f"Error searching in OFF: {e}")

        return ProductSearchResult(
            product_name=product_name, found=False, error_message="OFF search failed"
        )

    def _calculate_confidence(self, search_name: str, found_name: str) -> float:
        """
        RU: Вычислить уверенность в совпадении названий.
        EN: Calculate confidence in name matching.

        Args:
            search_name: Искомое название
            found_name: Найденное название

        Returns:
            Уровень уверенности от 0.0 до 1.0
        """
        search_clean = search_name.lower().replace(" ", "").replace("_", "")
        found_clean = found_name.lower().replace(" ", "").replace("_", "")

        # Точное совпадение
        if search_clean == found_clean:
            return 1.0

        # Одно название содержит другое
        if search_clean in found_clean or found_clean in search_clean:
            return 0.8

        # Проверяем общие слова
        search_words = set(search_name.lower().split())
        found_words = set(found_name.lower().split())
        common_words = search_words.intersection(found_words)

        if common_words:
            return len(common_words) / max(len(search_words), len(found_words))

        return 0.0

    def add_product_to_database(self, search_result: ProductSearchResult) -> bool:
        """
        RU: Добавить найденный продукт в базу данных.
        EN: Add found product to database.

        Args:
            search_result: Результат поиска продукта

        Returns:
            True, если продукт успешно добавлен
        """
        if not search_result.found or not search_result.food_record:
            return False

        try:
            # Конвертируем FoodRecord в FoodItem
            food_item = self._convert_to_food_item(
                search_result.food_record, search_result.product_name
            )

            # Добавляем в базу данных
            self._append_to_food_db(food_item)

            logger.info(f"Successfully added {search_result.product_name} to database")
            return True

        except Exception as e:
            logger.error(f"Failed to add {search_result.product_name}: {e}")
            return False

    def _convert_to_food_item(
        self, food_record: FoodRecord, product_name: str
    ) -> FoodItem:
        """
        RU: Конвертировать FoodRecord в FoodItem.
        EN: Convert FoodRecord to FoodItem.

        Args:
            food_record: Запись о продукте
            product_name: Название продукта

        Returns:
            FoodItem объект
        """
        return FoodItem(
            name=product_name,
            unit_per=100,
            unit="g",
            protein_g=food_record.protein_g,
            fat_g=food_record.fat_g,
            carbs_g=food_record.carbs_g,
            fiber_g=food_record.fiber_g,
            Fe_mg=food_record.Fe_mg,
            Ca_mg=food_record.Ca_mg,
            VitD_IU=food_record.VitD_IU,
            B12_ug=food_record.B12_ug,
            Folate_ug=food_record.Folate_ug,
            Iodine_ug=food_record.Iodine_ug,
            K_mg=food_record.K_mg,
            Mg_mg=food_record.Mg_mg,
            price_per_unit=0.0,  # По умолчанию
            flags=set(),  # По умолчанию
        )

    def _append_to_food_db(self, food_item: FoodItem) -> None:
        """
        RU: Добавить продукт в файл базы данных.
        EN: Add product to food database file.

        Args:
            food_item: Продукт для добавления
        """
        db_path = Path("data/food_db.csv")

        # Проверяем, существует ли файл
        file_exists = db_path.exists()

        with open(db_path, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "name",
                "unit_per",
                "unit",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "Fe_mg",
                "Ca_mg",
                "VitD_IU",
                "B12_ug",
                "Folate_ug",
                "Iodine_ug",
                "K_mg",
                "Mg_mg",
                "price_per_unit",
                "flags",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Записываем заголовок, если файл новый
            if not file_exists:
                writer.writeheader()

            # Записываем данные продукта
            writer.writerow(
                {
                    "name": food_item.name,
                    "unit_per": food_item.unit_per,
                    "unit": food_item.unit,
                    "protein_g": food_item.protein_g,
                    "fat_g": food_item.fat_g,
                    "carbs_g": food_item.carbs_g,
                    "fiber_g": food_item.fiber_g,
                    "Fe_mg": food_item.Fe_mg,
                    "Ca_mg": food_item.Ca_mg,
                    "VitD_IU": food_item.VitD_IU,
                    "B12_ug": food_item.B12_ug,
                    "Folate_ug": food_item.Folate_ug,
                    "Iodine_ug": food_item.Iodine_ug,
                    "K_mg": food_item.K_mg,
                    "Mg_mg": food_item.Mg_mg,
                    "price_per_unit": food_item.price_per_unit,
                    "flags": ",".join(food_item.flags) if food_item.flags else "",
                }
            )

    def auto_expand_database(self, recipe_ingredients: List[str]) -> Dict[str, bool]:
        """
        RU: Автоматически расширить базу данных недостающими продуктами.
        EN: Automatically expand database with missing products.

        Args:
            recipe_ingredients: Список ингредиентов из рецептов

        Returns:
            Словарь с результатами добавления продуктов
        """
        logger.info("Starting automatic database expansion")

        # Находим недостающие продукты
        missing_products = self.find_missing_products(recipe_ingredients)
        logger.info(f"Found {len(missing_products)} missing products")

        results = {}

        for product in missing_products:
            logger.info(f"Processing product: {product}")

            # Ищем продукт
            search_result = self.search_product(product)

            if search_result.found:
                # Добавляем в базу данных
                success = self.add_product_to_database(search_result)
                results[product] = success

                if success:
                    logger.info(f"✅ Successfully added {product}")
                else:
                    logger.error(f"❌ Failed to add {product}")
            else:
                logger.warning(f"⚠️ Product not found: {product}")
                results[product] = False

        logger.info("Automatic database expansion completed")
        return results

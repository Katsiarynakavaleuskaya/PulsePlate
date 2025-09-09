# -*- coding: utf-8 -*-
"""
RU: Система для работы с различными сортами и марками продуктов.
EN: System for working with different product varieties and brands.

Этот модуль предоставляет функциональность для работы с различными
сортами, марками и вариантами продуктов с учетом их пищевой ценности.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from .food_db import FoodItem

logger = logging.getLogger(__name__)


@dataclass
class ProductVariety:
    """
    RU: Разновидность продукта с учетом сорта и марки.
    EN: Product variety considering type and brand.
    """

    name: str
    variety: str
    brand: str
    protein_g: float
    fat_g: float
    carbs_g: float
    fiber_g: float
    sugar_g: float
    Fe_mg: float
    Ca_mg: float
    VitD_IU: float
    B12_ug: float
    Folate_ug: float
    Iodine_ug: float
    K_mg: float
    Mg_mg: float
    flags: Set[str]
    notes: str

    def to_food_item(self) -> FoodItem:
        """
        RU: Конвертировать в FoodItem.
        EN: Convert to FoodItem.
        """
        return FoodItem(
            name=f"{self.name} ({self.variety})",
            unit_per=100,
            unit="g",
            protein_g=self.protein_g,
            fat_g=self.fat_g,
            carbs_g=self.carbs_g,
            fiber_g=self.fiber_g,
            Fe_mg=self.Fe_mg,
            Ca_mg=self.Ca_mg,
            VitD_IU=self.VitD_IU,
            B12_ug=self.B12_ug,
            Folate_ug=self.Folate_ug,
            Iodine_ug=self.Iodine_ug,
            K_mg=self.K_mg,
            Mg_mg=self.Mg_mg,
            price_per_unit=0.0,
            flags=self.flags,
        )

    def get_calories(self) -> float:
        """
        RU: Вычислить калории (4 ккал/г белка, 4 ккал/г углеводов, 9 ккал/г жиров).
        EN: Calculate calories (4 kcal/g protein, 4 kcal/g carbs, 9 kcal/g fat).
        """
        return (self.protein_g * 4) + (self.carbs_g * 4) + (self.fat_g * 9)

    def get_sugar_content(self) -> float:
        """
        RU: Получить содержание сахара.
        EN: Get sugar content.
        """
        return self.sugar_g

    def is_low_sugar(self) -> bool:
        """
        RU: Проверить, является ли продукт низкосахарным.
        EN: Check if product is low sugar.
        """
        return self.sugar_g <= 5.0

    def is_high_protein(self) -> bool:
        """
        RU: Проверить, является ли продукт высокобелковым.
        EN: Check if product is high protein.
        """
        return self.protein_g >= 20.0

    def is_low_fat(self) -> bool:
        """
        RU: Проверить, является ли продукт низкожирным.
        EN: Check if product is low fat.
        """
        return self.fat_g <= 3.0


class ProductVarietiesManager:
    """
    RU: Менеджер для работы с различными сортами продуктов.
    EN: Manager for working with different product varieties.
    """

    def __init__(self, csv_path: str = "external/detailed_products_varieties.csv"):
        """
        RU: Инициализировать менеджер сортов продуктов.
        EN: Initialize product varieties manager.

        Args:
            csv_path: Путь к CSV файлу с данными о сортах
        """
        self.csv_path = csv_path
        self.varieties: Dict[str, List[ProductVariety]] = {}
        self._load_varieties()

    def _load_varieties(self) -> None:
        """
        RU: Загрузить данные о сортах продуктов из CSV.
        EN: Load product varieties data from CSV.
        """
        if not Path(self.csv_path).exists():
            logger.warning(f"Varieties file not found: {self.csv_path}")
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        variety = ProductVariety(
                            name=row["name"],
                            variety=row["variety"],
                            brand=row["brand"],
                            protein_g=float(row.get("protein_g", 0)),
                            fat_g=float(row.get("fat_g", 0)),
                            carbs_g=float(row.get("carbs_g", 0)),
                            fiber_g=float(row.get("fiber_g", 0)),
                            sugar_g=float(row.get("sugar_g", 0)),
                            Fe_mg=float(row.get("Fe_mg", 0)),
                            Ca_mg=float(row.get("Ca_mg", 0)),
                            VitD_IU=float(row.get("VitD_IU", 0)),
                            B12_ug=float(row.get("B12_ug", 0)),
                            Folate_ug=float(row.get("Folate_ug", 0)),
                            Iodine_ug=float(row.get("Iodine_ug", 0)),
                            K_mg=float(row.get("K_mg", 0)),
                            Mg_mg=float(row.get("Mg_mg", 0)),
                            flags=(
                                set(row.get("flags", "").split(","))
                                if row.get("flags")
                                else set()
                            ),
                            notes=row.get("notes", ""),
                        )

                        if variety.name not in self.varieties:
                            self.varieties[variety.name] = []
                        self.varieties[variety.name].append(variety)

                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid variety record: {e}")
                        continue

            logger.info(f"Loaded {len(self.varieties)} product types with varieties")

        except Exception as e:
            logger.error(f"Error loading varieties: {e}")

    def get_varieties(self, product_name: str) -> List[ProductVariety]:
        """
        RU: Получить все сорта продукта.
        EN: Get all varieties of a product.

        Args:
            product_name: Название продукта

        Returns:
            Список сортов продукта
        """
        return self.varieties.get(product_name, [])

    def get_best_variety(
        self, product_name: str, criteria: str = "balanced"
    ) -> Optional[ProductVariety]:
        """
        RU: Получить лучший сорт продукта по критериям.
        EN: Get best product variety by criteria.

        Args:
            product_name: Название продукта
            criteria: Критерий выбора ("balanced", "low_sugar", "high_protein", "low_fat")

        Returns:
            Лучший сорт продукта или None
        """
        varieties = self.get_varieties(product_name)
        if not varieties:
            return None

        if criteria == "balanced":
            # Выбираем сорт с наиболее сбалансированным составом
            return min(
                varieties,
                key=lambda v: abs(v.protein_g - 15)
                + abs(v.fat_g - 10)
                + abs(v.sugar_g - 5),
            )
        elif criteria == "low_sugar":
            return min(varieties, key=lambda v: v.sugar_g)
        elif criteria == "high_protein":
            return max(varieties, key=lambda v: v.protein_g)
        elif criteria == "low_fat":
            return min(varieties, key=lambda v: v.fat_g)
        else:
            return varieties[0]  # Возвращаем первый доступный

    def search_varieties(
        self, product_name: str, variety_name: str = None, brand: str = None
    ) -> List[ProductVariety]:
        """
        RU: Поиск сортов продукта по критериям.
        EN: Search product varieties by criteria.

        Args:
            product_name: Название продукта
            variety_name: Название сорта (опционально)
            brand: Марка (опционально)

        Returns:
            Список найденных сортов
        """
        varieties = self.get_varieties(product_name)
        if not varieties:
            return []

        filtered = varieties
        if variety_name:
            filtered = [
                v for v in filtered if variety_name.lower() in v.variety.lower()
            ]
        if brand:
            filtered = [v for v in filtered if brand.lower() in v.brand.lower()]

        return filtered

    def get_nutritional_comparison(
        self, product_name: str
    ) -> Dict[str, Dict[str, float]]:
        """
        RU: Получить сравнение питательной ценности сортов продукта.
        EN: Get nutritional comparison of product varieties.

        Args:
            product_name: Название продукта

        Returns:
            Словарь с сравнением питательной ценности
        """
        varieties = self.get_varieties(product_name)
        if not varieties:
            return {}

        comparison = {}
        for variety in varieties:
            key = f"{variety.variety} ({variety.brand})"
            comparison[key] = {
                "calories": variety.get_calories(),
                "protein": variety.protein_g,
                "fat": variety.fat_g,
                "carbs": variety.carbs_g,
                "sugar": variety.sugar_g,
                "fiber": variety.fiber_g,
                "calcium": variety.Ca_mg,
                "iron": variety.Fe_mg,
            }

        return comparison

    def recommend_variety(
        self, product_name: str, user_preferences: Dict[str, str]
    ) -> Optional[ProductVariety]:
        """
        RU: Рекомендовать сорт продукта на основе предпочтений пользователя.
        EN: Recommend product variety based on user preferences.

        Args:
            product_name: Название продукта
            user_preferences: Предпочтения пользователя

        Returns:
            Рекомендуемый сорт продукта
        """
        varieties = self.get_varieties(product_name)
        if not varieties:
            return None

        # Применяем фильтры на основе предпочтений
        filtered = varieties

        # Фильтр по сахару
        if user_preferences.get("low_sugar", False):
            low_sugar_varieties = [v for v in filtered if v.is_low_sugar()]
            if low_sugar_varieties:
                filtered = low_sugar_varieties

        # Фильтр по жирам
        if user_preferences.get("low_fat", False):
            low_fat_varieties = [v for v in filtered if v.is_low_fat()]
            if low_fat_varieties:
                filtered = low_fat_varieties

        # Фильтр по белку
        if user_preferences.get("high_protein", False):
            high_protein_varieties = [v for v in filtered if v.is_high_protein()]
            if high_protein_varieties:
                filtered = high_protein_varieties

        # Фильтр по флагам
        if user_preferences.get("vegetarian", False):
            veg_varieties = [v for v in filtered if "VEG" in v.flags]
            if veg_varieties:
                filtered = veg_varieties

        if user_preferences.get("gluten_free", False):
            gf_varieties = [v for v in filtered if "GF" in v.flags]
            if gf_varieties:
                filtered = gf_varieties

        if not filtered:
            return varieties[0]  # Возвращаем первый доступный, если ничего не подходит

        # Выбираем лучший из отфильтрованных
        if len(filtered) == 1:
            return filtered[0]

        # Для нескольких вариантов выбираем наиболее сбалансированный
        return min(
            filtered,
            key=lambda v: abs(v.protein_g - 15)
            + abs(v.fat_g - 10)
            + abs(v.sugar_g - 5),
        )

    def get_all_products(self) -> List[str]:
        """
        RU: Получить список всех продуктов с сортами.
        EN: Get list of all products with varieties.

        Returns:
            Список названий продуктов
        """
        return list(self.varieties.keys())

    def get_statistics(self) -> Dict[str, int]:
        """
        RU: Получить статистику по сортам продуктов.
        EN: Get statistics on product varieties.

        Returns:
            Словарь со статистикой
        """
        total_products = len(self.varieties)
        total_varieties = sum(len(varieties) for varieties in self.varieties.values())
        avg_varieties_per_product = (
            total_varieties / total_products if total_products > 0 else 0
        )

        return {
            "total_products": total_products,
            "total_varieties": total_varieties,
            "avg_varieties_per_product": round(avg_varieties_per_product, 2),
        }

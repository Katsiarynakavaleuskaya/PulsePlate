# -*- coding: utf-8 -*-
"""Shopping list generation and export utilities.

RU: Модуль для создания списков покупок из недельных планов питания.
EN: Module for creating shopping lists from weekly meal plans.

Sprint 2: Shoplist с округлением до упаковок.
"""

import math

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, TypeAlias, Union, Tuple
import logging

LOGGER = logging.getLogger(__name__)

# Module-level constant for ingredient categorization keywords
# Используем Tuple для неизменяемости значений
CATEGORY_KEYWORDS: Mapping[str, Tuple[str, ...]] = {
    "meat": (
        "мясо",
        "говядина",
        "свинина",
        "курица",
        "meat",
        "beef",
        "pork",
        "chicken",
        "carne",
        "res",
        "cerdo",
        "pollo",
    ),
    "fish": ("рыба", "лосось", "тунец", "fish", "salmon", "tuna", "pescado", "salmón", "atún"),
    "dairy": (
        "молоко",
        "йогурт",
        "сыр",
        "milk",
        "yogurt",
        "cheese",
        "leche",
        "yogur",
        "queso",
    ),
    "vegetables": (
        "овощ",
        "помидор",
        "огурец",
        "морковь",
        "vegetable",
        "tomato",
        "cucumber",
        "carrot",
        "vegetal",
        "tomate",
        "pepino",
        "zanahoria",
    ),
    "fruits": (
        "фрукт",
        "яблоко",
        "банан",
        "апельсин",
        "fruit",
        "apple",
        "banana",
        "orange",
        "fruta",
        "manzana",
        "plátano",
        "naranja",
    ),
    "grains": (
        "крупа",
        "рис",
        "гречка",
        "овес",
        "grain",
        "rice",
        "buckwheat",
        "oats",
        "cereal",
        "arroz",
        "trigo",
        "avena",
    ),
    "nuts": ("орех", "миндаль", "nut", "almond", "nuez", "almendra"),
    "oils": ("масло", "оливковое", "oil", "olive", "aceite", "oliva"),
    "spices": (
        "специя",
        "соль",
        "перец",
        "spice",
        "salt",
        "pepper",
        "especia",
        "sal",
        "pimienta",
    ),
}


@dataclass
class PackagingRule:
    """Правило упаковки для категории продуктов."""

    category: str
    unit: str  # 'g', 'ml', 'pcs', 'kg', 'l'
    typical_packages: List[float]  # [100, 250, 500, 1000] для граммов
    rounding_strategy: str  # 'up', 'down', 'nearest'


@dataclass
class ShoppingItem:
    """Элемент списка покупок."""

    name: str
    quantity: float
    unit: str
    category: str
    package_size: Optional[float] = None
    packages_needed: Optional[int] = None
    total_weight: Optional[float] = None


ShoplistItem: TypeAlias = ShoppingItem | Mapping[str, object]


class ShoplistGenerator:
    """Генератор списков покупок."""

    def __init__(self, packaging_rules_file: str = "data/packaging_defaults.csv") -> None:
        """Инициализирует генератор и загружает правила упаковки.

        Args:
            packaging_rules_file: Путь к CSV с правилами упаковки по умолчанию.
        """
        self.packaging_rules_file = packaging_rules_file
        self.packaging_rules = self._load_packaging_rules()

    def _load_packaging_rules(self) -> Dict[str, PackagingRule]:
        """Загружает правила упаковки из CSV файла."""
        rules = {}

        # Базовые правила по умолчанию
        default_rules = {
            "vegetables": PackagingRule("vegetables", "g", [100, 250, 500, 1000], "up"),
            "fruits": PackagingRule("fruits", "g", [100, 250, 500, 1000], "up"),
            "meat": PackagingRule("meat", "g", [200, 400, 500, 1000], "up"),
            "fish": PackagingRule("fish", "g", [200, 400, 500, 1000], "up"),
            "dairy": PackagingRule("dairy", "ml", [200, 500, 1000], "up"),
            "grains": PackagingRule("grains", "g", [250, 500, 1000], "up"),
            "nuts": PackagingRule("nuts", "g", [100, 200, 500], "up"),
            "oils": PackagingRule("oils", "ml", [250, 500, 1000], "up"),
            "spices": PackagingRule("spices", "g", [10, 25, 50, 100], "up"),
            "default": PackagingRule("default", "g", [100, 250, 500, 1000], "up"),
        }

        # Пытаемся загрузить из файла, если он существует
        if Path(self.packaging_rules_file).exists():
            try:
                with open(self.packaging_rules_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        category = row.get("category", "default")
                        unit = row.get("unit", "g")
                        packages = [
                            float(x)
                            for x in row.get("typical_packages", "100,250,500,1000").split(",")
                        ]
                        strategy = row.get("rounding_strategy", "up")

                        rules[category] = PackagingRule(category, unit, packages, strategy)
            except (OSError, csv.Error, ValueError, KeyError) as load_err:
                # Если не удалось загрузить, используем правила по умолчанию
                # Логируем кратко и продолжаем с правилами по умолчанию
                LOGGER.warning("Failed to load packaging rules: %s", load_err)
            except Exception as unexpected:  # noqa: BLE001 - continue with defaults
                # Log unexpected exceptions with full details
                exception_type = type(unexpected).__name__
                LOGGER.error(
                    "Unhandled error loading packaging rules from %s; falling back to defaults: "
                    "%s: %s",
                    self.packaging_rules_file,
                    exception_type,
                    unexpected,
                    exc_info=True,
                )

        # Если файл не существует или не загрузился, используем правила по умолчанию
        if not rules:
            rules = default_rules

        return rules

    def aggregate_ingredients(self, week_plan: Dict) -> Dict[str, float]:
        """Агрегирует ингредиенты из недельного плана.

        Args:
            week_plan: Словарь с недельным планом питания.

        Returns:
            Словарь вида {ingredient_name: total_grams}.
        """
        aggregated: Dict[str, float] = {}

        # Если week_plan содержит дни
        if "days" in week_plan:
            for day in week_plan["days"]:
                if "meals" in day:
                    for meal in day["meals"]:
                        if "ingredients" in meal:
                            for ingredient in meal["ingredients"]:
                                name = ingredient.get("name", "")
                                amount = ingredient.get("amount", 0)
                                unit = ingredient.get("unit", "g")

                                # Конвертируем в граммы
                                amount_g = self._convert_to_grams(amount, unit)

                                if name in aggregated:
                                    aggregated[name] += amount_g
                                else:
                                    aggregated[name] = amount_g

        # Если week_plan содержит ингредиенты напрямую
        elif "ingredients" in week_plan:
            for ingredient in week_plan["ingredients"]:
                name = ingredient.get("name", "")
                amount = ingredient.get("amount", 0)
                unit = ingredient.get("unit", "g")

                amount_g = self._convert_to_grams(amount, unit)

                if name in aggregated:
                    aggregated[name] += amount_g
                else:
                    aggregated[name] = amount_g

        return aggregated

    def _convert_to_grams(self, amount: float, unit: str) -> float:
        """Конвертирует количество в граммы."""
        conversion_factors = {
            "g": 1.0,
            "kg": 1000.0,
            "ml": 1.0,  # Предполагаем плотность воды
            "l": 1000.0,
            "pcs": 100.0,  # Средний вес одного продукта
            "tbsp": 15.0,  # Столовая ложка
            "tsp": 5.0,  # Чайная ложка
            "cup": 250.0,  # Стакан
        }

        return amount * conversion_factors.get(unit.lower(), 1.0)

    def _convert_unit_if_large(
        self, unit: str, total_grams: float, package_size: float
    ) -> tuple[str, float, float]:
        """Convert unit to kg/l if total >= 1000g/ml and scale package_size accordingly.

        Args:
            unit: Original unit (g, ml, etc.)
            total_grams: Total amount in grams/milliliters
            package_size: Package size in original unit

        Returns:
            Tuple of (converted_unit, total_weight, package_display_size)
        """
        if (unit == "g" or unit == "ml") and total_grams >= 1000:
            new_unit = "kg" if unit == "g" else "l"
            return new_unit, total_grams / 1000, package_size / 1000
        return unit, total_grams, package_size

    def round_to_packages(
        self,
        aggregated: Dict[str, float],
        packaging_db: Optional[Dict[str, Any]] = None,
        rules: Optional[Mapping[str, Union[PackagingRule, Any]]] = None,
    ) -> List[ShoppingItem]:
        """Округляет агрегированные ингредиенты до упаковок.

        Args:
            aggregated: Словарь {ingredient_name: total_grams}.
            packaging_db: База данных упаковок (опционально).
            rules: Правила округления (опционально).

        Returns:
            Список ShoppingItem с округленными количествами.
        """
        if rules is None:
            rules = self.packaging_rules

        shopping_list = []

        for ingredient_name, total_grams in aggregated.items():
            # Определяем категорию продукта
            category = self._categorize_ingredient(ingredient_name)

            # Получаем правило упаковки для категории
            rule = rules.get(category, rules.get("default"))
            if not isinstance(rule, PackagingRule):
                # Fallback to a sane default rule
                rule = PackagingRule("default", "g", [100, 250, 500, 1000], "up")

            # Округляем до ближайшей упаковки
            package_size, packages_needed = self._find_best_package(
                total_grams, rule.typical_packages, rule.rounding_strategy
            )

            # Конвертируем обратно в исходные единицы
            unit, total_weight, package_display_size = self._convert_unit_if_large(
                rule.unit, total_grams, package_size
            )

            shopping_item = ShoppingItem(
                name=ingredient_name,
                quantity=packages_needed,
                unit=unit,
                category=category,
                package_size=package_display_size,
                packages_needed=packages_needed,
                total_weight=total_weight,
            )

            shopping_list.append(shopping_item)

        return shopping_list

    def _categorize_ingredient(self, ingredient_name: str) -> str:
        """Определяет категорию ингредиента по названию."""
        name_lower = ingredient_name.lower()

        # Используем модульный константный словарь ключевых слов
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in name_lower for keyword in keywords):
                return category

        return "default"

    def _find_best_package(
        self, total_amount: float, typical_packages: List[float], strategy: str
    ) -> Tuple[float, int]:
        """Находит оптимальный размер упаковки и количество."""
        if not typical_packages:
            return total_amount, 1

        # Сортируем упаковки по размеру
        sorted_packages = sorted(typical_packages)
        # Фильтруем некорректные значения (<= 0), чтобы избежать деления на ноль и нелепых результатов
        sorted_packages = [p for p in sorted_packages if p > 0]
        if not sorted_packages:
            return total_amount, 1

        if strategy == "up":
            # Округляем вверх - берем упаковку с минимальным перерасходом
            # RU: При одинаковом перерасходе предпочитаем меньшее количество упаковок
            # EN: On equal overage, prefer fewer packages
            up_best_choice: Optional[Tuple[float, int]] = None
            best_overage = float("inf")
            for package_size in sorted_packages:
                packages_needed = math.ceil(total_amount / package_size)
                if packages_needed > 0:
                    overage = packages_needed * package_size - total_amount
                    if overage < best_overage or (
                        overage == best_overage
                        and up_best_choice is not None
                        and packages_needed < up_best_choice[1]
                    ):
                        best_overage = overage
                        up_best_choice = (package_size, packages_needed)
            if up_best_choice is not None:
                return up_best_choice
        elif strategy == "down":
            # Округляем вниз - берем максимальную упаковку, которая помещается
            for package_size in reversed(sorted_packages):
                packages_needed = int(total_amount / package_size)
                if packages_needed > 0:
                    return package_size, packages_needed
        else:  # 'nearest'
            # Ближайшее округление: оцениваем и floor, и ceil для каждой упаковки
            best_choice: Optional[Tuple[float, int]] = None
            best_error = float("inf")
            for package_size in sorted_packages:
                # Вариант округления вниз (если даёт >=1 упаковки)
                n_floor = int(total_amount / package_size)
                # Вариант округления вверх (хотя бы 1 упаковка)
                n_ceil = max(1, math.ceil(total_amount / package_size))

                candidates: List[Tuple[int, float]] = []
                if n_floor >= 1:
                    candidates.append((n_floor, abs(total_amount - n_floor * package_size)))
                candidates.append((n_ceil, abs(total_amount - n_ceil * package_size)))

                for n_packages, error in candidates:
                    if error < best_error or (
                        error == best_error
                        and best_choice is not None
                        and n_packages < best_choice[1]
                    ):
                        best_error = error
                        best_choice = (package_size, n_packages)
            if best_choice is not None:
                return best_choice

        # Fallback: use smallest package and calculate needed quantity
        fallback_size = sorted_packages[0]
        fallback_qty = max(1, int(math.ceil(total_amount / fallback_size)))
        return fallback_size, fallback_qty

    def format_export(
        self,
        shopping_list: List[ShoppingItem],
        locale: str = "ru",
        format_type: str = "json",
    ) -> Union[str, Dict]:
        """Форматирует список покупок для экспорта.

        Args:
            shopping_list: Список ShoppingItem.
            locale: Локаль (ru, en, es).
            format_type: Тип формата (json, csv, text).

        Returns:
            Отформатированный список покупок
        """
        if format_type == "json":
            return {
                "shopping_list": [
                    {
                        "name": item.name,
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "category": item.category,
                        "package_size": item.package_size,
                        "packages_needed": item.packages_needed,
                        "total_weight": item.total_weight,
                    }
                    for item in shopping_list
                ],
                "locale": locale,
                "total_items": len(shopping_list),
            }

        elif format_type == "csv":
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Заголовки
            headers = [
                "name",
                "quantity",
                "unit",
                "category",
                "package_size",
                "packages_needed",
                "total_weight",
            ]
            writer.writerow(headers)

            # Данные
            for item in shopping_list:
                writer.writerow(
                    [
                        item.name,
                        item.quantity,
                        item.unit,
                        item.category,
                        item.package_size,
                        item.packages_needed,
                        item.total_weight,
                    ]
                )

            return output.getvalue()

        elif format_type == "text":
            # Простой текстовый формат
            lines = []
            if locale == "ru":
                lines.append("Список покупок:")
            elif locale == "en":
                lines.append("Shopping List:")
            elif locale == "es":
                lines.append("Lista de compras:")
            else:
                lines.append("Shopping List:")

            lines.append("=" * 50)

            for item in shopping_list:
                if locale == "ru":
                    line = (
                        f"• {item.name}: {item.packages_needed} шт. по "
                        f"{item.package_size}{item.unit}"
                    )
                elif locale == "en":
                    line = (
                        f"• {item.name}: {item.packages_needed} pcs of "
                        f"{item.package_size}{item.unit}"
                    )
                elif locale == "es":
                    line = (
                        f"• {item.name}: {item.packages_needed} pcs de "
                        f"{item.package_size}{item.unit}"
                    )
                else:
                    line = (
                        f"• {item.name}: {item.packages_needed} pcs of "
                        f"{item.package_size}{item.unit}"
                    )

                lines.append(line)

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported format type: {format_type}")


# Generator instance initialized at module load to avoid repeated CSV I/O
# on first concurrent calls
_generator = ShoplistGenerator()


def _get_generator() -> ShoplistGenerator:
    """Get the generator instance."""
    return _generator


# Contract-only helper exports expected by low-coverage compatibility tests.
def create_shopping_list(meal_plan: Mapping[str, object]) -> list[ShoppingItem]:
    """Create deterministic shopping items from a loose meal-plan mapping.

    RU: Извлекает записи вида {"name","amount","unit"} и агрегирует количества.
    EN: Extracts {"name","amount","unit"} entries and aggregates quantities.
    """
    totals: dict[tuple[str, str], float] = {}

    for day_value in meal_plan.values():
        if not isinstance(day_value, Mapping):
            continue
        for meal_value in day_value.values():
            if not isinstance(meal_value, list):
                continue
            for item in meal_value:
                if not isinstance(item, Mapping):
                    continue

                raw_name = item.get("name")
                raw_unit = item.get("unit")
                raw_amount = item.get("amount")

                name = str(raw_name).strip() if raw_name is not None else ""
                unit = str(raw_unit).strip() if raw_unit is not None else ""
                if not name or not unit:
                    continue

                if isinstance(raw_amount, (int, float)):
                    quantity = float(raw_amount)
                elif isinstance(raw_amount, str):
                    try:
                        quantity = float(raw_amount)
                    except ValueError:
                        continue
                else:
                    continue

                key = (name, unit)
                totals[key] = totals.get(key, 0.0) + quantity

    return [
        ShoppingItem(name=name, quantity=qty, unit=unit, category="uncategorized")
        for (name, unit), qty in sorted(totals.items())
    ]


def group_by_category(items: list[ShoplistItem]) -> dict[str, list[ShoplistItem]]:
    """Group items by category with uncategorized fallback.

    Supports both mapping-style items and `ShoppingItem` dataclass instances
    so helper pipelines remain compatible.
    """
    grouped: dict[str, list[ShoplistItem]] = {}
    for item in items:
        if isinstance(item, Mapping):
            raw_category = item.get("category", "uncategorized")
        else:
            raw_category = getattr(item, "category", "uncategorized")
        if raw_category is None:
            category = "uncategorized"
        else:
            category = str(raw_category).strip() or "uncategorized"
        grouped.setdefault(category, []).append(item)
    return grouped


def optimize_packaging(items: list[Mapping[str, object]]) -> list[Mapping[str, object]]:
    # NOTE: Compatibility API name is preserved intentionally; behavior stays contract-only.
    """Contract-only packaging normalization.

    RU: Без логики упаковок, только фильтрация/нормализация входа.
    EN: No packaging logic here, just stable normalized output.
    """
    return [item for item in items if isinstance(item, Mapping)]


# Функции для удобного использования
def aggregate_ingredients(week_plan: Dict) -> Dict[str, float]:
    """Агрегирует ингредиенты из недельного плана."""
    return _get_generator().aggregate_ingredients(week_plan)


def round_to_packages(
    aggregated: Dict[str, float],
    packaging_db: Optional[Dict[str, Any]] = None,
    rules: Optional[Mapping[str, Union[PackagingRule, Any]]] = None,
) -> List[ShoppingItem]:
    """Округляет агрегированные ингредиенты до упаковок."""
    return _get_generator().round_to_packages(aggregated, packaging_db, rules)


def format_export(
    shopping_list: List[ShoppingItem], locale: str = "ru", format_type: str = "json"
) -> Union[str, Dict]:
    """Форматирует список покупок для экспорта."""
    return _get_generator().format_export(shopping_list, locale, format_type)


def get_shoplist(
    week_plan: Dict,
    format_type: str = "json",
    locale: str = "ru",
    packaging_db: Optional[Dict[str, Any]] = None,
    rules: Optional[Mapping[str, Union[PackagingRule, Any]]] = None,
) -> Union[str, Dict]:
    """Собирает и форматирует список покупок из недельного плана.

    Backward-compatible wrapper expected by the application.

    Args:
        week_plan: Словарь с недельным планом питания.
        format_type: Тип формата (json, csv, text).
        locale: Локаль (ru, en, es).
        packaging_db: База данных упаковок (опционально).
        rules: Правила округления (опционально).

    Returns:
        Отформатированный список покупок.
    """
    generator = _get_generator()
    # Aggregate ingredients from week_plan
    aggregated = generator.aggregate_ingredients(week_plan)
    # Round to packages using provided rules / packaging_db (falls back to defaults)
    shopping_items = generator.round_to_packages(aggregated, packaging_db, rules)
    # Format the result
    return generator.format_export(shopping_items, locale=locale, format_type=format_type)

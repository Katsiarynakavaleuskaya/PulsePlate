# -*- coding: utf-8 -*-
"""
Tests for Sprint 2: Shoplist functionality

RU: Тесты для функциональности списков покупок с округлением до упаковок
EN: Tests for shopping list functionality with package rounding
"""

from unittest.mock import patch

import pytest

from core.shoplist import (
    PackagingRule,
    ShoplistGenerator,
    ShoppingItem,
    aggregate_ingredients,
    format_export,
    round_to_packages,
)


class TestPackagingRule:
    """Тесты для класса PackagingRule"""

    def test_packaging_rule_creation(self):
        """Тест создания правила упаковки"""
        rule = PackagingRule(
            category="vegetables",
            unit="g",
            typical_packages=[100, 250, 500, 1000],
            rounding_strategy="up",
        )

        assert rule.category == "vegetables"
        assert rule.unit == "g"
        assert rule.typical_packages == [100, 250, 500, 1000]
        assert rule.rounding_strategy == "up"


class TestShoppingItem:
    """Тесты для класса ShoppingItem"""

    def test_shopping_item_creation(self):
        """Тест создания элемента списка покупок"""
        item = ShoppingItem(
            name="Морковь",
            quantity=2,
            unit="g",
            category="vegetables",
            package_size=500,
            packages_needed=2,
            total_weight=1000,
        )

        assert item.name == "Морковь"
        assert item.quantity == 2
        assert item.unit == "g"
        assert item.category == "vegetables"
        assert item.package_size == 500
        assert item.packages_needed == 2
        assert item.total_weight == 1000


class TestShoplistGenerator:
    """Тесты для класса ShoplistGenerator"""

    def test_init_with_default_rules(self):
        """Тест инициализации с правилами по умолчанию"""
        generator = ShoplistGenerator()

        assert isinstance(generator.packaging_rules, dict)
        assert "vegetables" in generator.packaging_rules
        assert "meat" in generator.packaging_rules
        assert "default" in generator.packaging_rules

    @patch("pathlib.Path.exists")
    def test_load_packaging_rules_from_file(self, mock_exists):
        """Тест загрузки правил из файла"""
        mock_exists.return_value = True

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = [
                "category,unit,typical_packages,rounding_strategy\n",
                'vegetables,g,"100,250,500",up\n',
            ]

            generator = ShoplistGenerator()
            rules = generator._load_packaging_rules()

            assert "vegetables" in rules
            assert rules["vegetables"].typical_packages == [100, 250, 500]

    def test_convert_to_grams(self):
        """Тест конвертации в граммы"""
        generator = ShoplistGenerator()

        # Тест различных единиц измерения
        assert generator._convert_to_grams(1, "g") == 1.0
        assert generator._convert_to_grams(1, "kg") == 1000.0
        assert generator._convert_to_grams(1, "ml") == 1.0
        assert generator._convert_to_grams(1, "l") == 1000.0
        assert generator._convert_to_grams(1, "pcs") == 100.0
        assert generator._convert_to_grams(1, "tbsp") == 15.0
        assert generator._convert_to_grams(1, "tsp") == 5.0
        assert generator._convert_to_grams(1, "cup") == 250.0
        assert generator._convert_to_grams(1, "unknown") == 1.0

    def test_categorize_ingredient(self):
        """Тест категоризации ингредиентов"""
        generator = ShoplistGenerator()

        # Тест различных категорий
        assert generator._categorize_ingredient("говядина") == "meat"
        assert generator._categorize_ingredient("chicken") == "meat"
        assert generator._categorize_ingredient("лосось") == "fish"
        assert generator._categorize_ingredient("salmon") == "fish"
        assert generator._categorize_ingredient("молоко") == "dairy"
        assert generator._categorize_ingredient("cheese") == "dairy"
        assert generator._categorize_ingredient("морковь") == "vegetables"
        assert generator._categorize_ingredient("tomato") == "vegetables"
        assert generator._categorize_ingredient("яблоко") == "fruits"
        assert generator._categorize_ingredient("apple") == "fruits"
        assert generator._categorize_ingredient("рис") == "grains"
        assert generator._categorize_ingredient("rice") == "grains"
        assert generator._categorize_ingredient("орех") == "nuts"
        assert generator._categorize_ingredient("almond") == "nuts"
        assert generator._categorize_ingredient("масло") == "oils"
        assert generator._categorize_ingredient("oil") == "oils"
        assert generator._categorize_ingredient("соль") == "spices"
        assert generator._categorize_ingredient("salt") == "spices"
        assert generator._categorize_ingredient("неизвестный продукт") == "default"

    def test_find_best_package_up_strategy(self):
        """Тест поиска лучшей упаковки с стратегией 'up'"""
        generator = ShoplistGenerator()

        # Тест округления вверх - берет первую упаковку, которая может покрыть количество
        package_size, packages_needed = generator._find_best_package(
            300, [100, 250, 500, 1000], "up"
        )
        assert package_size == 100  # Первая упаковка, которая может покрыть 300g
        assert packages_needed == 3  # 300 / 100 = 3 упаковки

    def test_find_best_package_down_strategy(self):
        """Тест поиска лучшей упаковки с стратегией 'down'"""
        generator = ShoplistGenerator()

        # Тест округления вниз
        package_size, packages_needed = generator._find_best_package(
            300, [100, 250, 500, 1000], "down"
        )
        assert package_size == 250
        assert packages_needed == 1  # 300 / 250 = 1.2, округляем вниз до 1

    def test_find_best_package_nearest_strategy(self):
        """Тест поиска лучшей упаковки с стратегией 'nearest'"""
        generator = ShoplistGenerator()

        # Тест ближайшего округления
        package_size, packages_needed = generator._find_best_package(
            300, [100, 250, 500, 1000], "nearest"
        )
        assert package_size in [100, 250, 500, 1000]
        assert packages_needed >= 1

    def test_aggregate_ingredients_from_days(self):
        """Тест агрегации ингредиентов из дней"""
        generator = ShoplistGenerator()

        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "Морковь", "amount": 100, "unit": "g"},
                                {"name": "Лук", "amount": 50, "unit": "g"},
                            ]
                        }
                    ]
                },
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "Морковь", "amount": 150, "unit": "g"},
                                {"name": "Картофель", "amount": 200, "unit": "g"},
                            ]
                        }
                    ]
                },
            ]
        }

        aggregated = generator.aggregate_ingredients(week_plan)

        assert "Морковь" in aggregated
        assert aggregated["Морковь"] == 250  # 100 + 150
        assert "Лук" in aggregated
        assert aggregated["Лук"] == 50
        assert "Картофель" in aggregated
        assert aggregated["Картофель"] == 200

    def test_aggregate_ingredients_direct(self):
        """Тест агрегации ингредиентов напрямую"""
        generator = ShoplistGenerator()

        week_plan = {
            "ingredients": [
                {"name": "Морковь", "amount": 100, "unit": "g"},
                {"name": "Лук", "amount": 50, "unit": "g"},
                {"name": "Морковь", "amount": 150, "unit": "g"},
            ]
        }

        aggregated = generator.aggregate_ingredients(week_plan)

        assert "Морковь" in aggregated
        assert aggregated["Морковь"] == 250  # 100 + 150
        assert "Лук" in aggregated
        assert aggregated["Лук"] == 50

    def test_round_to_packages(self):
        """Тест округления до упаковок"""
        generator = ShoplistGenerator()

        aggregated = {"Морковь": 300, "Молоко": 800}  # 300g  # 800ml

        shopping_list = generator.round_to_packages(aggregated)

        assert len(shopping_list) == 2

        # Проверяем, что все элементы имеют правильную структуру
        for item in shopping_list:
            assert isinstance(item, ShoppingItem)
            assert item.name in ["Морковь", "Молоко"]
            assert item.package_size is not None
            assert item.packages_needed is not None
            assert item.total_weight is not None

    def test_format_export_json(self):
        """Тест экспорта в JSON формат"""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="Морковь",
                quantity=2,
                unit="g",
                category="vegetables",
                package_size=250,
                packages_needed=2,
                total_weight=500,
            )
        ]

        result = generator.format_export(shopping_list, locale="ru", format_type="json")

        assert isinstance(result, dict)
        assert "shopping_list" in result
        assert "locale" in result
        assert "total_items" in result
        assert result["locale"] == "ru"
        assert result["total_items"] == 1
        assert len(result["shopping_list"]) == 1

    def test_format_export_csv(self):
        """Тест экспорта в CSV формат"""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="Морковь",
                quantity=2,
                unit="g",
                category="vegetables",
                package_size=250,
                packages_needed=2,
                total_weight=500,
            )
        ]

        result = generator.format_export(shopping_list, locale="ru", format_type="csv")

        assert isinstance(result, str)
        assert "name,quantity,unit,category" in result
        assert "Морковь" in result

    def test_format_export_text(self):
        """Тест экспорта в текстовый формат"""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="Морковь",
                quantity=2,
                unit="g",
                category="vegetables",
                package_size=250,
                packages_needed=2,
                total_weight=500,
            )
        ]

        result = generator.format_export(shopping_list, locale="ru", format_type="text")

        assert isinstance(result, str)
        assert "Список покупок:" in result
        assert "Морковь" in result
        assert "2 шт. по 250g" in result

    def test_format_export_unsupported_format(self):
        """Тест экспорта в неподдерживаемый формат"""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="Морковь",
                quantity=2,
                unit="g",
                category="vegetables",
                package_size=250,
                packages_needed=2,
                total_weight=500,
            )
        ]

        with pytest.raises(ValueError, match="Unsupported format type"):
            generator.format_export(shopping_list, locale="ru", format_type="xml")


class TestConvenienceFunctions:
    """Тесты для удобных функций"""

    def test_aggregate_ingredients_function(self):
        """Тест функции aggregate_ingredients"""
        week_plan = {"ingredients": [{"name": "Морковь", "amount": 100, "unit": "g"}]}

        result = aggregate_ingredients(week_plan)

        assert isinstance(result, dict)
        assert "Морковь" in result
        assert result["Морковь"] == 100

    def test_round_to_packages_function(self):
        """Тест функции round_to_packages"""
        aggregated = {"Морковь": 300}

        result = round_to_packages(aggregated)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ShoppingItem)

    def test_format_export_function(self):
        """Тест функции format_export"""
        shopping_list = [
            ShoppingItem(
                name="Морковь",
                quantity=2,
                unit="g",
                category="vegetables",
                package_size=250,
                packages_needed=2,
                total_weight=500,
            )
        ]

        result = format_export(shopping_list, locale="ru", format_type="json")

        assert isinstance(result, dict)
        assert "shopping_list" in result


class TestIntegration:
    """Интеграционные тесты"""

    def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        generator = ShoplistGenerator()

        # Создаем недельный план
        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "Морковь", "amount": 100, "unit": "g"},
                                {"name": "Лук", "amount": 50, "unit": "g"},
                                {"name": "Молоко", "amount": 200, "unit": "ml"},
                            ]
                        }
                    ]
                },
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "Морковь", "amount": 150, "unit": "g"},
                                {"name": "Картофель", "amount": 200, "unit": "g"},
                                {"name": "Молоко", "amount": 300, "unit": "ml"},
                            ]
                        }
                    ]
                },
            ]
        }

        # Агрегируем ингредиенты
        aggregated = generator.aggregate_ingredients(week_plan)

        # Округляем до упаковок
        shopping_list = generator.round_to_packages(aggregated)

        # Форматируем для экспорта
        formatted = generator.format_export(shopping_list, locale="ru", format_type="json")

        # Проверяем результат
        assert isinstance(formatted, dict)
        assert "shopping_list" in formatted
        assert formatted["total_items"] == 4  # Морковь, Лук, Молоко, Картофель

        # Проверяем, что Морковь агрегировалась правильно
        carrot_item = next(item for item in formatted["shopping_list"] if item["name"] == "Морковь")
        assert carrot_item["total_weight"] == 250  # 100 + 150

        # Проверяем, что Молоко агрегировалось правильно
        milk_item = next(item for item in formatted["shopping_list"] if item["name"] == "Молоко")
        assert milk_item["total_weight"] == 500  # 200 + 300

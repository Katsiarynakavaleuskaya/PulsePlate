# -*- coding: utf-8 -*-
"""
Additional coverage tests for core/shoplist.py to reach 97% coverage
"""

import pytest

from core.shoplist import ShoplistGenerator, ShoppingItem


class TestShoplistAdditional:
    """Additional tests to boost core/shoplist.py coverage to 97%."""

    def test_aggregate_ingredients_with_days_structure(self):
        """Test aggregate_ingredients with days structure."""
        generator = ShoplistGenerator()

        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "flour", "amount": 100, "unit": "g"},
                                {"name": "sugar", "amount": 50, "unit": "g"},
                            ]
                        },
                        {
                            "ingredients": [
                                {"name": "flour", "amount": 200, "unit": "g"},
                                {"name": "milk", "amount": 1, "unit": "l"},
                            ]
                        },
                    ]
                }
            ]
        }

        result = generator.aggregate_ingredients(week_plan)

        assert "flour" in result
        assert "sugar" in result
        assert "milk" in result
        assert result["flour"] == 300.0  # 100 + 200
        assert result["sugar"] == 50.0
        assert result["milk"] == 1000.0  # 1 liter = 1000ml

    def test_aggregate_ingredients_with_direct_ingredients(self):
        """Test aggregate_ingredients with direct ingredients structure."""
        generator = ShoplistGenerator()

        week_plan = {
            "ingredients": [
                {"name": "flour", "amount": 500, "unit": "g"},
                {"name": "sugar", "amount": 100, "unit": "g"},
                {"name": "flour", "amount": 200, "unit": "g"},  # Duplicate
            ]
        }

        result = generator.aggregate_ingredients(week_plan)

        assert "flour" in result
        assert "sugar" in result
        assert result["flour"] == 700.0  # 500 + 200
        assert result["sugar"] == 100.0

    def test_convert_to_grams_various_units(self):
        """Test _convert_to_grams with various units."""
        generator = ShoplistGenerator()

        # Test different units
        assert generator._convert_to_grams(100, "g") == 100.0
        assert generator._convert_to_grams(1, "kg") == 1000.0
        assert generator._convert_to_grams(500, "ml") == 500.0
        assert generator._convert_to_grams(1, "l") == 1000.0
        assert generator._convert_to_grams(5, "pcs") == 500.0
        assert generator._convert_to_grams(2, "tbsp") == 30.0
        assert generator._convert_to_grams(3, "tsp") == 15.0
        assert generator._convert_to_grams(1, "cup") == 250.0

        # Test unknown unit (should default to 1.0)
        assert generator._convert_to_grams(100, "unknown") == 100.0

    def test_convert_to_grams_case_insensitive(self):
        """Test _convert_to_grams with case insensitive units."""
        generator = ShoplistGenerator()

        assert generator._convert_to_grams(1, "KG") == 1000.0
        assert generator._convert_to_grams(1, "Kg") == 1000.0
        assert generator._convert_to_grams(1, "kG") == 1000.0

    def test_round_to_packages_with_unit_conversion_kg(self):
        """Test round_to_packages with kg unit conversion."""
        generator = ShoplistGenerator()

        # Test with 1500g (should convert to kg)
        ingredients = {"flour": 1500.0}
        result = generator.round_to_packages(ingredients)

        assert len(result) > 0
        item = result[0]
        assert item.unit in ["kg", "g"]
        assert item.total_weight == 1.5  # 1500g = 1.5kg

    def test_round_to_packages_with_unit_conversion_l(self):
        """Test round_to_packages with l unit conversion."""
        generator = ShoplistGenerator()

        # Test with 1500ml (should convert to l)
        ingredients = {"milk": 1500.0}
        result = generator.round_to_packages(ingredients)

        assert len(result) > 0
        item = result[0]
        assert item.unit in ["l", "ml"]
        assert item.total_weight == 1.5  # 1500ml = 1.5l

    def test_format_export_csv_format(self):
        """Test format_export with CSV format."""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="flour",
                quantity=2.0,
                packages_needed=2,
                package_size=500.0,
                unit="g",
                category="grains",
            )
        ]

        result = generator.format_export(shopping_list, "en", "csv")
        assert isinstance(result, str)
        assert "flour" in result
        assert "name,quantity,unit,category" in result

    def test_format_export_unsupported_format(self):
        """Test format_export with unsupported format."""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="flour",
                quantity=2.0,
                packages_needed=2,
                package_size=500.0,
                unit="g",
                category="grains",
            )
        ]

        with pytest.raises(ValueError, match="Unsupported format type"):
            generator.format_export(shopping_list, "en", "unsupported")

    def test_format_export_text_locale_ru_item_formatting(self):
        """Test format_export with Russian item formatting."""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="flour",
                quantity=2.0,
                packages_needed=2,
                package_size=500.0,
                unit="g",
                category="grains",
            )
        ]

        result = generator.format_export(shopping_list, "ru", "text")
        assert "• flour: 2 шт. по 500.0g" in result

    def test_format_export_text_locale_en_item_formatting(self):
        """Test format_export with English item formatting."""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="flour",
                quantity=2.0,
                packages_needed=2,
                package_size=500.0,
                unit="g",
                category="grains",
            )
        ]

        result = generator.format_export(shopping_list, "en", "text")
        assert "• flour: 2 pcs of 500.0g" in result

    def test_format_export_text_locale_es_item_formatting(self):
        """Test format_export with Spanish item formatting."""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="flour",
                quantity=2.0,
                packages_needed=2,
                package_size=500.0,
                unit="g",
                category="grains",
            )
        ]

        result = generator.format_export(shopping_list, "es", "text")
        assert "• flour: 2 pcs de 500.0g" in result

    def test_format_export_text_locale_default_item_formatting(self):
        """Test format_export with default locale item formatting."""
        generator = ShoplistGenerator()

        shopping_list = [
            ShoppingItem(
                name="flour",
                quantity=2.0,
                packages_needed=2,
                package_size=500.0,
                unit="g",
                category="grains",
            )
        ]

        result = generator.format_export(shopping_list, "unknown", "text")
        assert "• flour: 2 pcs of 500.0g" in result  # Should default to English

    def test_aggregate_ingredients_empty_week_plan(self):
        """Test aggregate_ingredients with empty week plan."""
        generator = ShoplistGenerator()

        week_plan = {}
        result = generator.aggregate_ingredients(week_plan)

        assert result == {}

    def test_aggregate_ingredients_missing_ingredients_key(self):
        """Test aggregate_ingredients with missing ingredients key."""
        generator = ShoplistGenerator()

        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            # Missing ingredients key
                        }
                    ]
                }
            ]
        }

        result = generator.aggregate_ingredients(week_plan)
        assert result == {}

    def test_aggregate_ingredients_missing_meals_key(self):
        """Test aggregate_ingredients with missing meals key."""
        generator = ShoplistGenerator()

        week_plan = {
            "days": [
                {
                    # Missing meals key
                }
            ]
        }

        result = generator.aggregate_ingredients(week_plan)
        assert result == {}

    def test_aggregate_ingredients_missing_days_key(self):
        """Test aggregate_ingredients with missing days key."""
        generator = ShoplistGenerator()

        week_plan = {
            # Missing days key
        }

        result = generator.aggregate_ingredients(week_plan)
        assert result == {}

    def test_aggregate_ingredients_ingredient_missing_name(self):
        """Test aggregate_ingredients with ingredient missing name."""
        generator = ShoplistGenerator()

        week_plan = {
            "ingredients": [
                {"amount": 100, "unit": "g"},  # Missing name
                {"name": "flour", "amount": 200, "unit": "g"},
            ]
        }

        result = generator.aggregate_ingredients(week_plan)

        # Should have both flour and empty name
        assert "flour" in result
        assert result["flour"] == 200.0
        assert "" in result
        assert result[""] == 100.0

    def test_aggregate_ingredients_ingredient_missing_amount(self):
        """Test aggregate_ingredients with ingredient missing amount."""
        generator = ShoplistGenerator()

        week_plan = {
            "ingredients": [
                {"name": "flour", "unit": "g"},  # Missing amount
                {"name": "sugar", "amount": 100, "unit": "g"},
            ]
        }

        result = generator.aggregate_ingredients(week_plan)

        # Should only have sugar, missing amount should default to 0
        assert "sugar" in result
        assert result["sugar"] == 100.0
        assert "flour" not in result or result.get("flour", 0) == 0.0

    def test_aggregate_ingredients_ingredient_missing_unit(self):
        """Test aggregate_ingredients with ingredient missing unit."""
        generator = ShoplistGenerator()

        week_plan = {
            "ingredients": [
                {"name": "flour", "amount": 100},  # Missing unit
                {"name": "sugar", "amount": 100, "unit": "g"},
            ]
        }

        result = generator.aggregate_ingredients(week_plan)

        # Both should be present, missing unit should default to "g"
        assert "flour" in result
        assert "sugar" in result
        assert result["flour"] == 100.0
        assert result["sugar"] == 100.0

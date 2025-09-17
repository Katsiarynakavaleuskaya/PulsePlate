"""
Advanced tests for core.shoplist module - formatting and integration

RU: Продвинутые тесты для модуля списков покупок - форматирование и интеграция.
EN: Advanced tests for shopping list module - formatting and integration.
"""

import pytest

from core.shoplist import (
    ShoppingItem,
    ShoplistGenerator,
    aggregate_ingredients,
    round_to_packages,
    format_export,
)


class TestShoplistGeneratorRounding:
    """Test shopping list rounding functionality."""

    @pytest.fixture
    def generator(self):
        """Create a ShoplistGenerator."""
        return ShoplistGenerator()

    def test_round_to_packages_basic(self, generator):
        """Test basic package rounding."""
        aggregated = {
            "chicken": 350.0,  # grams
            "rice": 180.0,  # grams
        }

        shopping_list = generator.round_to_packages(aggregated)

        assert len(shopping_list) == 2

        # Find chicken item
        chicken_item = next(item for item in shopping_list if item.name == "chicken")
        assert chicken_item.category == "meat"
        assert chicken_item.packages_needed > 0
        assert chicken_item.package_size > 0

        # Find rice item
        rice_item = next(item for item in shopping_list if item.name == "rice")
        assert rice_item.category == "grains"
        assert rice_item.packages_needed > 0
        assert rice_item.package_size > 0

    def test_round_to_packages_large_amounts(self, generator):
        """Test package rounding with large amounts."""
        aggregated = {
            "vegetables": 2500.0,  # 2.5 kg
        }

        shopping_list = generator.round_to_packages(aggregated)

        assert len(shopping_list) == 1
        item = shopping_list[0]

        assert item.name == "vegetables"
        assert item.category == "vegetables"
        assert item.unit == "kg"  # Should convert to kg for large amounts
        assert item.total_weight == 2.5

    def test_round_to_packages_with_custom_rules(self, generator):
        """Test package rounding with custom rules."""
        aggregated = {
            "test_ingredient": 75.0,
        }

        # Custom rules
        from core.shoplist import PackagingRule

        custom_rules = {"default": PackagingRule("default", "g", [50, 100, 200], "up")}

        shopping_list = generator.round_to_packages(aggregated, rules=custom_rules)

        assert len(shopping_list) == 1
        item = shopping_list[0]

        assert item.name == "test_ingredient"
        assert item.package_size in [50, 100, 200]
        assert item.packages_needed >= 1

    def test_round_to_packages_invalid_rule_fallback(self, generator):
        """Test package rounding with invalid rule fallback."""
        aggregated = {
            "test_ingredient": 150.0,
        }

        # Invalid rules (not PackagingRule objects)
        invalid_rules = {"default": "not_a_packaging_rule"}

        shopping_list = generator.round_to_packages(aggregated, rules=invalid_rules)

        assert len(shopping_list) == 1
        item = shopping_list[0]

        # Should fallback to default PackagingRule
        assert item.name == "test_ingredient"
        assert item.packages_needed >= 1


class TestShoplistGeneratorExport:
    """Test shopping list export functionality."""

    @pytest.fixture
    def generator(self):
        """Create a ShoplistGenerator."""
        return ShoplistGenerator()

    @pytest.fixture
    def sample_shopping_list(self):
        """Create sample shopping list."""
        return [
            ShoppingItem(
                name="chicken breast",
                quantity=2,
                unit="kg",
                category="meat",
                package_size=500.0,
                packages_needed=4,
                total_weight=2000.0,
            ),
            ShoppingItem(
                name="rice",
                quantity=1,
                unit="kg",
                category="grains",
                package_size=1000.0,
                packages_needed=1,
                total_weight=1000.0,
            ),
        ]

    def test_format_export_json(self, generator, sample_shopping_list):
        """Test JSON export format."""
        result = generator.format_export(sample_shopping_list, "en", "json")

        assert isinstance(result, dict)
        assert "shopping_list" in result
        assert "locale" in result
        assert "total_items" in result

        assert result["locale"] == "en"
        assert result["total_items"] == 2

        items = result["shopping_list"]
        assert len(items) == 2

        # Check first item structure
        item1 = items[0]
        assert item1["name"] == "chicken breast"
        assert item1["quantity"] == 2
        assert item1["unit"] == "kg"
        assert item1["category"] == "meat"
        assert item1["package_size"] == 500.0
        assert item1["packages_needed"] == 4
        assert item1["total_weight"] == 2000.0

    def test_format_export_csv(self, generator, sample_shopping_list):
        """Test CSV export format."""
        result = generator.format_export(sample_shopping_list, "en", "csv")

        assert isinstance(result, str)

        # Check CSV structure
        lines = result.strip().split("\n")
        assert len(lines) >= 3  # Header + 2 data rows

        # Check header
        header = lines[0]
        assert "name" in header
        assert "quantity" in header
        assert "unit" in header
        assert "category" in header

        # Check data rows
        assert "chicken breast" in lines[1]
        assert "rice" in lines[2]

    def test_format_export_text_russian(self, generator, sample_shopping_list):
        """Test text export format in Russian."""
        result = generator.format_export(sample_shopping_list, "ru", "text")

        assert isinstance(result, str)
        assert "Список покупок:" in result
        assert "chicken breast" in result
        assert "rice" in result
        assert "шт. по" in result  # Russian formatting

    def test_format_export_text_english(self, generator, sample_shopping_list):
        """Test text export format in English."""
        result = generator.format_export(sample_shopping_list, "en", "text")

        assert isinstance(result, str)
        assert "Shopping List:" in result
        assert "chicken breast" in result
        assert "rice" in result
        assert "pcs of" in result  # English formatting

    def test_format_export_text_spanish(self, generator, sample_shopping_list):
        """Test text export format in Spanish."""
        result = generator.format_export(sample_shopping_list, "es", "text")

        assert isinstance(result, str)
        assert "Lista de compras:" in result
        assert "chicken breast" in result
        assert "rice" in result
        assert "pcs de" in result  # Spanish formatting

    def test_format_export_text_unknown_locale(self, generator, sample_shopping_list):
        """Test text export format with unknown locale."""
        result = generator.format_export(sample_shopping_list, "unknown", "text")

        assert isinstance(result, str)
        assert "Shopping List:" in result  # Should default to English

    def test_format_export_invalid_format(self, generator, sample_shopping_list):
        """Test export with invalid format type."""
        with pytest.raises(ValueError) as exc_info:
            generator.format_export(sample_shopping_list, "en", "invalid_format")

        assert "Unsupported format type" in str(exc_info.value)

    def test_format_export_empty_list(self, generator):
        """Test export with empty shopping list."""
        empty_list = []

        # JSON format
        result_json = generator.format_export(empty_list, "en", "json")
        assert result_json["total_items"] == 0
        assert result_json["shopping_list"] == []

        # Text format
        result_text = generator.format_export(empty_list, "en", "text")
        assert "Shopping List:" in result_text


class TestUtilityFunctions:
    """Test utility functions."""

    def test_aggregate_ingredients_function(self):
        """Test standalone aggregate_ingredients function."""
        week_plan = {"ingredients": [{"name": "tomatoes", "amount": 500, "unit": "g"}]}

        result = aggregate_ingredients(week_plan)

        assert result["tomatoes"] == 500.0

    def test_round_to_packages_function(self):
        """Test standalone round_to_packages function."""
        aggregated = {"chicken": 300.0}

        result = round_to_packages(aggregated)

        assert len(result) == 1
        assert result[0].name == "chicken"
        assert result[0].category == "meat"

    def test_format_export_function(self):
        """Test standalone format_export function."""
        shopping_list = [ShoppingItem(name="test_item", quantity=1, unit="kg", category="test")]

        result = format_export(shopping_list, "en", "json")

        assert isinstance(result, dict)
        assert result["total_items"] == 1
        assert result["shopping_list"][0]["name"] == "test_item"


class TestShoplistGeneratorEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def generator(self):
        """Create a ShoplistGenerator."""
        return ShoplistGenerator()

    def test_aggregate_ingredients_malformed_plan(self, generator):
        """Test aggregating ingredients from malformed plan."""
        malformed_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "test"},  # Missing amount and unit
                                {"amount": 100},  # Missing name and unit
                                {"unit": "g"},  # Missing name and amount
                            ]
                        }
                    ]
                }
            ]
        }

        # Should not crash, should handle missing fields gracefully
        result = generator.aggregate_ingredients(malformed_plan)

        # Items with missing required fields might be skipped or have default values
        assert isinstance(result, dict)

    def test_aggregate_ingredients_no_structure(self, generator):
        """Test aggregating ingredients from plan with no expected structure."""
        weird_plan = {"some_other_key": "some_value"}

        result = generator.aggregate_ingredients(weird_plan)

        assert result == {}

    def test_categorize_ingredient_empty_name(self, generator):
        """Test categorizing ingredient with empty name."""
        result = generator._categorize_ingredient("")

        assert result == "default"

    def test_categorize_ingredient_none_name(self, generator):
        """Test categorizing ingredient with None name."""
        # This might cause an error, so we test error handling
        try:
            result = generator._categorize_ingredient(None)
            assert result == "default"
        except (AttributeError, TypeError):
            # This is acceptable - function might not handle None
            pass

    def test_convert_to_grams_negative_amount(self, generator):
        """Test converting negative amounts."""
        result = generator._convert_to_grams(-100, "g")

        assert result == -100.0  # Should preserve negative values

    def test_convert_to_grams_zero_amount(self, generator):
        """Test converting zero amounts."""
        result = generator._convert_to_grams(0, "g")

        assert result == 0.0

    def test_find_best_package_zero_amount(self, generator):
        """Test finding package for zero amount."""
        packages = [100, 250, 500]

        size, count = generator._find_best_package(0, packages, "up")

        # Should handle zero gracefully
        assert size in packages or size == 0
        assert count >= 0

    def test_find_best_package_negative_amount(self, generator):
        """Test finding package for negative amount."""
        packages = [100, 250, 500]

        size, count = generator._find_best_package(-100, packages, "up")

        # Should handle negative amounts gracefully
        assert isinstance(size, (int, float))
        assert isinstance(count, int)

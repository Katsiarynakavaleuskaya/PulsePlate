"""
Tests for core.shoplist module - shopping list generation

RU: Тесты для модуля генерации списков покупок.
EN: Tests for shopping list generation module.
"""

import csv
from pathlib import Path
import tempfile

import pytest

from core.shoplist import PackagingRule, ShoplistGenerator, ShoppingItem


class TestPackagingRuleDataClass:
    """Test PackagingRule dataclass."""

    def test_packaging_rule_creation(self):
        """Test PackagingRule creation."""
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

    def test_packaging_rule_defaults(self):
        """Test PackagingRule with different values."""
        rule = PackagingRule("spices", "ml", [10, 25, 50], "down")

        assert rule.category == "spices"
        assert rule.unit == "ml"
        assert rule.typical_packages == [10, 25, 50]
        assert rule.rounding_strategy == "down"


class TestShoppingItemDataClass:
    """Test ShoppingItem dataclass."""

    def test_shopping_item_minimal(self):
        """Test ShoppingItem with minimal required fields."""
        item = ShoppingItem(name="tomatoes", quantity=2.0, unit="kg", category="vegetables")

        assert item.name == "tomatoes"
        assert item.quantity == 2.0
        assert item.unit == "kg"
        assert item.category == "vegetables"
        assert item.package_size is None
        assert item.packages_needed is None
        assert item.total_weight is None

    def test_shopping_item_full(self):
        """Test ShoppingItem with all fields."""
        item = ShoppingItem(
            name="chicken breast",
            quantity=1.5,
            unit="kg",
            category="meat",
            package_size=500.0,
            packages_needed=3,
            total_weight=1500.0,
        )

        assert item.name == "chicken breast"
        assert item.quantity == 1.5
        assert item.unit == "kg"
        assert item.category == "meat"
        assert item.package_size == 500.0
        assert item.packages_needed == 3
        assert item.total_weight == 1500.0


class TestShoplistGeneratorBasics:
    """Test basic ShoplistGenerator functionality."""

    def test_generator_initialization_no_file(self):
        """Test generator initialization without packaging file."""
        generator = ShoplistGenerator("non_existent_file.csv")

        assert generator.packaging_rules_file == "non_existent_file.csv"
        assert len(generator.packaging_rules) > 0
        assert "vegetables" in generator.packaging_rules
        assert "default" in generator.packaging_rules

    def test_generator_initialization_with_file(self):
        """Test generator initialization with packaging file."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(["category", "unit", "typical_packages", "rounding_strategy"])
            writer.writerow(["test_category", "g", "50, 100, 200", "up"])
            temp_file = f.name

        try:
            generator = ShoplistGenerator(temp_file)

            assert temp_file in generator.packaging_rules_file
            assert "test_category" in generator.packaging_rules

            rule = generator.packaging_rules["test_category"]
            assert rule.category == "test_category"
            assert rule.unit == "g"
            assert rule.typical_packages == [50.0, 100.0, 200.0]
            assert rule.rounding_strategy == "up"
        finally:
            Path(temp_file).unlink()

    def test_generator_default_rules(self):
        """Test generator default packaging rules."""
        generator = ShoplistGenerator()

        # Check some default rules exist
        assert "vegetables" in generator.packaging_rules
        assert "meat" in generator.packaging_rules
        assert "dairy" in generator.packaging_rules
        assert "grains" in generator.packaging_rules
        assert "default" in generator.packaging_rules

        # Check rule structure
        vegetables_rule = generator.packaging_rules["vegetables"]
        assert vegetables_rule.category == "vegetables"
        assert vegetables_rule.unit == "g"
        assert vegetables_rule.rounding_strategy == "up"
        assert len(vegetables_rule.typical_packages) > 0


class TestShoplistGeneratorConversions:
    """Test unit conversion functionality."""

    @pytest.fixture
    def generator(self):
        """Create a ShoplistGenerator."""
        return ShoplistGenerator()

    def test_convert_to_grams_basic_units(self, generator):
        """Test basic unit conversions to grams."""
        assert generator._convert_to_grams(100, "g") == 100.0
        assert generator._convert_to_grams(1, "kg") == 1000.0
        assert generator._convert_to_grams(500, "ml") == 500.0  # Water density
        assert generator._convert_to_grams(1, "l") == 1000.0

    def test_convert_to_grams_special_units(self, generator):
        """Test special unit conversions."""
        assert generator._convert_to_grams(1, "pcs") == 100.0  # Average piece weight
        assert generator._convert_to_grams(1, "tbsp") == 15.0  # Tablespoon
        assert generator._convert_to_grams(1, "tsp") == 5.0  # Teaspoon
        assert generator._convert_to_grams(1, "cup") == 250.0  # Cup

    def test_convert_to_grams_case_insensitive(self, generator):
        """Test case insensitive unit conversion."""
        assert generator._convert_to_grams(100, "G") == 100.0
        assert generator._convert_to_grams(1, "KG") == 1000.0
        assert generator._convert_to_grams(500, "ML") == 500.0

    def test_convert_to_grams_unknown_unit(self, generator):
        """Test conversion with unknown unit."""
        assert generator._convert_to_grams(100, "unknown") == 100.0  # Default factor 1.0


class TestShoplistGeneratorAggregation:
    """Test ingredient aggregation functionality."""

    @pytest.fixture
    def generator(self):
        """Create a ShoplistGenerator."""
        return ShoplistGenerator()

    def test_aggregate_ingredients_simple_plan(self, generator):
        """Test aggregating ingredients from simple plan."""
        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 300, "unit": "g"},
                                {"name": "rice", "amount": 150, "unit": "g"},
                            ]
                        }
                    ]
                }
            ]
        }

        aggregated = generator.aggregate_ingredients(week_plan)

        assert aggregated["chicken"] == 300.0
        assert aggregated["rice"] == 150.0

    def test_aggregate_ingredients_multiple_days(self, generator):
        """Test aggregating ingredients from multiple days."""
        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 300, "unit": "g"},
                                {"name": "rice", "amount": 150, "unit": "g"},
                            ]
                        }
                    ]
                },
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 200, "unit": "g"},  # Same ingredient
                                {"name": "vegetables", "amount": 400, "unit": "g"},
                            ]
                        }
                    ]
                },
            ]
        }

        aggregated = generator.aggregate_ingredients(week_plan)

        assert aggregated["chicken"] == 500.0  # 300 + 200
        assert aggregated["rice"] == 150.0
        assert aggregated["vegetables"] == 400.0

    def test_aggregate_ingredients_direct_format(self, generator):
        """Test aggregating ingredients from direct format."""
        week_plan = {
            "ingredients": [
                {"name": "tomatoes", "amount": 500, "unit": "g"},
                {"name": "onions", "amount": 200, "unit": "g"},
            ]
        }

        aggregated = generator.aggregate_ingredients(week_plan)

        assert aggregated["tomatoes"] == 500.0
        assert aggregated["onions"] == 200.0

    def test_aggregate_ingredients_unit_conversion(self, generator):
        """Test aggregating ingredients with unit conversion."""
        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "milk", "amount": 1, "unit": "l"},  # 1000g
                                {"name": "milk", "amount": 500, "unit": "ml"},  # 500g
                            ]
                        }
                    ]
                }
            ]
        }

        aggregated = generator.aggregate_ingredients(week_plan)

        assert aggregated["milk"] == 1500.0  # 1000 + 500

    def test_aggregate_ingredients_empty_plan(self, generator):
        """Test aggregating ingredients from empty plan."""
        week_plan = {"days": []}

        aggregated = generator.aggregate_ingredients(week_plan)

        assert aggregated == {}


class TestShoplistGeneratorCategorization:
    """Test ingredient categorization."""

    @pytest.fixture
    def generator(self):
        """Create a ShoplistGenerator."""
        return ShoplistGenerator()

    def test_categorize_meat_ingredients(self, generator):
        """Test categorizing meat ingredients."""
        assert generator._categorize_ingredient("chicken breast") == "meat"
        assert generator._categorize_ingredient("beef steak") == "meat"
        assert generator._categorize_ingredient("pork chops") == "meat"
        assert generator._categorize_ingredient("курица") == "meat"
        assert generator._categorize_ingredient("говядина") == "meat"

    def test_categorize_fish_ingredients(self, generator):
        """Test categorizing fish ingredients."""
        assert generator._categorize_ingredient("salmon fillet") == "fish"
        assert generator._categorize_ingredient("tuna") == "fish"
        assert generator._categorize_ingredient("рыба") == "fish"
        assert generator._categorize_ingredient("лосось") == "fish"

    def test_categorize_dairy_ingredients(self, generator):
        """Test categorizing dairy ingredients."""
        assert generator._categorize_ingredient("milk") == "dairy"
        assert generator._categorize_ingredient("cheese") == "dairy"
        assert generator._categorize_ingredient("yogurt") == "dairy"
        assert generator._categorize_ingredient("молоко") == "dairy"
        assert generator._categorize_ingredient("сыр") == "dairy"

    def test_categorize_vegetable_ingredients(self, generator):
        """Test categorizing vegetable ingredients."""
        assert generator._categorize_ingredient("tomatoes") == "vegetables"
        assert generator._categorize_ingredient("carrot") == "vegetables"
        assert generator._categorize_ingredient("помидор") == "vegetables"
        assert generator._categorize_ingredient("морковь") == "vegetables"

    def test_categorize_fruit_ingredients(self, generator):
        """Test categorizing fruit ingredients."""
        assert generator._categorize_ingredient("apple") == "fruits"
        assert generator._categorize_ingredient("banana") == "fruits"
        assert generator._categorize_ingredient("яблоко") == "fruits"
        assert generator._categorize_ingredient("банан") == "fruits"

    def test_categorize_grain_ingredients(self, generator):
        """Test categorizing grain ingredients."""
        assert generator._categorize_ingredient("rice") == "grains"
        assert generator._categorize_ingredient("oats") == "grains"
        assert generator._categorize_ingredient("рис") == "grains"
        assert generator._categorize_ingredient("овес") == "grains"

    def test_categorize_nuts_ingredients(self, generator):
        """Test categorizing nuts ingredients."""
        assert generator._categorize_ingredient("almonds") == "nuts"
        assert generator._categorize_ingredient("орех грецкий") == "nuts"

    def test_categorize_oils_ingredients(self, generator):
        """Test categorizing oil ingredients."""
        assert generator._categorize_ingredient("olive oil") == "oils"
        assert generator._categorize_ingredient("оливковое масло") == "oils"

    def test_categorize_spices_ingredients(self, generator):
        """Test categorizing spice ingredients."""
        assert generator._categorize_ingredient("salt") == "spices"
        assert generator._categorize_ingredient("pepper") == "spices"
        assert generator._categorize_ingredient("соль") == "spices"

    def test_categorize_unknown_ingredients(self, generator):
        """Test categorizing unknown ingredients."""
        assert generator._categorize_ingredient("unknown ingredient") == "default"
        assert generator._categorize_ingredient("странный продукт") == "default"


class TestShoplistGeneratorPackaging:
    """Test package finding functionality."""

    @pytest.fixture
    def generator(self):
        """Create a ShoplistGenerator."""
        return ShoplistGenerator()

    def test_find_best_package_up_strategy(self, generator):
        """Test finding best package with 'up' strategy."""
        packages = [100, 250, 500, 1000]

        # Test exact match
        size, count = generator._find_best_package(250, packages, "up")
        assert size == 100  # Takes smallest package
        assert count == 3  # 3 packages of 100 to cover 250

        # Test larger amount
        size, count = generator._find_best_package(350, packages, "up")
        assert size == 100
        assert count == 4  # 4 packages of 100 to cover 350

    def test_find_best_package_down_strategy(self, generator):
        """Test finding best package with 'down' strategy."""
        packages = [100, 250, 500, 1000]

        # Test amount that fits exactly
        size, count = generator._find_best_package(250, packages, "down")
        assert size == 250
        assert count == 1

        # Test larger amount
        size, count = generator._find_best_package(350, packages, "down")
        assert size == 250
        assert count == 1  # 1 package of 250 (rounds down)

    def test_find_best_package_nearest_strategy(self, generator):
        """Test finding best package with 'nearest' strategy."""
        packages = [100, 250, 500, 1000]

        # Test amount close to package size
        size, count = generator._find_best_package(240, packages, "nearest")
        assert size in packages
        assert count >= 1

        # Test very small amount
        size, count = generator._find_best_package(50, packages, "nearest")
        assert count >= 1

    def test_find_best_package_empty_packages(self, generator):
        """Test finding best package with empty package list."""
        size, count = generator._find_best_package(100, [], "up")
        assert size == 100  # Returns the amount itself
        assert count == 1

    def test_find_best_package_fallback(self, generator):
        """Test finding best package fallback behavior."""
        packages = [1000, 2000]  # Large packages only

        # Very small amount should still work
        size, count = generator._find_best_package(50, packages, "unknown_strategy")
        assert size == 1000  # Fallback to first package
        assert count == 1

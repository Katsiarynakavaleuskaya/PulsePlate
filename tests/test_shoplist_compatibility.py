"""
Tests for shoplist compatibility functions

RU: Тесты для функций совместимости списка покупок
EN: Tests for shoplist compatibility functions
"""

import pytest
from unittest.mock import Mock, patch

from core.shoplist import get_shoplist, ShoplistGenerator, PackagingRule, ShoppingItem


class TestShoplistCompatibility:
    """Test shoplist compatibility functions."""

    @patch("core.shoplist.ShoplistGenerator")
    def test_get_shoplist_basic(self, mock_generator_class) -> None:
        """Test basic get_shoplist function."""
        # Setup mock
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        # Mock the methods
        mock_generator.aggregate_ingredients.return_value = {"ingredient1": 100.0}
        mock_generator.round_to_packages.return_value = [{"name": "ingredient1", "amount": 1}]
        mock_generator.format_export.return_value = "formatted_list"

        # Test data
        week_plan = {"recipes": []}

        # Call function
        result = get_shoplist(week_plan)

        # Assertions
        assert result == "formatted_list"
        mock_generator.aggregate_ingredients.assert_called_once_with(week_plan)
        mock_generator.round_to_packages.assert_called_once()
        mock_generator.format_export.assert_called_once()

    @patch("core.shoplist.ShoplistGenerator")
    def test_get_shoplist_with_options(self, mock_generator_class) -> None:
        """Test get_shoplist with all optional parameters."""
        # Setup mock
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        # Mock the methods
        mock_generator.aggregate_ingredients.return_value = {"ingredient1": 100.0}
        mock_generator.round_to_packages.return_value = [{"name": "ingredient1", "amount": 1}]
        mock_generator.format_export.return_value = "formatted_list"

        # Test data
        week_plan = {"recipes": []}
        format_type = "json"
        locale = "en"
        packaging_db = {"ingredient1": {"package_size": 100}}
        rules = {"round_up": True}

        # Call function
        result = get_shoplist(week_plan, format_type, locale, packaging_db, rules)

        # Assertions
        assert result == "formatted_list"
        mock_generator.aggregate_ingredients.assert_called_once_with(week_plan)
        mock_generator.round_to_packages.assert_called_once_with(
            {"ingredient1": 100.0}, packaging_db, rules
        )
        mock_generator.format_export.assert_called_once_with(
            [{"name": "ingredient1", "amount": 1}], locale=locale, format_type=format_type
        )


class TestShoplistGenerator:
    """Test ShoplistGenerator class methods."""

    def test_packaging_rule_creation(self) -> None:
        """Test PackagingRule dataclass creation."""
        rule = PackagingRule(
            category="vegetables",
            unit="g",
            typical_packages=[100, 250, 500],
            rounding_strategy="up",
        )
        assert rule.category == "vegetables"
        assert rule.unit == "g"
        assert rule.typical_packages == [100, 250, 500]
        assert rule.rounding_strategy == "up"

    def test_shopping_item_creation(self) -> None:
        """Test ShoppingItem dataclass creation."""
        item = ShoppingItem(
            name="tomatoes",
            quantity=500.0,
            unit="g",
            category="vegetables",
            package_size=250.0,
            packages_needed=2,
            total_weight=500.0,
        )
        assert item.name == "tomatoes"
        assert item.quantity == 500.0
        assert item.unit == "g"
        assert item.category == "vegetables"
        assert item.package_size == 250.0
        assert item.packages_needed == 2
        assert item.total_weight == 500.0

    @patch("core.shoplist.Path.exists")
    def test_shoplist_generator_init_with_file(self, mock_exists) -> None:
        """Test ShoplistGenerator initialization with packaging rules file."""
        mock_exists.return_value = True

        with patch(
            "builtins.open",
            mock_open(
                read_data='category,unit,typical_packages,rounding_strategy\nvegetables,g,"100,250,500",up'
            ),
        ):
            generator = ShoplistGenerator("test_rules.csv")
            assert generator.packaging_rules_file == "test_rules.csv"
            assert isinstance(generator.packaging_rules, dict)

    @patch("core.shoplist.Path.exists")
    def test_shoplist_generator_init_without_file(self, mock_exists) -> None:
        """Test ShoplistGenerator initialization without packaging rules file."""
        mock_exists.return_value = False

        generator = ShoplistGenerator("nonexistent.csv")
        assert generator.packaging_rules_file == "nonexistent.csv"
        assert isinstance(generator.packaging_rules, dict)
        # Should have default rules
        assert len(generator.packaging_rules) > 0

    def test_aggregate_ingredients_empty_plan(self) -> None:
        """Test aggregate_ingredients with empty week plan."""
        generator = ShoplistGenerator()
        week_plan = {"recipes": []}

        result = generator.aggregate_ingredients(week_plan)
        assert result == {}

    def test_aggregate_ingredients_with_recipes(self) -> None:
        """Test aggregate_ingredients with recipes containing ingredients."""
        generator = ShoplistGenerator()
        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "tomatoes", "amount": 200, "unit": "g"},
                                {"name": "onions", "amount": 100, "unit": "g"},
                            ]
                        }
                    ]
                },
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "tomatoes", "amount": 300, "unit": "g"},
                                {"name": "garlic", "amount": 50, "unit": "g"},
                            ]
                        }
                    ]
                },
            ]
        }

        result = generator.aggregate_ingredients(week_plan)
        assert "tomatoes" in result
        assert result["tomatoes"] == 500.0  # 200 + 300
        assert result["onions"] == 100.0
        assert result["garlic"] == 50.0

    def test_round_to_packages_basic(self) -> None:
        """Test round_to_packages with basic functionality."""
        generator = ShoplistGenerator()
        aggregated = {"tomatoes": 500.0, "onions": 150.0}

        result = generator.round_to_packages(aggregated)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_format_export_json(self) -> None:
        """Test format_export with JSON format."""
        generator = ShoplistGenerator()
        shopping_items = [
            ShoppingItem(name="tomatoes", quantity=2, unit="packages", category="vegetables")
        ]

        result = generator.format_export(shopping_items, format_type="json")
        assert isinstance(result, (str, dict))

    def test_format_export_csv(self) -> None:
        """Test format_export with CSV format."""
        generator = ShoplistGenerator()
        shopping_items = [
            ShoppingItem(name="tomatoes", quantity=2, unit="packages", category="vegetables")
        ]

        result = generator.format_export(shopping_items, format_type="csv")
        assert isinstance(result, str)

    def test_format_export_text(self) -> None:
        """Test format_export with text format."""
        generator = ShoplistGenerator()
        shopping_items = [
            ShoppingItem(name="tomatoes", quantity=2, unit="packages", category="vegetables")
        ]

        result = generator.format_export(shopping_items, format_type="text")
        assert isinstance(result, str)

    def test_format_export_with_locale(self) -> None:
        """Test format_export with different locales."""
        generator = ShoplistGenerator()
        shopping_items = [
            ShoppingItem(name="tomatoes", quantity=2, unit="packages", category="vegetables")
        ]

        # Test different locales
        for locale in ["ru", "en", "es"]:
            result = generator.format_export(shopping_items, locale=locale)
            assert isinstance(result, (str, dict))


def mock_open(read_data: str):
    """Helper function to mock file opening."""
    from unittest.mock import mock_open as _mock_open

    return _mock_open(read_data=read_data)

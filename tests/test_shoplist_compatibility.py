"""
Tests for shoplist compatibility functions

RU: Тесты для функций совместимости списка покупок
EN: Tests for shoplist compatibility functions
"""

import pytest
from unittest.mock import Mock, patch

from core.shoplist import get_shoplist


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

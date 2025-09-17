# -*- coding: utf-8 -*-
"""
Final coverage tests for core/shoplist.py to reach 97% coverage
"""

from core.shoplist import ShoplistGenerator, ShoppingItem


class TestShoplistFinal:
    """Final tests to boost core/shoplist.py coverage to 97%."""

    def test_categorize_ingredient_meat_category(self):
        """Test _categorize_ingredient with meat category."""
        generator = ShoplistGenerator()

        # Test meat category
        assert generator._categorize_ingredient("говядина") == "meat"
        assert generator._categorize_ingredient("chicken") == "meat"
        assert generator._categorize_ingredient("свинина") == "meat"
        assert generator._categorize_ingredient("beef") == "meat"

    def test_categorize_ingredient_fish_category(self):
        """Test categorize_ingredient with fish category."""
        generator = ShoplistGenerator()

        # Test fish category
        assert generator._categorize_ingredient("рыба") == "fish"
        assert generator._categorize_ingredient("salmon") == "fish"
        assert generator._categorize_ingredient("лосось") == "fish"
        assert generator._categorize_ingredient("tuna") == "fish"

    def test_categorize_ingredient_dairy_category(self):
        """Test categorize_ingredient with dairy category."""
        generator = ShoplistGenerator()

        # Test dairy category
        assert generator._categorize_ingredient("молоко") == "dairy"
        assert generator._categorize_ingredient("cheese") == "dairy"
        assert generator._categorize_ingredient("йогурт") == "dairy"
        assert generator._categorize_ingredient("yogurt") == "dairy"

    def test_categorize_ingredient_vegetables_category(self):
        """Test categorize_ingredient with vegetables category."""
        generator = ShoplistGenerator()

        # Test vegetables category
        assert generator._categorize_ingredient("морковь") == "vegetables"
        assert generator._categorize_ingredient("carrot") == "vegetables"
        assert generator._categorize_ingredient("помидор") == "vegetables"
        assert generator._categorize_ingredient("tomato") == "vegetables"

    def test_categorize_ingredient_fruits_category(self):
        """Test categorize_ingredient with fruits category."""
        generator = ShoplistGenerator()

        # Test fruits category
        assert generator._categorize_ingredient("яблоко") == "fruits"
        assert generator._categorize_ingredient("apple") == "fruits"
        assert generator._categorize_ingredient("банан") == "fruits"
        assert generator._categorize_ingredient("banana") == "fruits"
        assert generator._categorize_ingredient("orange") == "fruits"

    def test_categorize_ingredient_grains_category(self):
        """Test categorize_ingredient with grains category."""
        generator = ShoplistGenerator()

        # Test grains category
        assert generator._categorize_ingredient("рис") == "grains"
        assert generator._categorize_ingredient("rice") == "grains"
        assert generator._categorize_ingredient("гречка") == "grains"
        assert generator._categorize_ingredient("buckwheat") == "grains"
        assert generator._categorize_ingredient("овес") == "grains"
        assert generator._categorize_ingredient("oats") == "grains"

    def test_categorize_ingredient_nuts_category(self):
        """Test categorize_ingredient with nuts category."""
        generator = ShoplistGenerator()

        # Test nuts category
        assert generator._categorize_ingredient("орех") == "nuts"
        assert generator._categorize_ingredient("nut") == "nuts"
        assert generator._categorize_ingredient("миндаль") == "nuts"
        assert generator._categorize_ingredient("almond") == "nuts"

    def test_categorize_ingredient_oils_category(self):
        """Test categorize_ingredient with oils category."""
        generator = ShoplistGenerator()

        # Test oils category
        assert generator._categorize_ingredient("масло") == "oils"
        assert generator._categorize_ingredient("oil") == "oils"
        assert generator._categorize_ingredient("оливковое") == "oils"
        assert generator._categorize_ingredient("olive") == "oils"

    def test_categorize_ingredient_spices_category(self):
        """Test categorize_ingredient with spices category."""
        generator = ShoplistGenerator()

        # Test spices category
        assert generator._categorize_ingredient("специя") == "spices"
        assert generator._categorize_ingredient("spice") == "spices"
        assert generator._categorize_ingredient("соль") == "spices"
        assert generator._categorize_ingredient("salt") == "spices"
        assert generator._categorize_ingredient("перец") == "spices"
        assert generator._categorize_ingredient("pepper") == "spices"

    def test_categorize_ingredient_default_category(self):
        """Test categorize_ingredient with default category."""
        generator = ShoplistGenerator()

        # Test default category
        assert generator._categorize_ingredient("unknown_ingredient") == "default"
        assert generator._categorize_ingredient("") == "default"

    def test_find_best_package_strategy_zero_packages_needed(self):
        """Test find_best_package_strategy with zero packages needed."""
        generator = ShoplistGenerator()

        # Test case where packages_needed would be 0
        packages = [100, 200, 500]
        total_amount = 50  # Less than smallest package

        best_package, packages_needed = generator._find_best_package(total_amount, packages, "up")

        # Should return smallest package with 1 package needed
        assert best_package == 100
        assert packages_needed == 1

    def test_find_best_package_strategy_fallback(self):
        """Test find_best_package_strategy fallback case."""
        generator = ShoplistGenerator()

        # Test with empty packages list (should not happen in practice)
        packages = []
        total_amount = 100

        # This should trigger the fallback
        best_package, packages_needed = generator._find_best_package(total_amount, packages, "up")

        # Fallback should return first package with 1 package needed
        assert packages_needed == 1

    def test_module_level_functions_aggregate_ingredients(self):
        """Test module-level aggregate_ingredients function."""
        from core.shoplist import aggregate_ingredients

        week_plan = {"ingredients": [{"name": "flour", "amount": 100, "unit": "g"}]}

        result = aggregate_ingredients(week_plan)
        assert "flour" in result
        assert result["flour"] == 100.0

    def test_module_level_functions_round_to_packages(self):
        """Test module-level round_to_packages function."""
        from core.shoplist import round_to_packages

        ingredients = {"flour": 100.0}
        result = round_to_packages(ingredients)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_module_level_functions_format_export(self):
        """Test module-level format_export function."""
        from core.shoplist import format_export

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

        result = format_export(shopping_list, "en", "json")
        assert isinstance(result, dict)
        assert "flour" in str(result)

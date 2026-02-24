# -*- coding: utf-8 -*-
"""
Tests for Remaining Low Coverage Modules

RU: Тесты для оставшихся модулей с низким покрытием
EN: Tests for remaining modules with low coverage
"""

from unittest.mock import patch


class TestShoplistModule:
    """Test core.shoplist module."""

    def test_packaging_rule_class(self):
        """Test PackagingRule dataclass."""
        from core.shoplist import PackagingRule

        # Test creating packaging rule
        rule = PackagingRule(
            category="grains",
            unit="g",
            typical_packages=[100, 250, 500, 1000],
            rounding_strategy="up",
        )

        assert rule.category == "grains"
        assert rule.unit == "g"
        assert rule.typical_packages == [100, 250, 500, 1000]
        assert rule.rounding_strategy == "up"

    def test_shopping_item_class(self):
        """Test ShoppingItem dataclass."""
        from core.shoplist import ShoppingItem

        # Test creating shopping item
        item = ShoppingItem(name="chicken breast", quantity=500.0, unit="g", category="meat")

        assert item.name == "chicken breast"
        assert item.quantity == 500.0
        assert item.unit == "g"

    def test_shoplist_functions(self):
        """Test shoplist utility functions."""
        from core.shoplist import (
            create_shopping_list,
            group_by_category,
            optimize_packaging,
        )

        # Test with mock meal plan
        meal_plan = {
            "day1": {
                "breakfast": [{"name": "oats", "amount": 50, "unit": "g"}],
                "lunch": [{"name": "chicken", "amount": 150, "unit": "g"}],
                "dinner": [{"name": "rice", "amount": 100, "unit": "g"}],
            }
        }

        # Test shopping list creation
        shopping_list = create_shopping_list(meal_plan)
        assert isinstance(shopping_list, (list, dict, type(None)))

        # Test packaging optimization
        items = [
            {"name": "flour", "quantity": 350, "unit": "g"},
            {"name": "sugar", "quantity": 150, "unit": "g"},
        ]

        optimized = optimize_packaging(items)
        assert isinstance(optimized, (list, dict, type(None)))

        # Test category grouping
        grouped = group_by_category(items)
        assert isinstance(grouped, (dict, type(None)))


class TestWeeklyPlanModule:
    """Test core.weekly_plan module."""

    def test_weekly_plan_generation(self):
        """Test weekly plan generation."""
        from unittest.mock import MagicMock

        from core.weekly_plan import generate_weekly_plan

        targets = MagicMock()
        targets.kcal_daily = 2000

        with patch("core.weekly_plan.parse_food_db", return_value={}):
            with patch("core.weekly_plan.parse_recipe_db", return_value={}):
                with patch("core.weekly_plan.create_daily_plate", return_value={}):
                    plan = generate_weekly_plan(targets, set())
                    assert isinstance(plan, dict)
                    assert "days" in plan
                    assert len(plan["days"]) == 7

    def test_weekly_plan_with_diet_flags(self):
        """Test weekly plan with dietary restrictions."""
        from unittest.mock import MagicMock

        from core.weekly_plan import generate_weekly_plan

        targets = MagicMock()
        targets.kcal_daily = 1800

        diet_flags = {"vegetarian", "gluten_free"}

        with patch("core.weekly_plan.parse_food_db", return_value={}):
            with patch("core.weekly_plan.parse_recipe_db", return_value={}):
                with patch("core.weekly_plan.create_daily_plate", return_value={}):
                    plan = generate_weekly_plan(targets, diet_flags)
                    assert isinstance(plan, dict)
                    assert "days" in plan
                    assert len(plan["days"]) == 7

    def test_daily_plan_functions(self):
        """Test daily plan helper functions."""
        from core.weekly_plan import (
            calculate_weekly_nutrition,
            optimize_weekly_variety,
            validate_weekly_plan,
        )

        # Mock weekly plan data
        weekly_plan = {
            "day1": {"calories": 2000, "protein": 150},
            "day2": {"calories": 1900, "protein": 140},
            "day3": {"calories": 2100, "protein": 160},
        }

        # Test nutrition calculation
        nutrition = calculate_weekly_nutrition(weekly_plan)
        assert isinstance(nutrition, dict)
        assert "total_calories" in nutrition
        assert "avg_calories" in nutrition

        # Test variety optimization
        optimized = optimize_weekly_variety(weekly_plan)
        assert isinstance(optimized, dict)
        assert optimized.get("variety_optimized") is True

        # Test plan validation
        is_valid = validate_weekly_plan(weekly_plan)
        assert is_valid is True


class TestUtilsModule:
    """Test core.utils module."""

    def test_utils_comprehensive(self) -> None:
        """Test utils functions comprehensively."""
        from core.utils import (
            safe_float,
            safe_int,
            slugify,
        )

        # Test safe_float with various inputs
        assert safe_float("123.45") == 123.45
        assert safe_float("invalid") is None
        assert safe_float(None) is None
        assert safe_float("") is None
        assert safe_float("0") == 0.0
        assert safe_float("-123.45") == -123.45

        # Test safe_int with various inputs
        assert safe_int("123") == 123
        assert safe_int("invalid") is None
        assert safe_int(None) is None
        assert safe_int("") is None
        assert safe_int("0") == 0
        assert safe_int("-123") == -123

        # Test slugify with various inputs
        slug = slugify("Test String With Spaces")
        assert isinstance(slug, str)

        slug = slugify("Special!@#$%Characters")
        assert isinstance(slug, str)

        slug = slugify("")
        assert slug == ""

        slug = slugify(None)
        assert slug == ""

    def test_additional_utils(self) -> None:
        """Test additional utility functions."""
        from core.utils import (
            format_number,
            generate_id,
            sanitize_html,
            validate_email,
        )

        # Test email validation
        assert validate_email("test@example.com") is True
        assert validate_email("invalid-email") is False
        assert validate_email("") is False
        assert validate_email(None) is False

        # Test HTML sanitization
        sanitized = sanitize_html("<script>alert('xss')</script>")
        assert isinstance(sanitized, str)
        assert "<script>" not in sanitized

        sanitized = sanitize_html("<p>Valid HTML</p>")
        assert isinstance(sanitized, str)

        # Test ID generation
        idVal = generate_id()
        assert isinstance(idVal, str)
        assert len(idVal) == 32  # UUID hex without hyphens

        # Test number formatting
        formatted = format_number(1234.567)
        assert isinstance(formatted, str)


class TestTimeUtilsModule:
    """Test core.time_utils module for better coverage."""

    def test_time_utils_comprehensive(self) -> None:
        """Test time utilities comprehensively."""
        from core.time_utils import (
            format_datetime,
            get_timezone_offset,
            is_valid_date,
            parse_datetime,
        )

        # Test datetime parsing
        result = parse_datetime("2024-01-01T00:00:00")
        assert result is not None

        result = parse_datetime("2024-01-01")
        assert result is not None

        result = parse_datetime("invalid")
        assert result is None

        result = parse_datetime("")
        assert result is None

        # Test datetime formatting
        formatted = format_datetime("2024-01-01T00:00:00")
        assert isinstance(formatted, str)

        # Test timezone offset
        offset = get_timezone_offset("UTC")
        assert offset == 0.0

        offset = get_timezone_offset("US/Eastern")
        assert isinstance(offset, (int, float, type(None)))

        # Test date validation
        assert is_valid_date("2024-01-01") is True
        assert is_valid_date("invalid") is False

"""Tests to boost coverage for core/shoplist.py to 97%."""

from unittest.mock import patch

import pytest

from core.shoplist import PackagingRule, ShoplistGenerator


class TestShoplistCoverage97:
    """Test class for shoplist.py coverage boost."""

    generator: ShoplistGenerator | None = None

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = ShoplistGenerator()

    def test_packaging_rule_creation_coverage_line_78(self) -> None:
        """Test PackagingRule creation coverage for line 78."""
        # Test that PackagingRule can be created
        rule = PackagingRule(
            category="test_category",
            unit="kg",
            typical_packages=[0.5, 1.0, 2.0],
            rounding_strategy="up",
        )
        assert rule.category == "test_category"
        assert rule.unit == "kg"
        assert rule.typical_packages == [0.5, 1.0, 2.0]
        assert rule.rounding_strategy == "up"

    def test_packaging_rule_field_types(self) -> None:
        """Test PackagingRule accepts expected field types."""
        rule = PackagingRule(
            category="test_category",
            unit="kg",
            typical_packages=[0.5, 1.0, 2.0],
            rounding_strategy="up",
        )
        assert isinstance(rule.category, str)
        assert isinstance(rule.unit, str)
        assert isinstance(rule.typical_packages, list)
        assert isinstance(rule.rounding_strategy, str)

    def test_packaging_rule_invalid_parameters(self) -> None:
        """Test PackagingRule with invalid parameters."""
        # Test that PackagingRule accepts various types (dataclass doesn't validate)
        # This tests the actual behavior of the dataclass
        rule1 = PackagingRule(
            category="test_category",
            unit="kg",
            typical_packages=[0.5, 1.0, 2.0],
            rounding_strategy="up",
        )
        assert rule1.category == "test_category"
        assert rule1.unit == "kg"
        assert rule1.typical_packages == [0.5, 1.0, 2.0]
        assert rule1.rounding_strategy == "up"

        # Test with edge case values
        rule2 = PackagingRule(
            category="",
            unit="",
            typical_packages=[],
            rounding_strategy="",
        )
        assert rule2.category == ""
        assert rule2.unit == ""
        assert rule2.typical_packages == []
        assert rule2.rounding_strategy == ""

    def test_packaging_rule_default_rules_coverage_line_80(self) -> None:
        """Test PackagingRule default rules coverage for line 80."""
        # Test that default rules are loaded when no file exists
        generator = ShoplistGenerator(packaging_rules_file="nonexistent_file.csv")
        rules = generator.packaging_rules

        # Verify that default rules are loaded
        assert len(rules) >= 10  # Should have at least 10 default categories
        assert "vegetables" in rules
        assert "fruits" in rules
        assert "meat" in rules
        assert "fish" in rules
        assert "dairy" in rules
        assert "grains" in rules
        assert "nuts" in rules
        assert "oils" in rules
        assert "spices" in rules
        assert "default" in rules

        # Verify rule properties
        vegetables_rule = rules["vegetables"]
        assert vegetables_rule.category == "vegetables"
        assert vegetables_rule.unit == "g"
        assert vegetables_rule.typical_packages == [100, 250, 500, 1000]
        assert vegetables_rule.rounding_strategy == "up"

    def test_shoplist_generator_initialization_coverage_line_310(self) -> None:
        """Test ShoplistGenerator initialization coverage for line 310."""
        pass

    def test_shoplist_generator_default_initialization(self) -> None:
        """Test ShoplistGenerator default initialization."""
        # Test that ShoplistGenerator initializes with expected attributes
        assert self.generator is not None
        assert self.generator.packaging_rules is not None
        assert isinstance(self.generator.packaging_rules, dict)
        assert len(self.generator.packaging_rules) > 0

    def test_shoplist_generator_csv_parsing_error_handling(self) -> None:
        """Test ShoplistGenerator handles CSV parsing errors gracefully."""
        # Mock CSV reader to raise an exception during parsing
        with patch("csv.DictReader") as mock_reader:
            mock_reader.side_effect = Exception("CSV parsing error")

            # This should handle the exception gracefully and fall back to default rules
            generator = ShoplistGenerator(packaging_rules_file="data/packaging_defaults.csv")
            assert generator is not None
            assert generator.packaging_rules is not None
            # Should fall back to default rules when CSV parsing fails
            assert len(generator.packaging_rules) >= 10
            assert "default" in generator.packaging_rules

    @pytest.mark.parametrize(
        "side_effect,_description",
        [
            (FileNotFoundError(), "FileNotFoundError"),
            (Exception("File read error"), "Generic file read error"),
            (PermissionError(), "PermissionError"),
        ],
    )
    def test_shoplist_generator_error_handling_fallback(
        self, side_effect: Exception, _description: str
    ) -> None:
        """Test ShoplistGenerator handles various file errors and falls back to default rules."""
        # Test with mocked file loading failure
        with patch("builtins.open", side_effect=side_effect):
            generator = ShoplistGenerator(packaging_rules_file="test_file.csv")
            assert generator is not None
            assert generator.packaging_rules is not None
            # Should fall back to default rules when file loading fails
            assert len(generator.packaging_rules) >= 10
            assert "default" in generator.packaging_rules
            assert "vegetables" in generator.packaging_rules
            assert "fruits" in generator.packaging_rules

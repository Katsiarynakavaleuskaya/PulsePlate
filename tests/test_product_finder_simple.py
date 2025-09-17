# -*- coding: utf-8 -*-
"""
Simplified tests for core.product_finder module.
Covers main functionality for coverage improvement.
"""

import pytest
from pathlib import Path
from typing import Literal
from unittest.mock import Mock, patch, mock_open

from core.product_finder import ProductSearchResult, ProductFinder
from core.food_db import FoodItem
from core.food_sources.base import FoodRecord


def create_mock_food_record(name, protein_g=0, fat_g=0, carbs_g=0):
    """Helper to create FoodRecord with minimal required fields."""
    return FoodRecord(
        name=name,
        locale="en",
        per_g=100.0,
        kcal=100.0,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        fiber_g=0,
        Fe_mg=0,
        Ca_mg=0,
        VitD_IU=0,
        B12_ug=0,
        Folate_ug=0,
        Iodine_ug=0,
        K_mg=0,
        Mg_mg=0,
        flags=[],
        price=1.0,
        source="TEST",
        version_date="2025-01-01",
    )


class TestProductSearchResult:
    """Tests for ProductSearchResult dataclass."""

    def test_create_successful_result(self):
        """Test creating a successful search result."""
        food_record = create_mock_food_record("Test Food", protein_g=10.0)

        result = ProductSearchResult(
            product_name="Test Product",
            found=True,
            source="USDA",
            food_record=food_record,
            confidence=0.85,
        )

        assert result.product_name == "Test Product"
        assert result.found is True
        assert result.source == "USDA"
        assert result.confidence == 0.85

    def test_create_failed_result(self):
        """Test creating a failed search result."""
        result = ProductSearchResult(
            product_name="Unknown Product", found=False, error_message="Product not found"
        )

        assert result.found is False
        assert result.error_message == "Product not found"


class TestProductFinder:
    """Tests for ProductFinder class."""

    @patch("core.product_finder.parse_food_db")
    @patch("core.product_finder.USDAAdapter")
    @patch("core.product_finder.OFFAdapter")
    def test_init(self, mock_off, mock_usda, mock_parse_db):
        """Test ProductFinder initialization."""
        mock_parse_db.return_value = {}

        finder = ProductFinder()

        assert finder.usda_adapter is not None
        assert finder.off_adapter is not None

    def test_find_missing_products_all_found(self):
        """Test finding missing products when all are present."""
        mock_food_db = {
            1: FoodItem(
                name="Apple",
                unit_per=100,
                unit="g",
                protein_g=0.3,
                fat_g=0.2,
                carbs_g=14,
                fiber_g=2.4,
                Fe_mg=0.12,
                Ca_mg=6,
                VitD_IU=0,
                B12_ug=0,
                Folate_ug=3,
                Iodine_ug=0,
                K_mg=107,
                Mg_mg=5,
                price_per_unit=0.5,
                flags=set(),
            ),
        }

        with patch("core.product_finder.parse_food_db", return_value=mock_food_db):
            finder = ProductFinder()

            ingredients = ["apple"]
            missing = finder.find_missing_products(ingredients)

            assert len(missing) == 0

    def test_find_missing_products_some_missing(self):
        """Test finding missing products when some are missing."""
        mock_food_db = {
            1: FoodItem(
                name="Apple",
                unit_per=100,
                unit="g",
                protein_g=0.3,
                fat_g=0.2,
                carbs_g=14,
                fiber_g=2.4,
                Fe_mg=0.12,
                Ca_mg=6,
                VitD_IU=0,
                B12_ug=0,
                Folate_ug=3,
                Iodine_ug=0,
                K_mg=107,
                Mg_mg=5,
                price_per_unit=0.5,
                flags=set(),
            ),
        }

        with patch("core.product_finder.parse_food_db", return_value=mock_food_db):
            finder = ProductFinder()

            ingredients = ["apple", "unknown ingredient"]
            missing = finder.find_missing_products(ingredients)

            assert len(missing) == 1
            assert "unknown ingredient" in missing

    @pytest.mark.parametrize(
        "name1,name2,expected",
        [
            ("apple", "apple", True),
            ("chicken breast", "breast", True),
            ("apple", "chicken", False),
        ],
    )
    def test_similar_names(
        self,
        name1: Literal["apple"] | Literal["chicken breast"],
        name2: Literal["apple"] | Literal["breast"] | Literal["chicken"],
        expected: bool,
    ):
        """Test similar names detection."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            result = finder._similar_names(name1, name2)
            assert result == expected

    def test_search_product_usda_success(self):
        """Test successful product search in USDA."""
        mock_food_record = create_mock_food_record("Test Apple", protein_g=0.3)

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            # Mock USDA search success
            with patch.object(finder, "_search_in_usda") as mock_usda_search:
                mock_usda_search.return_value = ProductSearchResult(
                    product_name="apple",
                    found=True,
                    source="USDA",
                    food_record=mock_food_record,
                    confidence=0.9,
                )

                result = finder.search_product("apple")

                assert result.found is True
                assert result.source == "USDA"

    def test_search_product_both_fail(self):
        """Test product search when both USDA and OFF fail."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            # Mock both searches failing
            with (
                patch.object(finder, "_search_in_usda") as mock_usda_search,
                patch.object(finder, "_search_in_off") as mock_off_search,
            ):

                mock_usda_search.return_value = ProductSearchResult(
                    product_name="unknown food", found=False
                )

                mock_off_search.return_value = ProductSearchResult(
                    product_name="unknown food", found=False
                )

                result = finder.search_product("unknown food")

                assert result.found is False
                assert result.error_message == "Product not found in any source"

    def test_search_product_usda_exception(self):
        """Test product search when USDA throws exception."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            # Test case 1: USDA throws exception, OFF succeeds
            with (
                patch.object(finder, "_search_in_usda") as mock_usda_search,
                patch.object(finder, "_search_in_off") as mock_off_search,
            ):

                mock_usda_search.side_effect = Exception("USDA API error")

                mock_off_search.return_value = ProductSearchResult(
                    product_name="test food", found=True, source="OFF", confidence=0.7
                )

                result = finder.search_product("test food")

                assert result.found is True
                assert result.source == "OFF"

            # Test case 2: Both USDA and OFF throw exceptions
            with (
                patch.object(finder, "_search_in_usda") as mock_usda_search,
                patch.object(finder, "_search_in_off") as mock_off_search,
            ):

                mock_usda_search.side_effect = Exception("USDA API error")
                mock_off_search.side_effect = Exception("OFF service unavailable")

                result = finder.search_product("test food")

                assert result.found is False
                assert result.product_name == "test food"
                assert result.error_message == "Product not found in any source"

    def test_search_in_usda_success(self):
        """Test successful USDA search."""
        mock_foods = [
            create_mock_food_record("Green Apple", protein_g=0.3, fat_g=0.2, carbs_g=14),
        ]

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.usda_adapter.normalize = Mock(return_value=mock_foods)

            result = finder._search_in_usda("apple")

            assert result.found is True
            assert result.source == "USDA"

    def test_search_in_usda_no_match(self):
        """Test USDA search with no matching products."""
        mock_foods = [
            create_mock_food_record("Chicken", protein_g=25),
        ]

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.usda_adapter.normalize = Mock(return_value=mock_foods)

            result = finder._search_in_usda("banana")  # No banana in mock data

            assert result.found is False

    def test_search_in_usda_exception(self):
        """Test USDA search with exception."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.usda_adapter.normalize = Mock(side_effect=Exception("API Error"))

            result = finder._search_in_usda("apple")

            assert result.found is False

    def test_search_in_off_success(self):
        """Test successful OFF search."""
        mock_foods = [
            create_mock_food_record("Organic Apple", protein_g=0.3),
        ]

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.off_adapter.normalize = Mock(return_value=mock_foods)

            result = finder._search_in_off("apple")

            assert result.found is True
            assert result.source == "OFF"

    def test_search_in_off_exception(self):
        """Test OFF search with exception."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.off_adapter.normalize = Mock(side_effect=Exception("API Error"))

            result = finder._search_in_off("apple")

            assert result.found is False

    @pytest.mark.parametrize(
        "search_name,found_name,expected_min,expected_max",
        [
            ("apple", "apple", 1.0, 1.0),  # Exact match
            ("apple", "green apple", 0.7, 0.9),  # Contains
            ("apple", "banana", 0.0, 0.0),  # No match
        ],
    )
    def test_calculate_confidence(
        self,
        search_name: Literal["apple"],
        found_name: Literal["apple"] | Literal["green apple"] | Literal["banana"],
        expected_min: float,
        expected_max: float,
    ):
        """Test confidence calculation for name matching."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            confidence = finder._calculate_confidence(search_name, found_name)

            assert expected_min <= confidence <= expected_max

    def test_add_product_to_database_success(self):
        """Test successful product addition to database."""
        mock_food_record = create_mock_food_record("Test Food", protein_g=10.0)

        search_result = ProductSearchResult(
            product_name="Test Product",
            found=True,
            source="USDA",
            food_record=mock_food_record,
            confidence=0.9,
        )

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            with patch.object(finder, "_append_to_food_db") as mock_append:
                result = finder.add_product_to_database(search_result)

                assert result is True
                mock_append.assert_called_once()

    def test_add_product_to_database_not_found(self):
        """Test adding product when search result is not found."""
        search_result = ProductSearchResult(product_name="Unknown Product", found=False)

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            result = finder.add_product_to_database(search_result)

            assert result is False

    def test_add_product_to_database_exception(self):
        """Test adding product with exception during conversion."""
        mock_food_record = create_mock_food_record("Test Food", protein_g=10.0)

        search_result = ProductSearchResult(
            product_name="Test Product",
            found=True,
            source="USDA",
            food_record=mock_food_record,
            confidence=0.9,
        )

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            with patch.object(
                finder, "_convert_to_food_item", side_effect=Exception("Conversion error")
            ):
                result = finder.add_product_to_database(search_result)

                assert result is False

    def test_convert_to_food_item(self):
        """Test converting FoodRecord to FoodItem."""
        food_record = create_mock_food_record("Original Name", protein_g=10.0)

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            food_item = finder._convert_to_food_item(food_record, "Custom Name")

            assert isinstance(food_item, FoodItem)
            assert food_item.name == "Custom Name"  # Should use provided name
            assert food_item.protein_g == 10.0

    def test_append_to_food_db_new_file(self):
        """Test appending to food database when file doesn't exist."""
        food_item = FoodItem(
            name="Test Food",
            unit_per=100,
            unit="g",
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=20.0,
            fiber_g=3.0,
            Fe_mg=1.0,
            Ca_mg=50.0,
            VitD_IU=100.0,
            B12_ug=2.0,
            Folate_ug=10.0,
            Iodine_ug=15.0,
            K_mg=100.0,
            Mg_mg=25.0,
            price_per_unit=1.5,
            flags=set(),
        )

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            with patch("core.product_finder.Path") as mock_path:
                mock_path.return_value.exists.return_value = False

                with patch("builtins.open", mock_open()) as mock_file:
                    finder._append_to_food_db(food_item)

                    # Verify file was opened for append
                    mock_file.assert_called_once()

    def test_auto_expand_database(self):
        """Test automatic database expansion."""
        mock_food_db = {
            1: FoodItem(
                name="Apple",
                unit_per=100,
                unit="g",
                protein_g=0.3,
                fat_g=0.2,
                carbs_g=14,
                fiber_g=2.4,
                Fe_mg=0.12,
                Ca_mg=6,
                VitD_IU=0,
                B12_ug=0,
                Folate_ug=3,
                Iodine_ug=0,
                K_mg=107,
                Mg_mg=5,
                price_per_unit=0.5,
                flags=set(),
            ),
        }

        with patch("core.product_finder.parse_food_db", return_value=mock_food_db):
            finder = ProductFinder()

            # Mock search and add methods
            with (
                patch.object(finder, "search_product") as mock_search,
                patch.object(finder, "add_product_to_database") as mock_add,
            ):

                # Setup mock responses
                mock_search.return_value = ProductSearchResult(
                    product_name="banana", found=True, confidence=0.9
                )
                mock_add.return_value = True

                ingredients = ["apple", "banana"]
                results = finder.auto_expand_database(ingredients)

                # Should find one missing product (banana)
                assert len(results) == 1
                assert "banana" in results
                assert results["banana"] is True


class TestProductFinderAdditionalCoverage:
    """Additional tests to cover remaining missing lines in ProductFinder."""

    def test_search_off_error_handling(self):
        """Test OFF search error handling - covers lines 136-137."""
        with (
            patch("core.product_finder.parse_food_db", return_value={}),
            patch("core.product_finder.USDAAdapter"),
            patch("core.product_finder.OFFAdapter"),
        ):
            finder = ProductFinder()

            # Mock both USDA returns nothing and OFF raises exception
            with (
                patch.object(finder, "_search_in_usda") as mock_usda,
                patch.object(finder, "_search_in_off") as mock_off,
            ):
                mock_usda.return_value = ProductSearchResult(
                    product_name="test_product", found=False
                )
                mock_off.side_effect = Exception("OFF service unavailable")

                # Should handle the error gracefully and return not found
                result = finder.search_product("test_product")
                assert not result.found
                assert result.product_name == "test_product"

    def test_calculate_confidence_no_common_words(self):
        """Test confidence calculation with no common words - covers line 257."""
        # Mock all external dependencies that ProductFinder.__init__ would create
        with (
            patch("core.product_finder.USDAAdapter") as mock_usda_class,
            patch("core.product_finder.OFFAdapter") as mock_off_class,
            patch("core.product_finder.parse_food_db", return_value={}) as mock_parse_db,
        ):

            finder = ProductFinder()

            # Verify that dependencies were created during initialization
            mock_usda_class.assert_called_once()
            mock_off_class.assert_called_once()
            mock_parse_db.assert_called_once_with("data/food_db.csv")

            # Products with completely different words
            confidence = finder._calculate_confidence("apple red", "banana yellow")
            assert confidence == 0.0

    def test_search_off_with_confidence_filtering(self):
        """Test OFF search with confidence filtering - covers lines 208->206, 212->224."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            # Test the confidence calculation directly
            low_confidence = finder._calculate_confidence("apple red", "banana yellow")
            high_confidence = finder._calculate_confidence("apple red", "apple fresh red")

            assert low_confidence == 0.0  # No common words
            assert high_confidence > 0.5  # Common words "apple" and "red"
        high_confidence = finder._calculate_confidence("apple red", "apple fresh red")

        assert low_confidence == 0.0  # No common words
        assert high_confidence > 0.5  # Common words "apple" and "red"

    def test_expand_database_csv_header_creation(self, tmp_path: Path):
        """Test CSV header creation in expand_database - covers lines 359->363."""
        # Avoid side-effects in ProductFinder.__init__
        with patch.object(ProductFinder, "__init__", return_value=None):
            finder = ProductFinder()
            finder.usda_adapter = None
            finder.off_adapter = None
            finder.food_db = {}

        csv_path = tmp_path / "expand_create_header.csv"
        # Ensure clean start
        if csv_path.exists():
            csv_path.unlink()

        try:
            # Mock successful product search
            mock_result = ProductSearchResult(
                product_name="test",
                found=True,
                food_record=create_mock_food_record("test food", 1.0, 2.0, 15.0),
                confidence=0.8,
                source="test",
            )

            with patch.object(finder, "search_product", return_value=mock_result):
                results = finder.expand_database(["test"], str(csv_path))

                # Should create file with header
                assert csv_path.exists()
                with open(csv_path, "r") as f:
                    content = f.read()
                    assert "name" in content  # Check header was written

                assert results["test"] is True

        finally:
            # tmp_path handles cleanup; ensure file closed before fixture teardown
            pass

    def test_expand_database_logging_cases(self, tmp_path: Path):
        """Test logging in expand_database - covers lines 418-421."""
        # Avoid side-effects in ProductFinder.__init__
        with patch.object(ProductFinder, "__init__", return_value=None):
            finder = ProductFinder()
            finder.usda_adapter = None
            finder.off_adapter = None
            finder.food_db = {}

        csv_path = tmp_path / "expand_logging.csv"

        try:
            # Test case 1: Product found and added successfully
            mock_success = ProductSearchResult(
                product_name="success_product",
                found=True,
                food_record=create_mock_food_record("success food", 1.0, 2.0, 15.0),
                confidence=0.8,
                source="test",
            )

            # Test case 2: Product not found
            mock_not_found = ProductSearchResult(
                product_name="not_found_product",
                found=False,
                food_record=None,
                confidence=0.0,
                source="none",
            )

            def mock_search(product_name):
                if product_name == "success_product":
                    return mock_success
                elif product_name == "not_found_product":
                    return mock_not_found
                else:
                    return mock_not_found

            with patch.object(finder, "search_product", side_effect=mock_search):
                with patch("core.product_finder.logger") as mock_logger:
                    results = finder.expand_database(
                        ["success_product", "not_found_product"], str(csv_path)
                    )

                    # Check results
                    assert results["success_product"] is True
                    assert results["not_found_product"] is False

                    # Verify logging calls were made
                    mock_logger.info.assert_called()
                    mock_logger.warning.assert_called()

        finally:
            # tmp_path handles cleanup
            pass

# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.product_finder module.
Covers ProductSearchResult and ProductFinder classes.
"""

import pytest
import tempfile
import csv
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from core.product_finder import ProductSearchResult, ProductFinder
from core.food_db import FoodItem
from core.food_sources.base import FoodRecord


def create_mock_food_record(
    name,
    protein_g=0,
    fat_g=0,
    carbs_g=0,
    fiber_g=0,
    Fe_mg=0,
    Ca_mg=0,
    VitD_IU=0,
    B12_ug=0,
    Folate_ug=0,
    Iodine_ug=0,
    K_mg=0,
    Mg_mg=0,
):
    """Helper function to create FoodRecord with default values."""
    return FoodRecord(
        name=name,
        locale="en",
        per_g=100.0,
        kcal=protein_g * 4 + carbs_g * 4 + fat_g * 9,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        fiber_g=fiber_g,
        Fe_mg=Fe_mg,
        Ca_mg=Ca_mg,
        VitD_IU=VitD_IU,
        B12_ug=B12_ug,
        Folate_ug=Folate_ug,
        Iodine_ug=Iodine_ug,
        K_mg=K_mg,
        Mg_mg=Mg_mg,
        flags=[],
        price=1.0,
        source="TEST",
        version_date="2025-01-01",
    )


class TestProductSearchResult:
    """Tests for ProductSearchResult dataclass."""

    def test_create_successful_result(self):
        """Test creating a successful search result."""
        food_record = create_mock_food_record(
            "Test Food",
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=20.0,
            fiber_g=3.0,
            Fe_mg=1.0,
            Ca_mg=50.0,
            Folate_ug=10.0,
            K_mg=100.0,
            Mg_mg=25.0,
        )

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
        assert result.food_record == food_record
        assert result.confidence == 0.85
        assert result.error_message is None

    def test_create_failed_result(self):
        """Test creating a failed search result."""
        result = ProductSearchResult(
            product_name="Unknown Product", found=False, error_message="Product not found"
        )

        assert result.product_name == "Unknown Product"
        assert result.found is False
        assert result.source is None
        assert result.food_record is None
        assert result.confidence == 0.0
        assert result.error_message == "Product not found"


class TestProductFinder:
    """Tests for ProductFinder class."""

    def create_test_food_db_csv(self):
        """Create a temporary food database CSV for testing."""
        csv_data = [
            [
                "name",
                "unit_per",
                "unit",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "Fe_mg",
                "Ca_mg",
                "VitD_IU",
                "B12_ug",
                "Folate_ug",
                "Iodine_ug",
                "K_mg",
                "Mg_mg",
                "price_per_unit",
                "flags",
            ],
            [
                "Apple",
                "100",
                "g",
                "0.3",
                "0.2",
                "14",
                "2.4",
                "0.12",
                "6",
                "0",
                "0",
                "3",
                "0",
                "107",
                "5",
                "0.5",
                "",
            ],
            [
                "Chicken Breast",
                "100",
                "g",
                "31",
                "3.6",
                "0",
                "0",
                "0.89",
                "15",
                "0",
                "0.89",
                "4",
                "0",
                "256",
                "29",
                "3.0",
                "",
            ],
            [
                "Brown Rice",
                "100",
                "g",
                "7.9",
                "2.9",
                "77",
                "3.5",
                "2.2",
                "33",
                "0",
                "0",
                "20",
                "0",
                "223",
                "143",
                "1.2",
                "",
            ],
        ]

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        writer = csv.writer(temp_file)
        writer.writerows(csv_data)
        temp_file.close()

        return temp_file.name

    @patch("core.product_finder.parse_food_db")
    @patch("core.product_finder.USDAAdapter")
    @patch("core.product_finder.OFFAdapter")
    def test_init(self, mock_off, mock_usda, mock_parse_db):
        """Test ProductFinder initialization."""
        mock_parse_db.return_value = {}

        finder = ProductFinder()

        assert finder.usda_adapter is not None
        assert finder.off_adapter is not None
        assert finder.food_db == {}
        mock_parse_db.assert_called_once_with("data/food_db.csv")

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
            2: FoodItem(
                name="Chicken Breast",
                unit_per=100,
                unit="g",
                protein_g=31,
                fat_g=3.6,
                carbs_g=0,
                fiber_g=0,
                Fe_mg=0.89,
                Ca_mg=15,
                VitD_IU=0,
                B12_ug=0.89,
                Folate_ug=4,
                Iodine_ug=0,
                K_mg=256,
                Mg_mg=29,
                price_per_unit=3.0,
                flags=set(),
            ),
        }

        with patch("core.product_finder.parse_food_db", return_value=mock_food_db):
            finder = ProductFinder()

            ingredients = ["apple", "chicken breast"]
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

            ingredients = ["apple", "unknown ingredient", "mystery food"]
            missing = finder.find_missing_products(ingredients)

            assert len(missing) == 2
            assert "unknown ingredient" in missing
            assert "mystery food" in missing

    @pytest.mark.parametrize(
        "name1,name2,expected",
        [
            ("apple", "apple", True),
            ("chicken breast", "breast", True),
            ("brown rice", "rice brown", True),
            ("apple", "chicken", False),
            ("olive oil", "oil", True),
            ("red apple", "apple green", True),  # Common word "apple"
            ("completely different", "nothing similar", False),
        ],
    )
    def test_similar_names(self, name1, name2, expected):
        """Test similar names detection."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            result = finder._similar_names(name1, name2)
            assert result == expected

    def test_search_product_usda_success(self):
        """Test successful product search in USDA."""
        mock_food_record = create_mock_food_record(
            "Test Apple",
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
        )

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
                assert result.confidence == 0.9

    def test_search_product_off_fallback(self):
        """Test product search falling back to OFF when USDA fails."""
        mock_food_record = create_mock_food_record(
            "Test Food",
            protein_g=5.0,
            fat_g=3.0,
            carbs_g=10,
            fiber_g=1.0,
            Fe_mg=1.0,
            Ca_mg=20,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=5,
            Iodine_ug=0,
            K_mg=50,
            Mg_mg=10,
        )

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            # Mock USDA search failure and OFF success
            with (
                patch.object(finder, "_search_in_usda") as mock_usda_search,
                patch.object(finder, "_search_in_off") as mock_off_search,
            ):
                mock_usda_search.return_value = ProductSearchResult(
                    product_name="test food", found=False
                )

                mock_off_search.return_value = ProductSearchResult(
                    product_name="test food",
                    found=True,
                    source="OFF",
                    food_record=mock_food_record,
                    confidence=0.8,
                )

                result = finder.search_product("test food")

                assert result.found is True
                assert result.source == "OFF"
                assert result.confidence == 0.8

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

            # Mock USDA throwing exception, OFF succeeding
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

    def test_search_in_usda_success(self):
        """Test successful USDA search."""
        mock_foods = [
            create_mock_food_record(
                "Green Apple",
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
            ),
            create_mock_food_record(
                "Red Apple",
                protein_g=0.4,
                fat_g=0.1,
                carbs_g=15,
                fiber_g=2.5,
                Fe_mg=0.15,
                Ca_mg=7,
                VitD_IU=0,
                B12_ug=0,
                Folate_ug=4,
                Iodine_ug=0,
                K_mg=110,
                Mg_mg=6,
            ),
        ]

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.usda_adapter.normalize = Mock(return_value=mock_foods)

            result = finder._search_in_usda("apple")

            assert result.found is True
            assert result.source == "USDA"
            assert result.confidence > 0.3

    def test_search_in_usda_no_match(self):
        """Test USDA search with no matching products."""
        mock_foods = [
            create_mock_food_record(
                "Chicken",
                protein_g=25,
                fat_g=5,
                carbs_g=0,
                fiber_g=0,
                Fe_mg=1.0,
                Ca_mg=15,
                VitD_IU=0,
                B12_ug=0.3,
                Folate_ug=4,
                Iodine_ug=0,
                K_mg=256,
                Mg_mg=25,
            ),
        ]

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.usda_adapter.normalize = Mock(return_value=mock_foods)

            result = finder._search_in_usda("banana")  # No banana in mock data

            assert result.found is False
            assert result.error_message == "USDA search failed"

    def test_search_in_usda_exception(self):
        """Test USDA search with exception."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.usda_adapter.normalize = Mock(side_effect=Exception("API Error"))

            result = finder._search_in_usda("apple")

            assert result.found is False
            assert result.error_message == "USDA search failed"

    def test_search_in_off_success(self):
        """Test successful OFF search."""
        mock_foods = [
            create_mock_food_record(
                "Organic Apple",
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
            ),
        ]

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.off_adapter.normalize = Mock(return_value=mock_foods)

            result = finder._search_in_off("apple")

            assert result.found is True
            assert result.source == "OFF"
            assert result.confidence > 0.3

    def test_search_in_off_exception(self):
        """Test OFF search with exception."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()
            finder.off_adapter.normalize = Mock(side_effect=Exception("API Error"))

            result = finder._search_in_off("apple")

            assert result.found is False
            assert result.error_message == "OFF search failed"

    @pytest.mark.parametrize(
        "search_name,found_name,expected_min,expected_max",
        [
            ("apple", "apple", 1.0, 1.0),  # Exact match
            ("apple", "green apple", 0.7, 0.9),  # Contains
            ("green apple", "apple", 0.7, 0.9),  # Contains
            ("apple pie", "apple cake", 0.4, 0.6),  # Common words
            ("apple", "banana", 0.0, 0.0),  # No match
            ("chicken breast", "chicken", 0.7, 0.9),  # Contains
        ],
    )
    def test_calculate_confidence(self, search_name, found_name, expected_min, expected_max):
        """Test confidence calculation for name matching."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            confidence = finder._calculate_confidence(search_name, found_name)

            assert expected_min <= confidence <= expected_max

    def test_add_product_to_database_success(self):
        """Test successful product addition to database."""
        mock_food_record = create_mock_food_record(
            "Test Food",
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=20.0,
            fiber_g=3.0,
            Fe_mg=1.0,
            Ca_mg=50.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=10.0,
            Iodine_ug=0.0,
            K_mg=100.0,
            Mg_mg=25.0,
        )

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

    def test_add_product_to_database_no_food_record(self):
        """Test adding product when no food record exists."""
        search_result = ProductSearchResult(
            product_name="Test Product", found=True, food_record=None
        )

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            result = finder.add_product_to_database(search_result)

            assert result is False

    def test_add_product_to_database_exception(self):
        """Test adding product with exception during conversion."""
        mock_food_record = create_mock_food_record(
            "Test Food",
            protein_g=10.0,
            fat_g=5.0,
            carbs_g=20.0,
            fiber_g=3.0,
            Fe_mg=1.0,
            Ca_mg=50.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=10.0,
            Iodine_ug=0.0,
            K_mg=100.0,
            Mg_mg=25.0,
        )

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
        food_record = create_mock_food_record(
            "Original Name",
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
        )

        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            food_item = finder._convert_to_food_item(food_record, "Custom Name")

            assert isinstance(food_item, FoodItem)
            assert food_item.name == "Custom Name"  # Should use provided name
            assert food_item.protein_g == 10.0
            assert food_item.fat_g == 5.0
            assert food_item.carbs_g == 20.0
            assert food_item.unit_per == 100
            assert food_item.unit == "g"
            assert food_item.price_per_unit == 0.0
            assert food_item.flags == set()

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
            flags={"VEG"},
        )

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as temp_file:
            temp_path = temp_file.name

        # Remove the file so it doesn't exist
        Path(temp_path).unlink()

        try:
            with patch("core.product_finder.parse_food_db", return_value={}):
                finder = ProductFinder()

                with patch("core.product_finder.Path") as mock_path:
                    mock_path.return_value.exists.return_value = False

                    with patch("builtins.open", mock_open()) as mock_file:
                        finder._append_to_food_db(food_item)

                        # Verify file was opened for append
                        mock_file.assert_called_once()
        finally:
            # Clean up if file was created
            if Path(temp_path).exists():
                Path(temp_path).unlink()

    def test_append_to_food_db_existing_file(self):
        """Test appending to existing food database file."""
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
                mock_path.return_value.exists.return_value = True

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
                mock_search.side_effect = [
                    ProductSearchResult(product_name="banana", found=True, confidence=0.9),
                    ProductSearchResult(product_name="unknown", found=False),
                ]

                mock_add.return_value = True

                ingredients = ["apple", "banana", "unknown"]
                results = finder.auto_expand_database(ingredients)

                # Should find one missing product (banana), unknown not found
                assert len(results) == 2
                assert "banana" in results
                assert "unknown" in results
                assert results["banana"] is True
                assert results["unknown"] is False

    def test_auto_expand_database_add_failure(self):
        """Test automatic database expansion with add failure."""
        with patch("core.product_finder.parse_food_db", return_value={}):
            finder = ProductFinder()

            # Mock search and add methods
            with (
                patch.object(finder, "search_product") as mock_search,
                patch.object(finder, "add_product_to_database") as mock_add,
            ):
                # Setup mock responses
                mock_search.return_value = ProductSearchResult(
                    product_name="test", found=True, confidence=0.9
                )
                mock_add.return_value = False  # Add fails

                ingredients = ["test"]
                results = finder.auto_expand_database(ingredients)

                assert len(results) == 1
                assert results["test"] is False

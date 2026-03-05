"""
Simple tests for food_sources module to improve coverage.

Targeting specific lines with error scenarios and edge cases:
- USDA lines 34->39, 49-55: directory traversal, CSV parsing
- OFF lines 34->43, 53-59: directory traversal, CSV parsing
- Base lines 54, 61: abstract method calls
"""

import csv
import os
import tempfile

import pytest

from core.food_sources.base import BaseAdapter, FoodRecord
from core.food_sources.off import OFFAdapter
from core.food_sources.usda import USDAAdapter


class TestUSDAAdapter:
    """Test USDA adapter error handling scenarios."""

    def test_usda_directory_processing(self):
        """Test USDA fetch from directory with multiple CSV files."""
        # Create temp directory with CSV files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create valid CSV file
            csv1_path = os.path.join(temp_dir, "file1.csv")
            with open(csv1_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["description", "energy_kcal", "protein_g"])
                writer.writerow(["Apple", "52", "0.3"])

            # Create another CSV file
            csv2_path = os.path.join(temp_dir, "file2.csv")
            with open(csv2_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["description", "energy_kcal", "protein_g"])
                writer.writerow(["Banana", "89", "1.1"])

            # Create non-CSV file (should be ignored)
            txt_path = os.path.join(temp_dir, "readme.txt")
            with open(txt_path, "w") as f:
                f.write("Not a CSV")

            # Test directory processing
            adapter = USDAAdapter(csv_path=temp_dir)
            results = list(adapter.fetch())

            # Should process both CSV files, ignore txt file
            assert len(results) == 2
            assert any(row["description"] == "Apple" for row in results)
            assert any(row["description"] == "Banana" for row in results)

    def test_usda_missing_csv_file_error(self):
        """Test USDA fetch with missing CSV file."""
        adapter = USDAAdapter(csv_path="/nonexistent/file.csv")

        with pytest.raises(FileNotFoundError):
            list(adapter.fetch())

    def test_usda_normalize_with_missing_nutrients(self):
        """Test USDA normalize with missing/empty nutrient values."""
        # Create CSV with missing values
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["description", "energy_kcal", "protein_g", "fat_g", "carbs_g"])
            # Row with empty values that should fallback to 0
            writer.writerow(["Test Food", "", "", "", "5.0"])
            f.flush()

            adapter = USDAAdapter(csv_path=f.name)
            results = list(adapter.normalize())

            assert len(results) == 1
            food = results[0]
            assert food.name  # Should have canonical name
            assert food.kcal == 0.0  # Empty string -> 0
            assert food.protein_g == 0.0  # Empty string -> 0
            assert food.fat_g == 0.0  # Empty string -> 0
            assert food.carbs_g == 5.0  # Valid value
            assert food.source == "USDA"

        os.unlink(f.name)

    def test_usda_normalize_vitamin_d_conversion(self):
        """Test USDA vitamin D conversion from µg to IU."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["description", "vitd_ug"])
            writer.writerow(["Test Food", "10.0"])  # 10 µg should convert to IU
            f.flush()

            adapter = USDAAdapter(csv_path=f.name)
            results = list(adapter.normalize())

            assert len(results) == 1
            food = results[0]
            # Should convert µg to IU (10 µg * 40 = 400 IU approximately)
            assert food.VitD_IU > 0

        os.unlink(f.name)


class TestOFFAdapter:
    """Test OFF adapter error handling scenarios."""

    def test_off_directory_processing(self):
        """Test OFF fetch from directory with multiple CSV files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create CSV file with multiple product name fields
            csv1_path = os.path.join(temp_dir, "products1.csv")
            with open(csv1_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["product_name", "generic_name", "energy-kcal_100g"])
                writer.writerow(["", "Generic Apple", "52"])  # product_name empty, use generic

            csv2_path = os.path.join(temp_dir, "products2.csv")
            with open(csv2_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["product_name_en", "energy-kcal_100g"])
                writer.writerow(["English Banana", "89"])  # Use product_name_en

            # Test directory processing
            adapter = OFFAdapter(csv_path=temp_dir, locale="en")
            results = list(adapter.fetch())

            assert len(results) == 2
            assert any("Generic Apple" in str(row.values()) for row in results)
            assert any("English Banana" in str(row.values()) for row in results)

    def test_off_product_name_fallback(self):
        """Test OFF product name fallback chain."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["product_name", "generic_name", "product_name_en", "energy-kcal_100g"])
            # Test fallback: product_name empty -> use generic_name
            writer.writerow(["", "Generic Name", "English Name", "100"])
            # Test fallback: both empty -> use product_name_en
            writer.writerow(["", "", "English Only", "200"])
            f.flush()

            adapter = OFFAdapter(csv_path=f.name, locale="fr")
            results = list(adapter.normalize())

            assert len(results) == 2
            names = [food.name for food in results]
            # Should use fallback names - check if canonical names include fallback content
            assert len(names[0]) > 0 and len(names[1]) > 0  # Both should have names
            assert any(names)

        os.unlink(f.name)

    def test_off_dietary_flags_parsing(self):
        """Test OFF dietary flags extraction."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["product_name", "gluten-free", "vegan", "low-cost", "dairy_free"])
            writer.writerow(["Test Product", "yes", "yes", "yes", "yes"])
            f.flush()

            adapter = OFFAdapter(csv_path=f.name)
            results = list(adapter.normalize())

            assert len(results) == 1
            food = results[0]
            expected_flags = {"GF", "VEG", "LOW_COST", "DAIRY_FREE"}
            assert set(food.flags) == expected_flags

        os.unlink(f.name)

    def test_off_missing_file_error(self):
        """Test OFF fetch with missing CSV file."""
        adapter = OFFAdapter(csv_path="/nonexistent/off_file.csv")

        with pytest.raises(FileNotFoundError):
            list(adapter.fetch())

    def test_off_vitamin_d_converts_ug_to_iu(self) -> None:
        """OFF vitamin-d_100g must convert from µg to IU."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["product_name", "vitamin-d_100g"])
            writer.writerow(["Test Product", "10.0"])  # 10 µg -> 400 IU
            f.flush()

            adapter = OFFAdapter(csv_path=f.name)
            results = list(adapter.normalize())

            assert len(results) == 1
            assert results[0].VitD_IU == 400.0

        os.unlink(f.name)

    def test_off_skips_nameless_rows(self) -> None:
        """Rows without product_name/generic_name/product_name_en are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["product_name", "generic_name", "product_name_en", "energy-kcal_100g"])
            writer.writerow(["", "", "", "50"])  # nameless row should be skipped
            writer.writerow(["None", "", "", "60"])  # explicit malformed null marker
            writer.writerow(["Named Product", "", "", "120"])
            f.flush()

            adapter = OFFAdapter(csv_path=f.name)
            results = list(adapter.normalize())

            assert len(results) == 1
            assert results[0].name

        os.unlink(f.name)

    def test_off_skips_none_name_candidates_from_fetch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """None candidate values should be ignored as nameless input."""
        adapter = OFFAdapter(csv_path="/tmp/unused.csv")

        def _fake_fetch() -> list[dict[str, object]]:
            return [
                {
                    "product_name": None,
                    "generic_name": None,
                    "product_name_en": None,
                    "energy-kcal_100g": "50",
                },
                {
                    "product_name": None,
                    "generic_name": "Valid Fallback Name",
                    "product_name_en": None,
                    "energy-kcal_100g": "120",
                },
            ]

        monkeypatch.setattr(adapter, "fetch", _fake_fetch)
        results = list(adapter.normalize())

        assert len(results) == 1
        assert results[0].name


class TestBaseAdapter:
    """Test base adapter abstract methods."""

    def test_base_adapter_abstract_methods(self):
        """Test that BaseAdapter methods raise NotImplementedError."""
        adapter = BaseAdapter()

        with pytest.raises(NotImplementedError):
            list(adapter.fetch())

        with pytest.raises(NotImplementedError):
            list(adapter.normalize())

    def test_food_record_creation(self):
        """Test FoodRecord dataclass creation."""
        record = FoodRecord(
            name="Test Food",
            locale="en",
            per_g=100.0,
            kcal=250.0,
            protein_g=10.0,
            fat_g=15.0,
            carbs_g=30.0,
            fiber_g=5.0,
            Fe_mg=2.0,
            Ca_mg=100.0,
            VitD_IU=50.0,
            B12_ug=1.0,
            Folate_ug=20.0,
            Iodine_ug=10.0,
            K_mg=300.0,
            Mg_mg=50.0,
            flags=["GF"],
            price=2.5,
            source="TEST",
            version_date="2024-01-01",
        )

        assert record.name == "Test Food"
        assert record.kcal == 250.0
        assert record.flags == ["GF"]
        assert record.source == "TEST"


class TestFoodSourcesIntegration:
    """Integration tests for food sources."""

    def test_usda_csv_edge_cases(self):
        """Test USDA CSV with edge case data."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            writer = csv.writer(f)
            writer.writerow(["description", "energy_kcal", "protein_g", "vitd_ug", "iron_mg"])
            # Edge cases: zero values, very small values
            writer.writerow(["Zero Nutrition", "0", "0.0", "0", "0.0"])
            writer.writerow(["Micro Values", "0.1", "0.01", "0.001", "0.001"])
            f.flush()

            adapter = USDAAdapter(csv_path=f.name)
            results = list(adapter.normalize())

            assert len(results) == 2
            # Should handle zero and very small values
            assert all(food.kcal >= 0 for food in results)
            assert all(food.protein_g >= 0 for food in results)

        os.unlink(f.name)

    def test_off_empty_csv_handling(self):
        """Test OFF adapter with empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            # Create CSV with headers but no data rows
            writer = csv.writer(f)
            writer.writerow(["product_name", "energy-kcal_100g"])
            # No data rows
            f.flush()

            adapter = OFFAdapter(csv_path=f.name)
            results = list(adapter.normalize())

            # Should handle empty data gracefully
            assert not results

        os.unlink(f.name)

    def test_usda_default_path(self):
        """Test USDA adapter with default path (None)."""
        # Test with None path - should use default external file
        adapter = USDAAdapter()  # No csv_path argument
        # Should set default path without crashing
        assert adapter.csv_path
        assert "external" in adapter.csv_path
        assert "usda_fdc_sample.csv" in adapter.csv_path

    def test_off_default_path_and_locale(self):
        """Test OFF adapter with default path and locale."""
        # Test with None path - should use default external file
        adapter = OFFAdapter(locale="es")  # No csv_path argument
        # Should set default path and locale
        assert adapter.csv_path
        assert "external" in adapter.csv_path
        assert "off_products_sample.csv" in adapter.csv_path
        assert adapter.locale == "es"

    def test_usda_directory_not_exists(self):
        """Test USDA with non-existent directory."""
        adapter = USDAAdapter(csv_path="/non/existent/directory")
        with pytest.raises(FileNotFoundError):
            list(adapter.fetch())

    def test_off_directory_no_csv_files(self):
        """Test OFF with directory containing no CSV files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create non-CSV files
            with open(os.path.join(temp_dir, "readme.txt"), "w") as f:
                f.write("Not a CSV")
            with open(os.path.join(temp_dir, "data.json"), "w") as f:
                f.write("{}")

            adapter = OFFAdapter(csv_path=temp_dir)
            results = list(adapter.fetch())

            # Should return empty results when no CSV files found
            assert not results

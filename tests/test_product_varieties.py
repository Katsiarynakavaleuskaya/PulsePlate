"""
Comprehensive tests for core.product_varieties module.
Covers ProductVariety and ProductVarietiesManager classes.
"""

import csv
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from core.food_db import FoodItem
from core.product_varieties import ProductVarietiesManager, ProductVariety


class TestProductVariety:
    """Tests for ProductVariety class."""

    def test_create_product_variety(self):
        """Test creating a ProductVariety instance."""
        variety = ProductVariety(
            name="Apple",
            variety="Gala",
            brand="Organic Valley",
            protein_g=0.5,
            fat_g=0.2,
            carbs_g=14.0,
            fiber_g=2.4,
            sugar_g=10.0,
            Fe_mg=0.15,
            Ca_mg=6.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=3.0,
            Iodine_ug=0.0,
            K_mg=107.0,
            Mg_mg=5.0,
            flags={"VEG", "GF"},
            notes="Fresh organic apple",
        )

        assert variety.name == "Apple"
        assert variety.variety == "Gala"
        assert variety.brand == "Organic Valley"
        assert variety.protein_g == 0.5
        assert variety.fat_g == 0.2
        assert variety.carbs_g == 14.0
        assert "VEG" in variety.flags
        assert "GF" in variety.flags

    def test_to_food_item(self):
        """Test converting ProductVariety to FoodItem."""
        variety = ProductVariety(
            name="Chicken",
            variety="Organic",
            brand="Farm Fresh",
            protein_g=25.0,
            fat_g=5.0,
            carbs_g=0.0,
            fiber_g=0.0,
            sugar_g=0.0,
            Fe_mg=1.2,
            Ca_mg=15.0,
            VitD_IU=0.0,
            B12_ug=0.3,
            Folate_ug=4.0,
            Iodine_ug=0.0,
            K_mg=256.0,
            Mg_mg=25.0,
            flags=set(),
            notes="",
        )

        food_item = variety.to_food_item()

        assert isinstance(food_item, FoodItem)
        assert food_item.name == "Chicken (Organic)"
        assert food_item.protein_g == 25.0
        assert food_item.fat_g == 5.0
        assert food_item.carbs_g == 0.0
        assert food_item.unit_per == 100
        assert food_item.unit == "g"

    def test_get_calories(self):
        """Test calorie calculation."""
        variety = ProductVariety(
            name="Test",
            variety="Test",
            brand="Test",
            protein_g=10.0,  # 40 kcal
            fat_g=5.0,  # 45 kcal
            carbs_g=20.0,  # 80 kcal
            fiber_g=0.0,
            sugar_g=0.0,
            Fe_mg=0.0,
            Ca_mg=0.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=0.0,
            Iodine_ug=0.0,
            K_mg=0.0,
            Mg_mg=0.0,
            flags=set(),
            notes="",
        )

        calories = variety.get_calories()
        expected = (10 * 4) + (20 * 4) + (5 * 9)  # 40 + 80 + 45 = 165
        assert calories == expected

    def test_get_sugar_content(self):
        """Test sugar content getter."""
        variety = ProductVariety(
            name="Test",
            variety="Test",
            brand="Test",
            protein_g=0,
            fat_g=0,
            carbs_g=0,
            fiber_g=0,
            sugar_g=12.5,
            Fe_mg=0,
            Ca_mg=0,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=0,
            Iodine_ug=0,
            K_mg=0,
            Mg_mg=0,
            flags=set(),
            notes="",
        )

        assert variety.get_sugar_content() == 12.5

    @pytest.mark.parametrize(
        "sugar_level,expected",
        [
            (3.0, True),
            (5.0, True),
            (5.1, False),
            (10.0, False),
        ],
    )
    def test_is_low_sugar(self, sugar_level, expected):
        """Test low sugar detection."""
        variety = ProductVariety(
            name="Test",
            variety="Test",
            brand="Test",
            protein_g=0,
            fat_g=0,
            carbs_g=0,
            fiber_g=0,
            sugar_g=sugar_level,
            Fe_mg=0,
            Ca_mg=0,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=0,
            Iodine_ug=0,
            K_mg=0,
            Mg_mg=0,
            flags=set(),
            notes="",
        )

        assert variety.is_low_sugar() == expected

    @pytest.mark.parametrize(
        "protein_level,expected",
        [
            (15.0, False),
            (19.9, False),
            (20.0, True),
            (25.0, True),
        ],
    )
    def test_is_high_protein(self, protein_level, expected):
        """Test high protein detection."""
        variety = ProductVariety(
            name="Test",
            variety="Test",
            brand="Test",
            protein_g=protein_level,
            fat_g=0,
            carbs_g=0,
            fiber_g=0,
            sugar_g=0,
            Fe_mg=0,
            Ca_mg=0,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=0,
            Iodine_ug=0,
            K_mg=0,
            Mg_mg=0,
            flags=set(),
            notes="",
        )

        assert variety.is_high_protein() == expected

    @pytest.mark.parametrize(
        "fat_level,expected",
        [
            (1.0, True),
            (3.0, True),
            (3.1, False),
            (5.0, False),
        ],
    )
    def test_is_low_fat(self, fat_level, expected):
        """Test low fat detection."""
        variety = ProductVariety(
            name="Test",
            variety="Test",
            brand="Test",
            protein_g=0,
            fat_g=fat_level,
            carbs_g=0,
            fiber_g=0,
            sugar_g=0,
            Fe_mg=0,
            Ca_mg=0,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=0,
            Iodine_ug=0,
            K_mg=0,
            Mg_mg=0,
            flags=set(),
            notes="",
        )

        assert variety.is_low_fat() == expected


class TestProductVarietiesManager:
    """Tests for ProductVarietiesManager class."""

    def create_test_csv(self):
        """Create a temporary CSV file for testing."""
        csv_data = [
            [
                "name",
                "variety",
                "brand",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "sugar_g",
                "Fe_mg",
                "Ca_mg",
                "VitD_IU",
                "B12_ug",
                "Folate_ug",
                "Iodine_ug",
                "K_mg",
                "Mg_mg",
                "flags",
                "notes",
            ],
            [
                "Apple",
                "Gala",
                "Organic",
                "0.5",
                "0.2",
                "14",
                "2.4",
                "10",
                "0.15",
                "6",
                "0",
                "0",
                "3",
                "0",
                "107",
                "5",
                "VEG, GF",
                "Fresh apple",
            ],
            [
                "Apple",
                "Granny Smith",
                "Regular",
                "0.4",
                "0.3",
                "13",
                "2.8",
                "8",
                "0.12",
                "5",
                "0",
                "0",
                "2",
                "0",
                "120",
                "4",
                "VEG, GF",
                "Tart apple",
            ],
            [
                "Chicken",
                "Organic",
                "Farm Fresh",
                "25",
                "5",
                "0",
                "0",
                "0",
                "1.2",
                "15",
                "0",
                "0.3",
                "4",
                "0",
                "256",
                "25",
                "",
                "Organic chicken",
            ],
            [
                "Invalid",
                "Test",
                "Test",
                "invalid",
                "5",
                "0",
                "0",
                "0",
                "1.2",
                "15",
                "0",
                "0.3",
                "4",
                "0",
                "256",
                "25",
                "",
                "Should be skipped",
            ],
        ]

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        writer = csv.writer(temp_file)
        writer.writerows(csv_data)
        temp_file.close()

        return temp_file.name

    def test_init_with_nonexistent_file(self):
        """Test initialization with non-existent CSV file."""
        manager = ProductVarietiesManager("nonexistent.csv")
        assert len(manager.varieties) == 0

    def test_load_varieties_success(self):
        """Test successful loading of varieties from CSV."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            # Should have 2 products (Apple, Chicken) - Invalid should be skipped
            assert len(manager.varieties) == 2
            assert "Apple" in manager.varieties
            assert "Chicken" in manager.varieties

            # Apple should have 2 varieties
            apple_varieties = manager.varieties["Apple"]
            assert len(apple_varieties) == 2

            # Check first apple variety
            gala = apple_varieties[0]
            assert gala.variety == "Gala"
            assert gala.brand == "Organic"
            assert gala.protein_g == 0.5
            assert "VEG" in gala.flags
            assert "GF" in gala.flags

        finally:
            Path(csv_path).unlink()

    def test_load_varieties_file_error(self):
        """Test loading varieties with file read error."""
        with patch("builtins.open", side_effect=OSError("File read error")):
            manager = ProductVarietiesManager("test.csv")
            assert len(manager.varieties) == 0

    def test_get_varieties(self):
        """Test getting varieties for a product."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            # Test existing product
            apple_varieties = manager.get_varieties("Apple")
            assert len(apple_varieties) == 2

            # Test non-existent product
            missing_varieties = manager.get_varieties("NonExistent")
            assert len(missing_varieties) == 0

        finally:
            Path(csv_path).unlink()

    def test_get_best_variety_balanced(self):
        """Test getting best variety with balanced criteria."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            best = manager.get_best_variety("Apple", "balanced")
            assert best is not None
            assert best.variety in ["Gala", "Granny Smith"]

            # Test non-existent product
            missing = manager.get_best_variety("NonExistent", "balanced")
            assert missing is None

        finally:
            Path(csv_path).unlink()

    def test_get_best_variety_low_sugar(self):
        """Test getting best variety with low sugar criteria."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            best = manager.get_best_variety("Apple", "low_sugar")
            assert best is not None
            # Granny Smith has lower sugar (8) than Gala (10)
            assert best.variety == "Granny Smith"

        finally:
            Path(csv_path).unlink()

    def test_get_best_variety_high_protein(self):
        """Test getting best variety with high protein criteria."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            best = manager.get_best_variety("Apple", "high_protein")
            assert best is not None
            # Gala has higher protein (0.5) than Granny Smith (0.4)
            assert best.variety == "Gala"

        finally:
            Path(csv_path).unlink()

    def test_get_best_variety_low_fat(self):
        """Test getting best variety with low fat criteria."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            best = manager.get_best_variety("Apple", "low_fat")
            assert best is not None
            # Gala has lower fat (0.2) than Granny Smith (0.3)
            assert best.variety == "Gala"

        finally:
            Path(csv_path).unlink()

    def test_get_best_variety_unknown_criteria(self):
        """Test getting best variety with unknown criteria."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            best = manager.get_best_variety("Apple", "unknown")
            assert best is not None
            # Should return first available

        finally:
            Path(csv_path).unlink()

    def test_search_varieties(self):
        """Test searching varieties by criteria."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            # Search by variety name
            gala_results = manager.search_varieties("Apple", variety_name="Gala")
            assert len(gala_results) == 1
            assert gala_results[0].variety == "Gala"

            # Search by brand
            organic_results = manager.search_varieties("Apple", brand="Organic")
            assert len(organic_results) == 1
            assert organic_results[0].brand == "Organic"

            # Search by both
            specific_results = manager.search_varieties(
                "Apple", variety_name="Gala", brand="Organic"
            )
            assert len(specific_results) == 1

            # Search non-existent product
            missing_results = manager.search_varieties("NonExistent")
            assert len(missing_results) == 0

        finally:
            Path(csv_path).unlink()

    def test_get_nutritional_comparison(self):
        """Test getting nutritional comparison."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            comparison = manager.get_nutritional_comparison("Apple")
            assert len(comparison) == 2

            # Check if both varieties are included
            assert "Gala (Organic)" in comparison
            assert "Granny Smith (Regular)" in comparison

            # Check nutritional data structure
            gala_data = comparison["Gala (Organic)"]
            assert "calories" in gala_data
            assert "protein" in gala_data
            assert "fat" in gala_data
            assert "carbs" in gala_data

            # Test non-existent product
            empty_comparison = manager.get_nutritional_comparison("NonExistent")
            assert len(empty_comparison) == 0

        finally:
            Path(csv_path).unlink()

    def test_recommend_variety_no_preferences(self):
        """Test variety recommendation with no preferences."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            recommendation = manager.recommend_variety("Apple", {})
            assert recommendation is not None

            # Test non-existent product
            missing_recommendation = manager.recommend_variety("NonExistent", {})
            assert missing_recommendation is None

        finally:
            Path(csv_path).unlink()

    def test_recommend_variety_with_preferences(self):
        """Test variety recommendation with specific preferences."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            # Test low sugar preference
            low_sugar_rec = manager.recommend_variety("Apple", {"low_sugar": True})
            assert low_sugar_rec is not None

            # Test vegetarian preference
            veg_rec = manager.recommend_variety("Apple", {"vegetarian": True})
            assert veg_rec is not None
            assert "VEG" in veg_rec.flags

            # Test gluten free preference
            gf_rec = manager.recommend_variety("Apple", {"gluten_free": True})
            assert gf_rec is not None
            assert "GF" in gf_rec.flags

            # Test multiple preferences
            multi_rec = manager.recommend_variety(
                "Apple", {"low_sugar": True, "vegetarian": True, "gluten_free": True}
            )
            assert multi_rec is not None

        finally:
            Path(csv_path).unlink()

    def test_recommend_variety_no_matching_preferences(self):
        """Test variety recommendation when no varieties match preferences."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            # Test with impossible criteria for chicken (vegetarian)
            rec = manager.recommend_variety("Chicken", {"vegetarian": True})
            assert rec is not None  # Should return first available when no match

        finally:
            Path(csv_path).unlink()

    def test_get_all_products(self):
        """Test getting all products list."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            products = manager.get_all_products()
            assert len(products) == 2
            assert "Apple" in products
            assert "Chicken" in products

        finally:
            Path(csv_path).unlink()

    def test_get_statistics(self):
        """Test getting statistics."""
        csv_path = self.create_test_csv()

        try:
            manager = ProductVarietiesManager(csv_path)

            stats = manager.get_statistics()
            assert stats["total_products"] == 2
            assert stats["total_varieties"] == 3  # 2 apples + 1 chicken
            assert stats["avg_varieties_per_product"] == 1.5

        finally:
            Path(csv_path).unlink()

    def test_get_statistics_empty_manager(self):
        """Test getting statistics for empty manager."""
        manager = ProductVarietiesManager("nonexistent.csv")

        stats = manager.get_statistics()
        assert stats["total_products"] == 0
        assert stats["total_varieties"] == 0
        assert stats["avg_varieties_per_product"] == 0

    def test_edge_cases_empty_flags(self):
        """Test handling of empty flags in CSV."""
        csv_data = [
            [
                "name",
                "variety",
                "brand",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "sugar_g",
                "Fe_mg",
                "Ca_mg",
                "VitD_IU",
                "B12_ug",
                "Folate_ug",
                "Iodine_ug",
                "K_mg",
                "Mg_mg",
                "flags",
                "notes",
            ],
            [
                "Test",
                "Basic",
                "Generic",
                "5",
                "2",
                "10",
                "1",
                "3",
                "0.5",
                "10",
                "0",
                "0",
                "1",
                "0",
                "50",
                "10",
                "",
                "No flags",
            ],
        ]

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        writer = csv.writer(temp_file)
        writer.writerows(csv_data)
        temp_file.close()

        try:
            manager = ProductVarietiesManager(temp_file.name)
            varieties = manager.get_varieties("Test")
            assert len(varieties) == 1
            assert len(varieties[0].flags) == 0

        finally:
            Path(temp_file.name).unlink()

    def test_edge_cases_missing_values(self):
        """Test handling of missing values in CSV."""
        csv_data = [
            [
                "name",
                "variety",
                "brand",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "sugar_g",
                "Fe_mg",
                "Ca_mg",
                "VitD_IU",
                "B12_ug",
                "Folate_ug",
                "Iodine_ug",
                "K_mg",
                "Mg_mg",
                "flags",
                "notes",
            ],
            [
                "Test",
                "Minimal",
                "Basic",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "",
                "",
            ],
        ]

        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv")
        writer = csv.writer(temp_file)
        writer.writerows(csv_data)
        temp_file.close()

        try:
            manager = ProductVarietiesManager(temp_file.name)
            varieties = manager.get_varieties("Test")
            assert len(varieties) == 1
            variety = varieties[0]
            # All values should be 0
            assert variety.protein_g == 0.0
            assert variety.fat_g == 0.0
            assert variety.carbs_g == 0.0

        finally:
            Path(temp_file.name).unlink()


class TestProductVarietiesManagerAdditionalCoverage:
    """Additional tests to cover remaining missing lines."""

    def test_load_varieties_error_handling(self):
        """Test error handling during varieties loading - covers lines 175-176."""
        with patch("builtins.open", side_effect=OSError("File not found")):
            manager = ProductVarietiesManager("nonexistent.csv")
            # Manager should handle the error gracefully
            assert manager.varieties == {}

    def test_recommend_variety_with_low_sugar_preference(self):
        """Test variety recommendation with low sugar preference - covers line 307."""
        manager = ProductVarietiesManager()

        # Create varieties with different sugar content
        high_sugar = ProductVariety(
            name="Apple",
            variety="High Sugar",
            brand="Test",
            protein_g=0.5,
            fat_g=0.2,
            carbs_g=15.0,
            fiber_g=2.0,
            sugar_g=15.0,  # High sugar
            Fe_mg=0.1,
            Ca_mg=5.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=2.0,
            Iodine_ug=0.0,
            K_mg=100.0,
            Mg_mg=4.0,
            flags=set(),
            notes="High sugar variety",
        )

        low_sugar = ProductVariety(
            name="Apple",
            variety="Low Sugar",
            brand="Test",
            protein_g=0.5,
            fat_g=0.2,
            carbs_g=10.0,
            fiber_g=2.0,
            sugar_g=3.0,  # Low sugar (< 5g)
            Fe_mg=0.1,
            Ca_mg=5.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=2.0,
            Iodine_ug=0.0,
            K_mg=100.0,
            Mg_mg=4.0,
            flags=set(),
            notes="Low sugar variety",
        )

        manager.varieties["Apple"] = [high_sugar, low_sugar]

        # Request with low sugar preference
        user_prefs = {"low_sugar": True}
        recommended = manager.recommend_variety("Apple", user_prefs)

        assert recommended.variety == "Low Sugar"
        assert recommended.sugar_g == 3.0

    def test_recommend_variety_with_low_fat_preference(self):
        """Test variety recommendation with low fat preference - covers lines 311-313."""
        manager = ProductVarietiesManager()

        high_fat = ProductVariety(
            name="Cheese",
            variety="Full Fat",
            brand="Test",
            protein_g=25.0,
            fat_g=35.0,
            carbs_g=1.0,
            fiber_g=0.0,  # High fat
            sugar_g=1.0,
            Fe_mg=0.1,
            Ca_mg=700.0,
            VitD_IU=0.0,
            B12_ug=1.0,
            Folate_ug=5.0,
            Iodine_ug=0.0,
            K_mg=100.0,
            Mg_mg=25.0,
            flags=set(),
            notes="High fat variety",
        )

        low_fat = ProductVariety(
            name="Cheese",
            variety="Low Fat",
            brand="Test",
            protein_g=30.0,
            fat_g=2.0,
            carbs_g=2.0,
            fiber_g=0.0,  # Low fat (< 5g)
            sugar_g=2.0,
            Fe_mg=0.1,
            Ca_mg=700.0,
            VitD_IU=0.0,
            B12_ug=1.0,
            Folate_ug=5.0,
            Iodine_ug=0.0,
            K_mg=100.0,
            Mg_mg=25.0,
            flags=set(),
            notes="Low fat variety",
        )

        manager.varieties["Cheese"] = [high_fat, low_fat]

        user_prefs = {"low_fat": True}
        recommended = manager.recommend_variety("Cheese", user_prefs)

        assert recommended.variety == "Low Fat"
        assert recommended.fat_g == 2.0

    def test_recommend_variety_with_high_protein_preference(self):
        """Test variety recommendation with high protein preference - covers lines 317-319."""
        manager = ProductVarietiesManager()

        low_protein = ProductVariety(
            name="Beans",
            variety="Regular",
            brand="Test",
            protein_g=8.0,
            fat_g=1.0,
            carbs_g=20.0,
            fiber_g=8.0,  # Low protein
            sugar_g=2.0,
            Fe_mg=2.0,
            Ca_mg=40.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=150.0,
            Iodine_ug=0.0,
            K_mg=600.0,
            Mg_mg=60.0,
            flags={"VEG"},
            notes="Regular protein variety",
        )

        high_protein = ProductVariety(
            name="Beans",
            variety="Protein Plus",
            brand="Test",
            protein_g=25.0,
            fat_g=1.5,
            carbs_g=18.0,
            fiber_g=10.0,  # High protein (> 20g)
            sugar_g=1.0,
            Fe_mg=3.0,
            Ca_mg=50.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=200.0,
            Iodine_ug=0.0,
            K_mg=700.0,
            Mg_mg=80.0,
            flags={"VEG"},
            notes="High protein variety",
        )

        manager.varieties["Beans"] = [low_protein, high_protein]

        user_prefs = {"high_protein": True}
        recommended = manager.recommend_variety("Beans", user_prefs)

        assert recommended.variety == "Protein Plus"
        assert recommended.protein_g == 25.0

    def test_recommend_variety_with_gluten_free_preference(self):
        """Test variety recommendation with gluten free preference - covers lines 329->332."""
        manager = ProductVarietiesManager()

        regular_bread = ProductVariety(
            name="Bread",
            variety="Wheat",
            brand="Test",
            protein_g=8.0,
            fat_g=2.0,
            carbs_g=50.0,
            fiber_g=3.0,
            sugar_g=3.0,
            Fe_mg=2.0,
            Ca_mg=80.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=50.0,
            Iodine_ug=0.0,
            K_mg=150.0,
            Mg_mg=25.0,
            flags=set(),
            notes="Regular wheat bread",  # No GF flag
        )

        gf_bread = ProductVariety(
            name="Bread",
            variety="Gluten Free",
            brand="Test",
            protein_g=6.0,
            fat_g=3.0,
            carbs_g=45.0,
            fiber_g=4.0,
            sugar_g=2.0,
            Fe_mg=1.5,
            Ca_mg=60.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=30.0,
            Iodine_ug=0.0,
            K_mg=120.0,
            Mg_mg=20.0,
            flags={"GF"},
            notes="Gluten free bread",  # Has GF flag
        )

        manager.varieties["Bread"] = [regular_bread, gf_bread]

        user_prefs = {"gluten_free": True}
        recommended = manager.recommend_variety("Bread", user_prefs)

        assert recommended.variety == "Gluten Free"
        assert "GF" in recommended.flags

    def test_recommend_variety_fallback_when_no_match(self):
        """Test fallback to first variety when no preferences match - covers line 333."""
        manager = ProductVarietiesManager()

        only_variety = ProductVariety(
            name="Exotic Fruit",
            variety="Rare",
            brand="Test",
            protein_g=1.0,
            fat_g=0.5,
            carbs_g=20.0,
            fiber_g=5.0,
            sugar_g=15.0,
            Fe_mg=0.5,
            Ca_mg=20.0,
            VitD_IU=0.0,
            B12_ug=0.0,
            Folate_ug=10.0,
            Iodine_ug=0.0,
            K_mg=200.0,
            Mg_mg=10.0,
            flags=set(),
            notes="Rare exotic fruit",  # No special flags
        )

        manager.varieties["Exotic Fruit"] = [only_variety]

        # Request with preferences that don't match
        user_prefs = {"gluten_free": True, "low_sugar": True, "high_protein": True}
        recommended = manager.recommend_variety("Exotic Fruit", user_prefs)

        # Should return the only available variety as fallback
        assert recommended.variety == "Rare"
        assert recommended.name == "Exotic Fruit"

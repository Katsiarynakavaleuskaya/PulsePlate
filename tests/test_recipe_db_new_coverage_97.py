"""Tests to boost coverage for core/recipe_db_new.py to 97%."""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import patch, MagicMock, mock_open
from core.recipe_db_new import RecipeDB, Recipe


class TestRecipeDBCoverage97:
    """Test class for RecipeDB coverage boost."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock recipe data
        self.mock_recipes = [
            Recipe(
                name="Test Recipe 1",
                meal="breakfast",
                tags=["VEG", "GF"],
                ingredients={"food1": 100.0, "food2": 50.0},
            ),
            Recipe(name="Test Recipe 2", meal="lunch", tags=["OMNI"], ingredients={"food3": 200.0}),
        ]

        # Mock nutrition data
        self.mock_nutrition = {
            "kcal": 300.0,
            "macros": {"protein": 15.0, "carbs": 45.0, "fat": 10.0},
            "micros": {"fiber": 5.0},
        }

    def test_compatible_veg_omni_line_75(self):
        """Test line 75: VEG diet with OMNI recipe - should be incompatible."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,OMNI"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        recipe_flags = ["OMNI"]
        diet_flags = ["VEG"]
        result = db._compatible(recipe_flags, diet_flags)
        assert result is False

    def test_compatible_pesc_omni_line_77(self):
        """Test line 77: PESC diet with OMNI recipe - should be incompatible."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,OMNI"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        recipe_flags = ["OMNI"]
        diet_flags = ["PESC"]
        result = db._compatible(recipe_flags, diet_flags)
        assert result is False

    def test_compatible_gf_missing_line_79(self):
        """Test line 79: GF diet with non-GF recipe - should be incompatible."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        recipe_flags = ["VEG"]  # No GF tag
        diet_flags = ["GF"]
        result = db._compatible(recipe_flags, diet_flags)
        assert result is False

    def test_compatible_gf_present_line_79(self):
        """Test line 79: GF diet with GF recipe - should be compatible."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG;GF"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        recipe_flags = ["VEG", "GF"]  # Has GF tag
        diet_flags = ["GF"]
        result = db._compatible(recipe_flags, diet_flags)
        assert result is True

    def test_get_recipe_by_id_invalid_type_line_120(self):
        """Test line 120: get_recipe_by_id with invalid recipe_id type."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test with string that can't be converted to int
        result = db.get_recipe_by_id("invalid_id")
        assert result is None

    def test_scale_recipe_zero_kcal_line_166(self):
        """Test line 166: scale_recipe with zero base kcal."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        recipe = self.mock_recipes[0]

        with patch.object(db, "_nutrition_for") as mock_nutrition:
            # First call returns zero kcal
            mock_nutrition.return_value = {"kcal": 0.0, "macros": {}, "micros": {}}

            with patch("core.recipe_db_new.translate_recipe", return_value="Translated Recipe"):
                # Pass an int for kcal_goal to match the function signature
                result = db.scale_recipe_to_kcal(recipe, 500, "en")

                # Should handle zero kcal case
                assert result is not None
                # Should call _nutrition_for at least once
                assert mock_nutrition.called

    def test_scale_recipe_kcal_correction_line_177(self):
        """Test line 177: scale_recipe with kcal correction when off by >5%."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        recipe = self.mock_recipes[0]

        with patch.object(db, "_nutrition_for") as mock_nutrition:
            # First call returns base nutrition
            # Second call returns nutrition that's off by >5%
            # Third call returns corrected nutrition
            mock_nutrition.side_effect = [
                {
                    "kcal": 300.0,
                    "macros": {"protein": 15.0, "carbs": 45.0, "fat": 10.0},
                    "micros": {"fiber": 5.0},
                },  # base
                {
                    "kcal": 200.0,
                    "macros": {"protein": 10.0, "carbs": 30.0, "fat": 7.0},
                    "micros": {"fiber": 3.0},
                },  # after scaling (off by >5%)
                {
                    "kcal": 500.0,
                    "macros": {"protein": 25.0, "carbs": 75.0, "fat": 17.0},
                    "micros": {"fiber": 8.0},
                },  # after correction
            ]

            with patch("core.recipe_db_new.translate_recipe", return_value="Translated Recipe"):
                # Pass an int for kcal_goal to match the function signature
                result = db.scale_recipe_to_kcal(recipe, 500, "en")

                # Should handle kcal correction
                assert result is not None
                # Should call _nutrition_for multiple times for correction
                assert mock_nutrition.call_count >= 3

    def test_scale_recipe_kcal_correction_line_178(self):
        """Test line 178: scale_recipe with second alpha calculation."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        recipe = self.mock_recipes[0]

        with patch.object(db, "_nutrition_for") as mock_nutrition:
            # Simulate case where we need correction
            mock_nutrition.side_effect = [
                {
                    "kcal": 300.0,
                    "macros": {"protein": 15.0, "carbs": 45.0, "fat": 10.0},
                    "micros": {"fiber": 5.0},
                },  # base
                {
                    "kcal": 200.0,
                    "macros": {"protein": 10.0, "carbs": 30.0, "fat": 7.0},
                    "micros": {"fiber": 3.0},
                },  # after scaling (off by >5%)
                {
                    "kcal": 500.0,
                    "macros": {"protein": 25.0, "carbs": 75.0, "fat": 17.0},
                    "micros": {"fiber": 8.0},
                },  # after correction
            ]

            with patch("core.recipe_db_new.translate_recipe", return_value="Translated Recipe"):
                result = db.scale_recipe_to_kcal(recipe, 500, "en")

                # Should apply second alpha correction
                assert result is not None

                # Verify the correction path was taken
                assert mock_nutrition.call_count >= 3

    def test_get_recipe_by_name_line_111(self):
        """Test line 111: get_recipe_by_id with name lookup."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test lookup by name
        result = db.get_recipe_by_id("Test Recipe")
        assert result is not None
        assert result.name == "Test Recipe"

    def test_search_recipes_with_query_line_131(self):
        """Test line 131: search_recipes with query normalization."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test search with query
        results = db.search_recipes("test")
        assert len(results) == 1
        assert results[0].name == "Test Recipe"

    def test_search_recipes_with_tags_line_132(self):
        """Test line 132: search_recipes with tag filtering."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test search with tags
        results = db.search_recipes(tags=["VEG"])
        assert len(results) == 1
        assert results[0].name == "Test Recipe"

    def test_search_recipes_with_limit_line_145(self):
        """Test line 145: search_recipes with limit."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe 1,breakfast,food1:100.0,VEG\nTest Recipe 2,lunch,food2:200.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test search with limit
        results = db.search_recipes(limit=1)
        assert len(results) == 1

    def test_get_all_recipes_line_151(self):
        """Test line 151: get_all_recipes returns copy."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test get_all_recipes
        results = db.get_all_recipes()
        assert len(results) == 1
        assert results[0].name == "Test Recipe"
        # Should return a copy, not the original list
        assert results is not db.recipes

    def test_pick_base_recipe_fallback_line_70_71(self):
        """Test pick_base_recipe fallback logic lines 70-71."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nVeggie Salad,lunch,lettuce:100.0,VEG\nChicken Salad,dinner,chicken:200.0,OMNI"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test fallback when no candidates for target meal
        result = db.pick_base_recipe(["VEG"], 1)  # lunch index, but only VEG available
        assert result is not None
        assert "VEG" in result.tags

    def test_nutrition_calculation_line_84_97(self):
        """Test _nutrition_for method lines 84-97."""
        mock_fooddb = MagicMock()
        mock_food = MagicMock()
        mock_food.per_g = 100.0
        mock_food.protein_g = 10.0
        mock_food.carbs_g = 20.0
        mock_food.fat_g = 5.0
        mock_food.fiber_g = 3.0
        mock_food.micros = {"Fe_mg": 50.0, "Ca_mg": 2.0}
        mock_fooddb.get_food.return_value = mock_food

        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        nutrition = db._nutrition_for({"test_food": 200.0})
        assert nutrition["kcal"] > 0
        assert nutrition["macros"]["protein_g"] > 0
        assert nutrition["micros"]["Fe_mg"] > 0

    def test_get_recipe_by_id_valid_index_line_118_119(self):
        """Test get_recipe_by_id with valid index lines 118-119."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        result = db.get_recipe_by_id(0)
        assert result is not None
        assert result.name == "Test Recipe"

    def test_search_recipes_query_filter_line_135(self):
        """Test search_recipes with query filter line 135."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nApple Pie,dessert,apple:100.0,SWEET\nBanana Bread,breakfast,banana:100.0,SWEET"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test query filter
        results = db.search_recipes("Apple")
        assert len(results) == 1
        assert results[0].name == "Apple Pie"

    def test_search_recipes_tag_filter_line_139(self):
        """Test search_recipes with tag filter line 139."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nVeggie Salad,lunch,lettuce:100.0,VEG\nChicken Salad,lunch,chicken:100.0,OMNI"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test tag filter
        results = db.search_recipes(tags=["VEG"])
        assert len(results) == 1
        assert results[0].name == "Veggie Salad"

    def test_search_recipes_no_matches_line_136(self):
        """Test search_recipes with no matches line 136."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nApple Pie,dessert,apple:100.0,SWEET"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test no matches
        results = db.search_recipes("Orange")
        assert len(results) == 0

    def test_pick_base_recipe_no_candidates_line_71(self):
        """Test pick_base_recipe when no candidates available line 71."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nChicken Salad,lunch,chicken:100.0,OMNI"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test when no compatible recipes exist
        result = db.pick_base_recipe(["VEG"], 0)  # breakfast index, but only OMNI available
        assert result is None

    def test_get_recipe_by_id_out_of_bounds_line_120(self):
        """Test get_recipe_by_id with out of bounds index line 120."""
        mock_fooddb = MagicMock()
        csv_content = "name,meal,ingredients,tags\nTest Recipe,breakfast,food1:100.0,VEG"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            db = RecipeDB("test.csv", mock_fooddb)

        # Test out of bounds index
        result = db.get_recipe_by_id(5)  # Only 1 recipe (index 0), so 5 is out of bounds
        assert result is None

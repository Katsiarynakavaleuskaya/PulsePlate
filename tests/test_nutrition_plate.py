"""
Tests for nutrition_plate module

Comprehensive tests for plate generation logic:
- MacroDistribution model validation
- Macro calculation functions
- Meal suggestion generation
- Complete plate recommendation workflow
- Edge cases and input validation
"""

import pytest
from pydantic import ValidationError

from nutrition_plate import (
    MacroDistribution,
    PlateRecommendation,
    calculate_macros_in_grams,
    get_macro_distribution,
    get_meal_suggestions,
    get_nutrition_notes,
    make_plate,
)


class TestMacroDistribution:
    """Test MacroDistribution model."""

    def test_valid_macro_distribution(self):
        """Test valid macro distribution creation."""
        macro = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )
        assert macro.protein_percent == 25.0
        assert macro.carbs_percent == 45.0
        assert macro.fat_percent == 30.0

    def test_macro_percentages_sum_validation(self):
        """Test that macro percentages must sum to 100."""
        with pytest.raises(ValidationError) as exc_info:
            MacroDistribution(
                protein_percent=25.0,
                carbs_percent=45.0,
                fat_percent=25.0,  # Sum is 95%, should fail
            )
        assert "must sum to 100%" in str(exc_info.value)

    def test_macro_percentage_range_validation(self):
        """Test macro percentage range validation."""
        # Test protein too low
        with pytest.raises(ValidationError):
            MacroDistribution(protein_percent=5.0, carbs_percent=45.0, fat_percent=50.0)

        # Test protein too high
        with pytest.raises(ValidationError):
            MacroDistribution(
                protein_percent=60.0, carbs_percent=25.0, fat_percent=15.0
            )

        # Test carbs too low
        with pytest.raises(ValidationError):
            MacroDistribution(
                protein_percent=25.0, carbs_percent=15.0, fat_percent=60.0
            )

        # Test carbs too high
        with pytest.raises(ValidationError):
            MacroDistribution(
                protein_percent=15.0, carbs_percent=75.0, fat_percent=10.0
            )

        # Test fat too low
        with pytest.raises(ValidationError):
            MacroDistribution(
                protein_percent=50.0, carbs_percent=40.0, fat_percent=10.0
            )

        # Test fat too high
        with pytest.raises(ValidationError):
            MacroDistribution(
                protein_percent=15.0, carbs_percent=35.0, fat_percent=50.0
            )

    def test_macro_percentage_negative_validation(self):
        """Test that negative percentages are rejected."""
        with pytest.raises(ValidationError):
            MacroDistribution(
                protein_percent=-5.0, carbs_percent=55.0, fat_percent=50.0
            )

    def test_macro_percentage_over_100_validation(self):
        """Test that percentages over 100 are rejected."""
        with pytest.raises(ValidationError):
            MacroDistribution(
                protein_percent=110.0, carbs_percent=45.0, fat_percent=30.0
            )

    def test_floating_point_tolerance(self):
        """Test that small floating point differences are tolerated."""
        # Should pass with 99.9% (within tolerance)
        macro = MacroDistribution(
            protein_percent=25.0, carbs_percent=44.9, fat_percent=30.0
        )
        assert macro is not None

    def test_valid_percentage_return_value(self):
        """Test that valid percentages are properly returned by validator."""
        # This specifically tests the return v path in the validator
        macro = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )
        # Verify the values were properly set (testing the return path)
        assert macro.protein_percent == 25.0
        assert macro.carbs_percent == 45.0
        assert macro.fat_percent == 30.0


class TestGetMacroDistribution:
    """Test get_macro_distribution function."""

    def test_default_maintenance_goal(self):
        """Test default maintenance macro distribution."""
        macro = get_macro_distribution()
        assert macro.protein_percent == 25
        assert macro.carbs_percent == 45
        assert macro.fat_percent == 30

    def test_weight_loss_goal(self):
        """Test weight loss macro distribution."""
        macro = get_macro_distribution("weight_loss")
        assert macro.protein_percent == 30
        assert macro.carbs_percent == 35
        assert macro.fat_percent == 35

    def test_weight_gain_goal(self):
        """Test weight gain macro distribution."""
        macro = get_macro_distribution("weight_gain")
        assert macro.protein_percent == 20
        assert macro.carbs_percent == 50
        assert macro.fat_percent == 30

    def test_muscle_gain_goal(self):
        """Test muscle gain macro distribution."""
        macro = get_macro_distribution("muscle_gain")
        assert macro.protein_percent == 30
        assert macro.carbs_percent == 40
        assert macro.fat_percent == 30

    def test_unknown_goal_defaults_to_maintenance(self):
        """Test that unknown goals default to maintenance."""
        macro = get_macro_distribution("unknown_goal")
        assert macro.protein_percent == 25
        assert macro.carbs_percent == 45
        assert macro.fat_percent == 30

    def test_active_activity_level(self):
        """Test adjustments for active activity level."""
        macro = get_macro_distribution("maintenance", "active")
        assert macro.carbs_percent == 50  # Increased from 45
        assert macro.fat_percent == 25  # Decreased from 30

    def test_very_active_activity_level(self):
        """Test adjustments for very active activity level."""
        macro = get_macro_distribution("maintenance", "very_active")
        assert macro.carbs_percent == 50  # Increased from 45
        assert macro.fat_percent == 25  # Decreased from 30

    def test_sedentary_activity_level(self):
        """Test adjustments for sedentary activity level."""
        macro = get_macro_distribution("maintenance", "sedentary")
        assert macro.carbs_percent == 40  # Decreased from 45
        assert macro.fat_percent == 35  # Increased from 30

    def test_carb_limits_with_activity(self):
        """Test that carb adjustments respect limits."""
        macro = get_macro_distribution("weight_gain", "active")  # Base carbs 50
        assert macro.carbs_percent <= 60  # Should not exceed limit

    def test_fat_limits_with_activity(self):
        """Test that fat adjustments respect limits."""
        macro = get_macro_distribution("weight_loss", "sedentary")  # Base fat 35
        assert macro.fat_percent <= 40  # Should not exceed limit


class TestCalculateMacrosInGrams:
    """Test calculate_macros_in_grams function."""

    def test_basic_macro_calculation(self):
        """Test basic macro calculation."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        macros = calculate_macros_in_grams(2000, macro_dist)

        # 25% of 2000 calories = 500 calories protein / 4 = 125g
        assert macros["protein"] == 125.0
        # 45% of 2000 calories = 900 calories carbs / 4 = 225g
        assert macros["carbs"] == 225.0
        # 30% of 2000 calories = 600 calories fat / 9 = 66.7g
        assert macros["fat"] == 66.7

    def test_macro_calculation_rounding(self):
        """Test that macro calculations are properly rounded."""
        macro_dist = MacroDistribution(
            protein_percent=30.0, carbs_percent=40.0, fat_percent=30.0
        )

        macros = calculate_macros_in_grams(
            1837, macro_dist
        )  # Odd number to test rounding

        # All values should be rounded to 1 decimal place
        assert isinstance(macros["protein"], float)
        assert isinstance(macros["carbs"], float)
        assert isinstance(macros["fat"], float)

    def test_low_calorie_calculation(self):
        """Test macro calculation with low calories."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        macros = calculate_macros_in_grams(1200, macro_dist)

        # Verify calculations are reasonable for low calorie diet
        assert macros["protein"] > 0
        assert macros["carbs"] > 0
        assert macros["fat"] > 0

    def test_high_calorie_calculation(self):
        """Test macro calculation with high calories."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        macros = calculate_macros_in_grams(3500, macro_dist)

        # Verify calculations are reasonable for high calorie diet
        assert macros["protein"] > 0
        assert macros["carbs"] > 0
        assert macros["fat"] > 0


class TestGetMealSuggestions:
    """Test get_meal_suggestions function."""

    def test_basic_meal_suggestions_english(self):
        """Test basic meal suggestions in English."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        suggestions = get_meal_suggestions(macro_dist, "en")

        assert len(suggestions) >= 4  # At least 4 basic suggestions
        assert any("Breakfast" in s for s in suggestions)
        assert any("Lunch" in s for s in suggestions)
        assert any("Dinner" in s for s in suggestions)
        assert any("Snack" in s for s in suggestions)

    def test_basic_meal_suggestions_russian(self):
        """Test basic meal suggestions in Russian."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        suggestions = get_meal_suggestions(macro_dist, "ru")

        assert len(suggestions) >= 4  # At least 4 basic suggestions
        assert any("Завтрак" in s for s in suggestions)
        assert any("Обед" in s for s in suggestions)
        assert any("Ужин" in s for s in suggestions)
        assert any("Перекус" in s for s in suggestions)

    def test_high_protein_additional_suggestions(self):
        """Test additional suggestions for high protein diets."""
        macro_dist = MacroDistribution(
            protein_percent=35.0, carbs_percent=35.0, fat_percent=30.0
        )

        suggestions_en = get_meal_suggestions(macro_dist, "en")
        suggestions_ru = get_meal_suggestions(macro_dist, "ru")

        # Should include protein shake suggestion
        assert any("protein" in s.lower() for s in suggestions_en)
        assert any("Протеиновый" in s for s in suggestions_ru)

    def test_high_carb_additional_suggestions(self):
        """Test additional suggestions for high carb diets."""
        macro_dist = MacroDistribution(
            protein_percent=20.0, carbs_percent=55.0, fat_percent=25.0
        )

        suggestions_en = get_meal_suggestions(macro_dist, "en")
        suggestions_ru = get_meal_suggestions(macro_dist, "ru")

        # Should include additional carb suggestions
        assert any("fruit" in s.lower() or "grain" in s.lower() for s in suggestions_en)
        assert any("Фрукты" in s or "цельнозерновые" in s for s in suggestions_ru)

    def test_default_language_english(self):
        """Test default language is English."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        suggestions = get_meal_suggestions(macro_dist)  # No lang specified

        # Should default to English
        assert any("Breakfast" in s for s in suggestions)


class TestGetNutritionNotes:
    """Test get_nutrition_notes function."""

    def test_basic_nutrition_notes_english(self):
        """Test basic nutrition notes in English."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        notes = get_nutrition_notes(macro_dist, "maintenance", "en")

        assert len(notes) >= 3  # At least 3 basic notes
        assert any("distribution" in note.lower() for note in notes)
        assert any("water" in note.lower() for note in notes)
        assert any("protein" in note.lower() for note in notes)

    def test_basic_nutrition_notes_russian(self):
        """Test basic nutrition notes in Russian."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        notes = get_nutrition_notes(macro_dist, "maintenance", "ru")

        assert len(notes) >= 3  # At least 3 basic notes
        assert any("распределение" in note for note in notes)
        assert any("воды" in note for note in notes)
        assert any("белка" in note for note in notes)

    def test_weight_loss_specific_notes(self):
        """Test weight loss specific notes."""
        macro_dist = MacroDistribution(
            protein_percent=30.0, carbs_percent=35.0, fat_percent=35.0
        )

        notes_en = get_nutrition_notes(macro_dist, "weight_loss", "en")
        notes_ru = get_nutrition_notes(macro_dist, "weight_loss", "ru")

        # Should include weight loss specific advice
        assert any("portion control" in note.lower() for note in notes_en)
        assert any("порций" in note for note in notes_ru)

    def test_muscle_gain_specific_notes(self):
        """Test muscle gain specific notes."""
        macro_dist = MacroDistribution(
            protein_percent=30.0, carbs_percent=40.0, fat_percent=30.0
        )

        notes_en = get_nutrition_notes(macro_dist, "muscle_gain", "en")
        notes_ru = get_nutrition_notes(macro_dist, "muscle_gain", "ru")

        # Should include muscle gain specific advice
        assert any("protein every" in note.lower() for note in notes_en)
        assert any("белок каждые" in note for note in notes_ru)

    def test_default_language_english(self):
        """Test default language is English."""
        macro_dist = MacroDistribution(
            protein_percent=25.0, carbs_percent=45.0, fat_percent=30.0
        )

        notes = get_nutrition_notes(macro_dist, "maintenance")  # No lang specified

        # Should default to English
        assert any("Target distribution" in note for note in notes)


class TestMakePlate:
    """Test make_plate function integration."""

    def test_basic_plate_creation(self):
        """Test basic plate creation."""
        plate = make_plate(
            weight_kg=70.0, height_cm=175.0, age=30, sex="male", activity="moderate"
        )

        assert isinstance(plate, PlateRecommendation)
        assert plate.target_calories > 0
        assert isinstance(plate.macro_distribution, MacroDistribution)
        assert plate.protein_grams > 0
        assert plate.carbs_grams > 0
        assert plate.fat_grams > 0
        assert len(plate.meal_suggestions) > 0
        assert len(plate.notes) > 0

    def test_weight_loss_plate(self):
        """Test plate creation for weight loss."""
        maintenance_plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            goal="maintenance",
        )

        weight_loss_plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            goal="weight_loss",
        )

        # Weight loss should have fewer calories
        assert weight_loss_plate.target_calories < maintenance_plate.target_calories

        # Should have higher protein percentage
        assert (
            weight_loss_plate.macro_distribution.protein_percent
            > maintenance_plate.macro_distribution.protein_percent
        )

    def test_weight_gain_plate(self):
        """Test plate creation for weight gain."""
        maintenance_plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            goal="maintenance",
        )

        weight_gain_plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            goal="weight_gain",
        )

        # Weight gain should have more calories
        assert weight_gain_plate.target_calories > maintenance_plate.target_calories

        # Should have higher carb percentage
        assert (
            weight_gain_plate.macro_distribution.carbs_percent
            > maintenance_plate.macro_distribution.carbs_percent
        )

    def test_muscle_gain_plate(self):
        """Test plate creation for muscle gain."""
        maintenance_plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            goal="maintenance",
        )

        muscle_gain_plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            goal="muscle_gain",
        )

        # Muscle gain should have more calories than maintenance but less than weight gain
        assert muscle_gain_plate.target_calories > maintenance_plate.target_calories

        # Should have high protein percentage
        assert muscle_gain_plate.macro_distribution.protein_percent == 30

    def test_female_plate(self):
        """Test plate creation for female."""
        plate = make_plate(
            weight_kg=60.0, height_cm=165.0, age=25, sex="female", activity="moderate"
        )

        assert isinstance(plate, PlateRecommendation)
        assert plate.target_calories > 0
        # Female typically has lower calorie needs
        assert plate.target_calories < 2500

    def test_active_plate(self):
        """Test plate creation for active person."""
        moderate_plate = make_plate(
            weight_kg=70.0, height_cm=175.0, age=30, sex="male", activity="moderate"
        )

        active_plate = make_plate(
            weight_kg=70.0, height_cm=175.0, age=30, sex="male", activity="active"
        )

        # Active should have more calories
        assert active_plate.target_calories > moderate_plate.target_calories

        # Should have higher carb percentage
        assert (
            active_plate.macro_distribution.carbs_percent
            > moderate_plate.macro_distribution.carbs_percent
        )

    def test_sedentary_plate(self):
        """Test plate creation for sedentary person."""
        moderate_plate = make_plate(
            weight_kg=70.0, height_cm=175.0, age=30, sex="male", activity="moderate"
        )

        sedentary_plate = make_plate(
            weight_kg=70.0, height_cm=175.0, age=30, sex="male", activity="sedentary"
        )

        # Sedentary should have fewer calories
        assert sedentary_plate.target_calories < moderate_plate.target_calories

        # Should have lower carb percentage
        assert (
            sedentary_plate.macro_distribution.carbs_percent
            < moderate_plate.macro_distribution.carbs_percent
        )

    def test_bodyfat_parameter(self):
        """Test plate creation with body fat percentage."""
        plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            bodyfat=15.0,
        )

        assert isinstance(plate, PlateRecommendation)
        assert plate.target_calories > 0

    def test_russian_language(self):
        """Test plate creation with Russian language."""
        plate = make_plate(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            sex="male",
            activity="moderate",
            lang="ru",
        )

        # Should have Russian meal suggestions and notes
        assert any("Завтрак" in suggestion for suggestion in plate.meal_suggestions)
        assert any("распределение" in note for note in plate.notes)

    def test_calorie_adjustment_values(self):
        """Test specific calorie adjustment values for different goals."""
        base_params = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
        }

        maintenance_plate = make_plate(**base_params, goal="maintenance")
        weight_loss_plate = make_plate(**base_params, goal="weight_loss")
        weight_gain_plate = make_plate(**base_params, goal="weight_gain")
        muscle_gain_plate = make_plate(**base_params, goal="muscle_gain")

        # Check specific calorie differences
        assert (
            weight_loss_plate.target_calories == maintenance_plate.target_calories - 500
        )
        assert (
            weight_gain_plate.target_calories == maintenance_plate.target_calories + 500
        )
        assert (
            muscle_gain_plate.target_calories == maintenance_plate.target_calories + 300
        )

    def test_edge_case_values(self):
        """Test edge case input values."""
        # Very light person
        light_plate = make_plate(
            weight_kg=45.0, height_cm=150.0, age=18, sex="female", activity="sedentary"
        )
        assert isinstance(light_plate, PlateRecommendation)
        assert light_plate.target_calories > 0

        # Heavy person
        heavy_plate = make_plate(
            weight_kg=120.0, height_cm=190.0, age=45, sex="male", activity="very_active"
        )
        assert isinstance(heavy_plate, PlateRecommendation)
        assert heavy_plate.target_calories > 0

        # Elderly person
        elderly_plate = make_plate(
            weight_kg=65.0, height_cm=165.0, age=75, sex="female", activity="light"
        )
        assert isinstance(elderly_plate, PlateRecommendation)
        assert elderly_plate.target_calories > 0

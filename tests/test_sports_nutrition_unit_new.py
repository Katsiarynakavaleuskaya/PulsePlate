"""
Comprehensive tests for core.sports_nutrition module
Designed for maximum coverage of 350+ lines with minimal test code
"""

import math
import pytest
from unittest.mock import Mock
import core.sports_nutrition as sn


# --- Mock UserProfile for testing ---
def create_mock_profile(weight_kg=70.0, goal="maintain"):
    """Create a mock UserProfile for testing"""
    profile = Mock()
    profile.weight_kg = weight_kg
    profile.goal = goal
    return profile


# --- Constants/Data Structures Tests ---
def test_constants_exist_and_non_empty():
    """Test that all major constants are properly defined"""
    # Check SportCategory enum
    assert hasattr(sn, "SportCategory")
    categories = [e.value for e in sn.SportCategory]
    assert len(categories) == 7
    assert "endurance" in categories
    assert "strength" in categories

    # Check TrainingPhase enum
    assert hasattr(sn, "TrainingPhase")
    phases = [e.value for e in sn.TrainingPhase]
    assert len(phases) == 5
    assert "in_season" in phases

    # Check calculator constants
    calc = sn.SportsNutritionCalculator
    assert hasattr(calc, "SPORT_PROTEIN_REQUIREMENTS")
    assert hasattr(calc, "SPORT_CARB_REQUIREMENTS")
    assert hasattr(calc, "HYDRATION_GUIDELINES")
    assert len(calc.SPORT_PROTEIN_REQUIREMENTS) == 7
    assert len(calc.SPORT_CARB_REQUIREMENTS) == 7
    assert len(calc.HYDRATION_GUIDELINES) == 7

    # Check sport mapping
    assert hasattr(sn, "SPORT_MAPPING")
    assert len(sn.SPORT_MAPPING) > 10
    assert "running" in sn.SPORT_MAPPING


# --- Main Function Tests with Comprehensive Coverage ---
@pytest.mark.parametrize(
    "sport_name,phase_name,weight,goal",
    [
        ("endurance", "in_season", 70.0, "maintain"),
        ("strength", "peak", 82.0, "gain"),
        ("power", "off_season", 68.0, "loss"),
        ("team", "pre_season", 75.0, "maintain"),
        ("aesthetic", "recovery", 60.0, "loss"),
        ("combat", "in_season", 80.0, "maintain"),
        ("recreational", "in_season", 70.0, "gain"),
    ],
)
def test_get_sport_recommendations_comprehensive(sport_name, phase_name, weight, goal):
    """Test get_sport_recommendations for all sport categories and phases"""
    profile = create_mock_profile(weight_kg=weight, goal=goal)
    sport = sn.SportCategory(sport_name)
    phase = sn.TrainingPhase(phase_name)

    result = sn.get_sport_recommendations(
        profile=profile, sport=sport, training_phase=phase, training_hours_per_week=6.0
    )

    # Verify structure
    required_keys = [
        "sport_category",
        "training_phase",
        "daily_targets",
        "hydration",
        "timing",
        "supplements",
        "special_considerations",
        "disclaimer",
    ]
    for key in required_keys:
        assert key in result

    # Verify daily targets
    targets = result["daily_targets"]
    target_keys = [
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g",
        "protein_per_kg",
        "carbs_per_kg",
        "fat_per_kg",
    ]
    for key in target_keys:
        assert key in targets
        assert isinstance(targets[key], (int, float))
        assert targets[key] >= 0

    # Verify calorie calculation is reasonable
    protein_cal = targets["protein_g"] * 4
    carb_cal = targets["carbs_g"] * 4
    fat_cal = targets["fat_g"] * 9
    total_calculated = protein_cal + carb_cal + fat_cal
    assert 0.85 <= total_calculated / max(1.0, targets["calories"]) <= 1.15

    # Verify hydration section
    hydration = result["hydration"]
    assert "training_fluid_ml_per_hour" in hydration
    assert "electrolyte_replacement" in hydration
    assert isinstance(hydration["training_fluid_ml_per_hour"], int)
    assert isinstance(hydration["electrolyte_replacement"], bool)

    # Verify timing section
    timing = result["timing"]
    timing_keys = [
        "pre_workout_carbs_g",
        "post_workout_protein_g",
        "post_workout_carbs_g",
        "meal_frequency",
    ]
    for key in timing_keys:
        assert key in timing

    # Verify supplements section
    supplements = result["supplements"]
    assert "creatine_recommended" in supplements
    assert "caffeine_timing" in supplements
    assert isinstance(supplements["creatine_recommended"], bool)

    # Verify special considerations
    special = result["special_considerations"]
    assert "carb_loading_recommended" in special
    assert "weight_cutting_advice" in special


# --- Calculator Class Method Tests ---
def test_calculate_sports_targets_direct():
    """Test SportsNutritionCalculator.calculate_sports_targets directly"""
    profile = create_mock_profile(weight_kg=75.0, goal="gain")

    targets = sn.SportsNutritionCalculator.calculate_sports_targets(
        profile=profile,
        sport=sn.SportCategory.STRENGTH,
        training_phase=sn.TrainingPhase.IN_SEASON,
        training_hours_per_week=8.0,
    )

    # Verify SportsNutritionTargets dataclass
    assert hasattr(targets, "protein_g_per_kg")
    assert hasattr(targets, "carbs_g_per_kg")
    assert hasattr(targets, "fat_g_per_kg")
    assert hasattr(targets, "fluid_ml_per_hour_training")
    assert hasattr(targets, "electrolyte_replacement")
    assert hasattr(targets, "creatine_recommended")
    assert hasattr(targets, "meal_frequency")

    # Verify reasonable values
    assert 1.0 <= targets.protein_g_per_kg <= 3.0
    assert 2.0 <= targets.carbs_g_per_kg <= 12.0
    assert 0.5 <= targets.fat_g_per_kg <= 2.0
    assert 100 <= targets.fluid_ml_per_hour_training <= 800
    assert isinstance(targets.electrolyte_replacement, bool)
    assert isinstance(targets.creatine_recommended, bool)
    assert 3 <= targets.meal_frequency <= 7


# --- Training Volume Adjustment Tests ---
@pytest.mark.parametrize("hours_per_week", [0, 2, 5, 10, 15, 20])
def test_training_volume_adjustments(hours_per_week):
    """Test that training volume affects recommendations appropriately"""
    profile = create_mock_profile(weight_kg=70.0, goal="maintain")

    result = sn.get_sport_recommendations(
        profile=profile,
        sport=sn.SportCategory.ENDURANCE,
        training_phase=sn.TrainingPhase.IN_SEASON,
        training_hours_per_week=hours_per_week,
    )

    targets = result["daily_targets"]
    timing = result["timing"]

    # Higher training volume should generally mean higher intake
    assert targets["calories"] > 0
    assert targets["protein_g"] > 0
    assert targets["carbs_g"] > 0

    # Meal frequency should increase with training volume
    if hours_per_week > 10:
        assert timing["meal_frequency"] >= 5
    elif hours_per_week > 6:
        assert timing["meal_frequency"] >= 4
    else:
        assert timing["meal_frequency"] >= 3


# --- Phase Multiplier Tests ---
@pytest.mark.parametrize(
    "phase",
    [
        sn.TrainingPhase.OFF_SEASON,
        sn.TrainingPhase.PRE_SEASON,
        sn.TrainingPhase.IN_SEASON,
        sn.TrainingPhase.PEAK,
        sn.TrainingPhase.RECOVERY,
    ],
)
def test_phase_multipliers_coverage(phase):
    """Test _get_phase_multipliers for all phases"""
    protein_mult, carb_mult = sn.SportsNutritionCalculator._get_phase_multipliers(phase)

    assert isinstance(protein_mult, float)
    assert isinstance(carb_mult, float)
    assert 0.5 <= protein_mult <= 1.5
    assert 0.5 <= carb_mult <= 1.5


# --- Fat Calculation Tests ---
@pytest.mark.parametrize(
    "sport,goal",
    [
        (sn.SportCategory.ENDURANCE, "maintain"),
        (sn.SportCategory.STRENGTH, "gain"),
        (sn.SportCategory.AESTHETIC, "loss"),
        (sn.SportCategory.COMBAT, "maintain"),
    ],
)
def test_fat_needs_calculation(sport, goal):
    """Test _calculate_fat_needs for different sports and goals"""
    fat_per_kg = sn.SportsNutritionCalculator._calculate_fat_needs(sport, goal)

    assert isinstance(fat_per_kg, float)
    assert fat_per_kg >= 0.8  # Minimum for health
    assert fat_per_kg <= 2.0  # Reasonable upper bound


# --- Pre/Post Workout Nutrition Tests ---
@pytest.mark.parametrize(
    "sport,daily_carbs",
    [
        (sn.SportCategory.ENDURANCE, 400.0),
        (sn.SportCategory.STRENGTH, 200.0),
        (sn.SportCategory.POWER, 250.0),
        (sn.SportCategory.TEAM, 350.0),
    ],
)
def test_pre_workout_carbs_calculation(sport, daily_carbs):
    """Test _calculate_pre_workout_carbs logic"""
    pre_carbs = sn.SportsNutritionCalculator._calculate_pre_workout_carbs(sport, daily_carbs)

    if sport in [sn.SportCategory.ENDURANCE, sn.SportCategory.TEAM]:
        assert pre_carbs is not None
        assert pre_carbs > 0
        assert pre_carbs <= daily_carbs * 0.2  # Reasonable percentage
    elif sport in [sn.SportCategory.STRENGTH, sn.SportCategory.POWER]:
        assert pre_carbs is not None
        assert pre_carbs >= 0


@pytest.mark.parametrize(
    "sport,daily_protein",
    [
        (sn.SportCategory.STRENGTH, 150.0),
        (sn.SportCategory.COMBAT, 140.0),
        (sn.SportCategory.AESTHETIC, 120.0),
    ],
)
def test_post_workout_protein_calculation(sport, daily_protein):
    """Test _calculate_post_workout_protein logic"""
    post_protein = sn.SportsNutritionCalculator._calculate_post_workout_protein(
        sport, daily_protein
    )

    assert post_protein is not None
    assert post_protein > 0
    assert post_protein <= daily_protein * 0.5  # Reasonable percentage


# --- Caffeine Timing Tests ---
@pytest.mark.parametrize(
    "sport",
    [
        sn.SportCategory.ENDURANCE,
        sn.SportCategory.POWER,
        sn.SportCategory.TEAM,
        sn.SportCategory.STRENGTH,
        sn.SportCategory.AESTHETIC,
    ],
)
def test_caffeine_timing_recommendations(sport):
    """Test _get_caffeine_timing for different sports"""
    timing = sn.SportsNutritionCalculator._get_caffeine_timing(sport)

    if sport in [sn.SportCategory.ENDURANCE, sn.SportCategory.POWER, sn.SportCategory.TEAM]:
        assert timing is not None
        assert "minutes" in timing.lower()
    # For other sports, timing may be None


# --- Meal Frequency Tests ---
@pytest.mark.parametrize(
    "sport,hours",
    [
        (sn.SportCategory.ENDURANCE, 12.0),
        (sn.SportCategory.STRENGTH, 8.0),
        (sn.SportCategory.RECREATIONAL, 4.0),
    ],
)
def test_meal_frequency_calculation(sport, hours):
    """Test _get_meal_frequency for different training volumes"""
    frequency = sn.SportsNutritionCalculator._get_meal_frequency(sport, hours)

    assert isinstance(frequency, int)
    assert 3 <= frequency <= 7

    if hours > 10:
        assert frequency == 6
    elif hours > 6:
        assert frequency == 5
    else:
        assert frequency == 4


# --- Weight Cutting Advice Tests ---
@pytest.mark.parametrize(
    "sport",
    [
        sn.SportCategory.COMBAT,
        sn.SportCategory.AESTHETIC,
    ],
)
def test_weight_cutting_advice(sport):
    """Test _get_weight_cutting_advice for relevant sports"""
    advice = sn.SportsNutritionCalculator._get_weight_cutting_advice(sport)

    assert isinstance(advice, str)
    assert len(advice) > 20
    assert "weight" in advice.lower()


# --- Sport Mapping Tests ---
@pytest.mark.parametrize(
    "sport_name,expected_category",
    [
        ("running", sn.SportCategory.ENDURANCE),
        ("weightlifting", sn.SportCategory.STRENGTH),
        ("sprinting", sn.SportCategory.POWER),
        ("football", sn.SportCategory.TEAM),
        ("gymnastics", sn.SportCategory.AESTHETIC),
        ("boxing", sn.SportCategory.COMBAT),
        ("fitness", sn.SportCategory.RECREATIONAL),
    ],
)
def test_sport_mapping_coverage(sport_name, expected_category):
    """Test SPORT_MAPPING for key sport mappings"""
    assert sport_name in sn.SPORT_MAPPING
    assert sn.SPORT_MAPPING[sport_name] == expected_category


# --- Edge Cases and Error Conditions ---
def test_extreme_weight_values():
    """Test with extreme but valid weight values"""
    for weight in [40.0, 50.0, 100.0, 150.0]:
        profile = create_mock_profile(weight_kg=weight, goal="maintain")
        result = sn.get_sport_recommendations(
            profile=profile,
            sport=sn.SportCategory.RECREATIONAL,
            training_phase=sn.TrainingPhase.IN_SEASON,
            training_hours_per_week=5.0,
        )

        assert result["daily_targets"]["calories"] > 0
        assert result["daily_targets"]["protein_g"] > 0


def test_extreme_training_hours():
    """Test with extreme training hour values"""
    profile = create_mock_profile(weight_kg=70.0, goal="maintain")

    for hours in [0.5, 25.0, 40.0]:
        result = sn.get_sport_recommendations(
            profile=profile,
            sport=sn.SportCategory.ENDURANCE,
            training_phase=sn.TrainingPhase.IN_SEASON,
            training_hours_per_week=hours,
        )

        # Should still produce valid results
        assert result["daily_targets"]["calories"] > 0
        assert result["timing"]["meal_frequency"] >= 3


# --- End-to-End Smoke Test ---
def test_end_to_end_all_combinations_smoke():
    """Smoke test to ensure no crashes with various combinations"""
    profile = create_mock_profile(weight_kg=75.0, goal="maintain")

    # Test a few key combinations without full parametrization
    combinations = [
        (sn.SportCategory.ENDURANCE, sn.TrainingPhase.PEAK),
        (sn.SportCategory.STRENGTH, sn.TrainingPhase.OFF_SEASON),
        (sn.SportCategory.COMBAT, sn.TrainingPhase.RECOVERY),
    ]

    for sport, phase in combinations:
        result = sn.get_sport_recommendations(
            profile=profile, sport=sport, training_phase=phase, training_hours_per_week=7.0
        )

        # Basic smoke test - should not crash and return valid structure
        assert isinstance(result, dict)
        assert "daily_targets" in result
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 50


# --- Type and Value Validation ---
def test_result_types_and_ranges():
    """Test that all returned values have correct types and reasonable ranges"""
    profile = create_mock_profile(weight_kg=70.0, goal="maintain")

    result = sn.get_sport_recommendations(
        profile=profile,
        sport=sn.SportCategory.TEAM,
        training_phase=sn.TrainingPhase.IN_SEASON,
        training_hours_per_week=6.0,
    )

    # Check that all numeric values are finite
    targets = result["daily_targets"]
    for key, value in targets.items():
        assert math.isfinite(value)
        assert value >= 0

    # Check specific reasonable ranges
    assert 1000 <= targets["calories"] <= 6000
    assert 50 <= targets["protein_g"] <= 300
    assert 100 <= targets["carbs_g"] <= 800
    assert 30 <= targets["fat_g"] <= 200

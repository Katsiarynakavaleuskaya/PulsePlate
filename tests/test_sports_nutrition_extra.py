from core.sports_nutrition import (
    SportCategory,
    SportsNutritionCalculator,
    TrainingPhase,
    get_sport_recommendations,
)
from core.targets import UserProfile


def test_meal_frequency_thresholds():
    # > 10 hours -> 6 meals (254)
    assert SportsNutritionCalculator._get_meal_frequency(SportCategory.ENDURANCE, 11) == 6
    # > 6 hours -> 5 meals (256)
    assert SportsNutritionCalculator._get_meal_frequency(SportCategory.ENDURANCE, 7) == 5
    # else -> 4 meals
    assert SportsNutritionCalculator._get_meal_frequency(SportCategory.ENDURANCE, 3) == 4


def test_get_sport_recommendations_structure():
    profile = UserProfile(
        sex="male",
        age=28,
        height_cm=178.0,
        weight_kg=72.0,
        activity="active",
        goal="maintain",
    )
    rec = get_sport_recommendations(
        profile,
        SportCategory.ENDURANCE,
        TrainingPhase.IN_SEASON,
        training_hours_per_week=8.0,
    )
    # Basic structure keys (275-288 coverage)
    assert "sport_category" in rec
    assert "daily_targets" in rec
    assert "hydration" in rec
    assert "timing" in rec
    assert "supplements" in rec
    assert "special_considerations" in rec
    assert "disclaimer" in rec


from core.recommendations import build_nutrition_targets
from core.targets import UserProfile
from core.weekly_plan import generate_weekly_plan


def test_generate_weekly_plan_smoke():
    profile = UserProfile(
        sex="female",
        age=28,
        height_cm=165,
        weight_kg=60,
        activity="light",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
        life_stage="adult",
    )
    targets = build_nutrition_targets(profile)
    week = generate_weekly_plan(targets, profile.diet_flags)
    assert isinstance(week["days"], list) and len(week["days"]) == 7
    assert isinstance(week["weekly_coverage"], dict)
    assert isinstance(week["shopping_list"], dict)

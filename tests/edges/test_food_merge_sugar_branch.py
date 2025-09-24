from core.food_merge import _classify_food_group


def test_classify_food_group_high_sugar_branch():
    record = {
        "protein_g": 1.0,
        "fat_g": 0.2,
        "carbs_g": 30.0,
        "fiber_g": 1.0,
        "kcal": 120.0,
        "sugar_g": 15.0,
        "name": "sweet fruit bar",
        "flags": [],
    }
    assert _classify_food_group(record) in {"fruit", "grain", "other"}

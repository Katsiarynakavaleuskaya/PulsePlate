from typing import Dict

import pytest

from core.auto_repair import AutoRepairEngine, RepairStrategy
from core.recommendations import build_nutrition_targets
from core.targets import MicronutrientTargets, UserProfile


def test_auto_repair_partial_status_when_no_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    # Week plan with simple gaps pattern that won't improve across iterations
    week_plan: Dict = {
        "days": [
            {
                "meals": [
                    {
                        "ingredients": [
                            {"name": "bread"},
                            {"name": "rice"},
                        ],
                        "nutrients": {
                            "kcal": 0.0,
                            "protein_g": 0.0,
                            "fat_g": 0.0,
                            "carbs_g": 0.0,
                            "fiber_g": 0.0,
                            "iron_mg": 0.0,
                            "calcium_mg": 0.0,
                            "magnesium_mg": 0.0,
                            "zinc_mg": 0.0,
                            "potassium_mg": 0.0,
                            "iodine_ug": 0.0,
                            "selenium_ug": 0.0,
                            "folate_ug": 0.0,
                            "b12_ug": 0.0,
                            "vitamin_d_iu": 0.0,
                            "vitamin_a_ug": 0.0,
                            "vitamin_c_mg": 0.0,
                        },
                    }
                ]
            }
        ]
    }
    # minimal viable targets tuple values (min, target, max)
    targets = MicronutrientTargets(
        iron_mg=(8.0, 18.0, 45.0),
        calcium_mg=(800.0, 1000.0, 2500.0),
        magnesium_mg=(300.0, 400.0, 700.0),
        zinc_mg=(8.0, 11.0, 40.0),
        potassium_mg=(2000.0, 3500.0, 5000.0),
        iodine_ug=(90.0, 150.0, 600.0),
        selenium_ug=(30.0, 55.0, 400.0),
        folate_ug=(200.0, 400.0, 1000.0),
        b12_ug=(1.0, 2.4, 100.0),
        vitamin_d_iu=(400.0, 600.0, 4000.0),
        vitamin_a_ug=(500.0, 700.0, 3000.0),
        vitamin_c_mg=(45.0, 90.0, 2000.0),
    )

    engine = AutoRepairEngine(max_iterations=1)

    monkeypatch.setattr("core.auto_repair.repair_week_plan", lambda plan, *_args: plan)
    nutrition_targets = build_nutrition_targets(
        UserProfile(
            sex="male",
            age=30,
            height_cm=175.0,
            weight_kg=70.0,
            activity="moderate",
            goal="maintain",
        )
    )

    result = engine.auto_repair_week_plan(
        week_plan,
        targets,
        initial_strategy=RepairStrategy.BALANCED,
        nutrition_targets=nutrition_targets,
    )

    assert result.status.name == "FAILED"
    assert result.iterations == 1

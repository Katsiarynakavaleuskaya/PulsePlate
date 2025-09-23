from typing import Dict

from core.auto_repair import AutoRepairEngine, RepairStrategy
from core.targets import MicronutrientTargets


def test_auto_repair_partial_status_when_no_progress():
    # Week plan with simple gaps pattern that won't improve across iterations
    week_plan: Dict = {
        "days": [
            {
                "meals": [
                    {
                        "ingredients": [
                            {"name": "bread"},
                            {"name": "rice"},
                        ]
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

    # Force _analyze_nutrient_gaps to always return same dict so no progress
    def _no_progress(plan, t):
        return {"vitamin_c": 50.0, "folate": 30.0}

    engine._analyze_nutrient_gaps = _no_progress  # type: ignore[attr-defined]

    result = engine.auto_repair_week_plan(
        week_plan, targets, initial_strategy=RepairStrategy.BALANCED
    )

    # With no progress and iterations exhausted, expect PARTIAL or FAILED depending on baseline
    assert result.status.name in {"PARTIAL", "FAILED"}

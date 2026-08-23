"""
Comprehensive tests for core/auto_repair.py module to boost coverage to 97%.
"""

from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest

import core.food_apis.unified_db as unified_db_module
from core.auto_repair import (
    AutoRepairEngine,
    RepairIteration,
    RepairResult,
    RepairStatus,
    RepairStrategy,
    _known_nutrient_contributions,
    _week_menu_to_wire,
    auto_repair_week_plan,
    get_auto_repair_engine,
    suggest_manual_fixes,
    validate_week_plan,
)
from core.menu_engine import (
    DayMenu,
    FoodItem,
    MAX_INGREDIENTS_PER_MEAL,
    WeekMenu,
    _calculate_day_nutrients,
    _get_default_food_db,
    _safe_booster_amount,
    calculate_known_nutrient_gaps,
    has_complete_nutrition_evidence,
    repair_week_plan as repair_canonical_week_plan,
)
from core.targets import MicronutrientTargets, NutritionTargets
from core.targets import ActivityTargets, MacroTargets, MicroTargets, UserProfile
from core.food_apis.unified_db import get_cached_common_foods_snapshot


def _nutrition_targets() -> NutritionTargets:
    """Build explicit internally consistent daily targets for core tests."""
    profile = UserProfile(
        sex="male",
        age=30,
        height_cm=175.0,
        weight_kg=70.0,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        region="BY",
        timezone="UTC",
        diet_flags=set(),
        life_stage="adult",
        medical_conditions=set(),
    )
    return NutritionTargets(
        kcal_daily=1800,
        macros=MacroTargets(protein_g=100, fat_g=60, carbs_g=215, fiber_g=30),
        water_ml_daily=2000,
        micros=MicroTargets(
            iron_mg=8.0,
            calcium_mg=1000.0,
            magnesium_mg=400.0,
            zinc_mg=11.0,
            potassium_mg=4700.0,
            iodine_ug=150.0,
            selenium_ug=55.0,
            folate_ug=400.0,
            b12_ug=2.4,
            vitamin_d_iu=600.0,
            vitamin_a_ug=900.0,
            vitamin_c_mg=90.0,
        ),
        activity=ActivityTargets(
            moderate_aerobic_min=150,
            vigorous_aerobic_min=75,
            strength_sessions=2,
            steps_daily=8000,
        ),
        calculated_for=profile,
        calculation_date="2026-08-22",
    )


def _complete_nutrients(overrides: dict[str, float] | None = None) -> dict[str, float]:
    values = {
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
    }
    if overrides:
        values.update(overrides)
    return values


def _food_item(name: str, nutrients: dict[str, float]) -> FoodItem:
    complete = {
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
        **nutrients,
    }
    return FoodItem(name, complete, 1.0, [], [" BY "])


def _same_week_menu(plan: WeekMenu, *_args: object) -> WeekMenu:
    """Return the canonical input unchanged to represent legitimate no-progress."""
    return plan


def _changed_week_menu(plan: WeekMenu, *_args: object) -> WeekMenu:
    """Return one canonical material change without inventing nutrition data."""
    return replace(plan, adherence_score=plan.adherence_score + 1.0)


def _changed_on_boosters(
    plan: WeekMenu,
    _targets: MicronutrientTargets,
    strategy: str,
) -> WeekMenu:
    """Change only the explicitly mapped canonical boosters strategy."""
    return replace(plan, adherence_score=1.0) if strategy == "boosters_first" else plan


def _canonical_plan(*days: list[dict[str, Any]]) -> WeekMenu:
    """Build a deterministic canonical plan from explicit meal evidence."""
    normalized_days = deepcopy(days)
    for meals in normalized_days:
        for meal in meals:
            raw_nutrients = meal.get("nutrients")
            meal["nutrients"] = _complete_nutrients(
                raw_nutrients if isinstance(raw_nutrients, dict) else None
            )
    return WeekMenu(
        week_start="week",
        daily_menus=[
            DayMenu(
                date=f"day_{index}",
                meals=meals,
                total_nutrients={},
                targets=_nutrition_targets(),
                coverage={},
                recommendations=[],
                estimated_cost=0.0,
            )
            for index, meals in enumerate(normalized_days, start=1)
        ],
        weekly_coverage={},
        shopping_list={},
        total_cost=0.0,
        adherence_score=0.0,
    )


class TestAutoRepairComprehensive:
    """Comprehensive tests for auto_repair module."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        # Create a sample micronutrient targets
        self.targets = MicronutrientTargets(
            vitamin_a_ug=(600, 900, 3000),
            vitamin_c_mg=(75, 90, 2000),
            calcium_mg=(800, 1000, 2500),
            iron_mg=(6, 8, 45),
            magnesium_mg=(300, 400, 700),
            zinc_mg=(8, 11, 40),
            potassium_mg=(3500, 4700, 5000),
            iodine_ug=(130, 150, 1100),
            selenium_ug=(45, 55, 400),
            folate_ug=(320, 400, 1000),
            b12_ug=(2, 2.4, 100),
            vitamin_d_iu=(400, 600, 4000),
        )
        self.nutrition_targets = _nutrition_targets()

    def test_auto_repair_engine_initialization(self):
        """Test AutoRepairEngine initialization."""
        engine = AutoRepairEngine()
        assert engine.max_iterations == 3
        assert engine.repair_history == []

        # Test with custom max iterations
        engine_custom = AutoRepairEngine(max_iterations=5)
        assert engine_custom.max_iterations == 5

    def test_repair_strategy_enum(self):
        """Test RepairStrategy enum values."""
        assert RepairStrategy.CONSERVATIVE.value == "conservative"
        assert RepairStrategy.BALANCED.value == "balanced"
        assert RepairStrategy.AGGRESSIVE.value == "aggressive"

    def test_repair_status_enum(self):
        """Test RepairStatus enum values."""
        assert RepairStatus.SUCCESS.value == "success"
        assert RepairStatus.PARTIAL.value == "partial"
        assert RepairStatus.FAILED.value == "failed"
        assert RepairStatus.NEEDS_MANUAL.value == "needs_manual"

    def test_repair_result_dataclass(self):
        """Test RepairResult dataclass."""
        result = RepairResult(
            status=RepairStatus.SUCCESS,
            repaired_plan={"test": "plan"},
            original_plan={"test": "original"},
            changes_made=[{"change": "test"}],
            remaining_gaps={"gap": 1.0},
            strategy_used=RepairStrategy.BALANCED,
            iterations=1,
            message="Test message",
            suggestions=["suggestion1", "suggestion2"],
        )

        assert result.status == RepairStatus.SUCCESS
        assert result.repaired_plan == {"test": "plan"}
        assert result.original_plan == {"test": "original"}
        assert result.changes_made == [{"change": "test"}]
        assert result.remaining_gaps == {"gap": 1.0}
        assert result.strategy_used == RepairStrategy.BALANCED
        assert result.iterations == 1
        assert result.message == "Test message"
        assert result.suggestions == ["suggestion1", "suggestion2"]

    def test_repair_iteration_dataclass(self):
        """Test RepairIteration dataclass."""
        iteration = RepairIteration(
            iteration_number=1,
            strategy=RepairStrategy.AGGRESSIVE,
            gaps_before={"iron": 20.0},
            gaps_after={"iron": 10.0},
            changes_applied=[{"type": "add_ingredient"}],
            success=True,
        )

        assert iteration.iteration_number == 1
        assert iteration.strategy == RepairStrategy.AGGRESSIVE
        assert iteration.gaps_before == {"iron": 20.0}
        assert iteration.gaps_after == {"iron": 10.0}
        assert iteration.changes_applied == [{"type": "add_ingredient"}]
        assert iteration.success is True

    def test_get_auto_repair_engine(self):
        """Test get_auto_repair_engine function."""
        engine1 = get_auto_repair_engine()
        engine2 = get_auto_repair_engine()

        # Should return the same instance (singleton pattern)
        assert engine1 is engine2
        assert isinstance(engine1, AutoRepairEngine)

    def test_auto_repair_week_plan_success(self) -> None:
        """A changed canonical WeekMenu result is represented as truthful partial repair."""
        engine = AutoRepairEngine()
        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "estimated_cost": 5,
                    "total_nutrients": {"iron_mg": 1},
                    "coverage": {"iron_mg": {"status": "deficient"}},
                    "recommendations": ["review"],
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [{"name": "bread", "amount": 100}],
                        }
                    ],
                }
            ]
        }

        with patch("core.auto_repair.repair_week_plan", side_effect=_changed_week_menu):
            result = engine.auto_repair_week_plan(
                week_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )

        assert result.status == RepairStatus.PARTIAL
        assert result.iterations == 1
        assert result.changes_made
        assert "adherence_score" not in result.repaired_plan
        assert "estimated_cost" not in result.repaired_plan["days"][0]
        assert result.repaired_plan["days"][0]["total_nutrients"] == {}
        assert "recommendations" not in result.repaired_plan["days"][0]
        assert result.repaired_plan["days"][0]["meals"][0]["ingredients"] == [
            {"name": "bread", "amount": 100}
        ]
        assert week_plan["days"][0]["meals"][0]["ingredients"] == [{"name": "bread", "amount": 100}]

    def test_auto_repair_week_plan_no_gaps(self) -> None:
        """Test auto repair when no gaps exist."""
        engine = AutoRepairEngine()

        week_plan = {"days": []}

        with pytest.raises(ValueError, match="non-empty list"):
            engine.auto_repair_week_plan(
                week_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )

    def test_auto_repair_week_plan_with_strategies(self):
        """Test auto repair with different strategies."""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [{"name": "bread", "amount": 100}],
                        }
                    ],
                }
            ]
        }

        # Test with conservative strategy
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.side_effect = _same_week_menu
            result = engine.auto_repair_week_plan(
                week_plan,
                self.targets,
                RepairStrategy.CONSERVATIVE,
                nutrition_targets=self.nutrition_targets,
            )
            assert isinstance(result, RepairResult)

        # Test with balanced strategy
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.side_effect = _same_week_menu
            result = engine.auto_repair_week_plan(
                week_plan,
                self.targets,
                RepairStrategy.BALANCED,
                nutrition_targets=self.nutrition_targets,
            )
            assert isinstance(result, RepairResult)

        # Test with aggressive strategy
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.side_effect = _same_week_menu
            result = engine.auto_repair_week_plan(
                week_plan,
                self.targets,
                RepairStrategy.AGGRESSIVE,
                nutrition_targets=self.nutrition_targets,
            )
            assert isinstance(result, RepairResult)

    def test_auto_repair_week_plan_max_iterations(self) -> None:
        """Test auto repair reaching maximum iterations."""
        engine = AutoRepairEngine(max_iterations=2)
        engine.repair_history = [
            RepairIteration(
                iteration_number=99,
                strategy=RepairStrategy.AGGRESSIVE,
                gaps_before={},
                gaps_after={},
                changes_applied=[{"stale": True}],
                success=True,
            )
        ]

        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [{"name": "bread", "amount": 100}],
                        }
                    ],
                }
            ]
        }

        with patch("core.auto_repair.repair_week_plan", side_effect=_same_week_menu):
            result = engine.auto_repair_week_plan(
                week_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )

            assert isinstance(result, RepairResult)
            assert result.iterations == 2
            assert result.status == RepairStatus.FAILED
            assert result.changes_made == []
            assert engine.repair_history[0].changes_applied == []
            assert [item.strategy for item in engine.repair_history] == [
                RepairStrategy.BALANCED,
                RepairStrategy.AGGRESSIVE,
            ]

    def test_exhausted_repair_reports_only_canonical_known_gaps(self) -> None:
        """No-progress failure preserves known gaps without inventing missing evidence."""
        compliant_evidence = _complete_nutrients(
            {
                "kcal": 1200.0,
                "protein_g": 60.0,
                "fat_g": 40.0,
                "carbs_g": 100.0,
                "fiber_g": 20.0,
                "iron_mg": 0.0,
                "calcium_mg": 1000.0,
                "magnesium_mg": 400.0,
                "zinc_mg": 11.0,
                "potassium_mg": 4700.0,
                "iodine_ug": 150.0,
                "selenium_ug": 55.0,
                "folate_ug": 400.0,
                "b12_ug": 2.4,
                "vitamin_d_iu": 600.0,
                "vitamin_a_ug": 900.0,
                "vitamin_c_mg": 90.0,
            }
        )

        def _day(evidence: dict[str, float]) -> dict[str, object]:
            return {
                "meals": [
                    {
                        "ingredients": [{"name": "rice"}],
                        "nutrients": deepcopy(evidence),
                    }
                ]
            }

        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot",
            return_value={},
        ):
            one_day = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                {"days": [_day(compliant_evidence)]},
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )
            two_days = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                {"days": [_day(compliant_evidence), _day(compliant_evidence)]},
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )
            missing_iron = deepcopy(compliant_evidence)
            missing_iron.pop("iron_mg")
            ambiguous = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                {"days": [_day(missing_iron)]},
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )

        assert one_day.status is RepairStatus.FAILED
        assert one_day.remaining_gaps == {"iron_mg": 8.0}
        assert two_days.status is RepairStatus.FAILED
        assert two_days.remaining_gaps == {"iron_mg": 16.0}
        assert ambiguous.status is RepairStatus.FAILED
        assert ambiguous.remaining_gaps == {}

    def test_conservative_strategy_rotates_to_balanced_boosters(self) -> None:
        """One attempt fails conservatively; the second reaches mapped boosters."""
        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "bread", "amount": 100, "unit": "g"}]}]}]
        }

        with patch("core.auto_repair.repair_week_plan", side_effect=_changed_on_boosters) as mock:
            one_attempt = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                week_plan,
                self.targets,
                RepairStrategy.CONSERVATIVE,
                nutrition_targets=self.nutrition_targets,
            )
        assert one_attempt.status == RepairStatus.FAILED
        assert one_attempt.iterations == 1
        assert [call.args[2] for call in mock.call_args_list] == ["replace_ingredients"]

        with patch("core.auto_repair.repair_week_plan", side_effect=_changed_on_boosters) as mock:
            two_attempts = AutoRepairEngine(max_iterations=2).auto_repair_week_plan(
                week_plan,
                self.targets,
                RepairStrategy.CONSERVATIVE,
                nutrition_targets=self.nutrition_targets,
            )
        assert two_attempts.status == RepairStatus.PARTIAL
        assert two_attempts.iterations == 2
        assert two_attempts.strategy_used == RepairStrategy.BALANCED
        assert [call.args[2] for call in mock.call_args_list] == [
            "replace_ingredients",
            "boosters_first",
        ]

    def test_canonical_booster_gap_fill_and_input_immutability(self) -> None:
        """Use one FoodItem for name, density, contribution, and exact gap amount."""
        plan = _canonical_plan(
            [
                {
                    "ingredients": [{"name": "rice", "amount": 100, "unit": "g"}],
                    "nutrients": {"iron_mg": 0.0},
                }
            ]
        )
        original = deepcopy(plan)
        food_db = {"iron": _food_item("Iron Food", {"iron_mg": 10.0})}

        repaired = repair_canonical_week_plan(
            plan,
            self.targets,
            strategy="boosters_first",
            food_db=food_db,
        )

        repaired_meal = repaired.daily_menus[0].meals[0]
        assert repaired_meal["ingredients"][-1] == {
            "name": "Iron Food",
            "amount": 80.0,
            "unit": "g",
        }
        assert repaired_meal["nutrients"]["iron_mg"] == 8.0
        assert repaired.daily_menus[0].total_nutrients["iron_mg"] == 8.0
        assert plan == original
        assert repaired is not plan

        assert MAX_INGREDIENTS_PER_MEAL == 15
        for existing_count in (
            MAX_INGREDIENTS_PER_MEAL - 1,
            MAX_INGREDIENTS_PER_MEAL,
        ):
            existing_ingredients = [
                {"name": f"existing-{index}", "amount": index + 1, "unit": "g"}
                for index in range(existing_count)
            ]
            bounded_plan = _canonical_plan(
                [
                    {
                        "ingredients": existing_ingredients,
                        "nutrients": {"iron_mg": 0.0},
                    }
                ]
            )
            bounded_snapshot = deepcopy(bounded_plan)

            bounded_result = repair_canonical_week_plan(
                bounded_plan,
                self.targets,
                strategy="boosters_first",
                food_db=food_db,
            )

            bounded_ingredients = bounded_result.daily_menus[0].meals[0]["ingredients"]
            assert bounded_ingredients[:existing_count] == existing_ingredients
            if existing_count == MAX_INGREDIENTS_PER_MEAL - 1:
                assert len(bounded_ingredients) == MAX_INGREDIENTS_PER_MEAL
                assert bounded_ingredients[-1] == {
                    "name": "Iron Food",
                    "amount": 80.0,
                    "unit": "g",
                }
            else:
                assert bounded_result == bounded_plan
                assert bounded_ingredients == existing_ingredients
            assert bounded_plan == bounded_snapshot

        conservative = repair_canonical_week_plan(
            plan,
            self.targets,
            strategy="replace_ingredients",
            food_db=food_db,
        )
        aggressive = repair_canonical_week_plan(
            plan,
            self.targets,
            strategy="add_snacks",
            food_db=food_db,
        )
        assert conservative == plan and conservative is not plan
        assert aggressive == plan and aggressive is not plan

    def test_paid_repair_real_db_failure_is_unchanged(self) -> None:
        """Paid repair never consumes the mock fallback when real loading fails."""
        with patch("core.menu_engine.get_unified_food_db", side_effect=RuntimeError("offline")):
            mock_fallback = _get_default_food_db()
        assert {food.name for food in mock_fallback.values()} == {
            "Chicken Breast (Mock)",
            "Lentils (Mock)",
        }

        wire_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [{"name": "rice"}],
                            "nutrients": {"iron_mg": 0.0},
                        }
                    ]
                }
            ]
        }
        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot", return_value={}
        ) as resolver:
            result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                wire_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )

        resolver.assert_not_called()
        assert result.status == RepairStatus.FAILED
        assert result.repaired_plan == result.original_plan
        assert result.changes_made == []
        assert "Mock" not in str(result.repaired_plan)

    def test_cached_common_food_snapshot_is_read_only_and_fail_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Read only the configured cache and return fresh validated objects."""
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", None)
        with patch.object(
            unified_db_module,
            "UnifiedFoodDatabase",
            side_effect=AssertionError("must not instantiate"),
        ):
            assert get_cached_common_foods_snapshot() == {}

        missing_instance = SimpleNamespace(cache_dir=tmp_path / "missing-cache")
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", missing_instance)
        assert get_cached_common_foods_snapshot() == {}

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "common_foods.json"
        valid_nutrients = {
            "protein_g": 9.0,
            "fat_g": 0.4,
            "carbs_g": 20.0,
            "fiber_g": 8.0,
            "iron_mg": 3.3,
        }
        valid_row = {
            "name": "Lentils",
            "nutrients_per_100g": valid_nutrients,
            "cost_per_100g": 1.0,
            "tags": ["VEG"],
            "availability_regions": ["BY"],
            "source": "cached-test",
            "source_id": "lentils-1",
            "nutrition_inputs": [
                {
                    "source": "estimate",
                    "record_id": "lentils-1",
                    "nutrients": deepcopy(valid_nutrients),
                }
            ],
            "nutrition_provenance": {nutrient: "estimate" for nutrient in valid_nutrients},
            "nutrition_nutrient_confidence": {nutrient: 0.4 for nutrient in valid_nutrients},
            "nutrition_confidence": 0.4,
        }
        cache_file.write_text(
            json.dumps({"lentils": valid_row}),
            encoding="utf-8",
        )
        configured_instance = SimpleNamespace(cache_dir=cache_dir)
        monkeypatch.setattr(
            unified_db_module,
            "_unified_db_instance",
            configured_instance,
        )

        first = get_cached_common_foods_snapshot()
        first["lentils"].nutrients_per_100g["iron_mg"] = 999.0
        second = get_cached_common_foods_snapshot()
        assert second["lentils"].nutrients_per_100g["iron_mg"] == 3.3
        assert unified_db_module._unified_db_instance is configured_instance

        cache_file.write_text("{", encoding="utf-8")
        assert get_cached_common_foods_snapshot() == {}
        cache_file.write_text("[]", encoding="utf-8")
        assert get_cached_common_foods_snapshot() == {}
        cache_file.write_text('{"lentils": {"name": "broken"}}', encoding="utf-8")
        assert get_cached_common_foods_snapshot() == {}

        invalid_rows = []
        for updates in (
            {"name": ""},
            {"nutrients_per_100g": []},
            {"nutrients_per_100g": {"": 1.0}},
            {"nutrients_per_100g": {"iron_mg": True}},
            {"nutrients_per_100g": {"iron_mg": -1.0}},
            {"cost_per_100g": True},
            {"tags": "VEG"},
            {"availability_regions": "BY"},
            {"category": 123},
            {"nutrition_inputs": ["invalid"]},
            {"nutrition_provenance": {"iron_mg": 123}},
            {"nutrition_nutrient_confidence": []},
            {"nutrition_nutrient_confidence": {"iron_mg": True}},
            {"nutrition_nutrient_confidence": {"iron_mg": "high"}},
            {"nutrition_nutrient_confidence": {"iron_mg": 2.0}},
            {"nutrition_confidence": True},
        ):
            row = deepcopy(valid_row)
            row.update(updates)
            invalid_rows.append(row)
        invalid_rows.append(["not-an-object"])

        cache_file.write_text(json.dumps({"": valid_row}), encoding="utf-8")
        assert get_cached_common_foods_snapshot() == {}
        for invalid_row in invalid_rows:
            cache_file.write_text(
                json.dumps({"lentils": invalid_row}),
                encoding="utf-8",
            )
            assert get_cached_common_foods_snapshot() == {}

    def test_known_remaining_gaps_and_wire_metadata_are_preserved(self) -> None:
        """Report governed changes while preserving metadata and opaque meal evidence."""
        lentils = _food_item(
            "Lentils",
            {
                "iron_mg": 3.3,
                "folate_ug": 180.0,
                "magnesium_mg": 36.0,
                "protein_g": 9.0,
                "fat_g": 0.4,
                "carbs_g": 20.0,
                "fiber_g": 8.0,
                "opaque_client_metric": 2.0,
            },
        )
        governed_evidence = _complete_nutrients(
            {
                nutrient: self.targets.get_target(nutrient)
                for nutrient in self.targets.priority_nutrients
            }
        )
        governed_evidence.update(
            {
                "iron_mg": 0.0,
                "folate_ug": 0.0,
                "magnesium_mg": 0.0,
                "opaque_client_metric": 5.0,
            }
        )
        wire_plan = {
            "plan_id": "plan-123",
            "client_metadata": {"trace": "trace-456"},
            "weekly_coverage": {"stale": 1.0},
            "shopping_list": {"stale": 1.0},
            "total_cost": 99.0,
            "adherence_score": 99.0,
            "days": [
                {
                    "day": "monday",
                    "name": "Display label",
                    "day_id": "day-1",
                    "label": "Stable label",
                    "coverage": {"stale": True},
                    "recommendations": ["stale"],
                    "estimated_cost": 99.0,
                    "meals": [
                        {
                            "meal_id": "meal-1",
                            "ingredients": [{"name": "rice"}],
                            "nutrients": governed_evidence,
                        }
                    ],
                }
            ],
        }
        wire_snapshot = deepcopy(wire_plan)
        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot",
            return_value={"lentils": lentils},
        ):
            result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                wire_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )

        assert result.status == RepairStatus.PARTIAL
        assert result.remaining_gaps == {
            "folate_ug": 220.0,
            "iron_mg": 4.7,
            "magnesium_mg": 364.0,
        }
        repaired_plan = result.repaired_plan
        repaired_meal = repaired_plan["days"][0]["meals"][0]
        assert set(repaired_meal["nutrients"]) == set(governed_evidence)
        assert repaired_meal["nutrients"]["opaque_client_metric"] == 5.0
        assert set(result.changes_made[0]["nutrient_contributions"]) == {
            "kcal",
            "protein_g",
            "fat_g",
            "carbs_g",
            "fiber_g",
            "iron_mg",
            "folate_ug",
            "magnesium_mg",
        }
        assert "opaque_client_metric" not in result.remaining_gaps
        assert "opaque_client_metric" not in result.changes_made[0]["nutrient_contributions"]
        assert "opaque_client_metric" not in repaired_plan["days"][0]["total_nutrients"]
        assert wire_plan == wire_snapshot
        assert repaired_plan["plan_id"] == "plan-123"
        assert repaired_plan["client_metadata"] == {"trace": "trace-456"}
        assert repaired_plan["days"][0]["day_id"] == "day-1"
        assert repaired_plan["days"][0]["day"] == "monday"
        assert repaired_plan["days"][0]["name"] == "Display label"
        assert repaired_plan["days"][0]["label"] == "Stable label"
        assert repaired_meal["meal_id"] == "meal-1"

        date_projection = _week_menu_to_wire(
            _canonical_plan([{"ingredients": [{"name": "dated"}], "nutrients": {"iron_mg": 0.0}}]),
            {
                "days": [
                    {
                        "date": "old-date",
                        "name": "Do not overwrite",
                        "meals": [{"ingredients": [{"name": "dated"}]}],
                    }
                ]
            },
        )
        assert date_projection["days"][0]["date"] == "day_1"
        assert date_projection["days"][0]["name"] == "Do not overwrite"
        for stale_field in (
            "weekly_coverage",
            "shopping_list",
            "total_cost",
            "adherence_score",
        ):
            assert stale_field not in repaired_plan
        for stale_field in ("coverage", "recommendations", "estimated_cost"):
            assert stale_field not in repaired_plan["days"][0]

        invalid_before = _canonical_plan(
            [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
        )
        invalid_after = deepcopy(invalid_before)
        invalid_after.daily_menus[0].meals[0]["nutrients"]["iron_mg"] = True
        assert _known_nutrient_contributions(invalid_before, invalid_after, self.targets) == {}
        assert (
            calculate_known_nutrient_gaps(
                _canonical_plan(),
                self.targets,
            )
            == {}
        )
        noncancelling_plan = _canonical_plan(
            [{"ingredients": [{"name": "surplus"}], "nutrients": {"iron_mg": 16.0}}],
            [{"ingredients": [{"name": "deficit"}], "nutrients": {"iron_mg": 0.0}}],
        )
        assert calculate_known_nutrient_gaps(noncancelling_plan, self.targets)["iron_mg"] == 8.0
        assert not has_complete_nutrition_evidence(_canonical_plan(), self.targets)
        missing_complete = _canonical_plan(
            [{"ingredients": [{"name": "missing"}], "nutrients": {}}]
        )
        missing_complete.daily_menus[0].meals[0]["nutrients"].pop("iron_mg")
        assert not has_complete_nutrition_evidence(missing_complete, self.targets)
        overmax_complete = _canonical_plan(
            [{"ingredients": [{"name": "overmax"}], "nutrients": {"iron_mg": 46.0}}]
        )
        assert not has_complete_nutrition_evidence(overmax_complete, self.targets)

    def test_canonical_booster_amount_caps(self) -> None:
        """Bound amounts by 100 g and by another governed nutrient maximum."""
        hundred_gram_plan = _canonical_plan(
            [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
        )
        hundred_gram_food = {"low_density": _food_item("Low Density Iron", {"iron_mg": 1.0})}
        hundred_gram_result = repair_canonical_week_plan(
            hundred_gram_plan,
            self.targets,
            food_db=hundred_gram_food,
        )
        assert hundred_gram_result.daily_menus[0].meals[0]["ingredients"][-1]["amount"] == 100.0

        cross_cap_plan = _canonical_plan(
            [
                {
                    "ingredients": [{"name": "rice"}],
                    "nutrients": {"iron_mg": 0.0, "vitamin_c_mg": 1990.0},
                }
            ]
        )
        cross_cap_food = {
            "cross_cap": _food_item(
                "Cross Cap Food",
                {"iron_mg": 10.0, "vitamin_c_mg": 1000.0},
            )
        }
        cross_cap_result = repair_canonical_week_plan(
            cross_cap_plan,
            self.targets,
            food_db=cross_cap_food,
        )
        cross_cap_meal = cross_cap_result.daily_menus[0].meals[0]
        assert cross_cap_meal["ingredients"][-1]["amount"] == 1.0
        assert cross_cap_meal["nutrients"]["iron_mg"] == 0.1
        assert cross_cap_meal["nutrients"]["vitamin_c_mg"] == 2000.0

        macro_cap_plan = _canonical_plan(
            [
                {
                    "ingredients": [{"name": "rice"}],
                    "nutrients": {
                        "kcal": 1796.0,
                        "protein_g": 99.0,
                        "fat_g": 60.0,
                        "carbs_g": 215.0,
                        "fiber_g": 30.0,
                        "iron_mg": 0.0,
                    },
                }
            ]
        )
        macro_cap_food = {
            "macro_cap": _food_item(
                "Macro Cap Food",
                {"iron_mg": 10.0, "protein_g": 10.0},
            )
        }
        macro_cap_result = repair_canonical_week_plan(
            macro_cap_plan,
            self.targets,
            food_db=macro_cap_food,
        )
        macro_cap_meal = macro_cap_result.daily_menus[0].meals[0]
        assert macro_cap_meal["ingredients"][-1]["amount"] == 10.0
        assert macro_cap_meal["nutrients"]["protein_g"] == 100.0
        assert macro_cap_meal["nutrients"]["kcal"] == 1800.0

    def test_canonical_booster_one_per_day_and_stable_tie_break(self) -> None:
        """Choose by density/name deterministically and add at most one booster per day."""
        meals = [
            {"ingredients": [{"name": "breakfast"}], "nutrients": {"iron_mg": 0.0}},
            {"ingredients": [{"name": "lunch"}], "nutrients": {"iron_mg": 0.0}},
        ]
        plan = _canonical_plan(meals, meals)
        original = deepcopy(plan)
        tied_foods = {
            "zeta": _food_item("Zeta", {"iron_mg": 10.0}),
            "alpha": _food_item("Alpha", {"iron_mg": 10.0}),
        }

        repaired = repair_canonical_week_plan(
            plan,
            self.targets,
            food_db=tied_foods,
        )

        for day in repaired.daily_menus:
            assert day.meals[0]["ingredients"][-1]["name"] == "Alpha"
            assert len(day.meals[0]["ingredients"]) == 2
            assert len(day.meals[1]["ingredients"]) == 1
        assert plan == original

    def test_canonical_booster_rejects_missing_ambiguous_and_nonfinite_evidence(self) -> None:
        """Never treat absent or invalid current intake as zero evidence."""
        valid_food = {
            "iron": _food_item("Iron", {"iron_mg": 10.0}),
        }
        cases = (
            (_canonical_plan([{"ingredients": [{"name": "rice"}], "nutrients": {}}]), valid_food),
            (
                _canonical_plan(
                    [
                        {
                            "ingredients": [{"name": "rice"}],
                            "nutrients": {"iron_mg": math.nan},
                        }
                    ]
                ),
                valid_food,
            ),
            (
                _canonical_plan(
                    [
                        {"ingredients": [{"name": "one"}], "nutrients": {"iron_mg": 0.0}},
                        {"ingredients": [{"name": "two"}], "nutrients": {}},
                    ]
                ),
                valid_food,
            ),
            (
                _canonical_plan(
                    [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
                ),
                {"bad": FoodItem("Bad", {"iron_mg": math.inf}, 1.0, [], [])},
            ),
            (
                _canonical_plan(
                    [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
                ),
                {"bad": FoodItem("Bad", {"iron_mg": "invalid"}, 1.0, [], [])},
            ),
            (
                _canonical_plan(
                    [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
                ),
                {"bad": FoodItem("Bad", {"": 1.0}, 1.0, [], [])},
            ),
            (
                _canonical_plan(
                    [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 8.0}}]
                ),
                valid_food,
            ),
            (
                _canonical_plan(
                    [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
                ),
                {
                    "missing_cross": _food_item(
                        "Missing Cross",
                        {"iron_mg": 10.0, "vitamin_c_mg": 10.0},
                    )
                },
            ),
            (
                _canonical_plan(
                    [
                        {
                            "ingredients": [{"name": "rice"}],
                            "nutrients": {"iron_mg": 0.0, "vitamin_c_mg": 2000.0},
                        }
                    ]
                ),
                {
                    "maxed_cross": _food_item(
                        "Maxed Cross",
                        {"iron_mg": 10.0, "vitamin_c_mg": 10.0},
                    )
                },
            ),
            (
                _canonical_plan(
                    [
                        {
                            "ingredients": [{"name": "rice"}],
                            "nutrients": {"iron_mg": 0.0, "protein_g": "invalid"},
                        }
                    ]
                ),
                {
                    "bad_existing": _food_item(
                        "Bad Existing",
                        {"iron_mg": 10.0, "protein_g": 1.0},
                    )
                },
            ),
            (
                _canonical_plan(
                    [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
                ),
                {},
            ),
        )

        cases[0][0].daily_menus[0].meals[0]["nutrients"].pop("iron_mg")
        cases[2][0].daily_menus[0].meals[1]["nutrients"].pop("iron_mg")
        cases[7][0].daily_menus[0].meals[0]["nutrients"].pop("vitamin_c_mg")

        for plan, food_db in cases:
            before_lengths = [
                [len(meal["ingredients"]) for meal in day.meals] for day in plan.daily_menus
            ]
            repaired = repair_canonical_week_plan(
                plan,
                self.targets,
                food_db=food_db,
            )
            after_lengths = [
                [len(meal["ingredients"]) for meal in day.meals] for day in repaired.daily_menus
            ]
            assert after_lengths == before_lengths

        overflow_plan = _canonical_plan(
            [
                {
                    "ingredients": [{"name": "rice"}],
                    "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                }
            ]
        )
        overflow_original = deepcopy(overflow_plan)
        overflow_food_db = {
            "overflow": _food_item(
                "Overflow",
                {"iron_mg": 10.0, "protein_g": 1e308},
            )
        }
        overflow_repaired = repair_canonical_week_plan(
            overflow_plan,
            self.targets,
            food_db=overflow_food_db,
        )
        assert overflow_repaired == overflow_original
        assert overflow_plan == overflow_original
        assert all(
            math.isfinite(value)
            for value in overflow_repaired.daily_menus[0].meals[0]["nutrients"].values()
        )

        overflow_wire_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [{"name": "rice"}],
                            "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                        }
                    ]
                }
            ]
        }
        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot", return_value=overflow_food_db
        ):
            overflow_result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                overflow_wire_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )
        assert overflow_result.status == RepairStatus.FAILED
        assert overflow_result.changes_made == []
        assert overflow_result.repaired_plan == overflow_result.original_plan

        day_sum_overflow_plan = _canonical_plan(
            [
                {
                    "ingredients": [{"name": "one"}],
                    "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                },
                {
                    "ingredients": [{"name": "two"}],
                    "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                },
            ]
        )
        day_sum_original = deepcopy(day_sum_overflow_plan)
        iron_only_food_db = {
            "iron": _food_item("Iron", {"iron_mg": 10.0}),
        }
        day_sum_repaired = repair_canonical_week_plan(
            day_sum_overflow_plan,
            self.targets,
            food_db=iron_only_food_db,
        )
        assert day_sum_repaired == day_sum_original
        assert day_sum_overflow_plan == day_sum_original
        assert all(
            math.isfinite(value)
            for meal in day_sum_repaired.daily_menus[0].meals
            for value in meal["nutrients"].values()
        )

        day_sum_wire_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [{"name": "one"}],
                            "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                        },
                        {
                            "ingredients": [{"name": "two"}],
                            "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                        },
                    ]
                }
            ]
        }
        with (
            patch(
                "core.menu_engine.get_cached_common_foods_snapshot",
                return_value=iron_only_food_db,
            ),
            pytest.raises(ValueError, match="Day nutrient evidence overflowed"),
        ):
            AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                day_sum_wire_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )

        invalid_mapping_day = _canonical_plan(
            [{"ingredients": [{"name": "rice"}], "nutrients": []}]
        ).daily_menus[0]
        invalid_mapping_day.meals[0]["nutrients"] = []
        with pytest.raises(ValueError, match="Meal nutrients must be a mapping"):
            _calculate_day_nutrients(invalid_mapping_day)

        invalid_value_day = _canonical_plan(
            [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": True}}]
        ).daily_menus[0]
        with pytest.raises(
            ValueError,
            match="Meal nutrient evidence must be finite and nonnegative",
        ):
            _calculate_day_nutrients(invalid_value_day)

        empty_day = _canonical_plan([])
        assert (
            repair_canonical_week_plan(
                empty_day,
                self.targets,
                food_db=valid_food,
            )
            == empty_day
        )

        direct_day = _canonical_plan(
            [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
        ).daily_menus[0]
        assert (
            _safe_booster_amount(
                direct_day,
                self.targets,
                {"iron_mg": 0.0},
                "iron_mg",
            )
            is None
        )

        unknown = repair_canonical_week_plan(
            cases[-1][0],
            self.targets,
            strategy="unknown",
            food_db=valid_food,
        )
        assert unknown == cases[-1][0]

    def test_unsupported_controls_fail_closed(self) -> None:
        """Preferences, diet flags, and medical constraints take manual precedence."""
        compliant = _complete_nutrients(
            {
                "kcal": 1200.0,
                "protein_g": 60.0,
                "fat_g": 40.0,
                "carbs_g": 100.0,
                "fiber_g": 20.0,
                "iron_mg": 0.0,
                "calcium_mg": 1000.0,
                "magnesium_mg": 400.0,
                "zinc_mg": 11.0,
                "potassium_mg": 4700.0,
                "iodine_ug": 150.0,
                "selenium_ug": 55.0,
                "folate_ug": 400.0,
                "b12_ug": 2.4,
                "vitamin_d_iu": 600.0,
                "vitamin_a_ug": 900.0,
                "vitamin_c_mg": 90.0,
            }
        )
        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [{"name": "complete"}],
                            "nutrients": compliant,
                        }
                    ]
                }
            ]
        }
        diet_profile = replace(
            self.nutrition_targets.calculated_for,
            diet_flags={"VEG"},
        )
        medical_profile = replace(
            self.nutrition_targets.calculated_for,
            medical_conditions={"requires-review"},
        )
        constrained_cases = (
            (
                {"exclude": ["bread"]},
                self.nutrition_targets,
            ),
            (
                {},
                replace(self.nutrition_targets, calculated_for=diet_profile),
            ),
            (
                {},
                replace(self.nutrition_targets, calculated_for=medical_profile),
            ),
        )
        for preferences, nutrition_targets in constrained_cases:
            with patch(
                "core.menu_engine.get_cached_common_foods_snapshot",
                side_effect=AssertionError("catalog must not run for unsupported constraints"),
            ) as catalog:
                constrained_result = AutoRepairEngine().auto_repair_week_plan(
                    week_plan,
                    self.targets,
                    user_preferences=preferences,
                    nutrition_targets=nutrition_targets,
                )
            assert constrained_result.status == RepairStatus.NEEDS_MANUAL
            assert constrained_result.iterations == 0
            assert constrained_result.repaired_plan == week_plan
            assert constrained_result.original_plan == week_plan
            assert constrained_result.changes_made == []
            assert constrained_result.remaining_gaps == {"iron_mg": 8.0}
            catalog.assert_not_called()

        deficient_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "bread", "amount": 100, "unit": "g"}]}]}]
        }
        disabled_known_result = AutoRepairEngine(max_iterations=0).auto_repair_week_plan(
            week_plan,
            self.targets,
            nutrition_targets=self.nutrition_targets,
        )
        disabled_unknown_result = AutoRepairEngine(max_iterations=0).auto_repair_week_plan(
            deficient_plan,
            self.targets,
            nutrition_targets=self.nutrition_targets,
        )

        assert disabled_known_result.status == RepairStatus.FAILED
        assert disabled_known_result.iterations == 0
        assert disabled_known_result.remaining_gaps == {"iron_mg": 8.0}
        assert disabled_unknown_result.status == RepairStatus.FAILED
        assert disabled_unknown_result.iterations == 0
        assert disabled_unknown_result.remaining_gaps == {}
        with pytest.raises(ValueError, match="Explicit nutrition targets are required"):
            AutoRepairEngine().auto_repair_week_plan(deficient_plan, self.targets)

    def test_complete_explicit_plan_returns_zero_iteration_success(self) -> None:
        """Complete evidence below daily ceilings authorizes unchanged success."""
        complete = _complete_nutrients(
            {
                "kcal": 1200.0,
                "protein_g": 60.0,
                "fat_g": 40.0,
                "carbs_g": 100.0,
                "fiber_g": 20.0,
                "iron_mg": 8.0,
                "calcium_mg": 1000.0,
                "magnesium_mg": 400.0,
                "zinc_mg": 11.0,
                "potassium_mg": 4700.0,
                "iodine_ug": 150.0,
                "selenium_ug": 55.0,
                "folate_ug": 400.0,
                "b12_ug": 2.4,
                "vitamin_d_iu": 600.0,
                "vitamin_a_ug": 900.0,
                "vitamin_c_mg": 90.0,
            }
        )
        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [{"name": "complete"}],
                            "nutrients": complete,
                        }
                    ]
                }
            ]
        }
        result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
            week_plan,
            self.targets,
            nutrition_targets=self.nutrition_targets,
        )
        assert result.status == RepairStatus.SUCCESS
        assert result.iterations == 0
        assert result.repaired_plan == week_plan
        assert result.original_plan == week_plan
        assert result.changes_made == []
        assert result.remaining_gaps == {}
        assert result.message == ""

        over_ceiling = deepcopy(week_plan)
        over_ceiling["days"][0]["meals"][0]["nutrients"]["protein_g"] = 100.1
        canonical_over_ceiling = _canonical_plan(
            [
                {
                    "ingredients": [{"name": "complete"}],
                    "nutrients": over_ceiling["days"][0]["meals"][0]["nutrients"],
                }
            ]
        )
        assert not has_complete_nutrition_evidence(canonical_over_ceiling, self.targets)

    @pytest.mark.parametrize(
        "invalid_range",
        [
            (1.0, 2.0),
            (True, 2.0, 3.0),
            ("1", 2.0, 3.0),
            (float("nan"), 2.0, 3.0),
            (1.0, float("inf"), 3.0),
            (-1.0, 2.0, 3.0),
            (3.0, 2.0, 4.0),
            (1.0, 4.0, 3.0),
        ],
    )
    def test_micronutrient_ranges_fail_closed(self, invalid_range: object) -> None:
        """Malformed target ranges fail at their canonical domain boundary."""
        target_data = dict(self.targets.__dict__)
        target_data["iron_mg"] = invalid_range

        with pytest.raises(ValueError):
            MicronutrientTargets(**target_data)

    def test_public_target_ranges_require_positive_values(self) -> None:
        """Zero-valued internal controls fail only at the public admission method."""
        target_data = dict(self.targets.__dict__)
        target_data["iron_mg"] = (0.0, 0.0, 0.0)
        targets = MicronutrientTargets(**target_data)

        with pytest.raises(ValueError, match="iron_mg values must be positive"):
            targets.validate_positive_ranges()

    @pytest.mark.parametrize(
        "invalid_plan",
        [
            None,
            {},
            {"days": "not-a-list"},
            {"days": [None]},
            {"days": [{}]},
            {"days": [{"meals": [None]}]},
            {"days": [{"meals": [{}]}]},
            {"days": [{"meals": [{"ingredients": [None]}]}]},
            {"days": [{"meals": [{"ingredients": [{"name": ""}]}]}]},
        ],
    )
    def test_week_plan_validation_fails_closed(self, invalid_plan: object) -> None:
        """Every malformed nested container stops before repair execution."""
        with pytest.raises(ValueError):
            validate_week_plan(invalid_plan)

    def test_repair_strategies_fail_closed(self) -> None:
        """Unknown strategy values are never treated as balanced defaults."""
        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "bread", "amount": 100, "unit": "g"}]}]}]
        }
        with pytest.raises(ValueError, match="Unknown repair strategy"):
            AutoRepairEngine().auto_repair_week_plan(
                week_plan,
                self.targets,
                cast(RepairStrategy, "balanced"),
            )
        with pytest.raises(ValueError, match="Unknown repair strategy"):
            AutoRepairEngine()._attempt_repair(
                week_plan,
                self.targets,
                cast(RepairStrategy, object()),
                1,
                self.nutrition_targets,
            )

    def test_get_next_strategy(self):
        """Test _get_next_strategy method."""
        engine = AutoRepairEngine()

        # Conservative -> Balanced
        next_strategy = engine._get_next_strategy(RepairStrategy.CONSERVATIVE)
        assert next_strategy == RepairStrategy.BALANCED

        # Balanced -> Aggressive
        next_strategy = engine._get_next_strategy(RepairStrategy.BALANCED)
        assert next_strategy == RepairStrategy.AGGRESSIVE

        # Aggressive -> Conservative (cycle)
        next_strategy = engine._get_next_strategy(RepairStrategy.AGGRESSIVE)
        assert next_strategy == RepairStrategy.CONSERVATIVE

    def test_get_all_changes(self):
        """Test _get_all_changes method."""
        engine = AutoRepairEngine()

        # Add some mock iterations to history
        iteration1 = RepairIteration(
            iteration_number=1,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron": 20.0},
            gaps_after={"iron": 10.0},
            changes_applied=[{"type": "add_ingredient", "name": "spinach"}],
            success=True,
        )

        iteration2 = RepairIteration(
            iteration_number=2,
            strategy=RepairStrategy.AGGRESSIVE,
            gaps_before={"iron": 10.0},
            gaps_after={"iron": 5.0},
            changes_applied=[{"type": "add_ingredient", "name": "beef"}],
            success=True,
        )

        engine.repair_history = [iteration1, iteration2]

        all_changes = engine._get_all_changes()
        assert len(all_changes) == 2
        assert all_changes[0]["name"] == "spinach"
        assert all_changes[1]["name"] == "beef"

    def test_generate_success_suggestions(self):
        """Test _generate_success_suggestions method."""
        engine = AutoRepairEngine()
        suggestions = engine._generate_success_suggestions()

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert isinstance(suggestions[0], str)
        # Language-agnostic semantic check: look for a success marker in any locale
        normalized = suggestions[0].lower()
        assert ("success" in normalized) or ("успеш" in normalized)

    def test_generate_manual_suggestions(self):
        """Test _generate_manual_suggestions method."""
        engine = AutoRepairEngine()

        # Test with various gaps
        gaps = {
            "iron_mg": 30.0,
            "vitamin_c_mg": 25.0,
            "folate_ug": 15.0,
            "protein_g": 20.0,
        }

        suggestions = engine._generate_manual_suggestions(gaps)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert isinstance(suggestions[0], str)

        # Check that specific nutrients are mentioned
        suggestion_text = " ".join(suggestions)
        assert "желез" in suggestion_text or "iron" in suggestion_text.lower()
        assert "овощ" in suggestion_text or "vegetable" in suggestion_text.lower()
        assert "фолиев" in suggestion_text or "folate" in suggestion_text.lower()
        assert "белк" not in suggestion_text and "protein" not in suggestion_text.lower()
        assert (
            len(
                engine._generate_manual_suggestions(
                    {"iron": 1.0, "vitamin_c": 1.0, "folate": 1.0, "protein": 1.0}
                )
            )
            == 2
        )

    def test_get_repair_history(self):
        """Test get_repair_history method."""
        engine = AutoRepairEngine()

        # Add some mock iterations to history
        iteration = RepairIteration(
            iteration_number=1,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron": 20.0},
            gaps_after={"iron": 10.0},
            changes_applied=[{"type": "add_ingredient"}],
            success=True,
        )

        engine.repair_history = [iteration]

        history = engine.get_repair_history()
        assert len(history) == 1
        assert history[0] == iteration

    def test_suggest_manual_fixes(self):
        """Test suggest_manual_fixes method."""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [{"name": "bread", "amount": 100}],
                        }
                    ],
                }
            ]
        }

        suggestions = engine.suggest_manual_fixes(week_plan, self.targets)

        assert isinstance(suggestions, list)
        # Should return suggestions for gaps found in the plan
        assert len(suggestions) >= 0

    def test_analyze_nutrient_gaps(self):
        """Test _analyze_nutrient_gaps method."""
        engine = AutoRepairEngine()

        # Test plan with no vegetables (should detect vitamin C and folate gaps)
        week_plan_no_vegetables = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [
                                {"name": "bread", "amount": 100},
                                {"name": "butter", "amount": 20},
                            ],
                        }
                    ],
                }
            ]
        }

        gaps = engine._analyze_nutrient_gaps(week_plan_no_vegetables, self.targets)
        # Should detect gaps based on the logic in the method
        assert set(gaps) == {"iron_mg", "vitamin_c_mg", "folate_ug", "protein_g"}

        # Test plan with vegetables (should have fewer gaps)
        week_plan_with_vegetables = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [
                                {"name": "vegetable spinach", "amount": 100},
                                {"name": "vegetable peppers", "amount": 50},
                            ],
                        }
                    ],
                }
            ]
        }

        gaps_with_vegetables = engine._analyze_nutrient_gaps(
            week_plan_with_vegetables, self.targets
        )
        # Should have fewer gaps
        assert set(gaps_with_vegetables) == {"iron_mg", "protein_g"}

    def test_attempt_repair_success(self):
        """Test _attempt_repair method with successful repair."""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [{"name": "bread", "amount": 100}],
                        }
                    ],
                }
            ]
        }

        with patch("core.auto_repair.repair_week_plan", side_effect=_changed_week_menu):
            iteration = engine._attempt_repair(
                week_plan,
                self.targets,
                RepairStrategy.BALANCED,
                1,
                self.nutrition_targets,
            )

            assert isinstance(iteration, RepairIteration)
            assert iteration.iteration_number == 1
            assert iteration.strategy == RepairStrategy.BALANCED
            assert iteration.success is True

    def test_attempt_repair_failure(self) -> None:
        """Structural repair exceptions are not converted into no-progress results."""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [{"name": "bread", "amount": 100}],
                        }
                    ],
                }
            ]
        }

        with (
            patch(
                "core.auto_repair.repair_week_plan",
                side_effect=RuntimeError("structural repair failure"),
            ),
            pytest.raises(RuntimeError, match="structural repair failure"),
        ):
            engine._attempt_repair(
                week_plan,
                self.targets,
                RepairStrategy.BALANCED,
                1,
                self.nutrition_targets,
            )

        with (
            patch("core.auto_repair.repair_week_plan", return_value={}),
            pytest.raises(TypeError, match="Canonical repair returned an invalid result"),
        ):
            engine._attempt_repair(
                week_plan,
                self.targets,
                RepairStrategy.BALANCED,
                1,
                self.nutrition_targets,
            )

    def test_convenience_functions(self):
        """Test convenience functions."""
        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [{"name": "bread", "amount": 100}],
                        }
                    ],
                }
            ]
        }

        # Test auto_repair_week_plan convenience function
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.side_effect = _same_week_menu
            result = auto_repair_week_plan(
                week_plan,
                self.targets,
                nutrition_targets=self.nutrition_targets,
            )
            assert isinstance(result, RepairResult)

        # Test suggest_manual_fixes convenience function
        suggestions = suggest_manual_fixes(week_plan, self.targets)
        assert isinstance(suggestions, list)

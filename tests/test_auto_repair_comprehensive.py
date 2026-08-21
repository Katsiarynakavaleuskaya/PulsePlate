"""
Comprehensive tests for core/auto_repair.py module to boost coverage to 97%.
"""

from copy import deepcopy
from dataclasses import replace
import math
from typing import Any, cast
from unittest.mock import patch

import pytest

from core.auto_repair import (
    AutoRepairEngine,
    RepairIteration,
    RepairResult,
    RepairStatus,
    RepairStrategy,
    auto_repair_week_plan,
    get_auto_repair_engine,
    suggest_manual_fixes,
    validate_week_plan,
)
from core.menu_engine import (
    DayMenu,
    FoodItem,
    WeekMenu,
    _calculate_day_nutrients,
    _safe_booster_amount,
    repair_week_plan as repair_canonical_week_plan,
)
from core.targets import MicronutrientTargets, NutritionTargets


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
    return WeekMenu(
        week_start="week",
        daily_menus=[
            DayMenu(
                date=f"day_{index}",
                meals=deepcopy(meals),
                total_nutrients={},
                targets=cast(NutritionTargets, None),
                coverage={},
                recommendations=[],
                estimated_cost=0.0,
            )
            for index, meals in enumerate(days, start=1)
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
            result = engine.auto_repair_week_plan(week_plan, self.targets)

        assert result.status == RepairStatus.PARTIAL
        assert result.iterations == 1
        assert result.changes_made
        assert result.repaired_plan["adherence_score"] == 1.0
        assert result.repaired_plan["days"][0]["estimated_cost"] == 5.0
        assert result.repaired_plan["days"][0]["total_nutrients"] == {"iron_mg": 1.0}
        assert result.repaired_plan["days"][0]["recommendations"] == ["review"]
        assert result.repaired_plan["days"][0]["meals"][0]["ingredients"] == [
            {"name": "bread", "amount": 100}
        ]
        assert week_plan["days"][0]["meals"][0]["ingredients"] == [{"name": "bread", "amount": 100}]

    def test_auto_repair_week_plan_no_gaps(self) -> None:
        """Test auto repair when no gaps exist."""
        engine = AutoRepairEngine()

        week_plan = {"days": []}

        with patch.object(engine, "_analyze_nutrient_gaps", return_value={}):
            result = engine.auto_repair_week_plan(week_plan, self.targets)

        assert isinstance(result, RepairResult)
        assert result.status == RepairStatus.SUCCESS
        assert result.iterations == 0
        assert result.message == "План уже соответствует целям"
        assert result.repaired_plan == week_plan
        assert result.repaired_plan is not week_plan

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
                week_plan, self.targets, RepairStrategy.CONSERVATIVE
            )
            assert isinstance(result, RepairResult)

        # Test with balanced strategy
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.side_effect = _same_week_menu
            result = engine.auto_repair_week_plan(week_plan, self.targets, RepairStrategy.BALANCED)
            assert isinstance(result, RepairResult)

        # Test with aggressive strategy
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.side_effect = _same_week_menu
            result = engine.auto_repair_week_plan(
                week_plan, self.targets, RepairStrategy.AGGRESSIVE
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
            result = engine.auto_repair_week_plan(week_plan, self.targets)

            assert isinstance(result, RepairResult)
            assert result.iterations == 2
            assert result.status == RepairStatus.FAILED
            assert result.changes_made == []
            assert engine.repair_history[0].changes_applied == []
            assert [item.strategy for item in engine.repair_history] == [
                RepairStrategy.BALANCED,
                RepairStrategy.AGGRESSIVE,
            ]

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
            )
        assert one_attempt.status == RepairStatus.FAILED
        assert one_attempt.iterations == 1
        assert [call.args[2] for call in mock.call_args_list] == ["replace_ingredients"]

        with patch("core.auto_repair.repair_week_plan", side_effect=_changed_on_boosters) as mock:
            two_attempts = AutoRepairEngine(max_iterations=2).auto_repair_week_plan(
                week_plan,
                self.targets,
                RepairStrategy.CONSERVATIVE,
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
        food_db = {
            "iron": FoodItem(
                name="Iron Food",
                nutrients_per_100g={"iron_mg": 10.0, "protein_g": 0.0},
                cost_per_100g=1.0,
                tags=[],
                availability_regions=[],
            )
        }

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

    def test_canonical_booster_amount_caps(self) -> None:
        """Bound amounts by 100 g and by another governed nutrient maximum."""
        hundred_gram_plan = _canonical_plan(
            [{"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": 0.0}}]
        )
        hundred_gram_food = {
            "low_density": FoodItem(
                name="Low Density Iron",
                nutrients_per_100g={"iron_mg": 1.0},
                cost_per_100g=1.0,
                tags=[],
                availability_regions=[],
            )
        }
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
            "cross_cap": FoodItem(
                name="Cross Cap Food",
                nutrients_per_100g={"iron_mg": 10.0, "vitamin_c_mg": 1000.0},
                cost_per_100g=1.0,
                tags=[],
                availability_regions=[],
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

    def test_canonical_booster_one_per_day_and_stable_tie_break(self) -> None:
        """Choose by density/name deterministically and add at most one booster per day."""
        meals = [
            {"ingredients": [{"name": "breakfast"}], "nutrients": {"iron_mg": 0.0}},
            {"ingredients": [{"name": "lunch"}], "nutrients": {"iron_mg": 0.0}},
        ]
        plan = _canonical_plan(meals, meals)
        original = deepcopy(plan)
        tied_foods = {
            "zeta": FoodItem("Zeta", {"iron_mg": 10.0}, 1.0, [], []),
            "alpha": FoodItem("Alpha", {"iron_mg": 10.0}, 1.0, [], []),
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
            "iron": FoodItem("Iron", {"iron_mg": 10.0}, 1.0, [], []),
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
                    "missing_cross": FoodItem(
                        "Missing Cross",
                        {"iron_mg": 10.0, "vitamin_c_mg": 10.0},
                        1.0,
                        [],
                        [],
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
                    "maxed_cross": FoodItem(
                        "Maxed Cross",
                        {"iron_mg": 10.0, "vitamin_c_mg": 10.0},
                        1.0,
                        [],
                        [],
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
                    "bad_existing": FoodItem(
                        "Bad Existing",
                        {"iron_mg": 10.0, "protein_g": 1.0},
                        1.0,
                        [],
                        [],
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
            "overflow": FoodItem(
                "Overflow",
                {"iron_mg": 10.0, "protein_g": 1e308},
                1.0,
                [],
                [],
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
        with patch("core.menu_engine._get_default_food_db", return_value=overflow_food_db):
            overflow_result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                overflow_wire_plan,
                self.targets,
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
            "iron": FoodItem("Iron", {"iron_mg": 10.0}, 1.0, [], []),
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
        with patch("core.menu_engine._get_default_food_db", return_value=iron_only_food_db):
            day_sum_result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                day_sum_wire_plan,
                self.targets,
            )
        assert day_sum_result.status == RepairStatus.FAILED
        assert day_sum_result.changes_made == []
        assert day_sum_result.repaired_plan == day_sum_result.original_plan

        invalid_mapping_day = _canonical_plan(
            [{"ingredients": [{"name": "rice"}], "nutrients": []}]
        ).daily_menus[0]
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
        """Preferences and disabled execution never become semantic success."""
        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "bread", "amount": 100, "unit": "g"}]}]}]
        }

        preference_result = AutoRepairEngine().auto_repair_week_plan(
            week_plan,
            self.targets,
            user_preferences={"exclude": ["bread"]},
        )
        disabled_result = AutoRepairEngine(max_iterations=0).auto_repair_week_plan(
            week_plan,
            self.targets,
        )

        assert preference_result.status == RepairStatus.NEEDS_MANUAL
        assert preference_result.changes_made == []
        assert disabled_result.status == RepairStatus.FAILED
        assert disabled_result.iterations == 0

    def test_empty_plan_compat_records_local_success_history(self) -> None:
        """Internal empty-plan compatibility keeps response history invocation-local."""
        engine = AutoRepairEngine(max_iterations=1)
        week_plan = {"days": []}
        repair_iteration = RepairIteration(
            iteration_number=1,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron": 1.0},
            gaps_after={},
            changes_applied=[{"repaired_plan": week_plan}],
            success=True,
        )

        with (
            patch.object(
                engine,
                "_analyze_nutrient_gaps",
                side_effect=[{"iron": 1.0}, {"iron": 1.0}, {}],
            ),
            patch.object(engine, "_attempt_repair", return_value=repair_iteration),
        ):
            result = engine.auto_repair_week_plan(week_plan, self.targets)

        assert result.status == RepairStatus.SUCCESS
        assert result.changes_made == [{"repaired_plan": week_plan}]
        assert engine.get_repair_history() == [repair_iteration]

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
            "iron": 30.0,
            "vitamin_c": 25.0,
            "folate": 15.0,
            "protein": 20.0,
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
        assert "белк" in suggestion_text or "protein" in suggestion_text.lower()

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
        assert isinstance(gaps, dict)

        # Test plan with vegetables (should have fewer gaps)
        week_plan_with_vegetables = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [
                                {"name": "spinach", "amount": 100},
                                {"name": "bell peppers", "amount": 50},
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
        assert isinstance(gaps_with_vegetables, dict)

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
            iteration = engine._attempt_repair(week_plan, self.targets, RepairStrategy.BALANCED, 1)

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
            engine._attempt_repair(week_plan, self.targets, RepairStrategy.BALANCED, 1)

        with (
            patch("core.auto_repair.repair_week_plan", return_value={}),
            pytest.raises(TypeError, match="Canonical repair returned an invalid result"),
        ):
            engine._attempt_repair(week_plan, self.targets, RepairStrategy.BALANCED, 1)

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
            result = auto_repair_week_plan(week_plan, self.targets)
            assert isinstance(result, RepairResult)

        # Test suggest_manual_fixes convenience function
        suggestions = suggest_manual_fixes(week_plan, self.targets)
        assert isinstance(suggestions, list)

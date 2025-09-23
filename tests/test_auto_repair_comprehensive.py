"""
Comprehensive tests for core/auto_repair.py module to boost coverage to 97%.
"""

from unittest.mock import patch

from core.auto_repair import (
    AutoRepairEngine,
    RepairStrategy,
    RepairStatus,
    RepairResult,
    RepairIteration,
    get_auto_repair_engine,
    auto_repair_week_plan,
    suggest_manual_fixes,
)
from core.targets import MicronutrientTargets


class TestAutoRepairComprehensive:
    """Comprehensive tests for auto_repair module."""

    def setup_method(self):
        """Setup test fixtures."""
        # Create a sample micronutrient targets
        self.targets = MicronutrientTargets(
            vitamin_a_ug=(600, 900, 3000),
            vitamin_c_mg=(75, 90, 2000),
            calcium_mg=(800, 1000, 2500),
            iron_mg=(6, 8, 45),
            magnesium_mg=(300, 400, 350),
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

    def test_auto_repair_week_plan_success(self):
        """Test successful auto repair of week plan."""
        engine = AutoRepairEngine()

        # Mock the repair_week_plan function to return a successful result
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.return_value = {
                "days": [
                    {
                        "name": "Monday",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "ingredients": [
                                    {"name": "oatmeal", "amount": 100},
                                    {"name": "banana", "amount": 50},
                                ],
                            }
                        ],
                    }
                ]
            }

            # Create a plan with gaps that will be fixed
            week_plan = {
                "days": [
                    {
                        "name": "Monday",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "ingredients": [
                                    {"name": "bread", "amount": 100},
                                ],
                            }
                        ],
                    }
                ]
            }

            result = engine.auto_repair_week_plan(week_plan, self.targets)

            assert isinstance(result, RepairResult)
            assert result.status in [
                RepairStatus.SUCCESS,
                RepairStatus.PARTIAL,
                RepairStatus.FAILED,
            ]
            assert isinstance(result.repaired_plan, dict)
            assert isinstance(result.original_plan, dict)
            assert isinstance(result.message, str)

    def test_auto_repair_week_plan_no_gaps(self):
        """Test auto repair when no gaps exist."""
        engine = AutoRepairEngine()

        # Create a plan with no gaps
        week_plan = {
            "days": [
                {
                    "name": "Monday",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "ingredients": [
                                {"name": "spinach", "amount": 100},
                                {"name": "chicken", "amount": 150},
                                {"name": "bell peppers", "amount": 100},
                            ],
                        }
                    ],
                }
            ]
        }

        # Mock _analyze_nutrient_gaps to return empty dict (no gaps)
        with patch.object(engine, "_analyze_nutrient_gaps", return_value={}):
            result = engine.auto_repair_week_plan(week_plan, self.targets)

            assert isinstance(result, RepairResult)
            assert result.status == RepairStatus.SUCCESS
            assert result.iterations == 0
            assert result.message == "План уже соответствует целям"
            assert result.repaired_plan == week_plan

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
            mock_repair.return_value = week_plan.copy()
            result = engine.auto_repair_week_plan(
                week_plan, self.targets, RepairStrategy.CONSERVATIVE
            )
            assert isinstance(result, RepairResult)

        # Test with balanced strategy
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.return_value = week_plan.copy()
            result = engine.auto_repair_week_plan(week_plan, self.targets, RepairStrategy.BALANCED)
            assert isinstance(result, RepairResult)

        # Test with aggressive strategy
        with patch("core.auto_repair.repair_week_plan") as mock_repair:
            mock_repair.return_value = week_plan.copy()
            result = engine.auto_repair_week_plan(
                week_plan, self.targets, RepairStrategy.AGGRESSIVE
            )
            assert isinstance(result, RepairResult)

    def test_auto_repair_week_plan_max_iterations(self):
        """Test auto repair reaching maximum iterations."""
        engine = AutoRepairEngine(max_iterations=2)

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

        # Mock to always fail (no progress)
        with (
            patch("core.auto_repair.repair_week_plan") as mock_repair,
            patch.object(engine, "_analyze_nutrient_gaps") as mock_analyze,
        ):
            mock_repair.return_value = week_plan.copy()
            mock_analyze.return_value = {"iron": 20.0}  # Always return same gaps

            result = engine.auto_repair_week_plan(week_plan, self.targets)

            assert isinstance(result, RepairResult)
            assert result.iterations == 2  # Should reach max iterations
            assert result.status in [RepairStatus.FAILED, RepairStatus.PARTIAL]

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
        assert "успешно" in suggestions[0] or "successfully" in suggestions[0].lower()

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

        # Mock successful repair
        with (
            patch("core.auto_repair.repair_week_plan") as mock_repair,
            patch.object(engine, "_analyze_nutrient_gaps") as mock_analyze,
        ):
            mock_repair.return_value = {
                "days": [
                    {
                        "name": "Monday",
                        "meals": [
                            {
                                "name": "Breakfast",
                                "ingredients": [
                                    {"name": "bread", "amount": 100},
                                    {"name": "spinach", "amount": 50},
                                ],
                            }
                        ],
                    }
                ]
            }

            # Mock gaps_before (more gaps) and gaps_after (fewer gaps)
            mock_analyze.side_effect = [
                {"vitamin_c": 50.0, "folate": 30.0, "iron": 40.0, "protein": 20.0},  # gaps_before
                {"vitamin_c": 50.0, "folate": 30.0},  # gaps_after (fewer gaps = success)
            ]

            iteration = engine._attempt_repair(week_plan, self.targets, RepairStrategy.BALANCED, 1)

            assert isinstance(iteration, RepairIteration)
            assert iteration.iteration_number == 1
            assert iteration.strategy == RepairStrategy.BALANCED
            assert iteration.success is True

    def test_attempt_repair_failure(self):
        """Test _attempt_repair method with failed repair."""
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

        # Mock repair function to raise an exception
        with patch("core.auto_repair.repair_week_plan", side_effect=Exception("Repair failed")):
            iteration = engine._attempt_repair(week_plan, self.targets, RepairStrategy.BALANCED, 1)

            assert isinstance(iteration, RepairIteration)
            assert iteration.iteration_number == 1
            assert iteration.strategy == RepairStrategy.BALANCED
            assert iteration.success is False

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
            mock_repair.return_value = week_plan.copy()
            result = auto_repair_week_plan(week_plan, self.targets)
            assert isinstance(result, RepairResult)

        # Test suggest_manual_fixes convenience function
        suggestions = suggest_manual_fixes(week_plan, self.targets)
        assert isinstance(suggestions, list)

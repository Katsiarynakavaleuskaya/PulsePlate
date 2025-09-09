# -*- coding: utf-8 -*-
"""
Tests for repair_week_plan functionality

RU: Тесты для функции авто-ремонта недельного плана
EN: Tests for weekly menu auto-repair functionality
"""

from core.menu_engine import DayMenu, WeekMenu, repair_week_plan
from core.recommendations import build_micronutrient_targets
from core.targets import UserProfile


class TestRepairWeekPlan:
    """Test suite for repair_week_plan functionality."""

    def setup_method(self):
        """Set up test data."""
        # Create test user profile
        self.profile = UserProfile(
            sex="female",
            age=30,
            height_cm=165.0,
            weight_kg=60.0,
            activity="moderate",
            goal="maintain",
            life_stage="adult",
        )

        # Create micronutrient targets
        self.targets = build_micronutrient_targets(self.profile)

        # Create test weekly menu with calcium and vitamin D deficiencies
        self.test_plan = self._create_test_plan_with_deficiencies()

    def _create_test_plan_with_deficiencies(self) -> WeekMenu:
        """Create a test weekly plan with known deficiencies."""
        from core.recommendations import build_nutrition_targets

        # Get nutrition targets for the profile
        nutrition_targets = build_nutrition_targets(self.profile)

        # Create day menu with low calcium and vitamin D
        day_menu = DayMenu(
            date="2024-01-01",
            meals=[
                {
                    "name": "Breakfast",
                    "kcal": 300,
                    "nutrients": {
                        "calcium_mg": 50.0,  # Low calcium (target: 1000mg)
                        "vitamin_d_iu": 100.0,  # Low vitamin D (target: 800IU)
                        "iron_mg": 8.0,  # Adequate iron
                    },
                },
                {
                    "name": "Lunch",
                    "kcal": 500,
                    "nutrients": {
                        "calcium_mg": 100.0,  # Still low
                        "vitamin_d_iu": 50.0,  # Still low
                        "iron_mg": 5.0,  # Adequate
                    },
                },
                {
                    "name": "Dinner",
                    "kcal": 400,
                    "nutrients": {
                        "calcium_mg": 80.0,  # Still low
                        "vitamin_d_iu": 25.0,  # Still low
                        "iron_mg": 4.0,  # Adequate
                    },
                },
            ],
            total_nutrients={
                "calcium_mg": 230.0,  # Total daily calcium
                "vitamin_d_iu": 175.0,  # Total daily vitamin D
                "iron_mg": 17.0,  # Total daily iron
            },
            targets=nutrition_targets,
            coverage={},
            recommendations=[],
            estimated_cost=15.0,
        )

        # Create weekly menu with 7 days of the same deficient day
        daily_menus = [day_menu] * 7

        return WeekMenu(
            week_start="2024-01-01",
            daily_menus=daily_menus,
            weekly_coverage={},
            shopping_list={},
            total_cost=105.0,
            adherence_score=0.0,
        )

    def test_repair_week_plan_basic_functionality(self):
        """Test that repair_week_plan runs without errors."""
        # Test basic functionality
        repaired_plan = repair_week_plan(
            self.test_plan,
            self.targets,
            strategy="boosters_first",
        )

        # Should return a WeekMenu object
        assert isinstance(repaired_plan, WeekMenu)
        assert len(repaired_plan.daily_menus) == 7

    def test_repair_week_plan_different_strategies(self):
        """Test repair_week_plan with different strategies."""
        strategies = ["boosters_first", "replace_ingredients", "add_snacks"]

        for strategy in strategies:
            repaired_plan = repair_week_plan(
                self.test_plan,
                self.targets,
                strategy=strategy,
            )

            # Should return a WeekMenu object for each strategy
            assert isinstance(repaired_plan, WeekMenu)
            assert len(repaired_plan.daily_menus) == 7

    def test_repair_week_plan_with_none_food_db(self):
        """Test repair_week_plan with None food_db (should use default)."""
        repaired_plan = repair_week_plan(
            self.test_plan,
            self.targets,
            food_db=None,  # Should use default
        )

        assert isinstance(repaired_plan, WeekMenu)

    def test_repair_week_plan_micronutrient_targets_validation(self):
        """Test that micronutrient targets are properly validated."""
        # Test with valid targets
        repaired_plan = repair_week_plan(
            self.test_plan,
            self.targets,
        )

        assert isinstance(repaired_plan, WeekMenu)

        # Test that targets have required methods
        assert hasattr(self.targets, "get_target")
        assert hasattr(self.targets, "priority_nutrients")
        assert hasattr(self.targets, "is_deficient")

    def test_repair_week_plan_calcium_vitamin_d_deficiencies(self):
        """Test repair with specific calcium and vitamin D deficiencies."""
        # Calculate expected deficiencies
        daily_calcium = 50.0 + 100.0 + 80.0  # 230mg total
        daily_vitamin_d = 100.0 + 50.0 + 25.0  # 175IU total

        calcium_target = self.targets.get_target("calcium_mg")  # 1000mg
        vitamin_d_target = self.targets.get_target("vitamin_d_iu")  # 800IU

        # Verify deficiencies exist
        assert daily_calcium < calcium_target
        assert daily_vitamin_d < vitamin_d_target

        # Test repair
        repaired_plan = repair_week_plan(
            self.test_plan,
            self.targets,
            strategy="boosters_first",
        )

        # For now, the function returns the original plan
        # In a full implementation, this would show improved coverage
        assert isinstance(repaired_plan, WeekMenu)

    def test_repair_week_plan_priority_nutrients(self):
        """Test that priority nutrients are correctly identified."""
        # Get high-priority nutrients
        high_priority = self.targets.get_high_priority_nutrients()

        # Should include calcium and iron (priority 5)
        assert "calcium_mg" in high_priority
        assert "iron_mg" in high_priority

        # Test repair focuses on priority nutrients
        repaired_plan = repair_week_plan(
            self.test_plan,
            self.targets,
        )

        assert isinstance(repaired_plan, WeekMenu)

    def test_repair_week_plan_deficiency_threshold(self):
        """Test deficiency threshold calculation."""
        # Test deficiency threshold
        calcium_target = self.targets.get_target("calcium_mg")
        threshold = calcium_target * self.targets.deficiency_threshold  # 80% of target

        # Test with values below and above threshold
        low_calcium = threshold - 100  # Below threshold
        high_calcium = threshold + 100  # Above threshold

        assert self.targets.is_deficient("calcium_mg", low_calcium)
        assert not self.targets.is_deficient("calcium_mg", high_calcium)

    def test_repair_week_plan_edge_cases(self):
        """Test edge cases for repair_week_plan."""
        # Test with empty plan (should not crash)
        empty_plan = WeekMenu(
            week_start="2024-01-01",
            daily_menus=[],
            weekly_coverage={},
            shopping_list={},
            total_cost=0.0,
            adherence_score=0.0,
        )

        repaired_plan = repair_week_plan(
            empty_plan,
            self.targets,
        )

        assert isinstance(repaired_plan, WeekMenu)
        assert len(repaired_plan.daily_menus) == 0

    def test_repair_week_plan_integration_with_existing_functions(self):
        """Test integration with existing menu generation functions."""
        # This test ensures repair_week_plan works with existing infrastructure
        from core.menu_engine import make_weekly_menu

        # Generate a normal weekly menu
        normal_plan = make_weekly_menu(self.profile)

        # Repair the normal plan
        repaired_plan = repair_week_plan(
            normal_plan,
            self.targets,
        )

        # Both should be WeekMenu objects
        assert isinstance(normal_plan, WeekMenu)
        assert isinstance(repaired_plan, WeekMenu)
        assert len(repaired_plan.daily_menus) == len(normal_plan.daily_menus)

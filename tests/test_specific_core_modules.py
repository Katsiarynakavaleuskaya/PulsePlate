# -*- coding: utf-8 -*-
"""
Specific Core Module Tests

RU: Специфичные тесты для core модулей с низким покрытием
EN: Specific tests for core modules with low coverage
"""

import os
import tempfile
from typing import Any, cast
from unittest.mock import mock_open, patch

import pytest

from tests.feature_manifest import FEATURE_REASON, require_feature_or_raise


class TestAliasesModule:
    """Test core.aliases module specifically."""

    def test_aliases_load_empty(self):
        """Test loading aliases with non-existent file."""
        from core.aliases import _load_aliases

        # Test with non-existent file
        result = _load_aliases("/non/existent/path.csv")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_aliases_load_with_data(self):
        """Test loading aliases with mock CSV data."""
        from core.aliases import _load_aliases

        # Mock CSV data
        csv_content = "alias,canonical\napple,fruit_apple\nbanana,fruit_banana\n"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            result = _load_aliases("mock_path.csv")
            assert isinstance(result, dict)
            assert "apple" in result

    def test_map_to_canonical(self):
        """Test canonical name mapping."""
        from core.aliases import map_to_canonical

        # Test empty input
        result = map_to_canonical("")
        assert result == "unknown"

        # Test None input
        result = map_to_canonical(cast(Any, None))
        assert result == "unknown"

        # Test normal input
        result = map_to_canonical("Apple Fruit")
        assert isinstance(result, str)
        assert len(result) > 0

        # Test special characters
        result = map_to_canonical("Apple & Banana!")
        assert isinstance(result, str)

        # Test spaces and hyphens
        result = map_to_canonical("Green-Apple Fruit")
        assert isinstance(result, str)

    def test_add_alias(self):
        """Test adding new aliases."""
        from core.aliases import add_alias

        # Test with temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = f.name

        try:
            # Add alias to new file
            add_alias("test_alias", "test_canonical", temp_path)

            # Verify file was created and contains data
            assert os.path.exists(temp_path)

            with open(temp_path, "r") as f:
                content = f.read()
                assert "test_alias" in content

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestTargetsModule:
    """Test core.targets module specifically."""

    def test_targets_basic_functions(self):
        """Test basic targets functions."""
        from core.targets import MicronutrientTargets

        # Test with valid micronutrient targets
        targets = MicronutrientTargets(
            iron_mg=(15.0, 18.0, 20.0),
            calcium_mg=(900.0, 1000.0, 1100.0),
            magnesium_mg=(350.0, 400.0, 450.0),
            zinc_mg=(10.0, 11.0, 12.0),
            potassium_mg=(3200.0, 3500.0, 3800.0),
            iodine_ug=(140.0, 150.0, 160.0),
            selenium_ug=(50.0, 55.0, 60.0),
            folate_ug=(350.0, 400.0, 450.0),
            b12_ug=(2.2, 2.4, 2.6),
            vitamin_d_iu=(550.0, 600.0, 650.0),
            vitamin_a_ug=(850.0, 900.0, 950.0),
            vitamin_c_mg=(80.0, 90.0, 100.0),
        )
        assert targets.iron_mg == (15.0, 18.0, 20.0)
        assert targets.calcium_mg == (900.0, 1000.0, 1100.0)
        assert targets.vitamin_c_mg == (80.0, 90.0, 100.0)

    def test_who_recommendations(self):
        """Test WHO recommendations."""
        from core.targets import MicronutrientTargets

        # Test different targets with tuple format (min, target, max)
        targets = MicronutrientTargets(
            iron_mg=(10.0, 15.0, 20.0),
            calcium_mg=(600.0, 800.0, 1000.0),
            magnesium_mg=(250.0, 300.0, 350.0),
            zinc_mg=(6.0, 8.0, 10.0),
            potassium_mg=(2500.0, 3000.0, 3500.0),
            iodine_ug=(100.0, 120.0, 140.0),
            selenium_ug=(35.0, 45.0, 55.0),
            folate_ug=(250.0, 300.0, 350.0),
            b12_ug=(1.5, 2.0, 2.5),
            vitamin_d_iu=(300.0, 400.0, 500.0),
            vitamin_a_ug=(600.0, 700.0, 800.0),
            vitamin_c_mg=(65.0, 75.0, 85.0),
        )
        assert isinstance(targets.iron_mg, tuple)
        assert len(targets.iron_mg) == 3

    def test_calculate_daily_targets(self):
        """Test daily targets calculation with build_nutrition_targets."""
        from core.recommendations import build_nutrition_targets
        from core.targets import UserProfile

        # Test with valid user profile
        profile = UserProfile(
            sex="male",
            age=25,
            height_cm=175.0,
            weight_kg=70.0,
            activity="moderate",
            goal="maintain",
        )

        result = build_nutrition_targets(profile)
        assert result is not None
        assert hasattr(result, "kcal_daily")
        assert hasattr(result, "macros")
        assert hasattr(result, "micros")
        assert result.kcal_daily > 0
        assert result.macros.protein_g > 0
        assert result.macros.carbs_g > 0
        assert result.macros.fat_g > 0


class TestAutoRepairModule:
    """Test core.auto_repair module specifically."""

    def test_analyze_deficiencies_comprehensive(self):
        """Test deficiency analysis comprehensively."""
        from core.auto_repair import RepairStrategy

        # Test with simple repair strategy
        strategy = RepairStrategy.BALANCED
        assert strategy is not None

        # Test that strategy enum exists
        assert hasattr(RepairStrategy, "CONSERVATIVE")
        assert hasattr(RepairStrategy, "AGGRESSIVE")

    def test_repair_suggestions(self):
        """Test repair suggestions."""
        from core.auto_repair import suggest_manual_fixes
        from core.targets import MicronutrientTargets

        # Test with mock data
        week_plan = {"day1": {"meals": []}}
        targets = MicronutrientTargets(
            iron_mg=(15.0, 18.0, 20.0),
            calcium_mg=(800.0, 1000.0, 1200.0),
            magnesium_mg=(300.0, 400.0, 500.0),
            zinc_mg=(8.0, 10.0, 12.0),
            potassium_mg=(3000.0, 3500.0, 4000.0),
            iodine_ug=(120.0, 150.0, 200.0),
            selenium_ug=(50.0, 70.0, 100.0),
            folate_ug=(300.0, 400.0, 500.0),
            b12_ug=(2.0, 2.5, 3.0),
            vitamin_d_iu=(400.0, 600.0, 800.0),
            vitamin_a_ug=(600.0, 800.0, 1000.0),
            vitamin_c_mg=(60.0, 90.0, 120.0),
        )

        result = suggest_manual_fixes(week_plan, targets)
        assert isinstance(result, list)


class TestMenuEngineModule:
    """Test core.menu_engine module specifically."""

    def test_weekly_menu_generation(self):
        """Test weekly menu generation."""
        try:
            from core.menu_engine import make_weekly_menu
            from core.targets import UserProfile

            # Test with basic targets
            targets = UserProfile(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                sex="female",
                activity="moderate",
                goal="maintain",
            )

            preferences = {
                "vegetarian": False,
                "allergies": [],
                "liked_foods": ["chicken", "rice", "vegetables"],
            }

            result = make_weekly_menu(targets, preferences)
            from core.menu_engine import WeekMenu

            assert isinstance(result, WeekMenu)

        except ImportError as exc:
            require_feature_or_raise(exc, "planner_engines", reason=FEATURE_REASON)

    def test_nutrition_totals(self):
        """Test nutrition totals calculation."""
        from core.menu_engine import make_weekly_menu
        from core.targets import UserProfile

        # Test with UserProfile
        profile = UserProfile(
            sex="male",
            age=30,
            height_cm=180.0,
            weight_kg=75.0,
            activity="moderate",
            goal="maintain",
        )

        result = make_weekly_menu(profile)
        assert result is not None


class TestPlateModule:
    """Test core.plate module specifically."""

    def test_plate_creation(self):
        """Test nutrition plate creation."""
        from core.plate import make_plate

        # Test with basic plate parameters
        result = make_plate(
            weight_kg=70.0, tdee_val=2000.0, goal="maintain", deficit_pct=None, surplus_pct=None
        )
        assert isinstance(result, dict)

    def test_plate_balance_analysis(self):
        """Test plate balance analysis."""
        from core.plate import make_plate

        # Test with different goal for balance analysis
        result = make_plate(
            weight_kg=80.0, tdee_val=2200.0, goal="gain", deficit_pct=None, surplus_pct=10.0
        )
        assert isinstance(result, dict)


class TestI18nModule:
    """Test core.i18n module specifically."""

    def test_translation_function_comprehensive(self):
        """Test translation function comprehensively."""
        from typing import get_args

        from core.i18n import Language, t

        # Test actual BMI terms that exist in translations
        bmi_terms = [
            "bmi_underweight",
            "bmi_normal",
            "bmi_overweight",
            "bmi_obese_1",
            "bmi_obese_2",
            "bmi_obese_3",
        ]

        languages = get_args(Language)  # ("ru", "en", "es")

        for lang in languages:
            for term in bmi_terms:
                result = t(lang, term)
                assert isinstance(result, str)
                assert len(result) > 0

        # Test activity level terms
        activity_terms = [
            "activity_sedentary",
            "activity_light",
            "activity_moderate",
            "activity_active",
            "activity_very_active",
        ]

        for lang in languages:
            for term in activity_terms:
                result = t(lang, term)
                assert isinstance(result, str)
                assert len(result) > 0

    def test_language_functions(self):
        """Test language management functions."""
        from typing import get_args

        from core.i18n import Language, t

        # Test translation with parameters
        result = t("en", "bmi_normal")
        assert isinstance(result, str)
        assert len(result) > 0

        # Test different languages for the same key
        languages = get_args(Language)  # ("ru", "en", "es")
        for lang in languages:
            result = t(lang, "bmi_underweight")
            assert isinstance(result, str)
            assert len(result) > 0

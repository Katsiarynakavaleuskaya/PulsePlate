"""
Diff coverage tests for PR #339 - PRO tier router standardization.

These tests ensure 97%+ patch coverage by exercising all code branches
introduced in the PR, specifically targeting:
- _is_complete_targets() validation logic (all return paths)
- Hard guards for malformed targets
- Missing profile field error messages
- Cache initialization branches
- Deprecation logging (Event state transitions)

Focus: Hit new/changed lines with minimal dependencies on core/CSV.
"""

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


class TestPRORouterDiffCoverage:
    """Cover new branches in app/routers/pro.py added by PR #339."""

    def test_missing_profile_detail_helper_format(self):
        """Verify _missing_profile_detail() includes both required substrings."""
        from app.routers.pro import _missing_profile_detail

        msg = _missing_profile_detail("age")
        assert "Missing user profile data" in msg
        assert "Missing required field: age" in msg

    def test_is_complete_targets_all_branches(self):
        """Cover all return paths in _is_complete_targets()."""
        from app.routers.pro import _is_complete_targets

        # Missing required keys
        assert not _is_complete_targets({})
        assert not _is_complete_targets({"kcal": 2000})

        # macros not a dict
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": "invalid",
                "micro": {"Fe": 1.0},
                "water_ml": 2000,
                "activity_week": {},
            }
        )

        # micro not a dict
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": "invalid",
                "water_ml": 2000,
                "activity_week": {},
            }
        )

        # micro is empty (required to be non-empty)
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {},
                "water_ml": 2000,
                "activity_week": {},
            }
        )

        # macros is empty (required to be non-empty)
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {},
                "micro": {"Fe": 1.0},
                "water_ml": 2000,
                "activity_week": {},
            }
        )

        # Valid complete targets
        assert _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
                "activity_week": {"steps_daily": 8000},
            }
        )

        # Valid targets without activity_week (optional field)
        assert _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
            }
        )

        # Invalid: activity_week wrong type (not dict)
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
                "activity_week": "invalid_type",
            }
        )

    def test_cache_init_and_reuse_branches(self, monkeypatch):
        """Cover cache initialization (None → instance) and reuse paths."""
        from app.routers import pro as pro_router

        # Mock FoodDB/RecipeDB to avoid CSV dependency
        mock_fooddb = MagicMock()
        mock_recipedb = MagicMock()

        monkeypatch.setattr("app.routers.pro.FoodDB", lambda *args, **kwargs: mock_fooddb)
        monkeypatch.setattr("app.routers.pro.RecipeDB", lambda *args, **kwargs: mock_recipedb)

        # Reset cache to trigger init branch
        pro_router._food_db_cache = None
        pro_router._recipe_db_cache = None

        # First call: init branch (is None → create instance)
        db1 = pro_router.get_food_db()
        assert db1 is mock_fooddb

        # Second call: reuse branch (already cached)
        db2 = pro_router.get_food_db()
        assert db2 is db1

        # Same for RecipeDB
        rdb1 = pro_router.get_recipe_db()
        assert rdb1 is mock_recipedb

        rdb2 = pro_router.get_recipe_db()
        assert rdb2 is rdb1

    @pytest.mark.asyncio
    async def test_generate_week_plan_hard_guard_not_dict(self, monkeypatch):
        """Cover hard guard: targets is not a dict → 400."""
        from app.routers.pro import WeekPlanRequest, generate_week_plan

        # Mock dependencies
        monkeypatch.setattr("app.routers.pro.get_food_db", lambda: MagicMock())
        monkeypatch.setattr("app.routers.pro.get_recipe_db", lambda: MagicMock())
        monkeypatch.setattr(
            "app.routers.pro.estimate_targets_minimal",
            lambda *args, **kwargs: "not_a_dict",  # Type guard should catch this
        )

        req = WeekPlanRequest(sex="female", age=25, height_cm=165, weight_kg=60)

        with pytest.raises(HTTPException) as exc_info:
            await generate_week_plan(req)

        assert exc_info.value.status_code == 400
        assert "Unable to derive targets" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_generate_week_plan_hard_guard_incomplete(self, monkeypatch):
        """Cover hard guard: targets dict incomplete → 400."""
        from app.routers.pro import WeekPlanRequest, generate_week_plan

        # Mock dependencies
        monkeypatch.setattr("app.routers.pro.get_food_db", lambda: MagicMock())
        monkeypatch.setattr("app.routers.pro.get_recipe_db", lambda: MagicMock())
        monkeypatch.setattr(
            "app.routers.pro.estimate_targets_minimal",
            lambda *args, **kwargs: {"kcal": 2000, "macros": {}, "micro": {}},  # Missing keys
        )

        req = WeekPlanRequest(sex="male", age=30, height_cm=175, weight_kg=70)

        with pytest.raises(HTTPException) as exc_info:
            await generate_week_plan(req)

        assert exc_info.value.status_code == 400
        assert "Unable to derive targets" in exc_info.value.detail


class TestPremiumWeekDiffCoverage:
    """Cover new branches in app/routers/premium_week.py added by PR #339."""

    def test_missing_profile_detail_helper_format(self):
        """Verify _missing_profile_detail() includes both required substrings."""
        from app.routers.premium_week import _missing_profile_detail

        msg = _missing_profile_detail("height_cm")
        assert "Missing user profile data" in msg
        assert "Missing required field: height_cm" in msg

    def test_is_complete_targets_all_branches(self):
        """Cover all return paths in _is_complete_targets()."""
        from app.routers.premium_week import _is_complete_targets

        # Missing required keys
        assert not _is_complete_targets({})

        # macros not a dict
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": None,
                "micro": {"Fe": 1.0},
                "water_ml": 2000,
                "activity_week": {},
            }
        )

        # micro is empty
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {},
                "water_ml": 2000,
                "activity_week": {},
            }
        )

        # macros is empty
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
                "activity_week": {},
            }
        )

        # Valid
        assert _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
                "activity_week": {"steps_daily": 8000},
            }
        )

        # Valid without activity_week (optional)
        assert _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
            }
        )

        # Invalid: activity_week wrong type
        assert not _is_complete_targets(
            {
                "kcal": 2000,
                "macros": {"protein_g": 100},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
                "activity_week": "invalid",
            }
        )

    @pytest.mark.asyncio
    async def test_deprecation_event_both_states(self, monkeypatch):
        """Cover deprecation logging Event transitions (not set → set)."""
        from app.routers.premium_week import (
            WeekPlanRequest,
            _deprecation_logged,
            generate_week_plan,
        )

        # Mock dependencies
        monkeypatch.setattr("app.routers.premium_week._get_food_db", lambda: MagicMock())
        monkeypatch.setattr("app.routers.premium_week._get_recipe_db", lambda: MagicMock())
        monkeypatch.setattr(
            "app.routers.premium_week.build_week",
            lambda *args, **kwargs: {
                "daily_menus": [],
                "weekly_coverage": {},
                "shopping_list": {},
                "total_cost": 0.0,
                "adherence_score": 0.0,
            },
        )

        # Clear event to cover "not set" → "set" transition
        _deprecation_logged.clear()

        req = WeekPlanRequest(
            targets={
                "kcal": 2000,
                "macros": {"protein_g": 100, "fat_g": 70, "carbs_g": 250, "fiber_g": 30},
                "micro": {"Fe": 10.0},
                "water_ml": 2000,
                "activity_week": {"steps_daily": 8000},
            }
        )

        # First call: event not set → log warning + set event
        await generate_week_plan(req)
        assert _deprecation_logged.is_set()

        # Second call: event already set → skip logging
        await generate_week_plan(req)

    @pytest.mark.asyncio
    async def test_hard_guard_malformed_targets(self, monkeypatch):
        """Cover hard guard for malformed targets after derivation."""
        from app.routers.premium_week import WeekPlanRequest, generate_week_plan

        # Mock dependencies
        monkeypatch.setattr("app.routers.premium_week._get_food_db", lambda: MagicMock())
        monkeypatch.setattr("app.routers.premium_week._get_recipe_db", lambda: MagicMock())
        monkeypatch.setattr(
            "app.routers.premium_week.estimate_targets_minimal",
            lambda *args, **kwargs: {"kcal": 2000},  # Incomplete
        )

        req = WeekPlanRequest(sex="female", age=28, height_cm=160, weight_kg=55)

        with pytest.raises(HTTPException) as exc_info:
            await generate_week_plan(req)

        assert exc_info.value.status_code == 400
        assert "Unable to derive targets" in exc_info.value.detail

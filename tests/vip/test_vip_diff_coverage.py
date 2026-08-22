# -*- coding: utf-8 -*-
"""
Diff-coverage tests for VIP module.

RU: Тесты для закрытия недостающих строк в diff-cover.
EN: Tests to cover missing lines in diff-cover.

These tests target specific lines that diff-cover reports as missing:
- app/routers/vip_registration.py:45 (idempotent registration)
- app/routers/vip_shoplist.py:70, 74-75 (PDF export success path)
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import ValidationError

import pytest

import app.routers.vip as vip_router
from app.effective_routes import iter_effective_route_candidates, route_path
from app.schemas.vip import (
    AutoRepairActivityTargets,
    AutoRepairDailyTargets,
    AutoRepairIngredient,
    AutoRepairMacroTargets,
    AutoRepairMeal,
    AutoRepairMealNutrients,
    AutoRepairProfile,
    AutoRepairTargetRanges,
    AutoRepairWeeklyRequest,
    WeeklyPlanRequest,
    WeeklyRecipesRequest,
)
from app.services.fitchef_runtime import _is_valid_weekly_profile_field
from core.auto_repair import (
    AutoRepairEngine,
    RepairStatus,
    RepairStrategy,
    _known_nutrient_contributions,
    _week_menu_to_wire,
    auto_repair_week_plan,
    suggest_manual_fixes,
    validate_week_plan,
)
import core.food_apis.unified_db as unified_db_module
from core.food_apis.unified_db import UnifiedFoodDatabase, UnifiedFoodItem
from core.menu_engine import (
    DayMenu,
    FoodItem,
    WeekMenu,
    _apply_one_safe_booster,
    _apply_repair_strategy,
    _calculate_day_nutrients,
    _food_nutrient_evidence,
    _get_default_food_db,
    _safe_booster_amount,
    calculate_known_nutrient_gaps,
    has_complete_nutrition_evidence,
)
from core.menu_engine import repair_week_plan as repair_canonical_week_plan
from core.targets import (
    ActivityTargets,
    MacroTargets,
    MicronutrientTargets,
    MicroTargets,
    NutritionTargets,
    UserProfile,
    calculate_bmr,
    calculate_tdee,
)


def _registered_paths(app: FastAPI) -> list[str]:
    return [route_path(route) for route in iter_effective_route_candidates(app.routes)]


_TARGET_RANGES: dict[str, list[float]] = {
    "iron_mg": [6.0, 8.0, 45.0],
    "calcium_mg": [800.0, 1000.0, 2500.0],
    "magnesium_mg": [300.0, 400.0, 700.0],
    "zinc_mg": [8.0, 11.0, 40.0],
    "potassium_mg": [3500.0, 4700.0, 5000.0],
    "iodine_ug": [130.0, 150.0, 1100.0],
    "selenium_ug": [45.0, 55.0, 400.0],
    "folate_ug": [320.0, 400.0, 1000.0],
    "b12_ug": [2.0, 2.4, 100.0],
    "vitamin_d_iu": [400.0, 600.0, 4000.0],
    "vitamin_a_ug": [600.0, 900.0, 3000.0],
    "vitamin_c_mg": [75.0, 90.0, 2000.0],
}


def _micronutrient_targets() -> MicronutrientTargets:
    return MicronutrientTargets(**{name: tuple(values) for name, values in _TARGET_RANGES.items()})


def _profile(
    *,
    diet_flags: set[str] | None = None,
    medical_conditions: set[str] | None = None,
) -> UserProfile:
    return UserProfile(
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
        diet_flags=diet_flags or set(),
        life_stage="adult",
        medical_conditions=medical_conditions or set(),
    )


def _nutrition_targets(
    *,
    kcal_daily: int = 1800,
    macros: MacroTargets | None = None,
    profile: UserProfile | None = None,
    activity: ActivityTargets | None = None,
) -> NutritionTargets:
    return NutritionTargets(
        kcal_daily=kcal_daily,
        macros=macros or MacroTargets(protein_g=100, fat_g=60, carbs_g=215, fiber_g=30),
        water_ml_daily=2000,
        micros=MicroTargets(**{name: values[1] for name, values in _TARGET_RANGES.items()}),
        activity=activity
        or ActivityTargets(
            moderate_aerobic_min=150,
            vigorous_aerobic_min=75,
            strength_sessions=2,
            steps_daily=8000,
        ),
        calculated_for=profile or _profile(),
        calculation_date="2026-08-22",
    )


def _complete_evidence(overrides: dict[str, float] | None = None) -> dict[str, float]:
    evidence = {
        "kcal": 1200.0,
        "protein_g": 60.0,
        "fat_g": 40.0,
        "carbs_g": 100.0,
        "fiber_g": 20.0,
        **{name: values[1] for name, values in _TARGET_RANGES.items()},
    }
    if overrides:
        evidence.update(overrides)
    return evidence


def _wire_plan(overrides: dict[str, float] | None = None) -> dict[str, Any]:
    return {
        "plan_id": "coverage-plan",
        "days": [
            {
                "day": "Monday",
                "label": "Stable label",
                "meals": [
                    {
                        "meal_id": "breakfast",
                        "ingredients": [{"name": "rice"}],
                        "nutrients": _complete_evidence(overrides),
                    }
                ],
            }
        ],
    }


def _auto_repair_request(
    *,
    week_plan: dict[str, Any] | None = None,
    kcal_daily: int = 1800,
    macros: dict[str, int] | None = None,
    moderate: int = 150,
    vigorous: int = 75,
) -> dict[str, Any]:
    return {
        "week_plan": deepcopy(week_plan or _wire_plan()),
        "targets": deepcopy(_TARGET_RANGES),
        "profile": {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "deficit_pct": None,
            "surplus_pct": None,
            "bodyfat": None,
            "region": "BY",
            "timezone": "UTC",
            "diet_flags": [],
            "life_stage": "adult",
            "medical_conditions": [],
        },
        "daily_targets": {
            "kcal_daily": kcal_daily,
            "macros": macros or {"protein_g": 100, "fat_g": 60, "carbs_g": 215, "fiber_g": 30},
            "water_ml_daily": 2000,
            "activity": {
                "moderate_aerobic_min": moderate,
                "vigorous_aerobic_min": vigorous,
                "strength_sessions": 2,
                "steps_daily": 8000,
            },
            "calculation_date": "2026-08-22",
        },
        "strategy": "balanced",
        "user_preferences": {},
    }


def _food_item(name: str, nutrients: dict[str, float]) -> FoodItem:
    return FoodItem(
        name=name,
        nutrients_per_100g={
            "protein_g": 0.0,
            "fat_g": 0.0,
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            **nutrients,
        },
        cost_per_100g=1.0,
        tags=[],
        availability_regions=["BY"],
    )


def _canonical_plan(
    nutrients: dict[str, float],
    *,
    nutrition_targets: NutritionTargets | None = None,
) -> WeekMenu:
    day = DayMenu(
        date="Monday",
        meals=[{"ingredients": [{"name": "rice"}], "nutrients": deepcopy(nutrients)}],
        total_nutrients=deepcopy(nutrients),
        targets=nutrition_targets or _nutrition_targets(),
        coverage={},
        recommendations=[],
        estimated_cost=0.0,
    )
    return WeekMenu(
        week_start="week-1",
        daily_menus=[day],
        weekly_coverage={},
        shopping_list={},
        total_cost=0.0,
        adherence_score=0.0,
    )


def _json_payload(response: Response) -> dict[str, Any]:
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


@pytest.fixture(autouse=True)
def vip_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "test_key")  # pragma: allowlist secret


class TestVIPRegistrationIdempotent:
    """Test VIP registration (covers vip_registration.py:44-45, 53-57)."""

    def test_register_vip_routes_registers_routes(self, monkeypatch):
        """Test that register_vip_routes registers VIP routes when enabled."""
        # Enable VIP module
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")

        from app.routers.vip_registration import register_vip_routes

        app = FastAPI()

        # Call register_vip_routes (covers lines 44-45: if not is_vip_module_enabled(): return)
        register_vip_routes(app)

        # Verify VIP routes are registered (covers lines 53-57: hasattr check and include_router)
        paths = _registered_paths(app)
        assert any("/api/v1/vip" in path for path in paths), "VIP routes should be registered"
        assert "/api/v1/vip/fitchef/insight" in paths
        assert "/api/v1/insight/fitchef" in paths
        assert "/api/v1/insight/fitchef/weekly-reflection" in paths
        assert "/api/v1/insight/fitchef/slip-support" in paths

    def test_register_vip_routes_keeps_fitchef_registration_idempotent(self, monkeypatch):
        """Repeated registration must not duplicate any VIP routes."""

        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")

        from app.routers.vip_registration import register_vip_routes

        app = FastAPI()

        register_vip_routes(app)
        first_paths = sorted(_registered_paths(app))
        register_vip_routes(app)
        second_paths = sorted(_registered_paths(app))

        assert second_paths == first_paths
        assert second_paths.count("/api/v1/vip/fitchef/insight") == 1
        assert second_paths.count("/api/v1/insight/fitchef") == 1
        assert second_paths.count("/api/v1/insight/fitchef/weekly-reflection") == 1
        assert second_paths.count("/api/v1/insight/fitchef/slip-support") == 1

    def test_register_vip_routes_noop_when_disabled(self, monkeypatch):
        """Test that register_vip_routes is a no-op when VIP module disabled."""
        monkeypatch.setenv("VIP_MODULE_ENABLED", "false")

        from app.routers.vip_registration import register_vip_routes

        app = FastAPI()

        register_vip_routes(app)

        paths = _registered_paths(app)
        assert not any(
            "/api/v1/vip" in path for path in paths
        ), "VIP routes should not be registered"
        assert "/api/v1/vip/fitchef/insight" not in paths
        assert "/api/v1/insight/fitchef" not in paths
        assert "/api/v1/insight/fitchef/weekly-reflection" not in paths
        assert "/api/v1/insight/fitchef/slip-support" not in paths

    def test_register_vip_routes_rejects_foreign_fitchef_structured_handler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A pre-existing VIP structured path with a foreign handler must fail closed."""

        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")

        from app.routers.vip_registration import register_vip_routes

        app = FastAPI()

        @app.post("/api/v1/vip/fitchef/insight")
        async def _foreign_handler() -> dict[str, str]:
            return {"status": "foreign"}

        with pytest.raises(RuntimeError, match="Duplicate /api/v1/vip/fitchef/insight route"):
            register_vip_routes(app)

    def test_router_endpoint_skips_nonmatching_routes(self) -> None:
        """Router endpoint lookup should return None when path/method do not match."""

        from fastapi import APIRouter

        from app.routers.vip_registration import _router_endpoint

        router = APIRouter()

        @router.get("/api/v1/vip/fitchef/insight")
        async def _wrong_method() -> dict[str, str]:
            return {"status": "wrong-method"}

        @router.post("/api/v1/vip/other")
        async def _wrong_path() -> dict[str, str]:
            return {"status": "wrong-path"}

        assert _router_endpoint(router, "/api/v1/vip/fitchef/insight", "POST") is None


class TestWeeklyProfileDiffCoverage:
    """Cover strict weekly-profile branches used by the PR coverage carrier."""

    def test_weekly_plan_request_rejects_boolean_numeric_profile_value(self) -> None:
        """Pydantic must not coerce a boolean into a numeric profile field."""

        with pytest.raises(ValidationError, match="Boolean values are invalid"):
            WeeklyPlanRequest(
                sex="female",
                age=29,
                height_cm=True,
                weight_kg=58.0,
                activity="active",
                goal="maintain",
            )

    def test_weekly_profile_native_integer_and_unknown_field_branches(self) -> None:
        """The native runtime accepts bounded integers and rejects unknown fields."""

        assert _is_valid_weekly_profile_field("height_cm", 168)
        assert _is_valid_weekly_profile_field("weight_kg", 58)
        assert not _is_valid_weekly_profile_field("unknown", "private-value")


class TestTC209VIPDiffCoverage:
    """Canonical CI carrier for the bounded TC2-09 VIP repair surface."""

    def test_request_schemas_reject_ambiguous_values_and_normalize_day_ids(self) -> None:
        valid_request = _auto_repair_request()
        parsed = AutoRepairWeeklyRequest.model_validate(valid_request)
        assert parsed.daily_targets.kcal_daily == 1800

        recipe = WeeklyRecipesRequest.model_validate(
            {
                "week_plan": {
                    "days": [
                        {
                            "day": " Monday ",
                            "meals": [{"ingredients": [{"name": " rice "}]}],
                        }
                    ]
                }
            }
        )
        assert recipe.week_plan.days[0].day == "Monday"

        for invalid_recipe in (
            {"week_plan": {"days": [{"meals": [{"ingredients": [{"name": "rice"}]}]}]}},
            {"week_plan": {"days": [{"day": " ", "meals": [{"ingredients": [{"name": "rice"}]}]}]}},
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "Monday",
                            "meals": [{"ingredients": [{"name": "rice"}]}],
                        },
                        {
                            "day": " Monday ",
                            "meals": [{"ingredients": [{"name": "beans"}]}],
                        },
                    ]
                }
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "Monday",
                            "meals": [{"ingredients": [{"name": "rice"}]}],
                        }
                    ]
                },
                "recipes_per_day": True,
            },
        ):
            with pytest.raises(ValidationError):
                WeeklyRecipesRequest.model_validate(invalid_recipe)

        assert (
            AutoRepairDailyTargets.model_validate(
                {**valid_request["daily_targets"], "kcal_daily": 1801}
            ).kcal_daily
            == 1801
        )
        for moderate, vigorous in ((150, 0), (0, 75), (0, 0)):
            activity = AutoRepairActivityTargets.model_validate(
                {
                    "moderate_aerobic_min": moderate,
                    "vigorous_aerobic_min": vigorous,
                    "strength_sessions": 2,
                    "steps_daily": 8000,
                }
            )
            assert (
                activity.total_aerobic_equivalent()
                if hasattr(activity, "total_aerobic_equivalent")
                else moderate + vigorous * 2 >= 0
            )
        for invalid_aerobic in (-1, True, 1.5, "0"):
            with pytest.raises(ValidationError):
                AutoRepairActivityTargets.model_validate(
                    {
                        "moderate_aerobic_min": invalid_aerobic,
                        "vigorous_aerobic_min": 0,
                        "strength_sessions": 2,
                        "steps_daily": 8000,
                    }
                )

        with pytest.raises(ValidationError):
            AutoRepairTargetRanges.model_validate(
                {**deepcopy(_TARGET_RANGES), "iron_mg": [True, 8.0, 45.0]}
            )
        with pytest.raises(ValidationError):
            AutoRepairTargetRanges.model_validate(
                {**deepcopy(_TARGET_RANGES), "iron_mg": [8.0, 6.0, 45.0]}
            )
        with pytest.raises(ValidationError):
            AutoRepairMealNutrients.model_validate(
                {**_complete_evidence(), "iron_mg": float("inf")}
            )
        with pytest.raises(ValidationError):
            AutoRepairProfile.model_validate({**valid_request["profile"], "height_cm": True})
        with pytest.raises(ValidationError):
            AutoRepairIngredient.model_validate({"name": " "})
        with pytest.raises(ValidationError):
            AutoRepairMealNutrients.model_validate("not-an-object")
        with pytest.raises(ValidationError):
            AutoRepairMealNutrients.model_validate({**_complete_evidence(), "kcal": True})
        with pytest.raises(ValidationError):
            AutoRepairMeal.model_validate("not-an-object")
        with pytest.raises(ValidationError):
            AutoRepairMeal.model_validate({"ingredients": [{"name": "rice"}], "nutrients": []})
        with pytest.raises(ValidationError):
            AutoRepairMeal.model_validate(
                {"ingredients": [{"name": "rice"}], "nutrients": {"": 1.0}}
            )
        with pytest.raises(ValidationError):
            AutoRepairMeal.model_validate(
                {"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": True}}
            )
        with pytest.raises(ValidationError):
            AutoRepairMeal.model_validate(
                {"ingredients": [{"name": "rice"}], "nutrients": {"iron_mg": -1.0}}
            )
        with pytest.raises(ValidationError):
            AutoRepairTargetRanges.model_validate("not-an-object")
        with pytest.raises(ValidationError):
            AutoRepairTargetRanges.model_validate(
                {**deepcopy(_TARGET_RANGES), "iron_mg": [6.0, 8.0]}
            )
        with pytest.raises(ValidationError):
            AutoRepairTargetRanges.model_validate(
                {**deepcopy(_TARGET_RANGES), "iron_mg": [0.0, 8.0, 45.0]}
            )
        with pytest.raises(ValidationError):
            AutoRepairProfile.model_validate("not-an-object")
        with pytest.raises(ValidationError):
            AutoRepairProfile.model_validate(
                {**valid_request["profile"], "height_cm": float("inf")}
            )
        with pytest.raises(ValidationError):
            AutoRepairMacroTargets.model_validate(
                {"protein_g": True, "fat_g": 60, "carbs_g": 215, "fiber_g": 30}
            )
        with pytest.raises(ValidationError):
            AutoRepairDailyTargets.model_validate(
                {**valid_request["daily_targets"], "kcal_daily": True}
            )

        valid_macros = valid_request["daily_targets"]["macros"]
        assert AutoRepairMacroTargets.model_validate(valid_macros).protein_g == 100
        for field_name, valid_value in valid_macros.items():
            for invalid_value in (str(valid_value), float(valid_value), True):
                with pytest.raises(ValidationError):
                    AutoRepairMacroTargets.model_validate(
                        {**valid_macros, field_name: invalid_value}
                    )

        valid_activity = valid_request["daily_targets"]["activity"]
        assert AutoRepairActivityTargets.model_validate(valid_activity).steps_daily == 8000
        for field_name, valid_value in valid_activity.items():
            for invalid_value in (str(valid_value), float(valid_value), True):
                with pytest.raises(ValidationError):
                    AutoRepairActivityTargets.model_validate(
                        {**valid_activity, field_name: invalid_value}
                    )

        for field_name in ("kcal_daily", "water_ml_daily"):
            valid_value = valid_request["daily_targets"][field_name]
            for invalid_value in (str(valid_value), float(valid_value), True):
                with pytest.raises(ValidationError):
                    AutoRepairDailyTargets.model_validate(
                        {
                            **valid_request["daily_targets"],
                            field_name: invalid_value,
                        }
                    )

        assert AutoRepairProfile.model_validate(valid_request["profile"]).age == 30
        for invalid_age in ("30", 30.0, True):
            with pytest.raises(ValidationError):
                AutoRepairProfile.model_validate({**valid_request["profile"], "age": invalid_age})

        valid_recipe_request = {
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [{"ingredients": [{"name": "rice"}]}],
                    }
                ]
            },
            "recipes_per_day": 1,
        }
        assert WeeklyRecipesRequest.model_validate(valid_recipe_request).recipes_per_day == 1
        for invalid_count in ("1", 1.0, True):
            with pytest.raises(ValidationError):
                WeeklyRecipesRequest.model_validate(
                    {**valid_recipe_request, "recipes_per_day": invalid_count}
                )

    def test_canonical_targets_delegate_tolerance_and_activity_arithmetic(self) -> None:
        exact = _nutrition_targets()
        near = _nutrition_targets(kcal_daily=1801)
        at_tolerance = _nutrition_targets(
            kcal_daily=2000,
            macros=MacroTargets(protein_g=100, fat_g=60, carbs_g=240, fiber_g=30),
            activity=ActivityTargets(
                moderate_aerobic_min=0,
                vigorous_aerobic_min=0,
                strength_sessions=2,
                steps_daily=8000,
            ),
        )
        over_tolerance = _nutrition_targets(
            kcal_daily=2001,
            macros=MacroTargets(protein_g=100, fat_g=60, carbs_g=240, fiber_g=30),
        )

        assert exact.macros.total_calories() == 1800
        assert exact.validate_consistency()
        assert near.validate_consistency()
        assert at_tolerance.validate_consistency()
        assert at_tolerance.activity.total_aerobic_equivalent() == 0
        assert not over_tolerance.validate_consistency()
        assert calculate_bmr(age=30, gender="male", weight=70.0, height=175.0) is not None
        assert calculate_tdee(1700.0, "moderate") is not None

        targets = _micronutrient_targets()
        targets.validate_positive_ranges()
        assert targets.get_target("iron_mg") == 8.0
        assert targets.get_maximum("iron_mg") == 45.0
        with pytest.raises(ValueError):
            MicronutrientTargets(
                **{
                    **{name: tuple(values) for name, values in _TARGET_RANGES.items()},
                    "iron_mg": (8.0, 6.0, 45.0),
                }
            )
        zero_targets = MicronutrientTargets(
            **{
                **{name: tuple(values) for name, values in _TARGET_RANGES.items()},
                "iron_mg": (0.0, 0.0, 0.0),
            }
        )
        with pytest.raises(ValueError, match="positive"):
            zero_targets.validate_positive_ranges()

    def test_auto_repair_truthful_terminal_states_and_constraint_precedence(self) -> None:
        targets = _micronutrient_targets()
        complete_plan = _wire_plan()
        complete_result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
            complete_plan,
            targets,
            nutrition_targets=_nutrition_targets(),
        )
        assert complete_result.status is RepairStatus.SUCCESS
        assert complete_result.iterations == 0
        assert complete_result.repaired_plan == complete_plan
        assert complete_result.original_plan == complete_plan
        assert complete_result.changes_made == []
        assert complete_result.remaining_gaps == {}
        assert complete_result.message == ""

        deficient_plan = _wire_plan({"iron_mg": 0.0})
        cached_food = UnifiedFoodItem(
            name="Iron booster",
            nutrients_per_100g={
                "protein_g": 0.0,
                "fat_g": 0.0,
                "carbs_g": 0.0,
                "fiber_g": 0.0,
                "iron_mg": 10.0,
            },
            cost_per_100g=1.0,
            tags=[],
            availability_regions=["BY"],
            source="fixture",
            source_id="iron",
        )
        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot",
            return_value={"iron": cached_food},
        ):
            partial_result = AutoRepairEngine(max_iterations=1).auto_repair_week_plan(
                deficient_plan,
                targets,
                RepairStrategy.BALANCED,
                nutrition_targets=_nutrition_targets(),
            )
        assert partial_result.status is RepairStatus.PARTIAL
        assert partial_result.iterations == 1
        assert partial_result.repaired_plan != deficient_plan
        assert partial_result.changes_made
        assert partial_result.remaining_gaps == {}

        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot",
            return_value={},
        ):
            failed_result = AutoRepairEngine(max_iterations=2).auto_repair_week_plan(
                deficient_plan,
                targets,
                nutrition_targets=_nutrition_targets(),
            )
        assert failed_result.status is RepairStatus.FAILED
        assert failed_result.iterations == 2
        assert failed_result.changes_made == []
        assert failed_result.remaining_gaps == {"iron_mg": 8.0}

        constrained_targets = (
            ({"exclude": ["rice"]}, _nutrition_targets()),
            ({}, _nutrition_targets(profile=_profile(diet_flags={"VEG"}))),
            ({}, _nutrition_targets(profile=_profile(medical_conditions={"review"}))),
        )
        for preferences, nutrition_targets in constrained_targets:
            with patch(
                "core.menu_engine.get_cached_common_foods_snapshot",
                side_effect=AssertionError("catalog must not run"),
            ) as catalog:
                manual_result = AutoRepairEngine().auto_repair_week_plan(
                    complete_plan,
                    targets,
                    user_preferences=preferences,
                    nutrition_targets=nutrition_targets,
                )
            assert manual_result.status is RepairStatus.NEEDS_MANUAL
            assert manual_result.iterations == 0
            assert manual_result.repaired_plan == complete_plan
            assert manual_result.changes_made == []
            catalog.assert_not_called()

    def test_auto_repair_validation_projection_and_advisory_branches(self) -> None:
        targets = _micronutrient_targets()
        nutrition_targets = _nutrition_targets()
        invalid_plans: tuple[object, ...] = (
            "not-an-object",
            {"days": []},
            {"days": [None]},
            {"days": [{}]},
            {"days": [{"meals": [None]}]},
            {"days": [{"meals": [{}]}]},
            {"days": [{"meals": [{"ingredients": [None]}]}]},
            {"days": [{"meals": [{"ingredients": [{"name": " "}]}]}]},
        )
        for invalid_plan in invalid_plans:
            with pytest.raises(ValueError):
                validate_week_plan(invalid_plan)

        with pytest.raises(ValueError, match="Unknown repair strategy"):
            AutoRepairEngine().auto_repair_week_plan(
                _wire_plan(),
                targets,
                cast(RepairStrategy, "balanced"),
                nutrition_targets=nutrition_targets,
            )
        with pytest.raises(ValueError, match="Explicit nutrition targets"):
            AutoRepairEngine().auto_repair_week_plan(_wire_plan(), targets)

        disabled = AutoRepairEngine(max_iterations=0).auto_repair_week_plan(
            _wire_plan({"iron_mg": 0.0}),
            targets,
            nutrition_targets=nutrition_targets,
        )
        assert disabled.status is RepairStatus.FAILED
        assert disabled.iterations == 0
        assert disabled.remaining_gaps == {"iron_mg": 8.0}

        canonical = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        for template in (
            {"days": [{"date": "old", "meals": []}]},
            {"days": [{"name": "old", "meals": []}]},
            {"days": [{"meals": []}]},
        ):
            projection = _week_menu_to_wire(canonical, template)
            projected_day = projection["days"][0]
            assert (
                projected_day.get("date") or projected_day.get("name") or projected_day.get("day")
            ) == "Monday"

        invalid_before = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        invalid_after = deepcopy(invalid_before)
        invalid_before.daily_menus[0].meals[0]["nutrients"] = []
        assert _known_nutrient_contributions(invalid_before, invalid_after) == {}
        invalid_before = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        invalid_after = deepcopy(invalid_before)
        invalid_after.daily_menus[0].meals[0]["nutrients"]["iron_mg"] = True
        assert _known_nutrient_contributions(invalid_before, invalid_after) == {}

        advisory_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "vegetable"},
                                {"name": "chicken"},
                            ]
                        },
                        {"ingredients": [{"name": "rice"}]},
                    ]
                }
            ]
        }
        suggestions = suggest_manual_fixes(advisory_plan, targets)
        assert {item["nutrient"] for item in suggestions} == {
            "iron",
            "vitamin_c",
            "folate",
        }
        with pytest.raises(ValueError, match="non-empty list"):
            suggest_manual_fixes({"days": []}, targets)

        wrapped = auto_repair_week_plan(
            _wire_plan(),
            targets,
            nutrition_targets=nutrition_targets,
        )
        assert wrapped.status is RepairStatus.SUCCESS

    def test_cached_snapshot_is_local_validated_and_deep_independent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        instance = cast(UnifiedFoodDatabase, SimpleNamespace(cache_dir=cache_dir))
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", instance)
        cache_file = cache_dir / "common_foods.json"
        valid_row = {
            "name": "Lentils",
            "nutrients_per_100g": {
                "protein_g": 9.0,
                "fat_g": 0.4,
                "carbs_g": 20.0,
                "fiber_g": 8.0,
                "iron_mg": 3.3,
            },
            "cost_per_100g": 1.0,
            "tags": ["VEG"],
            "availability_regions": ["BY"],
            "source": "fixture",
            "source_id": "lentils-1",
            "nutrition_inputs": [],
            "nutrition_provenance": {"iron_mg": "fixture"},
            "nutrition_nutrient_confidence": {"iron_mg": 0.9},
            "nutrition_confidence": 0.9,
        }
        cache_file.write_text(json.dumps({"lentils": valid_row}), encoding="utf-8")
        first = unified_db_module.get_cached_common_foods_snapshot()
        first["lentils"].nutrients_per_100g["iron_mg"] = 999.0
        second = unified_db_module.get_cached_common_foods_snapshot()
        assert second["lentils"].nutrients_per_100g["iron_mg"] == 3.3
        assert first["lentils"] is not second["lentils"]

        invalid_rows: list[object] = [
            ["not-an-object"],
            {**valid_row, "name": ""},
            {**valid_row, "nutrients_per_100g": []},
            {**valid_row, "nutrients_per_100g": {"": 1.0}},
            {**valid_row, "nutrients_per_100g": {"iron_mg": True}},
            {**valid_row, "nutrients_per_100g": {"iron_mg": -1.0}},
            {**valid_row, "cost_per_100g": True},
            {**valid_row, "tags": "VEG"},
            {**valid_row, "availability_regions": "BY"},
            {**valid_row, "category": 123},
            {**valid_row, "nutrition_inputs": ["invalid"]},
            {**valid_row, "nutrition_provenance": {"iron_mg": 123}},
            {**valid_row, "nutrition_nutrient_confidence": []},
            {**valid_row, "nutrition_nutrient_confidence": {"iron_mg": True}},
            {**valid_row, "nutrition_nutrient_confidence": {"iron_mg": "high"}},
            {**valid_row, "nutrition_nutrient_confidence": {"iron_mg": 2.0}},
            {**valid_row, "nutrition_confidence": True},
            {**valid_row, "nutrition_confidence": 2.0},
            {"name": "missing required fields"},
        ]
        invalid_payloads = [
            "not-json",
            json.dumps([]),
            json.dumps({"": valid_row}),
            *(json.dumps({"lentils": row}) for row in invalid_rows),
        ]
        for invalid_payload in invalid_payloads:
            cache_file.write_text(invalid_payload, encoding="utf-8")
            assert unified_db_module.get_cached_common_foods_snapshot() == {}

        cache_file.unlink()
        assert unified_db_module.get_cached_common_foods_snapshot() == {}
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", None)
        assert unified_db_module.get_cached_common_foods_snapshot() == {}

    def test_booster_is_deterministic_capped_and_input_immutable(self) -> None:
        targets = _micronutrient_targets()
        deficient = _complete_evidence({"iron_mg": 0.0, "vitamin_c_mg": 1990.0})
        original = _canonical_plan(deficient)
        original_copy = deepcopy(original)
        food_db = {
            "zeta": _food_item("Zeta", {"iron_mg": 10.0, "vitamin_c_mg": 1000.0}),
            "alpha": _food_item("Alpha", {"iron_mg": 10.0, "vitamin_c_mg": 1000.0}),
        }

        repaired = repair_canonical_week_plan(original, targets, food_db=food_db)
        repaired_meal = repaired.daily_menus[0].meals[0]
        assert repaired_meal["ingredients"][-1] == {
            "name": "Alpha",
            "amount": 1.0,
            "unit": "g",
        }
        assert repaired_meal["nutrients"]["iron_mg"] == 0.1
        assert repaired_meal["nutrients"]["vitamin_c_mg"] == 2000.0
        assert original == original_copy

        hundred_gram = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        low_density = {"low": _food_item("Low", {"iron_mg": 1.0})}
        hundred_repaired = repair_canonical_week_plan(
            hundred_gram,
            targets,
            food_db=low_density,
        )
        assert hundred_repaired.daily_menus[0].meals[0]["ingredients"][-1]["amount"] == 100.0

        over_ceiling = _canonical_plan(_complete_evidence({"protein_g": 101.0, "iron_mg": 0.0}))
        assert (
            repair_canonical_week_plan(
                over_ceiling,
                targets,
                food_db={"protein": _food_item("Protein", {"iron_mg": 10.0, "protein_g": 10.0})},
            )
            == over_ceiling
        )

    def test_menu_engine_fail_closed_evidence_branches(self) -> None:
        targets = _micronutrient_targets()
        complete = _complete_evidence()
        empty_plan = WeekMenu("week", [], {}, {}, 0.0, 0.0)
        assert calculate_known_nutrient_gaps(empty_plan, targets) == {}
        assert not has_complete_nutrition_evidence(empty_plan, targets)

        missing_micro = _canonical_plan(complete)
        missing_micro.daily_menus[0].meals[0]["nutrients"].pop("iron_mg")
        assert calculate_known_nutrient_gaps(missing_micro, targets) == {}
        assert not has_complete_nutrition_evidence(missing_micro, targets)

        iron_target = targets.get_target("iron_mg")
        iron_maximum = targets.get_maximum("iron_mg")
        epsilon = 1e-9
        assert not has_complete_nutrition_evidence(
            _canonical_plan(_complete_evidence({"iron_mg": iron_target - epsilon})),
            targets,
        )
        assert has_complete_nutrition_evidence(
            _canonical_plan(_complete_evidence({"iron_mg": iron_target})),
            targets,
        )
        assert has_complete_nutrition_evidence(
            _canonical_plan(_complete_evidence({"iron_mg": iron_maximum})),
            targets,
        )
        assert not has_complete_nutrition_evidence(
            _canonical_plan(_complete_evidence({"iron_mg": iron_maximum + epsilon})),
            targets,
        )

        over_micro = _canonical_plan(_complete_evidence({"iron_mg": 46.0}))
        assert not has_complete_nutrition_evidence(over_micro, targets)
        over_macro = _canonical_plan(_complete_evidence({"protein_g": 101.0}))
        assert not has_complete_nutrition_evidence(over_macro, targets)
        known_gap = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        assert calculate_known_nutrient_gaps(known_gap, targets)["iron_mg"] == 8.0

        invalid_foods = (
            FoodItem("bad-name", cast(dict[str, float], {"": 1.0}), 1.0, [], []),
            FoodItem("bad-density", cast(dict[str, float], {"iron_mg": True}), 1.0, [], []),
            FoodItem("missing-macros", {"iron_mg": 1.0}, 1.0, [], []),
            FoodItem(
                "overflow",
                {
                    "protein_g": 1e308,
                    "fat_g": 0.0,
                    "carbs_g": 0.0,
                    "fiber_g": 0.0,
                    "iron_mg": 1.0,
                },
                1.0,
                [],
                [],
            ),
        )
        for food in invalid_foods:
            assert _food_nutrient_evidence(food) is None

        day = _canonical_plan(_complete_evidence({"iron_mg": 0.0})).daily_menus[0]
        assert _safe_booster_amount(day, targets, {"iron_mg": 0.0}, "iron_mg") is None
        missing_primary = deepcopy(day)
        missing_primary.meals[0]["nutrients"].pop("iron_mg")
        assert _safe_booster_amount(missing_primary, targets, {"iron_mg": 10.0}, "iron_mg") is None
        no_gap = _canonical_plan(_complete_evidence()).daily_menus[0]
        assert _safe_booster_amount(no_gap, targets, {"iron_mg": 10.0}, "iron_mg") is None
        ambiguous = _canonical_plan(_complete_evidence({"iron_mg": 0.0})).daily_menus[0]
        ambiguous.meals[0]["nutrients"].pop("vitamin_c_mg")
        assert (
            _safe_booster_amount(
                ambiguous,
                targets,
                {"iron_mg": 10.0, "vitamin_c_mg": 1.0},
                "iron_mg",
            )
            is None
        )

        empty_day = deepcopy(day)
        empty_day.meals = []
        assert not _apply_one_safe_booster(empty_day, targets, {})
        malformed_day = deepcopy(day)
        malformed_day.meals[0]["ingredients"] = "rice"
        assert not _apply_one_safe_booster(malformed_day, targets, {})
        assert not _apply_one_safe_booster(day, targets, {"bad": invalid_foods[2]})

        omitted_macros = _canonical_plan({"iron_mg": 0.0}).daily_menus[0]
        assert _apply_one_safe_booster(
            omitted_macros,
            targets,
            {"iron": _food_item("Iron", {"iron_mg": 10.0})},
        )
        assert set(omitted_macros.meals[0]["nutrients"]) == {"iron_mg"}

        invalid_existing = _canonical_plan(
            cast(dict[str, float], {"iron_mg": 0.0, "custom": True})
        ).daily_menus[0]
        custom_food = _food_item("Custom", {"iron_mg": 10.0, "custom": 1.0})
        assert not _apply_one_safe_booster(invalid_existing, targets, {"custom": custom_food})
        overflowing_existing = _canonical_plan({"iron_mg": 0.0, "custom": 1e308}).daily_menus[0]
        overflow_food = _food_item("Overflow", {"iron_mg": 10.0, "custom": 1e308})
        assert not _apply_one_safe_booster(
            overflowing_existing,
            targets,
            {"overflow": overflow_food},
        )

        prospective_invalid = _canonical_plan({"iron_mg": 0.0}).daily_menus[0]
        prospective_invalid.meals.append(
            {"ingredients": [{"name": "bad"}], "nutrients": {"iron_mg": 0.0, "bad": True}}
        )
        assert not _apply_one_safe_booster(
            prospective_invalid,
            targets,
            {"iron": _food_item("Iron", {"iron_mg": 10.0})},
        )

        invalid_mapping = _canonical_plan({"iron_mg": 0.0}).daily_menus[0]
        invalid_mapping.meals[0]["nutrients"] = []
        with pytest.raises(ValueError, match="mapping"):
            _calculate_day_nutrients(invalid_mapping)
        invalid_value = _canonical_plan(cast(dict[str, float], {"iron_mg": True})).daily_menus[0]
        with pytest.raises(ValueError, match="finite and nonnegative"):
            _calculate_day_nutrients(invalid_value)
        overflow_day = _canonical_plan({"protein_g": 1e308}).daily_menus[0]
        overflow_day.meals.append(
            {"ingredients": [{"name": "two"}], "nutrients": {"protein_g": 1e308}}
        )
        with pytest.raises(ValueError, match="overflowed"):
            _calculate_day_nutrients(overflow_day)

        assert _apply_repair_strategy(
            _canonical_plan(complete),
            {},
            {},
            "unknown",
            {},
            None,
        ) == _canonical_plan(complete)

        async def _running_loop_default() -> dict[str, FoodItem]:
            return _get_default_food_db(allow_mock_fallback=False)

        assert asyncio.run(_running_loop_default()) == {}

    def test_routes_publish_exact_custom_envelopes_and_tolerance(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        stable_message = "Auto-repair could not complete the requested repair"
        for payload in (
            _auto_repair_request(kcal_daily=1801),
            _auto_repair_request(
                kcal_daily=2000,
                macros={"protein_g": 100, "fat_g": 60, "carbs_g": 240, "fiber_g": 30},
                moderate=0,
                vigorous=0,
            ),
        ):
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = _json_payload(response)
            assert data["status"] == "success"
            assert data["repair_result"]["status"] == "success"
            assert data["repair_result"]["message"] == ""

        over_tolerance = _auto_repair_request(
            kcal_daily=2001,
            macros={"protein_g": 100, "fat_g": 60, "carbs_g": 240, "fiber_g": 30},
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=over_tolerance,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert _json_payload(response) == {"detail": "Invalid auto-repair request payload"}

        valid_strict_payload = _auto_repair_request()
        strict_cases: list[tuple[str, str, object]] = []
        strict_cases.extend(
            ("profile", "age", invalid_value) for invalid_value in ("30", 30.0, True)
        )
        for field_name, valid_value in valid_strict_payload["daily_targets"]["macros"].items():
            strict_cases.extend(
                ("macros", field_name, invalid_value)
                for invalid_value in (str(valid_value), float(valid_value), True)
            )
        for field_name, valid_value in valid_strict_payload["daily_targets"]["activity"].items():
            strict_cases.extend(
                ("activity", field_name, invalid_value)
                for invalid_value in (str(valid_value), float(valid_value), True)
            )
        for field_name in ("kcal_daily", "water_ml_daily"):
            valid_value = valid_strict_payload["daily_targets"][field_name]
            strict_cases.extend(
                ("daily", field_name, invalid_value)
                for invalid_value in (str(valid_value), float(valid_value), True)
            )

        for section, field_name, invalid_value in strict_cases:
            invalid_payload = deepcopy(valid_strict_payload)
            if section == "profile":
                invalid_payload["profile"][field_name] = invalid_value
            elif section == "daily":
                invalid_payload["daily_targets"][field_name] = invalid_value
            else:
                invalid_payload["daily_targets"][section][field_name] = invalid_value
            with monkeypatch.context() as strict_guard:
                adapter = Mock(
                    side_effect=AssertionError(
                        "auto-repair adapter must not run for coercive integer input"
                    )
                )
                strict_guard.setattr(vip_router, "get_auto_repair_engine", adapter)
                response = client.post(
                    "/api/v1/vip/auto-repair/weekly",
                    json=invalid_payload,
                    headers=vip_headers,
                )
            assert response.status_code == 422
            assert _json_payload(response) == {"detail": "Invalid auto-repair request payload"}
            adapter.assert_not_called()

        valid_recipe_payload = {
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [{"ingredients": [{"name": "rice"}]}],
                    }
                ]
            },
            "recipes_per_day": 1,
        }
        for invalid_count in ("1", 1.0, True):
            invalid_recipe_count = {
                **valid_recipe_payload,
                "recipes_per_day": invalid_count,
            }
            with monkeypatch.context() as recipe_count_guard:
                recipe_adapter = Mock(
                    side_effect=AssertionError(
                        "recipe adapter must not run for coercive integer input"
                    )
                )
                recipe_count_guard.setattr(
                    vip_router,
                    "_adapter_synthesize_recipes_for_week",
                    recipe_adapter,
                )
                response = client.post(
                    "/api/v1/vip/recipes/weekly",
                    json=invalid_recipe_count,
                    headers=vip_headers,
                )
            assert response.status_code == 422
            assert _json_payload(response) == {"detail": "Invalid weekly recipes request payload"}
            recipe_adapter.assert_not_called()

        invalid_recipe = {
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [{"ingredients": [{"name": "rice"}]}],
                    },
                    {
                        "day": " Monday ",
                        "meals": [{"ingredients": [{"name": "beans"}]}],
                    },
                ]
            }
        }
        synthesize = Mock(side_effect=AssertionError("synthesis must not run"))
        monkeypatch.setattr(vip_router, "_adapter_synthesize_recipes_for_week", synthesize)
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=invalid_recipe,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert _json_payload(response) == {"detail": "Invalid weekly recipes request payload"}
        synthesize.assert_not_called()

        manual_payload = _auto_repair_request(week_plan=_wire_plan({"iron_mg": 0.0}))
        manual_payload["profile"]["diet_flags"] = ["VEG"]
        catalog = Mock(side_effect=AssertionError("catalog must not run"))
        monkeypatch.setattr(
            "core.menu_engine.get_cached_common_foods_snapshot",
            catalog,
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=manual_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        manual_data = _json_payload(response)
        assert manual_data["status"] == "error"
        assert manual_data["code"] == "auto_repair_failed"
        assert manual_data["message"] == stable_message
        assert manual_data["detail"] == stable_message
        assert manual_data["repair_result"]["status"] == "needs_manual"
        assert manual_data["repair_result"]["iterations"] == 0
        assert manual_data["repair_result"]["remaining_gaps"] == {"iron_mg": 8.0}
        assert manual_data["repair_result"]["message"] == stable_message
        assert "Canonical auto-repair does not support" not in str(manual_data)
        catalog.assert_not_called()

        cached_food = UnifiedFoodItem(
            name="Iron booster",
            nutrients_per_100g={
                "protein_g": 0.0,
                "fat_g": 0.0,
                "carbs_g": 0.0,
                "fiber_g": 0.0,
                "iron_mg": 10.0,
            },
            cost_per_100g=1.0,
            tags=[],
            availability_regions=["BY"],
            source="fixture",
            source_id="iron",
        )
        monkeypatch.setattr(
            "core.menu_engine.get_cached_common_foods_snapshot",
            Mock(return_value={"iron": cached_food}),
        )
        partial_payload = _auto_repair_request(week_plan=_wire_plan({"iron_mg": 0.0}))

        with monkeypatch.context() as zero_iteration:
            zero_iteration.setattr(
                vip_router,
                "get_auto_repair_engine",
                lambda: AutoRepairEngine(max_iterations=0),
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=partial_payload,
                headers=vip_headers,
            )
        assert response.status_code == 200
        zero_iteration_data = _json_payload(response)
        assert zero_iteration_data["status"] == "error"
        assert zero_iteration_data["code"] == "auto_repair_failed"
        assert zero_iteration_data["message"] == stable_message
        assert zero_iteration_data["repair_result"]["status"] == "failed"
        assert zero_iteration_data["repair_result"]["iterations"] == 0
        assert zero_iteration_data["repair_result"]["remaining_gaps"] == {"iron_mg": 8.0}

        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=partial_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        partial_data = _json_payload(response)
        assert partial_data["status"] == "success"
        assert partial_data["repair_result"]["status"] == "partial"
        assert partial_data["repair_result"]["changes_made"]

        monkeypatch.setattr(
            "core.menu_engine.get_cached_common_foods_snapshot",
            Mock(return_value={}),
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=partial_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        failed_data = _json_payload(response)
        assert failed_data["status"] == "error"
        assert failed_data["code"] == "auto_repair_failed"
        assert failed_data["message"] == stable_message
        assert failed_data["detail"] == stable_message
        assert failed_data["repair_result"]["status"] == "failed"
        assert failed_data["repair_result"]["message"] == stable_message
        assert failed_data["repair_result"]["remaining_gaps"] == {"iron_mg": 8.0}


class TestVIPShoplistPDFExport:
    """Test VIP shoplist PDF export paths (covers vip_shoplist.py:70, 74-75, 567)."""

    def test_vip_shoplist_export_pdf_success(self, client_with_vip_access):
        """Test successful PDF export (covers vip_shoplist.py:70, 74-75)."""
        # Create a valid shoplist request
        payload = {
            "items": [
                {
                    "food_id": "test_food_1",
                    "qty": {"value": "100", "unit": "G"},
                    "form": "RAW",
                }
            ]
        }

        # Call PDF export endpoint
        response = client_with_vip_access.post(
            "/api/v1/vip/shoplist/export?format=pdf",
            json=payload,
        )

        # Should succeed with PDF content
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
        assert response.content.startswith(b"%PDF"), "Response should be valid PDF"

    def test_vip_shoplist_export_pdf_import_error_returns_501(
        self, client_with_vip_access, monkeypatch
    ):
        """Test PDF export when reportlab is unavailable (covers vip_shoplist.py:567)."""

        # Force ImportError branch regardless of whether reportlab is installed.
        def _raise_import_error(*_args: object, **_kwargs: object) -> bytes:
            raise ImportError("reportlab is missing")

        monkeypatch.setattr("app.routers.vip_shoplist._export_shoplist_to_pdf", _raise_import_error)

        payload = {
            "items": [
                {
                    "food_id": "test_food_1",
                    "qty": {"value": "100", "unit": "G"},
                    "form": "RAW",
                }
            ]
        }

        response = client_with_vip_access.post(
            "/api/v1/vip/shoplist/export?format=pdf",
            json=payload,
        )

        # Should return 501 NOT IMPLEMENTED (covers line 567: except ImportError as e)
        assert response.status_code == 501
        assert response.headers.get("content-type", "").startswith("application/json")
        assert "PDF export is not available" in response.json()["detail"]

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
from dataclasses import asdict, replace
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
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
from core.food_apis.openfoodfacts_client import OFFFoodItem
from core.food_apis.usda_client import USDAFoodItem
from core.menu_engine import (
    DayMenu,
    FoodItem,
    MAX_INGREDIENTS_PER_MEAL,
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
        },
        cost_per_100g=1.0,
        tags=[],
        availability_regions=["BY"],
    )


def _verified_cache_row(
    *,
    name: str = "Lentils",
    source_id: str = "lentils-1",
    iron_mg: float = 3.3,
) -> dict[str, object]:
    nutrients = {
        "protein_g": 9.0,
        "fat_g": 0.4,
        "carbs_g": 20.0,
        "fiber_g": 8.0,
        "iron_mg": iron_mg,
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
    return {
        "name": name,
        "nutrients_per_100g": nutrients,
        "cost_per_100g": 1.0,
        "tags": ["VEG"],
        "availability_regions": ["BY"],
        "source": "fixture",
        "source_id": source_id,
        "nutrition_inputs": [
            {
                "source": "estimate",
                "record_id": source_id,
                "nutrients": deepcopy(nutrients),
            }
        ],
        "nutrition_provenance": {nutrient: "estimate" for nutrient in nutrients},
        "nutrition_nutrient_confidence": {nutrient: 0.4 for nutrient in nutrients},
        "nutrition_confidence": 0.4,
    }


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


def _raw_request_units(value: object) -> int:
    """Mirror the documented aggregate-unit metric for exact-boundary fixtures."""

    units = 0
    stack = [value]
    while stack:
        current = stack.pop()
        if type(current) is dict:
            if not current:
                units += 1
            for key, child in current.items():
                assert type(key) is str
                units += 1
                stack.append(child)
        elif type(current) in {list, tuple, set}:
            if not current:
                units += 1
            stack.extend(current)
        else:
            units += 1
    return units


def _packed_raw_primitives(count: int) -> list[list[list[int]]]:
    """Pack primitive occurrences below all 50-entry and depth-four limits."""

    leaves = [[0] * min(50, count - offset) for offset in range(0, count, 50)]
    middle = [leaves[offset : offset + 50] for offset in range(0, len(leaves), 50)]
    assert len(middle) <= 50
    return middle


def _nested_raw_mapping(depth: int, leaf: object = 0) -> dict[str, object]:
    """Build a non-recursive raw mapping chain for admission-boundary tests."""

    nested: object = leaf
    for index in range(depth):
        nested = {f"level-{index}": nested}
    assert isinstance(nested, dict)
    return cast(dict[str, object], nested)


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
            assert activity.moderate_aerobic_min == moderate
            assert activity.vigorous_aerobic_min == vigorous
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

    def test_raw_request_product_and_aggregate_boundaries(self) -> None:
        auto_base = _auto_repair_request()
        auto_day = deepcopy(auto_base["week_plan"]["days"][0])
        auto_meal = deepcopy(auto_day["meals"][0])
        auto_ingredient = deepcopy(auto_meal["ingredients"][0])

        for day_count in (7, 8):
            payload = deepcopy(auto_base)
            payload["week_plan"]["days"] = [deepcopy(auto_day) for _ in range(day_count)]
            if day_count == 7:
                assert len(AutoRepairWeeklyRequest.model_validate(payload).week_plan.days) == 7
            else:
                with pytest.raises(ValidationError):
                    AutoRepairWeeklyRequest.model_validate(payload)

        for meal_count in (10, 11):
            payload = deepcopy(auto_base)
            payload["week_plan"]["days"][0]["meals"] = [
                deepcopy(auto_meal) for _ in range(meal_count)
            ]
            if meal_count == 10:
                assert (
                    len(AutoRepairWeeklyRequest.model_validate(payload).week_plan.days[0].meals)
                    == 10
                )
            else:
                with pytest.raises(ValidationError):
                    AutoRepairWeeklyRequest.model_validate(payload)

        for ingredient_count in (15, 16):
            payload = deepcopy(auto_base)
            payload["week_plan"]["days"][0]["meals"][0]["ingredients"] = [
                deepcopy(auto_ingredient) for _ in range(ingredient_count)
            ]
            if ingredient_count == 15:
                assert (
                    len(
                        AutoRepairWeeklyRequest.model_validate(payload)
                        .week_plan.days[0]
                        .meals[0]
                        .ingredients
                    )
                    == 15
                )
            else:
                with pytest.raises(ValidationError):
                    AutoRepairWeeklyRequest.model_validate(payload)

        recipe_base = {
            "week_plan": {
                "days": [
                    {
                        "day": "day-0",
                        "meals": [{"ingredients": [{"name": "rice"}]}],
                    }
                ]
            },
            "recipes_per_day": 1,
        }
        recipe_day = deepcopy(recipe_base["week_plan"]["days"][0])
        recipe_meal = deepcopy(recipe_day["meals"][0])
        recipe_ingredient = deepcopy(recipe_meal["ingredients"][0])

        for day_count in (7, 8):
            payload = deepcopy(recipe_base)
            payload["week_plan"]["days"] = [
                {**deepcopy(recipe_day), "day": f"day-{index}"} for index in range(day_count)
            ]
            if day_count == 7:
                assert len(WeeklyRecipesRequest.model_validate(payload).week_plan.days) == 7
            else:
                with pytest.raises(ValidationError):
                    WeeklyRecipesRequest.model_validate(payload)

        for meal_count in (10, 11):
            payload = deepcopy(recipe_base)
            payload["week_plan"]["days"][0]["meals"] = [
                deepcopy(recipe_meal) for _ in range(meal_count)
            ]
            if meal_count == 10:
                assert (
                    len(WeeklyRecipesRequest.model_validate(payload).week_plan.days[0].meals) == 10
                )
            else:
                with pytest.raises(ValidationError):
                    WeeklyRecipesRequest.model_validate(payload)

        for ingredient_count in (15, 16):
            payload = deepcopy(recipe_base)
            payload["week_plan"]["days"][0]["meals"][0]["ingredients"] = [
                deepcopy(recipe_ingredient) for _ in range(ingredient_count)
            ]
            if ingredient_count == 15:
                assert (
                    len(
                        WeeklyRecipesRequest.model_validate(payload)
                        .week_plan.days[0]
                        .meals[0]
                        .ingredients
                    )
                    == 15
                )
            else:
                with pytest.raises(ValidationError):
                    WeeklyRecipesRequest.model_validate(payload)

        for entry_count in (50, 51):
            payload = deepcopy(auto_base)
            payload["user_preferences"] = {f"key-{index}": index for index in range(entry_count)}
            if entry_count == 50:
                AutoRepairWeeklyRequest.model_validate(payload)
            else:
                with pytest.raises(ValidationError):
                    AutoRepairWeeklyRequest.model_validate(payload)

        for collection_size in (50, 51):
            payload = deepcopy(auto_base)
            payload["user_preferences"] = {"items": list(range(collection_size))}
            if collection_size == 50:
                AutoRepairWeeklyRequest.model_validate(payload)
            else:
                with pytest.raises(ValidationError):
                    AutoRepairWeeklyRequest.model_validate(payload)

        for string_length in (500, 501):
            payload = deepcopy(auto_base)
            payload["user_preferences"] = {"text": "x" * string_length}
            if string_length == 500:
                AutoRepairWeeklyRequest.model_validate(payload)
            else:
                with pytest.raises(ValidationError):
                    AutoRepairWeeklyRequest.model_validate(payload)

        for key_length in (500, 501):
            payload = deepcopy(auto_base)
            payload["user_preferences"] = {"k" * key_length: 1}
            if key_length == 500:
                AutoRepairWeeklyRequest.model_validate(payload)
            else:
                with pytest.raises(ValidationError):
                    AutoRepairWeeklyRequest.model_validate(payload)

        baseline_units = _raw_request_units(auto_base)
        exact_payload = deepcopy(auto_base)
        exact_payload["user_preferences"] = {
            "budget": _packed_raw_primitives(4096 - baseline_units)
        }
        assert _raw_request_units(exact_payload) == 4096
        AutoRepairWeeklyRequest.model_validate(exact_payload)

        over_payload = deepcopy(auto_base)
        over_payload["user_preferences"] = {"budget": _packed_raw_primitives(4097 - baseline_units)}
        assert _raw_request_units(over_payload) == 4097
        with pytest.raises(ValidationError):
            AutoRepairWeeklyRequest.model_validate(over_payload)

    def test_raw_request_extra_depth_cycles_and_plain_types(self) -> None:
        auto_base = _auto_repair_request()
        depth_four = {"a": {"b": {"c": {"d": {"value": 0}}}}}
        accepted = deepcopy(auto_base)
        accepted["user_preferences"] = depth_four
        AutoRepairWeeklyRequest.model_validate(accepted)
        accepted_unknown = deepcopy(auto_base)
        accepted_unknown["unknown_extra"] = depth_four
        AutoRepairWeeklyRequest.model_validate(accepted_unknown)

        depth_five = {"a": {"b": {"c": {"d": {"value": {"too_deep": 0}}}}}}
        for root_key in ("user_preferences", "unknown_extra"):
            rejected = deepcopy(auto_base)
            rejected[root_key] = depth_five
            with pytest.raises(ValidationError):
                AutoRepairWeeklyRequest.model_validate(rejected)

        list_depth_five = {"a": {"b": {"c": {"d": {"value": [[0]]}}}}}
        rejected_list_depth = deepcopy(auto_base)
        rejected_list_depth["user_preferences"] = list_depth_five
        with pytest.raises(ValidationError):
            AutoRepairWeeklyRequest.model_validate(rejected_list_depth)

        cycle: dict[str, object] = {}
        cycle["self"] = cycle
        cyclic = deepcopy(auto_base)
        cyclic["user_preferences"] = cycle
        with pytest.raises(ValidationError):
            AutoRepairWeeklyRequest.model_validate(cyclic)

        list_cycle: list[object] = []
        list_cycle.append(list_cycle)
        cyclic_list = deepcopy(auto_base)
        cyclic_list["user_preferences"] = {"cycle": list_cycle}
        with pytest.raises(ValidationError):
            AutoRepairWeeklyRequest.model_validate(cyclic_list)

        non_string_key = deepcopy(auto_base)
        non_string_key["user_preferences"] = cast(dict[str, object], {1: "invalid"})
        with pytest.raises(ValidationError):
            AutoRepairWeeklyRequest.model_validate(non_string_key)

        alias = _packed_raw_primitives(1100)
        repeated_alias = deepcopy(auto_base)
        repeated_alias["user_preferences"] = {
            "a": alias,
            "b": alias,
            "c": alias,
            "d": alias,
        }
        assert _raw_request_units(repeated_alias) > 4096
        with pytest.raises(ValidationError):
            AutoRepairWeeklyRequest.model_validate(repeated_alias)

        direct_plain = deepcopy(auto_base)
        direct_plain["user_preferences"] = {"tuple": (1, 2), "set": {1, 2}}
        AutoRepairWeeklyRequest.model_validate(direct_plain)

        class _CopySpy:
            deepcopy_calls = 0

            def __deepcopy__(self, _memo: object) -> object:
                self.deepcopy_calls += 1
                raise AssertionError("raw validation must precede deepcopy")

        copy_spy = _CopySpy()
        unsupported_values = (
            MappingProxyType({"key": "value"}),
            frozenset({1}),
            b"bytes",
            (value for value in (1, 2)),
            object(),
            copy_spy,
            float("nan"),
            float("inf"),
            10**310,
        )
        for unsupported in unsupported_values:
            payload = deepcopy(auto_base)
            payload["user_preferences"] = {"value": unsupported}
            with pytest.raises(ValidationError):
                AutoRepairWeeklyRequest.model_validate(payload)
        assert copy_spy.deepcopy_calls == 0

    def test_raw_request_declared_shapes_reject_container_carriers(self) -> None:
        for depth in (5, 6, 101):
            age_payload = _auto_repair_request()
            age_payload["profile"]["age"] = _nested_raw_mapping(depth)

            diet_payload = _auto_repair_request()
            diet_payload["profile"]["diet_flags"] = [_nested_raw_mapping(depth)]

            medical_payload = _auto_repair_request()
            medical_payload["profile"]["medical_conditions"] = [[_nested_raw_mapping(depth)]]

            triplet_payload = _auto_repair_request()
            triplet_payload["targets"]["iron_mg"] = [
                _nested_raw_mapping(depth),
                8.0,
                45.0,
            ]

            for payload in (age_payload, diet_payload, medical_payload, triplet_payload):
                with pytest.raises(
                    ValidationError,
                    match="VIP request scalar field contains a container",
                ):
                    AutoRepairWeeklyRequest.model_validate(payload)

        mapping_as_collection = _auto_repair_request()
        mapping_as_collection["week_plan"] = []
        collection_as_mapping = _auto_repair_request()
        collection_as_mapping["week_plan"]["days"] = {}
        structured_as_scalar = _auto_repair_request()
        structured_as_scalar["week_plan"] = 1
        structured_as_string = _auto_repair_request()
        structured_as_string["week_plan"] = "invalid"
        structured_as_bool = _auto_repair_request()
        structured_as_bool["week_plan"] = False
        with pytest.raises(ValidationError, match="declared collection shape"):
            AutoRepairWeeklyRequest.model_validate(mapping_as_collection)
        with pytest.raises(ValidationError, match="declared mapping shape"):
            AutoRepairWeeklyRequest.model_validate(collection_as_mapping)
        for payload in (structured_as_scalar, structured_as_string, structured_as_bool):
            with pytest.raises(ValidationError, match="declared container shape"):
                AutoRepairWeeklyRequest.model_validate(payload)

        recipe_payload = {
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [{"ingredients": [{"name": "rice"}]}],
                    }
                ]
            },
            "recipes_per_day": _nested_raw_mapping(101),
        }
        with pytest.raises(
            ValidationError,
            match="VIP request scalar field contains a container",
        ):
            WeeklyRecipesRequest.model_validate(recipe_payload)

        class _CopySpy:
            deepcopy_calls = 0

            def __deepcopy__(self, _memo: object) -> object:
                self.deepcopy_calls += 1
                raise AssertionError("declared scalar rejection must precede deepcopy")

        copy_spy = _CopySpy()
        no_traversal_payload = _auto_repair_request()
        no_traversal_payload["profile"]["age"] = _nested_raw_mapping(101, copy_spy)
        with pytest.raises(
            ValidationError,
            match="VIP request scalar field contains a container",
        ):
            AutoRepairWeeklyRequest.model_validate(no_traversal_payload)
        assert copy_spy.deepcopy_calls == 0

        deepest_extra = _auto_repair_request()
        deepest_extra["week_plan"]["days"][0]["meals"][0]["ingredients"][0]["unknown_extra"] = (
            _nested_raw_mapping(6)
        )
        with pytest.raises(ValidationError, match="container depth exceeds its declared bound"):
            AutoRepairWeeklyRequest.model_validate(deepest_extra)

        nested_collection: object = 0
        for _ in range(6):
            nested_collection = [nested_collection]
        deepest_collection_extra = _auto_repair_request()
        deepest_collection_extra["week_plan"]["days"][0]["meals"][0]["ingredients"][0][
            "unknown_extra"
        ] = nested_collection
        with pytest.raises(ValidationError, match="container depth exceeds its declared bound"):
            AutoRepairWeeklyRequest.model_validate(deepest_collection_extra)

    def test_meal_nutrients_publish_and_enforce_nonnegative_fields(self) -> None:
        valid = _complete_evidence()
        for field_name in valid:
            zero_payload = {**valid, field_name: 0}
            parsed = AutoRepairMealNutrients.model_validate(zero_payload)
            assert getattr(parsed, field_name) == 0.0
            for invalid_value in (
                True,
                "0",
                object(),
                float("nan"),
                float("inf"),
                10**310,
                -1,
            ):
                with pytest.raises(ValidationError):
                    AutoRepairMealNutrients.model_validate({**valid, field_name: invalid_value})

    def test_raw_request_plus_one_rejects_before_runtime_adapters(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        auto_base = _auto_repair_request()
        auto_day = deepcopy(auto_base["week_plan"]["days"][0])
        oversized_days = deepcopy(auto_base)
        oversized_days["week_plan"]["days"] = [deepcopy(auto_day) for _ in range(8)]

        baseline_units = _raw_request_units(auto_base)
        oversized_aggregate = deepcopy(auto_base)
        oversized_aggregate["user_preferences"] = {
            "budget": _packed_raw_primitives(4097 - baseline_units)
        }
        assert _raw_request_units(oversized_aggregate) == 4097

        scalar_container_payloads: list[dict[str, Any]] = []
        for depth in (5, 6, 101):
            age_payload = _auto_repair_request()
            age_payload["profile"]["age"] = _nested_raw_mapping(depth)
            scalar_container_payloads.append(age_payload)

            flags_payload = _auto_repair_request()
            flags_payload["profile"]["diet_flags"] = [_nested_raw_mapping(depth)]
            scalar_container_payloads.append(flags_payload)

            triplet_payload = _auto_repair_request()
            triplet_payload["targets"]["iron_mg"] = [
                _nested_raw_mapping(depth),
                8.0,
                45.0,
            ]
            scalar_container_payloads.append(triplet_payload)

        for invalid_payload in (
            oversized_days,
            oversized_aggregate,
            *scalar_container_payloads,
        ):
            with monkeypatch.context() as auto_guard:
                runtime = Mock(
                    side_effect=AssertionError("auto-repair runtime must not be constructed")
                )
                catalog = Mock(
                    side_effect=AssertionError("catalog must not run before raw admission")
                )
                target_builder = Mock(
                    side_effect=AssertionError("target adapter must not run before raw admission")
                )
                repair_deepcopy = Mock(
                    side_effect=AssertionError("repair deepcopy must not run before raw admission")
                )
                auto_guard.setattr(vip_router, "get_auto_repair_engine", runtime)
                auto_guard.setattr(
                    vip_router,
                    "_build_auto_repair_nutrition_targets",
                    target_builder,
                )
                auto_guard.setattr(
                    "core.menu_engine.get_cached_common_foods_snapshot",
                    catalog,
                )
                auto_guard.setattr("core.auto_repair.deepcopy", repair_deepcopy)
                response = client.post(
                    "/api/v1/vip/auto-repair/weekly",
                    json=invalid_payload,
                    headers=vip_headers,
                )
            assert response.status_code == 422
            assert _json_payload(response) == {"detail": "Invalid auto-repair request payload"}
            runtime.assert_not_called()
            catalog.assert_not_called()
            target_builder.assert_not_called()
            repair_deepcopy.assert_not_called()

        recipe_day = {
            "day": "day-0",
            "meals": [{"ingredients": [{"name": "rice"}]}],
        }
        oversized_recipe = {
            "week_plan": {
                "days": [{**deepcopy(recipe_day), "day": f"day-{index}"} for index in range(8)]
            },
            "recipes_per_day": 1,
        }
        scalar_recipe: dict[str, Any] = {
            "week_plan": deepcopy(oversized_recipe["week_plan"]),
            "recipes_per_day": _nested_raw_mapping(101),
        }
        scalar_recipe["week_plan"]["days"] = [deepcopy(recipe_day)]
        for invalid_recipe in (oversized_recipe, scalar_recipe):
            with monkeypatch.context() as recipe_guard:
                synthesize = Mock(
                    side_effect=AssertionError("recipe synthesis must not run before raw admission")
                )
                recipe_guard.setattr(
                    vip_router,
                    "_adapter_synthesize_recipes_for_week",
                    synthesize,
                )
                response = client.post(
                    "/api/v1/vip/recipes/weekly",
                    json=invalid_recipe,
                    headers=vip_headers,
                )
            assert response.status_code == 422
            assert _json_payload(response) == {"detail": "Invalid weekly recipes request payload"}
            synthesize.assert_not_called()

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
            **_verified_cache_row(
                name="Iron booster",
                source_id="iron",
                iron_mg=10.0,
            )
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
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        instance = cast(UnifiedFoodDatabase, SimpleNamespace(cache_dir=cache_dir))
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", instance)
        cache_file = cache_dir / "common_foods.json"
        valid_row = _verified_cache_row()
        cache_file.write_text(json.dumps({"lentils": valid_row}), encoding="utf-8")
        caplog.clear()
        first = unified_db_module.get_cached_common_foods_snapshot()
        first["lentils"].nutrients_per_100g["iron_mg"] = 999.0
        second = unified_db_module.get_cached_common_foods_snapshot()
        assert second["lentils"].nutrients_per_100g["iron_mg"] == 3.3
        assert first["lentils"] is not second["lentils"]
        assert caplog.records == []

        deficient_plan = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot",
            return_value=second,
        ):
            repaired_from_verified_cache = repair_canonical_week_plan(
                deficient_plan,
                _micronutrient_targets(),
            )
        assert repaired_from_verified_cache != deficient_plan
        assert (
            repaired_from_verified_cache.daily_menus[0].meals[0]["ingredients"][-1]["name"]
            == "Lentils"
        )

        cache_file.write_text("{}", encoding="utf-8")
        caplog.clear()
        assert unified_db_module.get_cached_common_foods_snapshot() == {}
        assert caplog.records == []

        cache_file.write_text(json.dumps({"lentils": valid_row}), encoding="utf-8")

        def _raise_unreadable(
            _path: Path,
            *args: object,
            **kwargs: object,
        ) -> str:
            del args, kwargs
            raise OSError("secret-exception-value")

        with monkeypatch.context() as unreadable_cache:
            unreadable_cache.setattr(Path, "read_text", _raise_unreadable)
            assert unified_db_module.get_cached_common_foods_snapshot() == {}

        legacy_row = {
            key: deepcopy(value)
            for key, value in valid_row.items()
            if key
            not in {
                "nutrition_inputs",
                "nutrition_provenance",
                "nutrition_nutrient_confidence",
                "nutrition_confidence",
            }
        }
        missing_provenance = deepcopy(valid_row)
        missing_provenance["nutrition_provenance"].pop("iron_mg")
        missing_nutrient_confidence = deepcopy(valid_row)
        missing_nutrient_confidence["nutrition_nutrient_confidence"].pop("iron_mg")
        zero_nutrient_confidence = deepcopy(valid_row)
        zero_nutrient_confidence["nutrition_nutrient_confidence"]["iron_mg"] = 0.0
        zero_overall_confidence = {**valid_row, "nutrition_confidence": 0.0}
        extra_provenance = deepcopy(valid_row)
        extra_provenance["nutrition_provenance"]["unpublished_mg"] = "fixture"
        raw_coverage_missing = deepcopy(valid_row)
        raw_coverage_missing["nutrition_inputs"][0]["nutrients"].pop("iron_mg")
        raw_value_mismatch = deepcopy(valid_row)
        raw_value_mismatch["nutrition_inputs"][0]["nutrients"]["iron_mg"] = 9.9
        raw_source_mismatch = deepcopy(valid_row)
        raw_source_mismatch["nutrition_inputs"][0]["source"] = "usda"
        stored_provenance_mismatch = deepcopy(valid_row)
        stored_provenance_mismatch["nutrition_provenance"] = {
            nutrient: "usda" for nutrient in stored_provenance_mismatch["nutrients_per_100g"]
        }
        stored_confidence_mismatch = deepcopy(valid_row)
        stored_confidence_mismatch["nutrition_nutrient_confidence"] = {
            nutrient: 0.7 for nutrient in stored_confidence_mismatch["nutrients_per_100g"]
        }
        stored_overall_mismatch = {**valid_row, "nutrition_confidence": 0.7}
        invalid_rows: list[object] = [
            ["not-an-object"],
            legacy_row,
            {**valid_row, "nutrition_inputs": [{"junk": True}]},
            {
                **valid_row,
                "nutrition_inputs": [{"nutrients": {"iron_mg": 3.3}}],
            },
            {**valid_row, "nutrition_inputs": [{"source": "estimate"}]},
            raw_coverage_missing,
            raw_value_mismatch,
            raw_source_mismatch,
            missing_provenance,
            extra_provenance,
            stored_provenance_mismatch,
            missing_nutrient_confidence,
            zero_nutrient_confidence,
            stored_confidence_mismatch,
            zero_overall_confidence,
            stored_overall_mismatch,
            {**valid_row, "name": ""},
            {**valid_row, "name": 123},
            {**valid_row, "source": 123},
            {**valid_row, "source_id": {"unexpected": "shape"}},
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

        reason_codes = {
            record.getMessage().partition("reason=")[2]
            for record in caplog.records
            if record.name == "core.food_apis.unified_db" and "reason=" in record.getMessage()
        }
        assert {
            "instance_unconfigured",
            "cache_file_missing",
            "cache_unreadable_or_invalid_json",
            "payload_not_object",
            "entry_identity_or_shape_invalid",
            "item_identity_invalid",
            "nutrition_inputs_missing_or_invalid",
            "nutrition_input_source_invalid",
            "nutrition_input_nutrients_missing_or_invalid",
            "nutrition_input_coverage_invalid",
            "nutrition_provenance_coverage_invalid",
            "nutrient_confidence_coverage_invalid",
            "nutrient_confidence_range_invalid",
            "overall_confidence_invalid",
            "resolved_nutrients_mismatch",
            "resolved_provenance_mismatch",
            "resolved_nutrient_confidence_mismatch",
            "resolved_overall_confidence_mismatch",
        } <= reason_codes
        diagnostic_text = caplog.text
        assert str(cache_file) not in diagnostic_text
        assert "lentils" not in diagnostic_text.lower()
        assert "not-json" not in diagnostic_text
        assert "missing required fields" not in diagnostic_text
        assert "secret-exception-value" not in diagnostic_text

    def test_common_food_cache_publication_is_atomic_and_failure_safe(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "common_foods.json"
        old_payload = {"old": _verified_cache_row(name="Old food", source_id="old-1")}
        new_payload = {
            "new": _verified_cache_row(
                name="New food",
                source_id="new-1",
                iron_mg=4.4,
            )
        }
        cache_file.write_text(json.dumps(old_payload), encoding="utf-8")
        instance = cast(UnifiedFoodDatabase, SimpleNamespace(cache_dir=cache_dir))
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", instance)
        real_replace = unified_db_module.os.replace
        observed: dict[str, object] = {}

        def _inspect_replace(source: object, destination: object) -> None:
            observed["before"] = {
                key: item.name
                for key, item in unified_db_module.get_cached_common_foods_snapshot().items()
            }
            observed["temp"] = json.loads(Path(source).read_text(encoding="utf-8"))
            real_replace(source, destination)

        with monkeypatch.context() as successful_publish:
            successful_publish.setattr(unified_db_module.os, "replace", _inspect_replace)
            assert unified_db_module._publish_common_foods_cache(cache_file, new_payload)

        assert observed == {
            "before": {"old": "Old food"},
            "temp": new_payload,
        }
        assert {
            key: item.name
            for key, item in unified_db_module.get_cached_common_foods_snapshot().items()
        } == {"new": "New food"}
        assert list(cache_dir.glob(".common_foods.*.tmp")) == []

        cache_file.write_text(json.dumps(old_payload), encoding="utf-8")
        caplog.clear()

        def _fail_replace(_source: object, _destination: object) -> None:
            raise OSError("secret-replace-error")

        with monkeypatch.context() as failed_publish:
            failed_publish.setattr(unified_db_module.os, "replace", _fail_replace)
            assert not unified_db_module._publish_common_foods_cache(cache_file, new_payload)

        assert {
            key: item.name
            for key, item in unified_db_module.get_cached_common_foods_snapshot().items()
        } == {"old": "Old food"}
        assert list(cache_dir.glob(".common_foods.*.tmp")) == []
        assert "Failed to publish common-food cache" in caplog.text
        assert str(cache_file) not in caplog.text
        assert "secret-replace-error" not in caplog.text
        assert "Old food" not in caplog.text
        assert "New food" not in caplog.text

    def test_canonical_food_constructors_round_trip_sparse_verified_evidence(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        usda_item = USDAFoodItem(
            fdc_id=9001,
            description="Sparse USDA chicken",
            food_category="Poultry",
            nutrients_per_100g={"protein_g": 31.0, "kcal": 165.0},
            data_type="Foundation",
            publication_date="2019-04-01",
        )
        usda_unified = UnifiedFoodItem.from_usda_item(usda_item)
        off_item = OFFFoodItem(
            code="9998887776665",
            product_name="Legacy flat OFF row",
            categories=["Prepared foods"],
            nutrients_per_100g={"protein_g": 10.0, "fiber_g": 3.0},
            ingredients_text=None,
            brands=None,
            labels=[],
            countries=["BY"],
            packaging=[],
            image_url=None,
            last_modified_t=1,
        )
        off_unified = UnifiedFoodItem.from_off_item(off_item)
        merged = UnifiedFoodItem.from_usda_and_off_merge(usda_unified, off_unified)

        assert "fat_g" not in usda_unified.nutrients_per_100g
        assert "carbs_g" not in usda_unified.nutrients_per_100g
        assert "fat_g" not in off_unified.nutrients_per_100g
        assert "carbs_g" not in off_unified.nutrients_per_100g
        assert "fat_g" not in merged.nutrients_per_100g
        assert "carbs_g" not in merged.nutrients_per_100g
        assert set(usda_unified.nutrition_provenance.values()) == {"usda"}
        assert set(off_unified.nutrition_provenance.values()) == {"estimate"}
        assert merged.nutrition_provenance["protein_g"] == "usda"
        assert merged.nutrition_provenance["fiber_g"] == "estimate"

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "common_foods.json"
        serialized: dict[str, object] = {
            "usda": asdict(usda_unified),
            "off": asdict(off_unified),
            "merged": asdict(merged),
        }
        assert unified_db_module._publish_common_foods_cache(cache_file, serialized)
        database = cast(UnifiedFoodDatabase, SimpleNamespace(cache_dir=cache_dir))
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", database)

        snapshot = unified_db_module.get_cached_common_foods_snapshot()

        assert set(snapshot) == {"usda", "off", "merged"}
        assert snapshot["usda"].nutrients_per_100g == usda_unified.nutrients_per_100g
        assert snapshot["off"].nutrients_per_100g == off_unified.nutrients_per_100g
        assert snapshot["merged"].nutrients_per_100g == merged.nutrients_per_100g
        assert snapshot["usda"].nutrition_inputs
        assert snapshot["off"].nutrition_inputs
        assert snapshot["merged"].nutrition_inputs

    def test_common_food_database_build_uses_atomic_publisher(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        database = UnifiedFoodDatabase.__new__(UnifiedFoodDatabase)
        database.cache_dir = cache_dir
        search_calls = 0
        verified_item = UnifiedFoodItem(**_verified_cache_row())

        async def _search_food(
            _query: str,
            prefer_source: str = "usda",
            save_cache: bool = True,
        ) -> list[UnifiedFoodItem]:
            nonlocal search_calls
            del prefer_source
            assert save_cache is False
            search_calls += 1
            return [verified_item] if search_calls == 1 else []

        database.search_food = _search_food
        monkeypatch.setenv("UNIFIED_DB_COMMON_SLEEP_MS", "0")

        built = asyncio.run(database.get_common_foods_database())

        assert len(built) == 1
        assert next(iter(built.values())) is verified_item
        assert search_calls == 20
        assert list(cache_dir.glob(".common_foods.*.tmp")) == []
        monkeypatch.setattr(unified_db_module, "_unified_db_instance", database)
        snapshot = unified_db_module.get_cached_common_foods_snapshot()
        assert len(snapshot) == 1
        assert next(iter(snapshot.values())).name == "Lentils"

    def test_booster_is_deterministic_capped_and_input_immutable(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
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

        for existing_count in (
            MAX_INGREDIENTS_PER_MEAL - 1,
            MAX_INGREDIENTS_PER_MEAL,
        ):
            existing_ingredients = [
                {"name": f"existing-{index}"} for index in range(existing_count)
            ]
            bounded_plan = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
            bounded_plan.daily_menus[0].meals[0]["ingredients"] = deepcopy(existing_ingredients)
            bounded_snapshot = deepcopy(bounded_plan)
            bounded_result = repair_canonical_week_plan(
                bounded_plan,
                targets,
                food_db={"complete": _food_item("Complete", {"iron_mg": 10.0})},
            )
            result_ingredients = bounded_result.daily_menus[0].meals[0]["ingredients"]
            assert result_ingredients[:existing_count] == existing_ingredients
            if existing_count == MAX_INGREDIENTS_PER_MEAL - 1:
                assert len(result_ingredients) == MAX_INGREDIENTS_PER_MEAL
                assert result_ingredients[-1]["name"] == "Complete"
            else:
                assert bounded_result == bounded_plan
                assert result_ingredients == existing_ingredients
            assert bounded_plan == bounded_snapshot

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

        explicit_kcal_plan = _canonical_plan(_complete_evidence({"iron_mg": 0.0, "kcal": 1796.0}))
        explicit_kcal_food = _food_item(
            "Explicit kcal",
            {"iron_mg": 10.0, "protein_g": 25.0, "kcal": 10.0},
        )
        explicit_kcal_repaired = repair_canonical_week_plan(
            explicit_kcal_plan,
            targets,
            food_db={"explicit": explicit_kcal_food},
        )
        explicit_kcal_meal = explicit_kcal_repaired.daily_menus[0].meals[0]
        assert explicit_kcal_meal["ingredients"][-1]["amount"] == 40.0
        assert explicit_kcal_meal["nutrients"]["kcal"] == 1800.0
        assert (
            _known_nutrient_contributions(
                explicit_kcal_plan,
                explicit_kcal_repaired,
            )["kcal"]
            == 4.0
        )

        invalid_explicit_kcal = _food_item(
            "Invalid explicit kcal",
            {"iron_mg": 10.0, "protein_g": 25.0, "kcal": float("inf")},
        )
        assert (
            repair_canonical_week_plan(
                explicit_kcal_plan,
                targets,
                food_db={"invalid-explicit": invalid_explicit_kcal},
            )
            == explicit_kcal_plan
        )

        derived_kcal_plan = _canonical_plan(_complete_evidence({"iron_mg": 0.0, "kcal": 1760.0}))
        derived_kcal_food = _food_item(
            "Derived kcal",
            {"iron_mg": 10.0, "protein_g": 25.0},
        )
        derived_kcal_repaired = repair_canonical_week_plan(
            derived_kcal_plan,
            targets,
            food_db={"derived": derived_kcal_food},
        )
        assert derived_kcal_repaired.daily_menus[0].meals[0]["ingredients"][-1]["amount"] == 40.0
        assert derived_kcal_repaired.daily_menus[0].meals[0]["nutrients"]["kcal"] == 1800.0

        normalized_region_plan = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        normalized_region_plan.daily_menus[0].targets = replace(
            normalized_region_plan.daily_menus[0].targets,
            calculated_for=replace(
                normalized_region_plan.daily_menus[0].targets.calculated_for,
                region=" by ",
            ),
        )
        normalized_region_food = _food_item("Regional", {"iron_mg": 10.0})
        normalized_region_food.availability_regions = [" US ", " By "]
        assert (
            repair_canonical_week_plan(
                normalized_region_plan,
                targets,
                food_db={"regional": normalized_region_food},
            )
            != normalized_region_plan
        )

        for invalid_regions in (["US"], [], cast(list[str], [123])):
            unavailable_food = _food_item("Unavailable", {"iron_mg": 10.0})
            unavailable_food.availability_regions = invalid_regions
            assert (
                repair_canonical_week_plan(
                    normalized_region_plan,
                    targets,
                    food_db={"unavailable": unavailable_food},
                )
                == normalized_region_plan
            )

        missing_requested_region = deepcopy(normalized_region_plan)
        missing_requested_region.daily_menus[0].targets = replace(
            missing_requested_region.daily_menus[0].targets,
            calculated_for=replace(
                missing_requested_region.daily_menus[0].targets.calculated_for,
                region="   ",
            ),
        )
        assert (
            repair_canonical_week_plan(
                missing_requested_region,
                targets,
                food_db={"regional": normalized_region_food},
            )
            == missing_requested_region
        )

        complete_candidate = _food_item("Complete", {"iron_mg": 10.0})
        for missing_nutrient in _TARGET_RANGES:
            incomplete_candidate = deepcopy(complete_candidate)
            incomplete_candidate.nutrients_per_100g.pop(missing_nutrient)
            assert (
                repair_canonical_week_plan(
                    normalized_region_plan,
                    targets,
                    food_db={"incomplete": incomplete_candidate},
                )
                == normalized_region_plan
            )

        derived_overflow = _food_item(
            "Derived overflow",
            {"iron_mg": 10.0, "protein_g": 1e308},
        )
        assert _food_nutrient_evidence(derived_overflow) is None

        no_candidate_plan = _canonical_plan(_complete_evidence({"iron_mg": 0.0}))
        caplog.clear()
        with patch(
            "core.menu_engine.get_cached_common_foods_snapshot",
            return_value={},
        ):
            no_candidate_result = repair_canonical_week_plan(
                no_candidate_plan,
                targets,
            )
        assert no_candidate_result == no_candidate_plan
        menu_warnings = [
            record.getMessage() for record in caplog.records if record.name == "core.menu_engine"
        ]
        assert menu_warnings == ["Auto-repair has no cached booster candidates"]

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
            **_verified_cache_row(
                name="Iron booster",
                source_id="iron",
                iron_mg=10.0,
            )
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

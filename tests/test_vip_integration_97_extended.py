"""
Расширенные интеграционные тесты для VIP endpoints для достижения 97% покрытия
"""

from copy import deepcopy
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app.routers.vip as vip_router
import core.menu_engine as menu_engine
from core.menu_engine import FoodItem
from tests._helpers.vip_contracts import assert_json_response_payload


def _complete_nutrient_evidence(
    overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Build complete explicit per-meal baseline evidence."""
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


def _auto_repair_payload(week_plan: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical deterministic VIP auto-repair request."""
    canonical_plan = deepcopy(week_plan)
    days = canonical_plan.get("days", [])
    for day in days if isinstance(days, list) else []:
        if not isinstance(day, dict):
            continue
        for meal in day.get("meals", []):
            if not isinstance(meal, dict):
                continue
            nutrients = meal.get("nutrients")
            meal["nutrients"] = _complete_nutrient_evidence(
                nutrients if isinstance(nutrients, dict) else None
            )
    return {
        "week_plan": canonical_plan,
        "targets": {
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
        },
        "strategy": "balanced",
        "user_preferences": {},
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
            "kcal_daily": 1800,
            "macros": {
                "protein_g": 100,
                "fat_g": 60,
                "carbs_g": 215,
                "fiber_g": 30,
            },
            "water_ml_daily": 2000,
            "activity": {
                "moderate_aerobic_min": 150,
                "vigorous_aerobic_min": 75,
                "strength_sessions": 2,
                "steps_daily": 8000,
            },
            "calculation_date": "2026-08-22",
        },
    }


def _shoplist_day(
    food_id: str,
    *,
    quantity: str,
    pack_size: str,
) -> dict[str, Any]:
    """Build one canonical deterministic weekly-shoplist day."""
    return {
        "items": [
            {
                "food_id": food_id,
                "qty": {"value": quantity, "unit": "G"},
                "form": "RAW",
            }
        ],
        "packaging_rules": [
            {
                "food_id": food_id,
                "pack_size": {"value": pack_size, "unit": "G"},
                "rounding": "CEIL",
                "min_packs": 1,
            }
        ],
    }


@pytest.fixture
def canonical_auto_repair_food_db() -> dict[str, FoodItem]:
    """Provide one deterministic canonical booster record for route integration."""
    return {
        "iron_booster": FoodItem(
            name="Iron Booster",
            nutrients_per_100g={
                "iron_mg": 10.0,
                "protein_g": 0.0,
                "fat_g": 0.0,
                "carbs_g": 0.0,
                "fiber_g": 0.0,
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
            cost_per_100g=1.0,
            tags=[],
            availability_regions=[" by "],
        )
    }


@pytest.mark.smoke
class TestVIPIntegration97Extended:
    """Расширенные интеграционные тесты для VIP endpoints"""

    def test_vip_weekly_menu_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты VIP weekly menu endpoint"""
        payload_full = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "deficit_pct": 10,
            "surplus_pct": 5,
            "bodyfat": 15.0,
            "region": "BY",
            "timezone": "UTC",
            "diet_flags": ["VEG"],
            "life_stage": "adult",
            "medical_conditions": [],
        }

        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=payload_full,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "echo" in data
        assert "menu" in data

        payload_minimal = {
            "sex": "female",
            "age": 25,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "active",
            "goal": "loss",
        }

        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=payload_minimal,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"

        payload_alternative = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "calories": 2000,
            "protein": 150.0,
            "user_id": "test_user_123",
            "preferences": {"cuisine": "mediterranean"},
            "goals": {"weight_loss": True},
            "constraints": {"allergies": ["nuts"]},
        }

        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=payload_alternative,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"

        activity_goals = [
            ("sedentary", "maintain"),
            ("light", "loss"),
            ("moderate", "gain"),
            ("active", "maintain"),
            ("very_active", "loss"),
        ]

        for activity, goal in activity_goals:
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": activity,
                "goal": goal,
            }
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data["status"] == "success"

    def test_vip_recipes_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты VIP recipes endpoint"""
        payload_complex = {
            "week_plan": {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [
                                    {"name": "chicken", "amount": 100, "unit": "g"},
                                    {"name": "rice", "amount": 150, "unit": "g"},
                                    {"name": "onion", "amount": 50, "unit": "g"},
                                ],
                            },
                            {
                                "meal_type": "lunch",
                                "ingredients": [
                                    {"name": "salmon", "amount": 120, "unit": "g"},
                                    {"name": "broccoli", "amount": 200, "unit": "g"},
                                    {"name": "olive_oil", "amount": 15, "unit": "ml"},
                                ],
                            },
                            {
                                "meal_type": "dinner",
                                "ingredients": [
                                    {"name": "beef", "amount": 150, "unit": "g"},
                                    {"name": "potato", "amount": 200, "unit": "g"},
                                    {"name": "carrot", "amount": 100, "unit": "g"},
                                ],
                            },
                        ],
                    },
                    {
                        "day": "tuesday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [
                                    {"name": "eggs", "amount": 2, "unit": "pieces"},
                                    {"name": "bread", "amount": 2, "unit": "slices"},
                                    {"name": "butter", "amount": 10, "unit": "g"},
                                ],
                            },
                            {
                                "meal_type": "lunch",
                                "ingredients": [
                                    {"name": "turkey", "amount": 130, "unit": "g"},
                                    {"name": "quinoa", "amount": 100, "unit": "g"},
                                    {"name": "spinach", "amount": 150, "unit": "g"},
                                ],
                            },
                        ],
                    },
                ]
            }
        }
        payload_simple = {
            "week_plan": {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [{"name": "chicken", "amount": 100, "unit": "g"}],
                            }
                        ],
                    }
                ]
            }
        }
        payload_units = {
            "week_plan": {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [
                                    {"name": "milk", "amount": 250, "unit": "ml"},
                                    {"name": "cereal", "amount": 50, "unit": "g"},
                                    {"name": "banana", "amount": 1, "unit": "piece"},
                                    {"name": "honey", "amount": 10, "unit": "g"},
                                ],
                            }
                        ],
                    }
                ]
            }
        }

        for payload in (payload_complex, payload_simple, payload_units):
            response = client.post(
                "/api/v1/vip/recipes/weekly",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data["status"] == "success"
            assert data["weekly_recipes"]
            assert data["total_recipes"] > 0
            assert data["echo"] == payload

        with monkeypatch.context() as missing_capability:
            missing_capability.setattr(vip_router, "synthesize_recipes_for_week", None)
            response = client.post(
                "/api/v1/vip/recipes/weekly",
                json=payload_simple,
                headers=vip_headers,
            )
            assert response.status_code == 200
            assert assert_json_response_payload(response) == {
                "status": "error",
                "weekly_recipes": {},
                "total_recipes": 0,
                "echo": payload_simple,
                "message": "Recipe synthesis is unavailable",
            }

        with monkeypatch.context() as empty_capability:
            empty_capability.setattr(
                vip_router,
                "_adapter_synthesize_recipes_for_week",
                lambda *_args, **_kwargs: {},
            )
            response = client.post(
                "/api/v1/vip/recipes/weekly",
                json=payload_simple,
                headers=vip_headers,
            )
            assert response.status_code == 200
            assert assert_json_response_payload(response) == {
                "status": "error",
                "message": "Recipe synthesis returned no recipes",
                "weekly_recipes": {},
                "total_recipes": 0,
                "echo": payload_simple,
            }

        malformed_recipe_results = (
            {"monday": [{"status": "error"}]},
            {"monday": [{"unexpected": "shape"}]},
        )
        for malformed_result in malformed_recipe_results:
            with monkeypatch.context() as malformed_capability:
                malformed_capability.setattr(
                    vip_router,
                    "_adapter_synthesize_recipes_for_week",
                    Mock(return_value=malformed_result),
                )
                response = client.post(
                    "/api/v1/vip/recipes/weekly",
                    json=payload_simple,
                    headers=vip_headers,
                )
                assert response.status_code == 200
                assert assert_json_response_payload(response) == {
                    "status": "error",
                    "message": "An internal error occurred during recipe synthesis",
                    "weekly_recipes": {},
                    "total_recipes": 0,
                    "echo": payload_simple,
                }

        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json={"week_plan": {"days": "not-a-list"}},
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid weekly recipes request payload"
        }

        invalid_day_payloads = (
            {
                "week_plan": {
                    "days": [
                        {
                            "meals": payload_simple["week_plan"]["days"][0]["meals"],
                        }
                    ]
                }
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "   ",
                            "meals": payload_simple["week_plan"]["days"][0]["meals"],
                        }
                    ]
                }
            },
            {
                "week_plan": {
                    "days": [
                        payload_simple["week_plan"]["days"][0],
                        {
                            "day": " monday ",
                            "meals": payload_simple["week_plan"]["days"][0]["meals"],
                        },
                    ]
                }
            },
        )
        for invalid_payload in invalid_day_payloads:
            with monkeypatch.context() as invalid_day_capability:
                synthesize = Mock(
                    side_effect=AssertionError(
                        "recipe synthesis must not run for invalid day identifiers"
                    )
                )
                invalid_day_capability.setattr(
                    vip_router,
                    "_adapter_synthesize_recipes_for_week",
                    synthesize,
                )
                response = client.post(
                    "/api/v1/vip/recipes/weekly",
                    json=invalid_payload,
                    headers=vip_headers,
                )
            assert response.status_code == 422
            assert assert_json_response_payload(response) == {
                "detail": "Invalid weekly recipes request payload"
            }
            synthesize.assert_not_called()

        for invalid_count in (0, True, 10**310):
            response = client.post(
                "/api/v1/vip/recipes/weekly",
                json={
                    "week_plan": payload_simple["week_plan"],
                    "recipes_per_day": invalid_count,
                },
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert assert_json_response_payload(response) == {
                "detail": "Invalid weekly recipes request payload"
            }

        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=[],
            headers=vip_headers,
        )
        assert response.status_code == 422
        standard_validation = assert_json_response_payload(response)
        assert isinstance(standard_validation["detail"], list)

    def test_vip_auto_repair_integration_extended_scenarios(
        self,
        canonical_auto_repair_food_db: dict[str, FoodItem],
        client: TestClient,
        test_environment: None,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты VIP auto repair endpoint"""
        monkeypatch.setattr(
            menu_engine,
            "get_cached_common_foods_snapshot",
            lambda: canonical_auto_repair_food_db,
        )
        payload_problems = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [{"name": "chicken", "amount": 100, "unit": "g"}],
                                "nutrients": {"iron_mg": 0.0},
                                "nutrition_gaps": ["protein", "vitamin_c", "fiber"],
                            },
                            {
                                "meal_type": "lunch",
                                "ingredients": [{"name": "rice", "amount": 150, "unit": "g"}],
                                "nutrients": {"iron_mg": 0.0},
                                "nutrition_gaps": ["vitamin_a", "calcium"],
                            },
                        ],
                    }
                ]
            }
        )
        payload_simple_problems = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [{"name": "chicken", "amount": 100, "unit": "g"}],
                                "nutrients": {"iron_mg": 0.0},
                                "nutrition_gaps": ["protein"],
                            }
                        ],
                    }
                ]
            }
        )
        payload_multi_ingredient_deficit = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [
                                    {"name": "chicken", "amount": 100, "unit": "g"},
                                    {"name": "rice", "amount": 150, "unit": "g"},
                                    {"name": "broccoli", "amount": 100, "unit": "g"},
                                    {"name": "spinach", "amount": 100, "unit": "g"},
                                ],
                                "nutrients": {"iron_mg": 0.0},
                            }
                        ],
                    }
                ]
            }
        )

        for payload in (
            payload_problems,
            payload_simple_problems,
            payload_multi_ingredient_deficit,
        ):
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data["status"] == "success"
            repair_result = data["repair_result"]
            assert isinstance(repair_result, dict)
            assert repair_result["status"] == "partial"
            assert repair_result["iterations"] == 1
            assert repair_result["changes_made"]
            repaired_meal = repair_result["repaired_plan"]["days"][0]["meals"][0]
            assert repaired_meal["ingredients"][-1] == {
                "name": "Iron Booster",
                "amount": 80.0,
                "unit": "g",
            }
            assert repaired_meal["nutrients"]["iron_mg"] == 8.0
            assert data["echo"] == payload
            assert data["message"] == "Auto-repair completed with status: partial"

        stale_summary_payload = _auto_repair_payload(payload_simple_problems["week_plan"])
        stale_summary_payload["week_plan"].update(
            {
                "weekly_coverage": {"stale": 1.0},
                "shopping_list": "invalid",
                "total_cost": 99.0,
                "adherence_score": {"invalid": True},
            }
        )
        stale_day = stale_summary_payload["week_plan"]["days"][0]
        stale_day.update(
            {
                "coverage": {"stale": 1.0},
                "recommendations": "invalid",
                "estimated_cost": {"invalid": True},
            }
        )
        cached_only = Mock(return_value=canonical_auto_repair_food_db)
        with monkeypatch.context() as stale_guard:
            stale_guard.setattr(
                menu_engine,
                "get_cached_common_foods_snapshot",
                cached_only,
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=stale_summary_payload,
                headers=vip_headers,
            )
        assert response.status_code == 200
        stale_data = assert_json_response_payload(response)
        assert stale_data["status"] == "success"
        repaired_stale_plan = stale_data["repair_result"]["repaired_plan"]
        for stale_field in (
            "weekly_coverage",
            "shopping_list",
            "total_cost",
            "adherence_score",
        ):
            assert stale_field not in repaired_stale_plan
        for stale_field in ("coverage", "recommendations", "estimated_cost"):
            assert stale_field not in repaired_stale_plan["days"][0]
        cached_only.assert_called()

        complete_payload = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "ingredients": [{"name": "complete"}],
                                "nutrients": _complete_nutrient_evidence(
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
                                ),
                            }
                        ],
                    }
                ]
            }
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=complete_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        complete_data = assert_json_response_payload(response)
        assert complete_data["status"] == "success"
        assert complete_data["repair_result"]["status"] == "success"
        assert complete_data["repair_result"]["iterations"] == 0
        assert complete_data["repair_result"]["changes_made"] == []
        assert complete_data["repair_result"]["remaining_gaps"] == {}
        assert complete_data["repair_result"]["message"] == ""
        assert complete_data["repair_result"]["repaired_plan"] == complete_payload["week_plan"]
        assert complete_data["repair_result"]["original_plan"] == complete_payload["week_plan"]

        for kcal_daily, macros in (
            (1801, {"protein_g": 100, "fat_g": 60, "carbs_g": 215, "fiber_g": 30}),
            (2000, {"protein_g": 100, "fat_g": 60, "carbs_g": 240, "fiber_g": 30}),
        ):
            tolerance_payload = deepcopy(complete_payload)
            tolerance_payload["daily_targets"]["kcal_daily"] = kcal_daily
            tolerance_payload["daily_targets"]["macros"] = macros
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=tolerance_payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            tolerance_data = assert_json_response_payload(response)
            assert tolerance_data["status"] == "success"
            assert tolerance_data["repair_result"]["status"] == "success"

        over_tolerance_payload = deepcopy(complete_payload)
        over_tolerance_payload["daily_targets"]["kcal_daily"] = 2001
        over_tolerance_payload["daily_targets"]["macros"] = {
            "protein_g": 100,
            "fat_g": 60,
            "carbs_g": 240,
            "fiber_g": 30,
        }
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=over_tolerance_payload,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid auto-repair request payload"
        }

        for moderate, vigorous in ((150, 0), (0, 75), (0, 0)):
            activity_payload = deepcopy(complete_payload)
            activity_payload["daily_targets"]["activity"].update(
                {
                    "moderate_aerobic_min": moderate,
                    "vigorous_aerobic_min": vigorous,
                }
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=activity_payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            assert assert_json_response_payload(response)["status"] == "success"

        for field_name, invalid_value in (
            ("moderate_aerobic_min", -1),
            ("moderate_aerobic_min", True),
            ("moderate_aerobic_min", 1.5),
            ("vigorous_aerobic_min", "0"),
        ):
            invalid_activity_payload = deepcopy(complete_payload)
            invalid_activity_payload["daily_targets"]["activity"][field_name] = invalid_value
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=invalid_activity_payload,
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert assert_json_response_payload(response) == {
                "detail": "Invalid auto-repair request payload"
            }

        known_deficits_payload = _auto_repair_payload(
            {
                "plan_id": "route-plan",
                "days": [
                    {
                        "day": "monday",
                        "day_id": "route-day",
                        "meals": [
                            {
                                "ingredients": [{"name": "rice"}],
                                "nutrients": _complete_nutrient_evidence(
                                    {
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
                                        "vitamin_c_mg": 0.0,
                                    }
                                ),
                            }
                        ],
                    }
                ],
            }
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=known_deficits_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        known_deficits_data = assert_json_response_payload(response)
        assert known_deficits_data["status"] == "success"
        assert known_deficits_data["repair_result"]["status"] == "partial"
        assert known_deficits_data["repair_result"]["remaining_gaps"] == {"vitamin_c_mg": 90.0}
        assert known_deficits_data["repair_result"]["repaired_plan"]["plan_id"] == "route-plan"
        assert (
            known_deficits_data["repair_result"]["repaired_plan"]["days"][0]["day_id"]
            == "route-day"
        )

        with monkeypatch.context() as unavailable_real_food_db:
            unavailable_real_food_db.setattr(
                menu_engine,
                "get_cached_common_foods_snapshot",
                lambda: {},
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload_simple_problems,
                headers=vip_headers,
            )
            assert response.status_code == 200
            unavailable_data = assert_json_response_payload(response)
            assert unavailable_data["status"] == "error"
            assert unavailable_data["code"] == "auto_repair_failed"
            assert unavailable_data["repair_result"]["changes_made"] == []
            assert "Chicken Breast (Mock)" not in str(unavailable_data)
            assert "Lentils (Mock)" not in str(unavailable_data)

        payload_no_candidate = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [{"name": "rice", "amount": 100, "unit": "g"}],
                                "nutrients": {"iron_mg": 45.0},
                            }
                        ],
                    }
                ]
            }
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=payload_no_candidate,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "error"
        assert data["code"] == "auto_repair_failed"
        assert data["repair_result"]["status"] == "failed"
        assert data["repair_result"]["iterations"] == 3

        overflow_payload = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "ingredients": [{"name": "one"}],
                                "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                            },
                            {
                                "ingredients": [{"name": "two"}],
                                "nutrients": {"iron_mg": 0.0, "protein_g": 1e308},
                            },
                        ],
                    }
                ]
            }
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=overflow_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        overflow_data = assert_json_response_payload(response)
        assert overflow_data["status"] == "error"
        assert overflow_data["code"] == "internal_error"
        assert overflow_data["repair_result"] == {}
        assert "Infinity" not in response.text
        assert "NaN" not in response.text

        malformed_plan = _auto_repair_payload({"days": "not-a-list"})
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=malformed_plan,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid auto-repair request payload"
        }

        overflow_admission = _auto_repair_payload(payload_multi_ingredient_deficit["week_plan"])
        overflow_admission["week_plan"]["days"][0]["meals"][0]["nutrients"]["kcal"] = 10**310
        cached_reader = Mock(side_effect=AssertionError("core cache must not be called"))
        with monkeypatch.context() as overflow_guard:
            overflow_guard.setattr(
                menu_engine,
                "get_cached_common_foods_snapshot",
                cached_reader,
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=overflow_admission,
                headers=vip_headers,
            )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid auto-repair request payload"
        }
        cached_reader.assert_not_called()

        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=[],
            headers=vip_headers,
        )
        assert response.status_code == 422
        standard_auto_validation = assert_json_response_payload(response)
        assert isinstance(standard_auto_validation["detail"], list)

        for forbidden_target_field, forbidden_value in (
            ("priority_nutrients", {"iron_mg": 5}),
            ("deficiency_threshold", 0.8),
        ):
            payload_with_extra_target = _auto_repair_payload(
                payload_multi_ingredient_deficit["week_plan"]
            )
            payload_with_extra_target["targets"][forbidden_target_field] = forbidden_value
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload_with_extra_target,
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert assert_json_response_payload(response) == {
                "detail": "Invalid auto-repair request payload"
            }

        invalid_nutrients = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "ingredients": [{"name": "rice", "amount": 100, "unit": "g"}],
                                "nutrients": {"iron_mg": -1.0},
                            }
                        ],
                    }
                ]
            }
        )
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=invalid_nutrients,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid auto-repair request payload"
        }

        stable_failure_message = "Auto-repair could not complete the requested repair"
        preferences_payload = _auto_repair_payload(payload_multi_ingredient_deficit["week_plan"])
        preferences_payload["user_preferences"] = {"exclude": ["bread"]}
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=preferences_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "error"
        assert data["code"] == "auto_repair_failed"
        assert data["message"] == stable_failure_message
        assert data["detail"] == stable_failure_message
        assert data["repair_result"]["status"] == "needs_manual"
        assert data["repair_result"]["iterations"] == 0
        assert data["repair_result"]["message"] == stable_failure_message
        assert "Canonical auto-repair does not support these preferences" not in str(data)

        for profile_field, constraint in (
            ("diet_flags", ["VEG"]),
            ("medical_conditions", ["requires-review"]),
        ):
            constrained_payload = deepcopy(complete_payload)
            constrained_payload["profile"][profile_field] = constraint
            with monkeypatch.context() as constraint_guard:
                catalog = Mock(
                    side_effect=AssertionError(
                        "catalog must not run for unsupported dietary or medical constraints"
                    )
                )
                constraint_guard.setattr(
                    menu_engine,
                    "get_cached_common_foods_snapshot",
                    catalog,
                )
                response = client.post(
                    "/api/v1/vip/auto-repair/weekly",
                    json=constrained_payload,
                    headers=vip_headers,
                )
            assert response.status_code == 200
            constrained_data = assert_json_response_payload(response)
            assert constrained_data["status"] == "error"
            assert constrained_data["code"] == "auto_repair_failed"
            assert constrained_data["repair_result"]["status"] == "needs_manual"
            assert constrained_data["repair_result"]["iterations"] == 0
            assert (
                constrained_data["repair_result"]["repaired_plan"] == complete_payload["week_plan"]
            )
            assert (
                constrained_data["repair_result"]["original_plan"] == complete_payload["week_plan"]
            )
            catalog.assert_not_called()

        zero_interval = _auto_repair_payload(payload_multi_ingredient_deficit["week_plan"])
        zero_interval["targets"]["iron_mg"] = [0.0, 0.0, 0.0]
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=zero_interval,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid auto-repair request payload"
        }

        negative_interval = _auto_repair_payload(payload_multi_ingredient_deficit["week_plan"])
        negative_interval["targets"]["iron_mg"] = [-1.0, 8.0, 45.0]
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=negative_interval,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid auto-repair request payload"
        }

        malformed_interval = _auto_repair_payload(payload_multi_ingredient_deficit["week_plan"])
        malformed_interval["targets"]["iron_mg"] = [8.0, 6.0, 45.0]
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=malformed_interval,
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert assert_json_response_payload(response) == {
            "detail": "Invalid auto-repair request payload"
        }

        partial_result = {
            "status": "partial",
            "repaired_plan": {
                **payload_simple_problems["week_plan"],
                "canonical_repair_applied": True,
            },
            "original_plan": payload_simple_problems["week_plan"],
            "changes_made": [{"type": "canonical_repair"}],
            "remaining_gaps": {},
            "strategy_used": "balanced",
            "iterations": 1,
            "message": "Canonical repair produced a changed plan",
            "suggestions": [],
            "private_debug": "secret-token",
        }
        with monkeypatch.context() as partial_success:
            partial_success.setattr(vip_router, "get_auto_repair_engine", None)
            partial_success.setattr(
                vip_router,
                "auto_repair_week_plan",
                Mock(return_value=partial_result),
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload_simple_problems,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data["status"] == "success"
            expected_partial_result = {
                key: value for key, value in partial_result.items() if key != "private_debug"
            }
            assert data["repair_result"] == expected_partial_result
            assert data["message"] == "Auto-repair completed with status: partial"
            assert "private_debug" not in data["repair_result"]
            assert "secret-token" not in str(data)

        malformed_results = (
            {"status": "success"},
            {**partial_result, "status": ""},
            {**partial_result, "original_plan": []},
            {**partial_result, "repaired_plan": {"days": []}},
            {**partial_result, "original_plan": {"days": [{"meals": []}]}},
            {**partial_result, "changes_made": {}},
            {**partial_result, "remaining_gaps": []},
            {**partial_result, "strategy_used": ""},
            {**partial_result, "iterations": True},
            {**partial_result, "iterations": 0},
            {**partial_result, "message": ""},
            {**partial_result, "suggestions": {}},
            {**partial_result, "status": "success"},
            {
                **partial_result,
                "repaired_plan": payload_simple_problems["week_plan"],
            },
            {**partial_result, "changes_made": []},
        )
        for malformed_result in malformed_results:
            with monkeypatch.context() as malformed_success:
                malformed_success.setattr(vip_router, "get_auto_repair_engine", None)
                malformed_success.setattr(
                    vip_router,
                    "auto_repair_week_plan",
                    Mock(return_value=malformed_result),
                )
                response = client.post(
                    "/api/v1/vip/auto-repair/weekly",
                    json=payload_simple_problems,
                    headers=vip_headers,
                )
                assert response.status_code == 200
                data = assert_json_response_payload(response)
                assert data == {
                    "status": "error",
                    "code": "internal_error",
                    "message": "Error during auto-repair",
                    "detail": "Error during auto-repair",
                    "error": "internal_error",
                    "repair_result": {},
                    "echo": payload_simple_problems,
                }

        failed_result = {
            "status": "failed",
            "repaired_plan": payload_simple_problems["week_plan"],
            "original_plan": payload_simple_problems["week_plan"],
            "changes_made": [],
            "remaining_gaps": {"vitamin_c": 50.0},
            "strategy_used": "balanced",
            "iterations": 3,
            "message": "/private/db/path",
            "suggestions": [],
        }
        with monkeypatch.context() as no_progress:
            no_progress.setattr(vip_router, "get_auto_repair_engine", None)
            no_progress.setattr(
                vip_router,
                "auto_repair_week_plan",
                Mock(return_value=failed_result),
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload_simple_problems,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data["status"] == "error"
            assert data["code"] == "auto_repair_failed"
            assert data["message"] == stable_failure_message
            assert data["detail"] == stable_failure_message
            assert data["repair_result"] == {
                **failed_result,
                "message": stable_failure_message,
            }
            assert data["repair_result"]["message"] == stable_failure_message
            assert "/private/db/path" not in str(data)

        with monkeypatch.context() as structural_failure:
            structural_failure.setattr(vip_router, "get_auto_repair_engine", None)
            structural_failure.setattr(
                vip_router,
                "auto_repair_week_plan",
                Mock(side_effect=RuntimeError("private structural detail")),
            )
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload_simple_problems,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data == {
                "status": "error",
                "code": "internal_error",
                "message": "Error during auto-repair",
                "detail": "Error during auto-repair",
                "error": "internal_error",
                "repair_result": {},
                "echo": payload_simple_problems,
            }
            assert "private structural detail" not in str(data)

    def test_vip_shoplist_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты VIP shoplist endpoint"""
        payload_full = {
            "days": [
                _shoplist_day("chicken", quantity="1200", pack_size="500"),
                _shoplist_day("rice", quantity="2000", pack_size="1000"),
            ]
        }
        response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json=payload_full,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert len(data["days"]) == 2
        assert data["days"][0]["packed"][0]["food_id"] == "chicken"
        assert data["days"][0]["packed"][0]["packs"] == 3
        assert data["days"][1]["packed"][0]["food_id"] == "rice"
        assert data["days"][1]["packed"][0]["packs"] == 2

        payload_simple = {"days": [_shoplist_day("chicken", quantity="1200", pack_size="500")]}
        response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json=payload_simple,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert len(data["days"]) == 1
        day = data["days"][0]
        assert len(day["packed"]) == 1
        assert day["packed"][0]["packs"] == 3
        assert isinstance(day["unpacked"], list)
        assert isinstance(day["analytics"], dict)
        assert day["packed"][0]["reasons"]

        region_payload = {"days": [_shoplist_day("chicken", quantity="1200", pack_size="500")]}
        for region in ("BY", "US", "ES", "DE", "FR"):
            response = client.post(
                "/api/v1/vip/shoplist/weekly",
                json=region_payload,
                headers=vip_headers,
                params={"region_id": region.lower()},
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert len(data["days"]) == 1
            day = data["days"][0]
            assert day["packed"][0]["food_id"] == "chicken"
            assert day["packed"][0]["packs"] == 3
            assert isinstance(day["unpacked"], list)
            assert isinstance(day["analytics"], dict)
            assert day["packed"][0]["reasons"]

    def test_vip_error_handling_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты обработки ошибок VIP endpoints"""
        invalid_payloads = [
            {"invalid_field": "invalid_value", "calories": 2000},
            {"sex": "invalid_sex", "calories": 2000},
            {"age": -5, "calories": 2000},
            {"height_cm": 0, "calories": 2000},
            {"weight_kg": -10, "calories": 2000},
            {"activity": "invalid_activity", "calories": 2000},
            {"goal": "invalid_goal", "calories": 2000},
            {"calories": 2000},
            {"sex": "male", "calories": 2000},
        ]

        for payload in invalid_payloads:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert assert_json_response_payload(response) == {
                "detail": "Invalid weekly plan request payload"
            }

    def test_vip_api_key_validation_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Verify ordinary managed-client VIP tier authentication."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
        }
        invalid_key_detail = (
            "API key does not have VIP tier access. Upgrade to VIP to access this feature."
        )

        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=payload,
        )
        assert response.status_code == 403
        assert assert_json_response_payload(response) == {"detail": "VIP access required"}

        for key in ("invalid-key", "wrong-key", "test-key", "dev-key"):
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=payload,
                headers={"X-API-Key": key},
            )
            assert response.status_code == 403
            assert assert_json_response_payload(response) == {"detail": invalid_key_detail}

        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"

    def test_vip_weekly_menu_succeeds_in_test_environment(
        self,
        client: TestClient,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Verify authenticated weekly-menu success in the stable test environment."""
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"

    def test_vip_comprehensive_workflow_integration_extended_scenarios(
        self,
        canonical_auto_repair_food_db: dict[str, FoodItem],
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты полного workflow VIP функций"""
        monkeypatch.setattr(
            menu_engine,
            "get_cached_common_foods_snapshot",
            lambda: canonical_auto_repair_food_db,
        )
        menu_payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
        }
        menu_response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=menu_payload,
            headers=vip_headers,
        )
        assert menu_response.status_code == 200
        menu_data = assert_json_response_payload(menu_response)
        assert menu_data["status"] == "success"

        workflow_week_plan = {
            "days": [
                {
                    "day": "monday",
                    "meals": [
                        {
                            "meal_type": "breakfast",
                            "ingredients": [{"name": "bread", "amount": 100, "unit": "g"}],
                            "nutrients": {"iron_mg": 0.0},
                        }
                    ],
                }
            ]
        }
        recipes_payload = {"week_plan": workflow_week_plan}
        recipes_response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=recipes_payload,
            headers=vip_headers,
        )
        assert recipes_response.status_code == 200
        recipes_data = assert_json_response_payload(recipes_response)
        assert recipes_data["status"] == "success"
        assert recipes_data["weekly_recipes"]
        assert recipes_data["total_recipes"] > 0

        repair_payload = _auto_repair_payload(workflow_week_plan)
        repair_response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=repair_payload,
            headers=vip_headers,
        )
        assert repair_response.status_code == 200
        repair_data = assert_json_response_payload(repair_response)
        assert repair_data["status"] == "success"
        assert repair_data["repair_result"]["status"] == "partial"
        assert repair_data["repair_result"]["changes_made"]

        shoplist_payload = {"days": [_shoplist_day("chicken", quantity="1200", pack_size="500")]}
        shoplist_response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json=shoplist_payload,
            headers=vip_headers,
        )
        assert shoplist_response.status_code == 200
        shoplist_data = assert_json_response_payload(shoplist_response)
        assert len(shoplist_data["days"]) == 1

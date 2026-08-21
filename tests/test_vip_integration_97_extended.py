"""
Расширенные интеграционные тесты для VIP endpoints для достижения 97% покрытия
"""

from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app.routers.vip as vip_router
from tests._helpers.vip_contracts import assert_json_response_payload


def _auto_repair_payload(week_plan: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical deterministic VIP auto-repair request."""
    return {
        "week_plan": week_plan,
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

    def test_vip_auto_repair_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты VIP auto repair endpoint"""
        payload_problems = _auto_repair_payload(
            {
                "days": [
                    {
                        "day": "monday",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "ingredients": [{"name": "chicken", "amount": 100, "unit": "g"}],
                                "nutrition_gaps": ["protein", "vitamin_c", "fiber"],
                            },
                            {
                                "meal_type": "lunch",
                                "ingredients": [{"name": "rice", "amount": 150, "unit": "g"}],
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
                                "nutrition_gaps": ["protein"],
                            }
                        ],
                    }
                ]
            }
        )
        payload_no_problems = _auto_repair_payload(
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
                            }
                        ],
                    }
                ]
            }
        )

        for payload in (payload_problems, payload_simple_problems, payload_no_problems):
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data["status"] == "error"
            assert data["code"] == "auto_repair_failed"
            repair_result = data["repair_result"]
            assert isinstance(repair_result, dict)
            assert repair_result["status"] == "failed"
            assert repair_result["iterations"] == 1
            assert repair_result["changes_made"] == []
            assert data["echo"] == payload
            assert data["message"] == "Auto-repair could not complete the requested repair"

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

        stable_failure_message = "Auto-repair could not complete the requested repair"
        preferences_payload = _auto_repair_payload(payload_no_problems["week_plan"])
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

        zero_interval = _auto_repair_payload(payload_no_problems["week_plan"])
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

        malformed_interval = _auto_repair_payload(payload_no_problems["week_plan"])
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
        client: TestClient,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты полного workflow VIP функций"""
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
        assert repair_data["status"] == "error"
        assert repair_data["code"] == "auto_repair_failed"
        assert repair_data["repair_result"]["status"] == "failed"
        assert repair_data["repair_result"]["changes_made"] == []

        shoplist_payload = {"days": [_shoplist_day("chicken", quantity="1200", pack_size="500")]}
        shoplist_response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json=shoplist_payload,
            headers=vip_headers,
        )
        assert shoplist_response.status_code == 200
        shoplist_data = assert_json_response_payload(shoplist_response)
        assert len(shoplist_data["days"]) == 1

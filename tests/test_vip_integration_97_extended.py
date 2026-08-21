"""
Расширенные интеграционные тесты для VIP endpoints для достижения 97% покрытия
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests._client import open_test_client
from tests._helpers.vip_contracts import assert_json_response_payload


def _auto_repair_payload(week_plan: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical deterministic VIP auto-repair request."""
    return {
        "week_plan": week_plan,
        "targets": {
            "iron_mg": [6.0, 8.0, 45.0],
            "calcium_mg": [800.0, 1000.0, 2500.0],
            "magnesium_mg": [300.0, 400.0, 350.0],
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
            assert "weekly_recipes" in data
            assert "total_recipes" in data
            assert data["echo"] == payload

    def test_vip_auto_repair_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
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
            assert data["status"] == "success"
            repair_result = data["repair_result"]
            assert isinstance(repair_result, dict)
            assert "status" in repair_result
            assert repair_result["status"] in {"success", "partial", "failed"}
            assert "iterations" in repair_result
            assert data["echo"] == payload
            assert data["message"] == (
                f"Auto-repair completed with status: {repair_result['status']}"
            )

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
        test_environment: None,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Test request-time production auth after test-safe app startup."""
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

        with open_test_client() as client:
            with monkeypatch.context() as request_env:
                request_env.setenv("APP_ENV", "production")
                request_env.setenv("DEBUG", "false")
                request_env.setenv("ALLOW_DEV_API_KEY", "false")
                request_env.setenv("VIP_MODULE_ENABLED", "true")
                request_env.setenv("VIP_API_KEYS", vip_headers["X-API-Key"])
                request_env.delenv("ENVIRONMENT", raising=False)
                request_env.delenv("ALLOW_ANONYMOUS_API_KEYS", raising=False)

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

    def test_vip_environment_switching_integration_extended_scenarios(
        self,
        client: TestClient,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Расширенные интеграционные тесты переключения окружений"""
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

        recipes_payload = {"week_plan": menu_data["menu"]}
        recipes_response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=recipes_payload,
            headers=vip_headers,
        )
        assert recipes_response.status_code == 200
        recipes_data = assert_json_response_payload(recipes_response)
        assert recipes_data["status"] == "success"

        repair_payload = _auto_repair_payload(menu_data["menu"])
        repair_response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=repair_payload,
            headers=vip_headers,
        )
        assert repair_response.status_code == 200
        repair_data = assert_json_response_payload(repair_response)
        assert repair_data["status"] == "success"

        shoplist_payload = {"days": [_shoplist_day("chicken", quantity="1200", pack_size="500")]}
        shoplist_response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json=shoplist_payload,
            headers=vip_headers,
        )
        assert shoplist_response.status_code == 200
        shoplist_data = assert_json_response_payload(shoplist_response)
        assert len(shoplist_data["days"]) == 1

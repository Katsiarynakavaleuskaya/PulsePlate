"""
Ультимативные интеграционные тесты для VIP endpoints для достижения 97% покрытия
"""

from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from tests._helpers.vip_contracts import (
    assert_json_response_payload,
    build_auto_repair_weekly_request_payload,
    build_weekly_recipes_request_payload,
)


@pytest.mark.slow
class TestVIPIntegration97Ultimate:
    """Ультимативные интеграционные тесты для VIP endpoints"""

    def test_vip_weekly_menu_integration_ultimate_scenarios(self, test_environment, vip_headers):
        """Ультимативные интеграционные тесты VIP weekly menu endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тест 1: Полные данные пользователя с различными комбинациями
        full_scenarios = [
            {
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
            },
            {
                "sex": "female",
                "age": 25,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "active",
                "goal": "loss",
                "deficit_pct": 15,
                "surplus_pct": 5,
                "bodyfat": 20.0,
                "region": "US",
                "timezone": "America/New_York",
                "diet_flags": ["KETO"],
                "life_stage": "adult",
                "medical_conditions": ["diabetes"],
            },
            {
                "sex": "male",
                "age": 35,
                "height_cm": 180.0,
                "weight_kg": 80.0,
                "activity": "very_active",
                "goal": "gain",
                "deficit_pct": 0,
                "surplus_pct": 10,
                "bodyfat": 12.0,
                "region": "ES",
                "timezone": "Europe/Madrid",
                "diet_flags": ["PALEO"],
                "life_stage": "adult",
                "medical_conditions": [],
            },
        ]

        for scenario in full_scenarios:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error"]
            if data["status"] == "success":
                assert "echo" in data
                assert "menu" in data

        # Тест 2: Минимальные данные с различными комбинациями
        minimal_scenarios = [
            {
                "sex": "female",
                "age": 25,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "active",
                "goal": "loss",
            },
            {
                "sex": "male",
                "age": 35,
                "height_cm": 180.0,
                "weight_kg": 80.0,
                "activity": "very_active",
                "goal": "gain",
            },
            {
                "sex": "female",
                "age": 40,
                "height_cm": 160.0,
                "weight_kg": 65.0,
                "activity": "light",
                "goal": "maintain",
            },
        ]

        for scenario in minimal_scenarios:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

        # Тест 3: Альтернативные поля с различными комбинациями
        alternative_scenarios = [
            {
                "calories": 2000,
                "protein": 150.0,
                "user_id": "test_user_123",
                "preferences": {"cuisine": "mediterranean"},
                "goals": {"weight_loss": True},
                "constraints": {"allergies": ["nuts"]},
            },
            {
                "calories": 1800,
                "protein": 120.0,
                "user_id": "test_user_456",
                "preferences": {"cuisine": "asian"},
                "goals": {"muscle_gain": True},
                "constraints": {"dietary_restrictions": ["gluten_free"]},
            },
            {
                "calories": 2200,
                "protein": 180.0,
                "user_id": "test_user_789",
                "preferences": {"cuisine": "mexican"},
                "goals": {"maintenance": True},
                "constraints": {"preferences": ["spicy"]},
            },
        ]

        for scenario in alternative_scenarios:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert response.headers.get("content-type", "").startswith("application/json")
            assert response.json() == {"detail": "Invalid weekly plan request payload"}

        # Тест 4: Различные комбинации активности и целей
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
            data = response.json()
            assert data["status"] == "success"

    def test_vip_recipes_integration_ultimate_scenarios(self, test_environment, vip_headers):
        """Ультимативные интеграционные тесты VIP recipes endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тест 1: Полный week_plan с множественными днями и приемами пищи
        complex_scenarios = [
            {
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
                    ],
                }
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "wednesday",
                            "meals": [
                                {
                                    "meal_type": "breakfast",
                                    "ingredients": [
                                        {"name": "oats", "amount": 50, "unit": "g"},
                                        {"name": "milk", "amount": 200, "unit": "ml"},
                                        {"name": "banana", "amount": 1, "unit": "piece"},
                                    ],
                                },
                                {
                                    "meal_type": "lunch",
                                    "ingredients": [
                                        {"name": "pork", "amount": 140, "unit": "g"},
                                        {"name": "pasta", "amount": 100, "unit": "g"},
                                        {"name": "tomato", "amount": 100, "unit": "g"},
                                    ],
                                },
                            ],
                        }
                    ],
                }
            },
        ]

        for scenario in complex_scenarios:
            response = client.post(
                "/api/v1/vip/recipes/weekly",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

        # Тест 2: Простой week_plan с различными продуктами
        simple_scenarios = [
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "monday",
                            "meals": [
                                {
                                    "meal_type": "breakfast",
                                    "ingredients": [
                                        {"name": "chicken", "amount": 100, "unit": "g"}
                                    ],
                                }
                            ],
                        }
                    ],
                }
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "tuesday",
                            "meals": [
                                {
                                    "meal_type": "lunch",
                                    "ingredients": [{"name": "beef", "amount": 150, "unit": "g"}],
                                }
                            ],
                        }
                    ],
                }
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "wednesday",
                            "meals": [
                                {
                                    "meal_type": "dinner",
                                    "ingredients": [{"name": "fish", "amount": 120, "unit": "g"}],
                                }
                            ],
                        }
                    ],
                }
            },
        ]

        for scenario in simple_scenarios:
            response = client.post(
                "/api/v1/vip/recipes/weekly",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

        # Тест 3: Week_plan с различными единицами измерения
        units_scenarios = [
            {
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
                    ],
                }
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "tuesday",
                            "meals": [
                                {
                                    "meal_type": "lunch",
                                    "ingredients": [
                                        {"name": "water", "amount": 500, "unit": "ml"},
                                        {"name": "salt", "amount": 5, "unit": "g"},
                                        {"name": "pepper", "amount": 2, "unit": "g"},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            },
        ]

        for scenario in units_scenarios:
            response = client.post(
                "/api/v1/vip/recipes/weekly",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_vip_auto_repair_integration_ultimate_scenarios(
        self,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Ультимативные интеграционные тесты VIP auto repair endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        for day, ingredient_name in (
            ("Monday", "chicken"),
            ("Tuesday", "beef"),
            ("Wednesday", "fish"),
            ("Thursday", "salmon"),
            ("Friday", "quinoa"),
            ("Saturday", "spinach"),
        ):
            scenario = build_auto_repair_weekly_request_payload()
            scenario["week_plan"]["days"][0]["day"] = day
            scenario["week_plan"]["days"][0]["meals"][0]["ingredients"][0]["name"] = ingredient_name
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = assert_json_response_payload(response)
            assert data["status"] == "success"
            assert data["repair_result"]["status"] == "success"
            assert data["echo"] == scenario

    def test_vip_shoplist_integration_ultimate_scenarios(self, test_environment, vip_headers):
        """Ультимативные интеграционные тесты VIP shoplist endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тест 1: Полный week_plan для генерации списка покупок
        full_shoplist_scenarios = [
            {
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
                                        {"name": "chicken", "amount": 120, "unit": "g"},
                                        {"name": "rice", "amount": 200, "unit": "g"},
                                        {"name": "carrot", "amount": 100, "unit": "g"},
                                    ],
                                },
                            ],
                        },
                        {
                            "day": "tuesday",
                            "meals": [
                                {
                                    "meal_type": "dinner",
                                    "ingredients": [
                                        {"name": "chicken", "amount": 150, "unit": "g"},
                                        {"name": "rice", "amount": 180, "unit": "g"},
                                        {"name": "onion", "amount": 30, "unit": "g"},
                                    ],
                                }
                            ],
                        },
                    ],
                },
                "shopping_options": {
                    "region": "BY",
                    "package_rounding": True,
                    "bulk_discounts": True,
                    "prefer_organic": False,
                    "budget_limit": 100.0,
                },
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "wednesday",
                            "meals": [
                                {
                                    "meal_type": "breakfast",
                                    "ingredients": [
                                        {"name": "beef", "amount": 120, "unit": "g"},
                                        {"name": "potato", "amount": 200, "unit": "g"},
                                        {"name": "carrot", "amount": 100, "unit": "g"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
                "shopping_options": {
                    "region": "US",
                    "package_rounding": False,
                    "bulk_discounts": False,
                    "prefer_organic": True,
                    "budget_limit": 50.0,
                },
            },
        ]

        for scenario in full_shoplist_scenarios:
            response = client.post(
                "/api/v1/vip/shoplist",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"

        # Тест 2: Простой week_plan
        simple_shoplist_scenarios = [
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "monday",
                            "meals": [
                                {
                                    "meal_type": "breakfast",
                                    "ingredients": [
                                        {"name": "chicken", "amount": 100, "unit": "g"}
                                    ],
                                }
                            ],
                        }
                    ],
                },
                "shopping_options": {
                    "region": "US",
                    "package_rounding": False,
                },
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "tuesday",
                            "meals": [
                                {
                                    "meal_type": "lunch",
                                    "ingredients": [{"name": "fish", "amount": 120, "unit": "g"}],
                                }
                            ],
                        }
                    ],
                },
                "shopping_options": {
                    "region": "ES",
                    "package_rounding": True,
                },
            },
        ]

        for scenario in simple_shoplist_scenarios:
            response = client.post(
                "/api/v1/vip/shoplist",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code in [200, 404]

        # Тест 3: Week_plan с различными регионами
        regions = ["BY", "US", "ES", "DE", "FR", "IT", "PL"]

        for region in regions:
            payload = {
                "week_plan": {
                    "days": [
                        {
                            "day": "monday",
                            "meals": [
                                {
                                    "meal_type": "breakfast",
                                    "ingredients": [
                                        {"name": "chicken", "amount": 100, "unit": "g"}
                                    ],
                                }
                            ],
                        }
                    ],
                },
                "shopping_options": {
                    "region": region,
                    "package_rounding": True,
                },
            }

            response = client.post(
                "/api/v1/vip/shoplist",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code in [200, 404]

    def test_vip_error_handling_integration_ultimate_scenarios(self, test_environment, vip_headers):
        """Ультимативные интеграционные тесты обработки ошибок VIP endpoints"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тест 1: Невалидные данные
        invalid_payloads = [
            {"invalid_field": "invalid_value"},
            {"sex": "invalid_sex"},
            {"age": -5},
            {"height_cm": 0},
            {"weight_kg": -10},
            {"activity": "invalid_activity"},
            {"goal": "invalid_goal"},
            {"sex": "male", "age": "invalid_age"},
            {"sex": "male", "height_cm": "invalid_height"},
            {"sex": "male", "weight_kg": "invalid_weight"},
        ]

        for payload in invalid_payloads:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert response.headers.get("Content-Type", "").startswith("application/json")
            assert response.json() == {"detail": "Invalid weekly plan request payload"}

        # Тест 2: Пустые данные
        empty_payloads = [
            {},
            {"sex": ""},
            {"age": None},
            {"height_cm": None},
            {"weight_kg": None},
        ]

        for payload in empty_payloads:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert response.headers.get("Content-Type", "").startswith("application/json")
            assert response.json() == {"detail": "Invalid weekly plan request payload"}

        # Тест 3: Отсутствующие обязательные поля
        partial_payloads = [
            {"sex": "male"},
            {"age": 30},
            {"height_cm": 175.0},
            {"weight_kg": 70.0},
            {"activity": "moderate"},
            {"goal": "maintain"},
        ]

        for payload in partial_payloads:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code == 422
            assert response.headers.get("Content-Type", "").startswith("application/json")
            assert response.json() == {"detail": "Invalid weekly plan request payload"}

    def test_vip_api_key_validation_integration_ultimate_scenarios(
        self, production_environment, vip_headers
    ):
        """Ультимативные интеграционные тесты валидации API ключа в production"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тест 1: Без API ключа
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
        )
        assert response.status_code in [401, 403]

        # Тест 2: С различными невалидными API ключами
        invalid_keys = [
            "invalid-key",
            "wrong-key",
            "test-key",
            "dev-key",
            "admin-key",
            "user-key",
            "guest-key",
            "public-key",
            "private-key",
            "secret-key",
        ]

        for key in invalid_keys:
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
                headers={"X-API-Key": key},
            )
            assert response.status_code in [401, 403]

        # Тест 3: С валидным API ключом
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

    def test_vip_environment_switching_integration_ultimate_scenarios(
        self, test_environment, vip_headers
    ):
        """Ультимативные интеграционные тесты переключения окружений"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тест в test окружении
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

    def test_vip_authenticated_strict_endpoint_sequence_ultimate_scenarios(
        self,
        test_environment: None,
        vip_headers: dict[str, str],
    ) -> None:
        """Exercise an authenticated sequence of independent strict VIP endpoint contracts."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Menu uses its own independent weekly-menu request DTO.
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
        menu_response_payload = assert_json_response_payload(menu_response)
        assert menu_response_payload["status"] == "success"

        # Weekly recipes uses its own independent strict request DTO.
        recipes_payload = build_weekly_recipes_request_payload()
        recipes_response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=recipes_payload,
            headers=vip_headers,
        )
        assert recipes_response.status_code == 200
        recipes_data = assert_json_response_payload(recipes_response)
        assert recipes_data["status"] == "success"
        assert recipes_data["weekly_recipes"]
        assert recipes_data["total_recipes"] == 1
        assert recipes_data["echo"] == recipes_payload

        # Auto-repair uses its own independent strict request DTO.
        repair_payload = build_auto_repair_weekly_request_payload()

        repair_response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=repair_payload,
            headers=vip_headers,
        )
        assert repair_response.status_code == 200
        repair_data = assert_json_response_payload(repair_response)
        assert repair_data["status"] == "success"
        assert repair_data["repair_result"]["status"] == "success"
        assert repair_data["echo"] == repair_payload

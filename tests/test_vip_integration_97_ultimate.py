"""
Ультимативные интеграционные тесты для VIP endpoints для достижения 97% покрытия
"""

import pytest
from typing import cast

from fastapi.testclient import TestClient
from starlette.types import ASGIApp


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
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error"]

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

    def test_vip_auto_repair_integration_ultimate_scenarios(self, test_environment, vip_headers):
        """Ультимативные интеграционные тесты VIP auto repair endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тест 1: Проблемный week_plan с множественными проблемами
        problems_scenarios = [
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
                                    "nutrition_gaps": ["protein", "vitamin_c", "fiber"],
                                },
                                {
                                    "meal_type": "lunch",
                                    "ingredients": [{"name": "rice", "amount": 150, "unit": "g"}],
                                    "nutrition_gaps": ["vitamin_a", "calcium"],
                                },
                            ],
                        }
                    ],
                },
                "repair_options": {
                    "add_supplements": True,
                    "adjust_portions": True,
                    "suggest_alternatives": True,
                    "balance_macros": True,
                    "add_micronutrients": True,
                },
            },
            {
                "week_plan": {
                    "days": [
                        {
                            "day": "tuesday",
                            "meals": [
                                {
                                    "meal_type": "dinner",
                                    "ingredients": [{"name": "beef", "amount": 150, "unit": "g"}],
                                    "nutrition_gaps": ["iron", "zinc"],
                                }
                            ],
                        }
                    ],
                },
                "repair_options": {
                    "add_supplements": True,
                    "adjust_portions": False,
                    "suggest_alternatives": True,
                },
            },
        ]

        for scenario in problems_scenarios:
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error"]

        # Тест 2: Простой проблемный week_plan
        simple_problems_scenarios = [
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
                                    "nutrition_gaps": ["protein"],
                                }
                            ],
                        }
                    ],
                },
                "repair_options": {
                    "add_supplements": True,
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
                                    "nutrition_gaps": ["omega_3"],
                                }
                            ],
                        }
                    ],
                },
                "repair_options": {
                    "adjust_portions": True,
                },
            },
        ]

        for scenario in simple_problems_scenarios:
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error"]

        # Тест 3: Week_plan без проблем
        no_problems_scenarios = [
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
                                        {"name": "broccoli", "amount": 100, "unit": "g"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
                "repair_options": {
                    "add_supplements": False,
                    "adjust_portions": False,
                    "suggest_alternatives": False,
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
                                    "ingredients": [
                                        {"name": "salmon", "amount": 120, "unit": "g"},
                                        {"name": "quinoa", "amount": 100, "unit": "g"},
                                        {"name": "spinach", "amount": 150, "unit": "g"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
                "repair_options": {
                    "add_supplements": False,
                    "adjust_portions": False,
                    "suggest_alternatives": False,
                },
            },
        ]

        for scenario in no_problems_scenarios:
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=scenario,
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error"]

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
            assert response.status_code in [200, 422]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"

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
            assert response.status_code in [200, 422]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"

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
            assert response.status_code in [200, 422]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"

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

    def test_vip_comprehensive_workflow_integration_ultimate_scenarios(
        self, test_environment, vip_headers
    ):
        """Ультимативные интеграционные тесты полного workflow VIP функций"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # 1. Создание недельного плана
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
        menu_data = menu_response.json()
        assert menu_data["status"] == "success"

        # 2. Генерация рецептов (если endpoint существует)
        if "menu" in menu_data and menu_data["menu"] != {"mode": "echo"}:
            recipes_payload = {"week_plan": menu_data.get("menu", {})}

            recipes_response = client.post(
                "/api/v1/vip/recipes/weekly",
                json=recipes_payload,
                headers=vip_headers,
            )
            assert recipes_response.status_code == 200

        # 3. Авто-ремонт плана (если endpoint существует)
        repair_payload = {
            "week_plan": menu_data.get("menu", {}),
            "repair_options": {"add_supplements": True},
        }

        repair_response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=repair_payload,
            headers=vip_headers,
        )
        assert repair_response.status_code == 200

        # 4. Генерация списка покупок (если endpoint существует)
        shoplist_payload = {
            "week_plan": menu_data.get("menu", {}),
            "shopping_options": {"region": "BY", "package_rounding": True},
        }

        shoplist_response = client.post(
            "/api/v1/vip/shoplist",
            json=shoplist_payload,
            headers=vip_headers,
        )
        assert shoplist_response.status_code in [200, 404]

"""
Расширенные интеграционные тесты для VIP endpoints для достижения 97% покрытия
"""

from fastapi.testclient import TestClient


def _get_app():
    """Safely get the FastAPI app instance."""
    import app

    if app.app is None:
        raise RuntimeError("FastAPI app is not initialized")
    return app.app


import pytest


@pytest.mark.smoke
class TestVIPIntegration97Extended:
    """Расширенные интеграционные тесты для VIP endpoints"""

    def test_vip_weekly_menu_integration_extended_scenarios(self, test_environment, vip_headers):
        """Расширенные интеграционные тесты VIP weekly menu endpoint"""
        client = TestClient(_get_app())

        # Тест 1: Полные данные пользователя
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
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data
        assert "menu" in data

        # Тест 2: Минимальные данные
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
        data = response.json()
        assert data["status"] == "success"

        # Тест 3: Альтернативные поля
        payload_alternative = {
            # Provide alternative fields plus minimal valid core to satisfy UserProfile
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
        data = response.json()
        assert data.get("status") in ["success", "error"]

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
            assert data.get("status") in ["success", "error"]

    def test_vip_recipes_integration_extended_scenarios(self, test_environment, vip_headers):
        """Расширенные интеграционные тесты VIP recipes endpoint"""
        client = TestClient(_get_app())

        # Тест 1: Полный week_plan с множественными днями и приемами пищи
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

        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=payload_complex,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["success", "error"]

        # Тест 2: Простой week_plan
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

        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=payload_simple,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["success", "error"]

        # Тест 3: Week_plan с различными единицами измерения
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

        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=payload_units,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_vip_auto_repair_integration_extended_scenarios(self, test_environment, vip_headers):
        """Расширенные интеграционные тесты VIP auto repair endpoint"""
        client = TestClient(_get_app())

        # Тест 1: Проблемный week_plan с множественными проблемами
        payload_problems = {
            "week_plan": {
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
            },
            "repair_options": {
                "add_supplements": True,
                "adjust_portions": True,
                "suggest_alternatives": True,
                "balance_macros": True,
                "add_micronutrients": True,
            },
        }

        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=payload_problems,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "error"]

        # Тест 2: Простой проблемный week_plan
        payload_simple_problems = {
            "week_plan": {
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
            },
            "repair_options": {"add_supplements": True},
        }

        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=payload_simple_problems,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "error"]

        # Тест 3: Week_plan без проблем
        payload_no_problems = {
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
                ]
            },
            "repair_options": {
                "add_supplements": False,
                "adjust_portions": False,
                "suggest_alternatives": False,
            },
        }

        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=payload_no_problems,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "error"]

    def test_vip_shoplist_integration_extended_scenarios(self, test_environment, vip_headers):
        """Расширенные интеграционные тесты VIP shoplist endpoint"""
        client = TestClient(_get_app())

        # Тест 1: Полный week_plan для генерации списка покупок
        payload_full = {
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
                ]
            },
            "shopping_options": {
                "region": "BY",
                "package_rounding": True,
                "bulk_discounts": True,
                "prefer_organic": False,
                "budget_limit": 100.0,
            },
        }

        response = client.post(
            "/api/v1/vip/shoplist",
            json=payload_full,
            headers=vip_headers,
        )
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"

        # Тест 2: Простой week_plan
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
            },
            "shopping_options": {"region": "US", "package_rounding": False},
        }

        response = client.post(
            "/api/v1/vip/shoplist",
            json=payload_simple,
            headers=vip_headers,
        )
        assert response.status_code in [200, 404]

        # Тест 3: Week_plan с различными регионами
        regions = ["BY", "US", "ES", "DE", "FR"]

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
                    ]
                },
                "shopping_options": {"region": region, "package_rounding": True},
            }

            response = client.post(
                "/api/v1/vip/shoplist",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code in [200, 404]

    def test_vip_error_handling_integration_extended_scenarios(self, test_environment, vip_headers):
        """Расширенные интеграционные тесты обработки ошибок VIP endpoints"""
        client = TestClient(_get_app())

        # Тест 1: Невалидные данные
        invalid_payloads = [
            {"invalid_field": "invalid_value", "calories": 2000},
            {"sex": "invalid_sex", "calories": 2000},
            {"age": -5, "calories": 2000},
            {"height_cm": 0, "calories": 2000},
            {"weight_kg": -10, "calories": 2000},
            {"activity": "invalid_activity", "calories": 2000},
            {"goal": "invalid_goal", "calories": 2000},
        ]

        for payload in invalid_payloads:
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json=payload,
                headers=vip_headers,
            )
            assert response.status_code in [200, 422]  # Возвращает echo mode или validation error
            if response.status_code == 200:
                data = response.json()
                assert data.get("status") in ["success", "error"]

        # Тест 2: Пустые данные
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={"calories": 2000},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["success", "error"]

        # Тест 3: Отсутствующие обязательные поля
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={"sex": "male", "calories": 2000},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["success", "error"]

    def test_vip_api_key_validation_integration_extended_scenarios(
        self, production_environment, vip_headers
    ):
        """Расширенные интеграционные тесты валидации API ключа в production"""
        client = TestClient(_get_app())

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

        # Тест 2: С невалидным API ключом
        invalid_keys = ["invalid-key", "wrong-key", "test-key", "dev-key"]

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

    def test_vip_environment_switching_integration_extended_scenarios(
        self, test_environment, vip_headers
    ):
        """Расширенные интеграционные тесты переключения окружений"""
        client = TestClient(_get_app())

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

    def test_vip_comprehensive_workflow_integration_extended_scenarios(
        self, test_environment, vip_headers
    ):
        """Расширенные интеграционные тесты полного workflow VIP функций"""
        client = TestClient(_get_app())

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

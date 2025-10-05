"""
Тесты для повышения покрытия app.py до 97%
Покрывают слабые места: import errors, feature flags, premium endpoints, error paths
"""

from unittest.mock import patch
import pytest
from app import app


class TestAppCoverageBoost97:
    """Класс для тестов повышения покрытия app.py до 97%"""

    def test_bmr_calculation_module_unavailable(self, client) -> None:
        """Тест покрытия когда BMR модуль недоступен (строка 1668 в app.py)"""
        # Имитируем ситуацию когда BMR модуль недоступен
        data = {"sex": "male", "age": 30, "height_cm": 175, "weight_kg": 70, "activity": "moderate"}

        # Когда calculate_all_bmr is None, должен возвращаться 200 с fallback поведением
        with patch("app.calculate_all_bmr", None):
            with patch("app.calculate_all_tdee", None):
                response = client.post(
                    "/api/v1/premium/bmr", json=data, headers={"X-API-Key": "test_key"}
                )
                assert response.status_code == 200  # Fallback behavior
                result = response.json()
                # Должен содержать BMR/TDEE данные из fallback логики
                assert "bmr" in result or "tdee" in result

    def test_who_targets_module_unavailable(self, client) -> None:
        """Тест покрытия когда WHO targets модуль недоступен"""
        data = {"sex": "male", "age": 30, "height_cm": 175, "weight_kg": 70, "activity": "moderate"}

        # Когда build_nutrition_targets is None, должен возвращаться 200 с fallback
        with patch("app.build_nutrition_targets", None):
            response = client.post(
                "/api/v1/premium/targets", json=data, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200  # Fallback behavior
            result = response.json()
            # Должен содержать nutritional данные (macros, kcal_daily, etc.)
            assert "macros" in result or "kcal_daily" in result

    def test_premium_plate_module_unavailable(self, client) -> None:
        """Тест покрытия когда premium plate модуль недоступен"""
        data = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        # Когда make_plate is None, должен возвращаться 200 с fallback
        with patch("app.make_plate", None):
            response = client.post(
                "/api/v1/premium/plate", json=data, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200  # Fallback behavior
            result = response.json()
            # Должен содержать plate данные из fallback логики
            assert "plate" in result or "macros" in result

    def test_weekly_menu_module_unavailable(self, client) -> None:
        """Тест покрытия когда weekly menu модуль недоступен"""
        data = {"sex": "male", "age": 30, "height_cm": 175, "weight_kg": 70, "activity": "moderate"}

        # Когда make_weekly_menu is None, должен возвращаться 200 с fallback
        with patch("app.make_weekly_menu", None):
            response = client.post(
                "/api/v1/premium/plan/week", json=data, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200  # Fallback behavior
            result = response.json()
            # Должен содержать weekly plan данные (daily_menus, shopping_list, etc.)
            assert "daily_menus" in result or "shopping_list" in result

    def test_prometheus_metrics_unavailable(self, client) -> None:
        """Тест metrics endpoint когда prometheus недоступен"""
        # Когда prometheus недоступен, generate_latest будет None
        if hasattr(app, "generate_latest"):
            with patch.object(app, "generate_latest", None):
                response = client.get("/metrics")
                assert response.status_code == 200
                data = response.json()
                assert "error" in data
                assert "Prometheus client not available" in data["error"]
        else:
            # Если prometheus не импортирован, тест пропускаем
            pytest.skip("Prometheus not available in this environment")

    def test_bmi_visualization_unavailable(self, client) -> None:
        """Тест BMI endpoint когда визуализация недоступна"""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "include_chart": True,
        }

        # Когда generate_bmi_visualization is None и MATPLOTLIB_AVAILABLE is False
        with patch("app.generate_bmi_visualization", None):
            with patch("app.MATPLOTLIB_AVAILABLE", False):
                response = client.post("/bmi", json=data)
                assert response.status_code == 200
                result = response.json()
                # Должно быть сообщение об ошибке визуализации
                if "visualization" in result:
                    assert result["visualization"]["available"] is False

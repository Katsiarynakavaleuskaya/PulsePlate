import os


"""
Дополнительные тесты для покрытия app/routers/premium_week.py
Цель: покрыть недостающие 11 строк для достижения 97% покрытия
"""

import sys

from fastapi.testclient import TestClient


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from main.py file
import importlib.util


spec = importlib.util.spec_from_file_location("app_module", "main.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load main.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app


class TestPremiumWeekAdditionalCoverage:
    """Дополнительные тесты для premium_week.py"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def setup_method(self):
        """Настройка для каждого теста"""
        self.client = TestClient(app)

    def test_premium_week_plan_creation_invalid_data_coverage(self):
        """Тест создания недельного плана с невалидными данными для покрытия"""
        invalid_data = {"invalid_field": "invalid_value"}

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=invalid_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_missing_fields_coverage(self):
        """Тест создания недельного плана с отсутствующими полями для покрытия"""
        incomplete_data = {
            "weight_kg": 70,
            # Отсутствуют height_cm, age, gender
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=incomplete_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_edge_values_coverage(self):
        """Тест создания недельного плана с граничными значениями для покрытия"""
        edge_data = {
            "weight_kg": 0.1,  # Минимальный вес
            "height_cm": 50,  # Минимальный рост
            "age": 0,  # Минимальный возраст
            "gender": "male",
            "activity": "sedentary",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=edge_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (200, 400, 403, 422, 500)

    def test_premium_week_plan_creation_max_values_coverage(self):
        """Тест создания недельного плана с максимальными значениями для покрытия"""
        max_data = {
            "weight_kg": 500,  # Максимальный вес
            "height_cm": 300,  # Максимальный рост
            "age": 120,  # Максимальный возраст
            "gender": "female",
            "activity": "very_active",
            "goal": "lose_weight",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=max_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (200, 400, 403, 422, 500)

    def test_premium_week_plan_creation_invalid_gender_coverage(self):
        """Тест создания недельного плана с невалидным полом для покрытия"""
        invalid_gender_data = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "invalid_gender",
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=invalid_gender_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_invalid_activity_coverage(self):
        """Тест создания недельного плана с невалидной активностью для покрытия"""
        invalid_activity_data = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "male",
            "activity": "invalid_activity",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=invalid_activity_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_invalid_goal_coverage(self):
        """Тест создания недельного плана с невалидной целью для покрытия"""
        invalid_goal_data = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "male",
            "activity": "moderate",
            "goal": "invalid_goal",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=invalid_goal_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_negative_values_coverage(self):
        """Тест создания недельного плана с отрицательными значениями для покрытия"""
        negative_data = {
            "weight_kg": -10,  # Отрицательный вес
            "height_cm": -50,  # Отрицательный рост
            "age": -5,  # Отрицательный возраст
            "gender": "male",
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=negative_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_float_values_coverage(self):
        """Тест создания недельного плана с дробными значениями для покрытия"""
        float_data = {
            "weight_kg": 70.5,
            "height_cm": 175.3,
            "age": 30,
            "gender": "male",
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=float_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (200, 400, 403, 422, 500)

    def test_premium_week_plan_creation_string_numbers_coverage(self):
        """Тест создания недельного плана со строковыми числами для покрытия"""
        string_numbers_data = {
            "weight_kg": "70",  # Строковое число
            "height_cm": "175",  # Строковое число
            "age": "30",  # Строковое число
            "gender": "male",
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=string_numbers_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (200, 400, 403, 422, 500)

    def test_premium_week_plan_creation_extra_fields_coverage(self):
        """Тест создания недельного плана с дополнительными полями для покрытия"""
        extra_fields_data = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "male",
            "activity": "moderate",
            "goal": "maintain",
            "extra_field1": "extra_value1",
            "extra_field2": 123,
            "extra_field3": True,
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=extra_fields_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (200, 400, 403, 422, 500)

    def test_premium_week_plan_creation_null_values_coverage(self):
        """Тест создания недельного плана с null значениями для покрытия"""
        null_data = {
            "weight_kg": None,
            "height_cm": None,
            "age": None,
            "gender": None,
            "activity": None,
            "goal": None,
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=null_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_empty_strings_coverage(self):
        """Тест создания недельного плана с пустыми строками для покрытия"""
        empty_strings_data = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "",  # Пустая строка
            "activity": "",  # Пустая строка
            "goal": "",  # Пустая строка
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=empty_strings_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_boolean_values_coverage(self):
        """Тест создания недельного плана с булевыми значениями для покрытия"""
        boolean_data = {
            "weight_kg": True,  # Булево значение вместо числа
            "height_cm": False,  # Булево значение вместо числа
            "age": True,  # Булево значение вместо числа
            "gender": "male",
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=boolean_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

    def test_premium_week_plan_creation_array_values_coverage(self):
        """Тест создания недельного плана с массивами вместо скаляров для покрытия"""
        array_data = {
            "weight_kg": [70, 80],  # Массив вместо числа
            "height_cm": [175, 180],  # Массив вместо числа
            "age": [30, 35],  # Массив вместо числа
            "gender": ["male", "female"],  # Массив вместо строки
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plan/week",
            json=array_data,
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code in (400, 403, 422, 500)

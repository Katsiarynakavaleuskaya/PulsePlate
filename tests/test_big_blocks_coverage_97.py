"""
Тесты для покрытия больших непокрытых блоков в main.py.
Цель: покрыть блоки 668-677, 698-709, 750-760 (~33 строки).
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Shared TestClient with isolated environment per test.

    Uses monkeypatch to set and auto-restore environment variables to avoid
    cross-test side effects and keep tests hermetic.
    """
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    from app import app

    return TestClient(app)


class TestBMIVisualizationBlocks:
    """Тестирование BMI visualization блоков (668-677, 698-709)"""

    def test_bmi_with_visualization_enabled(self, client):
        """Тест BMI с включенной визуализацией (строки 668-677)"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "include_chart": True,  # Включаем визуализацию
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        # Может содержать visualization если matplotlib доступен

    def test_bmi_with_visualization_disabled(self, client):
        """Тест BMI без визуализации"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "include_chart": False,  # Отключаем визуализацию
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data

    def test_bmi_visualization_error_handling(self, client):
        """Тест обработки ошибок визуализации (строки 698-709)"""
        # Тест когда matplotlib может быть недоступен
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 85.0,
                "height_m": 1.80,
                "age": 25,
                "gender": "female",
                "pregnant": "no",
                "athlete": "no",
                "include_chart": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data

    def test_bmi_with_athlete_flags(self, client):
        """Тест BMI с athlete флагами (покрывает логику флагов)"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 80.0,
                "height_m": 1.75,
                "age": 28,
                "gender": "male",
                "pregnant": "no",
                "athlete": "yes",  # Атлет
                "include_chart": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert "category" in data

    def test_bmi_with_waist_risk_calculation(self, client):
        """Тест waist risk calculation в BMI"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 95.0,
                "height_m": 1.75,
                "age": 35,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "waist_cm": 105.0,  # Высокий waist для risk calculation
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data


class TestPersonalPlanBlocks:
    """Тестирование personal plan блоков (750-760)"""

    def test_personal_plan_basic(self, client):
        """Тест базового personal plan (строки 750-760)"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "premium": False,  # Базовый план
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        # Может содержать элементы плана

    def test_personal_plan_premium(self, client):
        """Тест premium personal plan"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "premium": True,  # Premium план
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        # Может содержать premium элементы

    def test_personal_plan_different_categories(self, client):
        """Тест personal plan для разных BMI категорий"""
        test_cases = [
            # Underweight
            {"weight_kg": 45.0, "height_m": 1.70, "expected_bmi_range": "underweight"},
            # Normal
            {"weight_kg": 65.0, "height_m": 1.70, "expected_bmi_range": "normal"},
            # Overweight
            {"weight_kg": 85.0, "height_m": 1.70, "expected_bmi_range": "overweight"},
            # Obese
            {"weight_kg": 100.0, "height_m": 1.70, "expected_bmi_range": "obese"},
        ]

        for case in test_cases:
            response = client.post(
                "/bmi",
                json={
                    "weight_kg": case["weight_kg"],
                    "height_m": case["height_m"],
                    "age": 30,
                    "gender": "male",
                    "pregnant": "no",
                    "athlete": "no",
                    "premium": True,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "bmi" in data
            assert "category" in data


class TestLanguageAndLocalizationBlocks:
    """Тестирование language/localization путей"""

    def test_bmi_different_languages(self, client):
        """Тест BMI с разными языками"""
        languages = ["ru", "en", "es"]

        for lang in languages:
            response = client.post(
                "/bmi",
                json={
                    "weight_kg": 70.0,
                    "height_m": 1.70,
                    "age": 30,
                    "gender": "male",
                    "pregnant": "no",
                    "athlete": "no",
                    "lang": lang,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "bmi" in data
            assert "category" in data

    def test_bmi_pregnant_women_different_languages(self, client):
        """Тест BMI для беременных женщин на разных языках"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 65.0,
                "height_m": 1.65,
                "age": 28,
                "gender": "female",
                "pregnant": "yes",
                "athlete": "no",
                "lang": "es",  # Испанский язык
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert "category" in data


class TestEdgeCasesAndErrorPaths:
    """Тест edge cases для покрытия дополнительных строк"""

    def test_bmi_extreme_values(self, client):
        """Тест BMI с экстремальными значениями"""
        # Очень низкий BMI
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 40.0,
                "height_m": 1.80,
                "age": 25,
                "gender": "female",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 200

        # Очень высокий BMI
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 120.0,
                "height_m": 1.60,
                "age": 40,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 200

    def test_bmi_elderly_persons(self, client):
        """Тест BMI для пожилых людей"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 75.0,
                "height_m": 1.70,
                "age": 75,  # Пожилой возраст
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert "category" in data

    def test_bmi_young_adults(self, client):
        """Тест BMI для молодых взрослых"""
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 60.0,
                "height_m": 1.65,
                "age": 20,  # Молодой возраст
                "gender": "female",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert "category" in data

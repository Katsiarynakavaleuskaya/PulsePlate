"""
Working tests for app module endpoints – final push to 97%.

RU: Рабочие тесты для покрытия модуля app, не main.py (докстринг
скорректирован для一致ности с импортами).
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import app
from app.middleware.api_tiers import TEST_KEY_VIP
from tests._client import open_test_client


@pytest.fixture
def working_endpoints_client() -> Iterator[TestClient]:
    """Open one managed working_endpoints_client for the exact imported application."""
    with open_test_client(app) as managed_client:
        yield managed_client


@pytest.fixture
def premium_working_endpoints_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Open a managed client with one fixture-scoped premium API key."""
    monkeypatch.setenv("API_KEY", "test_key_123")
    with open_test_client(app) as managed_client:
        yield managed_client


@pytest.fixture
def insight_disabled_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Open a managed client with the insight feature deterministically disabled."""
    monkeypatch.setenv("FEATURE_INSIGHT", "false")
    with open_test_client(app) as managed_client:
        yield managed_client


class TestWorkingEndpointCoverage:
    """Рабочие тесты для эндпоинтов с правильными данными"""

    def test_bmi_endpoints_working(self, working_endpoints_client):
        """Тест BMI endpoints с правильными данными"""
        # Legacy BMI endpoint (использует height_m)
        response = working_endpoints_client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 200

        # V1 BMI endpoint без API key (использует height_cm)
        response = working_endpoints_client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70.0, "height_cm": 170.0, "group": "general"},
        )
        assert response.status_code == 200

    def test_bodyfat_endpoint_working(self, working_endpoints_client):
        """Тест bodyfat endpoint с правильными данными"""
        response = working_endpoints_client.post(
            "/api/v1/bodyfat",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "waist_cm": 85.0,
                "neck_cm": 40.0,
            },
        )
        assert response.status_code == 200

    def test_premium_endpoints_with_api_key(self, premium_working_endpoints_client):
        """Тест premium endpoints с API ключом"""
        # BMR endpoint
        response = premium_working_endpoints_client.post(
            "/api/v1/premium/bmr",
            headers={"X-API-Key": "test_key_123"},
            json={
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "sex": "male",
                "activity": "moderate",
            },
        )
        assert response.status_code == 200

        # Enhanced plate endpoint
        response = premium_working_endpoints_client.post(
            "/api/v1/premium/plate",
            headers={"X-API-Key": "test_key_123"},
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code == 200

    def test_weekly_plan_endpoint(self, working_endpoints_client):
        """Тест weekly plan endpoint"""
        response = working_endpoints_client.post(
            "/api/v1/premium/plan/week",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            },
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API Key"}

    def test_misc_endpoints(self, working_endpoints_client):
        """Тест различных вспомогательных endpoints"""
        # Health checks
        response = working_endpoints_client.get("/health")
        assert response.status_code == 200

        response = working_endpoints_client.get("/api/v1/health")
        assert response.status_code == 200

        # Privacy
        response = working_endpoints_client.get("/privacy")
        assert response.status_code == 200

        # Metrics
        response = working_endpoints_client.get("/metrics")
        assert response.status_code == 200

        # Root page
        response = working_endpoints_client.get("/")
        assert response.status_code == 200


class TestEdgeCasesAndErrorPaths:
    """Тест edge cases и error paths"""

    def test_validation_error_paths(self, working_endpoints_client):
        """Тест различных validation errors"""
        # BMI с отрицательным весом (legacy endpoint использует height_m)
        response = working_endpoints_client.post(
            "/bmi",
            json={
                "weight_kg": -10.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 422

        # BMI с нулевым ростом (legacy endpoint)
        response = working_endpoints_client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 0.0,
                "age": 30,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 422

        # Bodyfat с невалидным полом
        response = working_endpoints_client.post(
            "/api/v1/bodyfat",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 30,
                "gender": "invalid",
                "waist_cm": 85.0,
                "neck_cm": 40.0,
            },
        )
        assert response.status_code == 422

    def test_auth_error_paths(self, working_endpoints_client):
        """Тест authentication error paths"""
        # Premium endpoint без ключа
        response = working_endpoints_client.post(
            "/api/v1/premium/bmr",
            json={
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "sex": "male",
                "activity": "moderate",
            },
        )
        assert response.status_code == 403

        # Premium endpoint с неправильным ключом
        response = working_endpoints_client.post(
            "/api/v1/premium/bmr",
            headers={"X-API-Key": "wrong_key"},
            json={
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "sex": "male",
                "activity": "moderate",
            },
        )
        assert response.status_code == 403

    def test_malformed_json_paths(self, working_endpoints_client):
        """Тест malformed JSON handling"""
        response = working_endpoints_client.post(
            "/bmi",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # Пустой JSON
        response = working_endpoints_client.post("/bmi", json={})
        assert response.status_code == 422

    def test_insight_endpoints_disabled(self, insight_disabled_client):
        """Тест insight endpoints когда отключены"""
        headers = {"X-API-Key": TEST_KEY_VIP}
        for path in ("/insight", "/api/v1/insight"):
            response = insight_disabled_client.post(
                path,
                json={"text": "I feel tired"},
                headers=headers,
            )
            assert response.status_code == 503
            assert response.json() == {"detail": "FEATURE_INSIGHT is disabled"}


class TestSpecialGroups:
    """Тестирование special groups для BMI"""

    def test_pregnant_group(self, working_endpoints_client):
        """Тест pregnant group"""
        response = working_endpoints_client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.70,
                "age": 25,
                "gender": "female",
                "pregnant": "yes",
                "athlete": "no",
            },
        )
        assert response.status_code == 200

    def test_athlete_group(self, working_endpoints_client):
        """Тест athlete group"""
        response = working_endpoints_client.post(
            "/bmi",
            json={
                "weight_kg": 80.0,
                "height_m": 1.80,
                "age": 25,
                "gender": "male",
                "pregnant": "no",
                "athlete": "yes",
            },
        )
        assert response.status_code == 200

    def test_elderly_group(self, working_endpoints_client):
        """Тест elderly group"""
        response = working_endpoints_client.post(
            "/bmi",
            json={
                "weight_kg": 75.0,
                "height_m": 1.75,
                "age": 70,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
            },
        )
        assert response.status_code == 200


class TestComprehensiveParameterCombinations:
    """Тест различных комбинаций параметров"""

    def test_bmi_with_waist_risk(self, working_endpoints_client):
        """Тест BMI с waist risk calculation"""
        response = working_endpoints_client.post(
            "/bmi",
            json={
                "weight_kg": 90.0,
                "height_m": 1.75,
                "age": 35,
                "gender": "male",
                "pregnant": "no",
                "athlete": "no",
                "waist_cm": 110.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Может содержать waist_risk в зависимости от логики
        assert "bmi" in data

    def test_bodyfat_all_formulas(self, working_endpoints_client):
        """Тест bodyfat со всеми доступными формулами"""
        # Navy formula (мужчины)
        response = working_endpoints_client.post(
            "/api/v1/bodyfat",
            json={
                "weight_kg": 80.0,
                "height_m": 1.80,
                "age": 35,
                "gender": "male",
                "waist_cm": 90.0,
                "neck_cm": 42.0,
            },
        )
        assert response.status_code == 200

        # Navy formula (женщины)
        response = working_endpoints_client.post(
            "/api/v1/bodyfat",
            json={
                "weight_kg": 65.0,
                "height_m": 1.65,
                "age": 30,
                "gender": "female",
                "waist_cm": 75.0,
                "neck_cm": 35.0,
                "hip_cm": 95.0,
            },
        )
        assert response.status_code == 200

    def test_bmr_all_scenarios(self, premium_working_endpoints_client):
        """Тест BMR endpoint со всеми сценариями"""
        # Мужчина с bodyfat
        response = premium_working_endpoints_client.post(
            "/api/v1/premium/bmr",
            headers={"X-API-Key": "test_key_123"},
            json={
                "weight_kg": 80.0,
                "height_cm": 180.0,
                "age": 35,
                "sex": "male",
                "activity": "very_active",
                "bodyfat": 15.0,
            },
        )
        assert response.status_code == 200

        # Женщина без bodyfat
        response = premium_working_endpoints_client.post(
            "/api/v1/premium/bmr",
            headers={"X-API-Key": "test_key_123"},
            json={
                "weight_kg": 60.0,
                "height_cm": 165.0,
                "age": 25,
                "sex": "female",
                "activity": "sedentary",
            },
        )
        assert response.status_code == 200

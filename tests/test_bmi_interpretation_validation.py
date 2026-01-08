"""
Tests for BMI interpretation validation.

RU: Тесты валидации запросов BMI (gender+pregnant).
EN: Tests for BMI request validation (gender+pregnant).
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import app
from app.schemas.bmi import BMICalculateRequest


@pytest.fixture()
def client() -> TestClient:
    """TestClient fixture for BMI API tests."""
    return TestClient(app)


class TestGenderPregnantValidation:
    """Tests for gender+pregnant validation (hard invariant)."""

    def test_male_pregnant_applies_soft_normalization(self) -> None:
        """
        RU: Мужчина с pregnant=True применяет мягкую нормализацию (pregnant=False, не 422).
        EN: Male with pregnant=True applies soft normalization (pregnant=False, no 422).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            pregnant=True,
            waist_cm=None,
        )
        assert req.gender == "male"
        assert req.pregnant is False  # Soft normalization: coerced to False

    def test_male_pregnant_string_yes_applies_soft_normalization(self) -> None:
        """
        RU: Мужчина с pregnant="yes" применяет мягкую нормализацию (pregnant=False, не 422).
        EN: Male with pregnant="yes" applies soft normalization (pregnant=False, no 422).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            pregnant="yes",
            waist_cm=None,
        )
        assert req.gender == "male"
        assert req.pregnant is False  # Soft normalization: coerced to False

    def test_male_pregnant_string_da_applies_soft_normalization(self) -> None:
        """
        RU: Мужчина с pregnant="да" применяет мягкую нормализацию (pregnant=False, не 422).
        EN: Male with pregnant="да" applies soft normalization (pregnant=False, no 422).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            pregnant="да",
            waist_cm=None,
        )
        assert req.gender == "male"
        assert req.pregnant is False  # Soft normalization: coerced to False

    def test_female_pregnant_validation_ok(self) -> None:
        """
        RU: Женщина с pregnant=True должна проходить валидацию.
        EN: Female with pregnant=True must pass validation.
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="female",
            pregnant=True,
            waist_cm=None,
        )
        assert req.gender == "female"
        assert req.pregnant is True

    def test_female_pregnant_string_yes_validation_ok(self) -> None:
        """
        RU: Женщина с pregnant="yes" должна проходить валидацию (нормализуется в bool).
        EN: Female with pregnant="yes" must pass validation (normalized to bool).
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="female",
            pregnant="yes",
            waist_cm=None,
        )
        assert req.gender == "female"
        assert req.pregnant is True  # Normalized to bool

    def test_male_pregnant_false_validation_ok(self) -> None:
        """
        RU: Мужчина с pregnant=False должен проходить валидацию.
        EN: Male with pregnant=False must pass validation.
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            pregnant=False,
            waist_cm=None,
        )
        assert req.gender == "male"
        assert req.pregnant is False

    def test_male_pregnant_string_no_validation_ok(self) -> None:
        """
        RU: Мужчина с pregnant="no" должен проходить валидацию (нормализуется в bool).
        EN: Male with pregnant="no" must pass validation (normalized to bool).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            pregnant="no",
            waist_cm=None,
        )
        assert req.gender == "male"
        assert req.pregnant is False  # Normalized to bool

    def test_male_pregnant_api_applies_soft_normalization(self, client: TestClient) -> None:
        """
        RU: API применяет мягкую нормализацию для male+pregnant (не 422, pipeline robustness).
        EN: API applies soft normalization for male+pregnant (no 422, pipeline robustness).
        """
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK  # Soft normalization: no 422
        data = resp.json()
        # Request succeeds with pregnant coerced to False
        assert data["group"] != "pregnant"  # Should not be pregnant group

    def test_female_pregnant_api_returns_200(self, client: TestClient) -> None:
        """
        RU: API должен возвращать 200 для female+pregnant.
        EN: API must return 200 for female+pregnant.
        """
        payload = {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "age": 28,
            "gender": "female",
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK

    def test_gender_normalization_ru_female_validation_ok(self) -> None:
        """
        RU: Нормализация gender "жен" должна работать.
        EN: Gender normalization "жен" must work.
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="жен",
            pregnant=True,
            waist_cm=None,
        )
        # Validation should pass (not raise)
        assert req.gender == "жен"

    def test_gender_normalization_es_female_validation_ok(self) -> None:
        """
        RU: Нормализация gender "mujer" должна работать.
        EN: Gender normalization "mujer" must work.
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="mujer",
            pregnant=True,
            waist_cm=None,
        )
        # Validation should pass (not raise)
        assert req.gender == "mujer"

    def test_gender_normalization_ru_male_pregnant_applies_soft_normalization(self) -> None:
        """
        RU: Нормализация gender "муж" + pregnant применяет мягкую нормализацию (pregnant=False, не 422).
        EN: Gender normalization "муж" + pregnant applies soft normalization (pregnant=False, no 422).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="муж",
            pregnant=True,
            waist_cm=None,
        )
        assert req.gender == "male"  # Normalized to "male"
        assert req.pregnant is False  # Soft normalization: coerced to False

    def test_gender_normalization_es_male_pregnant_applies_soft_normalization(self) -> None:
        """
        RU: Нормализация gender "hombre" + pregnant применяет мягкую нормализацию (pregnant=False, не 422).
        EN: Gender normalization "hombre" + pregnant applies soft normalization (pregnant=False, no 422).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="hombre",
            pregnant=True,
            waist_cm=None,
        )
        assert req.gender == "male"  # Normalized to "male"
        assert req.pregnant is False  # Soft normalization: coerced to False

    def test_gender_prefix_ru_male_applies_soft_normalization(self) -> None:
        """
        RU: Префикс "муж" (например, "мужик") применяет мягкую нормализацию (pregnant=False, не 422).
        EN: Prefix "муж" (e.g., "мужик") applies soft normalization (pregnant=False, no 422).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="мужик",
            pregnant=True,
            waist_cm=None,
        )
        assert req.gender == "male"  # Normalized to "male"
        assert req.pregnant is False  # Soft normalization: coerced to False

    def test_gender_prefix_es_male_applies_soft_normalization(self) -> None:
        """
        RU: Префикс "hombre" (например, "hombre_fullform") применяет мягкую нормализацию (pregnant=False, не 422).
        EN: Prefix "hombre" (e.g., "hombre_fullform") applies soft normalization (pregnant=False, no 422).
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="hombre_fullform",
            pregnant=True,
            waist_cm=None,
        )
        assert req.gender == "male"  # Normalized to "male"
        assert req.pregnant is False  # Soft normalization: coerced to False

    def test_gender_prefix_ru_male_api_applies_soft_normalization(self, client: TestClient) -> None:
        """
        RU: API применяет мягкую нормализацию для "мужик"+pregnant (не 422, pipeline robustness).
        EN: API applies soft normalization for "мужик"+pregnant (no 422, pipeline robustness).
        """
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "мужик",
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK  # Soft normalization: no 422
        data = resp.json()
        assert data["group"] != "pregnant"  # Should not be pregnant group

    def test_gender_prefix_es_male_api_applies_soft_normalization(self, client: TestClient) -> None:
        """
        RU: API применяет мягкую нормализацию для "hombre_fullform"+pregnant (не 422, pipeline robustness).
        EN: API applies soft normalization for "hombre_fullform"+pregnant (no 422, pipeline robustness).
        """
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "hombre_fullform",
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK  # Soft normalization: no 422
        data = resp.json()
        assert data["group"] != "pregnant"  # Should not be pregnant group


class TestSchemaEngineContractParity:
    """
    RU: Guard-тесты на контракт schema ↔ engine (предотвращение расхождений).
    EN: Guard tests for schema ↔ engine contract (prevent divergence).

    Critical: schema and engine must agree on gender token interpretation.
    """

    @pytest.mark.parametrize("male_token", ["male", "m", "man", "м"])
    def test_all_male_exact_tokens_apply_soft_normalization(
        self, client: TestClient, male_token: str
    ) -> None:
        """
        RU: Контракт schema ↔ engine: все male exact токены + pregnant применяют мягкую нормализацию (не 422).
        EN: Schema ↔ engine contract: all male exact tokens + pregnant apply soft normalization (no 422).
        """
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": male_token,
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert (
            resp.status_code == status.HTTP_200_OK
        ), f"Male token '{male_token}' + pregnant must return 200 (soft normalization), got {resp.status_code}"
        data = resp.json()
        assert data["group"] != "pregnant", f"Male token '{male_token}' + pregnant should not result in pregnant group"

    def test_schema_engine_exact_tokens_parity(self) -> None:
        """
        RU: Guard-тест: exact токены в schema и engine должны совпадать (двусторонняя проверка).
        EN: Guard test: exact tokens in schema and engine must match (bidirectional check).

        Uses contract spec as source of truth to verify both schema and engine.
        """
        from app.schemas.bmi import _MALE_EXACT, _FEMALE_EXACT
        from core.bmi.engine import _normalize_gender

        # Contract spec: canonical exact token sets (source of truth)
        CONTRACT_MALE_EXACT: set[str] = {"male", "m", "man", "м"}
        CONTRACT_FEMALE_EXACT: set[str] = {"female", "f", "woman", "w", "ж"}

        # Verify schema matches contract spec
        assert _MALE_EXACT == CONTRACT_MALE_EXACT, (
            f"Schema _MALE_EXACT must match contract spec. "
            f"Expected: {CONTRACT_MALE_EXACT}, Got: {_MALE_EXACT}"
        )
        assert _FEMALE_EXACT == CONTRACT_FEMALE_EXACT, (
            f"Schema _FEMALE_EXACT must match contract spec. "
            f"Expected: {CONTRACT_FEMALE_EXACT}, Got: {_FEMALE_EXACT}"
        )

        # Verify engine recognizes all contract male tokens as male
        for token in CONTRACT_MALE_EXACT:
            result = _normalize_gender(token)
            assert result == "male", (
                f"Contract token '{token}' must be recognized as male by engine. "
                f"Got: '{result}'"
            )

        # Verify engine recognizes all contract female tokens as female
        for token in CONTRACT_FEMALE_EXACT:
            result = _normalize_gender(token)
            assert result == "female", (
                f"Contract token '{token}' must be recognized as female by engine. "
                f"Got: '{result}'"
            )

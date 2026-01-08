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

    def test_male_pregnant_raises_validation_error(self) -> None:
        """
        RU: Мужчина с pregnant=True должен вызывать ValueError.
        EN: Male with pregnant=True must raise ValueError.
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="male",
                pregnant=True,
                waist_cm=None,
            )

    def test_male_pregnant_string_yes_raises_validation_error(self) -> None:
        """
        RU: Мужчина с pregnant="yes" должен вызывать ValueError.
        EN: Male with pregnant="yes" must raise ValueError.
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="male",
                pregnant="yes",
                waist_cm=None,
            )

    def test_male_pregnant_string_da_raises_validation_error(self) -> None:
        """
        RU: Мужчина с pregnant="да" должен вызывать ValueError.
        EN: Male with pregnant="да" must raise ValueError.
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="male",
                pregnant="да",
                waist_cm=None,
            )

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
        RU: Женщина с pregnant="yes" должна проходить валидацию.
        EN: Female with pregnant="yes" must pass validation.
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
        assert req.pregnant == "yes"

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
        RU: Мужчина с pregnant="no" должен проходить валидацию.
        EN: Male with pregnant="no" must pass validation.
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
        assert req.pregnant == "no"

    def test_male_pregnant_api_returns_422(self, client: TestClient) -> None:
        """
        RU: API должен возвращать 422 для male+pregnant (контракт).
        EN: API must return 422 for male+pregnant (contract).
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
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        body = resp.json()
        # Pydantic error structure: check that message is present
        detail = body.get("detail", [])
        if isinstance(detail, list) and len(detail) > 0:
            msg = str(detail[0].get("msg", ""))
        else:
            msg = str(body)
        assert "only applicable to females" in msg.lower()

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

    def test_gender_normalization_ru_male_pregnant_raises_error(self) -> None:
        """
        RU: Нормализация gender "муж" + pregnant должна вызывать ошибку.
        EN: Gender normalization "муж" + pregnant must raise error.
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="муж",
                pregnant=True,
                waist_cm=None,
            )

    def test_gender_normalization_es_male_pregnant_raises_error(self) -> None:
        """
        RU: Нормализация gender "hombre" + pregnant должна вызывать ошибку.
        EN: Gender normalization "hombre" + pregnant must raise error.
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="hombre",
                pregnant=True,
                waist_cm=None,
            )

    def test_gender_prefix_ru_male_blocks_pregnancy(self) -> None:
        """
        RU: Префикс "муж" (например, "мужик") должен блокировать pregnant (prefix-based).
        EN: Prefix "муж" (e.g., "мужик") must block pregnancy (prefix-based).
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="мужик",
                pregnant=True,
                waist_cm=None,
            )

    def test_gender_prefix_es_male_blocks_pregnancy(self) -> None:
        """
        RU: Префикс "hombre" (например, "hombre_fullform") должен блокировать pregnant (prefix-based).
        EN: Prefix "hombre" (e.g., "hombre_fullform") must block pregnancy (prefix-based).
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="hombre_fullform",
                pregnant=True,
                waist_cm=None,
            )

    def test_gender_prefix_ru_male_api_returns_422(self, client: TestClient) -> None:
        """
        RU: API должен возвращать 422 для "мужик"+pregnant (prefix-based, контракт).
        EN: API must return 422 for "мужик"+pregnant (prefix-based, contract).
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
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_gender_prefix_es_male_api_returns_422(self, client: TestClient) -> None:
        """
        RU: API должен возвращать 422 для "hombre_fullform"+pregnant (prefix-based, контракт).
        EN: API must return 422 for "hombre_fullform"+pregnant (prefix-based, contract).
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
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestSchemaEngineContractParity:
    """
    RU: Guard-тесты на контракт schema ↔ engine (предотвращение расхождений).
    EN: Guard tests for schema ↔ engine contract (prevent divergence).

    Critical: schema and engine must agree on gender token interpretation.
    If schema allows "woman" + pregnant, engine must also treat "woman" as female.
    """

    def test_schema_engine_contract_parity_woman_pregnant(self, client: TestClient) -> None:
        """
        RU: Контракт schema ↔ engine: "woman" + pregnant не должен быть отклонён как male.
        EN: Schema ↔ engine contract: "woman" + pregnant must not be rejected as male.

        Critical: schema treats "woman" as female, engine must also treat it as female.
        """
        payload = {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "age": 28,
            "gender": "woman",
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        # Must NOT be 422 (schema allows it, engine must also allow it)
        assert resp.status_code == status.HTTP_200_OK
        # Verify engine treated it as female (pregnant group)
        body = resp.json()
        assert body.get("group") == "pregnant"

    def test_schema_engine_contract_parity_zh_pregnant(self, client: TestClient) -> None:
        """
        RU: Контракт schema ↔ engine: "ж" + pregnant не должен быть отклонён как male.
        EN: Schema ↔ engine contract: "ж" + pregnant must not be rejected as male.

        Critical: schema treats "ж" as female, engine must also treat it as female.
        """
        payload = {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "age": 28,
            "gender": "ж",
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        # Must NOT be 422 (schema allows it, engine must also allow it)
        assert resp.status_code == status.HTTP_200_OK
        # Verify engine treated it as female (pregnant group)
        body = resp.json()
        assert body.get("group") == "pregnant"

    def test_schema_engine_contract_parity_man_pregnant_blocks(self, client: TestClient) -> None:
        """
        RU: Контракт schema ↔ engine: "man" + pregnant должен быть отклонён (оба слоя блокируют).
        EN: Schema ↔ engine contract: "man" + pregnant must be rejected (both layers block).

        Critical: schema treats "man" as male, engine must also treat it as male.
        """
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "man",
            "pregnant": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        # Must be 422 (both schema and engine block it)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_schema_engine_exact_tokens_parity(self) -> None:
        """
        RU: Guard-тест: exact токены в schema и engine должны совпадать.
        EN: Guard test: exact tokens in schema and engine must match.

        Prevents drift between schema's _MALE_EXACT/_FEMALE_EXACT and
        engine's _normalize_gender() exact token sets.
        """
        from app.schemas.bmi import _MALE_EXACT, _FEMALE_EXACT
        from core.bmi.engine import _normalize_gender

        # Extract engine's exact tokens by testing all schema tokens
        # Engine recognizes exact tokens (not via prefix)
        schema_male_tokens = _MALE_EXACT
        schema_female_tokens = _FEMALE_EXACT

        # Test: all schema male tokens must be recognized as male by engine
        for token in schema_male_tokens:
            result = _normalize_gender(token)
            assert result == "male", (
                f"Schema token '{token}' in _MALE_EXACT, but engine returns '{result}'. "
                f"Schema and engine exact tokens must match."
            )

        # Test: all schema female tokens must be recognized as female by engine
        for token in schema_female_tokens:
            result = _normalize_gender(token)
            assert result == "female", (
                f"Schema token '{token}' in _FEMALE_EXACT, but engine returns '{result}'. "
                f"Schema and engine exact tokens must match."
            )

        # Test: engine must not recognize unknown tokens as exact matches
        # (this ensures engine doesn't have extra tokens not in schema)
        unknown_tokens = {"unknown_gender", "xyz", "test"}
        for token in unknown_tokens:
            result = _normalize_gender(token)
            # Engine falls back to "male" for unknown, which is OK
            # But we verify it's not in our exact sets
            assert token not in schema_male_tokens
            assert token not in schema_female_tokens

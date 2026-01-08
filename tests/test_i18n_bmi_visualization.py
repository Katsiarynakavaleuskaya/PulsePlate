"""
Tests for BMI visualization i18n keys and normalize_lang policy.

RU: Тесты для ключей i18n visualization и политики normalize_lang.
EN: Tests for BMI visualization i18n keys and normalize_lang policy.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import app
from core.i18n import Language, TRANSLATIONS, normalize_lang, t

# Constants to avoid duplication
SUPPORTED_LANGS = ("ru", "en", "es")
BMI_VIZ_KEYS = ("bmi.underweight", "bmi.normal", "bmi.overweight", "bmi.obesity")
EXPECTED_VIZ_KEYS = set(BMI_VIZ_KEYS)


@pytest.fixture()
def client() -> TestClient:
    """TestClient fixture for BMI API tests."""
    return TestClient(app)


def _post_bmi(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    """
    RU: POST helper для BMI calculate endpoint.
    EN: POST helper for BMI calculate endpoint.
    """
    resp = client.post("/api/v1/bmi/calculate", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    result: dict[str, Any] = resp.json()  # type: ignore[assignment]
    return result


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    """
    RU: Валидный payload для BMICalculateRequest (гарантирует adult group с visualization).
    EN: Valid payload for BMICalculateRequest (guarantees adult group with visualization).

    Defaults ensure adult group (age=25, not pregnant, not athlete).
    """
    base: dict[str, Any] = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 25,  # Adult (not teen, not elderly)
        "gender": "male",
        "pregnant": "no",  # Not pregnant
        "athlete": "no",  # Not athlete (baseline adult)
        "lang": "en",
    }
    base.update(overrides)
    return base


class TestBMIVisualizationKeys:
    """
    RU: Тесты на наличие ключей visualization во всех языках.
    EN: Tests for visualization keys existence in all languages.
    """

    def test_bmi_visualization_keys_exist_in_all_langs(self) -> None:
        """
        RU: Все ключи visualization присутствуют во всех языках.
        EN: All visualization keys exist in all languages.
        """
        for lang_str in SUPPORTED_LANGS:
            lang: Language = lang_str  # type: ignore[assignment]
            for key in BMI_VIZ_KEYS:
                assert key in TRANSLATIONS[lang], f"Missing {key} in {lang}"
                assert TRANSLATIONS[lang][key], f"Empty {key} in {lang}"

    def test_bmi_visualization_keys_map_to_translations_via_api_adult(
        self, client: TestClient
    ) -> None:
        """
        RU: Ключи из visualization ranges (adult group, через API) мапятся на переводы без KeyError.
        EN: Visualization range keys (adult group, via API) map to translations without KeyError.

        Contract-first approach: uses actual API endpoint to get ranges,
        then verifies i18n keys are translatable. Tests adult baseline group.
        """
        # Adult group (baseline, has visualization)
        payload = _valid_payload(age=25, athlete="no")
        data = _post_bmi(client, payload)
        visualization = data.get("visualization")

        # Contract: adult group must have visualization
        assert visualization is not None, "Adult group must have visualization"
        ranges = visualization.get("ranges", [])

        # Extract all i18n keys from ranges (only check keys, not numbers)
        i18n_keys = [r["key"] for r in ranges if "key" in r]

        # Verify all keys are exactly the 4 expected keys
        assert (
            set(i18n_keys) == EXPECTED_VIZ_KEYS
        ), f"Expected {EXPECTED_VIZ_KEYS}, got {set(i18n_keys)}"

        # Verify all keys are translatable in all languages
        for key in i18n_keys:
            for lang in SUPPORTED_LANGS:
                translation = t(lang, key)
                assert translation, f"Empty translation for {key} in {lang}"
                # Verify it's not just the key itself (actual translation)
                assert translation != key, f"Translation missing for {key} in {lang}"

    def test_bmi_visualization_keys_map_to_translations_via_api_athlete(
        self, client: TestClient
    ) -> None:
        """
        RU: Ключи из visualization ranges (athlete group, через API) мапятся на переводы.
        EN: Visualization range keys (athlete group, via API) map to translations.

        Tests athlete group (normal upper bound differs from adult).
        """
        # Athlete group (has visualization, different thresholds)
        payload = _valid_payload(age=25, athlete="yes")
        data = _post_bmi(client, payload)
        visualization = data.get("visualization")

        # Contract: athlete group must have visualization
        assert visualization is not None, "Athlete group must have visualization"
        ranges = visualization.get("ranges", [])

        # Extract i18n keys (only check keys, not numbers)
        i18n_keys = [r["key"] for r in ranges if "key" in r]

        # Verify all keys are translatable
        assert (
            set(i18n_keys) == EXPECTED_VIZ_KEYS
        ), f"Expected {EXPECTED_VIZ_KEYS}, got {set(i18n_keys)}"

        for key in i18n_keys:
            for lang_str in SUPPORTED_LANGS:
                lang: Language = lang_str  # type: ignore[assignment]
                translation = t(lang, key)
                assert translation, f"Empty translation for {key} in {lang}"
                assert translation != key, f"Translation missing for {key} in {lang}"

    def test_bmi_visualization_keys_map_to_translations_via_api_elderly(
        self, client: TestClient
    ) -> None:
        """
        RU: Ключи из visualization ranges (elderly group, через API) мапятся на переводы.
        EN: Visualization range keys (elderly group, via API) map to translations.

        Tests elderly group (different underweight/normal thresholds).
        """
        # Elderly group (age >= 60, has visualization, different thresholds)
        payload = _valid_payload(age=75, athlete="no")
        data = _post_bmi(client, payload)
        visualization = data.get("visualization")

        # Contract: elderly group must have visualization
        assert visualization is not None, "Elderly group must have visualization"
        ranges = visualization.get("ranges", [])

        # Extract i18n keys (only check keys, not numbers)
        i18n_keys = [r["key"] for r in ranges if "key" in r]

        # Verify all keys are translatable
        assert (
            set(i18n_keys) == EXPECTED_VIZ_KEYS
        ), f"Expected {EXPECTED_VIZ_KEYS}, got {set(i18n_keys)}"

        for key in i18n_keys:
            for lang_str in SUPPORTED_LANGS:
                lang: Language = lang_str  # type: ignore[assignment]
                translation = t(lang, key)
                assert translation, f"Empty translation for {key} in {lang}"
                assert translation != key, f"Translation missing for {key} in {lang}"


class TestNormalizeLangPolicy:
    """
    RU: Тесты на политику normalize_lang (ru/es мапятся на себя).
    EN: Tests for normalize_lang policy (ru/es map to themselves).
    """

    def test_normalize_lang_ru_maps_to_ru(self) -> None:
        """
        RU: ru-RU и ru мапятся на ru, не на en (разные регистры и разделители).
        EN: ru-RU and ru map to ru, not en (different cases and separators).
        """
        # Standard formats
        assert normalize_lang("ru-RU") == "ru"
        assert normalize_lang("ru") == "ru"
        # Lowercase variant
        assert normalize_lang("ru-ru") == "ru"
        # Underscore separator (normalized to dash)
        assert normalize_lang("ru_RU") == "ru"
        assert normalize_lang("ru_ru") == "ru"
        # Mixed case
        assert normalize_lang("RU-ru") == "ru"
        assert normalize_lang("RU-RU") == "ru"
        # Implicit locales (not in LANG_ALIASES, use LOCALE_SPECIAL_CASES)
        assert normalize_lang("ru-KZ") == "ru"  # Kazakhstan → ru (not en)
        assert normalize_lang("ru-BY") == "ru"  # Belarus → ru (not en)
        assert normalize_lang("ru-kz") == "ru"
        assert normalize_lang("ru-by") == "ru"

    def test_normalize_lang_es_maps_to_es(self) -> None:
        """
        RU: es-ES, es-MX, es-AR и es мапятся на es, не на en (разные регистры и разделители).
        EN: es-ES, es-MX, es-AR and es map to es, not en (different cases and separators).
        """
        # Standard formats
        assert normalize_lang("es-ES") == "es"  # Changed: was "en"
        assert normalize_lang("es-MX") == "es"
        assert normalize_lang("es-AR") == "es"  # Changed: was "en"
        assert normalize_lang("es") == "es"
        # Lowercase variants
        assert normalize_lang("es-es") == "es"
        assert normalize_lang("es-mx") == "es"
        # Underscore separator (normalized to dash)
        assert normalize_lang("es_ES") == "es"
        assert normalize_lang("es_es") == "es"
        # Mixed case
        assert normalize_lang("ES-es") == "es"
        assert normalize_lang("ES-ES") == "es"
        # Implicit locales (not in LANG_ALIASES, use LOCALE_SPECIAL_CASES)
        assert normalize_lang("es-CL") == "es"  # Chile → es (not en)
        assert normalize_lang("es-CO") == "es"  # Colombia → es (not en)
        assert normalize_lang("es-cl") == "es"
        assert normalize_lang("es-co") == "es"

    def test_normalize_lang_en_maps_to_en(self) -> None:
        """
        RU: en-US, en-GB и en мапятся на en (разные регистры и разделители).
        EN: en-US, en-GB and en map to en (different cases and separators).
        """
        # Standard formats
        assert normalize_lang("en-US") == "en"
        assert normalize_lang("en-GB") == "en"
        assert normalize_lang("en") == "en"
        # Lowercase variants
        assert normalize_lang("en-us") == "en"
        assert normalize_lang("en-gb") == "en"
        # Underscore separator (normalized to dash)
        assert normalize_lang("en_US") == "en"
        assert normalize_lang("en_us") == "en"
        # Mixed case
        assert normalize_lang("EN-us") == "en"
        assert normalize_lang("EN-US") == "en"

    def test_normalize_lang_unknown_fallback_to_en(self) -> None:
        """
        RU: Неизвестные языки мапятся на en (fallback).
        EN: Unknown languages map to en (fallback).
        """
        assert normalize_lang("fr") == "en"
        assert normalize_lang("de-DE") == "en"
        assert normalize_lang("français") == "en"
        assert normalize_lang(None) == "en"
        assert normalize_lang("") == "en"

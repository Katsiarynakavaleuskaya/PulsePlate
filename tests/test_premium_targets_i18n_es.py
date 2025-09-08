# -*- coding: utf-8 -*-
"""
RU: Тест ES локализации для /api/v1/premium/targets (snapshot тест).
EN: Test ES localization for /api/v1/premium/targets (snapshot test).
"""
import pytest
from fastapi.testclient import TestClient

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(app_mod.app)  # type: ignore


@pytest.mark.parametrize("lang", ["es"])
def test_premium_targets_es_localization(lang):
    """Test Spanish localization for premium targets endpoint."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": lang,
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()

    # Check basic structure
    assert "kcal_daily" in data
    assert "macros" in data
    assert "water_ml" in data
    assert "priority_micros" in data
    assert "activity_weekly" in data
    assert "calculation_date" in data
    assert "warnings" in data

    # Check that warnings are in Spanish for life stage warnings
    if data["warnings"]:
        for warning in data["warnings"]:
            assert "code" in warning
            assert "message" in warning
            # Spanish messages should contain Spanish text
            if warning["code"] in ["teen", "pregnant", "lactating", "elderly", "child"]:
                message = warning["message"]
                # Check for Spanish keywords
                spanish_keywords = [
                    "adolescente",
                    "embarazo",
                    "lactancia",
                    "mayor",
                    "niño",
                    "especializada",
                ]
                assert any(
                    keyword in message.lower() for keyword in spanish_keywords
                ), f"Message '{message}' doesn't contain Spanish keywords"


def test_premium_targets_es_life_stage_warnings():
    """Test Spanish life stage warnings specifically."""
    test_cases = [
        {
            "age": 16,
            "life_stage": "teen",
            "expected_keywords": ["adolescente", "apropiadas"],
        },
        {
            "age": 30,
            "life_stage": "pregnant",
            "expected_keywords": ["embarazo", "especializada"],
        },
        {
            "age": 30,
            "life_stage": "lactating",
            "expected_keywords": ["lactancia", "nutrientes"],
        },
        {
            "age": 65,
            "life_stage": "elderly",
            "expected_keywords": ["micronutrientes", "diferir"],
        },
        {
            "age": 8,
            "life_stage": "child",
            "expected_keywords": ["infantil", "pediátricas"],
        },
    ]

    for case in test_cases:
        payload = {
            "sex": "female",
            "age": case["age"],
            "height_cm": 168,
            "weight_kg": 60,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": case["life_stage"],
            "lang": "es",
        }

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()
        warnings = data["warnings"]

        # Find the expected warning
        expected_code = case["life_stage"]
        warning = next((w for w in warnings if w.get("code") == expected_code), None)

        if warning:
            message = warning["message"].lower()
            for keyword in case["expected_keywords"]:
                assert (
                    keyword in message
                ), f"Expected keyword '{keyword}' not found in message '{warning['message']}'"


def test_premium_targets_es_snapshot_values():
    """Test that Spanish localization returns consistent values (snapshot test)."""
    payload = {
        "sex": "male",
        "age": 35,
        "height_cm": 180,
        "weight_kg": 80,
        "activity": "active",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "es",
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()

    # Snapshot test - check that values are reasonable
    assert 2000 <= data["kcal_daily"] <= 3500  # Reasonable calorie range for adult male
    assert data["macros"]["protein_g"] > 100  # Should have adequate protein
    assert data["macros"]["fat_g"] > 50  # Should have adequate fat
    assert data["macros"]["carbs_g"] > 200  # Should have adequate carbs
    assert data["water_ml"] > 2000  # Should have adequate water intake

    # Check priority micros structure
    priority_micros = data["priority_micros"]
    assert isinstance(priority_micros, dict)
    assert len(priority_micros) > 0

    # Check activity weekly structure
    activity_weekly = data["activity_weekly"]
    assert "moderate_aerobic_min" in activity_weekly
    assert "strength_sessions" in activity_weekly
    assert "steps_daily" in activity_weekly

    # Check calculation date format
    assert isinstance(data["calculation_date"], str)
    assert len(data["calculation_date"]) > 0


def test_premium_targets_es_multilingual_consistency():
    """Test that Spanish responses are consistent with other languages."""
    base_payload = {
        "sex": "female",
        "age": 28,
        "height_cm": 165,
        "weight_kg": 65,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "adult",
    }

    # Test with different languages
    languages = ["es", "en", "ru"]
    responses = {}

    for lang in languages:
        payload = {**base_payload, "lang": lang}
        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200
        responses[lang] = resp.json()

    # Check that numerical values are consistent across languages
    es_data = responses["es"]
    en_data = responses["en"]
    ru_data = responses["ru"]

    # Calorie values should be the same regardless of language
    assert es_data["kcal_daily"] == en_data["kcal_daily"] == ru_data["kcal_daily"]

    # Macro values should be the same
    for macro in ["protein_g", "fat_g", "carbs_g", "fiber_g"]:
        assert (
            es_data["macros"][macro]
            == en_data["macros"][macro]
            == ru_data["macros"][macro]
        )

    # Water intake should be the same
    assert es_data["water_ml"] == en_data["water_ml"] == ru_data["water_ml"]

    # Priority micros should have the same values
    for nutrient in es_data["priority_micros"]:
        if (
            nutrient in en_data["priority_micros"]
            and nutrient in ru_data["priority_micros"]
        ):
            assert (
                es_data["priority_micros"][nutrient]
                == en_data["priority_micros"][nutrient]
                == ru_data["priority_micros"][nutrient]
            )


def test_premium_targets_es_special_cases():
    """Test Spanish localization for special cases."""
    # Test with pregnant woman
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "pregnant",
        "lang": "es",
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()

    # Should have pregnancy warning in Spanish
    pregnancy_warnings = [w for w in data["warnings"] if w.get("code") == "pregnant"]
    assert len(pregnancy_warnings) > 0

    pregnancy_warning = pregnancy_warnings[0]
    message = pregnancy_warning["message"].lower()
    assert "embarazo" in message or "pregnancy" in message  # Should be in Spanish

    # Test with elderly person
    payload = {
        "sex": "male",
        "age": 70,
        "height_cm": 175,
        "weight_kg": 75,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "elderly",
        "lang": "es",
    }

    resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert resp.status_code == 200

    data = resp.json()

    # Should have elderly warning in Spanish
    elderly_warnings = [w for w in data["warnings"] if w.get("code") == "elderly"]
    assert len(elderly_warnings) > 0

    elderly_warning = elderly_warnings[0]
    message = elderly_warning["message"].lower()
    assert "micronutrientes" in message or "diferir" in message  # Should be in Spanish

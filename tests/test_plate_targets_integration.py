# -*- coding: utf-8 -*-
"""
RU: Интеграционный тест покрытия Plate→Targets.
EN: Integration test for Plate→Targets coverage.
"""
import pytest
from fastapi.testclient import TestClient

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(app_mod.app)  # type: ignore


def test_plate_targets_integration_workflow():
    """Test complete workflow from Plate generation to Targets comparison."""
    # Step 1: Generate plate
    plate_payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    plate_resp = client.post(
        "/api/v1/premium/plate", json=plate_payload, headers={"X-API-Key": "test_key"}
    )
    assert plate_resp.status_code == 200
    plate_data = plate_resp.json()

    # Step 2: Generate targets for the same profile
    targets_payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }

    targets_resp = client.post(
        "/api/v1/premium/targets",
        json=targets_payload,
        headers={"X-API-Key": "test_key"},
    )
    assert targets_resp.status_code == 200
    targets_data = targets_resp.json()

    # Step 3: Compare plate vs targets
    # Check that plate calories are reasonable compared to targets
    plate_kcal = plate_data["kcal"]
    target_kcal = targets_data["kcal_daily"]

    # Allow 10% deviation
    assert (
        abs(plate_kcal - target_kcal) / target_kcal <= 0.1
    ), f"Plate kcal {plate_kcal} vs target {target_kcal}"

    # Check macro alignment
    plate_macros = plate_data["macros"]
    target_macros = targets_data["macros"]

    for macro in ["protein_g", "fat_g", "carbs_g"]:
        if macro in plate_macros and macro in target_macros:
            plate_val = plate_macros[macro]
            target_val = target_macros[macro]
            # Allow 15% deviation for macros
            assert (
                abs(plate_val - target_val) / target_val <= 0.15
            ), f"{macro}: plate {plate_val} vs target {target_val}"


def test_plate_targets_micros_coverage():
    """Test that plate micros can be compared against target micros."""
    # Generate plate with micros
    plate_payload = {
        "sex": "male",
        "age": 25,
        "height_cm": 180,
        "weight_kg": 75,
        "activity": "active",
        "goal": "maintain",
    }

    plate_resp = client.post(
        "/api/v1/premium/plate", json=plate_payload, headers={"X-API-Key": "test_key"}
    )
    assert plate_resp.status_code == 200
    plate_data = plate_resp.json()

    # Generate targets
    targets_payload = {
        "sex": "male",
        "age": 25,
        "height_cm": 180,
        "weight_kg": 75,
        "activity": "active",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }

    targets_resp = client.post(
        "/api/v1/premium/targets",
        json=targets_payload,
        headers={"X-API-Key": "test_key"},
    )
    assert targets_resp.status_code == 200
    targets_data = targets_resp.json()

    # Check that both have micros data
    assert "day_micros" in plate_data
    assert "priority_micros" in targets_data

    plate_micros = plate_data["day_micros"]
    target_micros = targets_data["priority_micros"]

    # Both should have micronutrient data
    assert len(plate_micros) > 0
    assert len(target_micros) > 0

    # Check for common micronutrients
    common_micros = set(plate_micros.keys()) & set(target_micros.keys())
    assert len(common_micros) > 0, "No common micronutrients between plate and targets"


def test_plate_targets_different_goals():
    """Test plate-targets integration with different goals."""
    test_cases = [
        {"goal": "loss", "deficit_pct": 20},
        {"goal": "gain", "surplus_pct": 15},
        {"goal": "maintain"},
    ]

    for case in test_cases:
        base_payload = {
            "sex": "female",
            "age": 35,
            "height_cm": 165,
            "weight_kg": 65,
            "activity": "light",
        }

        # Generate plate
        plate_payload = {**base_payload, **case}
        plate_resp = client.post(
            "/api/v1/premium/plate",
            json=plate_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert plate_resp.status_code == 200
        plate_data = plate_resp.json()

        # Generate targets
        targets_payload = {**base_payload, **case, "life_stage": "adult", "lang": "en"}
        targets_resp = client.post(
            "/api/v1/premium/targets",
            json=targets_payload,
            headers={"X-API-Key": "test_key"},
        )
        assert targets_resp.status_code == 200
        targets_data = targets_resp.json()

        # Verify both have the expected structure
        assert "kcal" in plate_data
        assert "kcal_daily" in targets_data
        assert "day_micros" in plate_data
        assert "priority_micros" in targets_data


def test_plate_targets_life_stage_warnings():
    """Test that life stage warnings from targets are relevant for plate generation."""
    # Test with pregnant woman
    payload = {
        "sex": "female",
        "age": 28,
        "height_cm": 170,
        "weight_kg": 70,
        "activity": "moderate",
        "goal": "maintain",
        "life_stage": "pregnant",
        "lang": "en",
    }

    # Generate targets (should have warnings)
    targets_resp = client.post(
        "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
    )
    assert targets_resp.status_code == 200
    targets_data = targets_resp.json()

    # Check that warnings are present
    assert "warnings" in targets_data
    assert len(targets_data["warnings"]) > 0

    # Check that warning is about pregnancy
    warning_codes = [w.get("code") for w in targets_data["warnings"]]
    assert "pregnant" in warning_codes

    # Generate plate (should work despite warnings)
    plate_payload = {
        k: v for k, v in payload.items() if k not in ["life_stage", "lang"]
    }
    plate_resp = client.post(
        "/api/v1/premium/plate", json=plate_payload, headers={"X-API-Key": "test_key"}
    )
    assert plate_resp.status_code == 200
    plate_data = plate_resp.json()

    # Plate should still be generated successfully
    assert "kcal" in plate_data
    assert "day_micros" in plate_data


def test_plate_targets_validation_consistency():
    """Test that validation rules are consistent between plate and targets."""
    # Test with invalid data that should fail both endpoints
    invalid_payload = {
        "sex": "invalid_sex",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    # Both should return 422 for invalid sex
    plate_resp = client.post(
        "/api/v1/premium/plate", json=invalid_payload, headers={"X-API-Key": "test_key"}
    )
    assert plate_resp.status_code == 422

    targets_payload = {**invalid_payload, "life_stage": "adult", "lang": "en"}
    targets_resp = client.post(
        "/api/v1/premium/targets",
        json=targets_payload,
        headers={"X-API-Key": "test_key"},
    )
    assert targets_resp.status_code == 422


def test_plate_targets_api_key_consistency():
    """Test that both endpoints require the same API key."""
    payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168,
        "weight_kg": 60,
        "activity": "moderate",
        "goal": "maintain",
    }

    # Test without API key
    plate_resp = client.post("/api/v1/premium/plate", json=payload)
    assert plate_resp.status_code == 403

    targets_payload = {**payload, "life_stage": "adult", "lang": "en"}
    targets_resp = client.post("/api/v1/premium/targets", json=targets_payload)
    assert targets_resp.status_code == 403

    # Test with wrong API key
    plate_resp = client.post(
        "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "wrong_key"}
    )
    assert plate_resp.status_code == 403

    targets_resp = client.post(
        "/api/v1/premium/targets",
        json=targets_payload,
        headers={"X-API-Key": "wrong_key"},
    )
    assert targets_resp.status_code == 403

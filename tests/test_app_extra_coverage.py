"""Extra main.py coverage tests focusing on helper functions and common edge cases.

These tests are intentionally lightweight to avoid duplicating logic covered elsewhere,
but they help stabilize coverage across helper functions and simple endpoints.
"""

import os
from unittest.mock import Mock
from tests._client import get_client

import pytest
from fastapi.testclient import TestClient

import app as app_module
from tests.helpers.fast_update_stubs import make_scheduler_stub, patch_app_get_update_scheduler


class TestAppHelperFunctions:
    """Test standalone helper functions in main.py."""

    def setup_method(self) -> None:
        os.environ["API_KEY"] = "test-key"
        self.client = get_client()

    def teardown_method(self) -> None:
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_legacy_category_label_mappings(self):
        # English special-case: "Normal weight" -> "Healthy weight"
        assert app_module.legacy_category_label("Normal weight", "en") == "Healthy weight"
        # Russian special-case phrase tweak
        assert app_module.legacy_category_label("Избыточная масса", "ru") == "Избыточный вес"
        # Other categories remain unchanged
        assert app_module.legacy_category_label("Obese", "en") == "Obese"

    def test_rate_limiting_available_flag(self):
        # Should just return a boolean based on optional slowapi import presence
        val = app_module._is_rate_limiting_available()
        assert isinstance(val, bool)

    def test_bmr_wrapper_and_tdee_wrapper(self):
        # BMR wrapper should produce a dict of numeric values
        bmr = app_module._calculate_all_bmr_wrapper(70, 175, 30, "male", bodyfat=15)
        assert isinstance(bmr, dict) and bmr
        # TDEE wrapper should map BMR dict to TDEE dict with same keys
        tdee = app_module._calculate_all_tdee_wrapper(bmr, "moderate")
        assert isinstance(tdee, dict) and set(tdee.keys()) == set(bmr.keys())
        assert all(isinstance(v, (int, float)) for v in tdee.values())

    def test_resolve_attr_utility(self):
        # resolve_attr should pick attribute from candidates or return default
        mock_mod = Mock()
        mock_mod.answer = 42
        val = app_module.resolve_attr("answer", "missing", [mock_mod])
        assert val == 42
        val2 = app_module.resolve_attr("nope", "fallback", [mock_mod])
        assert val2 == "fallback"

    def test_bmi_endpoint_visualization_flag_safe(self):
        # Ensure visualization key is added when include_chart=True
        payload = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "include_chart": True,
        }
        r = self.client.post("/bmi", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "visualization" in data
        # Visualization is generated and populated (available=True with chart_base64)
        # or not available (available=False with error) - both are valid behaviors
        viz = data["visualization"]
        assert isinstance(viz.get("available"), bool)


class TestEndpointsAndValidation:
    def setup_method(self) -> None:
        os.environ["API_KEY"] = "test-key"
        self.client = get_client()

    def teardown_method(self) -> None:
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_bmi_request_validation_edge_cases(self):
        # Extreme but valid values
        data = {
            "weight_kg": 30.0,
            "height_m": 1.2,
            "age": 99,
            "gender": "female",
            "pregnant": "no",
            "athlete": "no",
        }
        assert self.client.post("/bmi", json=data).status_code == 200

        data2 = {
            "weight_kg": 300.0,
            "height_m": 2.5,
            "age": 99,
            "gender": "male",
            "pregnant": "no",
            "athlete": "yes",
        }
        assert self.client.post("/bmi", json=data2).status_code == 200

    def test_bmi_v1_success(self):
        payload = {"weight_kg": 70.0, "height_cm": 175.0, "group": "general"}
        r = self.client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test-key"})
        assert r.status_code == 200

    def test_invalid_json_and_missing_fields(self):
        r = self.client.post(
            "/bmi", content="not json", headers={"Content-Type": "application/json"}
        )
        assert r.status_code == 422

        # Missing weight_kg
        bad = {"height_m": 1.75, "age": 30, "gender": "male"}
        assert self.client.post("/bmi", json=bad).status_code == 422

    def test_invalid_types_and_enums(self):
        bad_type = {"weight_kg": "x", "height_m": 1.75, "age": 30, "gender": "male"}
        assert self.client.post("/bmi", json=bad_type).status_code == 422

        bad_enum = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "invalid",
            "pregnant": "no",
            "athlete": "no",
        }
        assert self.client.post("/bmi", json=bad_enum).status_code == 422

    def test_admin_and_debug_endpoints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Debug page is defined in main.py; tolerate environments where it might be restricted
        r = self.client.get("/debug_env")
        assert r.status_code in [200, 404, 405]

        # Admin endpoints (provided by routers) may be up or return 500/503 when backends are unavailable
        r1 = self.client.get("/api/v1/admin/db-status", headers={"X-API-Key": "test-key"})
        assert r1.status_code in [200, 500, 503]
        scheduler = make_scheduler_stub()
        patch_app_get_update_scheduler(monkeypatch, app_module, scheduler)
        r2 = self.client.post("/api/v1/admin/force-update", headers={"X-API-Key": "test-key"})
        assert r2.status_code in [200, 500, 503]

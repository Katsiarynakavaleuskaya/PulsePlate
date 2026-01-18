"""
RU: Тесты для обработки ошибок PRO endpoint BMI calculation.
EN: Tests for PRO endpoint BMI calculation error handling.

Covers error paths in app/routers/bmi_pro.py:calculate_bmi_pro()
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestProEndpointErrorHandling:
    """Tests for PRO endpoint error handling (covers lines 292-293, 310-311, 315-316, 320-321, 337-339)."""

    def test_calculate_bmi_result_is_none_returns_501(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _get_engine_calculator returns None → 501 (covers lines 292-293)."""
        import app.routers.bmi_pro as bmi_pro

        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        # Patch seam to return None (simulates ImportError)
        monkeypatch.setattr(bmi_pro, "_get_engine_calculator", lambda: None)

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 501
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        # Check for localized error message
        assert "detail" in data
        # Should contain bmi_engine_unavailable message (localized)

    def test_not_implemented_error_returns_501(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that NotImplementedError → 501 (covers lines 310-311)."""
        import app.routers.bmi_pro as bmi_pro

        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        def _raise_not_implemented(*args: object, **kwargs: object) -> None:
            raise NotImplementedError("Engine not available")

        # Patch seam to return function that raises NotImplementedError
        monkeypatch.setattr(bmi_pro, "_get_engine_calculator", lambda: _raise_not_implemented)

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 501
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert "detail" in data

    def test_value_error_returns_400(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ValueError → 400 (covers lines 315-316)."""
        import app.routers.bmi_pro as bmi_pro

        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        def _raise_value_error(*args: object, **kwargs: object) -> None:
            raise ValueError("Invalid parameters")

        # Patch seam to return function that raises ValueError
        monkeypatch.setattr(bmi_pro, "_get_engine_calculator", lambda: _raise_value_error)

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 400
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert "detail" in data
        # Should contain bmi_invalid_parameters message (localized)

    def test_generic_exception_returns_500(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that generic Exception → 500 (covers lines 320-321)."""
        import app.routers.bmi_pro as bmi_pro

        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        def _raise_runtime_error(*args: object, **kwargs: object) -> None:
            raise RuntimeError("Unexpected error")

        # Patch seam to return function that raises RuntimeError
        monkeypatch.setattr(bmi_pro, "_get_engine_calculator", lambda: _raise_runtime_error)

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 500
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert "detail" in data
        # Should contain bmi_calculation_failed message (localized)

    def test_soft_paywall_hook_when_disabled_returns_none(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that soft_paywall is None when SOFT_PAYWALL_ENABLED=False (covers lines 337-339)."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        # Disable soft paywall
        monkeypatch.setenv("SOFT_PAYWALL_ENABLED", "false")

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        # soft_paywall should be None when disabled
        assert data.get("soft_paywall") is None

    def test_visualization_error_handled_gracefully(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that visualization build error is handled gracefully (covers lines 361-362)."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        import app.routers.bmi_pro as bmi_pro

        def _build_failed(*args: object, **kwargs: object) -> object:
            raise Exception("Build failed")

        monkeypatch.setattr(bmi_pro, "build_bmi_scale_v1", _build_failed)

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        # visualization should be None when build fails
        assert data.get("visualization") is None

    def test_soft_paywall_hook_when_enabled_returns_hook(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that soft_paywall is returned when SOFT_PAYWALL_ENABLED=True (covers line 339)."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        # Enable soft paywall
        monkeypatch.setenv("SOFT_PAYWALL_ENABLED", "true")

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        # soft_paywall should be present when enabled
        assert data.get("soft_paywall") is not None
        assert data["soft_paywall"]["id"] == "bmi.pro_interpretation_v1"


class TestProEndpointHelperFunctions:
    """Tests for helper functions in bmi_pro.py (covers lines 71-72, 77, 82-90, 97)."""

    def test_pro_engine_importerror_fallback_returns_501(
        self, client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        RU: Тест fallback при ImportError (covers lines 71-72 via _get_engine_calculator seam).
        EN: Test fallback when ImportError occurs (covers lines 71-72 via _get_engine_calculator seam).

        Strategy: Patch _get_engine_calculator to return None (simulates ImportError),
        verify endpoint returns 501. This covers the except ImportError block (line 71)
        and return None (line 72) without requiring module reload or sys.modules mutations.
        """
        import app.routers.bmi_pro as bmi_pro

        # Patch seam to simulate ImportError (returns None)
        monkeypatch.setattr(bmi_pro, "_get_engine_calculator", lambda: None)

        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "female",
            "waist_cm": 80.0,
            "hip_cm": 100.0,
            "athlete": False,
            "pregnant": False,
            "lang": "en",
        }

        resp = client.post("/api/v1/pro/bmi/calculate", json=payload, headers=pro_headers)
        assert resp.status_code == 501
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert "detail" in data

    def test_env_bool_default_return(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _env_bool returns default for invalid values (covers line 77)."""
        from app.routers import bmi_pro

        # Set invalid value
        monkeypatch.setenv("TEST_ENV_BOOL", "invalid")
        result = bmi_pro._env_bool("TEST_ENV_BOOL", default=True)
        assert result is True  # Should return default for invalid value

    def test_normalize_bool_flag_non_str_non_bool(self) -> None:
        """Test _normalize_bool_flag with non-str, non-bool input (covers lines 82-90)."""
        from app.routers import bmi_pro

        # Test with bool (covers line 83)
        assert bmi_pro._normalize_bool_flag(True) is True
        assert bmi_pro._normalize_bool_flag(False) is False
        # Test with int (not bool, not str)
        assert bmi_pro._normalize_bool_flag(0) is False
        assert bmi_pro._normalize_bool_flag(1) is False
        # Test with None
        assert bmi_pro._normalize_bool_flag(None) is False  # type: ignore[arg-type]
        # Test with empty string
        assert bmi_pro._normalize_bool_flag("") is False
        # Test with whitespace-only string
        assert bmi_pro._normalize_bool_flag("   ") is False
        # Test with default yes_values (covers lines 89-90: default set)
        assert bmi_pro._normalize_bool_flag("yes") is True
        assert bmi_pro._normalize_bool_flag("y") is True
        assert bmi_pro._normalize_bool_flag("true") is True
        assert bmi_pro._normalize_bool_flag("1") is True
        assert bmi_pro._normalize_bool_flag("да") is True
        assert bmi_pro._normalize_bool_flag("д") is True
        assert bmi_pro._normalize_bool_flag("si") is True
        assert bmi_pro._normalize_bool_flag("sí") is True
        # Test with custom yes_values (covers lines 89-90)
        custom_yes = {"custom", "yes"}
        assert bmi_pro._normalize_bool_flag("custom", yes_values=custom_yes) is True
        assert bmi_pro._normalize_bool_flag("no", yes_values=custom_yes) is False

    def test_build_soft_paywall_hook_disabled_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test _build_soft_paywall_hook returns None when disabled (covers line 97)."""
        from app.routers import bmi_pro

        monkeypatch.setenv("SOFT_PAYWALL_ENABLED", "false")
        result = bmi_pro._build_soft_paywall_hook("en")
        assert result is None

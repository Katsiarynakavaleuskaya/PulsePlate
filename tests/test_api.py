# -*- coding: utf-8 -*-
from pathlib import Path
from typing import NoReturn, cast
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from module_purge import purge_modules

# client fixture is provided by conftest.py


def test_v1_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_v1_bmi_happy(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] == 24.2
    # v1 endpoint uses core/i18n categories in EN
    assert data["category"] == "Normal weight"


def test_v1_bmi_invalid_height(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 0, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    # Pydantic validation returns 422 for invalid field values
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_invalid_weight(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": -50, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    # Pydantic validation returns 422 for invalid field values
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_unrealistic_weight(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 10, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    # Pydantic validation returns 422 for unrealistic weight
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_invalid_group(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 170, "group": "invalid"},
        headers={"X-API-Key": "test_key"},
    )
    # Since we allow any string for group, this should work
    assert r.status_code == 200
    data = r.json()
    assert "bmi" in data


def test_v1_bmi_underweight(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 45, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] < 18.5
    assert data["category"] == "Underweight"


def test_v1_bmi_overweight(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 85, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert 25 <= data["bmi"] < 30
    assert data["category"] == "Overweight"


def test_v1_bmi_obese(client):
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 100, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] >= 30
    # Uses obesity classes
    assert data["category"] == "Obese Class I"


def test_v1_bodyfat(client):
    r = client.post(
        "/api/v1/bodyfat",
        json={
            "height_m": 1.70,
            "weight_kg": 65,
            "age": 28,
            "gender": "female",
            "neck_cm": 34,
            "waist_cm": 74,
            "hip_cm": 94,
            "language": "en",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "methods" in data
    assert "median" in data
    assert "labels" in data


def test_v1_bodyfat_missing_hip(client):
    r = client.post(
        "/api/v1/bodyfat",
        json={
            "height_m": 1.70,
            "weight_kg": 65,
            "age": 28,
            "gender": "female",
            "neck_cm": 34,
            "waist_cm": 74,
            "language": "en",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "methods" in data
    # Since hip_cm missing, us_navy should not be in methods
    assert "us_navy" not in data["methods"]


def test_bodyfat_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic seam test for bodyfat router unavailability path."""
    import app as app_mod
    import legacy_app

    monkeypatch.setattr(legacy_app, "get_bodyfat_router", None, raising=True)
    assert app_mod.get_bodyfat_router is None


def test_insight_import_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    vip_headers: dict[str, str],
) -> None:
    """Test coverage for llm import exception in main.py."""
    import app as app_mod
    import legacy_app

    def _raise_import_error() -> NoReturn:
        raise ImportError("boom")

    # Deterministic import-failure branch without sys.modules mutation.
    monkeypatch.setattr(legacy_app, "_load_llm_get_provider", _raise_import_error, raising=True)
    # Force feature enabled to prevent early-return bypass via disabled check.
    monkeypatch.setenv("FEATURE_INSIGHT", "true")

    client = TestClient(cast(ASGIApp, app_mod.app))

    response = client.post(
        "/api/v1/insight",
        json={"text": "test"},
        headers=vip_headers,
    )
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    # Backward-compatible shape: `detail` exists, but must not leak internals.
    assert "LLM module is not available" in data["detail"]
    assert "boom" not in data.get("detail", "")


@patch("llm.get_provider")
def test_api_insight_provider_generate_failure(
    mock_get_provider: Mock,
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test coverage for provider.generate exception in insight endpoint."""
    from unittest.mock import MagicMock

    mock_provider = MagicMock()
    mock_provider.name = "test"
    mock_provider.generate.side_effect = Exception("Generate failed")
    mock_get_provider.return_value = mock_provider

    # Deterministic env setup with auto-cleanup
    monkeypatch.setenv("FEATURE_INSIGHT", "true")

    response = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    # Privacy/safety: never leak raw exception details to the client.
    assert "Generate failed" not in data.get("detail", "")


@patch("llm.get_provider")
def test_api_insight_provider_none(
    mock_get_provider: Mock,
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test coverage for provider is None in insight endpoint."""
    mock_get_provider.return_value = None

    # Deterministic env setup with auto-cleanup
    monkeypatch.setenv("FEATURE_INSIGHT", "true")

    response = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert "No LLM provider configured" in data["detail"]


def test_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    # Metrics endpoint returns Prometheus format, not JSON
    content = response.text
    assert "python_info" in content or "error" in content


def test_category_by_bmi_ru(client):
    from core.bmi.engine import _bmi_category
    from core.i18n import t, normalize_lang

    def bmi_category(bmi: float, lang: str) -> str:
        """Helper to get localized BMI category."""
        category_key = _bmi_category(bmi=bmi, age=30, group="general")
        if category_key is None:
            return "N/A"
        lang_norm = normalize_lang(lang)
        i18n_key = f"bmi.{category_key}"
        try:
            return t(lang_norm, i18n_key)
        except KeyError:
            # Fallback to legacy keys
            legacy_map = {
                "underweight": "bmi_underweight",
                "normal": "bmi_normal",
                "overweight": "bmi_overweight",
                "obesity_1": "bmi_obese_1",
                "obesity_2": "bmi_obese_2",
                "obesity_3": "bmi_obese_3",
            }
            legacy_key = legacy_map.get(category_key, f"bmi_{category_key}")
            return t(lang_norm, legacy_key)

    assert bmi_category(17, "ru") == "Недостаточная масса"
    assert bmi_category(22, "ru") == "Норма"
    assert bmi_category(27, "ru") == "Избыточная масса"
    assert bmi_category(32, "ru") == "Ожирение I степени"


def test_compute_wht_ratio_round_exception(client) -> None:
    """
    Test that _compute_wht_ratio propagates round exceptions.

    _compute_wht_ratio should NOT catch generic exceptions raised by round().
    It must propagate them so callers/tests can detect unexpected failures.
    """
    import builtins

    import pytest
    from core.bmi.engine import _compute_wht_ratio

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("round exploded")

    # Patch builtins.round used by the function
    with patch.object(builtins, "round", boom):
        # Must raise exception, not return None or value
        with pytest.raises(RuntimeError, match="round exploded"):
            _compute_wht_ratio(waist_cm=80.0, height_m=1.70)


# Removed: test_v1_bmi_invalid_api_key and test_v1_bmi_no_api_key
# Reason: /api/v1/bmi is now a public endpoint (no API key required)
# These tests are obsolete as they tested API key validation on BMI endpoint


def test_v1_insight_invalid_api_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tier guard test: FREE headers (no key) → 403. Status-only assertion."""
    monkeypatch.setenv("API_KEY", "valid_key")

    # FREE headers (empty) → VIP tier gate denies access.
    r = client.post("/api/v1/insight", json={"text": "test"}, headers={})
    assert r.status_code == 403


def test_slowapi_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic seam test for slowapi-unavailable behavior."""
    import app as app_mod
    import legacy_app

    monkeypatch.setattr(legacy_app, "limiter", None, raising=True)
    assert app_mod.limiter is None


def test_prometheus_import_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic seam test for exporter failure fallback on /metrics."""
    import prometheus_client

    def _boom() -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(prometheus_client, "generate_latest", _boom)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert "error" in data


def test_no_app_import_skip_fallback_marker() -> None:
    """Guard: app import failures in this suite must fail, not skip."""
    content = Path(__file__).read_text(encoding="utf-8")
    marker = 'pytest.skip("App import ' + 'failed unexpectedly")'
    assert marker not in content

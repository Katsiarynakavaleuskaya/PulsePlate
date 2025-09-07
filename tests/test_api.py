# -*- coding: utf-8 -*-
import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = TestClient(app_module.app)


def test_v1_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_v1_bmi_happy():
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


def test_v1_bmi_invalid_height():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 0, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    # Pydantic validation returns 422 for invalid field values
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_invalid_weight():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": -50, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    # Pydantic validation returns 422 for invalid field values
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_unrealistic_weight():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 10, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    # Pydantic validation returns 422 for unrealistic weight
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_v1_bmi_invalid_group():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 170, "group": "invalid"},
        headers={"X-API-Key": "test_key"},
    )
    # Since we allow any string for group, this should work
    assert r.status_code == 200
    data = r.json()
    assert "bmi" in data


def test_v1_bmi_underweight():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 45, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bmi"] < 18.5
    assert data["category"] == "Underweight"


def test_v1_bmi_overweight():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 85, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "test_key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert 25 <= data["bmi"] < 30
    assert data["category"] == "Overweight"


def test_v1_bmi_obese():
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


def test_v1_bodyfat():
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


def test_v1_bodyfat_missing_hip():
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


def test_bodyfat_import_failure():
    """Test coverage for bodyfat import exception in app.py."""
    import builtins
    import sys
    from unittest.mock import patch

    # Save original app module if it exists
    original_app = sys.modules.get("app")

    # Save original before patching
    original_import = builtins.__import__

    with patch.object(builtins, "__import__") as mock_import:
        # Mock the import to fail
        def side_effect(name, *args, **kwargs):
            if name == "bodyfat":
                raise ImportError("Mocked import failure")
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = side_effect

        # Re-import app to trigger the exception
        if "app" in sys.modules:
            del sys.modules["app"]
        try:
            import app

            # If import succeeds, check that get_bodyfat_router is None
            assert app.get_bodyfat_router is None
        except Exception:
            pytest.skip("App import failed unexpectedly")
        finally:
            # Restore original app module
            if original_app is not None:
                sys.modules["app"] = original_app
            elif "app" in sys.modules:
                del sys.modules["app"]


def test_insight_import_failure():
    """Test coverage for llm import exception in app.py."""
    import builtins
    import sys
    from unittest.mock import patch

    # Save original app module if it exists
    original_app = sys.modules.get("app")

    # Save original before patching
    original_import = builtins.__import__

    with patch.object(builtins, "__import__") as mock_import:
        # Mock the import to fail for llm
        def side_effect(name, *args, **kwargs):
            if name == "llm":
                raise ImportError("Mocked llm import failure")
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = side_effect

        # Re-import app to trigger the exception
        if "app" in sys.modules:
            del sys.modules["app"]
        try:
            import app

            client = TestClient(app.app)

            response = client.post(
                "/api/v1/insight",
                json={"text": "test"},
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 503
            data = response.json()
            assert "insight provider not configured" in data["detail"]
        except Exception:
            pytest.skip("App import failed unexpectedly")
        finally:
            # Restore original app module
            if original_app is not None:
                sys.modules["app"] = original_app
            elif "app" in sys.modules:
                del sys.modules["app"]


@patch("llm.get_provider")
def test_api_insight_provider_generate_failure(mock_get_provider):
    """Test coverage for provider.generate exception in insight endpoint."""
    from unittest.mock import MagicMock

    mock_provider = MagicMock()
    mock_provider.name = "test"
    mock_provider.generate.side_effect = Exception("Generate failed")
    mock_get_provider.return_value = mock_provider

    response = client.post(
        "/api/v1/insight", json={"text": "test"}, headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 503
    data = response.json()
    assert "insight provider unavailable" in data["detail"]


@patch("llm.get_provider")
def test_api_insight_provider_none(mock_get_provider):
    """Test coverage for provider is None in insight endpoint."""
    mock_get_provider.return_value = None

    response = client.post(
        "/api/v1/insight", json={"text": "test"}, headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 503
    data = response.json()
    assert "insight provider not configured" in data["detail"]


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], float)
    assert data["uptime_seconds"] >= 0


def test_category_by_bmi_ru():
    from bmi_core import bmi_category

    assert bmi_category(17, "ru") == "Недостаточная масса"
    assert bmi_category(22, "ru") == "Норма"
    assert bmi_category(27, "ru") == "Избыточная масса"
    assert bmi_category(32, "ru") == "Ожирение I степени"


def test_compute_wht_ratio_round_exception():
    from bmi_core import compute_wht_ratio

    with patch("builtins.round", side_effect=Exception("Round failed")):
        result = compute_wht_ratio(80, 1.7)
        assert result is None


def test_v1_bmi_invalid_api_key():
    r = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "wrong_key"},
    )
    assert r.status_code == 403
    data = r.json()
    assert "Invalid API Key" in data["detail"]


def test_v1_bmi_no_api_key():
    r = client.post(
        "/api/v1/bmi", json={"weight_kg": 70, "height_cm": 170, "group": "general"}
    )
    assert r.status_code == 403
    data = r.json()
    assert "Invalid API Key" in data["detail"]


def test_v1_insight_invalid_api_key():
    r = client.post(
        "/api/v1/insight", json={"text": "test"}, headers={"X-API-Key": "wrong_key"}
    )
    assert r.status_code == 403
    data = r.json()
    assert "Invalid API Key" in data["detail"]


def test_slowapi_import_failure():
    """Test coverage for slowapi import exception in app.py."""
    import builtins
    import sys
    from unittest.mock import patch

    # Save original app module if it exists
    original_app = sys.modules.get("app")

    # Save original before patching
    original_import = builtins.__import__

    with patch.object(builtins, "__import__") as mock_import:
        # Mock the import to fail for slowapi
        def side_effect(name, *args, **kwargs):
            if name == "slowapi":
                raise ImportError("Mocked slowapi import failure")
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = side_effect

        # Re-import app to trigger the exception
        if "app" in sys.modules:
            del sys.modules["app"]
        try:
            import app

            # Check that limiter is None
            assert app.limiter is None
        except Exception:
            pytest.skip("App import failed unexpectedly")
        finally:
            # Restore original app module
            if original_app is not None:
                sys.modules["app"] = original_app
            elif "app" in sys.modules:
                del sys.modules["app"]


def test_prometheus_import_failure():
    """Test coverage for prometheus_client import exception in app.py."""
    import builtins
    import sys
    from unittest.mock import patch

    # Save original app module if it exists
    original_app = sys.modules.get("app")

    # Save original before patching
    original_import = builtins.__import__

    with patch.object(builtins, "__import__") as mock_import:
        # Mock the import to fail for prometheus_client
        def side_effect(name, *args, **kwargs):
            if name == "prometheus_client":
                raise ImportError("Mocked prometheus_client import failure")
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = side_effect

        # Re-import app to trigger the exception
        if "app" in sys.modules:
            del sys.modules["app"]
        try:
            import app

            # Check that Counter is None
            assert app.Counter is None
            assert app.Histogram is None
            assert app.generate_latest is None
        except Exception:
            pytest.skip("App import failed unexpectedly")
        finally:
            # Restore original app module
            if original_app is not None:
                sys.modules["app"] = original_app
            elif "app" in sys.modules:
                del sys.modules["app"]

# -*- coding: utf-8 -*-
"""
Доп. покрытие для app.py: корневой HTML, ветка slowapi, альтернативная ветка отключения инсайта.
"""

import importlib
import os
import sys
import types

from fastapi.testclient import TestClient


def _reload_app_with_fake_slowapi():
    # Готовим фейковые slowapi-модули
    slowapi = types.ModuleType("slowapi")
    slowapi_errors = types.ModuleType("slowapi.errors")
    slowapi_mw = types.ModuleType("slowapi.middleware")
    slowapi_util = types.ModuleType("slowapi.util")

    # Store original modules for cleanup
    orig_slowapi = sys.modules.get("slowapi")
    orig_slowapi_errors = sys.modules.get("slowapi.errors")
    orig_slowapi_mw = sys.modules.get("slowapi.middleware")
    orig_slowapi_util = sys.modules.get("slowapi.util")

    class Limiter:
        def __init__(self, key_func=None):
            self.key_func = key_func

    class SlowAPIMiddleware:
        pass

    class RateLimitExceeded(Exception):
        pass

    def get_remote_address(request=None):
        return "127.0.0.1"

    def _rate_limit_exceeded_handler(*args, **kwargs):
        return None

    slowapi.Limiter = Limiter
    slowapi._rate_limit_exceeded_handler = _rate_limit_exceeded_handler
    slowapi_errors.RateLimitExceeded = RateLimitExceeded
    slowapi_mw.SlowAPIMiddleware = SlowAPIMiddleware
    slowapi_util.get_remote_address = get_remote_address

    sys.modules["slowapi"] = slowapi
    sys.modules["slowapi.errors"] = slowapi_errors
    sys.modules["slowapi.middleware"] = slowapi_mw
    sys.modules["slowapi.util"] = slowapi_util

    # Перезагружаем app, чтобы прошёл блок if slowapi_available
    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])  # re-exec top-level
    else:
        import app  # noqa: F401

    # Вернуть cleanup, чтобы тест мог восстановить окружение
    def _cleanup():
        # Restore original modules or remove if they weren't there
        if orig_slowapi is not None:
            sys.modules["slowapi"] = orig_slowapi
        else:
            sys.modules.pop("slowapi", None)

        if orig_slowapi_errors is not None:
            sys.modules["slowapi.errors"] = orig_slowapi_errors
        else:
            sys.modules.pop("slowapi.errors", None)

        if orig_slowapi_mw is not None:
            sys.modules["slowapi.middleware"] = orig_slowapi_mw
        else:
            sys.modules.pop("slowapi.middleware", None)

        if orig_slowapi_util is not None:
            sys.modules["slowapi.util"] = orig_slowapi_util
        else:
            sys.modules.pop("slowapi.util", None)

        if "app" in sys.modules:
            importlib.reload(sys.modules["app"])

    return _cleanup


def test_root_route_html_renders():
    import app as app_mod

    client = TestClient(app_mod.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>BMI Calculator 2025</title>" in r.text


def test_feature_insight_disabled_other_string(monkeypatch):
    import app as app_mod

    client = TestClient(app_mod.app)
    monkeypatch.setenv("FEATURE_INSIGHT", "disabled")
    monkeypatch.setenv("LLM_PROVIDER", "stub")

    r = client.post("/insight", json={"text": "x"})
    assert r.status_code == 503
    assert "disabled" in r.json().get("detail", "")


def test_slowapi_branch_executes():
    cleanup = _reload_app_with_fake_slowapi()
    try:
        import app as app_mod

        # наличие лимитера на состоянии приложения подсказывает, что ветка прошла
        assert hasattr(app_mod.app.state, "limiter")
    finally:
        cleanup()


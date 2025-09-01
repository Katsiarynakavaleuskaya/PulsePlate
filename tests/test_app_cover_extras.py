# -*- coding: utf-8 -*-
"""
Доп. покрытие для app.py: корневой HTML, ветка slowapi, альтернативная ветка отключения инсайта.
"""

import types
import importlib
import os
import sys

from fastapi.testclient import TestClient


def _reload_app_with_fake_slowapi():
    # Готовим фейковые slowapi-модули
    slowapi = types.ModuleType("slowapi")
    slowapi_errors = types.ModuleType("slowapi.errors")
    slowapi_mw = types.ModuleType("slowapi.middleware")
    slowapi_util = types.ModuleType("slowapi.util")

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


def test_root_route_html_renders():
    import app as app_mod

    client = TestClient(app_mod.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>BMI Calculator 2025</title>" in r.text


def test_feature_insight_disabled_other_string():
    import app as app_mod

    client = TestClient(app_mod.app)
    original = os.environ.get("FEATURE_INSIGHT")
    original_provider = os.environ.get("LLM_PROVIDER")
    os.environ["FEATURE_INSIGHT"] = "disabled"
    os.environ["LLM_PROVIDER"] = "stub"
    try:
        r = client.post("/insight", json={"text": "x"})
        assert r.status_code == 503
        assert "disabled" in r.json().get("detail", "")
    finally:
        if original is not None:
            os.environ["FEATURE_INSIGHT"] = original
        else:
            os.environ.pop("FEATURE_INSIGHT", None)
        if original_provider is not None:
            os.environ["LLM_PROVIDER"] = original_provider
        else:
            os.environ.pop("LLM_PROVIDER", None)


def test_slowapi_branch_executes():
    _reload_app_with_fake_slowapi()
    import app as app_mod

    # наличие лимитера на состоянии приложения подсказывает, что ветка прошла
    assert hasattr(app_mod.app.state, "limiter")


"""
Ensure app starts without crashing when VIP_MODULE_ENABLED=true but VIP router import fails.

Checks that VIP routes are not registered while other routes remain available.
"""

import importlib
import os
import sys
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def env_set(key: str, value: str):
    old = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


def test_app_vip_import_failure_graceful_degrade():
    """Simulate ImportError for app.routers.vip with flag enabled and assert no VIP routes."""

    # Patch builtins.__import__ to fail only on VIP router import
    orig_builtin_import = __import__

    def import_side_effect(name, globals=None, locals=None, fromlist=(), level=0):
        # Intercept direct 'from app.routers.vip import router' as well as package import
        if name == "app.routers.vip" or (name == "app.routers" and fromlist and "vip" in fromlist):
            raise ImportError("Simulated VIP import failure")
        return orig_builtin_import(name, globals, locals, fromlist, level)

    with env_set("VIP_MODULE_ENABLED", "true"):
        with patch("builtins.__import__", side_effect=import_side_effect):
            # Force a clean import of the app module
            sys.modules.pop("app", None)
            app_mod = importlib.import_module("app")
            fastapi_app = getattr(app_mod, "app")

            # The app should be created and standard routes present
            paths = {getattr(r, "path", getattr(r, "path_format", "")) for r in fastapi_app.routes}
            assert "/health" in paths or "/api/v1/health" in paths

            # VIP routes must not be present due to failed import
            assert not any(p.startswith("/api/v1/vip") for p in paths)

    # Cleanup: reload app normally to not affect other tests
    sys.modules.pop("app", None)
    importlib.import_module("app")

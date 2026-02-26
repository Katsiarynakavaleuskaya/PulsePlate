"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from __future__ import annotations

from fastapi import FastAPI

from legacy_app import (
    _install_openapi_builder,
    app as _legacy_app,
)  # re-export FastAPI instance from legacy root module

# Register observability infrastructure (middleware + /metrics endpoint)
# This must be done here, not in legacy_app.py, to keep legacy as a thin proxy
from app.bootstrap.metrics import register_metrics
from app.bootstrap.pro_contracts import register_pro_contract_routes
import app.routers.realtime_ws as realtime_ws

app: FastAPI = _legacy_app

_install_openapi_builder(app)
register_metrics(app)
register_pro_contract_routes(app)


def _assert_no_duplicate_ws_route() -> None:
    """Fail fast if /ws or /api/v1/pro/ws is already registered elsewhere."""
    existing_paths = {getattr(route, "path", None) for route in app.routes}
    # Check for duplicate canonical PRO WS path
    if "/api/v1/pro/ws" in existing_paths:
        raise RuntimeError(
            "Duplicate /api/v1/pro/ws route detected. "
            "Check legacy_app.py or other router registration points."
        )
    # Check for duplicate legacy WS path (will be registered by realtime_ws.router)
    if "/ws" in existing_paths:
        raise RuntimeError(
            "Duplicate /ws route detected. "
            "Check legacy_app.py or other router registration points."
        )


_assert_no_duplicate_ws_route()
app.include_router(realtime_ws.router)

__all__ = ["app"]

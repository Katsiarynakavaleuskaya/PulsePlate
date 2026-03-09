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
from app.routers.billing import register_billing_routes
from app.routers.cbt_insight import router as cbt_insight_router
from app.routers.feedback import router as feedback_router
from app.routers.fitchef_insight import router as fitchef_insight_router
from app.routers.legal import router as legal_router

app: FastAPI = _legacy_app


def _internalize_users_openapi_surface(target_app: FastAPI) -> None:
    """Hide legacy users CRUD from the public OpenAPI contract.

    RU: Скрываем users CRUD из публичной OpenAPI surface в canonical entrypoint,
    не добавляя новый runtime behavior в legacy compatibility layer.
    EN: Hide users CRUD from the public OpenAPI surface in the canonical
    entrypoint instead of introducing new runtime behavior in legacy_app.py.
    """

    for route in target_app.routes:
        if str(getattr(route, "path", "")).startswith("/api/v1/users"):
            setattr(route, "include_in_schema", False)

    if target_app.openapi_tags:
        target_app.openapi_tags = [
            tag for tag in target_app.openapi_tags if tag.get("name") != "users"
        ]

    if target_app.description:
        target_app.description = target_app.description.replace(", user management", "")
        target_app.description = target_app.description.replace(
            "User management endpoints (FREE tier)", ""
        )

    target_app.openapi_schema = None


_internalize_users_openapi_surface(app)
_install_openapi_builder(app)
register_metrics(app)
register_pro_contract_routes(app)


def _assert_no_duplicate_ws_route() -> None:
    """Fail fast if WS routes are already registered elsewhere."""
    existing_paths = {getattr(route, "path", None) for route in app.routes}
    ws_paths = ("/api/v1/pro/ws", "/ws")  # tuple for deterministic order
    for path in ws_paths:
        if path in existing_paths:
            raise RuntimeError(
                f"Duplicate {path} route detected. "
                "Check legacy_app.py or other router registration points."
            )


_assert_no_duplicate_ws_route()
app.include_router(realtime_ws.router)

# Register feedback router (new endpoint, not legacy — belongs here per policy)
app.include_router(feedback_router)

# Register legal publication router outside legacy compatibility layer.
app.include_router(legal_router)

# Register billing router (canonical additive runtime payment surface).
register_billing_routes(app)

# Register CBT insight router (PRO tier, feature-flagged via FEATURE_CBT_AGENT)
app.include_router(cbt_insight_router)

# Register FitChef mascot router (VIP tier, feature-flagged via FEATURE_FITCHEF_MASCOT)
app.include_router(fitchef_insight_router)

__all__ = ["app"]

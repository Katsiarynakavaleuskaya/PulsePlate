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
from app.bootstrap.telemetry import register_request_telemetry
from app.bootstrap.tracing import register_tracing
import app.routers.realtime_ws as realtime_ws
from app.routers.billing import register_billing_routes
from app.routers.cbt_insight import router as cbt_insight_router
from app.routers.feedback import router as feedback_router
from app.routers.legal import router as legal_router

app: FastAPI = _legacy_app

_WS_ROUTE_PATHS: tuple[str, str] = ("/api/v1/pro/ws", "/ws")
_FEEDBACK_ROUTE_PATH: str = "/api/v1/feedback/rag"
_TERMS_ROUTE_PATH: str = "/terms"
_CBT_INSIGHT_ROUTE_PATH: str = "/api/v1/pro/cbt/insight"


def _has_route(
    target_app: FastAPI,
    path: str,
    method: str | None = None,
) -> bool:
    """Check whether a route is already registered on the target app.

    RU: Помогает делать additive bootstrap идемпотентным для reload paths.
    EN: Keeps additive bootstrap idempotent for reload-path rehydration.
    """
    method_name = method.upper() if method else None
    for route in target_app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", None) or set()
        if method_name is None or method_name in methods:
            return True
    return False


def _assert_no_duplicate_ws_route(target_app: FastAPI | None = None) -> None:
    """Fail fast when WS paths are already occupied before canonical registration.

    RU: Отдельный guard сохраняет старый fail-fast контракт для tests/runtime.
    EN: Separate guard preserves the legacy fail-fast contract for tests/runtime.
    """
    current_app = target_app or app
    existing_paths = {getattr(route, "path", None) for route in current_app.routes}
    for path in _WS_ROUTE_PATHS:
        if path in existing_paths:
            raise RuntimeError(
                f"Duplicate {path} route detected. "
                "Check legacy_app.py or other router registration points."
            )


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


def ensure_canonical_app_bootstrap(target_app: FastAPI) -> FastAPI:
    """Apply canonical additive bootstrap to the provided FastAPI instance.

    RU: Используется и при первичном импорте `app.main`, и когда `app.app`
    должен перевести facade на новый `legacy_app.app` без потери additive routes.
    EN: Used both on initial `app.main` import and when `app.app` must rehydrate
    a replaced `legacy_app.app` without losing additive routes.
    """
    global app

    app = target_app
    _internalize_users_openapi_surface(app)
    _install_openapi_builder(app)
    register_metrics(app)
    register_request_telemetry(app)
    register_tracing(app)
    register_pro_contract_routes(app)

    ws_paths_present = {path for path in _WS_ROUTE_PATHS if _has_route(app, path)}
    if not ws_paths_present:
        app.include_router(realtime_ws.router)
    elif ws_paths_present != set(_WS_ROUTE_PATHS):
        _assert_no_duplicate_ws_route(app)

    if not _has_route(app, _FEEDBACK_ROUTE_PATH, "POST"):
        app.include_router(feedback_router)

    if not _has_route(app, _TERMS_ROUTE_PATH, "GET"):
        app.include_router(legal_router)

    register_billing_routes(app)

    if not _has_route(app, _CBT_INSIGHT_ROUTE_PATH, "POST"):
        app.include_router(cbt_insight_router)

    return app


ensure_canonical_app_bootstrap(app)

__all__ = ["app"]

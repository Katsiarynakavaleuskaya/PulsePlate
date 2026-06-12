"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from legacy_app import (
    _install_openapi_builder,
    app as _legacy_app,
)  # re-export FastAPI instance from legacy root module

# Register observability infrastructure (middleware + /metrics endpoint)
# This must be done here, not in legacy_app.py, to keep legacy as a thin proxy
from app.bootstrap.direct_api_root import (
    LEGACY_BMI_WEB_ROUTE,
    serve_direct_api_root_probe,
    serve_legacy_bmi_calculator_web,
)
from app.bootstrap.food_search import register_food_search_backend
from app.bootstrap.metrics import register_metrics
from app.bootstrap.pro_contracts import register_pro_contract_routes
from app.bootstrap.public_discovery import SITEMAP_ROUTE_PATH, serve_public_sitemap
from app.bootstrap.telemetry import register_request_telemetry
from app.bootstrap.tracing import register_tracing
from app.routers.creative_research_internal import router as creative_research_internal_router
from app.routers.paywall_analytics import ingest_paywall_event, router as paywall_analytics_router
import app.routers.realtime_ws as realtime_ws
from app.routers.billing import register_billing_routes
from app.routers.cbt_insight import router as cbt_insight_router
from app.routers.feedback import router as feedback_router
from app.routers.fitchef_structured import router as fitchef_structured_router
from app.routers.health import router as health_router
from app.routers.legal import router as legal_router
from app.routers.vip_registration import register_vip_routes
from app.schemas.direct_api_root import DirectApiRootProbe

app: FastAPI = _legacy_app

_WS_ROUTE_PATHS: tuple[str, str] = ("/api/v1/pro/ws", "/ws")
_FEEDBACK_ROUTE_PATH: str = "/api/v1/feedback/rag"
_PRIVACY_ROUTE_PATH: str = "/privacy"
_TERMS_ROUTE_PATH: str = "/terms"
_LEGAL_ROUTE_PATHS: tuple[str, str] = (_PRIVACY_ROUTE_PATH, _TERMS_ROUTE_PATH)
_HEALTH_ROUTE_PATH: str = "/health"
_HEALTH_V1_ROUTE_PATH: str = "/api/v1/health"
_HEALTH_DB_ROUTE_PATH: str = "/health/db"
_READY_ROUTE_PATH: str = "/ready"
_HEALTH_ROUTE_PATHS: tuple[str, str, str, str] = (
    _HEALTH_ROUTE_PATH,
    _HEALTH_V1_ROUTE_PATH,
    _HEALTH_DB_ROUTE_PATH,
    _READY_ROUTE_PATH,
)
_CBT_INSIGHT_ROUTE_PATH: str = "/api/v1/pro/cbt/insight"
_FITCHEF_STRUCTURED_ROUTE_PATH: str = "/api/v1/pro/fitchef/explain"
_CREATIVE_RESEARCH_PILOT_ROUTE_PATH: str = "/api/v1/internal/creative-research/pilot"
_PAYWALL_EVENTS_ROUTE_PATH: str = "/api/v1/internal/paywall/events"


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


def _route_has_endpoint(
    target_app: FastAPI,
    path: str,
    method: str,
    endpoint: object,
) -> bool:
    """True when ``path``+``method`` is already bound to the expected callable.

    RU: Не считаем «маршрут есть», если на пути висит чужой handler (контракт другой).
    EN: Path/method alone is insufficient — wrong handler means wrong contract.
    """
    method_name = method.upper()
    for route in target_app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", None) or set()
        if method_name not in methods:
            continue
        if getattr(route, "endpoint", None) is endpoint:
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


def _include_legal_router_if_needed(target_app: FastAPI) -> None:
    """Register legal publication routes as one atomic route family."""

    expected_paths = set(_LEGAL_ROUTE_PATHS)
    expected_endpoints: dict[str, object] = {}
    expected_route_counts = dict.fromkeys(expected_paths, 0)
    for route in legal_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path in expected_paths and "GET" in methods:
            expected_route_counts[str(path)] += 1
            expected_endpoints[str(path)] = getattr(route, "endpoint", None)

    if set(expected_endpoints) != expected_paths or any(
        count != 1 for count in expected_route_counts.values()
    ):
        raise RuntimeError("Legal router does not define the expected route family.")

    legal_paths_present = {path for path in expected_paths if _has_route(target_app, path, "GET")}

    if not legal_paths_present:
        target_app.include_router(legal_router)
        return

    if legal_paths_present != expected_paths:
        existing = ", ".join(sorted(legal_paths_present))
        missing = ", ".join(sorted(expected_paths - legal_paths_present))
        raise RuntimeError(
            "Partial legal route registration detected. "
            f"Existing: {existing or '<none>'}; missing: {missing or '<none>'}."
        )

    for path, endpoint in expected_endpoints.items():
        matching_routes = [
            route
            for route in target_app.routes
            if getattr(route, "path", None) == path
            and "GET" in (getattr(route, "methods", None) or set())
        ]
        if (
            len(matching_routes) != 1
            or getattr(matching_routes[0], "endpoint", None) is not endpoint
        ):
            raise RuntimeError(f"Duplicate {path} route detected with a different legal handler.")


def _include_health_router_if_needed(target_app: FastAPI) -> None:
    """Register health/readiness routes as one atomic route family."""

    expected_paths = set(_HEALTH_ROUTE_PATHS)
    expected_endpoints: dict[str, object] = {}
    expected_route_counts = dict.fromkeys(expected_paths, 0)
    for route in health_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path in expected_paths and "GET" in methods:
            expected_route_counts[str(path)] += 1
            expected_endpoints[str(path)] = getattr(route, "endpoint", None)
            if getattr(route, "include_in_schema", True):
                raise RuntimeError("Health router does not preserve hidden OpenAPI visibility.")

    if set(expected_endpoints) != expected_paths or any(
        count != 1 for count in expected_route_counts.values()
    ):
        raise RuntimeError("Health router does not define the expected route family.")

    health_paths_present = {path for path in expected_paths if _has_route(target_app, path, "GET")}

    if not health_paths_present:
        target_app.include_router(health_router)
        return

    if health_paths_present != expected_paths:
        existing = ", ".join(sorted(health_paths_present))
        missing = ", ".join(sorted(expected_paths - health_paths_present))
        raise RuntimeError(
            "Partial health route registration detected. "
            f"Existing: {existing or '<none>'}; missing: {missing or '<none>'}."
        )

    for path, endpoint in expected_endpoints.items():
        matching_routes = [
            route
            for route in target_app.routes
            if getattr(route, "path", None) == path
            and "GET" in (getattr(route, "methods", None) or set())
        ]
        if (
            len(matching_routes) != 1
            or getattr(matching_routes[0], "endpoint", None) is not endpoint
        ):
            raise RuntimeError(f"Duplicate {path} route detected with a different health handler.")


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

    if not _route_has_endpoint(target_app, "/", "GET", serve_direct_api_root_probe):
        target_app.add_api_route(
            "/",
            serve_direct_api_root_probe,
            methods=["GET"],
            include_in_schema=False,
            response_model=DirectApiRootProbe,
        )
    if not _route_has_endpoint(
        target_app, LEGACY_BMI_WEB_ROUTE, "GET", serve_legacy_bmi_calculator_web
    ):
        target_app.add_api_route(
            LEGACY_BMI_WEB_ROUTE,
            serve_legacy_bmi_calculator_web,
            methods=["GET"],
            include_in_schema=False,
            response_class=HTMLResponse,
        )
    if not _route_has_endpoint(target_app, SITEMAP_ROUTE_PATH, "GET", serve_public_sitemap):
        target_app.add_api_route(
            SITEMAP_ROUTE_PATH,
            serve_public_sitemap,
            methods=["GET"],
            include_in_schema=False,
        )
    register_food_search_backend(app)
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

    _include_health_router_if_needed(app)
    _include_legal_router_if_needed(app)

    register_billing_routes(app)

    if not _has_route(app, _CBT_INSIGHT_ROUTE_PATH, "POST"):
        app.include_router(cbt_insight_router)

    if not _has_route(app, _FITCHEF_STRUCTURED_ROUTE_PATH, "POST"):
        app.include_router(fitchef_structured_router)

    register_vip_routes(target_app)

    if not _has_route(app, _CREATIVE_RESEARCH_PILOT_ROUTE_PATH, "POST"):
        app.include_router(creative_research_internal_router)

    if not _route_has_endpoint(
        app,
        _PAYWALL_EVENTS_ROUTE_PATH,
        "POST",
        ingest_paywall_event,
    ):
        if _has_route(app, _PAYWALL_EVENTS_ROUTE_PATH, "POST"):
            raise RuntimeError(
                "Duplicate /api/v1/internal/paywall/events route detected with a different "
                "handler."
            )
        app.include_router(paywall_analytics_router)

    return app


ensure_canonical_app_bootstrap(app)

__all__ = ["app"]

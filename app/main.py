"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Callable, cast

import legacy_app as _legacy_module
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute, APIWebSocketRoute
from settings import get_runtime_env_name

from app.bootstrap.application import app

# Register observability infrastructure (middleware + /metrics endpoint)
# This must be done here, not in legacy_app.py, to keep legacy as a thin proxy
from app.bootstrap.direct_api_root import (
    LEGACY_BMI_WEB_ROUTE,
    serve_direct_api_root_probe,
    serve_legacy_bmi_calculator_web,
)
from app.bootstrap.http_stack import register_http_middleware_stack
from app.bootstrap.lifespan import application_lifespan
from app.bootstrap.openapi import (
    apply_public_openapi_input_policy,
    install_canonical_openapi_builder,
    validate_openapi_builder_state,
)
from app.bootstrap.pro_contracts import register_pro_contract_routes
from app.bootstrap.public_discovery import SITEMAP_ROUTE_PATH, serve_public_sitemap
from app.effective_routes import (
    iter_effective_route_candidates,
    route_endpoint,
    route_endpoint_for_path_method,
    route_include_in_schema,
    route_methods,
    route_path,
)
from app.bootstrap.route_family import RouteMemberContract, ensure_route_family_registered
from app.middleware.api_tiers import get_current_user, require_pro_tier, require_vip_tier
from app.routers.creative_research_internal import router as creative_research_internal_router
from app.routers.paywall_analytics import router as paywall_analytics_router
import app.routers.realtime_ws as realtime_ws
from app.routers.admin_operations import (
    ADMIN_OPERATION_ROUTE_SPECS,
    router as admin_operations_router,
)
from app.routers.api_key import _get_api_key_dynamic, require_app_api_key
from app.routers.bayes_adherence import (
    BAYES_ADHERENCE_ROUTE_SPECS,
    router as bayes_adherence_router,
)
from app.routers.bodyfat import BODYFAT_ROUTE_SPECS, router as bodyfat_router
from app.routers.business import BUSINESS_ROUTE_SPECS, router as business_router
from app.routers.bmi_compat import BMI_COMPAT_ROUTE_SPECS, router as bmi_compat_router
from app.routers.bmi_registration import BmiRouteRegistration, register_bmi_routes
from app.routers.billing import register_billing_routes
from app.routers.catalog import (
    CATALOG_ROUTE_SPECS,
    get_catalog_service,
    router as catalog_router,
)
from app.routers.cbt_insight import router as cbt_insight_router
from app.routers.feedback import router as feedback_router
from app.routers.fitchef_structured import router as fitchef_structured_router
from app.routers.favicon import FAVICON_ROUTE_PATH, router as favicon_router
from app.routers.foods import FOODS_ROUTE_SPECS, get_food_store, router as foods_router
from app.routers.health import router as health_router
from app.routers.legal import router as legal_router
from app.routers.legacy_nutrition_alias import (
    LEGACY_NUTRITION_ALIAS_ROUTE_SPECS,
    router as legacy_nutrition_alias_router,
)
from app.routers.legacy_premium_nutrition import (
    LEGACY_PREMIUM_NUTRITION_ROUTE_SPECS,
    router as legacy_premium_nutrition_router,
)
from app.routers.legacy_insight import (
    LEGACY_INSIGHT_ROUTE_SPECS,
    router as legacy_insight_router,
)
from app.routers.legacy_premium_weekly_plan import (
    LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS,
    router as legacy_premium_weekly_plan_router,
)
from app.routers.nutrition_recommendations import (
    NUTRITION_RECOMMENDATIONS_ROUTE_SPECS,
    router as nutrition_recommendations_router,
)
from app.routers.nutrition_log import NUTRITION_LOG_ROUTE_SPECS, router as nutrition_log_router
from app.routers.plan_export import (
    PLAN_EXPORT_ROUTE_SPECS,
    WEEK_EXPORT_CSV_PATH,
    WEEK_EXPORT_PDF_PATH,
    _require_valid_token,
    export_router,
    plan_router,
)
from app.routers.pro_registration import register_pro_routes
from app.routers.recipes import RECIPES_ROUTE_SPECS, router as recipes_router
from app.routers.restaurants import (
    RESTAURANT_MODERATION_ROUTE_SPECS,
    RESTAURANT_ROUTE_SPECS,
    get_restaurant_store,
    moderation_router as restaurant_moderation_router,
    router as restaurants_router,
)
from app.routers.shoplist_day import SHOPLIST_DAY_ROUTE_SPECS, router as shoplist_day_router
from app.routers.shoplist_export import router as shoplist_export_router
from app.routers.shoplist_export_routes import SHOPLIST_ROUTE_SPECS
from app.routers.shopping_list_pro import (
    SHOPPING_LIST_PRO_ROUTE_SPECS,
    router as shopping_list_pro_router,
)
from app.routers.test import (
    TEST_ROUTE_SPECS,
    _ensure_non_production as ensure_test_routes_non_production,
    router as test_router,
)
from app.routers.users import (
    USERS_ROUTE_SPECS,
    _require_users_api_key,
    router as users_router,
)
from app.routers.vip_registration import register_vip_routes
from app.schemas.direct_api_root import DirectApiRootProbe
from app.utils.feature_flags import is_business_module_enabled, is_vip_module_enabled

logger = logging.getLogger(__name__)

VIP_MODULE_ENABLED: bool = False
vip_router: APIRouter | None = None
pro_router: APIRouter | None = None
premium_week_router: APIRouter | None = None
FEATURE_BMI_PRO_ENABLED: bool = False
bmi_router: APIRouter | None = None
bmi_pro_router: APIRouter | None = None
bmi_pro_legacy_alias_router: APIRouter | None = None

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
_ADMIN_OPERATION_ROUTE_SPECS: tuple[tuple[str, str], ...] = tuple(
    (path, method.upper()) for path, method in ADMIN_OPERATION_ROUTE_SPECS
)
_BAYES_ADHERENCE_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in BAYES_ADHERENCE_ROUTE_SPECS
)
_BMI_COMPAT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in BMI_COMPAT_ROUTE_SPECS
)
_BODYFAT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in BODYFAT_ROUTE_SPECS
)
_LEGACY_PREMIUM_NUTRITION_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in LEGACY_PREMIUM_NUTRITION_ROUTE_SPECS
)
_LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS
)
_LEGACY_INSIGHT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in LEGACY_INSIGHT_ROUTE_SPECS
)
_BUSINESS_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in BUSINESS_ROUTE_SPECS
)
_CATALOG_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in CATALOG_ROUTE_SPECS
)
_FOODS_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in FOODS_ROUTE_SPECS
)
_TEST_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in TEST_ROUTE_SPECS
)
_LEGACY_NUTRITION_ALIAS_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in LEGACY_NUTRITION_ALIAS_ROUTE_SPECS
)
_NUTRITION_LOG_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in NUTRITION_LOG_ROUTE_SPECS
)
_NUTRITION_RECOMMENDATIONS_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in NUTRITION_RECOMMENDATIONS_ROUTE_SPECS
)
_PLAN_EXPORT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in PLAN_EXPORT_ROUTE_SPECS
)
_RECIPES_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in RECIPES_ROUTE_SPECS
)
_SHOPLIST_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in SHOPLIST_ROUTE_SPECS
)
_SHOPLIST_DAY_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in SHOPLIST_DAY_ROUTE_SPECS
)
_SHOPPING_LIST_PRO_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in SHOPPING_LIST_PRO_ROUTE_SPECS
)
_RESTAURANT_MODERATION_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in RESTAURANT_MODERATION_ROUTE_SPECS
)
_RESTAURANT_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = tuple(
    (path, method.upper(), include_in_schema)
    for path, method, include_in_schema in RESTAURANT_ROUTE_SPECS
)
_USERS_ROUTE_SPECS = USERS_ROUTE_SPECS
_EXPORT_ROUTE_REQUIRED_STATUS_CODES = frozenset({429})
_RESTAURANT_MODERATION_REQUIRED_STATUS_CODES = frozenset({404, 422})
_RESTAURANT_MENU_REQUIRED_STATUS_CODES = frozenset({404})
_RESTAURANT_SUBMISSION_CREATE_REQUIRED_STATUS_CODES = frozenset({422})
_RESTAURANT_SUBMISSION_DETAIL_REQUIRED_STATUS_CODES = frozenset({404})
_PLAN_SIGNED_EXPORT_PATHS = frozenset({WEEK_EXPORT_CSV_PATH, WEEK_EXPORT_PDF_PATH})
_NO_REQUIRED_STATUS_CODES: frozenset[int] = frozenset()
_RESTAURANT_ROUTE_REQUIRED_STATUS_CODES: dict[tuple[str, str], frozenset[int]] = {
    ("/api/v1/restaurants/{chain_id}/menu", "GET"): _RESTAURANT_MENU_REQUIRED_STATUS_CODES,
    (
        "/api/v1/restaurants/submissions",
        "POST",
    ): _RESTAURANT_SUBMISSION_CREATE_REQUIRED_STATUS_CODES,
    (
        "/api/v1/restaurants/submissions/{submission_id}",
        "GET",
    ): _RESTAURANT_SUBMISSION_DETAIL_REQUIRED_STATUS_CODES,
}
_FOODS_BARCODE_REQUIRED_STATUS_CODES = frozenset({404, 422})


def _require_canonical_api_key_dependency(family_name: str) -> Callable[..., object]:
    dependency = _get_api_key_dynamic
    if not callable(dependency):
        raise RuntimeError(f"{family_name} API key dependency is unavailable.")
    return cast(Callable[..., object], dependency)


def _plan_export_route_members(
    api_key_dependency: Callable[..., object],
) -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_status_codes=_EXPORT_ROUTE_REQUIRED_STATUS_CODES,
            required_dependencies=(
                (api_key_dependency, _require_valid_token)
                if path in _PLAN_SIGNED_EXPORT_PATHS
                else (api_key_dependency,)
            ),
        )
        for path, method, include_in_schema in _PLAN_EXPORT_ROUTE_SPECS
    )


def _shoplist_export_route_members(
    api_key_dependency: Callable[..., object],
) -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_status_codes=_EXPORT_ROUTE_REQUIRED_STATUS_CODES,
            required_dependencies=(api_key_dependency,),
        )
        for path, method, include_in_schema in _SHOPLIST_ROUTE_SPECS
    )


def _shopping_list_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_dependencies=(require_pro_tier,),
        )
        for path, method, include_in_schema in (
            *_SHOPPING_LIST_PRO_ROUTE_SPECS,
            *_SHOPLIST_DAY_ROUTE_SPECS,
        )
    )


def _restaurant_moderation_route_members(
    api_key_dependency: Callable[..., object],
) -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_status_codes=_RESTAURANT_MODERATION_REQUIRED_STATUS_CODES,
            required_dependencies=(api_key_dependency,),
        )
        for path, method, include_in_schema in _RESTAURANT_MODERATION_ROUTE_SPECS
    )


def _restaurant_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_status_codes=_RESTAURANT_ROUTE_REQUIRED_STATUS_CODES.get(
                (path, method),
                _NO_REQUIRED_STATUS_CODES,
            ),
            required_dependencies=(get_restaurant_store,),
        )
        for path, method, include_in_schema in _RESTAURANT_ROUTE_SPECS
    )


def _nutrition_state_route_members() -> tuple[RouteMemberContract, ...]:
    stateful_dependencies = (require_pro_tier, get_current_user)
    alias_dependencies = (require_pro_tier,)
    members: list[RouteMemberContract] = []

    for path, method, include_in_schema in (
        *_BAYES_ADHERENCE_ROUTE_SPECS,
        *_NUTRITION_LOG_ROUTE_SPECS,
    ):
        members.append(
            RouteMemberContract(
                path=path,
                method=method,
                include_in_schema=include_in_schema,
                required_dependencies=stateful_dependencies,
            )
        )

    for path, method, include_in_schema in _LEGACY_NUTRITION_ALIAS_ROUTE_SPECS:
        members.append(
            RouteMemberContract(
                path=path,
                method=method,
                include_in_schema=include_in_schema,
                required_dependencies=alias_dependencies,
            )
        )

    return tuple(members)


def _bodyfat_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
        )
        for path, method, include_in_schema in _BODYFAT_ROUTE_SPECS
    )


def _legacy_premium_nutrition_route_members(
    api_key_dependency: Callable[..., object],
) -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_dependencies=() if path == "/premium_bmr" else (api_key_dependency,),
        )
        for path, method, include_in_schema in _LEGACY_PREMIUM_NUTRITION_ROUTE_SPECS
    )


def _legacy_premium_weekly_plan_route_members(
    api_key_dependency: Callable[..., object],
) -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_dependencies=(api_key_dependency,),
        )
        for path, method, include_in_schema in _LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS
    )


def _legacy_insight_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_status_codes=frozenset({429}),
            required_dependencies=(require_vip_tier,),
        )
        for path, method, include_in_schema in _LEGACY_INSIGHT_ROUTE_SPECS
    )


def _business_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_dependencies=(require_app_api_key,) if path.endswith("/analyze") else (),
        )
        for path, method, include_in_schema in _BUSINESS_ROUTE_SPECS
    )


def _food_catalog_route_members() -> tuple[RouteMemberContract, ...]:
    members: list[RouteMemberContract] = []
    for path, method, include_in_schema in _FOODS_ROUTE_SPECS:
        members.append(
            RouteMemberContract(
                path=path,
                method=method,
                include_in_schema=include_in_schema,
                required_status_codes=(
                    _FOODS_BARCODE_REQUIRED_STATUS_CODES
                    if path.endswith("/{barcode}")
                    else _NO_REQUIRED_STATUS_CODES
                ),
                required_dependencies=(get_food_store,),
            )
        )
    for path, method, include_in_schema in _CATALOG_ROUTE_SPECS:
        members.append(
            RouteMemberContract(
                path=path,
                method=method,
                include_in_schema=include_in_schema,
                required_dependencies=(get_catalog_service,),
            )
        )
    return tuple(members)


def _recipe_nutrition_reference_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
        )
        for path, method, include_in_schema in (
            *_RECIPES_ROUTE_SPECS,
            *_NUTRITION_RECOMMENDATIONS_ROUTE_SPECS,
        )
    )


def _users_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_dependencies=(_require_users_api_key,),
        )
        for path, method, include_in_schema in _USERS_ROUTE_SPECS
    )


def _test_route_members() -> tuple[RouteMemberContract, ...]:
    return tuple(
        RouteMemberContract(
            path=path,
            method=method,
            include_in_schema=include_in_schema,
            required_dependencies=(ensure_test_routes_non_production,),
        )
        for path, method, include_in_schema in _TEST_ROUTE_SPECS
    )


def _test_routes_enabled_for_registration() -> bool:
    env = get_runtime_env_name()
    return env in {"local", "dev", "development", "test", "testing", "ci"} or (
        env == "staging" and os.getenv("ENABLE_TEST_ROUTES") == "1"
    )


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
    for route in _effective_app_routes(target_app):
        if route_path(route) != path:
            continue
        methods = route_methods(route)
        if method_name is None or method_name in methods:
            return True
    return False


def _effective_app_routes(target_app: FastAPI) -> tuple[object, ...]:
    return tuple(iter_effective_route_candidates(target_app.routes))


def _route_has_endpoint(
    target_app: FastAPI,
    path: str,
    method: str,
    endpoint: object,
) -> bool:
    """True when ``path``+``method`` is already bound to the expected callable.

    An empty method checks path ownership for the websocket family.
    RU: Не считаем «маршрут есть», если на пути висит чужой handler (контракт другой).
    EN: Path/method alone is insufficient — wrong handler means wrong contract.
    """
    method_name = method.upper()
    carrier = APIRoute if method_name else APIWebSocketRoute
    owners: list[object | None] = []
    for route in _effective_app_routes(target_app):
        carrier_route = getattr(route, "original_route", route)
        if route_path(route) != path:
            continue
        if method_name and method_name not in route_methods(carrier_route):
            continue
        owners.append(route_endpoint(carrier_route) if isinstance(carrier_route, carrier) else None)
    if endpoint is not None and len(owners) == 1 and owners[0] is endpoint:
        return True
    if endpoint is not None and not owners:
        return False
    raise RuntimeError(f"Duplicate {path} route detected with a different or repeated owner.")


def _assert_no_duplicate_ws_route(target_app: FastAPI | None = None) -> None:
    """Fail fast when WS paths are already occupied before canonical registration.

    RU: Отдельный guard сохраняет старый fail-fast контракт для tests/runtime.
    EN: Separate guard preserves the legacy fail-fast contract for tests/runtime.
    """
    current_app = target_app or app
    existing_paths = {route_path(route) for route in _effective_app_routes(current_app)}
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
            for route in _effective_app_routes(target_app)
            if route_path(route) == path and "GET" in route_methods(route)
        ]
        if len(matching_routes) != 1 or route_endpoint(matching_routes[0]) is not endpoint:
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
            for route in _effective_app_routes(target_app)
            if route_path(route) == path and "GET" in route_methods(route)
        ]
        if len(matching_routes) != 1 or route_endpoint(matching_routes[0]) is not endpoint:
            raise RuntimeError(f"Duplicate {path} route detected with a different health handler.")
        if route_include_in_schema(matching_routes[0]):
            raise RuntimeError(
                f"Existing {path} route does not preserve hidden OpenAPI visibility."
            )


def _include_favicon_router_if_needed(target_app: FastAPI) -> None:
    """Register the runtime-only favicon endpoint once."""

    expected_endpoint: object | None = None
    expected_route_count = 0
    for route in favicon_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path == FAVICON_ROUTE_PATH and "GET" in methods:
            expected_route_count += 1
            expected_endpoint = getattr(route, "endpoint", None)
            if getattr(route, "include_in_schema", True):
                raise RuntimeError("Favicon router does not preserve hidden OpenAPI visibility.")

    if expected_route_count != 1 or expected_endpoint is None:
        raise RuntimeError("Favicon router does not define the expected route.")

    favicon_routes = [
        route
        for route in _effective_app_routes(target_app)
        if route_path(route) == FAVICON_ROUTE_PATH
    ]
    if not favicon_routes:
        target_app.include_router(favicon_router)
        return

    matching_routes = [route for route in favicon_routes if "GET" in route_methods(route)]
    if not matching_routes:
        raise RuntimeError("Partial favicon route registration detected.")

    if (
        len(favicon_routes) != 1
        or len(matching_routes) != 1
        or route_endpoint(matching_routes[0]) is not expected_endpoint
    ):
        raise RuntimeError(
            "Duplicate /favicon.ico route detected with a different favicon handler."
        )

    if route_include_in_schema(matching_routes[0]):
        raise RuntimeError(
            "Existing /favicon.ico route does not preserve hidden OpenAPI visibility."
        )


def _include_admin_operations_router_if_needed(target_app: FastAPI) -> None:
    """Register admin/debug operational routes as one hidden atomic family."""

    expected_specs = set(_ADMIN_OPERATION_ROUTE_SPECS)
    expected_paths = {path for path, _method in expected_specs}
    expected_methods_by_path = {path: method for path, method in expected_specs}
    expected_endpoints: dict[tuple[str, str], object] = {}
    expected_route_counts: dict[tuple[str, str], int] = {spec: 0 for spec in expected_specs}

    for route in admin_operations_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path not in expected_paths:
            continue
        expected_method = expected_methods_by_path[str(path)]
        if expected_method not in methods:
            raise RuntimeError("Admin operations router does not define the expected route family.")
        unexpected_methods = set(methods) - {expected_method, "HEAD", "OPTIONS"}
        if unexpected_methods:
            raise RuntimeError("Admin operations router does not define the expected route family.")
        expected_route_counts[(str(path), expected_method)] += 1
        expected_endpoints[(str(path), expected_method)] = getattr(route, "endpoint", None)
        if getattr(route, "include_in_schema", True):
            raise RuntimeError(
                "Admin operations router does not preserve hidden OpenAPI visibility."
            )

    if set(expected_endpoints) != expected_specs or any(
        count != 1 for count in expected_route_counts.values()
    ):
        raise RuntimeError("Admin operations router does not define the expected route family.")

    admin_routes = [
        route for route in _effective_app_routes(target_app) if route_path(route) in expected_paths
    ]
    if not admin_routes:
        target_app.include_router(admin_operations_router)
        return

    admin_paths_present = {
        route_path(route)
        for route in admin_routes
        if expected_methods_by_path[route_path(route)] in route_methods(route)
    }
    if admin_paths_present != expected_paths:
        existing = ", ".join(sorted(admin_paths_present))
        missing = ", ".join(sorted(expected_paths - admin_paths_present))
        raise RuntimeError(
            "Partial admin operations route registration detected. "
            f"Existing: {existing or '<none>'}; missing: {missing or '<none>'}."
        )

    for registered_route in admin_routes:
        path = route_path(registered_route)
        methods = route_methods(registered_route)
        expected_method = expected_methods_by_path[path]
        if expected_method not in methods:
            raise RuntimeError("Partial admin operations route registration detected.")
        unexpected_methods = set(methods) - {expected_method, "HEAD", "OPTIONS"}
        if unexpected_methods:
            raise RuntimeError("Partial admin operations route registration detected.")

    for (path, method), endpoint in expected_endpoints.items():
        matching_routes = [
            route
            for route in _effective_app_routes(target_app)
            if route_path(route) == path and method in route_methods(route)
        ]
        if len(matching_routes) != 1 or route_endpoint(matching_routes[0]) is not endpoint:
            raise RuntimeError(
                f"Duplicate {path} route detected with a different admin operations handler."
            )
        if route_include_in_schema(matching_routes[0]):
            raise RuntimeError(
                f"Existing {path} route does not preserve hidden OpenAPI visibility."
            )


def _include_bmi_compat_router_if_needed(target_app: FastAPI) -> None:
    """Register BMI compatibility routes as one atomic route family."""

    expected_specs = {(path, method) for path, method, _include in _BMI_COMPAT_ROUTE_SPECS}
    expected_paths = {path for path, _method in expected_specs}
    expected_methods_by_path = {path: method for path, method in expected_specs}
    expected_visibility = {
        (path, method): include_in_schema
        for path, method, include_in_schema in _BMI_COMPAT_ROUTE_SPECS
    }
    expected_endpoints: dict[tuple[str, str], object] = {}
    expected_route_counts: dict[tuple[str, str], int] = {spec: 0 for spec in expected_specs}

    for route in bmi_compat_router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path not in expected_paths:
            continue
        expected_method = expected_methods_by_path[str(path)]
        if expected_method not in methods:
            raise RuntimeError(
                "BMI compatibility router does not define the expected route family."
            )
        unexpected_methods = set(methods) - {expected_method, "HEAD", "OPTIONS"}
        if unexpected_methods:
            raise RuntimeError(
                "BMI compatibility router does not define the expected route family."
            )
        spec = (str(path), expected_method)
        expected_route_counts[spec] += 1
        expected_endpoints[spec] = getattr(route, "endpoint", None)
        if getattr(route, "include_in_schema", True) is not expected_visibility[spec]:
            raise RuntimeError("BMI compatibility router does not preserve OpenAPI visibility.")

    if set(expected_endpoints) != expected_specs or any(
        count != 1 for count in expected_route_counts.values()
    ):
        raise RuntimeError("BMI compatibility router does not define the expected route family.")

    bmi_compat_routes = [
        route for route in _effective_app_routes(target_app) if route_path(route) in expected_paths
    ]
    if not bmi_compat_routes:
        target_app.include_router(bmi_compat_router)
        return

    bmi_compat_paths_present = {
        route_path(route)
        for route in bmi_compat_routes
        if expected_methods_by_path[route_path(route)] in route_methods(route)
    }
    if bmi_compat_paths_present != expected_paths:
        existing = ", ".join(sorted(bmi_compat_paths_present))
        missing = ", ".join(sorted(expected_paths - bmi_compat_paths_present))
        raise RuntimeError(
            "Partial BMI compatibility route registration detected. "
            f"Existing: {existing or '<none>'}; missing: {missing or '<none>'}."
        )

    for registered_route in bmi_compat_routes:
        path = route_path(registered_route)
        methods = route_methods(registered_route)
        expected_method = expected_methods_by_path[path]
        if expected_method not in methods:
            raise RuntimeError("Partial BMI compatibility route registration detected.")
        unexpected_methods = set(methods) - {expected_method, "HEAD", "OPTIONS"}
        if unexpected_methods:
            raise RuntimeError("Partial BMI compatibility route registration detected.")

    for (path, method), endpoint in expected_endpoints.items():
        matching_routes = [
            route
            for route in _effective_app_routes(target_app)
            if route_path(route) == path and method in route_methods(route)
        ]
        if len(matching_routes) != 1 or route_endpoint(matching_routes[0]) is not endpoint:
            raise RuntimeError(
                f"Duplicate {path} route detected with a different BMI compatibility handler."
            )
        if route_include_in_schema(matching_routes[0]) is not expected_visibility[(path, method)]:
            raise RuntimeError(
                f"Existing {path} route does not preserve BMI compatibility OpenAPI visibility."
            )


def _include_plan_export_routers_if_needed(target_app: FastAPI) -> None:
    """Register canonical plan/export routes as one protected atomic family."""

    api_key_dependency = _require_canonical_api_key_dependency("Plan export")

    ensure_route_family_registered(
        target_app,
        family_name="Plan export",
        routers=(export_router, plan_router),
        members=_plan_export_route_members(api_key_dependency),
        registration_dependencies=(Depends(api_key_dependency),),
    )


def _include_shoplist_export_router_if_needed(target_app: FastAPI) -> None:
    """Register public shoplist export routes as one protected atomic family."""

    api_key_dependency = _require_canonical_api_key_dependency("Shoplist export")

    ensure_route_family_registered(
        target_app,
        family_name="Shoplist export",
        routers=(shoplist_export_router,),
        members=_shoplist_export_route_members(api_key_dependency),
        registration_dependencies=(Depends(api_key_dependency),),
    )


def _include_shopping_list_routers_if_needed(target_app: FastAPI) -> None:
    """Register paid shopping-list routes as one protected static family."""

    ensure_route_family_registered(
        target_app,
        family_name="Shopping list",
        routers=(shopping_list_pro_router, shoplist_day_router),
        members=_shopping_list_route_members(),
    )


def _include_nutrition_state_routers_if_needed(target_app: FastAPI) -> None:
    """Register nutrition/adherence state routes as one protected static family."""

    ensure_route_family_registered(
        target_app,
        family_name="Nutrition state",
        routers=(
            bayes_adherence_router,
            nutrition_log_router,
            legacy_nutrition_alias_router,
        ),
        members=_nutrition_state_route_members(),
    )


def _include_bodyfat_router_if_needed(target_app: FastAPI) -> None:
    """Register public bodyfat route as one canonical static family."""

    ensure_route_family_registered(
        target_app,
        family_name="Bodyfat",
        routers=(bodyfat_router,),
        members=_bodyfat_route_members(),
    )


def _include_legacy_premium_nutrition_router_if_needed(target_app: FastAPI) -> None:
    """Register legacy premium nutrition aliases as one exact compatibility family."""

    api_key_dependency = _require_canonical_api_key_dependency("Legacy premium nutrition")

    ensure_route_family_registered(
        target_app,
        family_name="Legacy premium nutrition",
        routers=(legacy_premium_nutrition_router,),
        members=_legacy_premium_nutrition_route_members(api_key_dependency),
    )


def _include_legacy_premium_weekly_plan_router_if_needed(target_app: FastAPI) -> None:
    """Register legacy premium weekly-plan alias as one exact compatibility family."""

    api_key_dependency = _require_canonical_api_key_dependency("Legacy premium weekly-plan")

    ensure_route_family_registered(
        target_app,
        family_name="Legacy premium weekly-plan",
        routers=(legacy_premium_weekly_plan_router,),
        members=_legacy_premium_weekly_plan_route_members(api_key_dependency),
    )


def _include_legacy_insight_router_if_needed(target_app: FastAPI) -> None:
    """Register legacy insight routes as one exact compatibility family."""

    ensure_route_family_registered(
        target_app,
        family_name="Legacy insight",
        routers=(legacy_insight_router,),
        members=_legacy_insight_route_members(),
    )


def _include_business_router_if_enabled(target_app: FastAPI) -> None:
    """Register business routes as one explicitly feature-flagged static family."""

    if not is_business_module_enabled():
        return

    ensure_route_family_registered(
        target_app,
        family_name="Business",
        routers=(business_router,),
        members=_business_route_members(),
    )


def _include_food_catalog_routers_if_needed(target_app: FastAPI) -> None:
    """Register foods/catalog routes as one canonical static family."""

    ensure_route_family_registered(
        target_app,
        family_name="Food catalog",
        routers=(foods_router, catalog_router),
        members=_food_catalog_route_members(),
    )


def _include_recipe_nutrition_reference_routers_if_needed(target_app: FastAPI) -> None:
    """Register recipe and nutrition-reference routes as one canonical static family."""

    ensure_route_family_registered(
        target_app,
        family_name="Recipe nutrition reference",
        routers=(recipes_router, nutrition_recommendations_router),
        members=_recipe_nutrition_reference_route_members(),
    )


def _include_users_router_if_needed(target_app: FastAPI) -> None:
    """Register internal users CRUD routes as one hidden canonical family."""

    ensure_route_family_registered(
        target_app,
        family_name="Users",
        routers=(users_router,),
        members=_users_route_members(),
    )


def _include_test_router_if_enabled(target_app: FastAPI) -> None:
    """Register non-production test routes as one hidden canonical family."""

    if not _test_routes_enabled_for_registration():
        return

    logger.info(
        "Test routes enabled for registration",
        extra={
            "runtime_env": get_runtime_env_name(),
            "enable_test_routes": os.getenv("ENABLE_TEST_ROUTES"),
        },
    )
    ensure_route_family_registered(
        target_app,
        family_name="Test",
        routers=(test_router,),
        members=_test_route_members(),
    )


def _include_restaurants_router_if_needed(target_app: FastAPI) -> None:
    """Register public restaurant routes as one hidden canonical static family."""

    ensure_route_family_registered(
        target_app,
        family_name="Restaurants",
        routers=(restaurants_router,),
        members=_restaurant_route_members(),
    )


def _include_restaurant_moderation_router_if_needed(target_app: FastAPI) -> None:
    """Register restaurant moderation route as one protected atomic family."""

    api_key_dependency = _require_canonical_api_key_dependency("Restaurant moderation")

    ensure_route_family_registered(
        target_app,
        family_name="Restaurant moderation",
        routers=(restaurant_moderation_router,),
        members=_restaurant_moderation_route_members(api_key_dependency),
        registration_dependencies=(Depends(api_key_dependency),),
    )


def _import_vip_module_for_compat() -> Any:
    from app.routers import vip as vip_module

    return vip_module


def _resolve_vip_router_for_compat() -> APIRouter | None:
    if not is_vip_module_enabled():
        return None

    try:
        vip_module = _import_vip_module_for_compat()
    except ModuleNotFoundError as exc:
        if exc.name == "app.routers.vip":
            return None
        raise
    return getattr(vip_module, "router", None)


def _mirror_paid_tier_registration_attrs(
    registered_pro_router: APIRouter | None,
    registered_premium_week_router: APIRouter | None,
) -> None:
    global VIP_MODULE_ENABLED, vip_router, pro_router, premium_week_router

    resolved_vip_module_enabled = is_vip_module_enabled()
    resolved_vip_router = _resolve_vip_router_for_compat()
    resolved_pro_router = registered_pro_router
    resolved_premium_week_router = registered_premium_week_router

    VIP_MODULE_ENABLED = resolved_vip_module_enabled
    vip_router = resolved_vip_router
    pro_router = resolved_pro_router
    premium_week_router = resolved_premium_week_router
    _legacy_module.VIP_MODULE_ENABLED = resolved_vip_module_enabled
    _legacy_module.vip_router = resolved_vip_router
    _legacy_module.pro_router = resolved_pro_router
    _legacy_module.premium_week_router = resolved_premium_week_router


def _register_paid_tier_routes(target_app: FastAPI) -> None:
    register_vip_routes(target_app)
    registered_pro_router, registered_premium_week_router = register_pro_routes(target_app)
    _mirror_paid_tier_registration_attrs(registered_pro_router, registered_premium_week_router)


def _mirror_bmi_registration_attrs(registration: BmiRouteRegistration) -> None:
    global FEATURE_BMI_PRO_ENABLED, bmi_router, bmi_pro_router, bmi_pro_legacy_alias_router

    FEATURE_BMI_PRO_ENABLED = registration.feature_bmi_pro_enabled
    bmi_router = registration.bmi_router
    bmi_pro_router = registration.bmi_pro_router
    bmi_pro_legacy_alias_router = registration.bmi_pro_legacy_alias_router
    _legacy_module.FEATURE_BMI_PRO_ENABLED = registration.feature_bmi_pro_enabled
    _legacy_module.bmi_router = registration.bmi_router
    _legacy_module.bmi_pro_router = registration.bmi_pro_router
    _legacy_module.bmi_pro_legacy_alias_router = registration.bmi_pro_legacy_alias_router


def _register_bmi_routes(target_app: FastAPI) -> None:
    _mirror_bmi_registration_attrs(register_bmi_routes(target_app))


def ensure_canonical_app_bootstrap(target_app: FastAPI) -> FastAPI:
    """Apply canonical additive bootstrap to the provided FastAPI instance.

    The supplied object is composed in place. This function never rebinds the
    module-level canonical singleton.
    """
    app = target_app
    validate_openapi_builder_state(app)
    bespoke_routes = (
        ("/", "GET", serve_direct_api_root_probe),
        (LEGACY_BMI_WEB_ROUTE, "GET", serve_legacy_bmi_calculator_web),
        (SITEMAP_ROUTE_PATH, "GET", serve_public_sitemap),
        *(
            (path, "POST", route_endpoint_for_path_method(router.routes, path, "POST"))
            for path, router in (
                (_FEEDBACK_ROUTE_PATH, feedback_router),
                (_CBT_INSIGHT_ROUTE_PATH, cbt_insight_router),
                (_FITCHEF_STRUCTURED_ROUTE_PATH, fitchef_structured_router),
                (_CREATIVE_RESEARCH_PILOT_ROUTE_PATH, creative_research_internal_router),
                (_PAYWALL_EVENTS_ROUTE_PATH, paywall_analytics_router),
            )
        ),
    )
    route_exists = {
        path: _route_has_endpoint(app, path, method, endpoint)
        for path, method, endpoint in bespoke_routes
    }
    ws_source = {route_path(route): route for route in realtime_ws.router.routes}
    ws_valid = not ws_source or len(realtime_ws.router.routes) == len(_WS_ROUTE_PATHS)
    ws_endpoints = tuple(route_endpoint(ws_source.get(p)) for p in _WS_ROUTE_PATHS)
    ws_endpoints = ws_endpoints if ws_source else (realtime_ws.ws_pro, realtime_ws.ws_root)
    ws_owner = cast(FastAPI, realtime_ws.router) if ws_source else app
    websocket_exists = []
    for path, endpoint in zip(_WS_ROUTE_PATHS, ws_endpoints, strict=True):
        _route_has_endpoint(ws_owner, path, "", endpoint)
        websocket_exists.append(_route_has_endpoint(app, path, "", endpoint))
    if not ws_valid or (any(websocket_exists) and not all(websocket_exists)):
        raise RuntimeError("Incomplete canonical websocket route family.")
    register_http_middleware_stack(target_app)

    if not route_exists["/"]:
        app.add_api_route(
            "/",
            serve_direct_api_root_probe,
            methods=["GET"],
            include_in_schema=False,
            response_model=DirectApiRootProbe,
        )
    if not route_exists[LEGACY_BMI_WEB_ROUTE]:
        app.add_api_route(
            LEGACY_BMI_WEB_ROUTE,
            serve_legacy_bmi_calculator_web,
            methods=["GET"],
            include_in_schema=False,
            response_class=HTMLResponse,
        )
    if not route_exists[SITEMAP_ROUTE_PATH]:
        app.add_api_route(
            SITEMAP_ROUTE_PATH,
            serve_public_sitemap,
            methods=["GET"],
            include_in_schema=False,
        )
    _register_paid_tier_routes(app)
    register_pro_contract_routes(app)
    _include_recipe_nutrition_reference_routers_if_needed(app)
    _include_nutrition_state_routers_if_needed(app)

    if ws_source and not any(websocket_exists):
        app.include_router(realtime_ws.router)

    if not route_exists[_FEEDBACK_ROUTE_PATH]:
        app.include_router(feedback_router)

    _include_health_router_if_needed(app)
    _include_legal_router_if_needed(app)
    _include_favicon_router_if_needed(app)
    _include_admin_operations_router_if_needed(app)
    _register_bmi_routes(app)
    _include_bmi_compat_router_if_needed(app)
    _include_bodyfat_router_if_needed(app)
    _include_business_router_if_enabled(app)
    _include_food_catalog_routers_if_needed(app)
    _include_users_router_if_needed(app)
    _include_test_router_if_enabled(app)
    _include_plan_export_routers_if_needed(app)
    _include_shoplist_export_router_if_needed(app)
    _include_legacy_premium_nutrition_router_if_needed(app)
    _include_legacy_premium_weekly_plan_router_if_needed(app)
    _include_legacy_insight_router_if_needed(app)
    _include_shopping_list_routers_if_needed(app)
    _include_restaurants_router_if_needed(app)
    _include_restaurant_moderation_router_if_needed(app)

    register_billing_routes(app)

    if not route_exists[_CBT_INSIGHT_ROUTE_PATH]:
        app.include_router(cbt_insight_router)

    if not route_exists[_FITCHEF_STRUCTURED_ROUTE_PATH]:
        app.include_router(fitchef_structured_router)

    if not route_exists[_CREATIVE_RESEARCH_PILOT_ROUTE_PATH]:
        app.include_router(creative_research_internal_router)

    if not route_exists[_PAYWALL_EVENTS_ROUTE_PATH]:
        app.include_router(paywall_analytics_router)

    apply_public_openapi_input_policy(app)
    install_canonical_openapi_builder(app)
    # Importing canonical routers loads the ``app.metrics`` submodule, which
    # Python records on the package and which would shadow the reviewed facade
    # export. Remove only that package binding after bootstrap so the existing
    # finite lazy export map remains authoritative for ``app.metrics``.
    app_package = sys.modules.get("app")
    metrics_module = sys.modules.get("app.metrics")
    if (
        app_package is not None
        and metrics_module is not None
        and vars(app_package).get("metrics") is metrics_module
    ):
        delattr(app_package, "metrics")
    app.router.lifespan_context = application_lifespan
    return app


ensure_canonical_app_bootstrap(app)

__all__ = ["app"]

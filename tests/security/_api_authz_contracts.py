from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
)
from app.middleware.api_tiers import require_pro_tier, require_vip_tier
from app.bootstrap.metrics import _metrics_api_key_guard
from app.routers.api_key import _get_api_key_dynamic, api_key_header
from app.routers.api_key import require_app_api_key
from app.routers.billing import (
    _require_billing_transport_key,
    _require_manual_billing_transport_key,
)
from app.routers.feedback import get_feedback_user
from app.routers.plan_export import _require_valid_token
from app.routers.test import _ensure_non_production
from app.routers.users import _require_users_api_key


class AuthClass(str, Enum):
    PRO_TIER = "pro_tier"
    VIP_TIER = "vip_tier"
    FEEDBACK_CREDENTIAL = "feedback_credential"
    USERS_CREDENTIAL = "users_credential"
    PRE_ENTITLEMENT_CREDENTIAL = "pre_entitlement_credential"
    PRE_ENTITLEMENT_TRANSPORT = "pre_entitlement_transport"
    BILLING_TRANSPORT = "billing_transport"
    DEPRECATED_ALIAS_CREDENTIAL = "deprecated_alias_credential"
    LEGACY_CREDENTIAL = "legacy_credential"
    LEGACY_HIDDEN_CREDENTIAL = "legacy_hidden_credential"
    LEGACY_PUBLIC_COMPATIBILITY = "legacy_public_compatibility"
    LEGACY_PRO_TIER = "legacy_pro_tier"
    LEGACY_VIP_TIER = "legacy_vip_tier"
    ADMIN_CREDENTIAL = "admin_credential"
    METRICS_CREDENTIAL = "metrics_credential"
    EXPORT_TOKEN = "export_token"
    OPTIONAL_PRO_CONTEXT = "optional_pro_context"
    NON_PRODUCTION_TEST_GUARD = "non_production_test_guard"


class MinimumTier(str, Enum):
    NONE = "none"
    FREE = "free"
    PRO = "pro"
    VIP = "vip"


class PrincipalSource(str, Enum):
    NONE = "none"
    CREDENTIAL_DERIVED_SUBJECT = "credential_derived_subject"
    BILLING_ISSUER = "billing_issuer"
    CATALOG_RESOURCE = "catalog_resource"
    INTERNAL_OPTIONAL = "internal_optional"
    LEGACY_HIDDEN = "legacy_hidden"
    LEGACY_CREDENTIAL_SUBJECT = "legacy_credential_subject"
    OPERATOR_CREDENTIAL = "operator_credential"


class OwnershipPolicy(str, Enum):
    NONE = "none"
    AUTHENTICATED_SUBJECT = "authenticated_subject"
    ISSUER_SCOPED = "issuer_scoped"
    CATALOG_RESOURCE = "catalog_resource"
    INTERNAL_OPTIONAL = "internal_optional"
    LEGACY_HIDDEN = "legacy_hidden"
    LEGACY_COMPATIBILITY = "legacy_compatibility"
    OPERATOR_GLOBAL = "operator_global"


class ApiExposure(str, Enum):
    PUBLIC_OPENAPI = "public_openapi"
    HIDDEN_RUNTIME = "hidden_runtime"
    DEPRECATED_ALIAS = "deprecated_alias"


RouteKey = tuple[str, str]
DependencyKey = tuple[str, str]


@dataclass(frozen=True)
class ApiAuthzContract:
    method: str
    path: str
    auth_class: AuthClass
    minimum_tier: MinimumTier
    principal_source: PrincipalSource
    ownership_policy: OwnershipPolicy
    exposure: ApiExposure
    foreign_object_status: int | None = None

    @property
    def key(self) -> RouteKey:
        return self.method.upper(), self.path


def _contract(
    method: str,
    path: str,
    auth_class: AuthClass,
    minimum_tier: MinimumTier,
    principal_source: PrincipalSource,
    ownership_policy: OwnershipPolicy,
    exposure: ApiExposure = ApiExposure.PUBLIC_OPENAPI,
    foreign_object_status: int | None = None,
) -> ApiAuthzContract:
    return ApiAuthzContract(
        method=method,
        path=path,
        auth_class=auth_class,
        minimum_tier=minimum_tier,
        principal_source=principal_source,
        ownership_policy=ownership_policy,
        exposure=exposure,
        foreign_object_status=foreign_object_status,
    )


PRO_SUBJECT = (
    AuthClass.PRO_TIER,
    MinimumTier.PRO,
    PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
    OwnershipPolicy.AUTHENTICATED_SUBJECT,
)
VIP_SUBJECT = (
    AuthClass.VIP_TIER,
    MinimumTier.VIP,
    PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
    OwnershipPolicy.AUTHENTICATED_SUBJECT,
)
VIP_CATALOG = (
    AuthClass.VIP_TIER,
    MinimumTier.VIP,
    PrincipalSource.CATALOG_RESOURCE,
    OwnershipPolicy.CATALOG_RESOURCE,
)


API_AUTHZ_CONTRACTS: tuple[ApiAuthzContract, ...] = (
    _contract("POST", "/api/v1/bayes/adherence/event", *PRO_SUBJECT),
    _contract("GET", "/api/v1/bayes/adherence/risk", *PRO_SUBJECT),
    _contract(
        "POST",
        "/api/v1/billing/apple/verify-receipt",
        AuthClass.BILLING_TRANSPORT,
        MinimumTier.NONE,
        PrincipalSource.BILLING_ISSUER,
        OwnershipPolicy.ISSUER_SCOPED,
    ),
    _contract(
        "GET",
        "/api/v1/admin/check-updates",
        AuthClass.ADMIN_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/admin/db-status",
        AuthClass.ADMIN_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/admin/status",
        AuthClass.ADMIN_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/admin/force-update",
        AuthClass.ADMIN_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/admin/rollback",
        AuthClass.ADMIN_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/admin/logs/cleanup",
        AuthClass.ADMIN_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/bmi",
        AuthClass.LEGACY_PUBLIC_COMPATIBILITY,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_HIDDEN,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/plan",
        AuthClass.LEGACY_PUBLIC_COMPATIBILITY,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_HIDDEN,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/bmi/pro",
        AuthClass.LEGACY_PRO_TIER,
        MinimumTier.PRO,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
        ApiExposure.DEPRECATED_ALIAS,
    ),
    _contract(
        "POST",
        "/api/v1/business/analyze",
        AuthClass.ADMIN_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/export/sign",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "POST",
        "/api/v1/feedback/rag",
        AuthClass.FEEDBACK_CREDENTIAL,
        MinimumTier.FREE,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
    ),
    _contract(
        "GET",
        "/api/v1/foods/{food_id}",
        AuthClass.OPTIONAL_PRO_CONTEXT,
        MinimumTier.NONE,
        PrincipalSource.CATALOG_RESOURCE,
        OwnershipPolicy.CATALOG_RESOURCE,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/foods/barcode/{barcode}",
        AuthClass.OPTIONAL_PRO_CONTEXT,
        MinimumTier.NONE,
        PrincipalSource.CATALOG_RESOURCE,
        OwnershipPolicy.CATALOG_RESOURCE,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/insight",
        AuthClass.LEGACY_VIP_TIER,
        MinimumTier.VIP,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/insight/fitchef",
        AuthClass.LEGACY_VIP_TIER,
        MinimumTier.VIP,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
    ),
    _contract(
        "POST",
        "/api/v1/insight/fitchef/slip-support",
        AuthClass.LEGACY_VIP_TIER,
        MinimumTier.VIP,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
    ),
    _contract(
        "POST",
        "/api/v1/insight/fitchef/weekly-reflection",
        AuthClass.LEGACY_VIP_TIER,
        MinimumTier.VIP,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
    ),
    _contract(
        "POST", "/api/v1/internal/creative-research/pilot", *VIP_SUBJECT, ApiExposure.HIDDEN_RUNTIME
    ),
    _contract(
        "POST",
        "/api/v1/internal/paywall/events",
        AuthClass.OPTIONAL_PRO_CONTEXT,
        MinimumTier.NONE,
        PrincipalSource.INTERNAL_OPTIONAL,
        OwnershipPolicy.INTERNAL_OPTIONAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/test/rate-limit",
        AuthClass.NON_PRODUCTION_TEST_GUARD,
        MinimumTier.NONE,
        PrincipalSource.INTERNAL_OPTIONAL,
        OwnershipPolicy.INTERNAL_OPTIONAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/test/echo",
        AuthClass.NON_PRODUCTION_TEST_GUARD,
        MinimumTier.NONE,
        PrincipalSource.INTERNAL_OPTIONAL,
        OwnershipPolicy.INTERNAL_OPTIONAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/plan/week/export.csv",
        AuthClass.EXPORT_TOKEN,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "GET",
        "/api/v1/plan/week/export.pdf",
        AuthClass.EXPORT_TOKEN,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "POST",
        "/api/v1/premium/bmr",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "POST",
        "/api/v1/premium/gaps",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "POST",
        "/api/v1/premium/plan/week",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/premium/plan/week-flexible",
        AuthClass.LEGACY_PRO_TIER,
        MinimumTier.PRO,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
        ApiExposure.DEPRECATED_ALIAS,
    ),
    _contract(
        "POST",
        "/api/v1/premium/plate",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "POST",
        "/api/v1/premium/targets",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract("GET", "/api/v1/pro/attribution", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/bmi", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/bmi/calculate", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/cbt/insight", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/fitchef/explain", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/fitchef/recommend", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/meal/shopping-list", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/meal/weekly", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/coverage", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/day-close", *PRO_SUBJECT),
    _contract("GET", "/api/v1/pro/nutrition/daily", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/deficiency-recommendations", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/bmr", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/gaps", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/meal-log", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/micronutrient-targets", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/plate", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/safety-check", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/nutrition/targets", *PRO_SUBJECT),
    _contract(
        "GET",
        "/api/v1/pro/payments/activations/{activation_id}",
        AuthClass.PRE_ENTITLEMENT_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.BILLING_ISSUER,
        OwnershipPolicy.ISSUER_SCOPED,
        foreign_object_status=403,
    ),
    _contract(
        "POST",
        "/api/v1/pro/payments/activate",
        AuthClass.PRE_ENTITLEMENT_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.BILLING_ISSUER,
        OwnershipPolicy.ISSUER_SCOPED,
    ),
    _contract(
        "POST",
        "/api/v1/pro/payments/ru-by/manual-intent",
        AuthClass.PRE_ENTITLEMENT_TRANSPORT,
        MinimumTier.NONE,
        PrincipalSource.BILLING_ISSUER,
        OwnershipPolicy.ISSUER_SCOPED,
    ),
    _contract(
        "POST",
        "/api/v1/pro/payments/ru-by/reconcile",
        AuthClass.PRE_ENTITLEMENT_TRANSPORT,
        MinimumTier.NONE,
        PrincipalSource.BILLING_ISSUER,
        OwnershipPolicy.ISSUER_SCOPED,
    ),
    _contract(
        "GET",
        "/api/v1/pro/payments/ru-by/reconcile/{intent_id}",
        AuthClass.PRE_ENTITLEMENT_TRANSPORT,
        MinimumTier.NONE,
        PrincipalSource.BILLING_ISSUER,
        OwnershipPolicy.ISSUER_SCOPED,
        foreign_object_status=403,
    ),
    _contract("POST", "/api/v1/pro/restaurants/partner/orders", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/restaurants/partner/orders/adapt/preview", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/restaurants/partner/orders/preview", *PRO_SUBJECT),
    _contract(
        "GET",
        "/api/v1/pro/restaurants/partner/orders/{order_id}",
        *PRO_SUBJECT,
        foreign_object_status=403,
    ),
    _contract(
        "POST",
        "/api/v1/pro/restaurants/partner/orders/{order_id}/confirm",
        *PRO_SUBJECT,
        foreign_object_status=403,
    ),
    _contract(
        "POST",
        "/api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares",
        *PRO_SUBJECT,
        foreign_object_status=403,
    ),
    _contract(
        "GET",
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status",
        *PRO_SUBJECT,
        foreign_object_status=403,
    ),
    _contract(
        "POST",
        "/api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke",
        *PRO_SUBJECT,
        foreign_object_status=403,
    ),
    _contract(
        "PATCH",
        "/api/v1/restaurants/submissions/{submission_id}/status",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/restaurants/{chain_id}/menu",
        AuthClass.OPTIONAL_PRO_CONTEXT,
        MinimumTier.NONE,
        PrincipalSource.CATALOG_RESOURCE,
        OwnershipPolicy.CATALOG_RESOURCE,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/api/v1/restaurants/submissions",
        AuthClass.OPTIONAL_PRO_CONTEXT,
        MinimumTier.NONE,
        PrincipalSource.CATALOG_RESOURCE,
        OwnershipPolicy.CATALOG_RESOURCE,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/restaurants/submissions/{submission_id}",
        AuthClass.OPTIONAL_PRO_CONTEXT,
        MinimumTier.NONE,
        PrincipalSource.CATALOG_RESOURCE,
        OwnershipPolicy.CATALOG_RESOURCE,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/recipes/{recipe_id}",
        AuthClass.OPTIONAL_PRO_CONTEXT,
        MinimumTier.NONE,
        PrincipalSource.CATALOG_RESOURCE,
        OwnershipPolicy.CATALOG_RESOURCE,
    ),
    _contract("GET", "/api/v1/pro/session", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/session/exchange", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/session/logout", *PRO_SUBJECT),
    _contract("POST", "/api/v1/pro/session/refresh", *PRO_SUBJECT),
    _contract("GET", "/api/v1/pro/shoplist/day", *PRO_SUBJECT),
    _contract(
        "POST",
        "/api/v1/users",
        AuthClass.USERS_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_HIDDEN,
        OwnershipPolicy.LEGACY_HIDDEN,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/users",
        AuthClass.USERS_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_HIDDEN,
        OwnershipPolicy.LEGACY_HIDDEN,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/v1/users/{user_id}",
        AuthClass.USERS_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_HIDDEN,
        OwnershipPolicy.LEGACY_HIDDEN,
        ApiExposure.HIDDEN_RUNTIME,
        foreign_object_status=403,
    ),
    _contract(
        "DELETE",
        "/api/v1/users/{user_id}",
        AuthClass.USERS_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_HIDDEN,
        OwnershipPolicy.LEGACY_HIDDEN,
        ApiExposure.HIDDEN_RUNTIME,
        foreign_object_status=403,
    ),
    _contract(
        "GET",
        "/api/v1/shoplist",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "GET",
        "/api/v1/shoplist/export.csv",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract(
        "GET",
        "/api/v1/shoplist/export.pdf",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
    _contract("POST", "/api/v1/vip/auto-repair/suggestions", *VIP_SUBJECT),
    _contract("GET", "/api/v1/vip/auto-repair/strategies", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/auto-repair/weekly", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/fitchef/insight", *VIP_SUBJECT),
    _contract("GET", "/api/v1/vip/health", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/menu/weekly/plan", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/menu/weekly/repair", *VIP_SUBJECT),
    _contract("GET", "/api/v1/vip/recipes/templates", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/recipes/synthesize", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/recipes/weekly", *VIP_SUBJECT),
    _contract("GET", "/api/v1/vip/regions", *VIP_CATALOG),
    _contract("GET", "/api/v1/vip/regions/{region}/categories", *VIP_CATALOG),
    _contract("GET", "/api/v1/vip/regions/{region}/search", *VIP_CATALOG),
    _contract("GET", "/api/v1/vip/regions/{region}/stores", *VIP_CATALOG),
    _contract("GET", "/api/v1/vip/regions/compare/{product_name}", *VIP_CATALOG),
    _contract("POST", "/api/v1/vip/shoplist/daily", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/shoplist/export", *VIP_SUBJECT),
    _contract("GET", "/api/v1/vip/shoplist/formats", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/shoplist/generate", *VIP_SUBJECT),
    _contract("GET", "/api/v1/vip/shoplist/preview", *VIP_SUBJECT),
    _contract("POST", "/api/v1/vip/shoplist/weekly", *VIP_SUBJECT),
    _contract(
        "POST",
        "/api/v1/vip/weekly-plan",
        AuthClass.DEPRECATED_ALIAS_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
        ApiExposure.DEPRECATED_ALIAS,
    ),
    _contract(
        "GET",
        "/metrics",
        AuthClass.METRICS_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.OPERATOR_CREDENTIAL,
        OwnershipPolicy.OPERATOR_GLOBAL,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/insight",
        AuthClass.LEGACY_VIP_TIER,
        MinimumTier.VIP,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "GET",
        "/api/nutrition/{date_str}",
        AuthClass.LEGACY_PRO_TIER,
        MinimumTier.PRO,
        PrincipalSource.CREDENTIAL_DERIVED_SUBJECT,
        OwnershipPolicy.AUTHENTICATED_SUBJECT,
        ApiExposure.HIDDEN_RUNTIME,
    ),
    _contract(
        "POST",
        "/premium_targets",
        AuthClass.LEGACY_CREDENTIAL,
        MinimumTier.NONE,
        PrincipalSource.LEGACY_CREDENTIAL_SUBJECT,
        OwnershipPolicy.LEGACY_COMPATIBILITY,
    ),
)

CONTRACT_BY_KEY: dict[RouteKey, ApiAuthzContract] = {
    contract.key: contract for contract in API_AUTHZ_CONTRACTS
}


def _load_routes(app: FastAPI) -> list[Any]:
    return [
        route
        for route in iter_effective_route_candidates(app.routes)
        if is_api_route_candidate(route)
    ]


def _route_keys(route: APIRoute) -> set[RouteKey]:
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    return {(method, route.path) for method in methods}


def sensitive_route_keys(routes: Iterable[APIRoute]) -> set[RouteKey]:
    keys: set[RouteKey] = set()
    for route in routes:
        if _is_sensitive_route(route):
            keys.update(_route_keys(route))
    return keys


def routes_by_key(routes: Iterable[APIRoute]) -> dict[RouteKey, list[APIRoute]]:
    grouped: dict[RouteKey, list[APIRoute]] = defaultdict(list)
    for route in routes:
        for key in _route_keys(route):
            grouped[key].append(route)
    return dict(grouped)


def _flatten_dependency_calls(route: APIRoute) -> list[Callable[..., Any]]:
    seen: set[int] = set()
    calls: list[Callable[..., Any]] = []

    def visit(dep: Dependant) -> None:
        call = getattr(dep, "call", None)
        if callable(call) and id(call) not in seen:
            seen.add(id(call))
            calls.append(call)
        for child in getattr(dep, "dependencies", []) or []:
            visit(child)

    for dep in getattr(route.dependant, "dependencies", []) or []:
        visit(dep)
    return calls


def _dependency_key(call: Callable[..., Any]) -> DependencyKey:
    module_name = getattr(call, "__module__", type(call).__module__)
    qualified_name = getattr(
        call,
        "__qualname__",
        getattr(call, "__name__", type(call).__name__),
    )
    return module_name, qualified_name


AUTH_DEPENDENCY_KEYS: frozenset[DependencyKey] = frozenset(
    {
        _dependency_key(require_pro_tier),
        _dependency_key(require_vip_tier),
        _dependency_key(get_feedback_user),
        _dependency_key(_require_users_api_key),
        _dependency_key(_require_billing_transport_key),
        _dependency_key(_require_manual_billing_transport_key),
        _dependency_key(api_key_header),
        _dependency_key(require_app_api_key),
        _dependency_key(_metrics_api_key_guard),
        _dependency_key(_require_valid_token),
        _dependency_key(_get_api_key_dynamic),
    }
)


def _has_auth_dependency(route: APIRoute) -> bool:
    flattened_calls = _flatten_dependency_calls(route)
    return any(_dependency_key(call) in AUTH_DEPENDENCY_KEYS for call in flattened_calls)


def _is_sensitive_route(route: APIRoute) -> bool:
    sensitive_prefixes = (
        "/api/v1/bayes/adherence",
        "/api/v1/feedback",
        "/api/v1/internal",
        "/api/v1/pro",
        "/api/v1/users",
        "/api/v1/vip",
    )
    has_object_identifier = "{" in route.path and "}" in route.path
    is_hidden_mutation = not route.include_in_schema and bool(
        (route.methods or set()) & {"POST", "PUT", "PATCH", "DELETE"}
    )
    return (
        route.path.startswith(sensitive_prefixes)
        or _has_auth_dependency(route)
        or has_object_identifier
        or is_hidden_mutation
    )


def _contains_dependency(
    flattened_calls: list[Callable[..., Any]],
    expected_dependency: Callable[..., Any],
) -> bool:
    if expected_dependency in flattened_calls:
        return True
    expected_key = _dependency_key(expected_dependency)
    return any(_dependency_key(call) == expected_key for call in flattened_calls)


EXPECTED_DEPENDENCY_BY_AUTH_CLASS: dict[AuthClass, Callable[..., Any] | None] = {
    AuthClass.PRO_TIER: require_pro_tier,
    AuthClass.VIP_TIER: require_vip_tier,
    AuthClass.FEEDBACK_CREDENTIAL: get_feedback_user,
    AuthClass.USERS_CREDENTIAL: _require_users_api_key,
    AuthClass.PRE_ENTITLEMENT_CREDENTIAL: api_key_header,
    AuthClass.PRE_ENTITLEMENT_TRANSPORT: _require_manual_billing_transport_key,
    AuthClass.BILLING_TRANSPORT: _require_billing_transport_key,
    AuthClass.DEPRECATED_ALIAS_CREDENTIAL: api_key_header,
    AuthClass.LEGACY_CREDENTIAL: _get_api_key_dynamic,
    AuthClass.LEGACY_HIDDEN_CREDENTIAL: api_key_header,
    AuthClass.LEGACY_PUBLIC_COMPATIBILITY: None,
    AuthClass.LEGACY_PRO_TIER: require_pro_tier,
    AuthClass.LEGACY_VIP_TIER: require_vip_tier,
    AuthClass.ADMIN_CREDENTIAL: require_app_api_key,
    AuthClass.METRICS_CREDENTIAL: _metrics_api_key_guard,
    AuthClass.EXPORT_TOKEN: _require_valid_token,
    AuthClass.OPTIONAL_PRO_CONTEXT: None,
    AuthClass.NON_PRODUCTION_TEST_GUARD: _ensure_non_production,
}

# -*- coding: utf-8 -*-
"""Canonical BMI route registration."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi.routing import APIRouter, APIRoute

from app.bootstrap.route_family import (
    RouteMemberContract,
    ensure_route_family_registered,
    route_member_contracts_from_router,
)
from app.middleware.api_tiers import require_pro_tier
from app.utils.feature_flags import _is_truthy

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = [
    "BMI_PRO_LEGACY_ALIAS_ROUTE_SPECS",
    "BMI_PRO_ROUTE_SPECS",
    "BMI_ROUTE_SPECS",
    "BmiRouteRegistration",
    "is_bmi_pro_enabled",
    "register_bmi_routes",
]

BMI_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (("/api/v1/bmi/calculate", "POST", True),)
BMI_PRO_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/pro/bmi", "POST", True),
    ("/api/v1/pro/bmi/calculate", "POST", True),
)
BMI_PRO_LEGACY_ALIAS_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/bmi/pro", "POST", True),
)
_FRAMEWORK_METHODS = frozenset({"HEAD", "OPTIONS"})


@dataclass(frozen=True, slots=True)
class BmiRouteRegistration:
    """Routers registered by canonical BMI bootstrap."""

    bmi_router: APIRouter
    bmi_pro_router: APIRouter | None
    bmi_pro_legacy_alias_router: APIRouter | None
    feature_bmi_pro_enabled: bool


def is_bmi_pro_enabled() -> bool:
    """Return whether BMI Pro routes should be registered."""

    raw_value = os.getenv("FEATURE_BMI_PRO_ENABLED")
    return bool(_is_truthy(raw_value)) if raw_value is not None else False


def _route_members_for_routers(
    family_name: str,
    routers: tuple[APIRouter, ...],
    *,
    extra_required_dependencies: tuple[Callable[..., object], ...] = (),
) -> tuple[RouteMemberContract, ...]:
    return tuple(
        member
        for router in routers
        for member in route_member_contracts_from_router(
            family_name,
            router,
            extra_required_dependencies=extra_required_dependencies,
        )
    )


def _require_exact_router_family(
    family_name: str,
    router: object,
    module_name: str,
    specs: tuple[tuple[str, str, bool], ...],
) -> APIRouter:
    if not isinstance(router, APIRouter) or not router.routes:
        raise RuntimeError(
            f"{family_name} router from {module_name} must be a non-empty APIRouter."
        )

    expected = {(path, method.upper()): include for path, method, include in specs}
    actual: dict[tuple[str, str], APIRoute] = {}
    for route in router.routes:
        if not isinstance(route, APIRoute):
            raise RuntimeError(f"{family_name} router does not define the expected route family.")

        methods = {
            str(method).upper()
            for method in (route.methods or set())
            if str(method).upper() not in _FRAMEWORK_METHODS
        }
        if len(methods) != 1:
            raise RuntimeError(f"{family_name} router does not define the expected route family.")
        method = next(iter(methods))
        key = (str(route.path), method)
        if key in actual:
            raise RuntimeError(f"{family_name} router does not define the expected route family.")
        actual[key] = route

    if set(actual) != set(expected):
        raise RuntimeError(f"{family_name} router does not define the expected route family.")

    for key, include_in_schema in expected.items():
        if actual[key].include_in_schema is not include_in_schema:
            raise RuntimeError(f"{family_name} router does not preserve OpenAPI visibility.")

    return router


def register_bmi_routes(app: "FastAPI") -> BmiRouteRegistration:
    """Register BMI route families with the FastAPI application."""

    cached = getattr(app.state, "_cached_bmi_route_registration", None)
    if getattr(app.state, "_bmi_routes_registered", False) and isinstance(
        cached,
        BmiRouteRegistration,
    ):
        return cached

    from app.routers.bmi import router as bmi_router_imported

    bmi_router = _require_exact_router_family(
        "BMI",
        bmi_router_imported,
        "app.routers.bmi",
        BMI_ROUTE_SPECS,
    )
    ensure_route_family_registered(
        app,
        family_name="BMI",
        routers=(bmi_router,),
        members=route_member_contracts_from_router("BMI", bmi_router),
    )

    bmi_pro_router: APIRouter | None = None
    bmi_pro_legacy_alias_router: APIRouter | None = None
    feature_bmi_pro_enabled = is_bmi_pro_enabled()
    if feature_bmi_pro_enabled:
        from app.routers.bmi_pro import router as bmi_pro_router_imported
        from app.routers.bmi_pro_legacy_alias import (
            router as bmi_pro_legacy_alias_router_imported,
        )

        bmi_pro_router = _require_exact_router_family(
            "BMI Pro",
            bmi_pro_router_imported,
            "app.routers.bmi_pro",
            BMI_PRO_ROUTE_SPECS,
        )
        bmi_pro_legacy_alias_router = _require_exact_router_family(
            "BMI Pro legacy alias",
            bmi_pro_legacy_alias_router_imported,
            "app.routers.bmi_pro_legacy_alias",
            BMI_PRO_LEGACY_ALIAS_ROUTE_SPECS,
        )
        bmi_pro_routers = (bmi_pro_router, bmi_pro_legacy_alias_router)
        ensure_route_family_registered(
            app,
            family_name="BMI Pro",
            routers=bmi_pro_routers,
            members=_route_members_for_routers(
                "BMI Pro",
                bmi_pro_routers,
                extra_required_dependencies=(require_pro_tier,),
            ),
        )

    registration = BmiRouteRegistration(
        bmi_router=bmi_router,
        bmi_pro_router=bmi_pro_router,
        bmi_pro_legacy_alias_router=bmi_pro_legacy_alias_router,
        feature_bmi_pro_enabled=feature_bmi_pro_enabled,
    )
    app.state._bmi_routes_registered = True
    app.state._cached_bmi_route_registration = registration
    return registration

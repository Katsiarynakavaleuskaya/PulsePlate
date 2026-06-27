# -*- coding: utf-8 -*-
"""
VIP Router Registration

RU: Централизованная регистрация VIP роутеров.
EN: Centralized VIP router registration.

This module provides a single entry point for registering all VIP routes
with the FastAPI application, eliminating import-side-effects and making
VIP route registration explicit and testable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.effective_routes import (
    iter_effective_route_candidates,
    route_endpoint,
    route_methods,
    route_path,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["register_vip_routes"]

_FITCHEF_STRUCTURED_VIP_ROUTE_PATH = "/api/v1/vip/fitchef/insight"


def _has_route(app: FastAPI, path: str, method: str) -> bool:
    """Return whether path/method is already registered."""

    method_name = method.upper()
    return any(
        route_path(route) == path and method_name in route_methods(route)
        for route in iter_effective_route_candidates(app.routes)
    )


def _route_has_endpoint(app: FastAPI, path: str, method: str, endpoint: object) -> bool:
    """Return whether path/method is bound to the expected endpoint."""

    method_name = method.upper()
    return any(
        route_path(route) == path
        and method_name in route_methods(route)
        and route_endpoint(route) is endpoint
        for route in iter_effective_route_candidates(app.routes)
    )


def _router_endpoint(router: Any, path: str, method: str) -> object | None:
    """Return the endpoint a router would register for path/method."""

    method_name = method.upper()
    for route in iter_effective_route_candidates(getattr(router, "routes", []) or []):
        if route_path(route) != path:
            continue
        if method_name not in route_methods(route):
            continue
        return route_endpoint(route)
    return None


def register_vip_routes(app: FastAPI) -> None:
    """
    Register VIP routes with the FastAPI application.

    RU: Регистрирует VIP роуты в FastAPI приложении.
    EN: Registers VIP routes with the FastAPI application.

    This function centralizes VIP route registration logic:
    - Checks VIP_MODULE_ENABLED feature flag
    - Includes vip_shoplist router
    - Applies route-level dependencies (API key)

    Args:
        app: FastAPI application instance

    Note:
        This function has no side effects if VIP_MODULE_ENABLED is False.
        It can be called multiple times safely (idempotent).
    """
    from app.routers.fitchef_insight import router as fitchef_insight_router
    from app.routers.fitchef_structured import vip_router as fitchef_structured_vip_router
    from app.utils.feature_flags import is_vip_module_enabled

    if not is_vip_module_enabled():
        return

    existing_paths = {route_path(route) for route in iter_effective_route_candidates(app.routes)}
    fitchef_structured_endpoint = _router_endpoint(
        fitchef_structured_vip_router,
        _FITCHEF_STRUCTURED_VIP_ROUTE_PATH,
        "POST",
    )
    if fitchef_structured_endpoint is not None:
        if _route_has_endpoint(
            app,
            _FITCHEF_STRUCTURED_VIP_ROUTE_PATH,
            "POST",
            fitchef_structured_endpoint,
        ):
            pass
        elif _has_route(app, _FITCHEF_STRUCTURED_VIP_ROUTE_PATH, "POST"):
            raise RuntimeError(
                "Duplicate /api/v1/vip/fitchef/insight route detected with a different handler."
            )
        else:
            app.include_router(fitchef_structured_vip_router)
            existing_paths = {
                route_path(route) for route in iter_effective_route_candidates(app.routes)
            }

    if (
        hasattr(fitchef_insight_router, "routes")
        and "/api/v1/insight/fitchef" not in existing_paths
    ):
        app.include_router(fitchef_insight_router)
        existing_paths = {
            route_path(route) for route in iter_effective_route_candidates(app.routes)
        }

    from app.routers import vip as vip_module
    from app.routers.api_key import api_key_header
    from app.bootstrap.route_family import (
        ensure_route_family_registered,
        route_member_contracts_from_router,
    )
    from fastapi import APIRouter, Depends

    # Register main VIP router (includes vip_shoplist and other VIP endpoints)
    # Route-level dependency: API key required for all VIP endpoints
    vip_router = getattr(vip_module, "router", None)
    if not isinstance(vip_router, APIRouter) or not vip_router.routes:
        raise RuntimeError("VIP router from app.routers.vip must be a non-empty APIRouter.")
    ensure_route_family_registered(
        app,
        family_name="VIP",
        routers=(vip_router,),
        members=route_member_contracts_from_router(
            "VIP",
            vip_router,
            extra_required_dependencies=(api_key_header,),
        ),
        registration_dependencies=(Depends(api_key_header),),
    )

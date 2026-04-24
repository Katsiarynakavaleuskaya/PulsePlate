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

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["register_vip_routes"]


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
    from app.utils.feature_flags import is_vip_module_enabled

    if not is_vip_module_enabled():
        return

    existing_paths = {getattr(route, "path", None) for route in app.routes}

    if (
        hasattr(fitchef_insight_router, "routes")
        and "/api/v1/insight/fitchef" not in existing_paths
    ):
        app.include_router(fitchef_insight_router)
        existing_paths = {getattr(route, "path", None) for route in app.routes}

    from app.routers import vip as vip_module
    from app.routers.api_key import api_key_header
    from fastapi import Depends

    # Register main VIP router (includes vip_shoplist and other VIP endpoints)
    # Route-level dependency: API key required for all VIP endpoints
    vip_router = cast(Any, getattr(vip_module, "router", None))
    vip_router_paths = (
        {
            getattr(route, "path", None)
            for route in vip_router.routes
            if getattr(route, "path", None) is not None
        }
        if vip_router is not None
        else set()
    )

    if vip_router is not None and vip_router_paths.isdisjoint(existing_paths):
        app.include_router(
            vip_router,
            dependencies=[Depends(api_key_header)],
        )

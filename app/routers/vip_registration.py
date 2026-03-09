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

from typing import TYPE_CHECKING

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

    existing_paths = {getattr(route, "path", None) for route in app.routes}

    if (
        hasattr(fitchef_insight_router, "routes")
        and "/api/v1/insight/fitchef" not in existing_paths
    ):
        app.include_router(fitchef_insight_router)

    if not is_vip_module_enabled():
        return

    from app.routers import vip as vip_module
    from app.routers.api_key import api_key_header
    from fastapi import Depends

    # Register main VIP router (includes vip_shoplist and other VIP endpoints)
    # Route-level dependency: API key required for all VIP endpoints
    if hasattr(vip_module, "router"):
        app.include_router(
            vip_module.router,
            dependencies=[Depends(api_key_header)],
        )

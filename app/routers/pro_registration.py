# -*- coding: utf-8 -*-
"""
PRO Router Registration

RU: Централизованная регистрация PRO и premium_week роутеров.
EN: Centralized PRO and premium_week router registration.

This module provides a single entry point for registering all PRO routes
with the FastAPI application, eliminating import-side-effects and making
PRO route registration explicit and testable.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi.routing import APIRouter

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["register_pro_routes"]


def register_pro_routes(app: "FastAPI") -> tuple[APIRouter | None, APIRouter | None]:
    """
    Register PRO and premium_week routes with the FastAPI application.

    RU: Регистрирует PRO и premium_week роуты в FastAPI приложении.
    EN: Registers PRO and premium_week routes with the FastAPI application.

    This function centralizes PRO route registration logic:
    - Includes pro router (canonical /api/v1/pro/* namespace)
    - Includes premium_week router for backward compatibility (deprecated)

    Args:
        app: FastAPI application instance

    Returns:
        Tuple of (pro_router, premium_week_router) for backward compatibility.
        Both may be None if feature flags are disabled.

    Note:
        This function can be called multiple times safely (idempotent).
    """
    # Return cached values if already registered (idempotent)
    if getattr(app.state, "_pro_routes_registered", False):
        cached_pro = getattr(app.state, "_cached_pro_router", None)
        cached_premium = getattr(app.state, "_cached_premium_week_router", None)
        return cached_pro, cached_premium

    pro_router_result: APIRouter | None = None
    premium_week_router_result: APIRouter | None = None

    from app.routers.pro import router as pro_router_imported

    if pro_router_imported is not None:
        app.include_router(pro_router_imported)
        pro_router_result = pro_router_imported

    # Include PRO nutrition insights router (coverage scoring)
    from app.routers.pro_nutrition_insights import router as pro_nutrition_insights_router

    app.include_router(pro_nutrition_insights_router)
    from app.routers.pro_food_attribution import router as pro_food_attribution_router

    app.include_router(pro_food_attribution_router)

    # Include premium_week router for backward compatibility (deprecated)
    # Check FEATURE_PREMIUM_WEEK_ENABLED feature flag
    from app.utils.feature_flags import is_vip_module_enabled

    feature_premium_week_enabled = (
        os.getenv("FEATURE_PREMIUM_WEEK_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    ) or is_vip_module_enabled()  # Also enable if VIP module is enabled

    if feature_premium_week_enabled:
        from app.routers.premium_week import router as premium_week_router_imported

        # premium_week endpoints enforce tier access internally via app.middleware.api_tiers
        # (e.g., require_pro_tier). Do not add the global API_KEY guard here, otherwise
        # PRO/VIP test keys (test_pro_key/test_vip_key) are rejected when API_KEY is set.
        # NOTE: This router is deprecated. Use /api/v1/pro/* endpoints instead.
        if premium_week_router_imported is not None:
            app.include_router(premium_week_router_imported)
            premium_week_router_result = premium_week_router_imported

    # Cache routers for idempotent return.
    app.state._pro_routes_registered = True
    app.state._cached_pro_router = pro_router_result
    app.state._cached_premium_week_router = premium_week_router_result

    return pro_router_result, premium_week_router_result

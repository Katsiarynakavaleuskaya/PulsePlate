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

from app.bootstrap.route_family import (
    RouteMemberContract,
    ensure_route_family_registered,
    route_member_contracts_from_router,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["register_pro_routes"]


def _route_members_for_routers(
    family_name: str,
    routers: tuple[APIRouter, ...],
) -> tuple[RouteMemberContract, ...]:
    return tuple(
        member
        for router in routers
        for member in route_member_contracts_from_router(family_name, router)
    )


def _require_non_empty_router(
    family_name: str,
    router: object,
    module_name: str,
) -> APIRouter:
    if not isinstance(router, APIRouter) or not router.routes:
        raise RuntimeError(
            f"{family_name} router from {module_name} must be a non-empty APIRouter."
        )
    return router


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

    from app.routers.pro_session import router as pro_session_router

    from app.routers.pro_nutrition_insights import router as pro_nutrition_insights_router

    from app.routers.pro_food_attribution import router as pro_food_attribution_router

    from app.routers.pro_payments import router as pro_payments_router

    from app.routers.pro_restaurant_partner import router as pro_restaurant_partner_router

    pro_routers = (
        _require_non_empty_router("PRO", pro_router_imported, "app.routers.pro"),
        _require_non_empty_router("PRO", pro_session_router, "app.routers.pro_session"),
        _require_non_empty_router(
            "PRO",
            pro_nutrition_insights_router,
            "app.routers.pro_nutrition_insights",
        ),
        _require_non_empty_router(
            "PRO",
            pro_food_attribution_router,
            "app.routers.pro_food_attribution",
        ),
        _require_non_empty_router("PRO", pro_payments_router, "app.routers.pro_payments"),
        _require_non_empty_router(
            "PRO",
            pro_restaurant_partner_router,
            "app.routers.pro_restaurant_partner",
        ),
    )
    ensure_route_family_registered(
        app,
        family_name="PRO",
        routers=pro_routers,
        members=_route_members_for_routers("PRO", pro_routers),
    )
    pro_router_result = pro_routers[0]

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
        premium_week_router = _require_non_empty_router(
            "Premium week",
            premium_week_router_imported,
            "app.routers.premium_week",
        )
        ensure_route_family_registered(
            app,
            family_name="Premium week",
            routers=(premium_week_router,),
            members=route_member_contracts_from_router(
                "Premium week",
                premium_week_router,
            ),
        )
        premium_week_router_result = premium_week_router

    # Cache routers for idempotent return.
    app.state._pro_routes_registered = True
    app.state._cached_pro_router = pro_router_result
    app.state._cached_premium_week_router = premium_week_router_result

    return pro_router_result, premium_week_router_result

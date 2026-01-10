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

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.routing import APIRouter

__all__ = ["register_pro_routes"]


def _is_openapi_schema_only_mode() -> bool:
    """Check if OpenAPI schema-only generation mode is active.

    Schema-only mode must never activate in production by accident.
    We only honor it in generation/test context (PULSEPLATE_OPENAPI=1 AND APP_ENV=test).
    """
    _openapi_flag = (os.getenv("PULSEPLATE_OPENAPI") or "").strip()
    _app_env = (os.getenv("APP_ENV") or "").strip().lower()
    return (_openapi_flag == "1") and (_app_env == "test")


def register_pro_routes(app: FastAPI) -> tuple[APIRouter | None, APIRouter | None]:
    """
    Register PRO and premium_week routes with the FastAPI application.

    RU: Регистрирует PRO и premium_week роуты в FastAPI приложении.
    EN: Registers PRO and premium_week routes with the FastAPI application.

    This function centralizes PRO route registration logic:
    - Checks OpenAPI schema-only mode (skips routers that import SQLAlchemy models)
    - Includes premium_week router
    - Includes pro router
    - Applies route-level dependencies (API key)

    Args:
        app: FastAPI application instance

    Returns:
        Tuple of (pro_router, premium_week_router) for backward compatibility.
        Both may be None if in OpenAPI schema-only mode or feature flags disabled.

    Note:
        This function has no side effects if in OpenAPI schema-only mode.
        It can be called multiple times safely (idempotent).
    """
    if getattr(app.state, "_pro_routes_registered", False):
        # Return cached values if already registered (idempotent)
        cached_pro = getattr(app.state, "_cached_pro_router", None)
        cached_premium = getattr(app.state, "_cached_premium_week_router", None)
        return cached_pro, cached_premium

    openapi_mode = _is_openapi_schema_only_mode()

    pro_router_result: APIRouter | None = None
    premium_week_router_result: APIRouter | None = None

    if not openapi_mode:
        # Import routers only in non-schema-only mode to avoid import-time ORM hazards.
        # These routers import app.models at module level, which triggers SQLAlchemy
        # table creation and causes "Table already defined" errors on repeated imports.
        from app.routers.pro import router as pro_router_imported

        if pro_router_imported is not None:
            app.include_router(pro_router_imported)
            pro_router_result = pro_router_imported

        # Include premium_week router for backward compatibility (deprecated)
        # Check FEATURE_PREMIUM_WEEK_ENABLED feature flag
        from app.utils.feature_flags import is_vip_module_enabled

        FEATURE_PREMIUM_WEEK_ENABLED = (
            os.getenv("FEATURE_PREMIUM_WEEK_ENABLED", "").strip().lower()
            in {"1", "true", "yes", "on"}
        ) or is_vip_module_enabled()  # Also enable if VIP module is enabled

        if FEATURE_PREMIUM_WEEK_ENABLED:
            from app.routers.premium_week import router as premium_week_router_imported

            # premium_week endpoints enforce tier access internally via app.middleware.api_tiers
            # (e.g., require_pro_tier). Do not add the global API_KEY guard here, otherwise
            # PRO/VIP test keys (test_pro_key/test_vip_key) are rejected when API_KEY is set.
            # NOTE: This router is deprecated. Use /api/v1/pro/* endpoints instead.
            if premium_week_router_imported is not None:
                app.include_router(premium_week_router_imported)
                premium_week_router_result = premium_week_router_imported

    # Cache routers for idempotent return
    app.state._pro_routes_registered = True
    app.state._cached_pro_router = pro_router_result
    app.state._cached_premium_week_router = premium_week_router_result

    return pro_router_result, premium_week_router_result

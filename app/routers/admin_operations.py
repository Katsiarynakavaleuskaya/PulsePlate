"""Canonical hidden admin/debug operational routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.routers.api_key import require_app_api_key
from app.services import admin_operations as service

DEBUG_ENV_ROUTE_PATH = "/debug_env"
ADMIN_STATUS_ROUTE_PATH = "/api/v1/admin/status"
ADMIN_LOGS_CLEANUP_ROUTE_PATH = "/admin/logs/cleanup"
ADMIN_DB_STATUS_ROUTE_PATH = "/api/v1/admin/db-status"
ADMIN_FORCE_UPDATE_ROUTE_PATH = "/api/v1/admin/force-update"
ADMIN_CHECK_UPDATES_ROUTE_PATH = "/api/v1/admin/check-updates"
ADMIN_ROLLBACK_ROUTE_PATH = "/api/v1/admin/rollback"

ADMIN_OPERATION_ROUTE_SPECS: tuple[tuple[str, str], ...] = (
    (DEBUG_ENV_ROUTE_PATH, "GET"),
    (ADMIN_STATUS_ROUTE_PATH, "GET"),
    (ADMIN_LOGS_CLEANUP_ROUTE_PATH, "POST"),
    (ADMIN_DB_STATUS_ROUTE_PATH, "GET"),
    (ADMIN_FORCE_UPDATE_ROUTE_PATH, "POST"),
    (ADMIN_CHECK_UPDATES_ROUTE_PATH, "GET"),
    (ADMIN_ROLLBACK_ROUTE_PATH, "POST"),
)

router = APIRouter(tags=["admin-operations"], include_in_schema=False)


@router.get(DEBUG_ENV_ROUTE_PATH, include_in_schema=False)
async def debug_env() -> JSONResponse:
    return await service.debug_env()


@router.get(
    ADMIN_STATUS_ROUTE_PATH,
    dependencies=[Depends(require_app_api_key)],
    include_in_schema=False,
)
async def admin_status() -> dict[str, str]:
    return await service.admin_status()


@router.post(
    ADMIN_LOGS_CLEANUP_ROUTE_PATH,
    dependencies=[Depends(require_app_api_key)],
    include_in_schema=False,
)
async def cleanup_expired_logs(data_class: str | None = None) -> dict[str, Any]:
    return await service.cleanup_expired_logs(data_class=data_class)


@router.get(
    ADMIN_DB_STATUS_ROUTE_PATH,
    dependencies=[Depends(require_app_api_key)],
    include_in_schema=False,
)
async def get_database_status() -> JSONResponse:
    return await service.get_database_status()


@router.post(
    ADMIN_FORCE_UPDATE_ROUTE_PATH,
    dependencies=[Depends(require_app_api_key)],
    include_in_schema=False,
)
async def force_database_update(source: str | None = None) -> JSONResponse:
    return await service.force_database_update(source=source)


@router.get(
    ADMIN_CHECK_UPDATES_ROUTE_PATH,
    dependencies=[Depends(require_app_api_key)],
    include_in_schema=False,
)
async def check_for_updates() -> JSONResponse:
    return await service.check_for_updates()


@router.post(
    ADMIN_ROLLBACK_ROUTE_PATH,
    dependencies=[Depends(require_app_api_key)],
    include_in_schema=False,
)
async def rollback_database(source: str, target_version: str) -> dict[str, Any]:
    return await service.rollback_database(source=source, target_version=target_version)

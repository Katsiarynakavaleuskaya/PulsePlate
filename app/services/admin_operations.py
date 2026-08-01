"""Service layer for hidden admin/debug operational endpoints."""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.services.scheduler_access import get_update_scheduler
from app.utils.feature_flags import _is_truthy
from core.food_apis.scheduler_runtime import (
    UpdateLeaseContended,
    refresh_update_version_state,
    run_with_update_lease,
)
from core.log_retention import DataClass, get_retention_manager
from settings import is_explicit_developer_env

logger = logging.getLogger(__name__)


async def admin_status() -> dict[str, str]:
    """Return scheduler availability for the hidden admin status endpoint."""

    try:
        scheduler = await get_update_scheduler()
        if scheduler is None:
            raise RuntimeError("Scheduler unavailable")
        return {"status": "ok", "scheduler": "available"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Scheduler unavailable") from exc


async def cleanup_expired_logs(data_class: str | None = None) -> dict[str, Any]:
    """Cleanup expired log files based on retention policy."""

    retention_manager = get_retention_manager()

    data_class_enum = None
    if data_class is not None:
        try:
            data_class_enum = DataClass(data_class)
        except ValueError:
            return {
                "status": "error",
                "deleted_files": 0,
                "data_class": data_class,
                "message": f"Invalid data_class: '{data_class}'. Must be one of: "
                f"{', '.join([entry.value for entry in DataClass])}",
            }

    deleted_count = retention_manager.cleanup_expired_logs(data_class=data_class_enum)

    return {
        "status": "success",
        "deleted_files": deleted_count,
        "data_class": data_class or "ALL",
        "message": f"Deleted {deleted_count} expired log file(s)",
    }


async def debug_env() -> JSONResponse:
    """Return limited debug configuration in explicit developer/flagged mode only."""

    debug_flag = _is_truthy(os.getenv("ENABLE_DEBUG_ENDPOINT"))
    if not is_explicit_developer_env() and not debug_flag:
        raise HTTPException(status_code=404, detail="Not found")

    data = {
        "FEATURE_INSIGHT": os.getenv("FEATURE_INSIGHT", ""),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER", ""),
        "PERPLEXITY_MODEL": os.getenv("PERPLEXITY_MODEL", ""),
        "PERPLEXITY_ENDPOINT": os.getenv("PERPLEXITY_ENDPOINT", ""),
    }
    flag = str(os.getenv("FEATURE_INSIGHT", "")).strip().lower()
    data["insight_enabled"] = str(flag in {"1", "true", "yes", "on"})
    return JSONResponse(content=data)


async def get_database_status() -> JSONResponse:
    """Get status of all databases and update scheduler."""

    try:
        scheduler = await get_update_scheduler()
        status = scheduler.get_status()
        return JSONResponse(content=status)
    except Exception as exc:
        logger.exception("Failed to get database status")
        raise HTTPException(
            status_code=500,
            detail="Failed to get database status",
        ) from exc


async def force_database_update(source: str | None = None) -> JSONResponse:
    """Force immediate database update."""

    try:
        scheduler = await get_update_scheduler()
        results = await scheduler.force_update(source)

        response: dict[str, Any] = {
            "message": f"Force update completed for {source or 'all sources'}",
            "results": {},
        }

        for src, result in results.items():
            response["results"][src] = {
                "success": result.success,
                "old_version": result.old_version,
                "new_version": result.new_version,
                "records_added": result.records_added,
                "records_updated": result.records_updated,
                "records_removed": result.records_removed,
                "duration_seconds": result.duration_seconds,
                "errors": result.errors,
            }

        return JSONResponse(content=response)
    except UpdateLeaseContended as exc:
        logger.info("Force update skipped because another update attempt holds the lease")
        raise HTTPException(
            status_code=409,
            detail="update_already_in_progress",
        ) from exc
    except Exception as exc:
        logger.exception("Force update failed")
        raise HTTPException(status_code=500, detail="Force update failed") from exc


async def check_for_updates() -> JSONResponse:
    """Check for available updates without installing them."""

    try:
        scheduler = await get_update_scheduler()
        if scheduler is None:
            raise RuntimeError("Scheduler resolved to None")

        update_manager = getattr(scheduler, "update_manager", None)
        if update_manager is None or not hasattr(update_manager, "check_for_updates"):
            raise RuntimeError("Update manager missing or check_for_updates not supported")

        available_updates = await update_manager.check_for_updates()

        updates_available = available_updates or {}
        total_sources_with_updates = sum(1 for value in updates_available.values() if bool(value))

        response = {
            "message": "Update check completed",
            "updates_available": updates_available,
            "total_sources_with_updates": int(total_sources_with_updates),
        }

        return JSONResponse(content=response)
    except Exception as exc:
        logger.exception("Update check failed")
        raise HTTPException(status_code=500, detail="Update check failed") from exc


async def rollback_database(source: str, target_version: str) -> dict[str, Any]:
    """Rollback database to a specific version."""

    try:
        scheduler = await get_update_scheduler()
        if scheduler is None:
            raise ValueError("Scheduler returned None")
    except Exception as exc:
        logger.exception("Rollback: could not get scheduler")
        error_detail = "Rollback operation failed: could not get scheduler"
        raise HTTPException(status_code=500, detail=error_detail) from exc

    update_manager = getattr(scheduler, "update_manager", None)
    if update_manager is None:
        raise HTTPException(
            status_code=500,
            detail="No update manager available; rollback operation failed",
        )

    rollback_callable = getattr(update_manager, "rollback_database", None)
    if rollback_callable is None or not callable(rollback_callable):
        raise HTTPException(
            status_code=500,
            detail="Rollback operation not supported by update manager",
        )

    async def _run_rollback() -> Any:
        refresh_update_version_state(update_manager)
        if inspect.iscoroutinefunction(rollback_callable):
            result = await rollback_callable(source, target_version)
        else:
            result = await run_in_threadpool(rollback_callable, source, target_version)

        if inspect.isawaitable(result):
            result = await result
        return result

    try:
        success = await run_with_update_lease(_run_rollback)
    except UpdateLeaseContended as exc:
        logger.info("Rollback skipped because another update attempt holds the lease")
        raise HTTPException(
            status_code=409,
            detail="update_already_in_progress",
        ) from exc
    except Exception as exc:
        logger.exception("Rollback callable raised")
        error_msg = "Rollback operation failed; Rollback failed; see server logs for details"
        raise HTTPException(status_code=500, detail=error_msg) from exc

    if success:
        return {
            "message": f"Successfully rolled back {source} to version {target_version}",
            "success": True,
        }

    error_detail = f"Rollback operation failed for {source} to version {target_version}"
    raise HTTPException(status_code=500, detail=error_detail)

"""Canonical application access to the optional database update scheduler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.food_apis.scheduler import DatabaseUpdateScheduler


async def get_update_scheduler() -> DatabaseUpdateScheduler:
    """Return the core-owned scheduler without making it a startup dependency."""

    from core.food_apis.scheduler import get_update_scheduler as core_get_update_scheduler

    return await core_get_update_scheduler()


__all__ = ["get_update_scheduler"]

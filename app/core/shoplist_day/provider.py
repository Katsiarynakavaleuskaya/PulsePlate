"""Provider hook for fetching day plan data.

PR-3: Real DB integration for day plan retrieval.
Uses lazy imports to avoid ORM registration side-effects at module import time.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional


async def fetch_day_plan(day: date, pro_ctx: Any) -> Optional[dict]:
    """Fetch day plan for a given date and PRO context.

    PR-3: Queries day_plans table for the given date.
    Uses lazy imports to avoid ORM registration at app import time.

    Args:
        day: Date to fetch plan for
        pro_ctx: PRO tier context (contains user info)

    Returns:
        Plan data dict with daily_menus format, or None if not found
    """
    # Extract user_id from PRO context
    if isinstance(pro_ctx, dict):
        user_id = pro_ctx.get("user_id")
    else:
        user_id = getattr(pro_ctx, "user_id", None)

    if user_id is None:
        # No user_id in context, return None (no plan available)
        return None

    # Lazy imports to avoid ORM side-effects at module import time
    from sqlalchemy import select

    from app.models import DayPlan
    from core.db import session_scope_async

    # Query DB for day plan
    try:
        async with session_scope_async() as session:
            stmt = select(DayPlan).where(DayPlan.user_id == user_id).where(DayPlan.date == day)
            result = await session.execute(stmt)
            day_plan = result.scalars().first()

        if day_plan is None:
            return None

        # Return plan_data from DB (already in daily_menus format)
        return day_plan.plan_data
    except (RuntimeError, ImportError):
        # RU: Async DB не настроен/недоступен — для MVP считаем, что плана нет.
        # EN: Async DB not configured/available — treat as "no plan" for MVP.
        return None

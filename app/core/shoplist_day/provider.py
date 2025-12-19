"""Provider hook for fetching day plan data.

PR-3: Real DB integration for day plan retrieval.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import select

from app.models.plans import DayPlan
from core.db import session_scope_async


async def fetch_day_plan(day: date, pro_ctx: Any) -> Optional[dict]:
    """Fetch day plan for a given date and PRO context.

    PR-3: Queries day_plans table for the given date.

    Args:
        day: Date to fetch plan for
        pro_ctx: PRO tier context (contains user info)

    Returns:
        Plan data dict with daily_menus format, or None if not found
    """
    # Extract user_id from PRO context (placeholder: assume dict-like)
    user_id = (
        getattr(pro_ctx, "user_id", None) or pro_ctx.get("user_id")
        if isinstance(pro_ctx, dict)
        else None
    )

    if user_id is None:
        # No user_id in context, return None (no plan available)
        return None

    # Query DB for day plan
    async with session_scope_async() as session:
        stmt = select(DayPlan).where(DayPlan.user_id == user_id).where(DayPlan.date == day)
        result = await session.execute(stmt)
        day_plan = result.scalars().first()

    if day_plan is None:
        return None

    # Return plan_data from DB (already in daily_menus format)
    return day_plan.plan_data

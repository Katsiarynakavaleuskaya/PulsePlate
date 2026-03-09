"""FitChef runtime test helpers. / Вспомогательные helpers для тестов FitChef runtime."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def make_mock_run_weekly_plan_task(
    *,
    menu: dict[str, Any] | None = None,
    capture: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Build async weekly runtime mock. / Собрать async mock для weekly runtime."""

    async def _mock_run_weekly_plan_task(task, *, menu_builder):
        if capture is not None:
            capture["task_type"] = task.task_type
            capture["menu_builder"] = menu_builder
        payload = {"days": []} if menu is None else menu
        return type("WeeklyPlanResult", (), {"menu": payload})()

    return _mock_run_weekly_plan_task


def make_mock_run_shopping_followup_task(
    *,
    shopping_list: dict[str, Any] | None = None,
    capture: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Build async shopping runtime mock. / Собрать async mock для shopping runtime."""

    async def _mock_run_shopping_followup_task(task, *, shopping_list_builder):
        if capture is not None:
            capture["task_type"] = task.task_type
            capture["shopping_list_builder"] = shopping_list_builder
            capture["plan_data"] = task.input.plan_data
            capture["preferences"] = task.input.preferences
        payload = (
            {
                "categories": [],
                "total_items": 0,
                "generated_at": "2025-01-01T00:00:00Z",
                "meta": {
                    "source": "inline_plan",
                    "unit_system": "metric",
                    "warnings": [],
                },
            }
            if shopping_list is None
            else shopping_list
        )
        return type("ShoppingFollowupResult", (), {"shopping_list": payload})()

    return _mock_run_shopping_followup_task

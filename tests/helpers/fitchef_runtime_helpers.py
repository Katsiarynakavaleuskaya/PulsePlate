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

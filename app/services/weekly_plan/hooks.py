# -*- coding: utf-8 -*-
"""
RU: Интерфейс хуков для weekly plan pipeline (no-op по умолчанию).
EN: Hooks interface for weekly plan pipeline (default no-op).

Design:
- Stable interface for future analytics / explainability / repair.
- No runtime wiring in PR-10: interface only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class WeeklyPlanEvent:
    """
    RU: Событие пайплайна weekly plan.
    EN: Weekly plan pipeline event.
    """

    stage: str
    code: str
    message: str
    meta: Mapping[str, Any] | None = None


class WeeklyPlanHook(Protocol):
    """
    RU: Контракт хуков. Реализации не должны кидать исключения.
    EN: Hooks contract. Implementations should not raise.
    """

    def on_success(self, event: WeeklyPlanEvent) -> None: ...

    def on_error(self, event: WeeklyPlanEvent) -> None: ...


class NullWeeklyPlanHook:
    """
    RU: Default no-op hook.
    EN: Default no-op hook.
    """

    def on_success(self, event: WeeklyPlanEvent) -> None:
        pass

    def on_error(self, event: WeeklyPlanEvent) -> None:
        pass


NULL_WEEKLY_PLAN_HOOK = NullWeeklyPlanHook()

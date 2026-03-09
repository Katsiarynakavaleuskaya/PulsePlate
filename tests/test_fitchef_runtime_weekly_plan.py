"""FitChef weekly-plan runtime tests. / Тесты weekly-plan runtime FitChef."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.schemas.fitchef import FitChefWeeklyPlanInput, FitChefWeeklyPlanTaskEnvelope
from app.services import fitchef_runtime


def test_run_weekly_plan_task_returns_echo_when_builder_missing() -> None:
    """Missing builder falls back to echo mode. / Отсутствующий builder даёт echo mode."""

    task = FitChefWeeklyPlanTaskEnvelope(
        mode="auto-safe",
        input=FitChefWeeklyPlanInput(request_data={"calories": 2000}),
    )

    result = asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            task,
            menu_builder=None,
        )
    )

    assert result.menu == {"mode": "echo"}


def test_run_weekly_plan_task_serializes_menu_and_builds_profile_defaults() -> None:
    """Weekly runtime serializes output and preserves profile defaults. / Runtime сериализует меню и хранит fallback."""

    captured: dict[str, object] = {}

    def fake_menu_builder(profile):
        captured["profile"] = profile
        return SimpleNamespace(
            week_start="2026-03-09",
            daily_menus=[],
            weekly_coverage={"protein": 1.0},
            shopping_list=[],
            total_cost=42.0,
            adherence_score=0.85,
        )

    task = FitChefWeeklyPlanTaskEnvelope(
        mode="auto-safe",
        input=FitChefWeeklyPlanInput(
            request_data={
                "sex": "female",
                "age": 29,
                "height_cm": 168.0,
                "weight_kg": 58.0,
                "activity": "active",
                "goal": "maintain",
                "diet_flags": ["VEG"],
                "medical_conditions": ["iron_deficiency"],
            }
        ),
    )

    result = asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            task,
            menu_builder=fake_menu_builder,
        )
    )

    profile = captured["profile"]
    assert getattr(profile, "sex") == "female"
    assert getattr(profile, "diet_flags") == {"VEG"}
    assert getattr(profile, "medical_conditions") == {"iron_deficiency"}
    assert result.menu["week_start"] == "2026-03-09"
    assert result.menu["weekly_coverage"] == {"protein": 1.0}


def test_run_weekly_plan_task_uses_safe_numeric_fallbacks() -> None:
    """Invalid numeric input falls back safely. / Неверные numeric поля переходят на safe fallback."""

    captured: dict[str, object] = {}

    def fake_menu_builder(profile):
        captured["profile"] = profile
        return {"days": []}

    task = FitChefWeeklyPlanTaskEnvelope(
        mode="auto-safe",
        input=FitChefWeeklyPlanInput(
            request_data={
                "sex": "male",
                "age": "bad-age",
                "height_cm": "bad-height",
                "weight_kg": "bad-weight",
                "activity": "moderate",
                "goal": "maintain",
            }
        ),
    )

    result = asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            task,
            menu_builder=fake_menu_builder,
        )
    )

    profile = captured["profile"]
    assert getattr(profile, "age") == 30
    assert getattr(profile, "height_cm") == 175.0
    assert getattr(profile, "weight_kg") == 70.0
    assert result.menu == {"days": []}


def test_run_weekly_plan_task_falls_back_when_builder_returns_none_or_non_dict() -> None:
    """Weekly runtime falls back to echo mode. / Weekly runtime откатывается в echo mode."""

    task = FitChefWeeklyPlanTaskEnvelope(
        mode="auto-safe",
        input=FitChefWeeklyPlanInput(request_data={"calories": 1800}),
    )

    none_result = asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            task,
            menu_builder=lambda profile: None,
        )
    )
    list_result = asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            task,
            menu_builder=lambda profile: ["not", "a", "dict"],
        )
    )

    assert none_result.menu == {"mode": "echo"}
    assert list_result.menu == {"mode": "echo"}

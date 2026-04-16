"""Deterministic tests for intervention trigger engine v1."""

from app.services.intervention_trigger_engine import (
    build_post_bmi_next_action,
    build_targets_next_action,
    build_weekly_plan_next_action,
)


def test_build_post_bmi_next_action_returns_unlock_targets() -> None:
    action = build_post_bmi_next_action(bmi=24.1)
    assert action is not None
    assert action.type == "unlock_targets"
    assert action.recommended_tier == "PRO"


def test_build_targets_next_action_returns_open_daily_plate() -> None:
    action = build_targets_next_action(kcal_daily=2100)
    assert action is not None
    assert action.type == "open_daily_plate"
    assert action.recommended_surface == "/api/v1/pro/nutrition/daily"


def test_build_weekly_plan_next_action_returns_upgrade_for_export() -> None:
    action = build_weekly_plan_next_action(daily_menu_count=7)
    assert action is not None
    assert action.type == "upgrade_for_export"
    assert action.recommended_tier == "VIP"


def test_intervention_engine_fail_closed_for_missing_context() -> None:
    assert build_post_bmi_next_action(bmi=None) is None
    assert build_targets_next_action(kcal_daily=None) is None
    assert build_weekly_plan_next_action(daily_menu_count=0) is None

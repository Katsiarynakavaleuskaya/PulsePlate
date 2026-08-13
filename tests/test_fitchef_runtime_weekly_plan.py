"""FitChef weekly-plan runtime tests. / Тесты weekly-plan runtime FitChef."""

from __future__ import annotations

import asyncio
import math
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

import core.targets as core_targets
from app.schemas.fitchef import FitChefWeeklyPlanInput, FitChefWeeklyPlanTaskEnvelope
from app.services import fitchef_runtime


def _valid_request_data() -> dict[str, Any]:
    return {
        "sex": "female",
        "age": 29,
        "height_cm": 168.0,
        "weight_kg": 58.0,
        "activity": "active",
        "goal": "maintain",
    }


def _weekly_task(request_data: dict[str, Any]) -> FitChefWeeklyPlanTaskEnvelope:
    return FitChefWeeklyPlanTaskEnvelope(
        mode="auto-safe",
        input=FitChefWeeklyPlanInput(request_data=request_data),
    )


def test_core_weekly_profile_fields_are_canonical_and_ordered() -> None:
    assert fitchef_runtime.CORE_WEEKLY_PROFILE_FIELDS == (
        "sex",
        "age",
        "height_cm",
        "weight_kg",
        "activity",
        "goal",
    )


def test_require_weekly_profile_input_returns_stable_top_level_snapshot() -> None:
    source = {
        **_valid_request_data(),
        "calories": 2100,
        "protein": 120.0,
        "protein_g": 121.0,
    }

    checked = fitchef_runtime._require_weekly_profile_input(source)
    source["age"] = 99

    assert checked is not source
    assert checked["age"] == 29
    assert checked["calories"] == 2100
    assert checked["protein"] == 120.0
    assert checked["protein_g"] == 121.0


def test_weekly_profile_input_error_is_ordered_and_never_leaks_values() -> None:
    payload = {
        "age": "private-age-90210",
        "weight_kg": math.inf,
        "goal": "private-goal-value",
    }

    with pytest.raises(fitchef_runtime.WeeklyProfileInputError) as exc_info:
        fitchef_runtime._require_weekly_profile_input(payload)

    error = exc_info.value
    assert error.missing_fields == ("sex", "height_cm", "activity")
    assert error.invalid_fields == ("age", "weight_kg", "goal")
    serialized_error = f"{str(error)} {repr(error)} {error.args!r}"
    assert "private-age-90210" not in serialized_error
    assert "private-goal-value" not in serialized_error
    assert "inf" not in serialized_error


@pytest.mark.parametrize("field", fitchef_runtime.CORE_WEEKLY_PROFILE_FIELDS)
@pytest.mark.parametrize(
    "supplements",
    (
        {},
        {"calories": 2100},
        {"protein": 120.0},
        {"calories": 2100, "protein": 120.0},
        {"protein_g": 121.0},
        {"calories": 2100, "protein_g": 121.0},
    ),
    ids=(
        "none",
        "calories",
        "protein",
        "calories-and-protein",
        "protein-g",
        "calories-and-protein-g",
    ),
)
def test_run_weekly_plan_task_rejects_each_missing_field_before_builder(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    supplements: dict[str, Any],
) -> None:
    threadpool_spy = Mock(side_effect=AssertionError("threadpool must not run"))
    profile_spy = Mock(side_effect=AssertionError("UserProfile must not be constructed"))
    builder_spy = Mock(side_effect=AssertionError("builder must not run"))
    monkeypatch.setattr(fitchef_runtime, "run_in_threadpool", threadpool_spy)
    monkeypatch.setattr(core_targets, "UserProfile", profile_spy)
    request_data = {**_valid_request_data(), **supplements}
    del request_data[field]

    with pytest.raises(fitchef_runtime.WeeklyProfileInputError) as exc_info:
        asyncio.run(
            fitchef_runtime.run_weekly_plan_task(
                _weekly_task(request_data),
                menu_builder=builder_spy,
            )
        )

    assert exc_info.value.missing_fields == (field,)
    assert exc_info.value.invalid_fields == ()
    threadpool_spy.assert_not_called()
    profile_spy.assert_not_called()
    builder_spy.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sex", None),
        ("sex", ""),
        ("sex", "Female"),
        ("sex", "female "),
        ("sex", "unknown"),
        ("age", None),
        ("age", True),
        ("age", False),
        ("age", 0),
        ("age", -1),
        ("age", 121),
        ("age", 29.0),
        ("age", "29"),
        ("height_cm", None),
        ("height_cm", True),
        ("height_cm", 0),
        ("height_cm", -1),
        ("height_cm", 300.1),
        ("height_cm", "168.0"),
        ("height_cm", math.nan),
        ("height_cm", math.inf),
        ("height_cm", -math.inf),
        ("weight_kg", None),
        ("weight_kg", False),
        ("weight_kg", 0),
        ("weight_kg", -1),
        ("weight_kg", 500.1),
        ("weight_kg", "58.0"),
        ("weight_kg", math.nan),
        ("weight_kg", math.inf),
        ("weight_kg", -math.inf),
        ("activity", None),
        ("activity", ""),
        ("activity", "Moderate"),
        ("activity", "moderate "),
        ("activity", "unknown"),
        ("goal", None),
        ("goal", ""),
        ("goal", "Maintain"),
        ("goal", "maintain "),
        ("goal", "unknown"),
    ),
)
def test_run_weekly_plan_task_rejects_present_invalid_direct_values_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    threadpool_spy = Mock(side_effect=AssertionError("threadpool must not run"))
    profile_spy = Mock(side_effect=AssertionError("UserProfile must not be constructed"))
    builder_spy = Mock(side_effect=AssertionError("builder must not run"))
    monkeypatch.setattr(fitchef_runtime, "run_in_threadpool", threadpool_spy)
    monkeypatch.setattr(core_targets, "UserProfile", profile_spy)
    request_data = _valid_request_data()
    request_data[field] = value

    with pytest.raises(fitchef_runtime.WeeklyProfileInputError) as exc_info:
        asyncio.run(
            fitchef_runtime.run_weekly_plan_task(
                _weekly_task(request_data),
                menu_builder=builder_spy,
            )
        )

    assert exc_info.value.missing_fields == ()
    assert exc_info.value.invalid_fields == (field,)
    threadpool_spy.assert_not_called()
    profile_spy.assert_not_called()
    builder_spy.assert_not_called()


def test_build_weekly_user_profile_public_helper_rejects_direct_numeric_string() -> None:
    request_data = {**_valid_request_data(), "age": "29"}

    with pytest.raises(fitchef_runtime.WeeklyProfileInputError) as exc_info:
        fitchef_runtime.build_weekly_user_profile(request_data)

    assert exc_info.value.missing_fields == ()
    assert exc_info.value.invalid_fields == ("age",)


@pytest.mark.parametrize(
    "request_data",
    (
        {"profile": _valid_request_data()},
        {
            "Sex": "female",
            "Age": 29,
            "Height_cm": 168.0,
            "Weight_kg": 58.0,
            "Activity": "active",
            "Goal": "maintain",
        },
        {
            "sex_type": "female",
            "age_years": 29,
            "height": 168.0,
            "weight": 58.0,
            "activity_level": "active",
            "goal_type": "maintain",
        },
    ),
    ids=("nested", "case-variants", "lookalikes"),
)
def test_require_weekly_profile_input_uses_exact_canonical_top_level_keys(
    request_data: dict[str, Any],
) -> None:
    with pytest.raises(fitchef_runtime.WeeklyProfileInputError) as exc_info:
        fitchef_runtime._require_weekly_profile_input(request_data)

    assert exc_info.value.missing_fields == fitchef_runtime.CORE_WEEKLY_PROFILE_FIELDS
    assert exc_info.value.invalid_fields == ()


def test_run_weekly_plan_task_rejects_incomplete_input_even_without_builder() -> None:
    request_data = _valid_request_data()
    del request_data["goal"]

    with pytest.raises(fitchef_runtime.WeeklyProfileInputError) as exc_info:
        asyncio.run(
            fitchef_runtime.run_weekly_plan_task(
                _weekly_task(request_data),
                menu_builder=None,
            )
        )

    assert exc_info.value.missing_fields == ("goal",)


def test_run_weekly_plan_task_returns_echo_for_complete_input_without_builder() -> None:
    result = asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            _weekly_task(_valid_request_data()),
            menu_builder=None,
        )
    )

    assert result.menu == {"mode": "echo"}


def test_run_weekly_plan_task_builds_exact_profile_once_and_serializes_menu() -> None:
    captured: dict[str, Any] = {"builder_calls": 0}

    def fake_menu_builder(profile: object) -> SimpleNamespace:
        captured["builder_calls"] += 1
        captured["profile"] = profile
        return SimpleNamespace(
            week_start="2026-03-09",
            daily_menus=[],
            weekly_coverage={"protein": 1.0},
            shopping_list=[],
            total_cost=42.0,
            adherence_score=0.85,
        )

    request_data = {
        **_valid_request_data(),
        "diet_flags": ["VEG"],
        "medical_conditions": ["iron_deficiency"],
        "region": "US",
        "timezone": "Europe/Minsk",
        "life_stage": "adult",
    }
    result = asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            _weekly_task(request_data),
            menu_builder=fake_menu_builder,
        )
    )

    profile = captured["profile"]
    assert captured["builder_calls"] == 1
    assert getattr(profile, "sex") == request_data["sex"]
    assert getattr(profile, "age") == request_data["age"]
    assert getattr(profile, "height_cm") == request_data["height_cm"]
    assert getattr(profile, "weight_kg") == request_data["weight_kg"]
    assert getattr(profile, "activity") == request_data["activity"]
    assert getattr(profile, "goal") == request_data["goal"]
    assert getattr(profile, "diet_flags") == {"VEG"}
    assert getattr(profile, "medical_conditions") == {"iron_deficiency"}
    assert getattr(profile, "region") == "US"
    assert getattr(profile, "timezone") == "Europe/Minsk"
    assert getattr(profile, "life_stage") == "adult"
    assert result.menu["week_start"] == "2026-03-09"
    assert result.menu["weekly_coverage"] == {"protein": 1.0}


def test_run_weekly_plan_task_preserves_set_inputs() -> None:
    captured: dict[str, object] = {}

    def fake_menu_builder(profile: object) -> dict[str, Any]:
        captured["profile"] = profile
        return {"days": []}

    request_data = {
        **_valid_request_data(),
        "diet_flags": {"VEG"},
        "medical_conditions": {"iron_deficiency"},
    }
    asyncio.run(
        fitchef_runtime.run_weekly_plan_task(
            _weekly_task(request_data),
            menu_builder=fake_menu_builder,
        )
    )

    profile = captured["profile"]
    assert getattr(profile, "diet_flags") == {"VEG"}
    assert getattr(profile, "medical_conditions") == {"iron_deficiency"}


def test_run_weekly_plan_task_falls_back_when_builder_returns_none_or_non_dict() -> None:
    task = _weekly_task(_valid_request_data())

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


def test_run_weekly_plan_task_propagates_builder_exceptions() -> None:
    def failing_menu_builder(profile: object) -> None:
        raise RuntimeError("weekly builder exploded")

    with pytest.raises(RuntimeError, match="weekly builder exploded") as exc_info:
        asyncio.run(
            fitchef_runtime.run_weekly_plan_task(
                _weekly_task(_valid_request_data()),
                menu_builder=failing_menu_builder,
            )
        )

    assert str(exc_info.value) == "weekly builder exploded"

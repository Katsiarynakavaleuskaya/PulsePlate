"""FitChef shopping-followup runtime tests. / Тесты shopping-followup runtime FitChef."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.schemas.fitchef import (
    FitChefShoppingFollowupInput,
    FitChefShoppingFollowupTaskEnvelope,
)
from app.schemas.shopping_list import ShoppingListDTO, ShoppingListPreferences
from app.services import fitchef_runtime


def _make_shopping_list_dto() -> ShoppingListDTO:
    """Build deterministic shopping DTO. / Собрать детерминированный shopping DTO."""

    dto: ShoppingListDTO
    dto = ShoppingListDTO.model_validate(
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
    )
    return dto


def test_run_shopping_followup_task_delegates_builder() -> None:
    """Shopping runtime delegates builder. / Shopping runtime делегирует builder."""

    captured: dict[str, object] = {}
    task = FitChefShoppingFollowupTaskEnvelope(
        mode="auto-safe",
        input=FitChefShoppingFollowupInput(
            plan_data={"daily_menus": []},
            preferences=ShoppingListPreferences(),
        ),
    )

    def fake_builder(*, plan_data, preferences, source):
        captured["plan_data"] = plan_data
        captured["preferences"] = preferences
        captured["source"] = source
        return _make_shopping_list_dto()

    result = asyncio.run(
        fitchef_runtime.run_shopping_followup_task(
            task,
            shopping_list_builder=fake_builder,
        )
    )

    assert captured["plan_data"] == {"daily_menus": []}
    assert captured["source"] == "inline_plan"
    assert isinstance(captured["preferences"], ShoppingListPreferences)
    assert result.shopping_list.meta.source == "inline_plan"


def test_run_shopping_followup_task_rejects_missing_plan_data() -> None:
    """Missing plan_data fails closed. / Отсутствующий plan_data закрывается fail-closed."""

    task = FitChefShoppingFollowupTaskEnvelope(
        mode="auto-safe",
        input=FitChefShoppingFollowupInput(
            plan_data=None,
            preferences=ShoppingListPreferences(),
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            fitchef_runtime.run_shopping_followup_task(
                task,
                shopping_list_builder=lambda **_kwargs: _make_shopping_list_dto(),
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal error: plan_data is None"


def test_run_shopping_followup_task_propagates_builder_exceptions() -> None:
    """Builder exceptions propagate. / Исключения builder проходят наружу как есть."""

    task = FitChefShoppingFollowupTaskEnvelope(
        mode="auto-safe",
        input=FitChefShoppingFollowupInput(
            plan_data={"daily_menus": []},
            preferences=ShoppingListPreferences(),
        ),
    )

    def failing_builder(**_kwargs):
        raise RuntimeError("shopping builder exploded")

    with pytest.raises(RuntimeError, match="shopping builder exploded") as exc_info:
        asyncio.run(
            fitchef_runtime.run_shopping_followup_task(
                task,
                shopping_list_builder=failing_builder,
            )
        )

    assert str(exc_info.value) == "shopping builder exploded"

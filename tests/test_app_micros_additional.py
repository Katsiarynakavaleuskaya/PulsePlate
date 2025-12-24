from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import app


def test_convert_db_nutrients_to_alias_format_success() -> None:
    data = {"Fe_mg": 2.5, "Ca_mg": 150, "custom": 3}
    result = app._convert_db_nutrients_to_alias_format(data)
    assert result["iron_mg"] == 2.5
    assert result["calcium_mg"] == 150
    assert result["custom"] == 3


def test_convert_db_nutrients_none_value() -> None:
    with pytest.raises(ValueError):
        app._convert_db_nutrients_to_alias_format({"Fe_mg": None})


def test_convert_db_nutrients_invalid_value() -> None:
    with pytest.raises(ValueError):
        app._convert_db_nutrients_to_alias_format({"Fe_mg": object()})


@pytest.mark.asyncio
async def test_aggregate_meal_micronutrients_various(monkeypatch: pytest.MonkeyPatch) -> None:
    collected_calls: List[Dict[str, Any]] = []

    foods = {
        "valid": {
            "per_g": 50,
            "Fe_mg": 1.0,
            "Ca_mg": 2.0,
            "K_mg": 3.0,
            "Mg_mg": 4.0,
            "VitD_IU": 5.0,
            "B12_ug": 6.0,
            "Folate_ug": 7.0,
            "Iodine_ug": 8.0,
        },
        "bad_per_g": {"per_g": "oops"},
        "zero_per_g": {"per_g": 0, "Fe_mg": 1.0},
        "bad_micro": {"per_g": 100, "Fe_mg": "bad-value"},
    }

    async def fake_to_thread(func, *args, **kwargs):
        collected_calls.append({"func": func, "args": args, "kwargs": kwargs})
        food_id = args[0]
        if food_id == "raise":
            raise RuntimeError("boom")
        return foods.get(food_id)

    monkeypatch.setattr(app.asyncio, "to_thread", fake_to_thread)

    ingredients = [
        {"grams": 10},  # missing food_id -> skip
        {"food_id": "valid", "grams": "not-number"},  # invalid grams -> skip
        {"food_id": "valid", "grams": -5},  # non-positive grams -> skip
        {"food_id": "missing", "grams": 10},  # missing food -> skip
        {"food_id": "bad_per_g", "grams": 10},  # invalid per_g -> uses default
        {"food_id": "zero_per_g", "grams": 10},  # zero per_g -> default
        {"food_id": "bad_micro", "grams": 10},  # invalid nutrient value
        {"food_id": "raise", "grams": 5},  # exception path
        {"food_id": "valid", "grams": 25},  # valid path
    ]

    result = await app._aggregate_meal_micronutrients(ingredients, meal_title="Test")
    assert "iron_mg" in result
    assert collected_calls  # ensured to_thread invoked


def test_get_recipe_ingredients_for_meal_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    recipe_data = {
        "ingredients_json": json.dumps(
            [
                {"food_id": "f1", "grams": 100},
                {"id": "f2", "grams": 50},
                ["f3", 25],
            ]
        )
    }

    monkeypatch.setattr(
        app.recipe_store, "search_recipes", lambda title, limit=1: [{"recipe_id": "r1"}]
    )
    monkeypatch.setattr(app.recipe_store, "get_recipe", lambda recipe_id: recipe_data)

    ingredients = app._get_recipe_ingredients_for_meal("Soup")
    assert len(ingredients) == 3
    assert ingredients[0]["food_id"] == "f1"
    assert ingredients[2]["grams"] == 25


def test_get_recipe_ingredients_for_meal_no_recipe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.recipe_store, "search_recipes", lambda *args, **kwargs: [])
    assert app._get_recipe_ingredients_for_meal("None") == []


def test_get_recipe_ingredients_missing_recipe_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.recipe_store, "search_recipes", lambda *args, **kwargs: [{}])
    assert app._get_recipe_ingredients_for_meal("Soup") == []


def test_get_recipe_ingredients_recipe_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.recipe_store, "search_recipes", lambda *args, **kwargs: [{"recipe_id": "r1"}]
    )
    monkeypatch.setattr(app.recipe_store, "get_recipe", lambda recipe_id: None)
    assert app._get_recipe_ingredients_for_meal("Soup") == []


def test_get_recipe_ingredients_missing_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.recipe_store, "search_recipes", lambda *args, **kwargs: [{"recipe_id": "r1"}]
    )
    monkeypatch.setattr(app.recipe_store, "get_recipe", lambda recipe_id: {})
    assert app._get_recipe_ingredients_for_meal("Soup") == []


def test_get_recipe_ingredients_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app.recipe_store, "search_recipes", lambda *args, **kwargs: [{"recipe_id": "r1"}]
    )
    monkeypatch.setattr(
        app.recipe_store, "get_recipe", lambda recipe_id: {"ingredients_json": "{}"}
    )
    assert app._get_recipe_ingredients_for_meal("Soup") == []


@pytest.mark.asyncio
async def test_aggregate_day_micronutrients(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_aggregate(
        ingredients: List[Dict[str, Any]], meal_title: str = ""
    ) -> Dict[str, float]:
        assert meal_title == "Meal B"
        return {"iron_mg": 1.0}

    app_module = getattr(app, "app_module", None)

    monkeypatch.setattr(app, "_aggregate_meal_micronutrients", fake_aggregate)
    if app_module is not None:
        monkeypatch.setattr(app_module, "_aggregate_meal_micronutrients", fake_aggregate)

    def fake_lookup(title: str) -> List[Dict[str, Any]]:
        return [{"food_id": "x", "grams": 10}]

    # Mock asyncio.to_thread to call _get_recipe_ingredients_for_meal directly
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(app, "_get_recipe_ingredients_for_meal", fake_lookup)
    if app_module is not None:
        monkeypatch.setattr(app_module, "_get_recipe_ingredients_for_meal", fake_lookup)

    meals = [
        {"title": "Meal A", "micros": {"iron_mg": 0.5}},
        {"title": "Meal B"},  # No ingredients, will call _get_recipe_ingredients_for_meal
    ]

    result = await app._aggregate_day_micronutrients(meals)
    # Only Meal A has micros (0.5), Meal B has no recipe so contributes 0
    assert result["iron_mg"] == pytest.approx(0.5)


def test_alias_micros_type_error() -> None:
    with pytest.raises(TypeError):
        app._alias_micros(["not", "a", "dict"])  # type: ignore[arg-type]


def test_alias_micros_value_error() -> None:
    with pytest.raises(ValueError):
        app._alias_micros({"iron_mg": object()})


def test_alias_micros_aliases() -> None:
    result = app._alias_micros({"iron_mg": 2})
    assert result["iron"] == 2.0
    assert result["fe"] == 2.0

"""Critical Plate micronutrient boundary tests."""

from __future__ import annotations

import asyncio
from decimal import Decimal
import json
from types import SimpleNamespace
from typing import Any, Dict, List

import numpy as np
import pytest

from app.services import pro_nutrition_plate as plate_service


def test_convert_db_nutrients_to_alias_format_success() -> None:
    data = {"Fe_mg": 2.5, "Ca_mg": 150, "custom": 3}
    result = plate_service._convert_db_nutrients_to_alias_format(data)
    assert result["iron_mg"] == 2.5
    assert result["calcium_mg"] == 150
    assert result["custom"] == 3


def test_convert_db_nutrients_none_value() -> None:
    with pytest.raises(ValueError):
        plate_service._convert_db_nutrients_to_alias_format({"Fe_mg": None})


def test_convert_db_nutrients_invalid_value() -> None:
    with pytest.raises(ValueError):
        plate_service._convert_db_nutrients_to_alias_format({"Fe_mg": object()})


def test_convert_db_nutrients_rejects_boolean_measurement() -> None:
    with pytest.raises(ValueError):
        plate_service._convert_db_nutrients_to_alias_format({"Fe_mg": True})


@pytest.mark.parametrize(
    "non_finite_value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
    ids=[
        "float-nan",
        "float-positive-infinity",
        "float-negative-infinity",
        "decimal-nan",
        "decimal-positive-infinity",
        "decimal-negative-infinity",
    ],
)
def test_convert_db_nutrients_rejects_non_finite_values(
    non_finite_value: Any,
) -> None:
    with pytest.raises(plate_service._NonFinitePlateDependencyOutputError):
        plate_service._convert_db_nutrients_to_alias_format({"Fe_mg": non_finite_value})


@pytest.mark.parametrize(
    "non_finite_value",
    [np.float16("nan"), np.float32("inf"), np.float32("-inf")],
    ids=["float16-nan", "float32-positive-infinity", "float32-negative-infinity"],
)
def test_finite_dependency_guard_rejects_numpy_scalars(
    non_finite_value: Any,
) -> None:
    with pytest.raises(plate_service._NonFinitePlateDependencyOutputError):
        plate_service._ensure_finite_dependency_output(non_finite_value)


def test_aggregate_meal_micronutrients_rejects_non_finite_food_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _food_from_db(
        _func: object,
        *_args: object,
        **_kwargs: object,
    ) -> dict[str, float]:
        return {"per_g": 100.0, "Fe_mg": float("inf")}

    monkeypatch.setattr(plate_service.asyncio, "to_thread", _food_from_db)

    with pytest.raises(plate_service._NonFinitePlateDependencyOutputError):
        asyncio.run(
            plate_service._aggregate_meal_micronutrients(
                [{"food_id": "db-food", "grams": 100}],
                meal_title="Meal",
            )
        )


@pytest.mark.parametrize(
    "non_finite_value",
    [float("-inf"), Decimal("NaN"), Decimal("Infinity")],
    ids=["float-negative-infinity", "decimal-nan", "decimal-infinity"],
)
def test_aggregate_day_micronutrients_rejects_existing_non_finite_meal_micros(
    non_finite_value: Any,
) -> None:
    meals = [
        {
            "title": "Meal",
            "micros": {"iron_mg": non_finite_value},
        }
    ]

    with pytest.raises(plate_service._NonFinitePlateDependencyOutputError):
        asyncio.run(plate_service._aggregate_day_micronutrients(meals))


def test_aggregate_meal_micronutrients_various(monkeypatch: pytest.MonkeyPatch) -> None:
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
    }

    async def fake_to_thread(func, *args, **kwargs):
        collected_calls.append({"func": func, "args": args, "kwargs": kwargs})
        food_id = args[0]
        return foods.get(food_id)

    monkeypatch.setattr(plate_service.asyncio, "to_thread", fake_to_thread)

    ingredients = [
        {"grams": 10},  # missing food_id -> skip
        {"food_id": "valid", "grams": 0},  # zero quantity -> no evidence
        {"food_id": "missing", "grams": 10},  # missing food -> skip
        {"food_id": "valid", "grams": 25},  # valid path
    ]

    result = asyncio.run(
        plate_service._aggregate_meal_micronutrients(
            ingredients,
            meal_title="Test",
        )
    )
    assert "iron_mg" in result
    assert collected_calls  # ensured to_thread invoked


def test_aggregate_meal_micronutrients_preserves_only_available_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _sparse_food_from_db(
        _func: object,
        *_args: object,
        **_kwargs: object,
    ) -> dict[str, object]:
        return {
            "per_g": 100,
            "Fe_mg": None,
            "Ca_mg": 0,
            "K_mg": 10,
        }

    monkeypatch.setattr(plate_service.asyncio, "to_thread", _sparse_food_from_db)

    result = asyncio.run(
        plate_service._aggregate_meal_micronutrients(
            [{"food_id": "sparse-food", "grams": 50}],
            meal_title="Sparse meal",
        )
    )

    assert result == {
        "calcium_mg": 0.0,
        "potassium_mg": 5.0,
    }


@pytest.mark.parametrize(
    ("food", "grams"),
    [
        pytest.param({"per_g": "oops"}, 10, id="malformed-serving-basis"),
        pytest.param({"per_g": 0, "Fe_mg": 1.0}, 10, id="zero-serving-basis"),
        pytest.param({"per_g": 100, "Fe_mg": "bad-value"}, 10, id="malformed-micro"),
        pytest.param({"per_g": 100, "Fe_mg": 1.0}, "bad-grams", id="malformed-grams"),
        pytest.param({"per_g": True, "Fe_mg": 1.0}, 10, id="boolean-serving-basis"),
        pytest.param({"per_g": 100, "Fe_mg": True}, 10, id="boolean-micro"),
        pytest.param({"per_g": 100, "Fe_mg": 1.0}, True, id="boolean-grams"),
    ],
)
def test_aggregate_meal_micronutrients_rejects_malformed_provider_values(
    monkeypatch: pytest.MonkeyPatch,
    food: dict[str, object],
    grams: object,
) -> None:
    async def _food_from_db(
        _func: object,
        *_args: object,
        **_kwargs: object,
    ) -> dict[str, object]:
        return food

    monkeypatch.setattr(plate_service.asyncio, "to_thread", _food_from_db)

    with pytest.raises(plate_service._InvalidPlateMicronutrientOutputError):
        asyncio.run(
            plate_service._aggregate_meal_micronutrients(
                [{"food_id": "db-food", "grams": grams}],
                meal_title="Meal",
            )
        )


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
        plate_service.recipe_store,
        "search_recipes",
        lambda title, limit=1: [{"recipe_id": "r1"}],
    )
    monkeypatch.setattr(
        plate_service.recipe_store,
        "get_recipe",
        lambda recipe_id: recipe_data,
    )

    ingredients = plate_service._get_recipe_ingredients_for_meal("Soup")
    assert len(ingredients) == 3
    assert ingredients[0]["food_id"] == "f1"
    assert ingredients[2]["grams"] == 25


def test_get_recipe_ingredients_for_meal_no_recipe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        plate_service.recipe_store,
        "search_recipes",
        lambda *args, **kwargs: [],
    )
    assert plate_service._get_recipe_ingredients_for_meal("None") == []


def test_get_recipe_ingredients_missing_recipe_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        plate_service.recipe_store,
        "search_recipes",
        lambda *args, **kwargs: [{}],
    )
    assert plate_service._get_recipe_ingredients_for_meal("Soup") == []


def test_get_recipe_ingredients_recipe_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        plate_service.recipe_store,
        "search_recipes",
        lambda *args, **kwargs: [{"recipe_id": "r1"}],
    )
    monkeypatch.setattr(
        plate_service.recipe_store,
        "get_recipe",
        lambda recipe_id: None,
    )
    assert plate_service._get_recipe_ingredients_for_meal("Soup") == []


def test_get_recipe_ingredients_missing_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        plate_service.recipe_store,
        "search_recipes",
        lambda *args, **kwargs: [{"recipe_id": "r1"}],
    )
    monkeypatch.setattr(
        plate_service.recipe_store,
        "get_recipe",
        lambda recipe_id: {},
    )
    assert plate_service._get_recipe_ingredients_for_meal("Soup") == []


def test_get_recipe_ingredients_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        plate_service.recipe_store,
        "search_recipes",
        lambda *args, **kwargs: [{"recipe_id": "r1"}],
    )
    monkeypatch.setattr(
        plate_service.recipe_store,
        "get_recipe",
        lambda recipe_id: {"ingredients_json": "{}"},
    )
    with pytest.raises(plate_service._InvalidPlateMicronutrientOutputError):
        plate_service._get_recipe_ingredients_for_meal("Soup")


def test_aggregate_day_micronutrients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _aggregate_day_micronutrients aggregates micros from meals.

    Meal A has explicit micros, Meal B needs ingredient lookup + aggregation.
    """

    async def fake_aggregate(
        ingredients: List[Dict[str, Any]], meal_title: str = ""
    ) -> Dict[str, float]:
        # This should be called for Meal B (no explicit micros)
        assert meal_title == "Meal B", f"Expected 'Meal B', got '{meal_title}'"
        return {"iron_mg": 1.0}

    def fake_lookup(title: str) -> List[Dict[str, Any]]:
        return [{"food_id": "x", "grams": 10}]

    # Mock asyncio.to_thread to bypass thread execution
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(plate_service.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        plate_service,
        "_get_recipe_ingredients_for_meal",
        fake_lookup,
    )
    monkeypatch.setattr(
        plate_service,
        "_aggregate_meal_micronutrients",
        fake_aggregate,
    )

    meals = [
        {"title": "Meal A", "micros": {"iron_mg": 0.5}},
        {"title": "Meal B"},  # No micros/ingredients, will trigger lookup + aggregation
    ]

    result = asyncio.run(plate_service._aggregate_day_micronutrients(meals))
    # Meal A: 0.5, Meal B: 1.0 (from fake_aggregate) = 1.5 total
    assert result["iron_mg"] == pytest.approx(1.5)


def test_alias_micros_type_error() -> None:
    invalid_micros: Any = ["not", "a", "dict"]
    with pytest.raises(TypeError):
        plate_service.alias_micros(invalid_micros)


def test_alias_micros_value_error() -> None:
    with pytest.raises(ValueError):
        plate_service.alias_micros({"iron_mg": object()})


def test_alias_micros_aliases() -> None:
    result = plate_service.alias_micros({"iron_mg": 2})
    assert result["iron"] == 2.0
    assert result["fe"] == 2.0

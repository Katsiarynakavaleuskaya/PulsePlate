from __future__ import annotations

from typing import Any, List

import pytest
from fastapi import HTTPException

from app.routers import foods
from app.schemas.food import FoodHit, FoodItem


def test_list_foods_invalid_limit() -> None:
    with pytest.raises(HTTPException):
        foods.list_foods(query="apple", limit=0, offset=0)


def test_list_foods_success(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "id": "f1",
            "canonical_name": "Apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14,
        },
    ]

    monkeypatch.setattr(foods.food_store, "search_foods", lambda *args, **kwargs: rows)
    result = foods.list_foods(query="apple", limit=10, offset=0)
    assert isinstance(result, list)
    assert isinstance(result[0], FoodHit)
    assert result[0].id == "f1"


def test_list_foods_search_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, tuple[Any, ...]] = {}

    def fake_list_foods(*args: Any, **kwargs: Any) -> List[FoodHit]:
        called["args"] = (args, kwargs)
        return [FoodHit(id="fX", name="X", kcal=1, protein_g=0, fat_g=0, carbs_g=0)]

    monkeypatch.setattr(foods, "list_foods", fake_list_foods)
    foods.list_foods_search(query="x", limit=5, offset=2)
    assert called["args"][0] == ()
    assert called["args"][1] == {"query": "x", "limit": 5, "offset": 2}


def test_get_food_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(foods.food_store, "get_food", lambda *_: None)
    with pytest.raises(HTTPException) as exc:
        foods.get_food("missing")
    assert exc.value.status_code == 404


def test_get_food_success(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "id": "f1",
        "canonical_name": "Apple",
        "kcal": 52,
        "protein_g": 0.3,
        "fat_g": 0.2,
        "carbs_g": 14,
        "version_date": "2024-01-01",
    }
    monkeypatch.setattr(foods.food_store, "get_food", lambda *_: row)
    result = foods.get_food("f1")
    assert isinstance(result, FoodItem)
    assert result.id == "f1"

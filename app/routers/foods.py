# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.food import FoodHit, FoodItem
from app.services import food_store

router = APIRouter(tags=["foods"])


class FoodStore(Protocol):
    def search_foods(self, query: str, limit: int, offset: int) -> Sequence[Mapping[str, Any]]: ...

    def get_food(self, food_id: str) -> Mapping[str, Any] | None: ...

    def get_food_by_barcode(self, barcode: str) -> Mapping[str, Any] | None: ...


class _FoodStoreCompat:
    """Compatibility wrapper that keeps router contract stable while allowing backend switching."""

    def search_foods(self, query: str, limit: int, offset: int) -> Sequence[Mapping[str, Any]]:
        backend = food_store.get_search_backend()
        return backend.search_foods(query=query, limit=limit, offset=offset)

    def get_food(self, food_id: str) -> Mapping[str, Any] | None:
        return food_store.get_food(food_id)

    def get_food_by_barcode(self, barcode: str) -> Mapping[str, Any] | None:
        return food_store.get_food_by_barcode(barcode)


_FOOD_STORE_COMPAT: FoodStore = _FoodStoreCompat()


def get_food_store() -> FoodStore:
    return _FOOD_STORE_COMPAT


@router.get("/api/v1/foods", response_model=list[FoodHit])
def list_foods(
    query: str = Query("", max_length=64),
    limit: int = 20,
    offset: int = 0,
    store: FoodStore = Depends(get_food_store),
) -> list[FoodHit]:
    if limit > 100 or limit < 1:
        raise HTTPException(422, "limit must be in [1,100]")
    rows = store.search_foods(query, limit, offset)
    return [
        FoodHit(
            id=r["id"],
            name=r["canonical_name"],
            kcal=r["kcal"],
            protein_g=r["protein_g"],
            fat_g=r["fat_g"],
            carbs_g=r["carbs_g"],
        )
        for r in rows
    ]


# Backward-compatible alias for tests expecting /api/v1/foods/search
@router.get("/api/v1/foods/search", response_model=list[FoodHit])
def list_foods_search(
    query: str = Query("", max_length=64),
    limit: int = 20,
    offset: int = 0,
    store: FoodStore = Depends(get_food_store),
) -> list[FoodHit]:
    # With --follow-imports=skip, FastAPI decorators are Any and `list_foods` becomes Any too.
    # Using a typed local keeps mypy happy while still allowing tests to monkeypatch `list_foods`.
    delegate: Callable[..., list[FoodHit]] = list_foods
    return delegate(query=query, limit=limit, offset=offset, store=store)


@router.get("/api/v1/foods/{food_id}", response_model=FoodItem)
def get_food(food_id: str, store: FoodStore = Depends(get_food_store)) -> FoodItem:
    row = store.get_food(food_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
    return FoodItem(**row)


@router.get(
    "/api/v1/foods/barcode/{barcode}",
    response_model=FoodItem,
    responses={
        422: {"description": "Malformed barcode"},
        404: {"description": "Food not found"},
    },
)
def get_food_by_barcode(barcode: str, store: FoodStore = Depends(get_food_store)) -> FoodItem:
    try:
        row = store.get_food_by_barcode(barcode)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
    return FoodItem(**row)

# -*- coding: utf-8 -*-
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.schemas.food import FoodHit, FoodItem
from app.services import food_store

router = APIRouter(tags=["foods"])


@router.get("/api/v1/foods", response_model=List[FoodHit])
def list_foods(query: str = Query("", max_length=64), limit: int = 20, offset: int = 0):
    if limit > 100 or limit < 1:
        raise HTTPException(422, "limit must be in [1,100]")
    rows = food_store.search_foods(query, limit, offset)
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


@router.get("/api/v1/foods/{food_id}", response_model=FoodItem)
def get_food(food_id: str):
    row = food_store.get_food(food_id)
    if not row:
        raise HTTPException(status_code=404, detail="Food not found")
    return FoodItem(**row)

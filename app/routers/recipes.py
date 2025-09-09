# -*- coding: utf-8 -*-
import json
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.schemas.recipe import (
    Recipe,
    RecipePreviewRequest,
    RecipePreviewResponse,
    RecipeQueryHit,
)
from app.services import recipe_store
from app.services.food_store import nutrients_for

router = APIRouter(tags=["recipes"])


@router.get("/api/v1/recipes", response_model=List[RecipeQueryHit])
def list_recipes(
    query: str = Query("", max_length=64), limit: int = 20, offset: int = 0
):
    if limit > 50 or limit < 1:
        raise HTTPException(422, "limit must be in [1,50]")
    rows = recipe_store.search_recipes(query or "*", limit, offset)
    out = []
    for r in rows:
        tags = json.loads(r.get("tags_json") or "[]")
        out.append(
            RecipeQueryHit(
                recipe_id=r["recipe_id"],
                title=r["title"],
                kcal_per_serv=r.get("kcal_per_serv", 0.0),
                tags=tags,
            )
        )
    return out


@router.get("/api/v1/recipes/{recipe_id}", response_model=Recipe)
def get_recipe(recipe_id: str):
    r = recipe_store.get_recipe(recipe_id)
    if not r:
        raise HTTPException(404, "Recipe not found")
    return Recipe(
        recipe_id=r["recipe_id"],
        title=r["title"],
        locale=r["locale"],
        servings=r["servings"],
        yield_total_g=r["yield_total_g"],
        ingredients=json.loads(r["ingredients_json"]),
        steps=json.loads(r.get("steps_json") or "[]"),
        tags=json.loads(r.get("tags_json") or "[]"),
        allergens=json.loads(r.get("allergens_json") or "[]"),
        cost_total=r.get("cost_total", 0.0),
        cost_per_serv=r.get("cost_per_serv", 0.0),
        nutrients_per_serv=json.loads(r.get("nutrients_per_serv_json") or "{}"),
        source=r.get("source", "internal"),
        version_date=r.get("version_date", ""),
    )


@router.post("/api/v1/recipes/preview", response_model=RecipePreviewResponse)
def recipe_preview(req: RecipePreviewRequest):
    if req.servings <= 0:
        raise HTTPException(422, "servings must be >= 1")
    total_g = sum(i.grams for i in req.ingredients)
    total = nutrients_for([i.model_dump() for i in req.ingredients])
    per_serv = {k: v / req.servings for k, v in total.items()}
    return RecipePreviewResponse(
        title=req.title, servings=req.servings, total_g=total_g, per_serving=per_serv
    )

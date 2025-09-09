# -*- coding: utf-8 -*-
"""
RU: Нормализованная схема рецепта и превью.
EN: Normalized recipe schema and preview.
"""
from typing import Dict, List

from pydantic import BaseModel, Field, conlist


class Ingredient(BaseModel):
    food_id: str
    grams: float


class Recipe(BaseModel):
    recipe_id: str
    title: str
    locale: str = "en"
    servings: int
    yield_total_g: float
    ingredients: conlist(Ingredient, min_length=1)
    steps: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    allergens: List[str] = Field(default_factory=list)
    cost_total: float = 0.0
    cost_per_serv: float = 0.0
    nutrients_per_serv: Dict[str, float] = Field(default_factory=dict)
    source: str = "internal"
    version_date: str


class RecipeQueryHit(BaseModel):
    recipe_id: str
    title: str
    kcal_per_serv: float
    tags: List[str] = Field(default_factory=list)


class RecipePreviewRequest(BaseModel):
    title: str
    servings: int = 1
    ingredients: conlist(Ingredient, min_length=1)


class RecipePreviewResponse(BaseModel):
    title: str
    servings: int
    total_g: float
    per_serving: Dict[str, float]

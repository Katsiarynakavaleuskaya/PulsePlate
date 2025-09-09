"""
Food and Recipe Data Schemas

RU: Схемы данных для продуктов и рецептов с полной прослеживаемостью.
EN: Data schemas for foods and recipes with full provenance tracking.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, conlist


class FoodItem(BaseModel):
    """
    RU: Полная схема продукта с прослеживаемостью источника.
    EN: Complete food item schema with source provenance.
    """

    # Core identification
    id: str = Field(..., description="Unique food identifier")
    canonical_name: str = Field(..., description="Canonical food name")
    group: str = Field(..., description="Food group category")

    # Nutritional data (per 100g)
    per_g: float = Field(default=100.0, description="Reference weight in grams")
    kcal: float = Field(..., description="Energy in kcal")
    protein_g: float = Field(..., description="Protein in grams")
    fat_g: float = Field(..., description="Fat in grams")
    carbs_g: float = Field(..., description="Carbohydrates in grams")
    fiber_g: float = Field(default=0.0, description="Dietary fiber in grams")

    # Micronutrients (WHO/EFSA tracked)
    Fe_mg: float = Field(default=0.0, description="Iron in mg")
    Ca_mg: float = Field(default=0.0, description="Calcium in mg")
    K_mg: float = Field(default=0.0, description="Potassium in mg")
    Mg_mg: float = Field(default=0.0, description="Magnesium in mg")
    VitD_IU: float = Field(default=0.0, description="Vitamin D in IU")
    B12_ug: float = Field(default=0.0, description="Vitamin B12 in µg")
    Folate_ug: float = Field(default=0.0, description="Folate in µg")
    Iodine_ug: float = Field(default=0.0, description="Iodine in µg")

    # Product metadata
    flags: List[str] = Field(
        default_factory=list, description="Dietary flags (VEG, GF, etc.)"
    )
    brand: Optional[str] = Field(default=None, description="Product brand")
    gtin: Optional[str] = Field(default=None, description="GTIN/barcode")
    fdc_id: Optional[str] = Field(default=None, description="USDA FDC ID")

    # Source tracking
    source: str = Field(..., description="Data source (USDA, OFF, etc.)")
    source_priority: int = Field(default=0, description="Source priority for conflicts")
    version_date: str = Field(..., description="Data version date")
    price_per_100g: float = Field(
        default=0.0, description="Price per 100g in local currency"
    )


class RecipeIngredient(BaseModel):
    """
    RU: Ингредиент рецепта с количеством.
    EN: Recipe ingredient with quantity.
    """

    food_id: str = Field(..., description="Reference to FoodItem.id")
    grams: float = Field(..., gt=0, description="Weight in grams")


class Recipe(BaseModel):
    """
    RU: Полная схема рецепта с расчетом нутриентов на порцию.
    EN: Complete recipe schema with per-serving nutrient calculation.
    """

    # Core identification
    recipe_id: str = Field(..., description="Unique recipe identifier")
    title: str = Field(..., description="Recipe title")
    locale: str = Field(default="en", description="Recipe locale")

    # Recipe structure
    yield_total_g: float = Field(..., gt=0, description="Total recipe weight in grams")
    servings: int = Field(..., gt=0, description="Number of servings")
    ingredients: conlist(RecipeIngredient, min_length=1) = Field(
        ..., description="List of ingredients with quantities"
    )
    steps: List[str] = Field(default_factory=list, description="Cooking steps")

    # Classification
    tags: List[str] = Field(default_factory=list, description="Recipe tags")
    allergens: List[str] = Field(default_factory=list, description="Allergen warnings")

    # Cost calculation
    cost_total: float = Field(default=0.0, description="Total recipe cost")
    cost_per_serv: float = Field(default=0.0, description="Cost per serving")

    # Nutritional summary (calculated)
    nutrients_per_serv: Dict[str, float] = Field(
        default_factory=dict, description="Nutrients per serving"
    )

    # Source tracking
    source: str = Field(..., description="Recipe source")
    version_date: str = Field(..., description="Recipe version date")


class FoodSearchRequest(BaseModel):
    """
    RU: Запрос поиска продуктов с фильтрами.
    EN: Food search request with filters.
    """

    query: Optional[str] = Field(default=None, description="Search query")
    group: Optional[str] = Field(default=None, description="Food group filter")
    flags: Optional[List[str]] = Field(default=None, description="Dietary flags filter")
    limit: int = Field(default=20, ge=1, le=100, description="Results limit")
    offset: int = Field(default=0, ge=0, description="Results offset")


class RecipeSearchRequest(BaseModel):
    """
    RU: Запрос поиска рецептов с фильтрами.
    EN: Recipe search request with filters.
    """

    query: Optional[str] = Field(default=None, description="Search query")
    diet: Optional[str] = Field(default=None, description="Diet type filter")
    max_kcal: Optional[float] = Field(
        default=None, description="Max calories per serving"
    )
    tags: Optional[List[str]] = Field(default=None, description="Tag filters")
    limit: int = Field(default=20, ge=1, le=100, description="Results limit")
    offset: int = Field(default=0, ge=0, description="Results offset")


class RecipePreviewRequest(BaseModel):
    """
    RU: Запрос предварительного расчета рецепта.
    EN: Recipe preview calculation request.
    """

    title: str = Field(..., description="Recipe title")
    ingredients: conlist(RecipeIngredient, min_length=1) = Field(
        ..., description="List of ingredients"
    )
    servings: int = Field(..., gt=0, description="Number of servings")
    locale: str = Field(default="en", description="Recipe locale")


class RecipePreviewResponse(BaseModel):
    """
    RU: Ответ с расчетом нутриентов и стоимости рецепта.
    EN: Response with recipe nutrient and cost calculation.
    """

    title: str = Field(..., description="Recipe title")
    servings: int = Field(..., description="Number of servings")
    total_weight_g: float = Field(..., description="Total recipe weight")
    cost_total: float = Field(..., description="Total recipe cost")
    cost_per_serv: float = Field(..., description="Cost per serving")
    nutrients_per_serv: Dict[str, float] = Field(
        ..., description="Nutrients per serving"
    )
    missing_ingredients: List[str] = Field(
        default_factory=list, description="Ingredients not found in database"
    )

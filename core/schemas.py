"""
Food and Recipe Data Schemas

RU: Схемы данных для продуктов и рецептов с полной прослеживаемостью.
EN: Data schemas for foods and recipes with full provenance tracking.
"""

from __future__ import annotations

from typing import Annotated, Dict, List, Optional

from pydantic import BaseModel, Field


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
    kcal: float | None = Field(default=None, description="Energy in kcal (None if unknown)")
    protein_g: float | None = Field(default=None, description="Protein in grams (None if unknown)")
    fat_g: float | None = Field(default=None, description="Fat in grams (None if unknown)")
    carbs_g: float | None = Field(
        default=None, description="Carbohydrates in grams (None if unknown)"
    )
    fiber_g: float | None = Field(
        default=None, description="Dietary fiber in grams (None if unknown)"
    )

    # Micronutrients (WHO/EFSA tracked) - None indicates unknown/missing values
    Fe_mg: float | None = Field(default=None, description="Iron in mg (None if unknown)")
    Ca_mg: float | None = Field(default=None, description="Calcium in mg (None if unknown)")
    K_mg: float | None = Field(default=None, description="Potassium in mg (None if unknown)")
    Mg_mg: float | None = Field(default=None, description="Magnesium in mg (None if unknown)")
    VitD_IU: float | None = Field(default=None, description="Vitamin D in IU (None if unknown)")
    B12_ug: float | None = Field(default=None, description="Vitamin B12 in µg (None if unknown)")
    Folate_ug: float | None = Field(default=None, description="Folate in µg (None if unknown)")
    Iodine_ug: float | None = Field(default=None, description="Iodine in µg (None if unknown)")

    # Product metadata
    flags: List[str] = Field(default_factory=list, description="Dietary flags (VEG, GF, etc.)")
    brand: Optional[str] = Field(default=None, description="Product brand")
    gtin: Optional[str] = Field(default=None, description="GTIN/barcode")
    fdc_id: Optional[str] = Field(default=None, description="USDA FDC ID")

    # Source tracking
    source: str = Field(..., description="Data source (USDA, OFF, etc.)")
    source_priority: int = Field(default=0, description="Source priority for conflicts")
    version_date: str = Field(..., description="Data version date")
    price_per_100g: float = Field(default=0.0, description="Price per 100g in local currency")

    @property
    def nutrients_per_100g(self) -> Dict[str, float]:
        """
        RU: Словарь питательных веществ на 100г (только известные значения).
        EN: Dictionary of nutrients per 100g (known values only).

        Returns only nutrients that have non-None values.
        """
        nutrients = {}
        if self.kcal is not None:
            nutrients["kcal"] = self.kcal
        if self.protein_g is not None:
            nutrients["protein_g"] = self.protein_g
        if self.fat_g is not None:
            nutrients["fat_g"] = self.fat_g
        if self.carbs_g is not None:
            nutrients["carbs_g"] = self.carbs_g
        if self.fiber_g is not None:
            nutrients["fiber_g"] = self.fiber_g
        if self.Fe_mg is not None:
            nutrients["Fe_mg"] = self.Fe_mg
        if self.Ca_mg is not None:
            nutrients["Ca_mg"] = self.Ca_mg
        if self.K_mg is not None:
            nutrients["K_mg"] = self.K_mg
        if self.Mg_mg is not None:
            nutrients["Mg_mg"] = self.Mg_mg
        if self.VitD_IU is not None:
            nutrients["VitD_IU"] = self.VitD_IU
        if self.B12_ug is not None:
            nutrients["B12_ug"] = self.B12_ug
        if self.Folate_ug is not None:
            nutrients["Folate_ug"] = self.Folate_ug
        if self.Iodine_ug is not None:
            nutrients["Iodine_ug"] = self.Iodine_ug
        return nutrients


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
    ingredients: Annotated[List[RecipeIngredient], Field(min_length=1)] = Field(
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
    max_kcal: Optional[float] = Field(default=None, description="Max calories per serving")
    tags: Optional[List[str]] = Field(default=None, description="Tag filters")
    limit: int = Field(default=20, ge=1, le=100, description="Results limit")
    offset: int = Field(default=0, ge=0, description="Results offset")


class RecipePreviewRequest(BaseModel):
    """
    RU: Запрос предварительного расчета рецепта.
    EN: Recipe preview calculation request.
    """

    title: str = Field(..., description="Recipe title")
    ingredients: Annotated[List[RecipeIngredient], Field(min_length=1)] = Field(
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
    nutrients_per_serv: Dict[str, float] = Field(..., description="Nutrients per serving")
    missing_ingredients: List[str] = Field(
        default_factory=list, description="Ingredients not found in database"
    )

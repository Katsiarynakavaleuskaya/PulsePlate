"""
RU: Нормализованная схема рецепта и превью.
EN: Normalized recipe schema and preview.
"""



from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    food_id: str
    grams: float


class Recipe(BaseModel):
    recipe_id: str
    title: str
    locale: str = "en"
    servings: int
    yield_total_g: float
    ingredients: list[Ingredient] = Field(..., min_length=1)
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    cost_total: float = 0.0
    cost_per_serv: float = 0.0
    nutrients_per_serv: dict[str, float] = Field(default_factory=dict)
    source: str = "internal"
    version_date: str


class RecipeQueryHit(BaseModel):
    recipe_id: str
    title: str
    kcal_per_serv: float
    tags: list[str] = Field(default_factory=list)


class RecipePreviewRequest(BaseModel):
    title: str
    servings: int = 1
    ingredients: list[Ingredient] = Field(..., min_length=1)


class RecipePreviewResponse(BaseModel):
    title: str
    servings: int
    total_g: float
    per_serving: dict[str, float]

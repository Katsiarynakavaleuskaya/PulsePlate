"""Shopping List Generator schemas (request/response DTOs).

Provides strongly typed contracts for the PRO shopping list generation endpoint.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypeAlias

from pydantic import BaseModel, Field, model_validator

# Type alias for source validation
SourceType: TypeAlias = Literal["weekly_plan_id", "inline_plan"]


class ShoppingListPreferences(BaseModel):
    """User preferences for shopping list generation."""

    group_by: Literal["category", "recipe"] = "category"
    unit_system: Literal["metric", "imperial"] = "metric"
    merge_similar_items: bool = True
    round_quantities: bool = True

    # Future extensibility
    exclude_items: List[str] = Field(default_factory=list)
    dietary_tags: List[str] = Field(default_factory=list)


class ShoppingListRequest(BaseModel):
    """Request to generate a shopping list from a weekly plan.

    Must provide either weekly_plan_id (from DB) or plan_data (inline JSON).
    """

    weekly_plan_id: Optional[str] = None
    plan_data: Optional[Dict[str, Any]] = None

    preferences: ShoppingListPreferences = Field(default_factory=ShoppingListPreferences)

    @model_validator(mode="after")
    def validate_input_source(self) -> "ShoppingListRequest":
        """Validate that exactly one input source is provided (XOR)."""
        if self.weekly_plan_id and self.plan_data:
            raise ValueError("Cannot provide both weekly_plan_id and plan_data")
        if not self.weekly_plan_id and not self.plan_data:
            raise ValueError("Must provide either weekly_plan_id or plan_data")
        return self


class ShoppingListItem(BaseModel):
    """Individual shopping list item."""

    key: str  # Stable identifier (e.g., "chicken_breast")
    name: str  # Display name
    quantity: float
    unit: str  # "g", "kg", "pcs", etc.
    recipe_refs: List[str] = Field(default_factory=list)  # Recipe IDs/titles


class ShoppingListCategory(BaseModel):
    """Category of shopping list items."""

    key: str  # Machine-friendly key (e.g., "proteins")
    title: str  # Display title (e.g., "Proteins")
    items: List[ShoppingListItem]


class ShoppingListMeta(BaseModel):
    """Metadata about shopping list generation."""

    source: SourceType
    unit_system: Literal["metric", "imperial"]
    warnings: List[str] = Field(default_factory=list)


class ShoppingListDTO(BaseModel):
    """Shopping list generation response."""

    categories: List[ShoppingListCategory]
    total_items: int
    generated_at: datetime

    meta: ShoppingListMeta


# Day Shopping List (MVP) - iOS offline-first
# RU: Список покупок на день (MVP) - iOS offline-first


class ShopUnit(str, Enum):
    """Stable units for iOS (do not rename; only extend).

    RU: Стабильные единицы измерения для iOS (не переименовывать, только расширять).
    """

    g = "g"
    kg = "kg"
    ml = "ml"
    liter = "l"  # noqa: E741 - API contract requires 'l' value
    pcs = "pcs"


class ShopAisle(str, Enum):
    """Stable aisle/category for iOS (do not rename; only extend).

    RU: Категории для группировки списка покупок (не переименовывать).
    """

    produce = "Produce"
    protein = "Protein"
    dairy = "Dairy"
    pantry = "Pantry"
    frozen = "Frozen"
    other = "Other"


class ShoplistSourceDTO(BaseModel):
    """Optional provenance of an item.

    RU: Источник/происхождение позиции (опционально).
    """

    type: Literal["plan", "manual", "import"] = "plan"
    ref: Optional[str] = None


class ShoplistDayItemDTO(BaseModel):
    """One day shopping list item (server → iOS).

    key: stable dedup key (server-side normalized slug or food_id-like).
    title: localized title for UI.

    RU: Одна строка списка покупок на день (сервер → iOS).
    """

    key: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=256)
    qty: float = Field(..., ge=0.0, le=1_000_000.0)
    unit: ShopUnit
    aisle: ShopAisle = ShopAisle.other
    notes: Optional[str] = Field(default=None, max_length=256)
    source: Optional[ShoplistSourceDTO] = None


class ShoplistDayResponse(BaseModel):
    """Day shopping list suggestions (MVP placeholder).

    RU: Подсказки списка покупок на день (MVP заглушка).
    """

    date: str = Field(..., description="YYYY-MM-DD")
    lang: str = Field(..., description="ru|en|es")
    items: list[ShoplistDayItemDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

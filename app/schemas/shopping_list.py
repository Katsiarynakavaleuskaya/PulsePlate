"""Shopping List Generator schemas (request/response DTOs).

Provides strongly typed contracts for the PRO shopping list generation endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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

    source: Literal["weekly_plan_id", "inline_plan"]
    unit_system: Literal["metric", "imperial"]
    warnings: List[str] = Field(default_factory=list)


class ShoppingListDTO(BaseModel):
    """Shopping list generation response."""

    categories: List[ShoppingListCategory]
    total_items: int
    generated_at: datetime

    meta: ShoppingListMeta

"""Shopping List Generator schemas (request/response DTOs).

Provides strongly typed contracts for the PRO shopping list generation endpoint.
"""

from __future__ import annotations

from datetime import datetime
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

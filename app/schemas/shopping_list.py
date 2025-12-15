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

    group_by: Literal["category"] = "category"  # recipe support planned for future
    unit_system: Literal["metric"] = "metric"  # imperial support planned for future
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

    key: str = Field(..., description="Stable identifier (e.g., 'chicken_breast').")
    name: str = Field(..., description="User-facing display name for the ingredient.")
    quantity: float = Field(..., gt=0, description="Required quantity (must be positive).")
    unit: str = Field(..., description="Unit of measurement (e.g., 'g', 'kg', 'pcs').")
    recipe_refs: List[str] = Field(
        default_factory=list,
        description="Optional list of recipe/meal references that contributed to this item.",
    )


class ShoppingListCategory(BaseModel):
    """Category of shopping list items."""

    key: str = Field(..., description="Machine-friendly category key (e.g., 'proteins').")
    title: str = Field(..., description="User-facing category title (e.g., 'Proteins').")
    items: List[ShoppingListItem] = Field(..., description="List of items in this category.")


class ShoppingListMeta(BaseModel):
    """Metadata about shopping list generation."""

    source: SourceType = Field(
        ..., description="Data source type: 'weekly_plan_id' or 'inline_plan'."
    )
    unit_system: Literal["metric", "imperial"] = Field(
        ..., description="Unit system used for quantities."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Diagnostic warnings (e.g., 'unknown_unit:xyz', 'missing_ingredients').",
    )


class ShoppingListDTO(BaseModel):
    """Shopping list generation response."""

    categories: List[ShoppingListCategory]
    total_items: int
    generated_at: datetime

    meta: ShoppingListMeta

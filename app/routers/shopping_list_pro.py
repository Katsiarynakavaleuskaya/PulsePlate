"""PRO Shopping List Generator endpoint.

Generates optimized shopping lists from weekly meal plans with category grouping,
unit normalization, and duplicate merging.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.shopping_list.generator import generate_shopping_list_from_plan
from app.middleware.api_tiers import require_pro_tier
from app.schemas.shopping_list import ShoppingListDTO, ShoppingListRequest

router = APIRouter(prefix="/api/v1/pro/meal", tags=["pro", "shopping-list"])


@router.post(
    "/shopping-list", response_model=ShoppingListDTO, dependencies=[Depends(require_pro_tier)]
)
async def generate_shopping_list(request: ShoppingListRequest) -> ShoppingListDTO:
    """Generate shopping list from weekly meal plan.

    **Input:**
    - `weekly_plan_id`: Optional ID of saved weekly plan (from DB)
    - `plan_data`: Optional inline weekly plan JSON
    - `preferences`: Shopping list generation preferences

    **Output:**
    - Categories with grouped items
    - Total item count
    - Generation metadata

    **Algorithm:**
    1. Validate input (XOR: weekly_plan_id OR plan_data)
    2. Extract ingredients from plan_data
    3. Normalize keys and aggregate quantities
    4. Group by categories
    5. Return structured DTO with warnings
    """
    # Validate preferences (reject unsupported features that bypass schema validation)
    prefs = request.preferences

    # Note: group_by and unit_system are already constrained by Pydantic Literal types
    # Only check for future-extensibility fields that have default values
    if prefs.exclude_items or prefs.dietary_tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="exclude_items and dietary_tags are not supported yet",
        )

    # Validate input (XOR constraint now handled by Pydantic model_validator)
    # But we still need to check which source is provided
    # Determine source
    if request.weekly_plan_id:
        # TODO(future): Fetch plan_data from database using weekly_plan_id
        # For now, this path requires implementation when DB integration is ready
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="weekly_plan_id support not yet implemented",
        )

    # Use inline plan_data (guaranteed non-None by Pydantic XOR validator)
    # Generate shopping list using core logic
    return generate_shopping_list_from_plan(
        plan_data=request.plan_data,  # type: ignore[arg-type]  # Pydantic ensures non-None
        preferences=request.preferences,
        source="inline_plan",
    )


__all__ = ["router"]

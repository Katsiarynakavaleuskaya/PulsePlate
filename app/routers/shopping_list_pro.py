"""PRO Shopping List Generator endpoint.

Generates optimized shopping lists from weekly meal plans with category grouping,
unit normalization, and duplicate merging.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.shopping_list.generator import generate_shopping_list_from_plan
from app.services import fitchef_runtime
from app.middleware.api_tiers import require_pro_tier
from app.schemas.fitchef import (
    FitChefShoppingFollowupInput,
    FitChefShoppingFollowupTaskEnvelope,
)
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
    # Validate preferences (reject unsupported features)
    prefs = request.preferences

    if prefs.group_by not in ("category", None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="group_by='recipe' is not supported yet",
        )

    if prefs.unit_system == "imperial":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="unit_system='imperial' is not supported yet",
        )

    if prefs.exclude_items or prefs.dietary_tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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

    task = FitChefShoppingFollowupTaskEnvelope(
        mode="auto-safe",
        input=FitChefShoppingFollowupInput(
            weekly_plan_id=request.weekly_plan_id,
            plan_data=request.plan_data,
            preferences=request.preferences,
        ),
    )
    result = await fitchef_runtime.run_shopping_followup_task(
        task,
        shopping_list_builder=generate_shopping_list_from_plan,
    )
    return result.shopping_list


__all__ = ["router"]

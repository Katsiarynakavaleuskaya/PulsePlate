"""PRO Shopping List Generator endpoint.

Generates optimized shopping lists from weekly meal plans with category grouping,
unit normalization, and duplicate merging.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.schemas.shopping_list import ShoppingListDTO, ShoppingListRequest

router = APIRouter(prefix="/api/v1/pro/meal", tags=["pro", "shopping-list"])


@router.post("/shopping-list", response_model=ShoppingListDTO)
def generate_shopping_list(request: ShoppingListRequest) -> ShoppingListDTO:
    """Generate shopping list from weekly meal plan.

    **Input:**
    - `weekly_plan_id`: Optional ID of saved weekly plan (from DB)
    - `plan_data`: Optional inline weekly plan JSON
    - `preferences`: Shopping list generation preferences

    **Output:**
    - Categories with grouped items
    - Total item count
    - Generation metadata

    **TODO(#XXX):** Implement core logic:
    1. Load weekly plan (from DB or inline data)
    2. Extract ingredients from all meals/recipes
    3. Normalize units (metric/imperial)
    4. Merge duplicate ingredients
    5. Group by category
    6. Return structured DTO
    """
    # Validate input (both conditions must be checked with proper handling of empty dicts)
    has_plan_id = request.weekly_plan_id is not None
    has_plan_data = request.plan_data is not None

    if has_plan_id and has_plan_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provide both weekly_plan_id and plan_data",
        )

    if not has_plan_id and not has_plan_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either weekly_plan_id or plan_data",
        )

    # TODO(#XXX): Replace with actual implementation
    # For now, return minimal valid response
    from app.schemas.shopping_list import (
        ShoppingListCategory,
        ShoppingListItem,
        ShoppingListMeta,
    )

    # Stub implementation
    return ShoppingListDTO(
        categories=[
            ShoppingListCategory(
                key="proteins",
                title="Proteins",
                items=[
                    ShoppingListItem(
                        key="chicken_breast",
                        name="Chicken breast",
                        quantity=500.0,
                        unit="g",
                        recipe_refs=["lunch_day1", "dinner_day3"],
                    )
                ],
            )
        ],
        total_items=1,
        generated_at=datetime.now(timezone.utc),
        meta=ShoppingListMeta(
            source="weekly_plan_id" if request.weekly_plan_id else "inline_plan",
            unit_system=request.preferences.unit_system,
            warnings=["stub_implementation_active"],
        ),
    )


__all__ = ["router"]

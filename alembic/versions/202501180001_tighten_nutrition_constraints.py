"""Tighten nutritional constraints for recipes and meals.

Revision ID: 202501180001
Revises: 202501170001
Create Date: 2025-01-18
"""

from __future__ import annotations

from alembic import op

revision = "202501180001"
down_revision = "202501170001"
branch_labels = None
depends_on = None


# Bounds aligned with WHO-based targets in core.targets.MicronutrientTargets
RECIPE_CONSTRAINTS = {
    "ck_recipe_kcal_max": "kcal_per_serving <= 2000",
    "ck_recipe_protein_max": "protein_g <= 60",
    "ck_recipe_fat_max": "fat_g <= 50",
    "ck_recipe_carbs_max": "carbs_g <= 150",
    "ck_recipe_fiber_max": "fiber_g <= 20",
}

MEAL_CONSTRAINTS = {
    "ck_meal_kcal_max": "kcal <= 2000",
    "ck_meal_protein_max": "protein_g <= 150",
    "ck_meal_fat_max": "fat_g <= 100",
    "ck_meal_carbs_max": "carbs_g <= 300",
    "ck_meal_fiber_max": "fiber_g <= 50",
}


def upgrade() -> None:
    for name, condition in RECIPE_CONSTRAINTS.items():
        op.drop_constraint(name, "recipes", type_="check")
        op.create_check_constraint(name, "recipes", condition)

    for name, condition in MEAL_CONSTRAINTS.items():
        op.drop_constraint(name, "meals", type_="check")
        op.create_check_constraint(name, "meals", condition)


def downgrade() -> None:
    previous_recipe = {
        "ck_recipe_kcal_max": "kcal_per_serving <= 5000",
        "ck_recipe_protein_max": "protein_g <= 500",
        "ck_recipe_fat_max": "fat_g <= 400",
        "ck_recipe_carbs_max": "carbs_g <= 800",
        "ck_recipe_fiber_max": "fiber_g <= 150",
    }
    previous_meal = {
        "ck_meal_kcal_max": "kcal <= 5000",
        "ck_meal_protein_max": "protein_g <= 500",
        "ck_meal_fat_max": "fat_g <= 400",
        "ck_meal_carbs_max": "carbs_g <= 800",
        "ck_meal_fiber_max": "fiber_g <= 150",
    }

    for name, condition in previous_recipe.items():
        op.drop_constraint(name, "recipes", type_="check")
        op.create_check_constraint(name, "recipes", condition)

    for name, condition in previous_meal.items():
        op.drop_constraint(name, "meals", type_="check")
        op.create_check_constraint(name, "meals", condition)

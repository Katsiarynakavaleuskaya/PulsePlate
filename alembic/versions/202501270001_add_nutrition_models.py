"""Add Recipe, Meal, FoodItem, and ContextEntry tables

RU: Добавление таблиц для рецептов, приёмов пищи, продуктов и контекста.
EN: Add tables for recipes, meals, food items, and context entries.

This migration adds the foundational database models for Bayesian test quality
analysis and nutrition tracking infrastructure.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "202501270001"
down_revision = "202501010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Применяем схему для таблиц питания и контекста.

    EN: Apply the nutrition and context tables schema.
    """

    # Create recipes table
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("kcal_per_serving", sa.Float(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("servings", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ingredients", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("allergens", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("version_date", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("kcal_per_serving >= 0", name="ck_recipe_kcal_positive"),
        sa.CheckConstraint("kcal_per_serving <= 2000", name="ck_recipe_kcal_max"),
        sa.CheckConstraint("protein_g >= 0", name="ck_recipe_protein_positive"),
        sa.CheckConstraint("protein_g <= 150", name="ck_recipe_protein_max"),  # Raised from 60
        sa.CheckConstraint("fat_g >= 0", name="ck_recipe_fat_positive"),
        sa.CheckConstraint("fat_g <= 100", name="ck_recipe_fat_max"),  # Raised from 50
        sa.CheckConstraint("carbs_g >= 0", name="ck_recipe_carbs_positive"),
        sa.CheckConstraint("carbs_g <= 300", name="ck_recipe_carbs_max"),  # Raised from 150
        sa.CheckConstraint("fiber_g >= 0", name="ck_recipe_fiber_positive"),
        sa.CheckConstraint("fiber_g <= 50", name="ck_recipe_fiber_max"),  # Raised from 20
        sa.CheckConstraint("servings > 0", name="ck_recipe_servings_positive"),
    )
    op.create_index("ix_recipes_title", "recipes", ["title"])
    op.create_index("ix_recipes_locale", "recipes", ["locale"])

    # Create meals table
    op.create_table(
        "meals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recipe_id",
            sa.Integer(),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("title_translated", sa.String(length=500), nullable=True),
        sa.Column("kcal", sa.Float(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grams_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("micros_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("kcal >= 0", name="ck_meal_kcal_positive"),
        sa.CheckConstraint("kcal <= 3000", name="ck_meal_kcal_max"),  # Raised from 2000
        sa.CheckConstraint("protein_g >= 0", name="ck_meal_protein_positive"),
        sa.CheckConstraint("protein_g <= 200", name="ck_meal_protein_max"),  # Raised from 150
        sa.CheckConstraint("fat_g >= 0", name="ck_meal_fat_positive"),
        sa.CheckConstraint("fat_g <= 150", name="ck_meal_fat_max"),  # Raised from 100
        sa.CheckConstraint("carbs_g >= 0", name="ck_meal_carbs_positive"),
        sa.CheckConstraint("carbs_g <= 400", name="ck_meal_carbs_max"),  # Raised from 300
        sa.CheckConstraint("fiber_g >= 0", name="ck_meal_fiber_positive"),
        sa.CheckConstraint("fiber_g <= 80", name="ck_meal_fiber_max"),  # Raised from 50
    )
    op.create_index("ix_meals_user_id", "meals", ["user_id"])
    op.create_index("ix_meals_recipe_id", "meals", ["recipe_id"])
    op.create_index("ix_meals_created_at", "meals", ["created_at"])

    # Create food_items table
    op.create_table(
        "food_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("food_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("food_group", sa.String(length=100), nullable=False),
        sa.Column("kcal_per_100g", sa.Float(), nullable=False),
        sa.Column("protein_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fiber_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("micros_data", sa.JSON(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("version_date", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("kcal_per_100g >= 0", name="ck_food_kcal_positive"),
        sa.CheckConstraint("kcal_per_100g <= 1000", name="ck_food_kcal_max"),
        sa.CheckConstraint("protein_g_per_100g >= 0", name="ck_food_protein_positive"),
        sa.CheckConstraint("protein_g_per_100g <= 100", name="ck_food_protein_max"),
        sa.CheckConstraint("fat_g_per_100g >= 0", name="ck_food_fat_positive"),
        sa.CheckConstraint("fat_g_per_100g <= 100", name="ck_food_fat_max"),
        sa.CheckConstraint("carbs_g_per_100g >= 0", name="ck_food_carbs_positive"),
        sa.CheckConstraint("carbs_g_per_100g <= 100", name="ck_food_carbs_max"),
        sa.CheckConstraint("fiber_g_per_100g >= 0", name="ck_food_fiber_positive"),
        sa.CheckConstraint("fiber_g_per_100g <= 100", name="ck_food_fiber_max"),
    )
    op.create_index("ix_food_items_canonical_name", "food_items", ["canonical_name"])

    # Create context table
    op.create_table(
        "context",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_context_locale", "context", ["locale"])


def downgrade() -> None:
    """RU: Откатываем схему таблиц питания и контекста.

    EN: Drop the nutrition and context tables schema.
    """

    # Drop context table
    op.drop_index("ix_context_locale", table_name="context")
    op.drop_table("context")

    # Drop food_items table
    op.drop_index("ix_food_items_canonical_name", table_name="food_items")
    op.drop_table("food_items")

    # Drop meals table
    op.drop_index("ix_meals_created_at", table_name="meals")
    op.drop_index("ix_meals_recipe_id", table_name="meals")
    op.drop_index("ix_meals_user_id", table_name="meals")
    op.drop_table("meals")

    # Drop recipes table
    op.drop_index("ix_recipes_locale", table_name="recipes")
    op.drop_index("ix_recipes_title", table_name="recipes")
    op.drop_table("recipes")

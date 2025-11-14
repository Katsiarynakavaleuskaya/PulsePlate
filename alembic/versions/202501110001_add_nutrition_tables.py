"""Add Recipe Meal FoodItem tables with CHECK constraints and nutrition validation

Revision ID: 202501110001
Revises: 202501010001
Create Date: 2025-01-11 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import alembic.op as op

# revision identifiers, used by Alembic.
revision: str = "202501110001"
down_revision: str = "202501010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Добавить таблицы Recipe, Meal, FoodItem с валидацией.
    EN: Add Recipe, Meal, FoodItem tables with validation."""

    bind = op.get_bind()
    dialect_name = bind.dialect.name

    def _json_server_default(literal: str) -> sa.sql.elements.TextClause:
        """Return a dialect-aware JSON default literal."""
        if dialect_name == "postgresql":
            return sa.text(f"'{literal}'::jsonb")
        if dialect_name == "mysql":
            return sa.text(f"CAST('{literal}' AS JSON)")
        return sa.text(f"'{literal}'")

    json_object_default = _json_server_default("{}")
    json_array_default = _json_server_default("[]")

    # Create recipes table
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipe_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default=sa.text("'en'")),
        sa.Column("kcal_per_serving", sa.Float(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("servings", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ingredients", sa.JSON(), nullable=False, server_default=json_object_default),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=json_array_default),
        sa.Column("allergens", sa.JSON(), nullable=False, server_default=json_array_default),
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
        sa.CheckConstraint("kcal_per_serving <= 5000", name="ck_recipe_kcal_max"),
        sa.CheckConstraint("protein_g >= 0", name="ck_recipe_protein_positive"),
        sa.CheckConstraint("protein_g <= 500", name="ck_recipe_protein_max"),
        sa.CheckConstraint("fat_g >= 0", name="ck_recipe_fat_positive"),
        sa.CheckConstraint("fat_g <= 400", name="ck_recipe_fat_max"),
        sa.CheckConstraint("carbs_g >= 0", name="ck_recipe_carbs_positive"),
        sa.CheckConstraint("carbs_g <= 800", name="ck_recipe_carbs_max"),
        sa.CheckConstraint("fiber_g >= 0", name="ck_recipe_fiber_positive"),
        sa.CheckConstraint("fiber_g <= 150", name="ck_recipe_fiber_max"),
        sa.CheckConstraint("servings > 0", name="ck_recipe_servings_positive"),
    )
    op.create_index("ix_recipes_title", "recipes", ["title"])
    op.create_index("ix_recipes_locale", "recipes", ["locale"])

    # Create meals table
    op.create_table(
        "meals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
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
        sa.Column(
            "kcal", sa.Float(), nullable=False
        ),  # Changed from Integer to Float to match model
        sa.Column("protein_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grams_data", sa.JSON(), nullable=False, server_default=json_object_default),
        sa.Column("micros_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("kcal >= 0", name="ck_meal_kcal_positive"),
        sa.CheckConstraint("kcal <= 5000", name="ck_meal_kcal_max"),
        sa.CheckConstraint("protein_g >= 0", name="ck_meal_protein_positive"),
        sa.CheckConstraint("protein_g <= 500", name="ck_meal_protein_max"),
        sa.CheckConstraint("fat_g >= 0", name="ck_meal_fat_positive"),
        sa.CheckConstraint("fat_g <= 400", name="ck_meal_fat_max"),
        sa.CheckConstraint("carbs_g >= 0", name="ck_meal_carbs_positive"),
        sa.CheckConstraint("carbs_g <= 800", name="ck_meal_carbs_max"),
        sa.CheckConstraint("fiber_g >= 0", name="ck_meal_fiber_positive"),
        sa.CheckConstraint("fiber_g <= 150", name="ck_meal_fiber_max"),
    )
    op.create_index("ix_meals_user_id", "meals", ["user_id"])
    op.create_index("ix_meals_recipe_id", "meals", ["recipe_id"])
    op.create_index("ix_meals_created_at", "meals", ["created_at"])

    # Create food_items table
    op.create_table(
        "food_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("food_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("food_group", sa.String(length=100), nullable=False),
        sa.Column("kcal_per_100g", sa.Float(), nullable=False),
        sa.Column("protein_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fiber_g_per_100g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("micros_data", sa.JSON(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=False, server_default=json_array_default),
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


def downgrade() -> None:
    """RU: Откатить миграцию (удалить таблицы).
    EN: Revert migration (drop tables)."""

    op.drop_index("ix_food_items_canonical_name", table_name="food_items")
    op.drop_table("food_items")

    op.drop_index("ix_meals_created_at", table_name="meals")
    op.drop_index("ix_meals_recipe_id", table_name="meals")
    op.drop_index("ix_meals_user_id", table_name="meals")
    op.drop_table("meals")

    op.drop_index("ix_recipes_locale", table_name="recipes")
    op.drop_index("ix_recipes_title", table_name="recipes")
    op.drop_table("recipes")

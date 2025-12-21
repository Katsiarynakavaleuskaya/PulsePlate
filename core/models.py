"""Declarative models for the core application domain.

RU: Декларативные модели для основного домена приложения с CHECK-ограничениями.
EN: Declarative models for core application domain with CHECK constraints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    """RU: Пользователь приложения. EN: Application user entity."""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Recipe(Base):
    """RU: Рецепт с ингредиентами и нутриентами.
    EN: Recipe with ingredients and nutritional data.

    Stores validated recipe data with CHECK constraints to ensure data integrity.
    """

    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("kcal_per_serving >= 0", name="ck_recipe_kcal_positive"),
        CheckConstraint("kcal_per_serving <= 2000", name="ck_recipe_kcal_max"),
        CheckConstraint("protein_g >= 0", name="ck_recipe_protein_positive"),
        CheckConstraint("protein_g <= 150", name="ck_recipe_protein_max"),  # High-protein meals
        CheckConstraint("fat_g >= 0", name="ck_recipe_fat_positive"),
        CheckConstraint("fat_g <= 100", name="ck_recipe_fat_max"),  # High-fat meals
        CheckConstraint("carbs_g >= 0", name="ck_recipe_carbs_positive"),
        CheckConstraint("carbs_g <= 300", name="ck_recipe_carbs_max"),  # High-carb meals
        CheckConstraint("fiber_g >= 0", name="ck_recipe_fiber_positive"),
        CheckConstraint("fiber_g <= 50", name="ck_recipe_fiber_max"),  # High-fiber meals
        CheckConstraint("servings > 0", name="ck_recipe_servings_positive"),
        Index("ix_recipes_title", "title"),
        Index("ix_recipes_locale", "locale"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    locale: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en", server_default=text("'en'")
    )

    # Nutritional data (per serving, validated by CHECK constraints)
    kcal_per_serving: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Recipe metadata
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ingredients: Mapped[dict[str, float]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=lambda: {},
        server_default=text("'{}'"),
    )  # {food_id: grams}
    tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=False,
        default=lambda: [],
        server_default=text("'[]'"),
    )  # App-layer default: []
    allergens: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=False,
        default=lambda: [],
        server_default=text("'[]'"),
    )  # App-layer default: []

    # Source tracking
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    version_date: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Meal(Base):
    """RU: Приём пищи (meal) с валидированными макронутриентами.
    EN: Meal with validated macronutrients.

    Stores meal data with CHECK constraints for nutrition safety.
    """

    __tablename__ = "meals"
    __table_args__ = (
        CheckConstraint("kcal >= 0", name="ck_meal_kcal_positive"),
        CheckConstraint("kcal <= 3000", name="ck_meal_kcal_max"),  # Large/athletic meals
        CheckConstraint("protein_g >= 0", name="ck_meal_protein_positive"),
        CheckConstraint("protein_g <= 200", name="ck_meal_protein_max"),  # Bodybuilding meals
        CheckConstraint("fat_g >= 0", name="ck_meal_fat_positive"),
        CheckConstraint("fat_g <= 150", name="ck_meal_fat_max"),  # Keto/high-fat diets
        CheckConstraint("carbs_g >= 0", name="ck_meal_carbs_positive"),
        CheckConstraint("carbs_g <= 400", name="ck_meal_carbs_max"),  # Endurance athlete meals
        CheckConstraint("fiber_g >= 0", name="ck_meal_fiber_positive"),
        CheckConstraint("fiber_g <= 80", name="ck_meal_fiber_max"),  # Very high-fiber diets
        Index("ix_meals_user_id", "user_id"),
        Index("ix_meals_recipe_id", "recipe_id"),
        Index("ix_meals_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recipe_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_translated: Mapped[str] = mapped_column(String(500), nullable=True)

    # Nutritional data (validated by CHECK constraints)
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Ingredient details
    grams_data: Mapped[dict[str, float]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=lambda: {},
        server_default=text("'{}'"),
    )  # {food_id: grams}
    micros_data: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )  # Micronutrients

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FoodItem(Base):
    """RU: Продукт питания с нутриентами и прослеживаемостью источника.
    EN: Food item with nutrients and source provenance.

    Stores food data from external sources (USDA, OpenFoodFacts) with validation.
    """

    __tablename__ = "food_items"
    __table_args__ = (
        CheckConstraint("kcal_per_100g >= 0", name="ck_food_kcal_positive"),
        CheckConstraint("kcal_per_100g <= 1000", name="ck_food_kcal_max"),
        CheckConstraint("protein_g_per_100g >= 0", name="ck_food_protein_positive"),
        CheckConstraint("protein_g_per_100g <= 100", name="ck_food_protein_max"),
        CheckConstraint("fat_g_per_100g >= 0", name="ck_food_fat_positive"),
        CheckConstraint("fat_g_per_100g <= 100", name="ck_food_fat_max"),
        CheckConstraint("carbs_g_per_100g >= 0", name="ck_food_carbs_positive"),
        CheckConstraint("carbs_g_per_100g <= 100", name="ck_food_carbs_max"),
        CheckConstraint("fiber_g_per_100g >= 0", name="ck_food_fiber_positive"),
        CheckConstraint("fiber_g_per_100g <= 100", name="ck_food_fiber_max"),
        # Index on canonical_name for food search optimization
        Index("ix_food_items_canonical_name", "canonical_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    food_group: Mapped[str] = mapped_column(String(100), nullable=False)

    # Nutritional data per 100g (validated by CHECK constraints)
    kcal_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_g_per_100g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Micronutrients
    micros_data: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )

    # Metadata (app-layer defaults via Pydantic, not DB-level)
    flags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        nullable=False,
        default=lambda: [],
        server_default=text("'[]'"),
    )  # VEG, GF, etc.
    brand: Mapped[str] = mapped_column(String(255), nullable=True)

    # Source tracking
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=True)
    version_date: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ContextEntry(Base):
    """RU: Контекстные записи для RAG/диагностики. EN: Context entries for RAG/diagnostics."""

    __tablename__ = "context"
    __table_args__ = (Index("ix_context_locale", "locale"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en", server_default=text("'en'")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=lambda: {},
        server_default=text("'{}'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AnalyzerStateModel(Base):
    """RU: Состояние байес-анализатора (source of truth для Postgres/SQLite).
    EN: Bayesian analyzer state storage with versioning and optimistic locking.

    Stores analyzer state with JSON payload (JSONB on Postgres) for flexibility.
    Unique constraint on (user_id, analyzer_key) ensures one state per user-analyzer pair.
    state_version enables optimistic concurrency control for safe multi-worker updates.
    """

    __tablename__ = "analyzer_state"
    __table_args__ = (
        Index("ix_analyzer_state_user_id", "user_id"),
        Index("ix_analyzer_state_analyzer_key", "analyzer_key"),
        UniqueConstraint("user_id", "analyzer_key", name="uq_analyzer_state_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    analyzer_key: Mapped[str] = mapped_column(String(64), nullable=False)

    state_schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    state_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )

    # JSON on SQLite, JSONB on Postgres via with_variant
    payload: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=lambda: {},
        server_default=text("'{}'"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


__all__: list[str] = ["User", "Recipe", "Meal", "FoodItem", "ContextEntry", "AnalyzerStateModel"]

"""Add Bayesian infrastructure tables

RU: Добавление таблиц для байесовских методов (meal_entries, recommendation_feedback).
EN: Add tables for Bayesian methods (meal_entries, recommendation_feedback).

Revision ID: 202501090001
Revises: 202501010001
Create Date: 2025-01-09
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "202501090001"
down_revision = "202501010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    RU: Создать таблицы для Bayesian инфраструктуры.
    EN: Create tables for Bayesian infrastructure.

    Creates:
    - meal_entries: User meal data for anomaly detection and pattern analysis
    - recommendation_feedback: User feedback for Thompson Sampling
    """
    # Create meal_entries table
    op.create_table(
        "meal_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Meal identification
        sa.Column("food_name", sa.String(length=255), nullable=False),
        sa.Column("meal_type", sa.String(length=50), nullable=True),
        # Macronutrients
        sa.Column("calories", sa.Float(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fat_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0.0"),
        # Micronutrients (optional)
        sa.Column("iron_mg", sa.Float(), nullable=True),
        sa.Column("calcium_mg", sa.Float(), nullable=True),
        sa.Column("vitamin_d_iu", sa.Float(), nullable=True),
        # Validation metadata
        sa.Column("was_validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validation_status", sa.String(length=50), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        # Timestamps
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Indexes for meal_entries
    op.create_index(
        "ix_meal_entries_user_timestamp", "meal_entries", ["user_id", "timestamp"]
    )
    op.create_index("ix_meal_entries_timestamp", "meal_entries", ["timestamp"])

    # Create recommendation_feedback table
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Recommendation details
        sa.Column("recommendation_id", sa.String(length=255), nullable=False),
        sa.Column("strategy_name", sa.String(length=100), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        # User response
        sa.Column("was_shown", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("was_clicked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("was_followed", sa.Boolean(), nullable=False, server_default="false"),
        # Engagement metrics
        sa.Column("time_to_click_ms", sa.Integer(), nullable=True),
        sa.Column("session_duration_ms", sa.Integer(), nullable=True),
        # Timestamps
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Indexes for recommendation_feedback
    op.create_index(
        "ix_recommendation_feedback_user_timestamp",
        "recommendation_feedback",
        ["user_id", "timestamp"],
    )
    op.create_index(
        "ix_recommendation_feedback_strategy", "recommendation_feedback", ["strategy_name"]
    )


def downgrade() -> None:
    """
    RU: Откатить Bayesian таблицы.
    EN: Drop Bayesian infrastructure tables.
    """
    # Drop recommendation_feedback
    op.drop_index("ix_recommendation_feedback_strategy", table_name="recommendation_feedback")
    op.drop_index(
        "ix_recommendation_feedback_user_timestamp", table_name="recommendation_feedback"
    )
    op.drop_table("recommendation_feedback")

    # Drop meal_entries
    op.drop_index("ix_meal_entries_timestamp", table_name="meal_entries")
    op.drop_index("ix_meal_entries_user_timestamp", table_name="meal_entries")
    op.drop_table("meal_entries")

"""Add weekly_plans and day_plans tables for day shopping list DB wiring

RU: Добавление таблиц weekly_plans и day_plans для сохранения планов питания.
EN: Add weekly_plans and day_plans tables for storing meal plans.

This migration adds persistence for generated weekly/day meal plans to support
the day shopping list feature (PR-3).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "202501270002"
down_revision = "202501270001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Создаём таблицы для weekly и day планов.

    EN: Create tables for weekly and day plans.
    """

    # Create weekly_plans table
    op.create_table(
        "weekly_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("plan_data", sa.JSON(), nullable=False, server_default="{}"),
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
        sa.CheckConstraint("start_date <= end_date", name="ck_weekly_plan_date_order"),
    )
    op.create_index("ix_weekly_plans_user_id", "weekly_plans", ["user_id"])
    op.create_index("ix_weekly_plans_start_date", "weekly_plans", ["start_date"])
    op.create_index(
        "ix_weekly_plans_user_date", "weekly_plans", ["user_id", "start_date"], unique=True
    )

    # Create day_plans table
    op.create_table(
        "day_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "weekly_plan_id",
            sa.Integer(),
            sa.ForeignKey("weekly_plans.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("plan_data", sa.JSON(), nullable=False, server_default="{}"),
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
    op.create_index("ix_day_plans_user_id", "day_plans", ["user_id"])
    op.create_index("ix_day_plans_date", "day_plans", ["date"])
    op.create_index("ix_day_plans_user_date", "day_plans", ["user_id", "date"], unique=True)
    op.create_index("ix_day_plans_weekly_plan_id", "day_plans", ["weekly_plan_id"])


def downgrade() -> None:
    """RU: Удаляем таблицы weekly и day планов.

    EN: Drop weekly and day plans tables.
    """

    # Drop day_plans table
    op.drop_index("ix_day_plans_weekly_plan_id", table_name="day_plans")
    op.drop_index("ix_day_plans_user_date", table_name="day_plans")
    op.drop_index("ix_day_plans_date", table_name="day_plans")
    op.drop_index("ix_day_plans_user_id", table_name="day_plans")
    op.drop_table("day_plans")

    # Drop weekly_plans table
    op.drop_index("ix_weekly_plans_user_date", table_name="weekly_plans")
    op.drop_index("ix_weekly_plans_start_date", table_name="weekly_plans")
    op.drop_index("ix_weekly_plans_user_id", table_name="weekly_plans")
    op.drop_table("weekly_plans")

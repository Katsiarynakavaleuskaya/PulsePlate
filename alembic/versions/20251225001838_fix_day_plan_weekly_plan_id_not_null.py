"""Fix day_plans.weekly_plan_id to be NOT NULL

RU: Исправление ограничения NOT NULL для weekly_plan_id в таблице day_plans.
EN: Fix NOT NULL constraint for weekly_plan_id in day_plans table.

This migration fixes a schema-model mismatch where the database column was created
as nullable=True but the ORM model requires nullable=False. Any orphaned day_plans
(those with NULL weekly_plan_id) are deleted before enforcing the constraint.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251225001838"
down_revision = "202512220001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Удаляем orphaned day_plans и делаем weekly_plan_id NOT NULL.

    EN: Delete orphaned day_plans and make weekly_plan_id NOT NULL.
    """
    # Delete any orphaned day_plans (those with NULL weekly_plan_id)
    # These are invalid according to the model which requires weekly_plan_id
    op.execute(sa.text("DELETE FROM day_plans WHERE weekly_plan_id IS NULL"))

    # Alter the column to be NOT NULL
    # SQLite requires recreating the table for this change
    with op.batch_alter_table("day_plans", schema=None) as batch_op:
        batch_op.alter_column(
            "weekly_plan_id",
            existing_type=sa.Integer(),
            nullable=False,
            existing_nullable=True,
        )


def downgrade() -> None:
    """RU: Возвращаем weekly_plan_id к nullable=True.

    EN: Revert weekly_plan_id back to nullable=True.
    """
    with op.batch_alter_table("day_plans", schema=None) as batch_op:
        batch_op.alter_column(
            "weekly_plan_id",
            existing_type=sa.Integer(),
            nullable=True,
            existing_nullable=False,
        )

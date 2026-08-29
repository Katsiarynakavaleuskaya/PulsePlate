"""Adopt historical unique indexes as canonical unique constraints.

Revision ID: 202608290001
Revises: 202608270001
Create Date: 2026-08-29

PostgreSQL can attach an existing unique index to a constraint without an
enforcement gap.  SQLite represents both historical objects with unique index
semantics and therefore requires no physical rewrite for this PostgreSQL drift
reconciliation.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "202608290001"
down_revision = "202608270001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adopt the two existing PostgreSQL unique indexes losslessly."""

    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        "ALTER TABLE analyzer_state "
        "ADD CONSTRAINT uq_analyzer_state_user_key "
        "UNIQUE USING INDEX uq_analyzer_state_user_key"
    )
    op.execute(
        "ALTER TABLE day_plans "
        "ADD CONSTRAINT uq_day_plans_user_date "
        "UNIQUE USING INDEX ix_day_plans_user_date"
    )


def downgrade() -> None:
    """Restore the exact historical unique-index names without an enforcement gap."""

    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("CREATE UNIQUE INDEX ix_day_plans_user_date_restore " "ON day_plans (user_id, date)")
    op.execute("ALTER TABLE day_plans DROP CONSTRAINT uq_day_plans_user_date")
    op.execute("ALTER INDEX ix_day_plans_user_date_restore " "RENAME TO ix_day_plans_user_date")

    op.execute(
        "CREATE UNIQUE INDEX uq_analyzer_state_user_key_restore "
        "ON analyzer_state (user_id, analyzer_key)"
    )
    op.execute("ALTER TABLE analyzer_state DROP CONSTRAINT uq_analyzer_state_user_key")
    op.execute(
        "ALTER INDEX uq_analyzer_state_user_key_restore " "RENAME TO uq_analyzer_state_user_key"
    )

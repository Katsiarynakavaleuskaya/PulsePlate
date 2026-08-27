"""add FitChef support outcome ledger

Revision ID: 202608270001
Revises: 202604130001
Create Date: 2026-08-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202608270001"
down_revision = "202604130001"
branch_labels = None
depends_on = None

_TABLE = "fitchef_support_outcome_events"
_POLICY = "fitchef_support_outcome_subject_isolation"


def upgrade() -> None:
    """Create the append-only, credential-subject-scoped outcome ledger."""

    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_id", sa.BigInteger(), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("support_need", sa.String(length=32), nullable=False),
        sa.Column("target_surface", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("client_event_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_id",
            "client_event_id",
            name="uq_fitchef_support_outcome_subject_event",
        ),
        sa.CheckConstraint(
            "schema_version = 'fitchef_support_outcome_v1'",
            name="ck_fitchef_support_outcome_schema_version",
        ),
        sa.CheckConstraint(
            "support_need IN ('daily_structure', 'weekly_structure')",
            name="ck_fitchef_support_outcome_support_need",
        ),
        sa.CheckConstraint(
            "target_surface IN ('pro_daily_plate', 'pro_weekly_plan')",
            name="ck_fitchef_support_outcome_target_surface",
        ),
        sa.CheckConstraint(
            "outcome IN ('acknowledged', 'dismissed')",
            name="ck_fitchef_support_outcome_outcome",
        ),
        sa.CheckConstraint(
            "((support_need = 'daily_structure' AND target_surface = 'pro_daily_plate') "
            "OR (support_need = 'weekly_structure' AND target_surface = 'pro_weekly_plan'))",
            name="ck_fitchef_support_outcome_compatible_pair",
        ),
    )
    op.create_index(
        "ix_fitchef_support_outcomes_subject_created_at",
        _TABLE,
        ["subject_id", "created_at"],
        unique=False,
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {_POLICY} ON {_TABLE}
            USING (
                subject_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
            )
            WITH CHECK (
                subject_id = NULLIF(current_setting('app.current_user_id', true), '')::bigint
            )
        """)


def downgrade() -> None:
    """Remove only the outcome ledger and its own isolation policy."""

    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"DROP POLICY IF EXISTS {_POLICY} ON {_TABLE}")
        op.execute(f"ALTER TABLE {_TABLE} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_fitchef_support_outcomes_subject_created_at",
        table_name=_TABLE,
    )
    op.drop_table(_TABLE)

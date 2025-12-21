"""Add analyzer_state table for Bayesian state storage.

Revision ID: 202512210001
Revises: 202501270002
Create Date: 2025-12-21 23:13:00.000000

RU: Добавить таблицу analyzer_state для хранения состояния байес-анализатора.
EN: Add analyzer_state table for persistent Bayesian analyzer state with versioning.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202512210001"
down_revision = "202501270002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create analyzer_state table with JSON/JSONB payload and optimistic locking."""
    op.create_table(
        "analyzer_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("analyzer_key", sa.String(length=64), nullable=False),
        sa.Column(
            "state_schema_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analyzer_state_analyzer_key", "analyzer_state", ["analyzer_key"], unique=False
    )
    op.create_index("ix_analyzer_state_user_id", "analyzer_state", ["user_id"], unique=False)
    op.create_index(
        "uq_analyzer_state_user_key", "analyzer_state", ["user_id", "analyzer_key"], unique=True
    )


def downgrade() -> None:
    """Drop analyzer_state table."""
    op.drop_index("uq_analyzer_state_user_key", table_name="analyzer_state")
    op.drop_index("ix_analyzer_state_user_id", table_name="analyzer_state")
    op.drop_index("ix_analyzer_state_analyzer_key", table_name="analyzer_state")
    op.drop_table("analyzer_state")

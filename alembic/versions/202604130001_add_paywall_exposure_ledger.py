"""add paywall exposure ledger

Revision ID: 202604130001
Revises: 202604120001
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202604130001"
down_revision = "202604120001"
branch_labels = None
depends_on = None


def _json_type() -> sa.JSON:
    """RU: Диалект-безопасный JSON/JSONB. EN: Dialect-safe JSON/JSONB."""

    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create paywall exposure ledger table and indexes."""

    op.create_table(
        "paywall_exposure_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("event_name", sa.String(length=32), nullable=False),
        sa.Column("source_surface", sa.String(length=64), nullable=False),
        sa.Column("trigger_reason", sa.String(length=64), nullable=False),
        sa.Column("via", sa.String(length=64), nullable=True),
        sa.Column("exposure_id", sa.String(length=128), nullable=False),
        sa.Column("client_event_id", sa.String(length=128), nullable=False),
        sa.Column("subject_id", sa.BigInteger(), nullable=True),
        sa.Column("auth_source", sa.String(length=16), nullable=True),
        sa.Column("tier_snapshot", sa.String(length=16), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_event_id",
            name="uq_paywall_exposure_ledger_client_event_id",
        ),
    )
    op.create_index(
        "ix_paywall_exposure_ledger_event_name_created_at",
        "paywall_exposure_ledger",
        ["event_name", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_paywall_exposure_ledger_source_surface_created_at",
        "paywall_exposure_ledger",
        ["source_surface", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_paywall_exposure_ledger_trigger_reason_created_at",
        "paywall_exposure_ledger",
        ["trigger_reason", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop paywall exposure ledger table and indexes."""

    op.drop_index(
        "ix_paywall_exposure_ledger_trigger_reason_created_at",
        table_name="paywall_exposure_ledger",
    )
    op.drop_index(
        "ix_paywall_exposure_ledger_source_surface_created_at",
        table_name="paywall_exposure_ledger",
    )
    op.drop_index(
        "ix_paywall_exposure_ledger_event_name_created_at",
        table_name="paywall_exposure_ledger",
    )
    op.drop_table("paywall_exposure_ledger")

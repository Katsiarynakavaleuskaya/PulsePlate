"""Add nutrition_events table

RU: Добавить таблицу nutrition_events для журнала событий питания.
EN: Add nutrition_events table for append-only event log with idempotency.

Revision ID: 202512220001
Revises: 202512210001
Create Date: 2025-12-22 15:50:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "202512220001"
down_revision = "202512210001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create nutrition_events table with idempotency constraint."""
    op.create_table(
        "nutrition_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("client_event_id", sa.String(length=64), nullable=True),
        sa.Column(
            "payload",
            sa.Text(),  # JSON as text for SQLite compatibility
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_id",
            "day",
            "source",
            "client_event_id",
            name="uq_nutrition_events_idempotency",
        ),
    )
    op.create_index(
        "ix_nutrition_events_subject_day",
        "nutrition_events",
        ["subject_id", "day"],
        unique=False,
    )
    op.create_index(
        "ix_nutrition_events_created_at",
        "nutrition_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop nutrition_events table."""
    op.drop_index("ix_nutrition_events_created_at", table_name="nutrition_events")
    op.drop_index("ix_nutrition_events_subject_day", table_name="nutrition_events")
    op.drop_table("nutrition_events")

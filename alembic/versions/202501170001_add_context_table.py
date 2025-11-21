"""Add context table for RAG/diagnostics storage.

RU: Добавляет таблицу context для хранения контекстов.
EN: Adds the context table for storing diagnostic/RAG snippets.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202501170001"
down_revision = "202501120001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create context table with indexes."""
    bind = op.get_bind()
    updated_at_column = sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    if bind.dialect.name == "mysql":
        updated_at_column.server_onupdate = sa.func.now()

    op.create_table(
        "context",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        updated_at_column,
    )
    op.create_index("ix_context_slug", "context", ["slug"], unique=True)
    op.create_index("ix_context_locale", "context", ["locale"])


def downgrade() -> None:
    """Drop context table."""
    op.drop_index("ix_context_locale", table_name="context")
    op.drop_index("ix_context_slug", table_name="context")
    op.drop_table("context")

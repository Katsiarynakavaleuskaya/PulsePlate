"""Add default and server_default to recipes.ingredients column

Revision ID: 202501120001
Revises: 202501120000
Create Date: 2025-01-12 00:01:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "202501120001"
down_revision = "202501120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Обновить server_default для колонки ingredients для совместимости диалектов.
    EN: Update ingredients column server_default for dialect compatibility."""
    # Determine database type for proper JSON default syntax
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Use database-specific JSON default syntax
    if dialect_name == "postgresql":
        # PostgreSQL requires explicit JSON cast for JSON columns
        json_default = text("'{}'::json")
    elif dialect_name == "mysql":
        # MySQL 8.0.13+ supports JSON literals directly
        json_default = text("('{}')")
    else:
        # SQLite and others: use text literal (SQLite treats JSON as TEXT)
        json_default = text("'{}'")

    # Alter the ingredients column to add server_default
    op.alter_column(
        "recipes",
        "ingredients",
        existing_type=sa.JSON(),
        nullable=False,
        server_default=json_default,
    )


def downgrade() -> None:
    """RU: Удалить server_default из колонки ingredients в таблице recipes.
    EN: Remove server_default from ingredients column in recipes table."""
    # Remove server_default from ingredients column
    op.alter_column(
        "recipes",
        "ingredients",
        existing_type=sa.JSON(),
        nullable=False,
        server_default=None,
    )

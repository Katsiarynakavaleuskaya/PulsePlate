"""Add server_default to recipes.locale column

Revision ID: 202501120000
Revises: 202501110001
Create Date: 2025-01-12 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "202501120000"
down_revision = "202501110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Добавить server_default для колонки locale в таблице recipes.
    EN: Add server_default for locale column in recipes table."""
    # Alter the locale column to add server_default
    op.alter_column(
        "recipes",
        "locale",
        existing_type=sa.String(length=10),
        nullable=False,
        server_default=text("'en'"),
    )


def downgrade() -> None:
    """RU: Удалить server_default из колонки locale в таблице recipes.
    EN: Remove server_default from locale column in recipes table."""
    # Remove server_default from locale column
    op.alter_column(
        "recipes",
        "locale",
        existing_type=sa.String(length=10),
        nullable=False,
        server_default=None,
    )

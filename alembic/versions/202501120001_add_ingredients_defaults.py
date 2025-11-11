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
    """RU: Добавить server_default для колонки ingredients в таблице recipes.
    EN: Add server_default for ingredients column in recipes table."""
    # Alter the ingredients column to add server_default
    op.alter_column(
        "recipes",
        "ingredients",
        existing_type=sa.JSON(),
        nullable=False,
        server_default=text("'{}'"),
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

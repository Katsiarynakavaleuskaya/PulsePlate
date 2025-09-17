"""Create users table

RU: Создание таблицы пользователей.
EN: Create users table.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202501010001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """RU: Применяем первую схему пользователей.

    EN: Apply the initial users schema.
    """

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    """RU: Откатываем схему пользователей.

    EN: Drop the users schema.
    """

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

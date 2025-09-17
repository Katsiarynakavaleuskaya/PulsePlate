"""Alembic revision template."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


def upgrade():
    """RU: Применить миграцию. EN: Apply migration."""
    ${upgrades if upgrades else 'pass'}


def downgrade():
    """RU: Откатить миграцию. EN: Revert migration."""
    ${downgrades if downgrades else 'pass'}

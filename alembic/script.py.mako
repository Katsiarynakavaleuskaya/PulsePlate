"""Alembic revision template."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# Revision identifiers supplied by Alembic's generation context.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    """RU: Применить миграцию. EN: Apply migration."""
    ${upgrades if upgrades else 'pass'}


def downgrade():
    """RU: Откатить миграцию. EN: Revert migration."""
    ${downgrades if downgrades else 'pass'}

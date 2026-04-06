"""enable pg_trgm and conditional GIN(trgm) indexes on foods (Postgres)

Revision ID: 202604060001
Revises: 202603110001
Create Date: 2026-04-06

Enables the pg_trgm extension for future PostgreSQL-native trigram candidate
lanes.  When public.foods exists (catalog colocated on the app database),
creates GIN indexes on canonical_name, group_name, and brand.

SQLite: no-op.  Downgrade drops only this revision's indexes, not the pg_trgm extension.
See docs/architecture/ADR_SEARCH_PGTRGM_CANDIDATES_LANE_P2.md
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202604060001"
down_revision = "202603110001"
branch_labels = None
depends_on = None

_UPGRADE_TRIGRAM_INDEXES = r"""
DO $pulseplate_pg_trgm$
BEGIN
  IF to_regclass('public.foods') IS NOT NULL THEN
    EXECUTE $sql$
CREATE INDEX IF NOT EXISTS ix_foods_canonical_name_gin_trgm
ON public.foods USING gin (canonical_name gin_trgm_ops)
$sql$;
    EXECUTE $sql$
CREATE INDEX IF NOT EXISTS ix_foods_group_name_gin_trgm
ON public.foods USING gin (group_name gin_trgm_ops)
$sql$;
    EXECUTE $sql$
CREATE INDEX IF NOT EXISTS ix_foods_brand_gin_trgm
ON public.foods USING gin (brand gin_trgm_ops)
$sql$;
  END IF;
END
$pulseplate_pg_trgm$;
"""

_DOWNGRADE_DROP_INDEXES = """
DO $pulseplate_pg_trgm$
BEGIN
  IF to_regclass('public.foods') IS NOT NULL THEN
    EXECUTE 'DROP INDEX IF EXISTS public.ix_foods_canonical_name_gin_trgm';
    EXECUTE 'DROP INDEX IF EXISTS public.ix_foods_group_name_gin_trgm';
    EXECUTE 'DROP INDEX IF EXISTS public.ix_foods_brand_gin_trgm';
  END IF;
END
$pulseplate_pg_trgm$;
"""


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(_UPGRADE_TRIGRAM_INDEXES)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "postgresql":
        return

    op.execute(_DOWNGRADE_DROP_INDEXES)
    # Intentionally do not DROP EXTENSION pg_trgm: upgrade uses CREATE IF NOT EXISTS, so this
    # revision does not own extension lifecycle; the extension may pre-exist or be shared.

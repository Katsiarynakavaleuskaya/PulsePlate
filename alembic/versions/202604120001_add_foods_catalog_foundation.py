"""add repo-aligned foods catalog foundation and restaurant schema

Revision ID: 202604120001
Revises: 202604060001
Create Date: 2026-04-12

Additive-only foundation revision that:
- creates `foods` aligned to the current runtime/local catalog vocabulary,
- creates future relational `restaurant_chains` + `restaurant_menu_items` tables,
- closes the PostgreSQL pg_trgm seam introduced in 202604060001.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202604120001"
down_revision = "202604060001"
branch_labels = None
depends_on = None


def _json_type() -> sa.JSON:
    """RU: Диалект-безопасный JSON/JSONB. EN: Dialect-safe JSON/JSONB."""

    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _table_exists(table_name: str) -> bool:
    """RU: Проверить наличие таблицы. EN: Check whether a table already exists."""

    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    """RU: Проверить наличие индекса. EN: Check whether an index already exists."""

    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


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


def upgrade() -> None:
    """Create repo-aligned foods catalog foundation tables."""

    if not _table_exists("foods"):
        op.create_table(
            "foods",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("canonical_name", sa.Text(), nullable=False),
            sa.Column("group_name", sa.Text(), nullable=False),
            sa.Column("per_g", sa.Numeric(8, 2), nullable=False, server_default="100.00"),
            sa.Column("kcal", sa.Numeric(8, 2), nullable=False),
            sa.Column("protein_g", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
            sa.Column("fat_g", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
            sa.Column("carbs_g", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
            sa.Column("fiber_g", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
            sa.Column("Fe_mg", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("Ca_mg", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("K_mg", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("Mg_mg", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("VitD_IU", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("B12_ug", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("Folate_ug", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("Iodine_ug", sa.Numeric(10, 3), nullable=False, server_default="0.000"),
            sa.Column("flags", _json_type(), nullable=False, server_default="[]"),
            sa.Column("brand", sa.Text(), nullable=True),
            sa.Column("gtin", sa.Text(), nullable=True),
            sa.Column("fdc_id", sa.Text(), nullable=True),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("source_priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("version_date", sa.String(length=64), nullable=False),
            sa.Column("price_per_100g", sa.Numeric(10, 2), nullable=True),
            sa.Column("nutrition_inputs_json", _json_type(), nullable=True),
            sa.Column("nutrition_provenance_json", _json_type(), nullable=True),
            sa.Column("nutrition_confidence", sa.Numeric(4, 3), nullable=True),
            sa.Column("nutrition_nutrient_confidence_json", _json_type(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("foods", "ix_foods_canonical_name"):
        op.create_index("ix_foods_canonical_name", "foods", ["canonical_name"], unique=False)
    if not _index_exists("foods", "ix_foods_group_name"):
        op.create_index("ix_foods_group_name", "foods", ["group_name"], unique=False)
    if not _index_exists("foods", "ix_foods_source"):
        op.create_index("ix_foods_source", "foods", ["source"], unique=False)
    if not _index_exists("foods", "ix_foods_gtin"):
        op.create_index("ix_foods_gtin", "foods", ["gtin"], unique=False)

    if not _table_exists("restaurant_chains"):
        op.create_table(
            "restaurant_chains",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("country", sa.String(length=16), nullable=True),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("source_id", sa.Text(), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("restaurant_chains", "ix_restaurant_chains_name"):
        op.create_index("ix_restaurant_chains_name", "restaurant_chains", ["name"], unique=False)

    if not _table_exists("restaurant_menu_items"):
        op.create_table(
            "restaurant_menu_items",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("chain_id", sa.Text(), nullable=False),
            sa.Column("food_id", sa.Text(), nullable=True),
            sa.Column("item_name", sa.Text(), nullable=False),
            sa.Column("category", sa.Text(), nullable=True),
            sa.Column("serving_size_g", sa.Numeric(10, 2), nullable=True),
            sa.Column("kcal", sa.Numeric(8, 2), nullable=True),
            sa.Column("protein_g", sa.Numeric(8, 2), nullable=True),
            sa.Column("fat_g", sa.Numeric(8, 2), nullable=True),
            sa.Column("carbs_g", sa.Numeric(8, 2), nullable=True),
            sa.Column("sodium_mg", sa.Numeric(10, 2), nullable=True),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("source_id", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["chain_id"],
                ["restaurant_chains.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["food_id"],
                ["foods.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("restaurant_menu_items", "ix_restaurant_menu_items_chain_id"):
        op.create_index(
            "ix_restaurant_menu_items_chain_id",
            "restaurant_menu_items",
            ["chain_id"],
            unique=False,
        )
    if not _index_exists("restaurant_menu_items", "ix_restaurant_menu_items_item_name"):
        op.create_index(
            "ix_restaurant_menu_items_item_name",
            "restaurant_menu_items",
            ["item_name"],
            unique=False,
        )
    if not _index_exists("restaurant_menu_items", "ix_restaurant_menu_items_food_id"):
        op.create_index(
            "ix_restaurant_menu_items_food_id",
            "restaurant_menu_items",
            ["food_id"],
            unique=False,
        )

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(_UPGRADE_TRIGRAM_INDEXES)


def downgrade() -> None:
    """Drop repo-aligned foods catalog foundation tables."""

    if _index_exists("restaurant_menu_items", "ix_restaurant_menu_items_food_id"):
        op.drop_index("ix_restaurant_menu_items_food_id", table_name="restaurant_menu_items")
    if _index_exists("restaurant_menu_items", "ix_restaurant_menu_items_item_name"):
        op.drop_index("ix_restaurant_menu_items_item_name", table_name="restaurant_menu_items")
    if _index_exists("restaurant_menu_items", "ix_restaurant_menu_items_chain_id"):
        op.drop_index(
            "ix_restaurant_menu_items_chain_id",
            table_name="restaurant_menu_items",
        )
    if _table_exists("restaurant_menu_items"):
        op.drop_table("restaurant_menu_items")

    if _index_exists("restaurant_chains", "ix_restaurant_chains_name"):
        op.drop_index("ix_restaurant_chains_name", table_name="restaurant_chains")
    if _table_exists("restaurant_chains"):
        op.drop_table("restaurant_chains")

    if _index_exists("foods", "ix_foods_gtin"):
        op.drop_index("ix_foods_gtin", table_name="foods")
    if _index_exists("foods", "ix_foods_source"):
        op.drop_index("ix_foods_source", table_name="foods")
    if _index_exists("foods", "ix_foods_group_name"):
        op.drop_index("ix_foods_group_name", table_name="foods")
    if _index_exists("foods", "ix_foods_canonical_name"):
        op.drop_index("ix_foods_canonical_name", table_name="foods")
    if _table_exists("foods"):
        op.drop_table("foods")

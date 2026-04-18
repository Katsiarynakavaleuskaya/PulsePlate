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

_OWNERSHIP_REGISTRY_TABLE = "pulseplate_migration_ownership"
_OBJECT_TYPE_TABLE = "table"
_OBJECT_TYPE_INDEX = "index"
_INSERT_OWNED_OBJECT_SQL = sa.text("""
    INSERT INTO pulseplate_migration_ownership
        (revision_id, object_type, table_name, object_name)
    VALUES
        (:revision_id, :object_type, :table_name, :object_name)
    """)
_SELECT_OWNED_OBJECT_SQL = sa.text("""
    SELECT 1
    FROM pulseplate_migration_ownership
    WHERE revision_id = :revision_id
      AND object_type = :object_type
      AND table_name = :table_name
      AND object_name = :object_name
    LIMIT 1
    """)
_DELETE_OWNED_OBJECT_SQL = sa.text("""
    DELETE FROM pulseplate_migration_ownership
    WHERE revision_id = :revision_id
      AND object_type = :object_type
      AND table_name = :table_name
      AND object_name = :object_name
    """)
_COUNT_OWNED_OBJECTS_SQL = sa.text("""
    SELECT COUNT(*)
    FROM pulseplate_migration_ownership
    """)


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


def _ownership_registry_exists() -> bool:
    """RU: Проверить наличие реестра владения. EN: Check whether ownership registry exists."""

    return _table_exists(_OWNERSHIP_REGISTRY_TABLE)


def _ensure_ownership_registry() -> None:
    """RU: Создать реестр владения при первом owned object. EN: Create registry on first owned object."""

    if _ownership_registry_exists():
        return
    op.create_table(
        _OWNERSHIP_REGISTRY_TABLE,
        sa.Column("revision_id", sa.String(length=32), nullable=False),
        sa.Column("object_type", sa.String(length=16), nullable=False),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("object_name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("revision_id", "object_type", "object_name"),
    )


def _record_owned_object(object_type: str, table_name: str, object_name: str) -> None:
    """RU: Записать объект, созданный этой ревизией. EN: Record object created by this revision."""

    _ensure_ownership_registry()
    bind = op.get_bind()
    if _owned_object_exists(object_type, table_name, object_name):
        return
    bind.execute(
        _INSERT_OWNED_OBJECT_SQL,
        {
            "revision_id": revision,
            "object_type": object_type,
            "table_name": table_name,
            "object_name": object_name,
        },
    )


def _owned_object_exists(object_type: str, table_name: str, object_name: str) -> bool:
    """RU: Проверить, что объект принадлежит ревизии. EN: Check whether object is owned by revision."""

    if not _ownership_registry_exists():
        return False
    bind = op.get_bind()
    result = bind.execute(
        _SELECT_OWNED_OBJECT_SQL,
        {
            "revision_id": revision,
            "object_type": object_type,
            "table_name": table_name,
            "object_name": object_name,
        },
    ).scalar()
    return result is not None


def _remove_owned_object_record(object_type: str, table_name: str, object_name: str) -> None:
    """RU: Удалить ownership marker после rollback. EN: Remove ownership marker after rollback."""

    if not _ownership_registry_exists():
        return
    op.get_bind().execute(
        _DELETE_OWNED_OBJECT_SQL,
        {
            "revision_id": revision,
            "object_type": object_type,
            "table_name": table_name,
            "object_name": object_name,
        },
    )


def _drop_ownership_registry_if_empty() -> None:
    """RU: Убрать пустой registry. EN: Drop empty ownership registry."""

    if not _ownership_registry_exists():
        return
    remaining = op.get_bind().execute(_COUNT_OWNED_OBJECTS_SQL).scalar_one()
    if remaining == 0:
        op.drop_table(_OWNERSHIP_REGISTRY_TABLE)


def _create_owned_table(
    table_name: str,
    *columns: sa.Column | sa.ForeignKeyConstraint | sa.PrimaryKeyConstraint,
) -> None:
    """RU: Создать таблицу и пометить ownership. EN: Create table and mark ownership."""

    if _table_exists(table_name):
        return
    op.create_table(table_name, *columns)
    _record_owned_object(_OBJECT_TYPE_TABLE, table_name, table_name)


def _create_owned_index(index_name: str, table_name: str, columns: list[str]) -> None:
    """RU: Создать индекс и пометить ownership. EN: Create index and mark ownership."""

    if _index_exists(table_name, index_name):
        return
    op.create_index(index_name, table_name, columns, unique=False)
    _record_owned_object(_OBJECT_TYPE_INDEX, table_name, index_name)


def _create_owned_postgres_index(index_name: str, ddl: str) -> None:
    """RU: Создать postgres-only индекс и пометить ownership.

    EN: Create Postgres-only index and mark ownership.
    """

    if _index_exists("foods", index_name):
        return
    op.execute(ddl)
    _record_owned_object(_OBJECT_TYPE_INDEX, "foods", index_name)


def _drop_owned_index(index_name: str, table_name: str) -> None:
    """RU: Удалить только owned index. EN: Drop only revision-owned index."""

    if not _owned_object_exists(_OBJECT_TYPE_INDEX, table_name, index_name):
        return
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)
    _remove_owned_object_record(_OBJECT_TYPE_INDEX, table_name, index_name)


def _drop_owned_table(table_name: str) -> None:
    """RU: Удалить только owned table. EN: Drop only revision-owned table."""

    if not _owned_object_exists(_OBJECT_TYPE_TABLE, table_name, table_name):
        return
    if _table_exists(table_name):
        op.drop_table(table_name)
    _remove_owned_object_record(_OBJECT_TYPE_TABLE, table_name, table_name)


def upgrade() -> None:
    """Create repo-aligned foods catalog foundation tables."""

    _create_owned_table(
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
    _create_owned_index("ix_foods_canonical_name", "foods", ["canonical_name"])
    _create_owned_index("ix_foods_group_name", "foods", ["group_name"])
    _create_owned_index("ix_foods_source", "foods", ["source"])
    _create_owned_index("ix_foods_gtin", "foods", ["gtin"])

    _create_owned_table(
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
    _create_owned_index("ix_restaurant_chains_name", "restaurant_chains", ["name"])

    _create_owned_table(
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
    _create_owned_index(
        "ix_restaurant_menu_items_chain_id",
        "restaurant_menu_items",
        ["chain_id"],
    )
    _create_owned_index(
        "ix_restaurant_menu_items_item_name",
        "restaurant_menu_items",
        ["item_name"],
    )
    _create_owned_index(
        "ix_restaurant_menu_items_food_id",
        "restaurant_menu_items",
        ["food_id"],
    )

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        _create_owned_postgres_index(
            "ix_foods_canonical_name_gin_trgm",
            "CREATE INDEX ix_foods_canonical_name_gin_trgm ON public.foods USING gin (canonical_name gin_trgm_ops)",
        )
        _create_owned_postgres_index(
            "ix_foods_group_name_gin_trgm",
            "CREATE INDEX ix_foods_group_name_gin_trgm ON public.foods USING gin (group_name gin_trgm_ops)",
        )
        _create_owned_postgres_index(
            "ix_foods_brand_gin_trgm",
            "CREATE INDEX ix_foods_brand_gin_trgm ON public.foods USING gin (brand gin_trgm_ops)",
        )


def downgrade() -> None:
    """Drop repo-aligned foods catalog foundation tables."""

    _drop_owned_index("ix_restaurant_menu_items_food_id", "restaurant_menu_items")
    _drop_owned_index("ix_restaurant_menu_items_item_name", "restaurant_menu_items")
    _drop_owned_index("ix_restaurant_menu_items_chain_id", "restaurant_menu_items")
    _drop_owned_table("restaurant_menu_items")

    _drop_owned_index("ix_restaurant_chains_name", "restaurant_chains")
    _drop_owned_table("restaurant_chains")

    _drop_owned_index("ix_foods_brand_gin_trgm", "foods")
    _drop_owned_index("ix_foods_group_name_gin_trgm", "foods")
    _drop_owned_index("ix_foods_canonical_name_gin_trgm", "foods")
    _drop_owned_index("ix_foods_gtin", "foods")
    _drop_owned_index("ix_foods_source", "foods")
    _drop_owned_index("ix_foods_group_name", "foods")
    _drop_owned_index("ix_foods_canonical_name", "foods")
    _drop_owned_table("foods")
    _drop_ownership_registry_if_empty()

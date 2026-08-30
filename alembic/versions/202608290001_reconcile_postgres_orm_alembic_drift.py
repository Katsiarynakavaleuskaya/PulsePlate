"""Adopt historical unique indexes as canonical unique constraints.

Revision ID: 202608290001
Revises: 202608270001
Create Date: 2026-08-29

PostgreSQL can attach an existing unique index to a constraint without an
enforcement gap.  SQLite represents both historical objects with unique index
semantics and therefore requires no physical rewrite for this PostgreSQL drift
reconciliation.
"""

from __future__ import annotations

from typing import NamedTuple

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "202608290001"
down_revision = "202608270001"
branch_labels = None
depends_on = None


class _ExpectedIndex(NamedTuple):
    table_name: str
    index_name: str
    key_columns: tuple[str, ...]


class _IndexDescriptor(NamedTuple):
    table_schema: str
    table_name: str
    index_schema: str
    index_name: str
    key_columns: tuple[str | None, ...]
    access_method: str
    is_unique: bool
    is_valid: bool
    is_ready: bool
    is_live: bool
    nulls_not_distinct: bool
    key_options: tuple[int, ...]
    key_opclasses_default: tuple[bool, ...]
    key_collations_match: tuple[bool, ...]
    predicate: str | None
    expressions: str | None
    included_column_count: int
    constraint_owner: str | None


_EXPECTED_INDEXES = (
    _ExpectedIndex(
        table_name="analyzer_state",
        index_name="uq_analyzer_state_user_key",
        key_columns=("user_id", "analyzer_key"),
    ),
    _ExpectedIndex(
        table_name="day_plans",
        index_name="ix_day_plans_user_date",
        key_columns=("user_id", "date"),
    ),
)


def _require_adoptable_index(
    descriptor: _IndexDescriptor,
    expected: _ExpectedIndex,
) -> None:
    """Fail closed unless one index is the exact safe adoption candidate."""

    checks = (
        ("table_schema", descriptor.table_schema == "public"),
        ("table_name", descriptor.table_name == expected.table_name),
        ("index_schema", descriptor.index_schema == "public"),
        ("index_name", descriptor.index_name == expected.index_name),
        ("key_columns", descriptor.key_columns == expected.key_columns),
        ("access_method", descriptor.access_method == "btree"),
        ("unique", descriptor.is_unique is True),
        ("valid", descriptor.is_valid is True),
        ("ready", descriptor.is_ready is True),
        ("live", descriptor.is_live is True),
        ("nulls_not_distinct", descriptor.nulls_not_distinct is False),
        ("key_options", descriptor.key_options == (0,) * len(expected.key_columns)),
        (
            "key_opclasses",
            descriptor.key_opclasses_default == (True,) * len(expected.key_columns),
        ),
        (
            "key_collations",
            descriptor.key_collations_match == (True,) * len(expected.key_columns),
        ),
        ("predicate", descriptor.predicate is None),
        ("expressions", descriptor.expressions is None),
        ("include_columns", descriptor.included_column_count == 0),
        ("constraint_owner", descriptor.constraint_owner is None),
    )
    for reason, accepted in checks:
        if not accepted:
            raise RuntimeError(f"index_admission_failed:{expected.index_name}:{reason}")


def _load_index_descriptor(bind: Connection, expected: _ExpectedIndex) -> _IndexDescriptor:
    """Read one bounded public index descriptor from PostgreSQL catalogs."""

    rows = (
        bind.execute(
            sa.text("""
            SELECT
                table_namespace.nspname AS table_schema,
                table_relation.relname AS table_name,
                index_namespace.nspname AS index_schema,
                index_relation.relname AS index_name,
                ARRAY(
                    SELECT CASE
                        WHEN index_key.attribute_number = 0 THEN NULL
                        ELSE attribute.attname
                    END
                    FROM pg_catalog.unnest(index_state.indkey) WITH ORDINALITY
                        AS index_key(attribute_number, position)
                    LEFT JOIN pg_catalog.pg_attribute AS attribute
                      ON attribute.attrelid = table_relation.oid
                     AND attribute.attnum = index_key.attribute_number
                    WHERE index_key.position <= index_state.indnkeyatts
                    ORDER BY index_key.position
                ) AS key_columns,
                access_method.amname AS access_method,
                index_state.indisunique AS is_unique,
                index_state.indisvalid AS is_valid,
                index_state.indisready AS is_ready,
                index_state.indislive AS is_live,
                index_state.indnullsnotdistinct AS nulls_not_distinct,
                ARRAY(
                    SELECT index_option.option_value
                    FROM pg_catalog.unnest(index_state.indoption) WITH ORDINALITY
                        AS index_option(option_value, position)
                    WHERE index_option.position <= index_state.indnkeyatts
                    ORDER BY index_option.position
                ) AS key_options,
                ARRAY(
                    SELECT selected_opclass.opcdefault
                    FROM pg_catalog.unnest(index_state.indclass) WITH ORDINALITY
                        AS index_opclass(opclass_oid, position)
                    JOIN pg_catalog.pg_opclass AS selected_opclass
                      ON selected_opclass.oid = index_opclass.opclass_oid
                    WHERE index_opclass.position <= index_state.indnkeyatts
                    ORDER BY index_opclass.position
                ) AS key_opclasses_default,
                ARRAY(
                    SELECT index_collation.collation_oid = attribute.attcollation
                    FROM pg_catalog.unnest(index_state.indcollation) WITH ORDINALITY
                        AS index_collation(collation_oid, position)
                    JOIN pg_catalog.unnest(index_state.indkey) WITH ORDINALITY
                        AS collation_key(attribute_number, position)
                      ON collation_key.position = index_collation.position
                    JOIN pg_catalog.pg_attribute AS attribute
                      ON attribute.attrelid = table_relation.oid
                     AND attribute.attnum = collation_key.attribute_number
                    WHERE index_collation.position <= index_state.indnkeyatts
                    ORDER BY index_collation.position
                ) AS key_collations_match,
                pg_catalog.pg_get_expr(index_state.indpred, index_state.indrelid) AS predicate,
                pg_catalog.pg_get_expr(index_state.indexprs, index_state.indrelid) AS expressions,
                index_state.indnatts - index_state.indnkeyatts AS included_column_count,
                constraint_state.conname AS constraint_owner
            FROM pg_catalog.pg_index AS index_state
            JOIN pg_catalog.pg_class AS index_relation
              ON index_relation.oid = index_state.indexrelid
            JOIN pg_catalog.pg_namespace AS index_namespace
              ON index_namespace.oid = index_relation.relnamespace
            JOIN pg_catalog.pg_class AS table_relation
              ON table_relation.oid = index_state.indrelid
            JOIN pg_catalog.pg_namespace AS table_namespace
              ON table_namespace.oid = table_relation.relnamespace
            JOIN pg_catalog.pg_am AS access_method
              ON access_method.oid = index_relation.relam
            LEFT JOIN pg_catalog.pg_constraint AS constraint_state
              ON constraint_state.conindid = index_state.indexrelid
            WHERE table_namespace.nspname = :schema_name
              AND table_relation.relname = :table_name
              AND index_namespace.nspname = :schema_name
              AND index_relation.relname = :index_name
            """),
            {
                "schema_name": "public",
                "table_name": expected.table_name,
                "index_name": expected.index_name,
            },
        )
        .mappings()
        .all()
    )
    if len(rows) != 1:
        raise RuntimeError(f"index_admission_failed:{expected.index_name}:cardinality")
    row = rows[0]
    raw_columns = row["key_columns"]
    if not isinstance(raw_columns, (list, tuple)):
        raise RuntimeError(f"index_admission_failed:{expected.index_name}:key_columns_shape")
    raw_key_options = row["key_options"]
    if not isinstance(raw_key_options, (list, tuple)):
        raise RuntimeError(f"index_admission_failed:{expected.index_name}:key_options_shape")
    raw_opclass_defaults = row["key_opclasses_default"]
    if not isinstance(raw_opclass_defaults, (list, tuple)):
        raise RuntimeError(f"index_admission_failed:{expected.index_name}:key_opclasses_shape")
    raw_collation_matches = row["key_collations_match"]
    if not isinstance(raw_collation_matches, (list, tuple)):
        raise RuntimeError(f"index_admission_failed:{expected.index_name}:key_collations_shape")
    return _IndexDescriptor(
        table_schema=str(row["table_schema"]),
        table_name=str(row["table_name"]),
        index_schema=str(row["index_schema"]),
        index_name=str(row["index_name"]),
        key_columns=tuple(None if value is None else str(value) for value in raw_columns),
        access_method=str(row["access_method"]),
        is_unique=bool(row["is_unique"]),
        is_valid=bool(row["is_valid"]),
        is_ready=bool(row["is_ready"]),
        is_live=bool(row["is_live"]),
        nulls_not_distinct=bool(row["nulls_not_distinct"]),
        key_options=tuple(int(value) for value in raw_key_options),
        key_opclasses_default=tuple(bool(value) for value in raw_opclass_defaults),
        key_collations_match=tuple(bool(value) for value in raw_collation_matches),
        predicate=None if row["predicate"] is None else str(row["predicate"]),
        expressions=None if row["expressions"] is None else str(row["expressions"]),
        included_column_count=int(row["included_column_count"]),
        constraint_owner=(
            None if row["constraint_owner"] is None else str(row["constraint_owner"])
        ),
    )


def upgrade() -> None:
    """Adopt the two existing PostgreSQL unique indexes losslessly."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("SET LOCAL search_path TO pg_catalog, public")
    op.execute("LOCK TABLE public.analyzer_state, public.day_plans " "IN ACCESS EXCLUSIVE MODE")
    descriptors = tuple(_load_index_descriptor(bind, expected) for expected in _EXPECTED_INDEXES)
    for descriptor, expected in zip(descriptors, _EXPECTED_INDEXES, strict=True):
        _require_adoptable_index(descriptor, expected)

    op.execute(
        "ALTER TABLE public.analyzer_state "
        "ADD CONSTRAINT uq_analyzer_state_user_key "
        "UNIQUE USING INDEX uq_analyzer_state_user_key"
    )
    op.execute(
        "ALTER TABLE public.day_plans "
        "ADD CONSTRAINT uq_day_plans_user_date "
        "UNIQUE USING INDEX ix_day_plans_user_date"
    )


def downgrade() -> None:
    """Restore the exact historical unique-index names without an enforcement gap."""

    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        "CREATE UNIQUE INDEX ix_day_plans_user_date_restore " "ON public.day_plans (user_id, date)"
    )
    op.execute("ALTER TABLE public.day_plans DROP CONSTRAINT uq_day_plans_user_date")
    op.execute(
        "ALTER INDEX public.ix_day_plans_user_date_restore " "RENAME TO ix_day_plans_user_date"
    )

    op.execute(
        "CREATE UNIQUE INDEX uq_analyzer_state_user_key_restore "
        "ON public.analyzer_state (user_id, analyzer_key)"
    )
    op.execute("ALTER TABLE public.analyzer_state DROP CONSTRAINT uq_analyzer_state_user_key")
    op.execute(
        "ALTER INDEX public.uq_analyzer_state_user_key_restore "
        "RENAME TO uq_analyzer_state_user_key"
    )

"""Bounded Alembic autogenerate admission for disposable PostgreSQL.

The caller owns database creation, identity verification, migration execution,
and cleanup. This module only evaluates one already-upgraded connection. It
recognizes four exact migration-only public table roots, validates their closed
physical descriptor projection, and then proves that the admitted Alembic
comparison is empty. It makes no production-parity or deployment-safety claim.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Literal
import warnings

from alembic.autogenerate import produce_migrations
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.schema import MetaData

from core.db_alembic_comparison import (
    AUTOGENERATE_EXEMPT_TABLE_ROOTS,
    compare_postgresql_server_default,
    include_autogenerate_object,
    proven_autogenerate_default_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INTERNAL_TABLE_ROOTS = frozenset({("public", "alembic_version")})
ADMISSION_RESULT_CLAIM = "bounded_exact_head_autogenerate_admission=PASS"
FOUNDATION_REVISION = "202604120001"
OBSERVED_IDENTITY_CAP = 64
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,126}$")

Result = Literal["pass", "fail"]
ValidationState = Literal["not_run", "passed", "failed"]


@dataclass(frozen=True, slots=True, order=True)
class OperationLeaf:
    """One semantic Alembic leaf with a bounded database identity."""

    operation: str
    schema: str
    table_name: str
    object_name: str


@dataclass(frozen=True, slots=True, order=True)
class ColumnDescriptor:
    table_name: str
    ordinal_position: int
    name: str
    formatted_type: str
    nullable: bool
    default: str | None = None
    identity: str | None = None
    generated: str | None = None


@dataclass(frozen=True, slots=True, order=True)
class PrimaryKeyDescriptor:
    table_name: str
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True, order=True)
class ForeignKeyDescriptor:
    table_name: str
    columns: tuple[str, ...]
    referred_schema: str
    referred_table: str
    referred_columns: tuple[str, ...]
    on_update: str
    on_delete: str


@dataclass(frozen=True, slots=True, order=True)
class NamedConstraintDescriptor:
    table_name: str
    kind: str
    name: str
    definition: str


@dataclass(frozen=True, slots=True, order=True)
class IndexDescriptor:
    table_name: str
    name: str
    key_columns: tuple[str, ...]
    included_columns: tuple[str, ...]
    access_method: str
    opclasses: tuple[str, ...]
    key_options: tuple[int, ...]
    unique: bool
    valid: bool
    ready: bool
    live: bool
    nulls_not_distinct: bool
    predicate: str | None
    expression: str | None
    constraint_owner: str | None


@dataclass(frozen=True, slots=True, order=True)
class RlsDescriptor:
    table_name: str
    enabled: bool
    forced: bool
    policy_count: int


@dataclass(frozen=True, slots=True)
class BoundedAutogenerateAdmissionReport:
    """Secret-free result for the exact current-head admission contract."""

    result: Result
    claim: str | None
    migration_head: str | None
    database_head: str | None
    default_schema_name: str | None
    canonical_table_roots: tuple[str, ...]
    exempt_table_roots: tuple[str, ...]
    public_table_roots: tuple[str, ...]
    raw_leaf_operations: tuple[OperationLeaf, ...]
    admitted_leaf_operations: tuple[OperationLeaf, ...]
    warning_categories: tuple[str, ...]
    descriptor_validation: ValidationState
    reason_codes: tuple[str, ...]
    observed_identities: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""

        return asdict(self)

    def to_json(self) -> str:
        """Serialize only bounded identities and stable reason codes."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def _columns(
    table_name: str,
    definitions: Sequence[tuple[str, str, bool, str | None]],
) -> tuple[ColumnDescriptor, ...]:
    return tuple(
        ColumnDescriptor(
            table_name=table_name,
            ordinal_position=position,
            name=name,
            formatted_type=formatted_type,
            nullable=nullable,
            default=default,
        )
        for position, (name, formatted_type, nullable, default) in enumerate(
            definitions,
            start=1,
        )
    )


EXPECTED_COLUMNS = tuple(
    sorted(
        (
            *_columns(
                "pulseplate_migration_ownership",
                (
                    ("revision_id", "character varying(32)", False, None),
                    ("object_type", "character varying(16)", False, None),
                    ("table_name", "character varying(128)", False, None),
                    ("object_name", "character varying(128)", False, None),
                ),
            ),
            *_columns(
                "foods",
                (
                    ("id", "text", False, None),
                    ("canonical_name", "text", False, None),
                    ("group_name", "text", False, None),
                    ("per_g", "numeric(8,2)", False, "100.00"),
                    ("kcal", "numeric(8,2)", False, None),
                    ("protein_g", "numeric(8,2)", False, "0.00"),
                    ("fat_g", "numeric(8,2)", False, "0.00"),
                    ("carbs_g", "numeric(8,2)", False, "0.00"),
                    ("fiber_g", "numeric(8,2)", False, "0.00"),
                    ("Fe_mg", "numeric(10,3)", False, "0.000"),
                    ("Ca_mg", "numeric(10,3)", False, "0.000"),
                    ("K_mg", "numeric(10,3)", False, "0.000"),
                    ("Mg_mg", "numeric(10,3)", False, "0.000"),
                    ("VitD_IU", "numeric(10,3)", False, "0.000"),
                    ("B12_ug", "numeric(10,3)", False, "0.000"),
                    ("Folate_ug", "numeric(10,3)", False, "0.000"),
                    ("Iodine_ug", "numeric(10,3)", False, "0.000"),
                    ("flags", "jsonb", False, "[]"),
                    ("brand", "text", True, None),
                    ("gtin", "text", True, None),
                    ("fdc_id", "text", True, None),
                    ("source", "text", False, None),
                    ("source_priority", "integer", False, "0"),
                    ("version_date", "character varying(64)", False, None),
                    ("price_per_100g", "numeric(10,2)", True, None),
                    ("nutrition_inputs_json", "jsonb", True, None),
                    ("nutrition_provenance_json", "jsonb", True, None),
                    ("nutrition_confidence", "numeric(4,3)", True, None),
                    ("nutrition_nutrient_confidence_json", "jsonb", True, None),
                ),
            ),
            *_columns(
                "restaurant_chains",
                (
                    ("id", "text", False, None),
                    ("name", "text", False, None),
                    ("country", "character varying(16)", True, None),
                    ("source", "text", False, None),
                    ("source_id", "text", True, None),
                    ("updated_at", "timestamp with time zone", False, "current_timestamp"),
                ),
            ),
            *_columns(
                "restaurant_menu_items",
                (
                    ("id", "text", False, None),
                    ("chain_id", "text", False, None),
                    ("food_id", "text", True, None),
                    ("item_name", "text", False, None),
                    ("category", "text", True, None),
                    ("serving_size_g", "numeric(10,2)", True, None),
                    ("kcal", "numeric(8,2)", True, None),
                    ("protein_g", "numeric(8,2)", True, None),
                    ("fat_g", "numeric(8,2)", True, None),
                    ("carbs_g", "numeric(8,2)", True, None),
                    ("sodium_mg", "numeric(10,2)", True, None),
                    ("source", "text", False, None),
                    ("source_id", "text", True, None),
                    ("is_active", "boolean", False, "true"),
                    ("updated_at", "timestamp with time zone", False, "current_timestamp"),
                ),
            ),
        )
    )
)

EXPECTED_PRIMARY_KEYS = tuple(
    sorted(
        (
            PrimaryKeyDescriptor(
                "pulseplate_migration_ownership",
                ("revision_id", "object_type", "table_name", "object_name"),
            ),
            PrimaryKeyDescriptor("foods", ("id",)),
            PrimaryKeyDescriptor("restaurant_chains", ("id",)),
            PrimaryKeyDescriptor("restaurant_menu_items", ("id",)),
        )
    )
)

EXPECTED_FOREIGN_KEYS = tuple(
    sorted(
        (
            ForeignKeyDescriptor(
                "restaurant_menu_items",
                ("chain_id",),
                "public",
                "restaurant_chains",
                ("id",),
                "NO ACTION",
                "CASCADE",
            ),
            ForeignKeyDescriptor(
                "restaurant_menu_items",
                ("food_id",),
                "public",
                "foods",
                ("id",),
                "NO ACTION",
                "SET NULL",
            ),
        )
    )
)

EXPECTED_INDEXES = tuple(
    sorted(
        IndexDescriptor(
            table_name=table_name,
            name=index_name,
            key_columns=(column_name,),
            included_columns=(),
            access_method=method,
            opclasses=(opclass,),
            key_options=(0,),
            unique=False,
            valid=True,
            ready=True,
            live=True,
            nulls_not_distinct=False,
            predicate=None,
            expression=None,
            constraint_owner=None,
        )
        for table_name, index_name, column_name, method, opclass in (
            ("foods", "ix_foods_canonical_name", "canonical_name", "btree", "text_ops"),
            ("foods", "ix_foods_group_name", "group_name", "btree", "text_ops"),
            ("foods", "ix_foods_source", "source", "btree", "text_ops"),
            ("foods", "ix_foods_gtin", "gtin", "btree", "text_ops"),
            (
                "foods",
                "ix_foods_canonical_name_gin_trgm",
                "canonical_name",
                "gin",
                "gin_trgm_ops",
            ),
            (
                "foods",
                "ix_foods_group_name_gin_trgm",
                "group_name",
                "gin",
                "gin_trgm_ops",
            ),
            ("foods", "ix_foods_brand_gin_trgm", "brand", "gin", "gin_trgm_ops"),
            (
                "restaurant_chains",
                "ix_restaurant_chains_name",
                "name",
                "btree",
                "text_ops",
            ),
            (
                "restaurant_menu_items",
                "ix_restaurant_menu_items_chain_id",
                "chain_id",
                "btree",
                "text_ops",
            ),
            (
                "restaurant_menu_items",
                "ix_restaurant_menu_items_item_name",
                "item_name",
                "btree",
                "text_ops",
            ),
            (
                "restaurant_menu_items",
                "ix_restaurant_menu_items_food_id",
                "food_id",
                "btree",
                "text_ops",
            ),
        )
    )
)

EXPECTED_OWNERSHIP_ROWS = tuple(
    sorted(
        (
            *(
                (FOUNDATION_REVISION, "table", table_name, table_name)
                for table_name in ("foods", "restaurant_chains", "restaurant_menu_items")
            ),
            *(
                (FOUNDATION_REVISION, "index", index.table_name, index.name)
                for index in EXPECTED_INDEXES
            ),
        )
    )
)

EXPECTED_RLS = tuple(
    RlsDescriptor(table_name, False, False, 0)
    for table_name in sorted(name for _, name in AUTOGENERATE_EXEMPT_TABLE_ROOTS)
)

EXPECTED_RAW_LEAVES = tuple(
    sorted(
        (
            *(
                OperationLeaf("DropTableOp", schema, table_name, table_name)
                for schema, table_name in AUTOGENERATE_EXEMPT_TABLE_ROOTS
            ),
            *(
                OperationLeaf("DropIndexOp", "public", index.table_name, index.name)
                for index in EXPECTED_INDEXES
            ),
        )
    )
)


def _bounded_identifier(value: object) -> str:
    if isinstance(value, str) and _SAFE_IDENTIFIER.fullmatch(value):
        return value
    return "<invalid>"


def _bounded_identities(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values))[:OBSERVED_IDENTITY_CAP])


def _root_key(schema: str, table_name: str) -> str:
    return f"{_bounded_identifier(schema)}.{_bounded_identifier(table_name)}"


def _make_report(
    *,
    reasons: Sequence[str],
    observed: Sequence[str],
    migration_head: str | None = None,
    database_head: str | None = None,
    default_schema_name: str | None = None,
    canonical_roots: Sequence[str] = (),
    public_roots: Sequence[str] = (),
    raw_leaves: Sequence[OperationLeaf] = (),
    admitted_leaves: Sequence[OperationLeaf] = (),
    warning_categories: Sequence[str] = (),
    descriptor_validation: ValidationState = "not_run",
) -> BoundedAutogenerateAdmissionReport:
    normalized_reasons = tuple(sorted(set(reasons)))
    result: Result = "pass" if not normalized_reasons else "fail"
    return BoundedAutogenerateAdmissionReport(
        result=result,
        claim=ADMISSION_RESULT_CLAIM if result == "pass" else None,
        migration_head=migration_head,
        database_head=database_head,
        default_schema_name=default_schema_name,
        canonical_table_roots=tuple(sorted(canonical_roots)),
        exempt_table_roots=tuple(
            sorted(_root_key(schema, name) for schema, name in AUTOGENERATE_EXEMPT_TABLE_ROOTS)
        ),
        public_table_roots=tuple(sorted(public_roots)),
        raw_leaf_operations=tuple(sorted(raw_leaves)),
        admitted_leaf_operations=tuple(sorted(admitted_leaves)),
        warning_categories=tuple(sorted(set(warning_categories))),
        descriptor_validation=descriptor_validation,
        reason_codes=normalized_reasons,
        observed_identities=_bounded_identities(tuple(observed)),
    )


def _migration_head() -> str | None:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    heads = tuple(ScriptDirectory.from_config(config).get_heads())
    return heads[0] if len(heads) == 1 and isinstance(heads[0], str) and heads[0] else None


def _database_head(connection: Connection) -> str | None:
    rows = connection.exec_driver_sql(
        "SELECT version_num FROM public.alembic_version ORDER BY version_num"
    ).all()
    if len(rows) != 1 or len(rows[0]) != 1:
        return None
    value = rows[0][0]
    return value if isinstance(value, str) and value else None


def _normalize_default(value: object) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().split()).lower()
    while normalized.startswith("(") and normalized.endswith(")"):
        normalized = normalized[1:-1].strip()
    if normalized in {"now()", "current_timestamp"}:
        return "current_timestamp"
    literal = re.fullmatch(r"'(?P<value>(?:[^']|'')*)'::[a-z0-9_ ]+", normalized)
    if literal is not None:
        return literal.group("value").replace("''", "'")
    return normalized


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"descriptor_shape_invalid:{field}")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"descriptor_shape_invalid:{field}")
    return tuple(value)


def _integer_tuple(value: object, *, field: str) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, int) for item in value):
        raise ValueError(f"descriptor_shape_invalid:{field}")
    return tuple(value)


def _read_columns(connection: Connection) -> tuple[ColumnDescriptor, ...]:
    rows = connection.execute(text("""
            SELECT relation.relname AS table_name,
                   attribute.attnum AS ordinal_position,
                   attribute.attname AS column_name,
                   pg_catalog.format_type(attribute.atttypid, attribute.atttypmod)
                       AS formatted_type,
                   attribute.attnotnull AS not_null,
                   pg_catalog.pg_get_expr(default_record.adbin, default_record.adrelid)
                       AS default_expression,
                   NULLIF(attribute.attidentity, '') AS identity_kind,
                   NULLIF(attribute.attgenerated, '') AS generated_kind
            FROM pg_catalog.pg_attribute AS attribute
            JOIN pg_catalog.pg_class AS relation ON relation.oid = attribute.attrelid
            JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            LEFT JOIN pg_catalog.pg_attrdef AS default_record
              ON default_record.adrelid = relation.oid
             AND default_record.adnum = attribute.attnum
            WHERE namespace.nspname = 'public'
              AND relation.relkind IN ('r', 'p')
              AND relation.relname IN (
                  'foods', 'pulseplate_migration_ownership',
                  'restaurant_chains', 'restaurant_menu_items'
              )
              AND attribute.attnum > 0
              AND NOT attribute.attisdropped
            ORDER BY relation.relname COLLATE "C", attribute.attnum
            """)).mappings().all()
    return tuple(
        sorted(
            ColumnDescriptor(
                table_name=str(row["table_name"]),
                ordinal_position=int(row["ordinal_position"]),
                name=str(row["column_name"]),
                formatted_type=str(row["formatted_type"]),
                nullable=row["not_null"] is not True,
                default=_normalize_default(row["default_expression"]),
                identity=None if row["identity_kind"] is None else str(row["identity_kind"]),
                generated=(None if row["generated_kind"] is None else str(row["generated_kind"])),
            )
            for row in rows
        )
    )


def _read_primary_keys(connection: Connection) -> tuple[PrimaryKeyDescriptor, ...]:
    rows = connection.execute(text("""
            SELECT relation.relname AS table_name,
                   ARRAY(
                       SELECT attribute.attname
                       FROM pg_catalog.unnest(constraint_record.conkey) WITH ORDINALITY
                           AS key_record(attribute_number, position)
                       JOIN pg_catalog.pg_attribute AS attribute
                         ON attribute.attrelid = relation.oid
                        AND attribute.attnum = key_record.attribute_number
                       ORDER BY key_record.position
                   ) AS key_columns
            FROM pg_catalog.pg_constraint AS constraint_record
            JOIN pg_catalog.pg_class AS relation ON relation.oid = constraint_record.conrelid
            JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            WHERE namespace.nspname = 'public'
              AND relation.relname IN (
                  'foods', 'pulseplate_migration_ownership',
                  'restaurant_chains', 'restaurant_menu_items'
              )
              AND constraint_record.contype = 'p'
            ORDER BY relation.relname COLLATE "C"
            """)).mappings().all()
    return tuple(
        sorted(
            PrimaryKeyDescriptor(
                str(row["table_name"]),
                _string_tuple(row["key_columns"], field="primary_key_columns"),
            )
            for row in rows
        )
    )


def _read_foreign_keys(connection: Connection) -> tuple[ForeignKeyDescriptor, ...]:
    rows = connection.execute(text("""
            SELECT source_relation.relname AS table_name,
                   ARRAY(
                       SELECT attribute.attname
                       FROM pg_catalog.unnest(constraint_record.conkey) WITH ORDINALITY
                           AS key_record(attribute_number, position)
                       JOIN pg_catalog.pg_attribute AS attribute
                         ON attribute.attrelid = source_relation.oid
                        AND attribute.attnum = key_record.attribute_number
                       ORDER BY key_record.position
                   ) AS source_columns,
                   target_namespace.nspname AS target_schema,
                   target_relation.relname AS target_table,
                   ARRAY(
                       SELECT attribute.attname
                       FROM pg_catalog.unnest(constraint_record.confkey) WITH ORDINALITY
                           AS key_record(attribute_number, position)
                       JOIN pg_catalog.pg_attribute AS attribute
                         ON attribute.attrelid = target_relation.oid
                        AND attribute.attnum = key_record.attribute_number
                       ORDER BY key_record.position
                   ) AS target_columns,
                   CASE constraint_record.confupdtype
                       WHEN 'a' THEN 'NO ACTION' WHEN 'r' THEN 'RESTRICT'
                       WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL'
                       WHEN 'd' THEN 'SET DEFAULT' ELSE '<invalid>'
                   END AS on_update,
                   CASE constraint_record.confdeltype
                       WHEN 'a' THEN 'NO ACTION' WHEN 'r' THEN 'RESTRICT'
                       WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL'
                       WHEN 'd' THEN 'SET DEFAULT' ELSE '<invalid>'
                   END AS on_delete
            FROM pg_catalog.pg_constraint AS constraint_record
            JOIN pg_catalog.pg_class AS source_relation
              ON source_relation.oid = constraint_record.conrelid
            JOIN pg_catalog.pg_namespace AS source_namespace
              ON source_namespace.oid = source_relation.relnamespace
            JOIN pg_catalog.pg_class AS target_relation
              ON target_relation.oid = constraint_record.confrelid
            JOIN pg_catalog.pg_namespace AS target_namespace
              ON target_namespace.oid = target_relation.relnamespace
            WHERE source_namespace.nspname = 'public'
              AND source_relation.relname IN (
                  'foods', 'pulseplate_migration_ownership',
                  'restaurant_chains', 'restaurant_menu_items'
              )
              AND constraint_record.contype = 'f'
            ORDER BY source_relation.relname COLLATE "C", constraint_record.conname COLLATE "C"
            """)).mappings().all()
    return tuple(
        sorted(
            ForeignKeyDescriptor(
                table_name=str(row["table_name"]),
                columns=_string_tuple(row["source_columns"], field="foreign_key_columns"),
                referred_schema=str(row["target_schema"]),
                referred_table=str(row["target_table"]),
                referred_columns=_string_tuple(
                    row["target_columns"], field="foreign_key_target_columns"
                ),
                on_update=str(row["on_update"]),
                on_delete=str(row["on_delete"]),
            )
            for row in rows
        )
    )


def _read_named_constraints(connection: Connection) -> tuple[NamedConstraintDescriptor, ...]:
    rows = connection.execute(text("""
            SELECT relation.relname AS table_name,
                   constraint_record.contype AS constraint_kind,
                   constraint_record.conname AS constraint_name,
                   pg_catalog.pg_get_constraintdef(constraint_record.oid, true) AS definition
            FROM pg_catalog.pg_constraint AS constraint_record
            JOIN pg_catalog.pg_class AS relation ON relation.oid = constraint_record.conrelid
            JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            WHERE namespace.nspname = 'public'
              AND relation.relname IN (
                  'foods', 'pulseplate_migration_ownership',
                  'restaurant_chains', 'restaurant_menu_items'
              )
              AND constraint_record.contype IN ('u', 'c')
            ORDER BY relation.relname COLLATE "C", constraint_record.conname COLLATE "C"
            """)).mappings().all()
    return tuple(
        sorted(
            NamedConstraintDescriptor(
                str(row["table_name"]),
                str(row["constraint_kind"]),
                str(row["constraint_name"]),
                " ".join(str(row["definition"]).split()),
            )
            for row in rows
        )
    )


def _read_indexes(connection: Connection) -> tuple[IndexDescriptor, ...]:
    rows = connection.execute(text("""
            SELECT table_relation.relname AS table_name,
                   index_relation.relname AS index_name,
                   ARRAY(
                       SELECT attribute.attname
                       FROM pg_catalog.unnest(index_state.indkey) WITH ORDINALITY
                           AS key_record(attribute_number, position)
                       JOIN pg_catalog.pg_attribute AS attribute
                         ON attribute.attrelid = table_relation.oid
                        AND attribute.attnum = key_record.attribute_number
                       WHERE key_record.position <= index_state.indnkeyatts
                       ORDER BY key_record.position
                   ) AS key_columns,
                   ARRAY(
                       SELECT attribute.attname
                       FROM pg_catalog.unnest(index_state.indkey) WITH ORDINALITY
                           AS key_record(attribute_number, position)
                       JOIN pg_catalog.pg_attribute AS attribute
                         ON attribute.attrelid = table_relation.oid
                        AND attribute.attnum = key_record.attribute_number
                       WHERE key_record.position > index_state.indnkeyatts
                       ORDER BY key_record.position
                   ) AS included_columns,
                   access_method.amname AS access_method,
                   ARRAY(
                       SELECT selected_opclass.opcname
                       FROM pg_catalog.unnest(index_state.indclass) WITH ORDINALITY
                           AS opclass_record(opclass_oid, position)
                       JOIN pg_catalog.pg_opclass AS selected_opclass
                         ON selected_opclass.oid = opclass_record.opclass_oid
                       WHERE opclass_record.position <= index_state.indnkeyatts
                       ORDER BY opclass_record.position
                   ) AS opclasses,
                   ARRAY(
                       SELECT option_record.option_value
                       FROM pg_catalog.unnest(index_state.indoption) WITH ORDINALITY
                           AS option_record(option_value, position)
                       WHERE option_record.position <= index_state.indnkeyatts
                       ORDER BY option_record.position
                   ) AS key_options,
                   index_state.indisunique AS is_unique,
                   index_state.indisvalid AS is_valid,
                   index_state.indisready AS is_ready,
                   index_state.indislive AS is_live,
                   index_state.indnullsnotdistinct AS nulls_not_distinct,
                   pg_catalog.pg_get_expr(index_state.indpred, index_state.indrelid) AS predicate,
                   pg_catalog.pg_get_expr(index_state.indexprs, index_state.indrelid) AS expression,
                   constraint_state.conname AS constraint_owner
            FROM pg_catalog.pg_index AS index_state
            JOIN pg_catalog.pg_class AS index_relation
              ON index_relation.oid = index_state.indexrelid
            JOIN pg_catalog.pg_class AS table_relation
              ON table_relation.oid = index_state.indrelid
            JOIN pg_catalog.pg_namespace AS namespace
              ON namespace.oid = table_relation.relnamespace
            JOIN pg_catalog.pg_am AS access_method
              ON access_method.oid = index_relation.relam
            LEFT JOIN pg_catalog.pg_constraint AS constraint_state
              ON constraint_state.conindid = index_state.indexrelid
            WHERE namespace.nspname = 'public'
              AND table_relation.relname IN (
                  'foods', 'pulseplate_migration_ownership',
                  'restaurant_chains', 'restaurant_menu_items'
              )
              AND constraint_state.oid IS NULL
            ORDER BY table_relation.relname COLLATE "C", index_relation.relname COLLATE "C"
            """)).mappings().all()
    return tuple(
        sorted(
            IndexDescriptor(
                table_name=str(row["table_name"]),
                name=str(row["index_name"]),
                key_columns=_string_tuple(row["key_columns"], field="index_key_columns"),
                included_columns=_string_tuple(
                    row["included_columns"], field="index_included_columns"
                ),
                access_method=str(row["access_method"]),
                opclasses=_string_tuple(row["opclasses"], field="index_opclasses"),
                key_options=_integer_tuple(row["key_options"], field="index_key_options"),
                unique=row["is_unique"] is True,
                valid=row["is_valid"] is True,
                ready=row["is_ready"] is True,
                live=row["is_live"] is True,
                nulls_not_distinct=row["nulls_not_distinct"] is True,
                predicate=None if row["predicate"] is None else str(row["predicate"]),
                expression=None if row["expression"] is None else str(row["expression"]),
                constraint_owner=(
                    None if row["constraint_owner"] is None else str(row["constraint_owner"])
                ),
            )
            for row in rows
        )
    )


def _read_ownership_rows(connection: Connection) -> tuple[tuple[str, str, str, str], ...]:
    rows = connection.execute(text("""
            SELECT revision_id, object_type, table_name, object_name
            FROM public.pulseplate_migration_ownership
            ORDER BY revision_id COLLATE "C", object_type COLLATE "C",
                     table_name COLLATE "C", object_name COLLATE "C"
            LIMIT 65
            """)).all()
    return tuple((str(row[0]), str(row[1]), str(row[2]), str(row[3])) for row in rows)


def _read_rls(connection: Connection) -> tuple[RlsDescriptor, ...]:
    rows = connection.execute(text("""
            SELECT relation.relname AS table_name,
                   relation.relrowsecurity AS rls_enabled,
                   relation.relforcerowsecurity AS rls_forced,
                   COUNT(policy.oid) AS policy_count
            FROM pg_catalog.pg_class AS relation
            JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            LEFT JOIN pg_catalog.pg_policy AS policy ON policy.polrelid = relation.oid
            WHERE namespace.nspname = 'public'
              AND relation.relname IN (
                  'foods', 'pulseplate_migration_ownership',
                  'restaurant_chains', 'restaurant_menu_items'
              )
            GROUP BY relation.relname, relation.relrowsecurity, relation.relforcerowsecurity
            ORDER BY relation.relname COLLATE "C"
            """)).mappings().all()
    return tuple(
        RlsDescriptor(
            str(row["table_name"]),
            row["rls_enabled"] is True,
            row["rls_forced"] is True,
            int(row["policy_count"]),
        )
        for row in rows
    )


def _read_owned_sequences(connection: Connection) -> tuple[str, ...]:
    rows = connection.execute(text("""
            SELECT sequence_relation.relname
            FROM pg_catalog.pg_class AS sequence_relation
            JOIN pg_catalog.pg_namespace AS sequence_namespace
              ON sequence_namespace.oid = sequence_relation.relnamespace
            JOIN pg_catalog.pg_depend AS dependency
              ON dependency.classid = 'pg_class'::regclass
             AND dependency.objid = sequence_relation.oid
             AND dependency.refclassid = 'pg_class'::regclass
             AND dependency.deptype IN ('a', 'i')
            JOIN pg_catalog.pg_class AS owner_relation
              ON owner_relation.oid = dependency.refobjid
            JOIN pg_catalog.pg_namespace AS owner_namespace
              ON owner_namespace.oid = owner_relation.relnamespace
            WHERE sequence_relation.relkind = 'S'
              AND sequence_namespace.nspname = 'public'
              AND owner_namespace.nspname = 'public'
              AND owner_relation.relname IN (
                  'foods', 'pulseplate_migration_ownership',
                  'restaurant_chains', 'restaurant_menu_items'
              )
            ORDER BY sequence_relation.relname COLLATE "C"
            LIMIT 17
            """)).all()
    return tuple(str(row[0]) for row in rows)


def _validate_descriptors(connection: Connection) -> tuple[tuple[str, ...], tuple[str, ...]]:
    checks: tuple[tuple[str, str, object, object], ...] = (
        (
            "migration_column_descriptor_mismatch",
            "descriptor:columns",
            _read_columns(connection),
            EXPECTED_COLUMNS,
        ),
        (
            "migration_primary_key_mismatch",
            "descriptor:primary_keys",
            _read_primary_keys(connection),
            EXPECTED_PRIMARY_KEYS,
        ),
        (
            "migration_foreign_key_mismatch",
            "descriptor:foreign_keys",
            _read_foreign_keys(connection),
            EXPECTED_FOREIGN_KEYS,
        ),
        (
            "migration_unique_or_check_constraint_mismatch",
            "descriptor:unique_or_check_constraints",
            _read_named_constraints(connection),
            (),
        ),
        (
            "migration_index_descriptor_mismatch",
            "descriptor:indexes",
            _read_indexes(connection),
            EXPECTED_INDEXES,
        ),
        (
            "migration_ownership_registry_mismatch",
            "descriptor:ownership_rows",
            _read_ownership_rows(connection),
            EXPECTED_OWNERSHIP_ROWS,
        ),
        (
            "migration_rls_or_policy_mismatch",
            "descriptor:rls_policies",
            _read_rls(connection),
            EXPECTED_RLS,
        ),
        (
            "migration_owned_sequence_present",
            "descriptor:owned_sequences",
            _read_owned_sequences(connection),
            (),
        ),
    )
    reasons: list[str] = []
    observed: list[str] = []
    for reason_code, identity, actual, expected in checks:
        if actual != expected:
            reasons.append(reason_code)
            observed.append(identity)
    return tuple(reasons), tuple(observed)


def _produce_upgrade_ops(
    connection: Connection,
    target_metadata: MetaData,
    *,
    admitted: bool,
) -> tuple[ops.UpgradeOps, tuple[str, ...]]:
    options: dict[str, object] = {
        "compare_type": True,
        "compare_server_default": compare_postgresql_server_default,
    }
    if admitted:
        options["include_object"] = include_autogenerate_object
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        context = MigrationContext.configure(connection, opts=options)
        if admitted:
            with proven_autogenerate_default_schema(str(connection.dialect.default_schema_name)):
                root = produce_migrations(context, target_metadata).upgrade_ops
        else:
            root = produce_migrations(context, target_metadata).upgrade_ops
    if not isinstance(root, ops.UpgradeOps):
        raise ValueError("autogenerate_upgrade_root_missing")
    categories = tuple(warning.category.__name__ for warning in caught)
    return root, categories


def _operation_leaf(operation: object, *, default_schema_name: str) -> OperationLeaf | None:
    if isinstance(operation, ops.DropTableOp):
        schema = operation.schema or default_schema_name
        table_name = _bounded_identifier(operation.table_name)
        return OperationLeaf(
            "DropTableOp",
            _bounded_identifier(schema),
            table_name,
            table_name,
        )
    if isinstance(operation, ops.DropIndexOp):
        schema = operation.schema or default_schema_name
        return OperationLeaf(
            "DropIndexOp",
            _bounded_identifier(schema),
            _bounded_identifier(operation.table_name),
            _bounded_identifier(operation.index_name),
        )
    return None


def _semantic_leaves(
    root: ops.UpgradeOps,
    *,
    default_schema_name: str,
) -> tuple[tuple[OperationLeaf, ...], tuple[str, ...], tuple[str, ...]]:
    leaves: list[OperationLeaf] = []
    reasons: list[str] = []
    observed: list[str] = []

    def walk(
        operation: object,
        *,
        depth: int,
        parent_table_root: tuple[str, str] | None = None,
    ) -> None:
        if isinstance(operation, ops.OpContainer):
            child_parent = parent_table_root
            if isinstance(operation, ops.UpgradeOps):
                if depth != 0:
                    reasons.append("autogenerate_container_topology_invalid")
                    observed.append("container:UpgradeOps:nested")
            elif isinstance(operation, ops.ModifyTableOps):
                parent_schema = _bounded_identifier(operation.schema or default_schema_name)
                parent_table = _bounded_identifier(operation.table_name)
                child_parent = (parent_schema, parent_table)
                if depth != 1:
                    reasons.append("autogenerate_container_topology_invalid")
                    observed.append("container:ModifyTableOps:invalid_depth")
                if not operation.ops:
                    reasons.append("autogenerate_modify_table_empty")
                    observed.append(
                        f"container:ModifyTableOps:{parent_schema}.{parent_table}:empty"
                    )
            else:
                reasons.append("autogenerate_container_unclassified")
                observed.append(f"container:{type(operation).__name__}")
            for child in operation.ops:
                walk(child, depth=depth + 1, parent_table_root=child_parent)
            return
        leaf = _operation_leaf(operation, default_schema_name=default_schema_name)
        if leaf is None:
            reasons.append("autogenerate_operation_unclassified")
            observed.append(f"operation:{type(operation).__name__}")
            return
        if isinstance(operation, ops.DropIndexOp):
            leaf_root = (leaf.schema, leaf.table_name)
            if parent_table_root is None:
                reasons.append("autogenerate_drop_index_parent_missing")
                observed.append(
                    f"operation:DropIndexOp:{leaf.schema}.{leaf.table_name}:parent_missing"
                )
            elif leaf_root != parent_table_root:
                reasons.append("autogenerate_drop_index_parent_mismatch")
                observed.append(
                    "operation:DropIndexOp:"
                    f"parent={parent_table_root[0]}.{parent_table_root[1]}:"
                    f"child={leaf.schema}.{leaf.table_name}"
                )
        leaves.append(leaf)

    walk(root, depth=0)
    return tuple(sorted(leaves)), tuple(reasons), tuple(observed)


def _validate_raw_leaves(
    leaves: tuple[OperationLeaf, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    actual = Counter(leaves)
    expected = Counter(EXPECTED_RAW_LEAVES)
    reasons: list[str] = []
    observed: list[str] = []
    missing = expected - actual
    extra = actual - expected
    duplicates = tuple(leaf for leaf, count in actual.items() if count > expected.get(leaf, 0))
    if missing:
        reasons.append("raw_leaf_inventory_missing")
        observed.extend(
            f"raw_missing:{leaf.operation}:{leaf.schema}.{leaf.table_name}:{leaf.object_name}"
            for leaf in missing
        )
    if extra:
        reasons.append("raw_leaf_inventory_extra")
        observed.extend(
            f"raw_extra:{leaf.operation}:{leaf.schema}.{leaf.table_name}:{leaf.object_name}"
            for leaf in extra
        )
    if duplicates:
        reasons.append("raw_leaf_inventory_duplicate")
        observed.extend(
            f"raw_duplicate:{leaf.operation}:{leaf.schema}.{leaf.table_name}:{leaf.object_name}"
            for leaf in duplicates
        )
    return tuple(reasons), tuple(observed)


def evaluate_alembic_autogenerate_admission(
    connection: Connection,
    target_metadata: MetaData,
) -> BoundedAutogenerateAdmissionReport:
    """Evaluate the exact four-root admission on one verified PostgreSQL connection."""

    reasons: list[str] = []
    observed: list[str] = []
    canonical_roots: tuple[str, ...] = ()
    public_roots: tuple[str, ...] = ()
    raw_leaves: tuple[OperationLeaf, ...] = ()
    admitted_leaves: tuple[OperationLeaf, ...] = ()
    warning_categories: list[str] = []
    migration_head: str | None = None
    database_head: str | None = None
    default_schema_name: str | None = None
    descriptor_validation: ValidationState = "not_run"

    def report() -> BoundedAutogenerateAdmissionReport:
        return _make_report(
            reasons=reasons,
            observed=observed,
            migration_head=migration_head,
            database_head=database_head,
            default_schema_name=default_schema_name,
            canonical_roots=canonical_roots,
            public_roots=public_roots,
            raw_leaves=raw_leaves,
            admitted_leaves=admitted_leaves,
            warning_categories=warning_categories,
            descriptor_validation=descriptor_validation,
        )

    try:
        from core.db import Base, load_canonical_orm_metadata

        canonical_metadata = load_canonical_orm_metadata()
    except Exception:
        reasons.append("canonical_metadata_load_failed")
        return report()
    if canonical_metadata is not Base.metadata:
        reasons.append("canonical_metadata_loader_identity_mismatch")
        return report()
    if target_metadata is not canonical_metadata:
        reasons.append("canonical_metadata_identity_mismatch")
        return report()

    canonical_root_pairs = tuple(
        sorted(
            (table.schema or "public", table.name) for table in canonical_metadata.tables.values()
        )
    )
    canonical_roots = tuple(_root_key(schema, name) for schema, name in canonical_root_pairs)
    if any(schema != "public" for schema, _ in canonical_root_pairs):
        reasons.append("canonical_metadata_schema_not_public")
        return report()
    if set(canonical_root_pairs) & AUTOGENERATE_EXEMPT_TABLE_ROOTS:
        reasons.append("autogenerate_exempt_root_became_metadata_owned")
        return report()

    dialect = getattr(connection, "dialect", None)
    if getattr(dialect, "name", None) != "postgresql":
        reasons.append("unsupported_dialect")
        return report()
    default_schema_name = getattr(dialect, "default_schema_name", None)
    if default_schema_name != "public":
        reasons.append("default_schema_not_public")
        return report()

    try:
        migration_head = _migration_head()
    except Exception:
        reasons.append("migration_head_resolution_failed")
        return report()
    if migration_head is None:
        reasons.append("migration_head_not_singleton")
        return report()
    try:
        database_head = _database_head(connection)
    except Exception:
        reasons.append("database_head_read_failed")
        return report()
    if database_head != migration_head:
        reasons.append("database_head_mismatch")
        return report()

    try:
        table_names = tuple(
            str(name) for name in inspect(connection).get_table_names(schema="public")
        )
    except Exception:
        reasons.append("public_table_census_failed")
        return report()
    public_root_pairs = frozenset(("public", name) for name in table_names)
    public_roots = tuple(_root_key(schema, name) for schema, name in public_root_pairs)
    expected_public_roots = (
        frozenset(canonical_root_pairs)
        | AUTOGENERATE_EXEMPT_TABLE_ROOTS
        | ALEMBIC_INTERNAL_TABLE_ROOTS
    )
    if public_root_pairs != expected_public_roots:
        reasons.append("public_table_root_partition_mismatch")
        observed.extend(
            f"public_missing:{_root_key(schema, name)}"
            for schema, name in sorted(expected_public_roots - public_root_pairs)
        )
        observed.extend(
            f"public_extra:{_root_key(schema, name)}"
            for schema, name in sorted(public_root_pairs - expected_public_roots)
        )
        return report()

    try:
        raw_root, raw_warnings = _produce_upgrade_ops(
            connection,
            target_metadata,
            admitted=False,
        )
    except Exception:
        reasons.append("raw_autogenerate_failed")
        return report()
    warning_categories.extend(f"raw:{category}" for category in raw_warnings)
    if raw_warnings:
        reasons.append("raw_autogenerate_warning")
        return report()
    raw_leaves, raw_tree_reasons, raw_tree_observed = _semantic_leaves(
        raw_root,
        default_schema_name=default_schema_name,
    )
    reasons.extend(raw_tree_reasons)
    observed.extend(raw_tree_observed)
    leaf_reasons, leaf_observed = _validate_raw_leaves(raw_leaves)
    reasons.extend(leaf_reasons)
    observed.extend(leaf_observed)
    if reasons:
        return report()

    try:
        descriptor_reasons, descriptor_observed = _validate_descriptors(connection)
    except Exception:
        reasons.append("migration_descriptor_read_failed")
        descriptor_validation = "failed"
        return report()
    reasons.extend(descriptor_reasons)
    observed.extend(descriptor_observed)
    descriptor_validation = "passed" if not descriptor_reasons else "failed"
    if reasons:
        return report()

    try:
        admitted_root, admitted_warnings = _produce_upgrade_ops(
            connection,
            target_metadata,
            admitted=True,
        )
    except Exception:
        reasons.append("admitted_autogenerate_failed")
        return report()
    warning_categories.extend(f"admitted:{category}" for category in admitted_warnings)
    if admitted_warnings:
        reasons.append("admitted_autogenerate_warning")
        return report()
    admitted_leaves, admitted_tree_reasons, admitted_tree_observed = _semantic_leaves(
        admitted_root,
        default_schema_name=default_schema_name,
    )
    reasons.extend(admitted_tree_reasons)
    observed.extend(admitted_tree_observed)
    if not admitted_root.is_empty() or admitted_root.ops:
        reasons.append("admitted_operation_tree_not_empty")
        observed.extend(
            f"admitted:{leaf.operation}:{leaf.schema}.{leaf.table_name}:{leaf.object_name}"
            for leaf in admitted_leaves
        )
    return report()


__all__ = [
    "ALEMBIC_INTERNAL_TABLE_ROOTS",
    "AUTOGENERATE_EXEMPT_TABLE_ROOTS",
    "BoundedAutogenerateAdmissionReport",
    "ColumnDescriptor",
    "EXPECTED_COLUMNS",
    "EXPECTED_FOREIGN_KEYS",
    "EXPECTED_INDEXES",
    "EXPECTED_OWNERSHIP_ROWS",
    "EXPECTED_PRIMARY_KEYS",
    "EXPECTED_RAW_LEAVES",
    "EXPECTED_RLS",
    "ForeignKeyDescriptor",
    "IndexDescriptor",
    "NamedConstraintDescriptor",
    "OperationLeaf",
    "ADMISSION_RESULT_CLAIM",
    "PrimaryKeyDescriptor",
    "RlsDescriptor",
    "evaluate_alembic_autogenerate_admission",
]

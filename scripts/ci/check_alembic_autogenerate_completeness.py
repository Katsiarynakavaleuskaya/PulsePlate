"""Bounded Alembic autogenerate recognizer for the current PostgreSQL epoch.

This module deliberately owns no database lifecycle.  A caller supplies an
already-upgraded disposable PostgreSQL connection and the canonical metadata.
Phase A proves the finite table census and classifies the structural Alembic
operation tree.  Descriptor, extension, RLS, policy, CHECK, and sequence proof
is reserved for the existing PostgreSQL contour in Phase B; until then the
report fails closed instead of claiming complete schema ownership.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from collections.abc import Mapping
from typing import Literal

from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from alembic.operations import ops
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.schema import MetaData
from sqlalchemy.sql import sqltypes

from core.db_alembic_ownership import (
    DEFAULT_SCHEMA_NAMES,
    MIGRATION_OWNED_TABLE_KEYS,
    include_autogenerate_object,
)

EXPECTED_ALEMBIC_HEAD = "202608270001"
REPORT_SCHEMA_VERSION = "pulseplate.alembic_autogenerate_completeness.phase_b.v1"
CLAIM_BOUNDARY = (
    "base=74b3ef863d3f663400c11a11e0f9aa37012b2fdf;"
    "alembic=1.19.1;sqlalchemy=2.0.52;schema=public;fresh_upgraded_postgresql"
)
VALIDATION_PENDING = "not_evaluated_phase_b"
VALIDATION_PASSED = "validated"

CANONICAL_MAPPED_TABLE_KEYS = frozenset(
    {
        "analyzer_state",
        "context",
        "day_plans",
        "fitchef_support_outcome_events",
        "food_items",
        "meals",
        "nutrition_events",
        "paywall_exposure_ledger",
        "rag_feedback",
        "recipes",
        "subscription_activation_audit",
        "subscriptions",
        "user_knowledge",
        "users",
        "vip_llm_monthly_usage",
        "weekly_plans",
    }
)

ALEMBIC_INTERNAL_TABLE_KEYS = frozenset({"alembic_version"})

MIGRATION_OWNED_INDEX_KEYS = frozenset(
    {
        "ix_foods_canonical_name",
        "ix_foods_group_name",
        "ix_foods_source",
        "ix_foods_gtin",
        "ix_foods_canonical_name_gin_trgm",
        "ix_foods_group_name_gin_trgm",
        "ix_foods_brand_gin_trgm",
        "ix_restaurant_chains_name",
        "ix_restaurant_menu_items_chain_id",
        "ix_restaurant_menu_items_item_name",
        "ix_restaurant_menu_items_food_id",
    }
)

EXPECTED_PHYSICAL_TABLE_KEYS = (
    CANONICAL_MAPPED_TABLE_KEYS | MIGRATION_OWNED_TABLE_KEYS | ALEMBIC_INTERNAL_TABLE_KEYS
)

Result = Literal["pass", "fail"]


@dataclass(frozen=True, slots=True)
class OperationDisposition:
    """Stable, secret-free disposition for one Alembic operation node."""

    path: str
    operation: str
    schema: str | None
    table_name: str | None
    object_name: str | None
    disposition: str
    reason_code: str


@dataclass(frozen=True, slots=True, order=True)
class ColumnSignature:
    name: str
    type_key: str
    nullable: bool
    default: str | None


@dataclass(frozen=True, slots=True, order=True)
class ForeignKeySignature:
    columns: tuple[str, ...]
    referred_schema: str
    referred_table: str
    referred_columns: tuple[str, ...]
    ondelete: str | None


@dataclass(frozen=True, slots=True, order=True)
class IndexSignature:
    name: str
    columns: tuple[str, ...]
    unique: bool
    method: str


@dataclass(frozen=True, slots=True, order=True)
class TableSignature:
    name: str
    columns: tuple[ColumnSignature, ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[ForeignKeySignature, ...] = ()
    unique_constraints: tuple[str, ...] = ()
    check_constraints: tuple[str, ...] = ()
    indexes: tuple[IndexSignature, ...] = ()


@dataclass(frozen=True, slots=True, order=True)
class ExtensionSignature:
    name: str
    installed_version: str
    default_version: str
    schema: str
    relocatable: bool


@dataclass(frozen=True, slots=True, order=True)
class PolicySignature:
    name: str
    permissive: bool
    command: str
    roles: str
    using_expression: str
    check_expression: str


@dataclass(frozen=True, slots=True, order=True)
class RlsTableSignature:
    table: str
    enabled: bool
    forced: bool
    policies: tuple[PolicySignature, ...]


@dataclass(frozen=True, slots=True, order=True)
class CheckSignature:
    table: str
    name: str
    definition: str


@dataclass(frozen=True, slots=True, order=True)
class SequenceSignature:
    schema: str
    name: str
    owner_schema: str | None
    owner_table: str | None
    owner_column: str | None
    dependency_type: str | None


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    status: str
    reason_codes: tuple[str, ...]
    unknown_objects: tuple[str, ...]


def _column(
    name: str,
    type_key: str,
    nullable: bool,
    default: str | None = None,
) -> ColumnSignature:
    return ColumnSignature(name, type_key, nullable, default)


def _index(
    name: str,
    column_name: str,
    method: str = "btree",
) -> IndexSignature:
    return IndexSignature(name, (column_name,), False, method)


EXPECTED_MIGRATION_TABLE_SIGNATURES = (
    TableSignature(
        name="pulseplate_migration_ownership",
        columns=tuple(
            sorted(
                (
                    _column("revision_id", "varchar:32", False),
                    _column("object_type", "varchar:16", False),
                    _column("table_name", "varchar:128", False),
                    _column("object_name", "varchar:128", False),
                )
            )
        ),
        primary_key=("revision_id", "object_type", "table_name", "object_name"),
    ),
    TableSignature(
        name="foods",
        columns=tuple(
            sorted(
                (
                    _column("id", "text", False),
                    _column("canonical_name", "text", False),
                    _column("group_name", "text", False),
                    _column("per_g", "numeric:8:2", False, "100.00"),
                    _column("kcal", "numeric:8:2", False),
                    _column("protein_g", "numeric:8:2", False, "0.00"),
                    _column("fat_g", "numeric:8:2", False, "0.00"),
                    _column("carbs_g", "numeric:8:2", False, "0.00"),
                    _column("fiber_g", "numeric:8:2", False, "0.00"),
                    _column("Fe_mg", "numeric:10:3", False, "0.000"),
                    _column("Ca_mg", "numeric:10:3", False, "0.000"),
                    _column("K_mg", "numeric:10:3", False, "0.000"),
                    _column("Mg_mg", "numeric:10:3", False, "0.000"),
                    _column("VitD_IU", "numeric:10:3", False, "0.000"),
                    _column("B12_ug", "numeric:10:3", False, "0.000"),
                    _column("Folate_ug", "numeric:10:3", False, "0.000"),
                    _column("Iodine_ug", "numeric:10:3", False, "0.000"),
                    _column("flags", "json", False, "[]"),
                    _column("brand", "text", True),
                    _column("gtin", "text", True),
                    _column("fdc_id", "text", True),
                    _column("source", "text", False),
                    _column("source_priority", "integer", False, "0"),
                    _column("version_date", "varchar:64", False),
                    _column("price_per_100g", "numeric:10:2", True),
                    _column("nutrition_inputs_json", "json", True),
                    _column("nutrition_provenance_json", "json", True),
                    _column("nutrition_confidence", "numeric:4:3", True),
                    _column("nutrition_nutrient_confidence_json", "json", True),
                )
            )
        ),
        primary_key=("id",),
        indexes=tuple(
            sorted(
                (
                    _index("ix_foods_brand_gin_trgm", "brand", "gin"),
                    _index("ix_foods_canonical_name", "canonical_name"),
                    _index("ix_foods_canonical_name_gin_trgm", "canonical_name", "gin"),
                    _index("ix_foods_group_name", "group_name"),
                    _index("ix_foods_group_name_gin_trgm", "group_name", "gin"),
                    _index("ix_foods_gtin", "gtin"),
                    _index("ix_foods_source", "source"),
                )
            )
        ),
    ),
    TableSignature(
        name="restaurant_chains",
        columns=tuple(
            sorted(
                (
                    _column("id", "text", False),
                    _column("name", "text", False),
                    _column("country", "varchar:16", True),
                    _column("source", "text", False),
                    _column("source_id", "text", True),
                    _column("updated_at", "timestamptz", False, "current_timestamp"),
                )
            )
        ),
        primary_key=("id",),
        indexes=(_index("ix_restaurant_chains_name", "name"),),
    ),
    TableSignature(
        name="restaurant_menu_items",
        columns=tuple(
            sorted(
                (
                    _column("id", "text", False),
                    _column("chain_id", "text", False),
                    _column("food_id", "text", True),
                    _column("item_name", "text", False),
                    _column("category", "text", True),
                    _column("serving_size_g", "numeric:10:2", True),
                    _column("kcal", "numeric:8:2", True),
                    _column("protein_g", "numeric:8:2", True),
                    _column("fat_g", "numeric:8:2", True),
                    _column("carbs_g", "numeric:8:2", True),
                    _column("sodium_mg", "numeric:10:2", True),
                    _column("source", "text", False),
                    _column("source_id", "text", True),
                    _column("is_active", "boolean", False, "true"),
                    _column("updated_at", "timestamptz", False, "current_timestamp"),
                )
            )
        ),
        primary_key=("id",),
        foreign_keys=tuple(
            sorted(
                (
                    ForeignKeySignature(
                        ("chain_id",),
                        "public",
                        "restaurant_chains",
                        ("id",),
                        "CASCADE",
                    ),
                    ForeignKeySignature(
                        ("food_id",),
                        "public",
                        "foods",
                        ("id",),
                        "SET NULL",
                    ),
                )
            )
        ),
        indexes=tuple(
            sorted(
                (
                    _index("ix_restaurant_menu_items_chain_id", "chain_id"),
                    _index("ix_restaurant_menu_items_food_id", "food_id"),
                    _index("ix_restaurant_menu_items_item_name", "item_name"),
                )
            )
        ),
    ),
)

EXPECTED_OWNERSHIP_ROWS = frozenset(
    {
        ("202604120001", "table", "foods", "foods"),
        ("202604120001", "table", "restaurant_chains", "restaurant_chains"),
        ("202604120001", "table", "restaurant_menu_items", "restaurant_menu_items"),
        *(
            ("202604120001", "index", table.name, index.name)
            for table in EXPECTED_MIGRATION_TABLE_SIGNATURES
            for index in table.indexes
        ),
    }
)

EXPECTED_EXTENSIONS = (
    ExtensionSignature("pg_trgm", "1.6", "1.6", "public", True),
    ExtensionSignature("vector", "0.8.2", "0.8.2", "public", True),
)

_USER_POLICY_EXPRESSION = (
    "(user_id = (NULLIF(current_setting('app.current_user_id'::text, true), " "''::text))::bigint)"
)
_SUBJECT_POLICY_EXPRESSION = (
    "(subject_id = (NULLIF(current_setting('app.current_user_id'::text, true), "
    "''::text))::bigint)"
)
EXPECTED_RLS_TABLES = (
    RlsTableSignature(
        "fitchef_support_outcome_events",
        True,
        True,
        (
            PolicySignature(
                "fitchef_support_outcome_subject_isolation",
                True,
                "*",
                "{0}",
                _SUBJECT_POLICY_EXPRESSION,
                _SUBJECT_POLICY_EXPRESSION,
            ),
        ),
    ),
    RlsTableSignature(
        "rag_feedback",
        True,
        True,
        (
            PolicySignature(
                "rag_feedback_user_isolation",
                True,
                "*",
                "{0}",
                _USER_POLICY_EXPRESSION,
                _USER_POLICY_EXPRESSION,
            ),
        ),
    ),
    RlsTableSignature(
        "user_knowledge",
        True,
        True,
        (
            PolicySignature(
                "user_knowledge_user_isolation",
                True,
                "*",
                "{0}",
                _USER_POLICY_EXPRESSION,
                _USER_POLICY_EXPRESSION,
            ),
        ),
    ),
)

EXPECTED_CRITICAL_CHECKS = tuple(
    sorted(
        (
            CheckSignature(
                "fitchef_support_outcome_events",
                "ck_fitchef_support_outcome_compatible_pair",
                "CHECK (support_need::text = 'daily_structure'::text AND "
                "target_surface::text = 'pro_daily_plate'::text OR "
                "support_need::text = 'weekly_structure'::text AND "
                "target_surface::text = 'pro_weekly_plan'::text)",
            ),
            CheckSignature(
                "fitchef_support_outcome_events",
                "ck_fitchef_support_outcome_outcome",
                "CHECK (outcome::text = ANY (ARRAY['acknowledged'::character varying, "
                "'dismissed'::character varying]::text[]))",
            ),
            CheckSignature(
                "fitchef_support_outcome_events",
                "ck_fitchef_support_outcome_schema_version",
                "CHECK (schema_version::text = 'fitchef_support_outcome_v1'::text)",
            ),
            CheckSignature(
                "fitchef_support_outcome_events",
                "ck_fitchef_support_outcome_support_need",
                "CHECK (support_need::text = ANY (ARRAY['daily_structure'::character varying, "
                "'weekly_structure'::character varying]::text[]))",
            ),
            CheckSignature(
                "fitchef_support_outcome_events",
                "ck_fitchef_support_outcome_target_surface",
                "CHECK (target_surface::text = ANY (ARRAY['pro_daily_plate'::character varying, "
                "'pro_weekly_plan'::character varying]::text[]))",
            ),
        )
    )
)


@dataclass(frozen=True, slots=True)
class CompletenessReport:
    """Immutable JSON-serializable Phase A completeness report."""

    schema_version: str
    boundary: str
    alembic_head: str | None
    canonical_mapped_table_count: int
    canonical_mapped_table_keys: tuple[str, ...]
    migration_owned_table_count: int
    migration_owned_table_keys: tuple[str, ...]
    migration_owned_object_count: int
    migration_owned_object_keys: tuple[str, ...]
    alembic_internal_object_count: int
    alembic_internal_object_keys: tuple[str, ...]
    raw_operations: tuple[OperationDisposition, ...]
    admitted_operations: tuple[OperationDisposition, ...]
    unknown_objects: tuple[str, ...]
    unknown_operations: tuple[str, ...]
    extension_validation: str
    rls_policy_validation: str
    check_validation: str
    sequence_validation: str
    reason_codes: tuple[str, ...]
    material_digest: str
    result: Result

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""

        return asdict(self)

    def to_json(self) -> str:
        """Serialize without local paths, connection data, or exception text."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def _operation_identity(operation: object) -> tuple[str | None, str | None, str | None]:
    schema = getattr(operation, "schema", None)
    table_name = getattr(operation, "table_name", None)
    object_name = getattr(operation, "index_name", None)
    if object_name is None:
        object_name = getattr(operation, "constraint_name", None)
    return schema, table_name, object_name


def _operation_key(record: OperationDisposition) -> str:
    schema = record.schema or "public"
    table = record.table_name or "-"
    name = record.object_name or "-"
    return f"{record.path}:{record.operation}:{schema}.{table}:{name}"


def _raw_drift_reason(operation: object) -> str:
    if isinstance(operation, (ops.CreateIndexOp, ops.DropIndexOp)):
        return "canonical_index_drift"
    if isinstance(operation, (ops.CreateUniqueConstraintOp, ops.DropConstraintOp)):
        return "canonical_unique_constraint_drift"
    if isinstance(operation, ops.AlterColumnOp):
        if operation.modify_type is not None:
            return "canonical_column_type_drift"
        if operation.modify_server_default is not False:
            return "canonical_column_default_drift"
        if operation.modify_nullable is not None:
            return "canonical_column_nullability_drift"
        return "canonical_column_drift"
    return "raw_operation_not_admitted"


def _classify_autogenerate_failure(error: object) -> str:
    original = getattr(error, "orig", None)
    sqlstate = getattr(original, "sqlstate", None)
    statement = getattr(error, "statement", None)
    if sqlstate == "42883" and statement == "SELECT '{}'::json = '{}' AS anon_1":
        return "json_default_comparison_operator_unsupported"
    return "autogenerate_production_failed"


def _classify_autogenerate_warning(message: str) -> str:
    if message == "Did not recognize type 'vector' of column 'embedding'":
        return "vector_reflection_type_unrecognized"
    return "autogenerate_warning_unclassified"


def _classify_operation_tree(
    root: object,
    *,
    rail: Literal["raw", "admitted"],
) -> tuple[tuple[OperationDisposition, ...], tuple[str, ...], tuple[str, ...]]:
    records: list[OperationDisposition] = []
    unknown: list[str] = []
    seen_drop_tables: list[str] = []

    def add_record(
        operation: object,
        path: str,
        disposition: str,
        reason_code: str,
    ) -> None:
        schema, table_name, object_name = _operation_identity(operation)
        record = OperationDisposition(
            path=path,
            operation=type(operation).__name__,
            schema=schema,
            table_name=table_name,
            object_name=object_name,
            disposition=disposition,
            reason_code=reason_code,
        )
        records.append(record)
        if disposition == "unknown":
            unknown.append(_operation_key(record))

    def walk(operation: object, path: str) -> None:
        if isinstance(operation, ops.OpContainer):
            if isinstance(operation, ops.UpgradeOps) and path == "upgrade":
                add_record(operation, path, "structural", f"{rail}_root_container")
            elif (
                isinstance(operation, ops.ModifyTableOps)
                and rail == "raw"
                and operation.schema in DEFAULT_SCHEMA_NAMES
                and operation.table_name in MIGRATION_OWNED_TABLE_KEYS
            ):
                add_record(
                    operation,
                    path,
                    "structural",
                    "expected_migration_table_container",
                )
            elif isinstance(operation, ops.UpgradeOps):
                add_record(operation, path, "unknown", "nested_upgrade_container")
            else:
                add_record(operation, path, "unknown", f"{rail}_unexpected_container")
            for index, child in enumerate(operation.ops):
                walk(child, f"{path}/{index}")
            return

        if rail == "admitted":
            add_record(operation, path, "unknown", "admitted_operation_present")
            return

        schema, table_name, object_name = _operation_identity(operation)
        if (
            isinstance(operation, ops.DropTableOp)
            and schema in DEFAULT_SCHEMA_NAMES
            and table_name in MIGRATION_OWNED_TABLE_KEYS
        ):
            seen_drop_tables.append(str(table_name))
            add_record(operation, path, "migration_owned", "expected_migration_table_drop")
            return

        if (
            isinstance(operation, ops.DropIndexOp)
            and schema in DEFAULT_SCHEMA_NAMES
            and table_name in MIGRATION_OWNED_TABLE_KEYS
            and object_name in MIGRATION_OWNED_INDEX_KEYS
        ):
            add_record(operation, path, "migration_owned", "expected_migration_index_drop")
            return

        add_record(operation, path, "unknown", _raw_drift_reason(operation))

    walk(root, "upgrade")
    reasons: list[str] = []
    observed = set(seen_drop_tables)
    missing = sorted(MIGRATION_OWNED_TABLE_KEYS - observed)
    duplicates = sorted(name for name in observed if seen_drop_tables.count(name) != 1)
    if rail == "raw" and missing:
        reasons.append("raw_migration_table_drop_missing")
        unknown.extend(f"missing_drop_table:public.{name}" for name in missing)
    if rail == "raw" and duplicates:
        reasons.append("raw_migration_table_drop_duplicate")
        unknown.extend(f"duplicate_drop_table:public.{name}" for name in duplicates)
    return tuple(records), tuple(sorted(set(unknown))), tuple(reasons)


def _produce_upgrade_ops(
    connection: Connection,
    target_metadata: MetaData,
    *,
    admitted: bool,
) -> ops.UpgradeOps:
    options: dict[str, object] = {
        "compare_type": True,
        "compare_server_default": True,
    }
    if admitted:
        options["include_object"] = include_autogenerate_object
    migration_context = MigrationContext.configure(connection, opts=options)
    return produce_migrations(migration_context, target_metadata).upgrade_ops


def _read_alembic_head(connection: Connection) -> str | None:
    rows = connection.exec_driver_sql(
        "SELECT version_num FROM alembic_version ORDER BY version_num"
    ).fetchall()
    if len(rows) != 1 or len(rows[0]) != 1:
        return None
    value = rows[0][0]
    return value if isinstance(value, str) and value else None


def _reflect_physical_table_keys(connection: Connection) -> frozenset[str]:
    return frozenset(str(name) for name in inspect(connection).get_table_names(schema="public"))


def _type_key(value: object) -> str:
    if isinstance(value, sqltypes.JSON):
        return "json"
    if isinstance(value, sqltypes.Text):
        return "text"
    if isinstance(value, sqltypes.String):
        return f"varchar:{value.length}"
    if isinstance(value, sqltypes.Numeric):
        return f"numeric:{value.precision}:{value.scale}"
    if isinstance(value, sqltypes.Integer):
        return "integer"
    if isinstance(value, sqltypes.Boolean):
        return "boolean"
    if isinstance(value, sqltypes.DateTime):
        return "timestamptz" if value.timezone else "timestamp"
    return f"unsupported:{type(value).__name__}"


def _normalize_default(value: object) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().split()).lower()
    if normalized in {"current_timestamp", "now()"}:
        return "current_timestamp"
    if normalized.startswith("'") and "'::" in normalized:
        return normalized[1 : normalized.rfind("'::")]
    return normalized


def _reflect_migration_table_signatures(connection: Connection) -> tuple[TableSignature, ...]:
    inspector = inspect(connection)
    signatures: list[TableSignature] = []
    for table_name in sorted(MIGRATION_OWNED_TABLE_KEYS):
        columns = tuple(
            sorted(
                ColumnSignature(
                    name=str(column["name"]),
                    type_key=_type_key(column["type"]),
                    nullable=column.get("nullable") is True,
                    default=_normalize_default(column.get("default")),
                )
                for column in inspector.get_columns(table_name, schema="public")
            )
        )
        primary_key = tuple(
            str(value)
            for value in (
                inspector.get_pk_constraint(table_name, schema="public").get("constrained_columns")
                or ()
            )
        )
        foreign_keys: list[ForeignKeySignature] = []
        for foreign_key in inspector.get_foreign_keys(table_name, schema="public"):
            options = foreign_key.get("options")
            option_mapping = options if isinstance(options, Mapping) else {}
            raw_ondelete = option_mapping.get("ondelete")
            foreign_keys.append(
                ForeignKeySignature(
                    columns=tuple(
                        str(value) for value in (foreign_key.get("constrained_columns") or ())
                    ),
                    referred_schema=str(foreign_key.get("referred_schema") or "public"),
                    referred_table=str(foreign_key.get("referred_table")),
                    referred_columns=tuple(
                        str(value) for value in (foreign_key.get("referred_columns") or ())
                    ),
                    ondelete=str(raw_ondelete).upper() if raw_ondelete is not None else None,
                )
            )
        unique_constraints = tuple(
            sorted(
                f"{constraint.get('name')}:{','.join(str(value) for value in (constraint.get('column_names') or ())) }"
                for constraint in inspector.get_unique_constraints(table_name, schema="public")
            )
        )
        check_constraints = tuple(
            sorted(
                f"{constraint.get('name')}:{' '.join(str(constraint.get('sqltext')).split())}"
                for constraint in inspector.get_check_constraints(table_name, schema="public")
            )
        )
        indexes: list[IndexSignature] = []
        for index in inspector.get_indexes(table_name, schema="public"):
            dialect_options = index.get("dialect_options")
            option_mapping = dialect_options if isinstance(dialect_options, Mapping) else {}
            indexes.append(
                IndexSignature(
                    name=str(index.get("name")),
                    columns=tuple(str(value) for value in (index.get("column_names") or ())),
                    unique=index.get("unique") is True,
                    method=str(option_mapping.get("postgresql_using") or "btree"),
                )
            )
        signatures.append(
            TableSignature(
                name=table_name,
                columns=columns,
                primary_key=primary_key,
                foreign_keys=tuple(sorted(foreign_keys)),
                unique_constraints=unique_constraints,
                check_constraints=check_constraints,
                indexes=tuple(sorted(indexes)),
            )
        )
    return tuple(sorted(signatures))


def _validation_outcome(
    reason_codes: list[str],
    unknown_objects: list[str],
) -> ValidationOutcome:
    return ValidationOutcome(
        status=VALIDATION_PASSED if not reason_codes else "failed",
        reason_codes=tuple(sorted(set(reason_codes))),
        unknown_objects=tuple(sorted(set(unknown_objects))),
    )


def _validate_migration_table_signatures(
    observed: tuple[TableSignature, ...],
) -> ValidationOutcome:
    expected_by_name = {table.name: table for table in EXPECTED_MIGRATION_TABLE_SIGNATURES}
    observed_by_name = {table.name: table for table in observed}
    reasons: list[str] = []
    unknown: list[str] = []
    if set(observed_by_name) != set(expected_by_name):
        reasons.append("migration_table_descriptor_inventory_mismatch")
        unknown.append("migration_table_descriptor_inventory")
    for table_name in sorted(set(expected_by_name) & set(observed_by_name)):
        expected = expected_by_name[table_name]
        actual = observed_by_name[table_name]
        expected_columns = {column.name: column for column in expected.columns}
        actual_columns = {column.name: column for column in actual.columns}
        if set(actual_columns) != set(expected_columns):
            reasons.append("migration_column_inventory_mismatch")
            unknown.append(f"migration_columns:public.{table_name}")
        for column_name in sorted(set(expected_columns) & set(actual_columns)):
            expected_column = expected_columns[column_name]
            actual_column = actual_columns[column_name]
            if actual_column.type_key != expected_column.type_key:
                reasons.append("migration_column_type_mismatch")
                unknown.append(f"migration_column_type:public.{table_name}.{column_name}")
            if actual_column.nullable != expected_column.nullable:
                reasons.append("migration_column_nullability_mismatch")
                unknown.append(f"migration_column_nullability:public.{table_name}.{column_name}")
            if actual_column.default != expected_column.default:
                reasons.append("migration_column_default_mismatch")
                unknown.append(f"migration_column_default:public.{table_name}.{column_name}")
        for attribute, reason_code in (
            ("primary_key", "migration_primary_key_mismatch"),
            ("foreign_keys", "migration_foreign_key_mismatch"),
            ("unique_constraints", "migration_unique_constraint_mismatch"),
            ("check_constraints", "migration_check_constraint_mismatch"),
            ("indexes", "migration_index_mismatch"),
        ):
            if getattr(actual, attribute) != getattr(expected, attribute):
                reasons.append(reason_code)
                unknown.append(f"{attribute}:public.{table_name}")
    return _validation_outcome(reasons, unknown)


def _read_ownership_rows(connection: Connection) -> frozenset[tuple[str, str, str, str]]:
    rows = connection.execute(text("""
            SELECT revision_id, object_type, table_name, object_name
            FROM pulseplate_migration_ownership
            ORDER BY revision_id, object_type, table_name, object_name
            LIMIT 16
            """)).fetchall()
    return frozenset((str(row[0]), str(row[1]), str(row[2]), str(row[3])) for row in rows)


def _validate_ownership_rows(
    observed: frozenset[tuple[str, str, str, str]],
) -> ValidationOutcome:
    if observed == EXPECTED_OWNERSHIP_ROWS:
        return _validation_outcome([], [])
    return _validation_outcome(
        ["migration_ownership_registry_mismatch"],
        ["migration_ownership_registry"],
    )


def _read_extension_signatures(connection: Connection) -> tuple[ExtensionSignature, ...]:
    rows = connection.execute(text("""
            SELECT extension.extname, extension.extversion,
                   available.default_version, namespace.nspname,
                   extension.extrelocatable
            FROM pg_extension AS extension
            JOIN pg_namespace AS namespace ON namespace.oid = extension.extnamespace
            LEFT JOIN pg_available_extensions AS available
              ON available.name = extension.extname
            WHERE extension.extname IN ('vector', 'pg_trgm')
            ORDER BY extension.extname
            LIMIT 3
            """)).fetchall()
    return tuple(
        ExtensionSignature(
            name=str(row[0]),
            installed_version=str(row[1]),
            default_version=str(row[2]),
            schema=str(row[3]),
            relocatable=row[4] is True,
        )
        for row in rows
    )


def _validate_extensions(observed: tuple[ExtensionSignature, ...]) -> ValidationOutcome:
    if observed == EXPECTED_EXTENSIONS:
        return _validation_outcome([], [])
    return _validation_outcome(["extension_epoch_mismatch"], ["required_extensions"])


def _read_rls_signatures(connection: Connection) -> tuple[RlsTableSignature, ...]:
    rows = connection.execute(text("""
            SELECT relation.relname, relation.relrowsecurity,
                   relation.relforcerowsecurity, policy.polname,
                   policy.polpermissive, policy.polcmd::text,
                   policy.polroles::text,
                   pg_get_expr(policy.polqual, policy.polrelid),
                   pg_get_expr(policy.polwithcheck, policy.polrelid)
            FROM pg_class AS relation
            JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            LEFT JOIN pg_policy AS policy ON policy.polrelid = relation.oid
            WHERE namespace.nspname = 'public'
              AND relation.relname IN (
                  'rag_feedback', 'user_knowledge',
                  'fitchef_support_outcome_events'
              )
            ORDER BY relation.relname, policy.polname
            LIMIT 7
            """)).fetchall()
    grouped: dict[str, tuple[bool, bool, list[PolicySignature]]] = {}
    for row in rows:
        table_name = str(row[0])
        enabled = row[1] is True
        forced = row[2] is True
        policies = grouped.setdefault(table_name, (enabled, forced, []))[2]
        if row[3] is not None:
            policies.append(
                PolicySignature(
                    name=str(row[3]),
                    permissive=row[4] is True,
                    command=str(row[5]),
                    roles=str(row[6]),
                    using_expression=str(row[7]),
                    check_expression=str(row[8]),
                )
            )
    return tuple(
        sorted(
            RlsTableSignature(name, enabled, forced, tuple(sorted(policies)))
            for name, (enabled, forced, policies) in grouped.items()
        )
    )


def _validate_rls(observed: tuple[RlsTableSignature, ...]) -> ValidationOutcome:
    if observed == EXPECTED_RLS_TABLES:
        return _validation_outcome([], [])
    return _validation_outcome(["rls_policy_epoch_mismatch"], ["required_rls_policies"])


def _read_critical_checks(connection: Connection) -> tuple[CheckSignature, ...]:
    rows = connection.execute(text("""
            SELECT relation.relname, constraint_record.conname,
                   pg_get_constraintdef(constraint_record.oid, true)
            FROM pg_constraint AS constraint_record
            JOIN pg_class AS relation ON relation.oid = constraint_record.conrelid
            JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            WHERE namespace.nspname = 'public'
              AND relation.relname = 'fitchef_support_outcome_events'
              AND constraint_record.contype = 'c'
            ORDER BY relation.relname, constraint_record.conname
            LIMIT 6
            """)).fetchall()
    return tuple(sorted(CheckSignature(str(row[0]), str(row[1]), str(row[2])) for row in rows))


def _validate_critical_checks(observed: tuple[CheckSignature, ...]) -> ValidationOutcome:
    if observed == EXPECTED_CRITICAL_CHECKS:
        return _validation_outcome([], [])
    return _validation_outcome(
        ["critical_check_definition_mismatch"],
        ["fitchef_support_outcome_events:critical_checks"],
    )


def _read_sequences(connection: Connection) -> tuple[SequenceSignature, ...]:
    rows = connection.execute(text("""
            SELECT sequence_namespace.nspname, sequence_relation.relname,
                   owner_namespace.nspname, owner_relation.relname,
                   owner_attribute.attname, dependency.deptype
            FROM pg_class AS sequence_relation
            JOIN pg_namespace AS sequence_namespace
              ON sequence_namespace.oid = sequence_relation.relnamespace
            LEFT JOIN pg_depend AS dependency
              ON dependency.classid = 'pg_class'::regclass
             AND dependency.objid = sequence_relation.oid
             AND dependency.refclassid = 'pg_class'::regclass
             AND dependency.deptype IN ('a', 'i')
            LEFT JOIN pg_class AS owner_relation
              ON owner_relation.oid = dependency.refobjid
            LEFT JOIN pg_namespace AS owner_namespace
              ON owner_namespace.oid = owner_relation.relnamespace
            LEFT JOIN pg_attribute AS owner_attribute
              ON owner_attribute.attrelid = owner_relation.oid
             AND owner_attribute.attnum = dependency.refobjsubid
            WHERE sequence_relation.relkind = 'S'
              AND sequence_namespace.nspname = 'public'
            ORDER BY sequence_namespace.nspname, sequence_relation.relname
            LIMIT 257
            """)).fetchall()
    return tuple(
        SequenceSignature(
            schema=str(row[0]),
            name=str(row[1]),
            owner_schema=str(row[2]) if row[2] is not None else None,
            owner_table=str(row[3]) if row[3] is not None else None,
            owner_column=str(row[4]) if row[4] is not None else None,
            dependency_type=str(row[5]) if row[5] is not None else None,
        )
        for row in rows
    )


def _validate_sequences(observed: tuple[SequenceSignature, ...]) -> ValidationOutcome:
    reasons: list[str] = []
    unknown: list[str] = []
    if len(observed) >= 257:
        reasons.append("public_sequence_inventory_over_bound")
        unknown.append("public_sequences:over_bound")
    for sequence in observed:
        if (
            sequence.schema != "public"
            or sequence.owner_schema != "public"
            or sequence.owner_table not in CANONICAL_MAPPED_TABLE_KEYS
            or not sequence.owner_column
            or sequence.dependency_type not in {"a", "i"}
        ):
            reasons.append("public_sequence_not_dependency_owned")
            unknown.append("public_sequence:unowned_or_unknown")
    return _validation_outcome(reasons, unknown)


def _make_report(
    *,
    alembic_head: str | None,
    metadata_keys: frozenset[str],
    raw_operations: tuple[OperationDisposition, ...] = (),
    admitted_operations: tuple[OperationDisposition, ...] = (),
    unknown_objects: tuple[str, ...] = (),
    unknown_operations: tuple[str, ...] = (),
    reason_codes: tuple[str, ...] = (),
    extension_validation: str = VALIDATION_PENDING,
    rls_policy_validation: str = VALIDATION_PENDING,
    check_validation: str = VALIDATION_PENDING,
    sequence_validation: str = VALIDATION_PENDING,
) -> CompletenessReport:
    normalized_reasons = tuple(sorted(set(reason_codes)))
    normalized_unknown_objects = tuple(sorted(set(unknown_objects)))
    normalized_unknown_operations = tuple(sorted(set(unknown_operations)))
    report_payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "boundary": CLAIM_BOUNDARY,
        "claim_contract": {
            "expected_alembic_head": EXPECTED_ALEMBIC_HEAD,
            "default_schema_projection": sorted(
                "<default>" if schema is None else schema for schema in DEFAULT_SCHEMA_NAMES
            ),
            "expected_physical_table_keys": sorted(EXPECTED_PHYSICAL_TABLE_KEYS),
        },
        "alembic_head": alembic_head,
        "canonical_mapped_table_count": len(metadata_keys),
        "canonical_mapped_table_keys": sorted(metadata_keys),
        "migration_owned_table_count": len(MIGRATION_OWNED_TABLE_KEYS),
        "migration_owned_table_keys": sorted(MIGRATION_OWNED_TABLE_KEYS),
        "migration_owned_object_count": (
            len(MIGRATION_OWNED_TABLE_KEYS) + len(MIGRATION_OWNED_INDEX_KEYS)
        ),
        "migration_owned_object_keys": sorted(
            MIGRATION_OWNED_TABLE_KEYS | MIGRATION_OWNED_INDEX_KEYS
        ),
        "alembic_internal_object_count": len(ALEMBIC_INTERNAL_TABLE_KEYS),
        "alembic_internal_object_keys": sorted(ALEMBIC_INTERNAL_TABLE_KEYS),
        "raw_operations": [asdict(record) for record in raw_operations],
        "admitted_operations": [asdict(record) for record in admitted_operations],
        "unknown_objects": list(normalized_unknown_objects),
        "unknown_operations": list(normalized_unknown_operations),
        "extension_validation": extension_validation,
        "rls_policy_validation": rls_policy_validation,
        "check_validation": check_validation,
        "sequence_validation": sequence_validation,
        "reason_codes": list(normalized_reasons),
    }
    digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(report_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    all_validations_passed = all(
        status == VALIDATION_PASSED
        for status in (
            extension_validation,
            rls_policy_validation,
            check_validation,
            sequence_validation,
        )
    )
    raw_drop_tables = [
        record.table_name
        for record in raw_operations
        if record.operation == "DropTableOp" and record.disposition == "migration_owned"
    ]
    raw_root_count = sum(
        record.operation == "UpgradeOps"
        and record.path == "upgrade"
        and record.disposition == "structural"
        for record in raw_operations
    )
    raw_contract_complete = (
        raw_root_count == 1
        and len(raw_drop_tables) == len(MIGRATION_OWNED_TABLE_KEYS)
        and set(raw_drop_tables) == MIGRATION_OWNED_TABLE_KEYS
    )
    admitted_contract_empty = len(admitted_operations) == 1 and admitted_operations[0] == (
        OperationDisposition(
            path="upgrade",
            operation="UpgradeOps",
            schema=None,
            table_name=None,
            object_name=None,
            disposition="structural",
            reason_code="admitted_root_container",
        )
    )
    pass_postconditions = (
        not normalized_reasons
        and not normalized_unknown_objects
        and not normalized_unknown_operations
        and admitted_contract_empty
        and raw_contract_complete
        and all(record.disposition != "unknown" for record in raw_operations)
        and alembic_head == EXPECTED_ALEMBIC_HEAD
        and metadata_keys == CANONICAL_MAPPED_TABLE_KEYS
        and all_validations_passed
    )
    result: Result = "pass" if pass_postconditions else "fail"
    return CompletenessReport(
        schema_version=REPORT_SCHEMA_VERSION,
        boundary=CLAIM_BOUNDARY,
        alembic_head=alembic_head,
        canonical_mapped_table_count=len(metadata_keys),
        canonical_mapped_table_keys=tuple(sorted(metadata_keys)),
        migration_owned_table_count=len(MIGRATION_OWNED_TABLE_KEYS),
        migration_owned_table_keys=tuple(sorted(MIGRATION_OWNED_TABLE_KEYS)),
        migration_owned_object_count=(
            len(MIGRATION_OWNED_TABLE_KEYS) + len(MIGRATION_OWNED_INDEX_KEYS)
        ),
        migration_owned_object_keys=tuple(
            sorted(MIGRATION_OWNED_TABLE_KEYS | MIGRATION_OWNED_INDEX_KEYS)
        ),
        alembic_internal_object_count=len(ALEMBIC_INTERNAL_TABLE_KEYS),
        alembic_internal_object_keys=tuple(sorted(ALEMBIC_INTERNAL_TABLE_KEYS)),
        raw_operations=raw_operations,
        admitted_operations=admitted_operations,
        unknown_objects=normalized_unknown_objects,
        unknown_operations=normalized_unknown_operations,
        extension_validation=extension_validation,
        rls_policy_validation=rls_policy_validation,
        check_validation=check_validation,
        sequence_validation=sequence_validation,
        reason_codes=normalized_reasons,
        material_digest=digest,
        result=result,
    )


def evaluate_alembic_autogenerate_completeness(
    connection: Connection,
    target_metadata: MetaData,
) -> CompletenessReport:
    """Evaluate the bounded Phase A rails and fail closed pending Phase B."""

    metadata_keys = frozenset(str(key) for key in target_metadata.tables)
    reasons: list[str] = []
    unknown_objects: list[str] = []
    from core.db import Base

    if target_metadata is not Base.metadata:
        return _make_report(
            alembic_head=None,
            metadata_keys=metadata_keys,
            reason_codes=("canonical_metadata_identity_mismatch",),
        )
    if metadata_keys != CANONICAL_MAPPED_TABLE_KEYS:
        reasons.append("canonical_metadata_table_inventory_mismatch")
        unknown_objects.extend(
            f"metadata_missing:public.{name}"
            for name in sorted(CANONICAL_MAPPED_TABLE_KEYS - metadata_keys)
        )
        unknown_objects.extend(
            f"metadata_extra:public.{name}"
            for name in sorted(metadata_keys - CANONICAL_MAPPED_TABLE_KEYS)
        )
        return _make_report(
            alembic_head=None,
            metadata_keys=metadata_keys,
            unknown_objects=tuple(unknown_objects),
            reason_codes=tuple(reasons),
        )

    if getattr(connection.dialect, "name", None) != "postgresql":
        return _make_report(
            alembic_head=None,
            metadata_keys=metadata_keys,
            reason_codes=("unsupported_dialect",),
        )

    try:
        alembic_head = _read_alembic_head(connection)
    except Exception:
        return _make_report(
            alembic_head=None,
            metadata_keys=metadata_keys,
            reason_codes=("alembic_head_read_failed",),
        )
    if alembic_head != EXPECTED_ALEMBIC_HEAD:
        reasons.append("alembic_head_mismatch")

    try:
        physical_keys = _reflect_physical_table_keys(connection)
    except Exception:
        return _make_report(
            alembic_head=alembic_head,
            metadata_keys=metadata_keys,
            reason_codes=tuple(reasons + ["physical_table_reflection_failed"]),
        )
    missing_physical = EXPECTED_PHYSICAL_TABLE_KEYS - physical_keys
    extra_physical = physical_keys - EXPECTED_PHYSICAL_TABLE_KEYS
    if missing_physical or extra_physical:
        reasons.append("physical_table_inventory_mismatch")
        unknown_objects.extend(
            f"physical_missing:public.{name}" for name in sorted(missing_physical)
        )
        unknown_objects.extend(f"physical_extra:public.{name}" for name in sorted(extra_physical))

    try:
        table_outcome = _validate_migration_table_signatures(
            _reflect_migration_table_signatures(connection)
        )
        ownership_outcome = _validate_ownership_rows(_read_ownership_rows(connection))
        extension_outcome = _validate_extensions(_read_extension_signatures(connection))
        rls_outcome = _validate_rls(_read_rls_signatures(connection))
        check_outcome = _validate_critical_checks(_read_critical_checks(connection))
        sequence_outcome = _validate_sequences(_read_sequences(connection))
    except Exception:
        return _make_report(
            alembic_head=alembic_head,
            metadata_keys=metadata_keys,
            unknown_objects=tuple(unknown_objects),
            reason_codes=tuple(reasons + ["postgresql_descriptor_validation_failed"]),
        )

    for outcome in (
        table_outcome,
        ownership_outcome,
        extension_outcome,
        rls_outcome,
        check_outcome,
        sequence_outcome,
    ):
        reasons.extend(outcome.reason_codes)
        unknown_objects.extend(outcome.unknown_objects)

    try:
        raw_root = _produce_upgrade_ops(connection, target_metadata, admitted=False)
        admitted_root = _produce_upgrade_ops(connection, target_metadata, admitted=True)
    except Exception as exc:
        return _make_report(
            alembic_head=alembic_head,
            metadata_keys=metadata_keys,
            unknown_objects=tuple(unknown_objects),
            reason_codes=tuple(reasons + [_classify_autogenerate_failure(exc)]),
        )

    raw_records, raw_unknown, raw_reasons = _classify_operation_tree(raw_root, rail="raw")
    admitted_records, admitted_unknown, admitted_reasons = _classify_operation_tree(
        admitted_root,
        rail="admitted",
    )
    reasons.extend(raw_reasons)
    reasons.extend(admitted_reasons)
    if raw_unknown:
        reasons.append("raw_operation_unclassified")
    if admitted_unknown:
        reasons.append("admitted_operation_tree_not_empty")

    return _make_report(
        alembic_head=alembic_head,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
        admitted_operations=admitted_records,
        unknown_objects=tuple(unknown_objects),
        unknown_operations=tuple(raw_unknown + admitted_unknown),
        reason_codes=tuple(reasons),
        extension_validation=extension_outcome.status,
        rls_policy_validation=rls_outcome.status,
        check_validation=check_outcome.status,
        sequence_validation=sequence_outcome.status,
    )


__all__ = [
    "ALEMBIC_INTERNAL_TABLE_KEYS",
    "CANONICAL_MAPPED_TABLE_KEYS",
    "CompletenessReport",
    "EXPECTED_ALEMBIC_HEAD",
    "MIGRATION_OWNED_INDEX_KEYS",
    "MIGRATION_OWNED_TABLE_KEYS",
    "OperationDisposition",
    "evaluate_alembic_autogenerate_completeness",
    "include_autogenerate_object",
]

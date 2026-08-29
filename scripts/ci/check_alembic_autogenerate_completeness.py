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
from typing import Literal

from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from alembic.operations import ops
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.schema import MetaData

from core.db_alembic_ownership import (
    DEFAULT_SCHEMA_NAMES,
    MIGRATION_OWNED_TABLE_KEYS,
    include_autogenerate_object,
)

EXPECTED_ALEMBIC_HEAD = "202608270001"
REPORT_SCHEMA_VERSION = "pulseplate.alembic_autogenerate_completeness.phase_a.v1"
CLAIM_BOUNDARY = (
    "repo=942cc0f10995d89be74f5ffc7ab9329809865e0b;"
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

        add_record(operation, path, "unknown", "raw_operation_not_admitted")

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
    pass_postconditions = (
        not normalized_reasons
        and not normalized_unknown_objects
        and not normalized_unknown_operations
        and not admitted_operations
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
        raw_root = _produce_upgrade_ops(connection, target_metadata, admitted=False)
        admitted_root = _produce_upgrade_ops(connection, target_metadata, admitted=True)
    except Exception:
        return _make_report(
            alembic_head=alembic_head,
            metadata_keys=metadata_keys,
            unknown_objects=tuple(unknown_objects),
            reason_codes=tuple(reasons + ["autogenerate_production_failed"]),
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

    # Phase A has no authority to claim descriptor, extension, RLS/policy,
    # CHECK, or sequence completeness.  The existing real-PostgreSQL contour
    # must discharge this reason in Phase B.
    reasons.append("phase_b_postgresql_descriptor_validation_required")
    return _make_report(
        alembic_head=alembic_head,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
        admitted_operations=admitted_records,
        unknown_objects=tuple(unknown_objects),
        unknown_operations=tuple(raw_unknown + admitted_unknown),
        reason_codes=tuple(reasons),
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

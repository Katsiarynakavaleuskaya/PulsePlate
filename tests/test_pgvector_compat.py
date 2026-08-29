"""Compatibility proof for the pgvector 0.5 Python binding and PostgreSQL 0.8.2.

The source/lock and import canaries always run.  The database assertions run
when ``PGVECTOR_COMPAT_DATABASE_URL`` is configured; CI makes that contract
mandatory with ``PGVECTOR_COMPAT_REQUIRED=1``.
"""

from __future__ import annotations

import ast
import asyncio
from datetime import date
from hashlib import sha256
import inspect
from itertools import chain
import json
import os
import re
import subprocess
import sys
import time
import warnings
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, cast
from urllib.parse import quote
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import (
    BigInteger,
    Column,
    Constraint,
    Index,
    MetaData,
    Table,
    Text,
    bindparam,
    create_engine,
    func,
    insert,
    select,
    text,
)
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import DBAPIError, InvalidRequestError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.types import UserDefinedType

from core.db_rls import apply_user_rls_context

REPO_ROOT = Path(__file__).resolve().parents[1]
PGVECTOR_COMPAT_DATABASE_URL = "PGVECTOR_COMPAT_DATABASE_URL"
PGVECTOR_COMPAT_REQUIRED = "PGVECTOR_COMPAT_REQUIRED"
PGVECTOR_BINDING_FEATURE = "pgvector_binding_ci_lite"
PGVECTOR_DATABASE_FEATURE = "pgvector_compat_database"
EXPECTED_BINDING_VERSION = "0.5.0"
EXPECTED_EXTENSION_VERSION = "0.8.2"
OWNER_PASSWORD = "pgvector_compat_owner_password"  # pragma: allowlist secret
TENANT_ONE = 101
TENANT_TWO = 202
ALEMBIC_DATABASE_PREFIX = "pulseplate_alembic_"
PRE_DRIFT_RECONCILIATION_HEAD = "202608270001"
EXPECTED_POSTFIX_ALEMBIC_RESIDUAL = frozenset(
    {
        "public.foods",
        "public.pulseplate_migration_ownership",
        "public.restaurant_chains",
        "public.restaurant_menu_items",
    }
)
UNEXPECTED_ALEMBIC_LEAF_REPORT_CAP = 128
FOUNDATION_OWNERSHIP_REVISION = "202604120001"
FOUNDATION_CATALOG_TABLES = frozenset({"foods", "restaurant_chains", "restaurant_menu_items"})
FOUNDATION_INTERNAL_TABLE = "pulseplate_migration_ownership"
FOUNDATION_INDEX_CONTRACTS = {
    ("foods", "ix_foods_canonical_name"): ("canonical_name", "btree", "text_ops"),
    ("foods", "ix_foods_group_name"): ("group_name", "btree", "text_ops"),
    ("foods", "ix_foods_source"): ("source", "btree", "text_ops"),
    ("foods", "ix_foods_gtin"): ("gtin", "btree", "text_ops"),
    ("foods", "ix_foods_canonical_name_gin_trgm"): (
        "canonical_name",
        "gin",
        "gin_trgm_ops",
    ),
    ("foods", "ix_foods_group_name_gin_trgm"): (
        "group_name",
        "gin",
        "gin_trgm_ops",
    ),
    ("foods", "ix_foods_brand_gin_trgm"): ("brand", "gin", "gin_trgm_ops"),
    ("restaurant_chains", "ix_restaurant_chains_name"): ("name", "btree", "text_ops"),
    ("restaurant_menu_items", "ix_restaurant_menu_items_chain_id"): (
        "chain_id",
        "btree",
        "text_ops",
    ),
    ("restaurant_menu_items", "ix_restaurant_menu_items_item_name"): (
        "item_name",
        "btree",
        "text_ops",
    ),
    ("restaurant_menu_items", "ix_restaurant_menu_items_food_id"): (
        "food_id",
        "btree",
        "text_ops",
    ),
}
EXPECTED_RAW_ALEMBIC_IDENTITIES = frozenset(
    {
        *(
            "operation_class=remove_table;subject_class=Table;"
            f"table=public.{table_name};object={table_name}"
            for table_name in (*sorted(FOUNDATION_CATALOG_TABLES), FOUNDATION_INTERNAL_TABLE)
        ),
        *(
            "operation_class=remove_index;subject_class=Index;"
            f"table=public.{table_name};object={index_name}"
            for table_name, index_name in sorted(FOUNDATION_INDEX_CONTRACTS)
        ),
    }
)
CONTROLLED_ALEMBIC_ENV = {
    "APP_ENV": "test",
    "ENVIRONMENT": "test",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONNOUSERSITE": "1",
    "TESTING": "true",
    "TZ": "UTC",
}
FORBIDDEN_ALEMBIC_ENV_KEYS = (
    "BASH_ENV",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "ENV",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "PULSEPLATE_SENTINEL_SECRET",
    "PYTHONHOME",
    "PYTHONINSPECT",
    "PYTHONPATH",
    "PYTHONPLATLIBDIR",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
)
PG_PROJECTION_VERSION = "pulseplate.postgres-resource-bounded-migration-state.v1"
PROJECTION_TABLE_CAP = 256
PROJECTION_COLUMN_CAP = 256
PG_DESCRIPTOR_AGGREGATE_CAP = 8192
PG_SEQUENCE_CAP = 256
PG_EXTENSION_CAP = 32
PROJECTION_ROWS_PER_TABLE_CAP = 10_000
PROJECTION_TOTAL_ROWS_CAP = 100_000
PROJECTION_SCALAR_BYTES_CAP = 1 * 1024 * 1024
PROJECTION_RECORD_BYTES_CAP = 4 * 1024 * 1024
PROJECTION_TOTAL_FRAMED_BYTES_CAP = 64 * 1024 * 1024
PROJECTION_FETCH_BATCH = 256
PG_STATEMENT_TIMEOUT_MAX_MS = 30_000
PROJECTION_DEADLINE_SECONDS = 120.0


def require_feature(feature_key: str, reason: str) -> NoReturn:
    """Use the repository skip protocol for optional compatibility dependencies."""

    assert feature_key in {PGVECTOR_BINDING_FEATURE, PGVECTOR_DATABASE_FEATURE}
    pytest.skip(f"feature_disabled:{feature_key} {reason}")
    raise AssertionError("pytest.skip returned unexpectedly")


def _skip_or_fail_binding(reason: str) -> NoReturn:
    if os.getenv("PRE_COMMIT", "").strip() == "1":
        require_feature(PGVECTOR_BINDING_FEATURE, reason)
    pytest.fail(reason)
    raise AssertionError("pytest.fail returned unexpectedly")


def _skip_or_fail_database(reason: str, *, required: bool) -> NoReturn:
    if required:
        pytest.fail(reason)
        raise AssertionError("pytest.fail returned unexpectedly")
    require_feature(PGVECTOR_DATABASE_FEATURE, reason)


def _vector_type(
    dimensions: int,
    *,
    module_loader: Callable[[str], ModuleType] = import_module,
) -> UserDefinedType:
    try:
        module = module_loader("pgvector.sqlalchemy")
    except ModuleNotFoundError as exc:
        if not exc.name or not exc.name.startswith("pgvector"):
            raise
        _skip_or_fail_binding("pgvector is unavailable in the ci-lite pre-commit environment")

    vector_factory = getattr(module, "VECTOR", None)
    if vector_factory is None:
        pytest.fail("pgvector.sqlalchemy.VECTOR is unavailable")
        raise AssertionError("pytest.fail returned unexpectedly")
    vector_type = vector_factory(dimensions)
    assert isinstance(vector_type, UserDefinedType)
    return vector_type


def _active_requirements(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _quote_identifier(engine: Engine, identifier: str) -> str:
    """Quote an internally generated PostgreSQL identifier."""

    quoted = engine.dialect.identifier_preparer.quote_identifier(identifier)
    if not isinstance(quoted, str):
        raise TypeError("PostgreSQL identifier preparer returned non-text")
    return quoted


def _required_ci_pgvector_url(environment: Mapping[str, str] | None = None) -> URL:
    source = os.environ if environment is None else environment
    required = source.get(PGVECTOR_COMPAT_REQUIRED, "").strip()
    database_url = source.get(PGVECTOR_COMPAT_DATABASE_URL, "").strip()
    if required != "1":
        if environment is None:
            require_feature(
                PGVECTOR_DATABASE_FEATURE,
                "resource-bounded migration projection requires PGVECTOR_COMPAT_REQUIRED=1",
            )
        pytest.fail(f"{PGVECTOR_COMPAT_REQUIRED} must equal 1")
    if source.get("CI", "").strip() != "true":
        pytest.fail("CI must equal true for the dedicated migration proof")
    if source.get("GITHUB_ACTIONS", "").strip() != "true":
        pytest.fail("GITHUB_ACTIONS must equal true for the dedicated migration proof")
    if not database_url:
        pytest.fail(f"{PGVECTOR_COMPAT_DATABASE_URL} is required")

    parsed_url = make_url(database_url)
    if parsed_url.query:
        pytest.fail(f"{PGVECTOR_COMPAT_DATABASE_URL} must not include query parameters")
    actual_contract = (
        parsed_url.drivername,
        parsed_url.host,
        parsed_url.port,
        parsed_url.username,
        parsed_url.database,
    )
    expected_contract = (
        "postgresql+psycopg",
        "localhost",
        5432,
        "pgvector_compat",
        "pgvector_compat",
    )
    if actual_contract != expected_contract:
        pytest.fail(f"{PGVECTOR_COMPAT_DATABASE_URL} must match the dedicated CI service tuple")
    return parsed_url


def _alembic_subprocess_env(database_url: URL) -> dict[str, str]:
    env = dict(CONTROLLED_ALEMBIC_ENV)
    env["DATABASE_URL"] = database_url.render_as_string(hide_password=False)
    return env


def _redact_database_output(value: str, database_url: URL) -> str:
    decoded_password = database_url.password or ""
    redactions = tuple(
        candidate
        for candidate in dict.fromkeys(
            (
                database_url.render_as_string(hide_password=False),
                quote(decoded_password, safe=""),
                decoded_password,
            )
        )
        if candidate
    )
    sanitized = value
    for redaction in sorted(redactions, key=len, reverse=True):
        sanitized = sanitized.replace(redaction, "[REDACTED]")
    return sanitized


def _normalize_timeout_partial_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return f"[unsupported-timeout-output:{type(value).__name__}]"


def _run_alembic(database_url: URL, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = _alembic_subprocess_env(database_url)
    command = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(REPO_ROOT / "alembic.ini"),
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _redact_database_output(
            _normalize_timeout_partial_output(exc.stdout),
            database_url,
        )
        stderr = _redact_database_output(
            _normalize_timeout_partial_output(exc.stderr),
            database_url,
        )
        pytest.fail(
            f"Alembic PostgreSQL subprocess timed out after {exc.timeout} seconds\n"
            f"stdout tail:\n{stdout[-4000:]}\n"
            f"stderr tail:\n{stderr[-4000:]}"
        )
    if completed.returncode != 0:
        stdout = _redact_database_output(completed.stdout, database_url)
        stderr = _redact_database_output(completed.stderr, database_url)
        pytest.fail(
            "Alembic PostgreSQL subprocess failed "
            f"(rc={completed.returncode})\n"
            f"stdout tail:\n{stdout[-4000:]}\n"
            f"stderr tail:\n{stderr[-4000:]}"
        )
    return completed


def _alembic_diff_identity(diff: object) -> str:
    """Return a bounded secret-free identity for one Alembic diff tuple."""

    if not isinstance(diff, tuple) or not diff:
        return (
            "operation_class=<unknown>;subject_class=<unknown>;"
            "table=public.<unknown>;object=<unknown>"
        )

    operation = diff[0] if isinstance(diff[0], str) else "<unknown>"
    subject = next(
        (item for item in diff[1:] if isinstance(item, (Table, Index, Constraint, Column))),
        None,
    )
    subject_class = "<unknown>" if subject is None else type(subject).__name__
    table: Table | None = subject if isinstance(subject, Table) else None
    object_name: str | None = subject.name if subject is not None else None
    if subject is not None and table is None:
        try:
            candidate_table = subject.table
        except (AttributeError, InvalidRequestError):
            candidate_table = None
        if isinstance(candidate_table, Table):
            table = candidate_table

    schema_name: str | None = None
    table_name: str | None = None
    if table is not None:
        schema_name = table.schema
        table_name = table.name
    elif len(diff) >= 4:
        schema_name = diff[1] if isinstance(diff[1], str) else None
        table_name = diff[2] if isinstance(diff[2], str) else None
        if object_name is None and isinstance(diff[3], str):
            object_name = diff[3]

    normalized_schema = "public" if schema_name in {None, "public"} else schema_name
    return (
        f"operation_class={operation};subject_class={subject_class};"
        f"table={normalized_schema}.{table_name or '<unknown>'};"
        f"object={object_name or '<unnamed>'}"
    )


def _fail_capped_identity_inventory(prefix: str, identities: Sequence[str]) -> NoReturn:
    """Fail once with a deterministic bounded identity inventory."""

    ordered_identities = sorted(identities)
    emitted_identities = ordered_identities[:UNEXPECTED_ALEMBIC_LEAF_REPORT_CAP]
    pytest.fail(
        f"{prefix}:"
        f"count={len(ordered_identities)};"
        f"cap={UNEXPECTED_ALEMBIC_LEAF_REPORT_CAP};"
        f"truncated={len(ordered_identities) > len(emitted_identities)};"
        f"identities={json.dumps(emitted_identities, separators=(',', ':'))}"
    )
    raise AssertionError("pytest.fail returned unexpectedly")


def _assert_foundation_ownership_rows(connection: Connection) -> None:
    """Cross-bind the closed foundation objects to their exact ownership rows."""

    inspector = sqlalchemy_inspect(connection)
    assert inspector.has_table(FOUNDATION_INTERNAL_TABLE, schema="public")
    observed_rows = tuple(
        tuple(str(value) for value in row)
        for row in connection.execute(
            text("""
                SELECT revision_id, object_type, table_name, object_name
                FROM public.pulseplate_migration_ownership
                WHERE revision_id = :revision_id
                ORDER BY object_type COLLATE "C", table_name COLLATE "C", object_name COLLATE "C"
                """),
            {"revision_id": FOUNDATION_OWNERSHIP_REVISION},
        ).all()
    )
    expected_rows = {
        *(
            (FOUNDATION_OWNERSHIP_REVISION, "table", table_name, table_name)
            for table_name in FOUNDATION_CATALOG_TABLES
        ),
        *(
            (FOUNDATION_OWNERSHIP_REVISION, "index", table_name, index_name)
            for table_name, index_name in FOUNDATION_INDEX_CONTRACTS
        ),
    }
    if len(observed_rows) != len(expected_rows) or set(observed_rows) != expected_rows:
        identities = tuple(
            "ownership_row:"
            f"revision={revision_id};type={object_type};"
            f"table=public.{table_name};object={object_name}"
            for revision_id, object_type, table_name, object_name in observed_rows
        )
        _fail_capped_identity_inventory("foundation_ownership_mismatch", identities)


def _fail_foundation_index_descriptor(table_name: str, index_name: str, field: str) -> NoReturn:
    pytest.fail(
        "foundation_index_descriptor_mismatch:"
        f"table=public.{table_name};object={index_name};field={field}"
    )
    raise AssertionError("pytest.fail returned unexpectedly")


def _assert_foundation_index_descriptors(connection: Connection) -> None:
    """Validate the exact physical descriptor of every migration-owned index."""

    rows = connection.execute(text("""
            SELECT
                table_relation.relname AS table_name,
                index_relation.relname AS index_name,
                ARRAY(
                    SELECT attribute.attname
                    FROM pg_catalog.unnest(index_state.indkey) WITH ORDINALITY
                        AS index_key(attribute_number, position)
                    JOIN pg_catalog.pg_attribute AS attribute
                      ON attribute.attrelid = table_relation.oid
                     AND attribute.attnum = index_key.attribute_number
                    WHERE index_key.position <= index_state.indnkeyatts
                    ORDER BY index_key.position
                ) AS key_columns,
                ARRAY(
                    SELECT selected_opclass.opcname
                    FROM pg_catalog.unnest(index_state.indclass) WITH ORDINALITY
                        AS index_opclass(opclass_oid, position)
                    JOIN pg_catalog.pg_opclass AS selected_opclass
                      ON selected_opclass.oid = index_opclass.opclass_oid
                    WHERE index_opclass.position <= index_state.indnkeyatts
                    ORDER BY index_opclass.position
                ) AS opclass_names,
                access_method.amname AS access_method,
                index_state.indisunique AS is_unique,
                index_state.indisvalid AS is_valid,
                index_state.indisready AS is_ready,
                index_state.indislive AS is_live,
                index_state.indnatts - index_state.indnkeyatts AS included_column_count,
                pg_catalog.pg_get_expr(index_state.indpred, index_state.indrelid) AS predicate,
                pg_catalog.pg_get_expr(index_state.indexprs, index_state.indrelid) AS expressions,
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
                    'foods', 'restaurant_chains', 'restaurant_menu_items'
              )
              AND index_relation.relname IN (
                    'ix_foods_brand_gin_trgm',
                    'ix_foods_canonical_name',
                    'ix_foods_canonical_name_gin_trgm',
                    'ix_foods_group_name',
                    'ix_foods_group_name_gin_trgm',
                    'ix_foods_gtin',
                    'ix_foods_source',
                    'ix_restaurant_chains_name',
                    'ix_restaurant_menu_items_chain_id',
                    'ix_restaurant_menu_items_food_id',
                    'ix_restaurant_menu_items_item_name'
              )
            ORDER BY table_relation.relname COLLATE "C", index_relation.relname COLLATE "C"
            """)).mappings().all()
    observed_keys = tuple((str(row["table_name"]), str(row["index_name"])) for row in rows)
    if len(observed_keys) != len(FOUNDATION_INDEX_CONTRACTS) or set(observed_keys) != set(
        FOUNDATION_INDEX_CONTRACTS
    ):
        identities = tuple(
            f"foundation_index:table=public.{table_name};object={index_name}"
            for table_name, index_name in observed_keys
        )
        _fail_capped_identity_inventory("foundation_index_inventory_mismatch", identities)

    inspector = sqlalchemy_inspect(connection)
    inspector_indexes = {
        (table_name, str(index["name"])): index
        for table_name in FOUNDATION_CATALOG_TABLES
        for index in inspector.get_indexes(table_name, schema="public")
        if index.get("name") is not None
    }
    for row in rows:
        table_name = str(row["table_name"])
        index_name = str(row["index_name"])
        expected_column, expected_access_method, expected_opclass = FOUNDATION_INDEX_CONTRACTS[
            (table_name, index_name)
        ]
        key_columns = row["key_columns"]
        opclass_names = row["opclass_names"]
        checks = (
            (
                "key_columns",
                isinstance(key_columns, (list, tuple)) and tuple(key_columns) == (expected_column,),
            ),
            (
                "opclass",
                isinstance(opclass_names, (list, tuple))
                and tuple(opclass_names) == (expected_opclass,),
            ),
            ("access_method", str(row["access_method"]) == expected_access_method),
            ("unique", row["is_unique"] is False),
            ("valid", row["is_valid"] is True),
            ("ready", row["is_ready"] is True),
            ("live", row["is_live"] is True),
            ("include_columns", int(row["included_column_count"]) == 0),
            ("predicate", row["predicate"] is None),
            ("expressions", row["expressions"] is None),
            ("constraint_owner", row["constraint_owner"] is None),
        )
        for descriptor_field, accepted in checks:
            if not accepted:
                _fail_foundation_index_descriptor(table_name, index_name, descriptor_field)

        inspected = inspector_indexes.get((table_name, index_name))
        if inspected is None:
            _fail_foundation_index_descriptor(table_name, index_name, "inspector_presence")
        if tuple(str(value) for value in inspected.get("column_names") or ()) != (expected_column,):
            _fail_foundation_index_descriptor(table_name, index_name, "inspector_columns")
        if bool(inspected.get("unique")):
            _fail_foundation_index_descriptor(table_name, index_name, "inspector_unique")


def _assert_exact_postfix_alembic_residual(connection: Connection) -> None:
    """Require the 23 reconciled leaves to be absent from a full comparison.

    The remaining exact four tables are owned by migration-only schema history
    and are intentionally left for the separate autogenerate-completeness lane.
    This assertion does not install or duplicate that lane's object filter.
    """

    from core.db import load_canonical_orm_metadata
    from core.db_alembic_comparison import compare_postgresql_server_default

    metadata = load_canonical_orm_metadata()
    comparison_context = MigrationContext.configure(
        connection,
        opts={
            "compare_type": True,
            "compare_server_default": compare_postgresql_server_default,
        },
    )
    with warnings.catch_warnings(record=True) as comparison_warnings:
        warnings.simplefilter("always")
        migration_script = produce_migrations(comparison_context, metadata)

    assert not comparison_warnings, tuple(
        f"{warning.category.__name__}:{warning.message}" for warning in comparison_warnings
    )
    diffs = tuple(migration_script.upgrade_ops.as_diffs())
    observed_identities = tuple(_alembic_diff_identity(diff) for diff in diffs)
    if (
        len(observed_identities) != len(EXPECTED_RAW_ALEMBIC_IDENTITIES)
        or set(observed_identities) != EXPECTED_RAW_ALEMBIC_IDENTITIES
    ):
        _fail_capped_identity_inventory("alembic_raw_residual_mismatch", observed_identities)

    remove_table_keys = frozenset(
        identity.split("table=", maxsplit=1)[1].split(";", maxsplit=1)[0]
        for identity in observed_identities
        if identity.startswith("operation_class=remove_table;")
    )
    assert remove_table_keys == EXPECTED_POSTFIX_ALEMBIC_RESIDUAL
    _assert_foundation_ownership_rows(connection)
    _assert_foundation_index_descriptors(connection)


def _drift_unique_object_inventory(connection: Connection) -> tuple[tuple[object, ...], ...]:
    """Return exact stable descriptors for the two reconciled unique objects."""

    rows = connection.execute(text("""
            SELECT
                table_relation.relname AS table_name,
                index_relation.relname AS index_name,
                index_state.indisunique AS is_unique,
                constraint_state.conname AS constraint_name,
                ARRAY(
                    SELECT attribute.attname
                    FROM unnest(index_state.indkey) WITH ORDINALITY
                        AS index_key(attribute_number, position)
                    JOIN pg_attribute AS attribute
                      ON attribute.attrelid = table_relation.oid
                     AND attribute.attnum = index_key.attribute_number
                    ORDER BY index_key.position
                ) AS column_names
            FROM pg_index AS index_state
            JOIN pg_class AS index_relation
              ON index_relation.oid = index_state.indexrelid
            JOIN pg_class AS table_relation
              ON table_relation.oid = index_state.indrelid
            JOIN pg_namespace AS namespace
              ON namespace.oid = table_relation.relnamespace
            LEFT JOIN pg_constraint AS constraint_state
              ON constraint_state.conindid = index_state.indexrelid
            WHERE namespace.nspname = 'public'
              AND (
                    (table_relation.relname = 'analyzer_state'
                     AND index_relation.relname IN (
                         'uq_analyzer_state_user_key',
                         'uq_analyzer_state_user_key_restore'
                     ))
                 OR (table_relation.relname = 'day_plans'
                     AND index_relation.relname IN (
                         'uq_day_plans_user_date',
                         'ix_day_plans_user_date',
                         'ix_day_plans_user_date_restore'
                     ))
              )
            ORDER BY table_relation.relname COLLATE "C", index_relation.relname COLLATE "C"
            """)).all()
    return tuple(
        (
            str(row.table_name),
            str(row.index_name),
            bool(row.is_unique),
            None if row.constraint_name is None else str(row.constraint_name),
            tuple(str(column_name) for column_name in row.column_names),
        )
        for row in rows
    )


def _frame_postgres_payload(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, byteorder="big", signed=False) + payload


def _require_pg_cap(label: str, observed: int, cap: int) -> None:
    if observed > cap:
        raise ValueError(f"{label} exceeds fixed resource bound: observed={observed}, cap={cap}")


def _pg_remaining_statement_ms(
    started_at: float,
    *,
    now: Callable[[], float] = time.monotonic,
    deadline_seconds: float = PROJECTION_DEADLINE_SECONDS,
) -> int:
    remaining_ms = int((deadline_seconds - (now() - started_at)) * 1000)
    if remaining_ms <= 0:
        raise TimeoutError("Resource-bounded migration-state projection deadline exceeded")
    return min(PG_STATEMENT_TIMEOUT_MAX_MS, remaining_ms)


def _encode_pg_scalar(value: object, *, cap: int = PROJECTION_SCALAR_BYTES_CAP) -> bytes:
    if value is None:
        encoded = b"null:"
    elif type(value) is bool:
        encoded = b"bool:true" if value else b"bool:false"
    elif type(value) is int:
        encoded = b"int:" + str(value).encode("ascii")
    elif isinstance(value, str):
        encoded = b"text:" + value.encode("utf-8")
    else:
        raise TypeError(f"Unsupported PostgreSQL projection scalar type: {type(value).__name__}")
    _require_pg_cap("PostgreSQL encoded scalar bytes", len(encoded), cap)
    return encoded


@dataclass
class _PostgresProjectionHasher:
    scalar_cap: int = PROJECTION_SCALAR_BYTES_CAP
    record_cap: int = PROJECTION_RECORD_BYTES_CAP
    total_cap: int = PROJECTION_TOTAL_FRAMED_BYTES_CAP
    total_framed_bytes: int = 0
    _hasher: Any = field(default_factory=sha256, init=False, repr=False)

    def _add_framed_record(self, record: bytes) -> None:
        _require_pg_cap("PostgreSQL encoded record bytes", len(record), self.record_cap)
        framed = _frame_postgres_payload(record)
        _require_pg_cap(
            "PostgreSQL total framed bytes",
            self.total_framed_bytes + len(framed),
            self.total_cap,
        )
        self._hasher.update(framed)
        self.total_framed_bytes += len(framed)

    def add_record(self, parts: Iterable[bytes]) -> None:
        record = bytearray()
        for part in parts:
            _require_pg_cap("PostgreSQL encoded scalar bytes", len(part), self.scalar_cap)
            record.extend(_frame_postgres_payload(part))
            _require_pg_cap("PostgreSQL encoded record bytes", len(record), self.record_cap)
        self._add_framed_record(bytes(record))

    def add_projected_payload(
        self,
        payload: object,
        max_scalar_octets: object,
        framed_record_octets: object,
    ) -> None:
        if not isinstance(payload, str):
            raise TypeError(
                f"PostgreSQL projected payload must be text, got {type(payload).__name__}"
            )
        if type(max_scalar_octets) is not int or type(framed_record_octets) is not int:
            raise TypeError("PostgreSQL projected byte metadata must be exact integers")
        payload_bytes = payload.encode("utf-8")
        if len(payload_bytes) + 8 != framed_record_octets:
            raise ValueError("PostgreSQL projected framed-byte metadata mismatch")
        _require_pg_cap(
            "PostgreSQL projected maximum scalar bytes",
            max_scalar_octets,
            self.scalar_cap,
        )
        _require_pg_cap(
            "PostgreSQL projected framed record bytes",
            framed_record_octets,
            self.record_cap,
        )
        self._add_framed_record(payload_bytes)

    def hexdigest(self) -> str:
        digest = self._hasher.hexdigest()
        if not isinstance(digest, str):
            raise TypeError("PostgreSQL projection digest must be text")
        return digest

    def remaining_bytes(self) -> int:
        return self.total_cap - self.total_framed_bytes


@dataclass(frozen=True)
class _PgPayloadPreflight:
    count: int
    max_scalar_bytes: int
    max_record_bytes: int
    total_bytes: int
    fetch_batch: int


def _derive_pg_fetch_batch(total_remaining: int, max_record_bytes: int) -> int:
    return max(
        1,
        min(
            PROJECTION_FETCH_BATCH,
            total_remaining // max(1, max_record_bytes),
        ),
    )


def _pg_synthetic_projection_digest(
    records: Iterable[Sequence[object]],
    *,
    record_cap: int,
) -> tuple[str, int]:
    hasher = _PostgresProjectionHasher(total_cap=64 * 1024)
    hasher.add_record((b"postgres-synthetic-migration-projection.v1",))
    observed = 0
    for record in records:
        observed += 1
        _require_pg_cap("synthetic PostgreSQL records", observed, record_cap)
        hasher.add_record(_encode_pg_scalar(value, cap=1024) for value in record)
    return hasher.hexdigest(), observed


def _pg_synthetic_sequence_digest(
    states: Iterable[tuple[str, str, object, object]],
    *,
    sequence_cap: int,
) -> tuple[str, int]:
    hasher = _PostgresProjectionHasher(total_cap=64 * 1024)
    hasher.add_record((b"postgres-synthetic-sequence-projection.v1",))
    observed = 0
    for schema_name, sequence_name, last_value, is_called in states:
        observed += 1
        _require_pg_cap("synthetic PostgreSQL sequences", observed, sequence_cap)
        if type(last_value) is not int:
            raise TypeError(
                f"PostgreSQL sequence last_value type is {type(last_value).__name__}, expected int"
            )
        if type(is_called) is not bool:
            raise TypeError(
                f"PostgreSQL sequence is_called type is {type(is_called).__name__}, expected bool"
            )
        hasher.add_record(
            (
                _encode_pg_scalar(schema_name, cap=1024),
                _encode_pg_scalar(sequence_name, cap=1024),
                _encode_pg_scalar(last_value, cap=1024),
                _encode_pg_scalar(is_called, cap=1024),
            )
        )
    return hasher.hexdigest(), observed


def _quote_pg_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _pg_execute_bounded(
    connection: Connection,
    statement: str,
    parameters: Mapping[str, object],
    *,
    started_at: float,
    stream_batch: int | None = None,
) -> Any:
    timeout_ms = _pg_remaining_statement_ms(started_at)
    connection.exec_driver_sql(f"SET LOCAL statement_timeout = {timeout_ms}")
    statement_object = text(statement)
    if stream_batch is not None:
        statement_object = statement_object.execution_options(
            stream_results=True,
            yield_per=stream_batch,
            max_row_buffer=stream_batch,
        )
    return connection.execute(statement_object, parameters)


def _validate_pg_payload_preflight(
    row: Sequence[object],
    *,
    expected_count: int,
    hasher: _PostgresProjectionHasher,
) -> _PgPayloadPreflight:
    if len(row) != 4 or any(type(value) is not int for value in row):
        raise ValueError("PostgreSQL payload preflight metadata must be exact integers")
    count, max_scalar, max_record, total = row
    if count != expected_count:
        raise ValueError("PostgreSQL payload preflight count does not match census")
    exact_count = count
    exact_max_scalar = cast(int, max_scalar)
    exact_max_record = cast(int, max_record)
    exact_total = cast(int, total)
    _require_pg_cap("PostgreSQL preflight scalar bytes", exact_max_scalar, hasher.scalar_cap)
    _require_pg_cap("PostgreSQL preflight record bytes", exact_max_record, hasher.record_cap)
    _require_pg_cap(
        "PostgreSQL preflight total bytes",
        exact_total,
        hasher.remaining_bytes(),
    )
    return _PgPayloadPreflight(
        count=exact_count,
        max_scalar_bytes=exact_max_scalar,
        max_record_bytes=exact_max_record,
        total_bytes=exact_total,
        fetch_batch=_derive_pg_fetch_batch(hasher.remaining_bytes(), exact_max_record),
    )


def _pg_typed_payload_query(
    kind: str,
    raw_query: str,
    *,
    passthrough_aliases: Sequence[str] = (),
) -> str:
    kind_literal = _quote_pg_literal(kind)
    passthrough = "".join(f", raw_projection.{alias}" for alias in passthrough_aliases)
    projected_passthrough = "".join(
        f", payload_projection.{alias}" for alias in passthrough_aliases
    )
    return f"""
        WITH raw_projection AS ({raw_query}),
        payload_projection AS (
            SELECT
                jsonb_build_array({kind_literal}, to_jsonb(raw_projection))::text AS payload,
                GREATEST(
                    octet_length(to_jsonb({kind_literal}::text)::text),
                    COALESCE((
                        SELECT MAX(GREATEST(
                            octet_length(to_jsonb(entry.key)::text),
                            octet_length(entry.value::text)
                        ))
                        FROM jsonb_each(to_jsonb(raw_projection)) AS entry
                    ), 0)
                )::bigint AS max_scalar_octets
                {passthrough}
            FROM raw_projection
        )
        SELECT payload,
               max_scalar_octets,
               (8 + octet_length(payload))::bigint AS framed_record_octets
               {projected_passthrough}
        FROM payload_projection
    """


def _pg_projected_payload_preflight(
    connection: Connection,
    projected_query: str,
    parameters: Mapping[str, object],
    *,
    expected_count: int,
    hasher: _PostgresProjectionHasher,
    started_at: float,
) -> _PgPayloadPreflight:
    result = _pg_execute_bounded(
        connection,
        f"""
        WITH exact_projection AS ({projected_query})
        SELECT COUNT(*)::bigint,
               COALESCE(MAX(max_scalar_octets), 0)::bigint,
               COALESCE(MAX(framed_record_octets), 0)::bigint,
               COALESCE(SUM(framed_record_octets), 0)::bigint
        FROM exact_projection
        """,
        parameters,
        started_at=started_at,
    )
    batch = result.fetchmany(PROJECTION_FETCH_BATCH)
    if len(batch) != 1:
        raise ValueError("PostgreSQL payload preflight returned invalid metadata rows")
    preflight = _validate_pg_payload_preflight(
        batch[0],
        expected_count=expected_count,
        hasher=hasher,
    )
    _pg_remaining_statement_ms(started_at)
    return preflight


def _pg_stream_projected_content(
    connection: Connection,
    projected_query: str,
    parameters: Mapping[str, object],
    *,
    expected_count: int,
    cap: int,
    hasher: _PostgresProjectionHasher,
    started_at: float,
) -> tuple[Any, _PgPayloadPreflight]:
    preflight = _pg_projected_payload_preflight(
        connection,
        projected_query,
        parameters,
        expected_count=expected_count,
        hasher=hasher,
        started_at=started_at,
    )
    result = _pg_execute_bounded(
        connection,
        f"""
        SELECT *
        FROM ({projected_query}) AS admitted_projection
        WHERE max_scalar_octets <= {PROJECTION_SCALAR_BYTES_CAP}
          AND framed_record_octets <= {PROJECTION_RECORD_BYTES_CAP}
        ORDER BY payload COLLATE "C"
        LIMIT {cap + 1}
        """,
        parameters,
        started_at=started_at,
        stream_batch=preflight.fetch_batch,
    )
    return result, preflight


def _pg_census(
    connection: Connection,
    inner_query: str,
    parameters: Mapping[str, object],
    *,
    cap: int,
    started_at: float,
) -> int:
    result = _pg_execute_bounded(
        connection,
        f"SELECT COUNT(*) FROM ({inner_query} LIMIT {cap + 1}) AS bounded_census",
        parameters,
        started_at=started_at,
    )
    batch = result.fetchmany(PROJECTION_FETCH_BATCH)
    if len(batch) != 1 or len(batch[0]) != 1 or type(batch[0][0]) is not int:
        raise ValueError("PostgreSQL bounded census returned invalid metadata")
    observed = int(batch[0][0])
    _require_pg_cap("PostgreSQL census", observed, cap)
    _pg_remaining_statement_ms(started_at)
    return observed


def _project_pg_descriptor_query(
    connection: Connection,
    hasher: _PostgresProjectionHasher,
    *,
    kind: str,
    inner_query: str,
    ordered_query: str,
    parameters: Mapping[str, object],
    cap: int,
    started_at: float,
) -> int:
    expected = _pg_census(
        connection,
        inner_query,
        parameters,
        cap=cap,
        started_at=started_at,
    )
    projected_query = _pg_typed_payload_query(kind, ordered_query)
    result, preflight = _pg_stream_projected_content(
        connection,
        projected_query,
        parameters,
        expected_count=expected,
        cap=cap,
        hasher=hasher,
        started_at=started_at,
    )
    observed = 0
    while True:
        _pg_remaining_statement_ms(started_at)
        batch = result.fetchmany(preflight.fetch_batch)
        if not batch:
            break
        for row in batch:
            observed += 1
            if len(row) != 3:
                raise ValueError("PostgreSQL descriptor payload metadata is invalid")
            hasher.add_projected_payload(row[0], row[1], row[2])
        _pg_remaining_statement_ms(started_at)
    if observed != expected:
        raise ValueError(f"PostgreSQL {kind} census/content count mismatch")
    return observed


def _project_postgres_migration_state(engine: Engine) -> _PostgresMigrationProjectionReceipt:
    caps = (
        ("tables", PROJECTION_TABLE_CAP),
        ("columns_per_table", PROJECTION_COLUMN_CAP),
        ("descriptor_aggregate", PG_DESCRIPTOR_AGGREGATE_CAP),
        ("sequences", PG_SEQUENCE_CAP),
        ("extensions", PG_EXTENSION_CAP),
        ("rows_per_table", PROJECTION_ROWS_PER_TABLE_CAP),
        ("total_rows", PROJECTION_TOTAL_ROWS_CAP),
        ("scalar_bytes", PROJECTION_SCALAR_BYTES_CAP),
        ("record_bytes", PROJECTION_RECORD_BYTES_CAP),
        ("total_framed_bytes", PROJECTION_TOTAL_FRAMED_BYTES_CAP),
        ("fetch_batch", PROJECTION_FETCH_BATCH),
        ("statement_timeout_ms", PG_STATEMENT_TIMEOUT_MAX_MS),
        ("deadline_seconds", int(PROJECTION_DEADLINE_SECONDS)),
    )
    started_at = time.monotonic()
    hasher = _PostgresProjectionHasher()
    hasher.add_record((PG_PROJECTION_VERSION.encode("ascii"),))
    for cap_name, cap_value in caps:
        hasher.add_record((cap_name.encode("ascii"), str(cap_value).encode("ascii")))

    descriptor_count = 0
    table_count = 0
    total_rows = 0
    sequence_count = 0
    extension_count = 0
    head = ""
    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            transaction = connection.begin()
            try:
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")

                head_expected = _pg_census(
                    connection,
                    "SELECT version_num FROM alembic_version",
                    {},
                    cap=1,
                    started_at=started_at,
                )
                head_result = _pg_execute_bounded(
                    connection,
                    "SELECT version_num FROM alembic_version "
                    'ORDER BY version_num COLLATE "C" LIMIT 2',
                    {},
                    started_at=started_at,
                )
                head_observed = 0
                while True:
                    _pg_remaining_statement_ms(started_at)
                    batch = head_result.fetchmany(PROJECTION_FETCH_BATCH)
                    if not batch:
                        break
                    for row in batch:
                        head_observed += 1
                        if len(row) != 1 or not isinstance(row[0], str) or not row[0]:
                            raise ValueError("PostgreSQL Alembic head has invalid bounded metadata")
                        head = row[0]
                    _pg_remaining_statement_ms(started_at)
                if head_expected != 1 or head_observed != head_expected:
                    raise ValueError("PostgreSQL migration projection requires exactly one head")
                hasher.add_record((b"head", _encode_pg_scalar(head)))

                relation_from = """
                    FROM pg_class AS relation
                    JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                    WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema')
                      AND namespace.nspname !~ '^pg_'
                      AND relation.relkind IN ('r', 'p')
                      AND NOT EXISTS (
                          SELECT 1 FROM pg_depend AS extension_dependency
                          WHERE extension_dependency.classid = 'pg_class'::regclass
                            AND extension_dependency.objid = relation.oid
                            AND extension_dependency.deptype = 'e'
                      )
                """
                table_count = _pg_census(
                    connection,
                    f"SELECT 1 {relation_from}",
                    {},
                    cap=PROJECTION_TABLE_CAP,
                    started_at=started_at,
                )
                relation_content_query = f"""
                    SELECT
                        namespace.nspname AS schema_name,
                        relation.relname AS table_name,
                        relation.relkind::text AS relation_kind,
                        relation.relpersistence::text AS persistence_kind,
                        relation.relrowsecurity AS row_security_enabled,
                        relation.relforcerowsecurity AS row_security_forced
                    {relation_from}
                    ORDER BY namespace.nspname COLLATE "C", relation.relname COLLATE "C"
                """
                relation_projection = _pg_typed_payload_query(
                    "relation",
                    relation_content_query,
                    passthrough_aliases=("schema_name", "table_name"),
                )
                table_result, relation_preflight = _pg_stream_projected_content(
                    connection,
                    relation_projection,
                    {},
                    expected_count=table_count,
                    cap=PROJECTION_TABLE_CAP,
                    hasher=hasher,
                    started_at=started_at,
                )
                tables_observed = 0
                while True:
                    _pg_remaining_statement_ms(started_at)
                    table_batch = table_result.fetchmany(relation_preflight.fetch_batch)
                    if not table_batch:
                        break
                    for relation_row in table_batch:
                        tables_observed += 1
                        if len(relation_row) != 5:
                            raise ValueError("PostgreSQL relation payload metadata is invalid")
                        schema_name = relation_row[3]
                        table_name = relation_row[4]
                        if not isinstance(schema_name, str) or not isinstance(table_name, str):
                            raise ValueError("PostgreSQL relation identity is not bounded text")
                        table_identity = f"{schema_name}.{table_name}"
                        hasher.add_projected_payload(
                            relation_row[0], relation_row[1], relation_row[2]
                        )
                        descriptor_count += 1
                        _require_pg_cap(
                            "PostgreSQL descriptor aggregate",
                            descriptor_count,
                            PG_DESCRIPTOR_AGGREGATE_CAP,
                        )
                        quoted_schema = _quote_identifier(engine, schema_name)
                        quoted_table = _quote_identifier(engine, table_name)
                        table_parameters = {"schema_name": schema_name, "table_name": table_name}

                        column_from = """
                            FROM pg_attribute AS attribute
                            JOIN pg_class AS relation ON relation.oid = attribute.attrelid
                            JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                            LEFT JOIN pg_attrdef AS default_record
                              ON default_record.adrelid = relation.oid
                             AND default_record.adnum = attribute.attnum
                            WHERE namespace.nspname = :schema_name
                              AND relation.relname = :table_name
                              AND attribute.attnum > 0
                              AND NOT attribute.attisdropped
                        """
                        descriptor_remaining = PG_DESCRIPTOR_AGGREGATE_CAP - descriptor_count
                        column_cap = min(PROJECTION_COLUMN_CAP, descriptor_remaining)
                        column_count = _pg_census(
                            connection,
                            f"SELECT 1 {column_from}",
                            table_parameters,
                            cap=column_cap,
                            started_at=started_at,
                        )
                        if column_count == 0:
                            raise ValueError("PostgreSQL admitted relation has zero columns")
                        column_content_query = f"""
                            SELECT
                                CAST(:schema_name AS text) AS relation_schema,
                                CAST(:table_name AS text) AS relation_name,
                                attribute.attnum AS attribute_number,
                                attribute.attname AS column_name,
                                format_type(attribute.atttypid, attribute.atttypmod)
                                  AS type_name,
                                attribute.attnotnull AS not_null,
                                pg_get_expr(default_record.adbin, default_record.adrelid)
                                  AS default_expression,
                                attribute.attidentity::text AS identity_kind,
                                attribute.attgenerated::text AS generated_kind
                            {column_from}
                            ORDER BY attribute.attnum
                        """
                        column_projection = _pg_typed_payload_query(
                            "column",
                            column_content_query,
                            passthrough_aliases=(
                                "attribute_number",
                                "column_name",
                                "type_name",
                            ),
                        )
                        column_result, column_preflight = _pg_stream_projected_content(
                            connection,
                            column_projection,
                            table_parameters,
                            expected_count=column_count,
                            cap=column_cap,
                            hasher=hasher,
                            started_at=started_at,
                        )
                        columns_observed = 0
                        cell_expressions = ""
                        scalar_octet_expressions = ""
                        while True:
                            _pg_remaining_statement_ms(started_at)
                            column_batch = column_result.fetchmany(column_preflight.fetch_batch)
                            if not column_batch:
                                break
                            for column_row in column_batch:
                                columns_observed += 1
                                if len(column_row) != 6:
                                    raise ValueError(
                                        "PostgreSQL column payload metadata is invalid"
                                    )
                                attnum, column_name, type_name = column_row[3:6]
                                if (
                                    type(attnum) is not int
                                    or not isinstance(column_name, str)
                                    or not isinstance(type_name, str)
                                ):
                                    raise ValueError(
                                        "PostgreSQL column descriptor has invalid types"
                                    )
                                hasher.add_projected_payload(
                                    column_row[0], column_row[1], column_row[2]
                                )
                                descriptor_count += 1
                                _require_pg_cap(
                                    "PostgreSQL descriptor aggregate",
                                    descriptor_count,
                                    PG_DESCRIPTOR_AGGREGATE_CAP,
                                )
                                quoted_column = _quote_identifier(engine, column_name)
                                column_literal = _quote_pg_literal(column_name)
                                type_literal = _quote_pg_literal(type_name)
                                type_tag_literal = _quote_pg_literal(f"pg:{type_name}")
                                cell_expressions += (", " if cell_expressions else "") + (
                                    f"jsonb_build_array({attnum}, {column_literal}, {type_literal}, "
                                    f"{type_tag_literal}, to_jsonb(row_value.{quoted_column}))"
                                )
                                scalar_octet_expressions += (
                                    ", " if scalar_octet_expressions else ""
                                ) + (
                                    "GREATEST("
                                    f"octet_length(to_jsonb({attnum})::text), "
                                    f"octet_length(to_jsonb({column_literal}::text)::text), "
                                    f"octet_length(to_jsonb({type_literal}::text)::text), "
                                    f"octet_length(to_jsonb({type_tag_literal}::text)::text), "
                                    "octet_length(COALESCE("
                                    f"to_jsonb(row_value.{quoted_column})::text, 'null')))"
                                )
                            _pg_remaining_statement_ms(started_at)
                        if columns_observed != column_count:
                            raise ValueError("PostgreSQL column census/content count mismatch")

                        descriptor_specs = (
                            (
                                "constraint",
                                """
                                FROM pg_constraint AS descriptor
                                JOIN pg_class AS relation ON relation.oid = descriptor.conrelid
                                JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                                WHERE namespace.nspname = :schema_name
                                  AND relation.relname = :table_name
                                  AND NOT EXISTS (
                                      SELECT 1 FROM pg_depend AS extension_dependency
                                      WHERE extension_dependency.classid = 'pg_constraint'::regclass
                                        AND extension_dependency.objid = descriptor.oid
                                        AND extension_dependency.deptype = 'e'
                                  )
                                """,
                                """
                                SELECT CAST(:schema_name AS text) AS relation_schema,
                                       CAST(:table_name AS text) AS relation_name,
                                       descriptor.conname AS constraint_name,
                                       descriptor.contype::text AS constraint_kind,
                                       descriptor.condeferrable AS is_deferrable,
                                       descriptor.condeferred AS initially_deferred,
                                       descriptor.convalidated AS is_validated,
                                       pg_get_constraintdef(descriptor.oid, true)
                                         AS constraint_definition
                                """,
                                'ORDER BY descriptor.conname COLLATE "C"',
                            ),
                            (
                                "index",
                                """
                                FROM pg_index AS index_record
                                JOIN pg_class AS index_relation
                                  ON index_relation.oid = index_record.indexrelid
                                JOIN pg_class AS relation ON relation.oid = index_record.indrelid
                                JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                                WHERE namespace.nspname = :schema_name
                                  AND relation.relname = :table_name
                                  AND NOT EXISTS (
                                      SELECT 1 FROM pg_depend AS extension_dependency
                                      WHERE extension_dependency.classid = 'pg_class'::regclass
                                        AND extension_dependency.objid = index_relation.oid
                                        AND extension_dependency.deptype = 'e'
                                  )
                                """,
                                """
                                SELECT CAST(:schema_name AS text) AS relation_schema,
                                       CAST(:table_name AS text) AS relation_name,
                                       index_relation.relname AS index_name,
                                       index_record.indisunique AS is_unique,
                                       index_record.indisprimary AS is_primary,
                                       index_record.indisvalid AS is_valid,
                                       index_record.indisready AS is_ready,
                                       pg_get_indexdef(index_record.indexrelid)
                                         AS index_definition
                                """,
                                'ORDER BY index_relation.relname COLLATE "C"',
                            ),
                            (
                                "policy",
                                """
                                FROM pg_policy AS descriptor
                                JOIN pg_class AS relation ON relation.oid = descriptor.polrelid
                                JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                                WHERE namespace.nspname = :schema_name
                                  AND relation.relname = :table_name
                                  AND NOT EXISTS (
                                      SELECT 1 FROM pg_depend AS extension_dependency
                                      WHERE extension_dependency.classid = 'pg_policy'::regclass
                                        AND extension_dependency.objid = descriptor.oid
                                        AND extension_dependency.deptype = 'e'
                                  )
                                """,
                                """
                                SELECT CAST(:schema_name AS text) AS relation_schema,
                                       CAST(:table_name AS text) AS relation_name,
                                       descriptor.polname AS policy_name,
                                       descriptor.polpermissive AS is_permissive,
                                       descriptor.polcmd::text AS policy_command,
                                       ARRAY(
                                           SELECT role.rolname
                                           FROM pg_roles AS role
                                           WHERE role.oid = ANY(descriptor.polroles)
                                           ORDER BY role.rolname COLLATE "C"
                                       )::text AS role_names,
                                       pg_get_expr(descriptor.polqual, descriptor.polrelid)
                                         AS using_expression,
                                       pg_get_expr(descriptor.polwithcheck, descriptor.polrelid)
                                         AS check_expression
                                """,
                                'ORDER BY descriptor.polname COLLATE "C"',
                            ),
                        )
                        for (
                            kind,
                            descriptor_from,
                            descriptor_select,
                            descriptor_order,
                        ) in descriptor_specs:
                            descriptor_remaining = PG_DESCRIPTOR_AGGREGATE_CAP - descriptor_count
                            observed = _project_pg_descriptor_query(
                                connection,
                                hasher,
                                kind=kind,
                                inner_query=f"SELECT 1 {descriptor_from}",
                                ordered_query=(
                                    f"{descriptor_select} {descriptor_from} {descriptor_order}"
                                ),
                                parameters=table_parameters,
                                cap=descriptor_remaining,
                                started_at=started_at,
                            )
                            descriptor_count += observed

                        row_count = _pg_census(
                            connection,
                            f"SELECT 1 FROM ONLY {quoted_schema}.{quoted_table}",
                            {},
                            cap=PROJECTION_ROWS_PER_TABLE_CAP,
                            started_at=started_at,
                        )
                        _require_pg_cap(
                            "PostgreSQL total rows",
                            total_rows + row_count,
                            PROJECTION_TOTAL_ROWS_CAP,
                        )
                        row_raw_query = f"""
                            SELECT
                                jsonb_build_array({cell_expressions}) AS row_cells,
                                GREATEST({scalar_octet_expressions})::bigint
                                  AS value_max_scalar_octets
                            FROM ONLY {quoted_schema}.{quoted_table} AS row_value
                        """
                        row_kind_literal = _quote_pg_literal("row")
                        table_identity_literal = _quote_pg_literal(table_identity)
                        row_projection = f"""
                            WITH raw_projection AS ({row_raw_query}),
                            payload_projection AS (
                                SELECT
                                    jsonb_build_array(
                                        {row_kind_literal},
                                        {table_identity_literal},
                                        raw_projection.row_cells
                                    )::text AS payload,
                                    GREATEST(
                                        octet_length(to_jsonb({row_kind_literal}::text)::text),
                                        octet_length(
                                            to_jsonb({table_identity_literal}::text)::text
                                        ),
                                        raw_projection.value_max_scalar_octets
                                    )::bigint AS max_scalar_octets
                                FROM raw_projection
                            )
                            SELECT payload, max_scalar_octets,
                                   (8 + octet_length(payload))::bigint
                                     AS framed_record_octets
                            FROM payload_projection
                        """
                        row_result, row_preflight = _pg_stream_projected_content(
                            connection,
                            row_projection,
                            {},
                            expected_count=row_count,
                            cap=PROJECTION_ROWS_PER_TABLE_CAP,
                            hasher=hasher,
                            started_at=started_at,
                        )
                        rows_observed = 0
                        while True:
                            _pg_remaining_statement_ms(started_at)
                            row_batch = row_result.fetchmany(row_preflight.fetch_batch)
                            if not row_batch:
                                break
                            for row in row_batch:
                                rows_observed += 1
                                if len(row) != 3:
                                    raise ValueError(
                                        "PostgreSQL row projection metadata is invalid"
                                    )
                                hasher.add_projected_payload(row[0], row[1], row[2])
                            _pg_remaining_statement_ms(started_at)
                        if rows_observed != row_count:
                            raise ValueError("PostgreSQL row census/content count mismatch")
                        total_rows += rows_observed
                        hasher.add_record(
                            (
                                b"table-counts",
                                _encode_pg_scalar(table_identity),
                                str(column_count).encode("ascii"),
                                str(row_count).encode("ascii"),
                            )
                        )
                    _pg_remaining_statement_ms(started_at)
                if tables_observed != table_count:
                    raise ValueError("PostgreSQL table census/content count mismatch")

                sequence_from = """
                    FROM pg_class AS sequence_relation
                    JOIN pg_namespace AS namespace
                      ON namespace.oid = sequence_relation.relnamespace
                    JOIN pg_sequence AS definition
                      ON definition.seqrelid = sequence_relation.oid
                    WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema')
                      AND namespace.nspname !~ '^pg_'
                      AND sequence_relation.relkind = 'S'
                      AND NOT EXISTS (
                          SELECT 1 FROM pg_depend AS extension_dependency
                          WHERE extension_dependency.classid = 'pg_class'::regclass
                            AND extension_dependency.objid = sequence_relation.oid
                            AND extension_dependency.deptype = 'e'
                      )
                """
                sequence_count = _pg_census(
                    connection,
                    f"SELECT 1 {sequence_from}",
                    {},
                    cap=PG_SEQUENCE_CAP,
                    started_at=started_at,
                )
                sequence_content_query = f"""
                    SELECT namespace.nspname AS sequence_schema,
                           sequence_relation.relname AS sequence_name,
                           format_type(definition.seqtypid, NULL) AS sequence_type,
                           definition.seqstart AS start_value,
                           definition.seqincrement AS increment_value,
                           definition.seqmax AS maximum_value,
                           definition.seqmin AS minimum_value,
                           definition.seqcycle AS cycles
                    {sequence_from}
                    ORDER BY namespace.nspname COLLATE "C",
                             sequence_relation.relname COLLATE "C"
                """
                sequence_projection = _pg_typed_payload_query(
                    "sequence-definition",
                    sequence_content_query,
                    passthrough_aliases=("sequence_schema", "sequence_name"),
                )
                sequence_result, sequence_preflight = _pg_stream_projected_content(
                    connection,
                    sequence_projection,
                    {},
                    expected_count=sequence_count,
                    cap=PG_SEQUENCE_CAP,
                    hasher=hasher,
                    started_at=started_at,
                )
                sequences_observed = 0
                while True:
                    _pg_remaining_statement_ms(started_at)
                    sequence_batch = sequence_result.fetchmany(sequence_preflight.fetch_batch)
                    if not sequence_batch:
                        break
                    for sequence_row in sequence_batch:
                        sequences_observed += 1
                        if len(sequence_row) != 5:
                            raise ValueError("PostgreSQL sequence payload metadata is invalid")
                        schema_name, sequence_name = sequence_row[3:5]
                        if not isinstance(schema_name, str) or not isinstance(sequence_name, str):
                            raise ValueError("PostgreSQL sequence identity is not bounded text")
                        quoted_schema = _quote_identifier(engine, schema_name)
                        quoted_sequence = _quote_identifier(engine, sequence_name)
                        runtime_query = (
                            f"SELECT last_value AS logical_last_value, "
                            f"is_called AS has_been_called, "
                            f"pg_typeof(last_value)::text AS last_value_type, "
                            f"pg_typeof(is_called)::text AS is_called_type "
                            f"FROM {quoted_schema}.{quoted_sequence} "
                            "WHERE pg_typeof(last_value)::text = 'bigint' "
                            "AND pg_typeof(is_called)::text = 'boolean'"
                        )
                        runtime_projection = _pg_typed_payload_query(
                            "sequence-runtime",
                            runtime_query,
                        )
                        runtime_result, runtime_preflight = _pg_stream_projected_content(
                            connection,
                            runtime_projection,
                            {},
                            expected_count=1,
                            cap=1,
                            hasher=hasher,
                            started_at=started_at,
                        )
                        runtime_batch = runtime_result.fetchmany(runtime_preflight.fetch_batch)
                        if len(runtime_batch) != 1 or len(runtime_batch[0]) != 3:
                            raise ValueError("PostgreSQL sequence runtime metadata is invalid")
                        hasher.add_projected_payload(
                            sequence_row[0], sequence_row[1], sequence_row[2]
                        )
                        hasher.add_projected_payload(
                            runtime_batch[0][0], runtime_batch[0][1], runtime_batch[0][2]
                        )
                    _pg_remaining_statement_ms(started_at)
                if sequences_observed != sequence_count:
                    raise ValueError("PostgreSQL sequence census/content count mismatch")

                extension_from = """
                    FROM pg_extension AS extension_record
                    JOIN pg_namespace AS namespace
                      ON namespace.oid = extension_record.extnamespace
                    WHERE namespace.nspname NOT IN ('pg_catalog', 'information_schema')
                      AND namespace.nspname !~ '^pg_'
                """
                extension_count = _pg_census(
                    connection,
                    f"SELECT 1 {extension_from}",
                    {},
                    cap=PG_EXTENSION_CAP,
                    started_at=started_at,
                )
                extension_content_query = f"""
                    SELECT extension_record.extname AS extension_name,
                           extension_record.extversion AS extension_version,
                           namespace.nspname AS extension_schema,
                           extension_record.extrelocatable AS is_relocatable
                    {extension_from}
                    ORDER BY extension_record.extname COLLATE "C"
                """
                extension_projection = _pg_typed_payload_query(
                    "extension",
                    extension_content_query,
                )
                extension_result, extension_preflight = _pg_stream_projected_content(
                    connection,
                    extension_projection,
                    {},
                    expected_count=extension_count,
                    cap=PG_EXTENSION_CAP,
                    hasher=hasher,
                    started_at=started_at,
                )
                extensions_observed = 0
                while True:
                    _pg_remaining_statement_ms(started_at)
                    extension_batch = extension_result.fetchmany(extension_preflight.fetch_batch)
                    if not extension_batch:
                        break
                    for extension_row in extension_batch:
                        extensions_observed += 1
                        if len(extension_row) != 3:
                            raise ValueError("PostgreSQL extension payload metadata is invalid")
                        hasher.add_projected_payload(
                            extension_row[0], extension_row[1], extension_row[2]
                        )
                    _pg_remaining_statement_ms(started_at)
                if extensions_observed != extension_count:
                    raise ValueError("PostgreSQL extension census/content count mismatch")

                hasher.add_record(
                    (
                        b"receipt-counts",
                        str(descriptor_count).encode("ascii"),
                        str(table_count).encode("ascii"),
                        str(total_rows).encode("ascii"),
                        str(sequence_count).encode("ascii"),
                        str(extension_count).encode("ascii"),
                    )
                )
                _pg_remaining_statement_ms(started_at)
                receipt = _PostgresMigrationProjectionReceipt(
                    projection_version=PG_PROJECTION_VERSION,
                    head=head,
                    descriptor_count=descriptor_count,
                    table_count=table_count,
                    row_count=total_rows,
                    sequence_count=sequence_count,
                    extension_count=extension_count,
                    caps=caps,
                    digest=hasher.hexdigest(),
                )
                transaction.rollback()
                return receipt
            finally:
                if transaction.is_active:
                    transaction.rollback()
    except SQLAlchemyError as exc:
        raise AssertionError(
            f"PostgreSQL resource-bounded migration-state projection failed: {type(exc).__name__}"
        ) from None


def _database_oid(connection: Connection, database_name: str) -> int | None:
    value = connection.scalar(
        text("SELECT oid FROM pg_database WHERE datname = :database_name"),
        {"database_name": database_name},
    )
    return int(value) if value is not None else None


def _raise_preserved_failures(
    primary_failure: BaseException | None,
    cleanup_failures: list[BaseException],
) -> None:
    failures = ([primary_failure] if primary_failure is not None else []) + cleanup_failures
    if not failures:
        return
    if len(failures) == 1:
        raise failures[0]
    raise BaseExceptionGroup("PostgreSQL migration proof and cleanup failures", failures)


@dataclass(frozen=True)
class _CreatedDatabaseReceipt:
    database_name: str
    oid: int


@dataclass(frozen=True)
class _PostgresMigrationProjectionReceipt:
    projection_version: str
    head: str
    descriptor_count: int
    table_count: int
    row_count: int
    sequence_count: int
    extension_count: int
    caps: tuple[tuple[str, int], ...]
    digest: str


@dataclass(frozen=True)
class _CompatDatabase:
    admin_engine: Engine
    owner_engine: Engine
    owner_role: str
    schema: str
    table: Table
    extension_version: str


def _seed_tenant_rows(database: _CompatDatabase) -> None:
    rows_by_tenant = {
        TENANT_ONE: [
            {
                "id": 1001,
                "user_id": TENANT_ONE,
                "content": "Tenant one closest",
                "source": "docs/tenant-one-closest.md",
                "embedding": [1.0, 0.0, 0.0],
            },
            {
                "id": 1002,
                "user_id": TENANT_ONE,
                "content": "Tenant one farther",
                "source": "docs/tenant-one-farther.md",
                "embedding": [0.8, 0.6, 0.0],
            },
        ],
        TENANT_TWO: [
            {
                "id": 2001,
                "user_id": TENANT_TWO,
                "content": "Tenant two private",
                "source": "docs/tenant-two-private.md",
                "embedding": [1.0, 0.0, 0.0],
            }
        ],
    }
    for tenant_id, rows in rows_by_tenant.items():
        with Session(database.owner_engine) as session:
            apply_user_rls_context(session, user_id=tenant_id)
            session.execute(insert(database.table), rows)
            session.commit()


@pytest.fixture(scope="module")
def pgvector_database() -> Iterator[_CompatDatabase]:
    """Create isolated objects owned by a genuine non-bypass PostgreSQL role."""

    database_url = os.getenv(PGVECTOR_COMPAT_DATABASE_URL, "").strip()
    required = os.getenv(PGVECTOR_COMPAT_REQUIRED, "").strip() == "1"
    if not database_url:
        _skip_or_fail_database(
            f"{PGVECTOR_COMPAT_DATABASE_URL} is not configured",
            required=required,
        )

    admin_engine: Engine | None = None
    try:
        parsed_url = make_url(database_url)
        if parsed_url.get_backend_name() != "postgresql":
            pytest.fail(f"{PGVECTOR_COMPAT_DATABASE_URL} must use PostgreSQL")
        admin_engine = create_engine(parsed_url, poolclass=NullPool)
        with admin_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        if admin_engine is not None:
            admin_engine.dispose()
        _skip_or_fail_database(
            f"pgvector compatibility database unavailable: {type(exc).__name__}",
            required=required,
        )

    assert admin_engine is not None
    token = uuid4().hex
    owner_role = f"pgvector_compat_owner_{token}"
    schema = f"pgvector_compat_{token}"
    quoted_owner = _quote_identifier(admin_engine, owner_role)
    quoted_schema = _quote_identifier(admin_engine, schema)
    role_created = False
    owner_engine: Engine | None = None

    try:
        with admin_engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            extension_version = connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = :extension"),
                {"extension": "vector"},
            )
            connection.exec_driver_sql(
                f"CREATE ROLE {quoted_owner} WITH LOGIN "
                f"PASSWORD '{OWNER_PASSWORD}' NOSUPERUSER NOBYPASSRLS"
            )
            role_created = True
            connection.exec_driver_sql(
                f"CREATE SCHEMA {quoted_schema} AUTHORIZATION {quoted_owner}"
            )

        owner_url = parsed_url.set(username=owner_role, password=OWNER_PASSWORD)
        owner_engine = create_engine(owner_url, poolclass=NullPool)
        qualified_table = f"{quoted_schema}.user_knowledge"
        with owner_engine.begin() as connection:
            connection.exec_driver_sql(f"""
                CREATE TABLE {qualified_table} (
                    id BIGINT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    embedding VECTOR(3) NOT NULL
                )
                """)
            connection.exec_driver_sql(f"ALTER TABLE {qualified_table} ENABLE ROW LEVEL SECURITY")
            connection.exec_driver_sql(f"ALTER TABLE {qualified_table} FORCE ROW LEVEL SECURITY")
            connection.exec_driver_sql(f"""
                CREATE POLICY user_knowledge_user_isolation
                ON {qualified_table}
                USING (
                    user_id =
                    NULLIF(current_setting('app.current_user_id', true), '')::bigint
                )
                WITH CHECK (
                    user_id =
                    NULLIF(current_setting('app.current_user_id', true), '')::bigint
                )
                """)

        metadata = MetaData()
        knowledge_table = Table(
            "user_knowledge",
            metadata,
            Column("id", BigInteger, primary_key=True),
            Column("user_id", BigInteger, nullable=False),
            Column("content", Text, nullable=False),
            Column("source", Text, nullable=False),
            Column("embedding", _vector_type(3), nullable=False),
            schema=schema,
        )
        database = _CompatDatabase(
            admin_engine=admin_engine,
            owner_engine=owner_engine,
            owner_role=owner_role,
            schema=schema,
            table=knowledge_table,
            extension_version=str(extension_version),
        )
        _seed_tenant_rows(database)
        yield database
    finally:
        if owner_engine is not None:
            owner_engine.dispose()
        if role_created:
            with admin_engine.begin() as connection:
                connection.exec_driver_sql(f"DROP SCHEMA IF EXISTS {quoted_schema} CASCADE")
                connection.exec_driver_sql(f"DROP OWNED BY {quoted_owner}")
                connection.exec_driver_sql(f"DROP ROLE IF EXISTS {quoted_owner}")
        admin_engine.dispose()


def _visible_sources(session: Session, table: Table) -> list[str]:
    statement = select(table.c.source).order_by(table.c.id)
    return list(session.scalars(statement))


def test_installed_pgvector_binding_is_exactly_0_5_0() -> None:
    try:
        installed_version = version("pgvector")
    except PackageNotFoundError:
        _skip_or_fail_binding("pgvector is unavailable in the ci-lite pre-commit environment")
    assert installed_version == EXPECTED_BINDING_VERSION


def test_source_and_lock_files_own_pgvector_and_test_numpy() -> None:
    input_files = (
        REPO_ROOT / "requirements-rag-vector.in",
        REPO_ROOT / "requirements-rag-vector-cpu.in",
        REPO_ROOT / "requirements-test.in",
    )
    lock_files = (
        REPO_ROOT / "requirements-rag-vector.txt",
        REPO_ROOT / "requirements-rag-vector-cpu.txt",
        REPO_ROOT / "requirements-test.txt",
    )

    for path in input_files[:2]:
        requirements = _active_requirements(path)
        assert "pgvector==0.5.0" in requirements, path
        assert not any(requirement.startswith("pgvector==0.4.") for requirement in requirements)

    test_requirements = _active_requirements(REPO_ROOT / "requirements-test.in")
    assert "pgvector~=0.5.0" in test_requirements
    assert "numpy~=2.4.6" in test_requirements
    for path in input_files[:2]:
        assert not any(
            requirement.startswith("numpy") for requirement in _active_requirements(path)
        )

    for path in lock_files:
        requirements = _active_requirements(path)
        assert "pgvector==0.5.0" in requirements, path
        assert "numpy==2.4.6" in requirements, path


def test_runtime_pgvector_imports_use_supported_modules() -> None:
    allowed_vector_import_found = False
    violations: list[str] = []
    for root_name in ("app", "core", "providers", "alembic"):
        for path in sorted((REPO_ROOT / root_name).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module == "pgvector.sqlalchemy":
                        if any(alias.name == "VECTOR" for alias in node.names):
                            allowed_vector_import_found = True
                        if any(
                            alias.name in {"HalfVector", "SparseVector"} for alias in node.names
                        ):
                            violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
                    if node.module == "pgvector" and any(
                        alias.name == "utils" for alias in node.names
                    ):
                        violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
                    if node.module is not None and node.module.startswith("pgvector.utils"):
                        violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
                elif isinstance(node, ast.Import):
                    if any(alias.name.startswith("pgvector.utils") for alias in node.names):
                        violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert allowed_vector_import_found
    assert not violations, f"Removed pgvector imports remain: {violations}"


def test_vector_type_accepts_list_bind_and_result_values() -> None:
    vector_type = _vector_type(3)
    bind_processor = vector_type.bind_processor(postgresql.dialect())
    result_processor = vector_type.result_processor(postgresql.dialect(), None)

    assert bind_processor is not None
    assert result_processor is not None
    encoded = bind_processor([1.0, 0.0, 0.0])
    assert json.loads(encoded) == [1.0, 0.0, 0.0]
    result = result_processor(encoded)
    assert isinstance(result, list)
    assert result == pytest.approx([1.0, 0.0, 0.0])


def test_ci_lite_missing_binding_uses_protocol_skip_and_other_lanes_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_pgvector(_: str) -> ModuleType:
        raise ModuleNotFoundError("No module named 'pgvector'", name="pgvector")

    monkeypatch.setenv("PRE_COMMIT", "1")
    with pytest.raises(
        pytest.skip.Exception,
        match="feature_disabled:pgvector_binding_ci_lite",
    ):
        _vector_type(3, module_loader=missing_pgvector)

    monkeypatch.delenv("PRE_COMMIT")
    with pytest.raises(pytest.fail.Exception, match="ci-lite pre-commit"):
        _vector_type(3, module_loader=missing_pgvector)


def test_ci_compatibility_proof_is_selected_and_merge_blocking() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    filter_contract = workflow.split("            pgvector_compat:", maxsplit=1)[1].splitlines()[0]
    merge_gate = workflow.split("  merge_readiness_gate:", maxsplit=1)[1].split(
        "  private_python_proxy_health:",
        maxsplit=1,
    )[0]
    security_job = workflow.split("  security:", maxsplit=1)[1].split(
        "  openapi-sync:",
        maxsplit=1,
    )[0]
    compat_job = workflow.split("\n  pgvector_compat:\n", maxsplit=1)[1].split(
        "  # Fast testing for feature branches",
        maxsplit=1,
    )[0]

    direct_proof_inputs = (
        ".github/workflows/ci.yml",
        "constraints.txt",
        "requirements-ci-lite.txt",
        "requirements-test.txt",
        "scripts/ci/emergency_python_wheels.json",
        "scripts/ci/install_locked_python_requirements.py",
        "alembic.ini",
        "alembic/env.py",
        "alembic/versions/**",
        "tests/test_pgvector_compat.py",
        "tests/test_pgvector_embedding_migration.py",
        "tests/test_vector_rag.py",
        "tests/test_db_rls.py",
    )
    assert all(f"'{path}'" in filter_contract for path in direct_proof_inputs)
    assert "'alembic/**'" not in filter_contract
    executable_proof_inputs = (
        "tests/test_pgvector_compat.py",
        "tests/test_pgvector_embedding_migration.py",
        "tests/test_vector_rag.py",
        "tests/test_db_rls.py",
    )
    assert all(path in compat_job for path in executable_proof_inputs)

    merge_gate_needs = merge_gate.split("needs:", maxsplit=1)[1].splitlines()[0]
    security_needs = security_job.split("needs:", maxsplit=1)[1].splitlines()[0]
    assert "security" in merge_gate_needs
    assert "pgvector_compat" not in merge_gate_needs
    assert "pgvector_compat" in security_needs
    assert "needs.changes.outputs.pgvector_compat == 'true'" in security_job
    assert "needs.pgvector_compat.result" in security_job
    assert '"true:success"|"false:skipped"' in security_job
    assert (
        "pgvector/pgvector:0.8.2-pg15-bookworm"
        "@sha256:bd12d6788a617f4147d5a2ae0b56d07921398adabfe5a033bd3f50c245df55a1" in compat_job
    )
    assert 'PGVECTOR_COMPAT_REQUIRED: "1"' in compat_job
    assert "scripts/ci/install_locked_python_requirements.py" in compat_job
    assert "--requirements-profile ci-test" in compat_job
    assert "--install-mode direct-proxy" in compat_job


def _ci_authority_environment(database_url: URL | None = None) -> dict[str, str]:
    selected_url = database_url or URL.create(
        "postgresql+psycopg",
        username="pgvector_compat",
        password="ephemeral-test-password",  # pragma: allowlist secret
        host="localhost",
        port=5432,
        database="pgvector_compat",
    )
    return {
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        PGVECTOR_COMPAT_DATABASE_URL: selected_url.render_as_string(hide_password=False),
        PGVECTOR_COMPAT_REQUIRED: "1",
    }


@pytest.mark.parametrize("query_key", ("host", "dbname", "port", "options", "arbitrary"))
def test_bounded_projection_authority_rejects_every_query_parameter(query_key: str) -> None:
    database_url = URL.create(
        "postgresql+psycopg",
        username="pgvector_compat",
        password="ephemeral-test-password",  # pragma: allowlist secret
        host="localhost",
        port=5432,
        database="pgvector_compat",
        query={query_key: "override"},
    )

    with pytest.raises(pytest.fail.Exception, match="must not include query parameters"):
        _required_ci_pgvector_url(_ci_authority_environment(database_url))


@pytest.mark.parametrize("marker", ("CI", "GITHUB_ACTIONS"))
def test_bounded_projection_authority_requires_exact_ci_markers(marker: str) -> None:
    environment = _ci_authority_environment()
    environment[marker] = "TRUE"

    with pytest.raises(pytest.fail.Exception, match=f"{marker} must equal true"):
        _required_ci_pgvector_url(environment)


@pytest.mark.parametrize("variable", FORBIDDEN_ALEMBIC_ENV_KEYS)
def test_pg_alembic_subprocess_environment_does_not_inherit_host_carriers(
    variable: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(variable, "sentinel-value")
    database_url = _required_ci_pgvector_url(_ci_authority_environment())

    env = _alembic_subprocess_env(database_url)

    assert variable not in env
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONHASHSEED"] == "0"
    assert env["APP_ENV"] == "test"
    assert env["ENVIRONMENT"] == "test"
    assert env["TESTING"] == "true"


def test_pg_alembic_failure_diagnostics_redact_url_and_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = URL.create(
        "postgresql+psycopg",
        username="pgvector_compat",
        password="decoded@password",  # pragma: allowlist secret
        host="localhost",
        port=5432,
        database="pulseplate_alembic_test",
    )
    credentialed_url = database_url.render_as_string(hide_password=False)
    captured_env: dict[str, str] = {}
    captured_command: list[str] = []

    def failed_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured_command.extend(command)
        raw_env = kwargs["env"]
        assert isinstance(raw_env, dict)
        captured_env.update({str(key): str(value) for key, value in raw_env.items()})
        return subprocess.CompletedProcess(
            command,
            9,
            stdout=credentialed_url,
            stderr="decoded@password decoded%40password",
        )

    monkeypatch.setattr(subprocess, "run", failed_run)

    with pytest.raises(pytest.fail.Exception) as failure:
        _run_alembic(database_url, "upgrade", "head")

    message = str(failure.value)
    assert captured_command[0] == sys.executable
    assert captured_env == _alembic_subprocess_env(database_url)
    assert credentialed_url not in message
    assert "decoded@password" not in message
    assert "decoded%40password" not in message
    assert "[REDACTED]" in message


@pytest.mark.parametrize("partial_kind", ("str", "bytes"))
def test_pg_alembic_timeout_diagnostics_normalize_and_redact_partial_output(
    partial_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = URL.create(
        "postgresql+psycopg",
        username="pgvector_compat",
        password="decoded@password",  # pragma: allowlist secret
        host="localhost",
        port=5432,
        database="pulseplate_alembic_timeout_test",
    )
    credentialed_url = database_url.render_as_string(hide_password=False)
    stdout_text = f"partial stdout {credentialed_url} decoded%40password"
    stderr_text = "partial stderr decoded@password"
    captured_command: list[str] = []

    def timed_out_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        captured_command.extend(command)
        stdout: str | bytes = stdout_text if partial_kind == "str" else stdout_text.encode()
        stderr: str | bytes = stderr_text if partial_kind == "str" else stderr_text.encode()
        raise subprocess.TimeoutExpired(
            command,
            180,
            output=stdout,
            stderr=stderr,
        )

    monkeypatch.setattr(subprocess, "run", timed_out_run)

    with pytest.raises(pytest.fail.Exception) as failure:
        _run_alembic(database_url, "upgrade", "head")

    message = str(failure.value)
    assert captured_command[0] == sys.executable
    assert "timed out after 180 seconds" in message
    assert credentialed_url not in message
    assert "decoded@password" not in message
    assert "decoded%40password" not in message
    assert "[REDACTED]" in message
    assert _normalize_timeout_partial_output(None) == ""
    assert _normalize_timeout_partial_output(object()) == "[unsupported-timeout-output:object]"


def test_database_failure_aggregation_preserves_primary_and_cleanup_errors() -> None:
    primary = AssertionError("primary migration failure")
    cleanup = RuntimeError("cleanup receipt failure")

    with pytest.raises(BaseExceptionGroup) as grouped:
        _raise_preserved_failures(primary, [cleanup])

    assert grouped.value.exceptions == (primary, cleanup)


def test_pg_synthetic_projection_is_content_identity_and_multiplicity_sensitive() -> None:
    base = _pg_synthetic_projection_digest((("public.sample", "alpha"),), record_cap=2)
    changed = _pg_synthetic_projection_digest((("public.sample", "beta"),), record_cap=2)
    rebound = _pg_synthetic_projection_digest((("public.other", "alpha"),), record_cap=2)
    duplicated = _pg_synthetic_projection_digest(
        (("public.sample", "alpha"), ("public.sample", "alpha")),
        record_cap=2,
    )

    assert len({base[0], changed[0], rebound[0], duplicated[0]}) == 4
    assert base[1] == changed[1] == rebound[1] == 1
    assert duplicated[1] == 2


def test_pg_sequence_projection_is_value_and_multiplicity_sensitive() -> None:
    base = _pg_synthetic_sequence_digest((("public", "sample_id_seq", 1, False),), sequence_cap=2)
    advanced = _pg_synthetic_sequence_digest(
        (("public", "sample_id_seq", 2, False),), sequence_cap=2
    )
    called = _pg_synthetic_sequence_digest((("public", "sample_id_seq", 1, True),), sequence_cap=2)
    duplicated = _pg_synthetic_sequence_digest(
        (
            ("public", "sample_id_seq", 1, False),
            ("public", "sample_id_seq", 1, False),
        ),
        sequence_cap=2,
    )

    assert len({base[0], advanced[0], called[0], duplicated[0]}) == 4
    assert base[1] == advanced[1] == called[1] == 1
    assert duplicated[1] == 2


@pytest.mark.parametrize(
    ("last_value", "is_called", "expected_type"),
    (
        (True, False, "bool"),
        (1.0, False, "float"),
        (1, 0, "int"),
    ),
)
def test_pg_projection_rejects_unsupported_scalar_types(
    last_value: object,
    is_called: object,
    expected_type: str,
) -> None:
    with pytest.raises(TypeError, match=expected_type):
        _pg_synthetic_sequence_digest(
            (("public", "sample_id_seq", last_value, is_called),),
            sequence_cap=1,
        )


def test_pg_extension_identity_is_projection_sensitive() -> None:
    base = _pg_synthetic_projection_digest((("vector", "0.8.2", "public", True),), record_cap=1)
    version_changed = _pg_synthetic_projection_digest(
        (("vector", "0.8.3", "public", True),), record_cap=1
    )
    schema_changed = _pg_synthetic_projection_digest(
        (("vector", "0.8.2", "extensions", True),), record_cap=1
    )
    relocatable_changed = _pg_synthetic_projection_digest(
        (("vector", "0.8.2", "public", False),), record_cap=1
    )
    assert len({base[0], version_changed[0], schema_changed[0], relocatable_changed[0]}) == 4


def test_pg_projection_caps_bytes_and_deadline_boundaries() -> None:
    _require_pg_cap("synthetic", 2, 2)
    with pytest.raises(ValueError, match="fixed resource bound"):
        _require_pg_cap("synthetic", 3, 2)
    with pytest.raises(ValueError, match="synthetic PostgreSQL records"):
        _pg_synthetic_projection_digest((("one",), ("two",)), record_cap=1)

    encoded = _encode_pg_scalar("x", cap=6)
    assert encoded == b"text:x"
    with pytest.raises(ValueError, match="encoded scalar bytes"):
        _encode_pg_scalar("x", cap=5)

    passing = _PostgresProjectionHasher(scalar_cap=1, record_cap=9, total_cap=17)
    passing.add_record((b"x",))
    assert passing.total_framed_bytes == 17
    with pytest.raises(ValueError, match="record bytes"):
        _PostgresProjectionHasher(scalar_cap=1, record_cap=8, total_cap=17).add_record((b"x",))
    with pytest.raises(ValueError, match="total framed bytes"):
        _PostgresProjectionHasher(scalar_cap=1, record_cap=9, total_cap=16).add_record((b"x",))

    row_hasher = _PostgresProjectionHasher(scalar_cap=8, record_cap=64, total_cap=128)
    row_hasher.add_projected_payload("[]", 1, 10)
    with pytest.raises(ValueError, match="framed-byte metadata mismatch"):
        row_hasher.add_projected_payload("[]", 1, 11)
    with pytest.raises(ValueError, match="maximum scalar bytes"):
        row_hasher.add_projected_payload("[]", 9, 10)

    payload = '["surface",{"field":1}]'
    framed_octets = len(payload.encode("utf-8")) + 8
    equality_hasher = _PostgresProjectionHasher(
        scalar_cap=64,
        record_cap=framed_octets,
        total_cap=framed_octets,
    )
    equality_preflight = _validate_pg_payload_preflight(
        (1, 8, framed_octets, framed_octets),
        expected_count=1,
        hasher=equality_hasher,
    )
    equality_hasher.add_projected_payload(payload, 8, framed_octets)
    assert equality_hasher.total_framed_bytes == equality_preflight.total_bytes

    assert _derive_pg_fetch_batch(1024, 4) == 256
    assert _derive_pg_fetch_batch(10, 3) == 3
    assert _derive_pg_fetch_batch(0, 8) == 1
    preflight_hasher = _PostgresProjectionHasher(scalar_cap=1, record_cap=1, total_cap=1)
    preflight = _validate_pg_payload_preflight(
        (1, 1, 1, 1),
        expected_count=1,
        hasher=preflight_hasher,
    )
    assert preflight.max_scalar_bytes == preflight.max_record_bytes == 1
    with pytest.raises(ValueError, match="preflight scalar bytes"):
        _validate_pg_payload_preflight(
            (1, 2, 1, 1),
            expected_count=1,
            hasher=preflight_hasher,
        )
    with pytest.raises(ValueError, match="preflight record bytes"):
        _validate_pg_payload_preflight(
            (1, 1, 2, 1),
            expected_count=1,
            hasher=preflight_hasher,
        )
    with pytest.raises(ValueError, match="preflight total bytes"):
        _validate_pg_payload_preflight(
            (1, 1, 1, 2),
            expected_count=1,
            hasher=preflight_hasher,
        )

    assert _pg_remaining_statement_ms(10.0, now=lambda: 10.0, deadline_seconds=30.0) == 30_000
    assert _pg_remaining_statement_ms(10.0, now=lambda: 39.998, deadline_seconds=30.0) == 2
    with pytest.raises(TimeoutError, match="deadline exceeded"):
        _pg_remaining_statement_ms(10.0, now=lambda: 40.0, deadline_seconds=30.0)


def test_pg_resource_bounded_projection_contract() -> None:
    assert (
        PROJECTION_TABLE_CAP,
        PROJECTION_COLUMN_CAP,
        PG_DESCRIPTOR_AGGREGATE_CAP,
        PG_SEQUENCE_CAP,
        PG_EXTENSION_CAP,
        PROJECTION_ROWS_PER_TABLE_CAP,
        PROJECTION_TOTAL_ROWS_CAP,
        PROJECTION_SCALAR_BYTES_CAP,
        PROJECTION_RECORD_BYTES_CAP,
        PROJECTION_TOTAL_FRAMED_BYTES_CAP,
        PROJECTION_FETCH_BATCH,
        PG_STATEMENT_TIMEOUT_MAX_MS,
        PROJECTION_DEADLINE_SECONDS,
    ) == (
        256,
        256,
        8192,
        256,
        32,
        10_000,
        100_000,
        1_048_576,
        4_194_304,
        67_108_864,
        256,
        30_000,
        120.0,
    )
    source = "\n".join(
        inspect.getsource(function)
        for function in (
            _pg_execute_bounded,
            _pg_typed_payload_query,
            _pg_projected_payload_preflight,
            _pg_stream_projected_content,
            _pg_census,
            _project_pg_descriptor_query,
            _project_postgres_migration_state,
        )
    )

    for required_fragment in (
        "relation.relrowsecurity",
        "relation.relforcerowsecurity",
        "relation.relkind IN ('r', 'p')",
        "pg_get_constraintdef(descriptor.oid, true)",
        "pg_get_indexdef(index_record.indexrelid)",
        "FROM pg_policy AS descriptor",
        "JOIN pg_sequence AS definition",
        "SELECT last_value AS logical_last_value",
        "is_called AS has_been_called",
        "quoted_sequence = _quote_identifier(engine, sequence_name)",
        "jsonb_build_array",
        "to_jsonb(row_value.",
        "FROM ONLY",
        "pg_depend AS extension_dependency",
        "extension_dependency.deptype = 'e'",
        "FROM pg_extension AS extension_record",
        "extension_record.extname",
        "extension_record.extversion",
        "extension_record.extrelocatable",
        'isolation_level="REPEATABLE READ"',
        "SET TRANSACTION READ ONLY",
        "SET LOCAL statement_timeout",
        "stream_results=True",
        "yield_per=stream_batch",
        "max_row_buffer=stream_batch",
        "jsonb_build_array({kind_literal}, to_jsonb(raw_projection))::text",
        "(8 + octet_length(payload))::bigint AS framed_record_octets",
        "_pg_projected_payload_preflight(",
        "_pg_stream_projected_content(",
        "stream_batch=",
        "MAX(max_scalar_octets)",
        "MAX(framed_record_octets)",
        "SUM(framed_record_octets)",
        "max_scalar_octets <=",
        "framed_record_octets <=",
        "fetchmany(PROJECTION_FETCH_BATCH)",
        "LIMIT {",
        'COLLATE "C"',
    ):
        assert required_fragment in source
    for forbidden_fragment in (
        "FROM pg_stat",
        "JOIN pg_stat",
        "reltuples",
        "relpages",
        "relfilenode",
        "SELECT oid",
        " AS relation_oid",
        " AS namespace_oid",
        " AS constraint_oid",
        " AS sequence_oid",
        "log_cnt",
        "page_lsn",
        "CURRENT_TIMESTAMP",
        "pg_trigger",
        "pg_proc",
        "information_schema.routines",
        "aclexplode",
        "os.environ",
        "getenv(",
        "relkind IN ('r', 'p', 'v'",
        ".all(",
        ".scalars",
        "tuple(",
        "list(",
        ".sort(",
        "sorted(",
    ):
        assert forbidden_fragment.lower() not in source.lower()
    assert ("cano" + "nical") not in source.lower()
    assert ("database" + "-state") not in source.lower()
    projector_source = inspect.getsource(_project_postgres_migration_state)
    assert "AS using_expression" in projector_source
    assert "AS check_expression" in projector_source
    assert projector_source.count("AS using_expression") == 1
    assert projector_source.count("AS check_expression") == 1
    for projection_name, streaming_name in (
        ("relation_projection =", "table_result, relation_preflight ="),
        ("column_projection =", "column_result, column_preflight ="),
        ("row_projection =", "row_result, row_preflight ="),
        ("sequence_projection =", "sequence_result, sequence_preflight ="),
        ("runtime_projection =", "runtime_result, runtime_preflight ="),
        ("extension_projection =", "extension_result, extension_preflight ="),
    ):
        assert projector_source.index(projection_name) < projector_source.index(streaming_name)
    for dynamic_fetch in (
        "fetchmany(relation_preflight.fetch_batch)",
        "fetchmany(column_preflight.fetch_batch)",
        "fetchmany(row_preflight.fetch_batch)",
        "fetchmany(sequence_preflight.fetch_batch)",
        "fetchmany(runtime_preflight.fetch_batch)",
        "fetchmany(extension_preflight.fetch_batch)",
    ):
        assert dynamic_fetch in projector_source


def test_bounded_projection_database_receipt_cleanup_contract_is_fail_closed() -> None:
    source = inspect.getsource(
        test_resource_bounded_alembic_graph_upgrades_dedicated_postgres_then_is_noop
    )

    absence_index = source.index("assert _database_oid(connection, database_name) is None")
    create_index = source.index('connection.exec_driver_sql(f"CREATE DATABASE {quoted_database}")')
    receipt_index = source.index("receipt = _CreatedDatabaseReceipt")
    oid_recheck_index = source.index("current_oid = _database_oid")
    drop_index = source.index('connection.exec_driver_sql(f"DROP DATABASE {quoted_database}")')
    absence_after_drop_index = source.index(
        "if _database_oid(connection, receipt.database_name) is not None"
    )

    assert absence_index < create_index < receipt_index < oid_recheck_index
    assert oid_recheck_index < drop_index < absence_after_drop_index
    assert "if receipt is not None and target_disposed" in source
    assert "DROP DATABASE IF EXISTS" not in source
    assert "FORCE" not in source
    assert "pg_terminate_backend" not in source


def test_resource_bounded_alembic_graph_upgrades_dedicated_postgres_then_is_noop() -> None:
    parsed_url = _required_ci_pgvector_url()
    admin_engine = create_engine(
        parsed_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    database_name = f"{ALEMBIC_DATABASE_PREFIX}{uuid4().hex}"
    assert re.fullmatch(r"pulseplate_alembic_[0-9a-f]{32}", database_name)
    quoted_database = _quote_identifier(admin_engine, database_name)
    receipt: _CreatedDatabaseReceipt | None = None
    target_engine: Engine | None = None
    primary_failure: BaseException | None = None
    cleanup_failures: list[BaseException] = []

    try:
        with admin_engine.connect() as connection:
            identity = connection.execute(text("""
                    SELECT
                        current_database() AS database_name,
                        current_user AS user_name,
                        inet_server_port() AS server_port
                    """)).one()
            assert identity.database_name == "pgvector_compat"
            assert identity.user_name == "pgvector_compat"
            assert identity.server_port == 5432
            assert _database_oid(connection, database_name) is None
            connection.exec_driver_sql(f"CREATE DATABASE {quoted_database}")
            created_oid = _database_oid(connection, database_name)
            if created_oid is None or created_oid <= 0:
                pytest.fail("Created database has no unambiguous positive OID receipt")
                raise AssertionError("pytest.fail returned unexpectedly")
            receipt = _CreatedDatabaseReceipt(database_name=database_name, oid=created_oid)

        target_url = parsed_url.set(database=database_name)
        target_engine = create_engine(target_url, poolclass=NullPool)
        _run_alembic(target_url, "upgrade", "head")

        scripts = ScriptDirectory.from_config(Config(str(REPO_ROOT / "alembic.ini")))
        heads = tuple(scripts.get_heads())
        assert len(heads) == 1
        assert heads[0]
        assert heads[0] == "202608290001"
        with target_engine.connect() as connection:
            _assert_exact_postfix_alembic_residual(connection)
            assert _drift_unique_object_inventory(connection) == (
                (
                    "analyzer_state",
                    "uq_analyzer_state_user_key",
                    True,
                    "uq_analyzer_state_user_key",
                    ("user_id", "analyzer_key"),
                ),
                (
                    "day_plans",
                    "uq_day_plans_user_date",
                    True,
                    "uq_day_plans_user_date",
                    ("user_id", "date"),
                ),
            )

        from app.models import UserKnowledge

        vector_values = [float(index) / 768 for index in range(768)]
        vector_payload = json.dumps(vector_values, separators=(",", ":"))
        with target_engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.current_user_id', '900001', true)"))
            connection.execute(
                insert(UserKnowledge.__table__),
                {
                    "id": 900001,
                    "user_id": 900001,
                    "content": "drift vector binding proof",
                    "embedding": vector_payload,
                    "source": "drift-proof",
                },
            )
            stored_embedding = connection.scalar(
                select(UserKnowledge.__table__.c.embedding).where(
                    UserKnowledge.__table__.c.id == 900001
                )
            )
            assert isinstance(stored_embedding, str)
            assert json.loads(stored_embedding) == pytest.approx(vector_values)
        first_projection = _project_postgres_migration_state(target_engine)
        assert first_projection.head == heads[0]

        _run_alembic(target_url, "current", "--check-heads")
        _run_alembic(target_url, "upgrade", "head")
        assert _project_postgres_migration_state(target_engine) == first_projection

        with target_engine.begin() as connection:
            connection.execute(text("""
                    INSERT INTO users (id, email, name)
                    VALUES (900001, 'drift-proof@example.test', 'Drift Proof')
                    """))
            connection.execute(text("""
                    INSERT INTO weekly_plans (
                        id, user_id, start_date, end_date, plan_data
                    ) VALUES (
                        900001, 900001, DATE '2026-08-24', DATE '2026-08-30', '{}'::json
                    )
                    """))
            connection.execute(text("""
                    INSERT INTO day_plans (
                        id, user_id, weekly_plan_id, date, plan_data
                    ) VALUES (
                        900001, 900001, 900001, DATE '2026-08-24', '{}'::json
                    )
                    """))
            connection.execute(text("""
                    INSERT INTO analyzer_state (
                        id, user_id, analyzer_key, payload
                    ) VALUES (
                        900001, 900001, 'drift-proof', '{}'::jsonb
                    )
                    """))

        seeded_head_projection = _project_postgres_migration_state(target_engine)
        _run_alembic(target_url, "downgrade", PRE_DRIFT_RECONCILIATION_HEAD)
        with target_engine.begin() as connection:
            assert _drift_unique_object_inventory(connection) == (
                (
                    "analyzer_state",
                    "uq_analyzer_state_user_key",
                    True,
                    None,
                    ("user_id", "analyzer_key"),
                ),
                (
                    "day_plans",
                    "ix_day_plans_user_date",
                    True,
                    None,
                    ("user_id", "date"),
                ),
            )
            analyzer_row = connection.execute(
                text("SELECT user_id, analyzer_key FROM analyzer_state WHERE id = 900001")
            ).one()
            day_row = connection.execute(
                text("SELECT user_id, weekly_plan_id, date FROM day_plans WHERE id = 900001")
            ).one()
            assert tuple(analyzer_row) == (900001, "drift-proof")
            assert tuple(day_row) == (900001, 900001, date(2026, 8, 24))

            connection.exec_driver_sql("CREATE SCHEMA hostile")
            connection.exec_driver_sql(
                "CREATE TABLE hostile.analyzer_state (user_id integer, analyzer_key text)"
            )
            connection.exec_driver_sql(
                "CREATE INDEX uq_analyzer_state_user_key "
                "ON hostile.analyzer_state (analyzer_key)"
            )
            connection.exec_driver_sql("SET LOCAL search_path TO hostile, public, pg_catalog")

            drift_revision = scripts.get_revision("202608290001")
            assert drift_revision is not None
            revision_module = drift_revision.module
            expected_index = getattr(revision_module, "_EXPECTED_INDEXES")[0]
            descriptor = getattr(revision_module, "_load_index_descriptor")(
                connection,
                expected_index,
            )
            getattr(revision_module, "_require_adoptable_index")(
                descriptor,
                expected_index,
            )
            assert descriptor.table_schema == "public"
            assert descriptor.key_columns == ("user_id", "analyzer_key")
            wrong_descriptor = descriptor._replace(key_columns=("analyzer_key", "user_id"))
            with pytest.raises(
                RuntimeError,
                match="index_admission_failed:uq_analyzer_state_user_key:key_columns",
            ):
                getattr(revision_module, "_require_adoptable_index")(
                    wrong_descriptor,
                    expected_index,
                )
            connection.exec_driver_sql("DROP SCHEMA hostile CASCADE")

        _run_alembic(target_url, "upgrade", "head")
        with target_engine.connect() as connection:
            _assert_exact_postfix_alembic_residual(connection)
            assert _drift_unique_object_inventory(connection) == (
                (
                    "analyzer_state",
                    "uq_analyzer_state_user_key",
                    True,
                    "uq_analyzer_state_user_key",
                    ("user_id", "analyzer_key"),
                ),
                (
                    "day_plans",
                    "uq_day_plans_user_date",
                    True,
                    "uq_day_plans_user_date",
                    ("user_id", "date"),
                ),
            )
        assert _project_postgres_migration_state(target_engine) == seeded_head_projection
    except BaseException as exc:
        primary_failure = exc
    finally:
        target_disposed = True
        if target_engine is not None:
            try:
                target_engine.dispose()
            except BaseException as exc:
                target_disposed = False
                cleanup_failures.append(exc)
        try:
            if receipt is not None and target_disposed:
                with admin_engine.connect() as connection:
                    current_oid = _database_oid(connection, receipt.database_name)
                    if current_oid != receipt.oid:
                        raise AssertionError(
                            "Created database cleanup receipt no longer matches the server OID"
                        )
                    connection.exec_driver_sql(f"DROP DATABASE {quoted_database}")
                    if _database_oid(connection, receipt.database_name) is not None:
                        raise AssertionError("Created database remains present after exact DROP")
            elif receipt is not None:
                cleanup_failures.append(
                    RuntimeError(
                        "Exact database cleanup was withheld because target disposal was not proven"
                    )
                )
        except BaseException as exc:
            cleanup_failures.append(exc)
        finally:
            try:
                admin_engine.dispose()
            except BaseException as exc:
                cleanup_failures.append(exc)

    _raise_preserved_failures(primary_failure, cleanup_failures)


def test_fitchef_outcome_fresh_migration_forces_exact_rls_and_real_role_isolation() -> None:
    """Prove the migrated outcome table under a real non-bypass PostgreSQL role."""

    parsed_url = _required_ci_pgvector_url()
    admin_engine = create_engine(
        parsed_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    token = uuid4().hex
    database_name = f"{ALEMBIC_DATABASE_PREFIX}{token}"
    role_name = f"fitchef_outcome_rls_{token}"
    assert re.fullmatch(r"pulseplate_alembic_[0-9a-f]{32}", database_name)
    assert re.fullmatch(r"fitchef_outcome_rls_[0-9a-f]{32}", role_name)
    quoted_database = _quote_identifier(admin_engine, database_name)
    quoted_role = _quote_identifier(admin_engine, role_name)
    receipt: _CreatedDatabaseReceipt | None = None
    target_engine: Engine | None = None
    role_engine: Engine | None = None
    role_created = False
    primary_failure: BaseException | None = None
    cleanup_failures: list[BaseException] = []

    try:
        with admin_engine.connect() as connection:
            assert _database_oid(connection, database_name) is None
            connection.exec_driver_sql(f"CREATE DATABASE {quoted_database}")
            created_oid = _database_oid(connection, database_name)
            if created_oid is None or created_oid <= 0:
                pytest.fail("FitChef outcome test database has no positive OID receipt")
                raise AssertionError("pytest.fail returned unexpectedly")
            receipt = _CreatedDatabaseReceipt(database_name=database_name, oid=created_oid)
            connection.exec_driver_sql(
                f"CREATE ROLE {quoted_role} WITH LOGIN "
                f"PASSWORD '{OWNER_PASSWORD}' NOSUPERUSER NOBYPASSRLS"
            )
            role_created = True

        target_url = parsed_url.set(database=database_name)
        target_engine = create_engine(target_url, poolclass=NullPool)
        _run_alembic(target_url, "upgrade", "head")

        with target_engine.begin() as connection:
            connection.exec_driver_sql(
                f"GRANT SELECT, INSERT ON TABLE " f"fitchef_support_outcome_events TO {quoted_role}"
            )
            relation = connection.execute(text("""
                    SELECT relrowsecurity, relforcerowsecurity
                    FROM pg_class
                    WHERE oid = 'fitchef_support_outcome_events'::regclass
                    """)).one()
            policies = connection.execute(text("""
                    SELECT
                        policy.polname,
                        policy.polpermissive,
                        policy.polcmd::text AS command,
                        policy.polroles::text AS roles,
                        pg_get_expr(policy.polqual, policy.polrelid) AS using_expression,
                        pg_get_expr(policy.polwithcheck, policy.polrelid) AS check_expression
                    FROM pg_policy AS policy
                    WHERE policy.polrelid = 'fitchef_support_outcome_events'::regclass
                    ORDER BY policy.polname COLLATE "C"
                    """)).all()
            role_flags = connection.execute(
                text("""
                    SELECT rolsuper, rolbypassrls
                    FROM pg_roles
                    WHERE rolname = :role_name
                    """),
                {"role_name": role_name},
            ).one()

        expected_expression = (
            "(subject_id = (NULLIF(current_setting('app.current_user_id'::text, true), "
            "''::text))::bigint)"
        )
        assert relation.relrowsecurity is True
        assert relation.relforcerowsecurity is True
        assert role_flags.rolsuper is False
        assert role_flags.rolbypassrls is False
        assert len(policies) == 1
        policy = policies[0]
        assert policy.polname == "fitchef_support_outcome_subject_isolation"
        assert policy.polpermissive is True
        assert policy.command == "*"
        assert policy.roles == "{0}"
        assert policy.using_expression == expected_expression
        assert policy.check_expression == expected_expression

        metadata = MetaData()
        outcome_table = Table(
            "fitchef_support_outcome_events",
            metadata,
            autoload_with=target_engine,
        )
        role_url = target_url.set(username=role_name, password=OWNER_PASSWORD)
        role_engine = create_engine(role_url, poolclass=NullPool)

        def row(
            *,
            row_id: str,
            subject_id: int,
            support_need: str,
            target_surface: str,
            outcome: str,
            client_event_id: str,
        ) -> dict[str, object]:
            return {
                "id": row_id,
                "subject_id": subject_id,
                "schema_version": "fitchef_support_outcome_v1",
                "support_need": support_need,
                "target_surface": target_surface,
                "outcome": outcome,
                "client_event_id": client_event_id,
            }

        with Session(role_engine) as missing_context:
            assert missing_context.scalar(select(func.count()).select_from(outcome_table)) == 0

        with Session(role_engine) as session:
            apply_user_rls_context(session, user_id=TENANT_ONE)
            session.execute(
                insert(outcome_table),
                row(
                    row_id="tenant-one-first",
                    subject_id=TENANT_ONE,
                    support_need="daily_structure",
                    target_surface="pro_daily_plate",
                    outcome="acknowledged",
                    client_event_id="tenant-one-event-0001",
                ),
            )
            session.commit()

        with Session(role_engine) as session:
            apply_user_rls_context(session, user_id=TENANT_TWO)
            session.execute(
                insert(outcome_table),
                row(
                    row_id="tenant-two-first",
                    subject_id=TENANT_TWO,
                    support_need="weekly_structure",
                    target_surface="pro_weekly_plan",
                    outcome="dismissed",
                    client_event_id="tenant-two-event-0001",
                ),
            )
            session.commit()

        with Session(role_engine) as first_session:
            apply_user_rls_context(first_session, user_id=TENANT_ONE)
            assert list(first_session.scalars(select(outcome_table.c.id))) == ["tenant-one-first"]

            with pytest.raises(DBAPIError):
                first_session.execute(
                    insert(outcome_table),
                    row(
                        row_id="tenant-mismatch",
                        subject_id=TENANT_TWO,
                        support_need="weekly_structure",
                        target_surface="pro_weekly_plan",
                        outcome="acknowledged",
                        client_event_id="tenant-mismatch-0001",
                    ),
                )
            first_session.rollback()
            apply_user_rls_context(first_session, user_id=TENANT_ONE)
            assert list(first_session.scalars(select(outcome_table.c.id))) == ["tenant-one-first"]

        with Session(role_engine) as second_session:
            apply_user_rls_context(second_session, user_id=TENANT_TWO)
            assert list(second_session.scalars(select(outcome_table.c.id))) == ["tenant-two-first"]
    except BaseException as exc:
        primary_failure = exc
    finally:
        if role_engine is not None:
            try:
                role_engine.dispose()
            except BaseException as exc:
                cleanup_failures.append(exc)
        target_disposed = True
        if target_engine is not None:
            try:
                target_engine.dispose()
            except BaseException as exc:
                target_disposed = False
                cleanup_failures.append(exc)
        try:
            if receipt is not None and target_disposed:
                with admin_engine.connect() as connection:
                    current_oid = _database_oid(connection, receipt.database_name)
                    if current_oid != receipt.oid:
                        raise AssertionError(
                            "FitChef outcome database cleanup receipt no longer matches OID"
                        )
                    connection.exec_driver_sql(f"DROP DATABASE {quoted_database}")
                    if role_created:
                        connection.exec_driver_sql(f"DROP ROLE {quoted_role}")
                        role_created = False
                    if _database_oid(connection, receipt.database_name) is not None:
                        raise AssertionError("FitChef outcome test database remains after DROP")
            elif receipt is not None:
                cleanup_failures.append(
                    RuntimeError(
                        "FitChef outcome database cleanup withheld because disposal was unproven"
                    )
                )
        except BaseException as exc:
            cleanup_failures.append(exc)
        finally:
            try:
                if role_created:
                    with admin_engine.connect() as connection:
                        connection.exec_driver_sql(f"DROP ROLE {quoted_role}")
            except BaseException as exc:
                cleanup_failures.append(exc)
            try:
                admin_engine.dispose()
            except BaseException as exc:
                cleanup_failures.append(exc)

    _raise_preserved_failures(primary_failure, cleanup_failures)


def test_database_uses_exact_extension_and_non_bypass_table_owner(
    pgvector_database: _CompatDatabase,
) -> None:
    database = pgvector_database
    assert database.extension_version == EXPECTED_EXTENSION_VERSION

    with database.admin_engine.connect() as connection:
        role_flags = connection.execute(
            text("""
                SELECT rolsuper, rolbypassrls
                FROM pg_roles
                WHERE rolname = :role_name
                """),
            {"role_name": database.owner_role},
        ).one()
        table_contract = connection.execute(
            text("""
                SELECT owner.rolname, relation.relrowsecurity, relation.relforcerowsecurity
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                JOIN pg_roles AS owner
                  ON owner.oid = relation.relowner
                WHERE namespace.nspname = :schema
                  AND relation.relname = :table_name
                """),
            {"schema": database.schema, "table_name": "user_knowledge"},
        ).one()

    assert role_flags.rolsuper is False
    assert role_flags.rolbypassrls is False
    assert table_contract.rolname == database.owner_role
    assert table_contract.relrowsecurity is True
    assert table_contract.relforcerowsecurity is True


def test_real_vector_list_round_trip_and_cosine_distance_order(
    pgvector_database: _CompatDatabase,
) -> None:
    database = pgvector_database
    query_vector = bindparam("query_vector", type_=_vector_type(3))
    distance = database.table.c.embedding.cosine_distance(query_vector).label("distance")
    statement = select(
        database.table.c.id,
        database.table.c.embedding,
        distance,
    ).order_by(distance)
    assert "<=>" in str(statement)

    with Session(database.owner_engine) as session:
        apply_user_rls_context(session, user_id=TENANT_ONE)
        rows = session.execute(
            statement,
            {"query_vector": [1.0, 0.0, 0.0]},
        ).all()

    assert [row.id for row in rows] == [1001, 1002]
    assert list(rows[0].embedding) == pytest.approx([1.0, 0.0, 0.0])
    assert rows[0].distance == pytest.approx(0.0)
    assert rows[1].distance == pytest.approx(0.2)


def test_invalid_vector_dimension_fails_and_session_recovers_after_rollback(
    pgvector_database: _CompatDatabase,
) -> None:
    database = pgvector_database
    quoted_schema = _quote_identifier(database.owner_engine, database.schema)
    invalid_insert = text(f"""
        INSERT INTO {quoted_schema}.user_knowledge (
            id, user_id, content, source, embedding
        )
        VALUES (
            :id, :user_id, :content, :source, CAST(:embedding AS VECTOR(3))
        )
        """)
    with Session(database.owner_engine) as session:
        apply_user_rls_context(session, user_id=TENANT_ONE)
        before = session.scalar(select(func.count()).select_from(database.table))

        with pytest.raises(DBAPIError):
            session.execute(
                invalid_insert,
                {
                    "id": 1099,
                    "user_id": TENANT_ONE,
                    "content": "Invalid dimension",
                    "source": "docs/invalid-dimension.md",
                    "embedding": "[1.0,0.0]",
                },
            )
        session.rollback()

        apply_user_rls_context(session, user_id=TENANT_ONE)
        after = session.scalar(select(func.count()).select_from(database.table))

    assert before == 2
    assert after == before


def test_force_rls_hides_rows_without_context_and_isolates_tenants(
    pgvector_database: _CompatDatabase,
) -> None:
    database = pgvector_database
    with Session(database.owner_engine) as missing_context_session:
        assert _visible_sources(missing_context_session, database.table) == []

    with database.owner_engine.connect() as first_connection:
        with database.owner_engine.connect() as second_connection:
            with Session(bind=first_connection) as first_session:
                with Session(bind=second_connection) as second_session:
                    apply_user_rls_context(first_session, user_id=TENANT_ONE)
                    apply_user_rls_context(second_session, user_id=TENANT_TWO)
                    first_pid = first_session.scalar(text("SELECT pg_backend_pid()"))
                    second_pid = second_session.scalar(text("SELECT pg_backend_pid()"))
                    first_sources = _visible_sources(first_session, database.table)
                    second_sources = _visible_sources(second_session, database.table)

    assert first_pid != second_pid
    assert first_sources == [
        "docs/tenant-one-closest.md",
        "docs/tenant-one-farther.md",
    ]
    assert second_sources == ["docs/tenant-two-private.md"]


def test_rls_context_is_transaction_local_and_does_not_leak(
    pgvector_database: _CompatDatabase,
) -> None:
    database = pgvector_database
    with database.owner_engine.connect() as connection:
        with Session(bind=connection) as session:
            apply_user_rls_context(session, user_id=TENANT_ONE)
            assert len(_visible_sources(session, database.table)) == 2
            session.commit()
            assert _visible_sources(session, database.table) == []


def test_real_postgres_advisory_lease_contends_then_releases(
    pgvector_database: _CompatDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import db as core_db
    from core.food_apis.scheduler_runtime import (
        SchedulerMode,
        UpdateLeaseContended,
        run_with_update_lease,
    )

    database = pgvector_database
    session_factory = sessionmaker(bind=database.owner_engine)
    events: list[str] = []

    async def scenario() -> None:
        async def competing_operation() -> None:
            events.append("competing-body")

        async def owning_operation() -> str:
            events.append("owning-body")
            with pytest.raises(UpdateLeaseContended):
                await run_with_update_lease(
                    competing_operation,
                    mode=SchedulerMode.EXTERNAL,
                    session_factory=session_factory,
                )
            events.append("contention-observed")
            return "owned"

        assert (
            await run_with_update_lease(
                owning_operation,
                mode=SchedulerMode.EXTERNAL,
                session_factory=session_factory,
            )
            == "owned"
        )
        await run_with_update_lease(
            competing_operation,
            mode=SchedulerMode.EXTERNAL,
            session_factory=session_factory,
        )

    baseline_database_url = os.environ["DATABASE_URL"]
    core_db.reset_db_for_tests()
    try:
        with monkeypatch.context() as database_env:
            database_env.setenv(
                "DATABASE_URL",
                database.owner_engine.url.render_as_string(hide_password=False),
            )
            database_env.setenv("FOOD_UPDATE_SCHEDULER_MODE", "external")
            asyncio.run(scenario())
    finally:
        core_db.reset_db_for_tests()
        core_db.init_db(baseline_database_url)

    assert events == [
        "owning-body",
        "contention-observed",
        "competing-body",
    ]


def test_production_vector_retrieval_uses_postgres_and_real_rls(
    pgvector_database: _CompatDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import db as core_db
    from core.rag import vector_rag

    database = pgvector_database
    quoted_schema = _quote_identifier(database.owner_engine, database.schema)

    class _StaticEmbeddingProvider:
        def encode(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["compatibility query"]
            return [[1.0, 0.0, 0.0]]

    @contextmanager
    def _compat_session_scope() -> Iterator[Session]:
        with database.owner_engine.connect() as connection:
            with Session(bind=connection) as session:
                session.execute(text(f"SET LOCAL search_path TO {quoted_schema}, public"))
                yield session

    monkeypatch.setattr(vector_rag, "_embedding_provider", _StaticEmbeddingProvider())
    monkeypatch.setattr(vector_rag, "EMBEDDING_DIMENSIONS", 3)
    monkeypatch.setattr(core_db, "session_scope", _compat_session_scope)

    context = vector_rag._retrieve_vector_from_db(
        "compatibility query",
        max_chunks=1,
        agent_id=None,
        user_tier="PRO",
        subject_id=TENANT_ONE,
    )

    assert len(context.chunks) == 1
    chunk = context.chunks[0]
    assert chunk.content == "Tenant one closest"
    assert chunk.file == "docs/tenant-one-closest.md"
    assert chunk.score == pytest.approx(1.0)
    assert "embedding" not in vars(chunk)

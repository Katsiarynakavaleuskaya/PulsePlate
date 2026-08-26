"""Deterministic regression proof for Alembic package and migration-tree ownership."""

from __future__ import annotations

import ast
import configparser
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
import inspect
from itertools import chain
import json
import math
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
CONTROLLED_CHILD_ENV = {
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
FORBIDDEN_CHILD_ENV_KEYS = (
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


SQLITE_PROJECTION_VERSION = "pulseplate.sqlite-resource-bounded-migration-state.v1"
PROJECTION_TABLE_CAP = 256
PROJECTION_COLUMN_CAP = 256
SQLITE_SCHEMA_RECORD_CAP = 2048
PROJECTION_ROWS_PER_TABLE_CAP = 10_000
PROJECTION_TOTAL_ROWS_CAP = 100_000
PROJECTION_SCALAR_BYTES_CAP = 1 * 1024 * 1024
PROJECTION_RECORD_BYTES_CAP = 4 * 1024 * 1024
PROJECTION_TOTAL_FRAMED_BYTES_CAP = 64 * 1024 * 1024
PROJECTION_FETCH_BATCH = 256
PROJECTION_DEADLINE_SECONDS = 120.0
SQLITE_PROGRESS_OPCODES = 1000


@dataclass(frozen=True)
class _SqliteMigrationProjectionReceipt:
    projection_version: str
    head: str
    schema_record_count: int
    table_count: int
    column_count: int
    row_count: int
    caps: tuple[tuple[str, int], ...]
    digest: str


def _tail(value: str, *, limit: int = 4000) -> str:
    return value[-limit:]


def _database_url_redactions(env: dict[str, str]) -> tuple[str, ...]:
    database_url = env.get("DATABASE_URL", "")
    if not database_url:
        return ()
    parsed = urlsplit(database_url)
    encoded_password = parsed.password or ""
    decoded_password = unquote(encoded_password)
    return tuple(
        value
        for value in dict.fromkeys((database_url, encoded_password, decoded_password))
        if value
    )


def _redact_output(value: str, redactions: tuple[str, ...]) -> str:
    sanitized = value
    for redaction in sorted(redactions, key=len, reverse=True):
        sanitized = sanitized.replace(redaction, "[REDACTED]")
    return sanitized


def _run_python(
    arguments: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        redactions = _database_url_redactions(env)
        pytest.fail(
            "Child Python command failed "
            f"(rc={completed.returncode})\n"
            f"stdout tail:\n{_tail(_redact_output(completed.stdout, redactions))}\n"
            f"stderr tail:\n{_tail(_redact_output(completed.stderr, redactions))}"
        )
    return completed


def _controlled_env(*, pythonpath: str | None) -> dict[str, str]:
    env = dict(CONTROLLED_CHILD_ENV)
    if pythonpath is not None:
        env["PYTHONPATH"] = pythonpath
    return env


def _script_heads() -> tuple[str, ...]:
    scripts = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    return tuple(scripts.get_heads())


def _frame_bytes(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, byteorder="big", signed=False) + payload


def _require_projection_cap(label: str, observed: int, cap: int) -> None:
    if observed > cap:
        raise ValueError(f"{label} exceeds fixed resource bound: observed={observed}, cap={cap}")


def _require_projection_deadline(
    started_at: float,
    *,
    now: Callable[[], float] = time.monotonic,
    deadline_seconds: float = PROJECTION_DEADLINE_SECONDS,
) -> None:
    if now() - started_at > deadline_seconds:
        raise TimeoutError("Resource-bounded migration-state projection deadline exceeded")


def _encode_sqlite_value(
    value: object,
    *,
    scalar_cap: int = PROJECTION_SCALAR_BYTES_CAP,
) -> bytes:
    if value is None:
        encoded = b"null:"
    elif isinstance(value, bool):
        raise ValueError("SQLite boolean value is outside the admitted projection")
    elif isinstance(value, int):
        encoded = b"int:" + str(value).encode("ascii")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("SQLite non-finite real is outside the admitted projection")
        encoded = b"float:" + value.hex().encode("ascii")
    elif isinstance(value, str):
        encoded = b"text:" + value.encode("utf-8")
    elif isinstance(value, bytes):
        encoded = b"bytes:" + value
    else:
        raise TypeError(f"Unsupported SQLite projection value type: {type(value).__name__}")
    _require_projection_cap("SQLite encoded scalar bytes", len(encoded), scalar_cap)
    return encoded


@dataclass
class _SqliteProjectionHasher:
    scalar_cap: int = PROJECTION_SCALAR_BYTES_CAP
    record_cap: int = PROJECTION_RECORD_BYTES_CAP
    total_cap: int = PROJECTION_TOTAL_FRAMED_BYTES_CAP
    total_framed_bytes: int = 0
    _hasher: Any = field(default_factory=sha256, init=False, repr=False)

    def add_record(self, parts: Iterable[bytes]) -> None:
        record = bytearray()
        for part in parts:
            _require_projection_cap("SQLite encoded scalar bytes", len(part), self.scalar_cap)
            record.extend(_frame_bytes(part))
            _require_projection_cap("SQLite encoded record bytes", len(record), self.record_cap)
        framed = _frame_bytes(bytes(record))
        _require_projection_cap(
            "SQLite total framed bytes",
            self.total_framed_bytes + len(framed),
            self.total_cap,
        )
        self._hasher.update(framed)
        self.total_framed_bytes += len(framed)

    def hexdigest(self) -> str:
        return self._hasher.hexdigest()

    def remaining_bytes(self) -> int:
        return self.total_cap - self.total_framed_bytes


@dataclass(frozen=True)
class _SqlitePayloadPreflight:
    count: int
    max_scalar_bytes: int
    max_record_bytes: int
    total_bytes: int
    fetch_batch: int


def _derive_projection_fetch_batch(total_remaining: int, max_record_bytes: int) -> int:
    return max(
        1,
        min(
            PROJECTION_FETCH_BATCH,
            total_remaining // max(1, max_record_bytes),
        ),
    )


def _sqlite_encoded_length_sql(expression: str) -> str:
    return f"""
        CASE typeof({expression})
            WHEN 'null' THEN 5
            WHEN 'integer' THEN 4 + length(CAST({expression} AS TEXT))
            WHEN 'real' THEN 32
            WHEN 'text' THEN 5 + length(CAST({expression} AS BLOB))
            WHEN 'blob' THEN 6 + length({expression})
            ELSE {PROJECTION_SCALAR_BYTES_CAP + 1}
        END
    """


def _sqlite_payload_preflight(
    connection: sqlite3.Connection,
    metadata_query: str,
    parameters: Sequence[object],
    *,
    expected_count: int,
    hasher: _SqliteProjectionHasher,
    started_at: float,
    record_overhead: int = 0,
) -> _SqlitePayloadPreflight:
    _require_projection_deadline(started_at)
    cursor = connection.execute(metadata_query, parameters)
    batch = cursor.fetchmany(PROJECTION_FETCH_BATCH)
    if len(batch) != 1 or len(batch[0]) != 4:
        raise ValueError("SQLite payload preflight returned invalid bounded metadata")
    count, max_scalar, max_record, total = batch[0]
    if any(type(value) is not int for value in (count, max_scalar, max_record, total)):
        raise ValueError("SQLite payload preflight metadata must be exact integers")
    if count != expected_count:
        raise ValueError("SQLite payload preflight count does not match census")
    adjusted_record = max_record + record_overhead
    adjusted_total = total + count * record_overhead
    _require_projection_cap("SQLite preflight scalar bytes", max_scalar, hasher.scalar_cap)
    _require_projection_cap("SQLite preflight record bytes", adjusted_record, hasher.record_cap)
    _require_projection_cap(
        "SQLite preflight total bytes",
        adjusted_total,
        hasher.remaining_bytes(),
    )
    _require_projection_deadline(started_at)
    return _SqlitePayloadPreflight(
        count=count,
        max_scalar_bytes=max_scalar,
        max_record_bytes=adjusted_record,
        total_bytes=adjusted_total,
        fetch_batch=_derive_projection_fetch_batch(
            hasher.remaining_bytes(),
            adjusted_record + 8,
        ),
    )


def _sqlite_synthetic_row_digest(
    table_name: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[object]],
    *,
    row_cap: int,
) -> tuple[str, int]:
    hasher = _SqliteProjectionHasher(total_cap=16 * 1024)
    hasher.add_record((b"sqlite-synthetic-row-projection.v1",))
    hasher.add_record((_encode_sqlite_value(table_name, scalar_cap=1024),))
    for column in columns:
        hasher.add_record((_encode_sqlite_value(column, scalar_cap=1024),))
    row_count = 0
    for row in rows:
        row_count += 1
        _require_projection_cap("synthetic SQLite rows", row_count, row_cap)
        if len(row) != len(columns):
            raise ValueError("SQLite row width does not match the bound column set")
        hasher.add_record(_encode_sqlite_value(value, scalar_cap=1024) for value in row)
    return hasher.hexdigest(), row_count


def _quote_sqlite_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _sqlite_census(
    connection: sqlite3.Connection,
    inner_query: str,
    parameters: Sequence[object],
    *,
    cap: int,
    started_at: float,
) -> int:
    _require_projection_deadline(started_at)
    cursor = connection.execute(
        f"SELECT COUNT(*) FROM ({inner_query} LIMIT {cap + 1}) AS bounded_census",
        parameters,
    )
    batch = cursor.fetchmany(PROJECTION_FETCH_BATCH)
    if len(batch) != 1 or len(batch[0]) != 1 or type(batch[0][0]) is not int:
        raise ValueError("SQLite bounded census returned an invalid metadata shape")
    observed = int(batch[0][0])
    _require_projection_cap("SQLite census", observed, cap)
    _require_projection_deadline(started_at)
    return observed


def _project_sqlite_migration_state(path: Path) -> _SqliteMigrationProjectionReceipt:
    caps = (
        ("tables", PROJECTION_TABLE_CAP),
        ("columns_per_table", PROJECTION_COLUMN_CAP),
        ("schema_records", SQLITE_SCHEMA_RECORD_CAP),
        ("rows_per_table", PROJECTION_ROWS_PER_TABLE_CAP),
        ("total_rows", PROJECTION_TOTAL_ROWS_CAP),
        ("scalar_bytes", PROJECTION_SCALAR_BYTES_CAP),
        ("record_bytes", PROJECTION_RECORD_BYTES_CAP),
        ("total_framed_bytes", PROJECTION_TOTAL_FRAMED_BYTES_CAP),
        ("fetch_batch", PROJECTION_FETCH_BATCH),
        ("deadline_seconds", int(PROJECTION_DEADLINE_SECONDS)),
        ("progress_opcodes", SQLITE_PROGRESS_OPCODES),
    )
    started_at = time.monotonic()
    hasher = _SqliteProjectionHasher()
    hasher.add_record((SQLITE_PROJECTION_VERSION.encode("ascii"),))
    for cap_name, cap_value in caps:
        hasher.add_record((cap_name.encode("ascii"), str(cap_value).encode("ascii")))

    connection = sqlite3.connect(path)
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("BEGIN")

    def progress_callback() -> int:
        return int(time.monotonic() - started_at > PROJECTION_DEADLINE_SECONDS)

    connection.set_progress_handler(progress_callback, SQLITE_PROGRESS_OPCODES)
    try:
        head_count = _sqlite_census(
            connection,
            "SELECT version_num FROM alembic_version",
            (),
            cap=1,
            started_at=started_at,
        )
        head_cursor = connection.execute(
            "SELECT version_num FROM alembic_version ORDER BY version_num COLLATE BINARY LIMIT 2"
        )
        head_observed = 0
        head = ""
        while True:
            _require_projection_deadline(started_at)
            batch = head_cursor.fetchmany(PROJECTION_FETCH_BATCH)
            if not batch:
                break
            for row in batch:
                head_observed += 1
                if len(row) != 1 or not isinstance(row[0], str) or not row[0]:
                    raise ValueError("SQLite Alembic head has an invalid bounded shape")
                head = row[0]
            _require_projection_deadline(started_at)
        if head_count != 1 or head_observed != head_count:
            raise ValueError("SQLite migration projection requires exactly one head")
        hasher.add_record((b"head", _encode_sqlite_value(head)))

        schema_filter = "type IN ('table', 'index') AND name NOT LIKE 'sqlite_%'"
        schema_count = _sqlite_census(
            connection,
            f"SELECT 1 FROM sqlite_schema WHERE {schema_filter}",
            (),
            cap=SQLITE_SCHEMA_RECORD_CAP,
            started_at=started_at,
        )
        schema_length_expressions = (
            _sqlite_encoded_length_sql("type"),
            _sqlite_encoded_length_sql("name"),
            _sqlite_encoded_length_sql("tbl_name"),
            _sqlite_encoded_length_sql("sql"),
        )
        schema_record_octets = " + ".join(
            f"(8 + ({expression}))" for expression in schema_length_expressions
        )
        schema_preflight = _sqlite_payload_preflight(
            connection,
            f"""
            WITH bounded AS (
                SELECT type, name, tbl_name, sql
                FROM sqlite_schema
                WHERE {schema_filter}
                LIMIT {SQLITE_SCHEMA_RECORD_CAP + 1}
            ), lengths AS (
                SELECT
                    MAX({", ".join(schema_length_expressions)}) AS max_scalar_octets,
                    {schema_record_octets} AS record_octets
                FROM bounded
            )
            SELECT COUNT(*),
                   COALESCE(MAX(max_scalar_octets), 0),
                   COALESCE(MAX(record_octets), 0),
                   COALESCE(SUM(8 + record_octets), 0)
            FROM lengths
            """,
            (),
            expected_count=schema_count,
            hasher=hasher,
            started_at=started_at,
        )
        schema_cursor = connection.execute(f"""
            SELECT type, name, tbl_name, sql
            FROM sqlite_schema
            WHERE {schema_filter}
            ORDER BY
                type COLLATE BINARY,
                name COLLATE BINARY,
                tbl_name COLLATE BINARY,
                COALESCE(sql, '') COLLATE BINARY
            LIMIT {SQLITE_SCHEMA_RECORD_CAP + 1}
            """)
        schema_observed = 0
        while True:
            _require_projection_deadline(started_at)
            batch = schema_cursor.fetchmany(schema_preflight.fetch_batch)
            if not batch:
                break
            for record in batch:
                schema_observed += 1
                hasher.add_record(_encode_sqlite_value(value) for value in record)
            _require_projection_deadline(started_at)
        if schema_observed != schema_count:
            raise ValueError("SQLite schema census/content count mismatch")

        table_filter = "type = 'table' AND name NOT LIKE 'sqlite_%'"
        table_count = _sqlite_census(
            connection,
            f"SELECT 1 FROM sqlite_schema WHERE {table_filter}",
            (),
            cap=PROJECTION_TABLE_CAP,
            started_at=started_at,
        )
        table_cursor = connection.execute(f"""
            SELECT name
            FROM sqlite_schema
            WHERE {table_filter}
            ORDER BY name COLLATE BINARY
            LIMIT {PROJECTION_TABLE_CAP + 1}
            """)
        tables_observed = 0
        total_columns = 0
        total_rows = 0
        while True:
            _require_projection_deadline(started_at)
            table_batch = table_cursor.fetchmany(schema_preflight.fetch_batch)
            if not table_batch:
                break
            for table_record in table_batch:
                tables_observed += 1
                if len(table_record) != 1 or not isinstance(table_record[0], str):
                    raise ValueError("SQLite table projection returned invalid metadata")
                table_name = table_record[0]
                quoted_table = _quote_sqlite_identifier(table_name)

                column_count = _sqlite_census(
                    connection,
                    "SELECT 1 FROM pragma_table_xinfo(?)",
                    (table_name,),
                    cap=PROJECTION_COLUMN_CAP,
                    started_at=started_at,
                )
                if column_count == 0:
                    raise ValueError("SQLite admitted table has zero columns")
                column_length_expressions = (
                    _sqlite_encoded_length_sql("cid"),
                    _sqlite_encoded_length_sql("name"),
                    _sqlite_encoded_length_sql("type"),
                    _sqlite_encoded_length_sql('"notnull"'),
                    _sqlite_encoded_length_sql("dflt_value"),
                    _sqlite_encoded_length_sql("pk"),
                    _sqlite_encoded_length_sql("hidden"),
                )
                column_record_octets = " + ".join(
                    f"(8 + ({expression}))" for expression in column_length_expressions
                )
                column_overhead = 8 + len(b"column") + 8 + len(_encode_sqlite_value(table_name))
                column_preflight = _sqlite_payload_preflight(
                    connection,
                    f"""
                    WITH bounded AS (
                        SELECT cid, name, type, "notnull", dflt_value, pk, hidden
                        FROM pragma_table_xinfo(?)
                        LIMIT {PROJECTION_COLUMN_CAP + 1}
                    ), lengths AS (
                        SELECT
                            MAX({", ".join(column_length_expressions)})
                              AS max_scalar_octets,
                            {column_record_octets} AS record_octets
                        FROM bounded
                    )
                    SELECT COUNT(*),
                           COALESCE(MAX(max_scalar_octets), 0),
                           COALESCE(MAX(record_octets), 0),
                           COALESCE(SUM(8 + record_octets), 0)
                    FROM lengths
                    """,
                    (table_name,),
                    expected_count=column_count,
                    hasher=hasher,
                    started_at=started_at,
                    record_overhead=column_overhead,
                )
                column_cursor = connection.execute(
                    f"""
                    SELECT cid, name, type, "notnull", dflt_value, pk, hidden
                    FROM pragma_table_xinfo(?)
                    ORDER BY cid
                    LIMIT {PROJECTION_COLUMN_CAP + 1}
                    """,
                    (table_name,),
                )
                columns_observed = 0
                selected_columns = ""
                order_terms = ""
                row_scalar_length_expressions: list[str] = []
                while True:
                    _require_projection_deadline(started_at)
                    column_batch = column_cursor.fetchmany(column_preflight.fetch_batch)
                    if not column_batch:
                        break
                    for column_record in column_batch:
                        columns_observed += 1
                        column_name = column_record[1]
                        if not isinstance(column_name, str):
                            raise ValueError("SQLite column name is not text")
                        quoted_column = _quote_sqlite_identifier(column_name)
                        selected_columns += (", " if selected_columns else "") + quoted_column
                        order_terms += (", " if order_terms else "") + (
                            f"typeof({quoted_column}) COLLATE BINARY, "
                            f"quote({quoted_column}) COLLATE BINARY"
                        )
                        scalar_length_expression = _sqlite_encoded_length_sql(quoted_column)
                        row_scalar_length_expressions.append(scalar_length_expression)
                        hasher.add_record(
                            chain(
                                (b"column", _encode_sqlite_value(table_name)),
                                (_encode_sqlite_value(value) for value in column_record),
                            )
                        )
                    _require_projection_deadline(started_at)
                if columns_observed != column_count:
                    raise ValueError("SQLite column census/content count mismatch")
                total_columns += columns_observed

                row_count = _sqlite_census(
                    connection,
                    f"SELECT 1 FROM {quoted_table}",
                    (),
                    cap=PROJECTION_ROWS_PER_TABLE_CAP,
                    started_at=started_at,
                )
                _require_projection_cap(
                    "SQLite total rows",
                    total_rows + row_count,
                    PROJECTION_TOTAL_ROWS_CAP,
                )
                row_record_octets = " + ".join(
                    f"(8 + ({expression}))" for expression in row_scalar_length_expressions
                )
                row_max_scalar_expression = (
                    row_scalar_length_expressions[0]
                    if column_count == 1
                    else f"MAX({', '.join(row_scalar_length_expressions)})"
                )
                row_overhead = 8 + len(b"row") + 8 + len(_encode_sqlite_value(table_name))
                row_preflight = _sqlite_payload_preflight(
                    connection,
                    f"""
                    WITH bounded AS (
                        SELECT {selected_columns}
                        FROM {quoted_table}
                        LIMIT {PROJECTION_ROWS_PER_TABLE_CAP + 1}
                    ), lengths AS (
                        SELECT
                            {row_max_scalar_expression} AS max_scalar_octets,
                            {row_record_octets} AS record_octets
                        FROM bounded
                    )
                    SELECT COUNT(*),
                           COALESCE(MAX(max_scalar_octets), 0),
                           COALESCE(MAX(record_octets), 0),
                           COALESCE(SUM(8 + record_octets), 0)
                    FROM lengths
                    """,
                    (),
                    expected_count=row_count,
                    hasher=hasher,
                    started_at=started_at,
                    record_overhead=row_overhead,
                )
                row_cursor = connection.execute(
                    f"SELECT {selected_columns} FROM {quoted_table} "
                    f"ORDER BY {order_terms} LIMIT {PROJECTION_ROWS_PER_TABLE_CAP + 1}"
                )
                rows_observed = 0
                while True:
                    _require_projection_deadline(started_at)
                    row_batch = row_cursor.fetchmany(row_preflight.fetch_batch)
                    if not row_batch:
                        break
                    for row in row_batch:
                        rows_observed += 1
                        hasher.add_record(
                            chain(
                                (b"row", _encode_sqlite_value(table_name)),
                                (_encode_sqlite_value(value) for value in row),
                            )
                        )
                    _require_projection_deadline(started_at)
                if rows_observed != row_count:
                    raise ValueError("SQLite row census/content count mismatch")
                total_rows += rows_observed
                hasher.add_record(
                    (
                        b"table-counts",
                        _encode_sqlite_value(table_name),
                        str(column_count).encode("ascii"),
                        str(row_count).encode("ascii"),
                    )
                )
            _require_projection_deadline(started_at)
        if tables_observed != table_count:
            raise ValueError("SQLite table census/content count mismatch")

        hasher.add_record(
            (
                b"receipt-counts",
                str(schema_count).encode("ascii"),
                str(table_count).encode("ascii"),
                str(total_columns).encode("ascii"),
                str(total_rows).encode("ascii"),
            )
        )
        _require_projection_deadline(started_at)
        receipt = _SqliteMigrationProjectionReceipt(
            projection_version=SQLITE_PROJECTION_VERSION,
            head=head,
            schema_record_count=schema_count,
            table_count=table_count,
            column_count=total_columns,
            row_count=total_rows,
            caps=caps,
            digest=hasher.hexdigest(),
        )
        connection.rollback()
        return receipt
    except sqlite3.Error as exc:
        raise AssertionError(
            f"SQLite resource-bounded migration-state projection failed: {type(exc).__name__}"
        ) from None
    finally:
        connection.set_progress_handler(None, 0)
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def _migration_tree_symlinks(root: Path) -> tuple[Path, ...]:
    return tuple(path for path in root.rglob("*") if path.is_symlink())


def test_migration_tree_has_no_top_level_regular_package_carrier() -> None:
    assert not (REPO_ROOT / "alembic/__init__.py").exists()
    assert (REPO_ROOT / "alembic/versions/__init__.py").is_file()


def test_current_repository_carriers_are_regular_and_migration_tree_has_no_symlinks() -> None:
    migration_root = REPO_ROOT / "alembic"
    assert migration_root.is_dir()
    assert not migration_root.is_symlink()
    assert migration_root.resolve() == migration_root
    assert _migration_tree_symlinks(migration_root) == ()

    for carrier in (
        REPO_ROOT / "app/__init__.py",
        REPO_ROOT / "core/__init__.py",
        REPO_ROOT / "settings.py",
    ):
        assert carrier.is_file()
        assert not carrier.is_symlink()
        assert carrier.resolve().is_relative_to(REPO_ROOT)


def test_migration_tree_symlink_census_detects_nested_carrier(tmp_path: Path) -> None:
    migration_root = tmp_path / "alembic"
    migration_root.mkdir()
    target = tmp_path / "outside.py"
    target.write_text("outside = True\n", encoding="utf-8")
    link = migration_root / "linked.py"
    link.symlink_to(target)

    assert _migration_tree_symlinks(migration_root) == (link,)


@pytest.mark.parametrize("variable", FORBIDDEN_CHILD_ENV_KEYS)
def test_controlled_child_environment_does_not_inherit_startup_or_secret_carriers(
    variable: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(variable, "sentinel-value")

    env = _controlled_env(pythonpath=None)

    assert variable not in env
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONHASHSEED"] == "0"
    assert env["APP_ENV"] == "test"
    assert env["ENVIRONMENT"] == "test"
    assert env["TESTING"] == "true"


def test_child_failure_diagnostics_redact_database_url_and_password(tmp_path: Path) -> None:
    credentialed_url = "postgresql+psycopg://migration_user:decoded%40password@localhost:5432/migration_db"  # pragma: allowlist secret
    env = _controlled_env(pythonpath=None)
    env["DATABASE_URL"] = credentialed_url
    probe = r"""
import os
import sys
from urllib.parse import unquote, urlsplit

database_url = os.environ["DATABASE_URL"]
sys.stdout.write(database_url)
sys.stderr.write(unquote(urlsplit(database_url).password or ""))
raise SystemExit(7)
"""

    with pytest.raises(pytest.fail.Exception) as failure:
        _run_python(["-c", probe], cwd=tmp_path, env=env)

    message = str(failure.value)
    assert credentialed_url not in message
    assert "decoded%40password" not in message
    assert "decoded@password" not in message
    assert "[REDACTED]" in message


def test_sqlite_bounded_projection_changes_after_dml_and_preserves_multiplicity(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sqlite-state-sensitivity.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('test-head')")
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES ('alpha')")
        connection.commit()
    first = _project_sqlite_migration_state(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE sample SET value = 'beta'")
        connection.commit()
    changed = _project_sqlite_migration_state(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO sample VALUES ('beta')")
        connection.commit()
    duplicated = _project_sqlite_migration_state(database_path)

    assert first.head == changed.head == duplicated.head == "test-head"
    assert (
        first.schema_record_count == changed.schema_record_count == duplicated.schema_record_count
    )
    assert first.digest != changed.digest
    assert changed.digest != duplicated.digest
    assert duplicated.row_count == changed.row_count + 1


def test_sqlite_projection_preserves_quoted_comma_identifier_expression(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sqlite-quoted-comma.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('test-head')")
        connection.execute('CREATE TABLE sample ("part, name" TEXT NOT NULL)')
        connection.execute("INSERT INTO sample (\"part, name\") VALUES ('alpha')")
        connection.commit()
    before = _project_sqlite_migration_state(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE sample SET \"part, name\" = 'beta'")
        connection.commit()
    after = _project_sqlite_migration_state(database_path)

    assert before.digest != after.digest
    quoted_expression = _sqlite_encoded_length_sql(_quote_sqlite_identifier("part, name"))
    assert '"part, name"' in quoted_expression


def test_sqlite_synthetic_digest_is_bound_to_content_columns_and_duplicate_count() -> None:
    base = _sqlite_synthetic_row_digest("sample", ("value",), (("alpha",),), row_cap=2)
    changed = _sqlite_synthetic_row_digest("sample", ("value",), (("beta",),), row_cap=2)
    renamed = _sqlite_synthetic_row_digest("sample", ("renamed",), (("alpha",),), row_cap=2)
    duplicated = _sqlite_synthetic_row_digest(
        "sample",
        ("value",),
        (("alpha",), ("alpha",)),
        row_cap=2,
    )

    assert len({base[0], changed[0], renamed[0], duplicated[0]}) == 4
    assert base[1] == changed[1] == renamed[1] == 1
    assert duplicated[1] == 2


def test_sqlite_projection_caps_pass_at_boundary_and_fail_at_cap_plus_one() -> None:
    _require_projection_cap("synthetic", 2, 2)
    with pytest.raises(ValueError, match="fixed resource bound"):
        _require_projection_cap("synthetic", 3, 2)
    with pytest.raises(ValueError, match="synthetic SQLite rows"):
        _sqlite_synthetic_row_digest(
            "sample",
            ("value",),
            (("alpha",), ("beta",)),
            row_cap=1,
        )


def test_sqlite_projection_byte_boundaries_are_exact() -> None:
    encoded = _encode_sqlite_value("x", scalar_cap=6)
    assert encoded == b"text:x"
    with pytest.raises(ValueError, match="encoded scalar bytes"):
        _encode_sqlite_value("x", scalar_cap=5)

    passing = _SqliteProjectionHasher(scalar_cap=1, record_cap=9, total_cap=17)
    passing.add_record((b"x",))
    assert passing.total_framed_bytes == 17
    with pytest.raises(ValueError, match="record bytes"):
        _SqliteProjectionHasher(scalar_cap=1, record_cap=8, total_cap=17).add_record((b"x",))
    with pytest.raises(ValueError, match="total framed bytes"):
        _SqliteProjectionHasher(scalar_cap=1, record_cap=9, total_cap=16).add_record((b"x",))

    assert _derive_projection_fetch_batch(1024, 4) == 256
    assert _derive_projection_fetch_batch(10, 3) == 3
    assert _derive_projection_fetch_batch(0, 8) == 1

    with sqlite3.connect(":memory:") as connection:
        passing_hasher = _SqliteProjectionHasher(scalar_cap=1, record_cap=1, total_cap=1)
        preflight = _sqlite_payload_preflight(
            connection,
            "SELECT 1, 1, 1, 1",
            (),
            expected_count=1,
            hasher=passing_hasher,
            started_at=time.monotonic(),
        )
        assert preflight.max_scalar_bytes == preflight.max_record_bytes == 1
        with pytest.raises(ValueError, match="preflight scalar bytes"):
            _sqlite_payload_preflight(
                connection,
                "SELECT 1, 2, 1, 1",
                (),
                expected_count=1,
                hasher=passing_hasher,
                started_at=time.monotonic(),
            )
        with pytest.raises(ValueError, match="preflight record bytes"):
            _sqlite_payload_preflight(
                connection,
                "SELECT 1, 1, 2, 1",
                (),
                expected_count=1,
                hasher=passing_hasher,
                started_at=time.monotonic(),
            )
        with pytest.raises(ValueError, match="preflight total bytes"):
            _sqlite_payload_preflight(
                connection,
                "SELECT 1, 1, 1, 2",
                (),
                expected_count=1,
                hasher=passing_hasher,
                started_at=time.monotonic(),
            )


def test_sqlite_projection_deadline_passes_at_boundary_and_fails_after() -> None:
    _require_projection_deadline(10.0, now=lambda: 11.0, deadline_seconds=1.0)
    with pytest.raises(TimeoutError, match="deadline exceeded"):
        _require_projection_deadline(10.0, now=lambda: 11.01, deadline_seconds=1.0)


def test_sqlite_projection_contract_has_exact_caps_and_bounded_queries() -> None:
    assert (
        PROJECTION_TABLE_CAP,
        PROJECTION_COLUMN_CAP,
        SQLITE_SCHEMA_RECORD_CAP,
        PROJECTION_ROWS_PER_TABLE_CAP,
        PROJECTION_TOTAL_ROWS_CAP,
        PROJECTION_SCALAR_BYTES_CAP,
        PROJECTION_RECORD_BYTES_CAP,
        PROJECTION_TOTAL_FRAMED_BYTES_CAP,
        PROJECTION_FETCH_BATCH,
        PROJECTION_DEADLINE_SECONDS,
        SQLITE_PROGRESS_OPCODES,
    ) == (256, 256, 2048, 10_000, 100_000, 1_048_576, 4_194_304, 67_108_864, 256, 120.0, 1000)
    projector_source = inspect.getsource(_project_sqlite_migration_state)
    source = "\n".join(
        (
            inspect.getsource(_sqlite_encoded_length_sql),
            inspect.getsource(_sqlite_payload_preflight),
            projector_source,
        )
    )
    assert "type IN ('table', 'index')" in source
    assert "name NOT LIKE 'sqlite_%'" in source
    assert "pragma_table_xinfo" in source
    assert "fetchmany(schema_preflight.fetch_batch)" in source
    assert "fetchmany(column_preflight.fetch_batch)" in source
    assert "fetchmany(row_preflight.fetch_batch)" in source
    assert "_sqlite_payload_preflight(" in source
    assert "MAX(max_scalar_octets)" in source
    assert "MAX(record_octets)" in source
    assert "SUM(8 + record_octets)" in source
    assert "length(CAST(" in source
    assert "_derive_projection_fetch_batch(" in source
    assert "row_scalar_length_expressions.append(" in source
    assert ".split(" not in source
    assert projector_source.index(
        "schema_preflight = _sqlite_payload_preflight"
    ) < projector_source.index("schema_cursor = connection.execute")
    assert projector_source.index(
        "column_preflight = _sqlite_payload_preflight"
    ) < projector_source.index("column_cursor = connection.execute")
    assert projector_source.index(
        "row_preflight = _sqlite_payload_preflight"
    ) < projector_source.index("row_cursor = connection.execute")
    assert "LIMIT {" in source
    assert "ORDER BY" in source
    assert "typeof(" in source and "quote(" in source and "COLLATE BINARY" in source
    assert "set_progress_handler" in source
    assert "PRAGMA busy_timeout = 30000" in source
    assert "BEGIN" in source
    for forbidden in (
        "cano" + "nical",
        "database" + "-state",
        "sqlite_sequence",
        "trigger",
        "view",
        "os.environ",
        "getenv(",
        ".all(",
        ".scalars",
        "tuple(",
        "list(",
        ".sort(",
        "sorted(",
    ):
        assert forbidden not in source.lower()


def test_sqlite_value_encoding_has_explicit_tags_and_rejects_unadmitted_values() -> None:
    encoded = {
        _encode_sqlite_value(None),
        _encode_sqlite_value(7),
        _encode_sqlite_value(0.5),
        _encode_sqlite_value("7"),
        _encode_sqlite_value(b"7"),
    }
    assert len(encoded) == 5
    assert _encode_sqlite_value(0.5) == b"float:0x1.0000000000000p-1"

    for value in (True, math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            _encode_sqlite_value(value)
    with pytest.raises(TypeError):
        _encode_sqlite_value(object())


def test_alembic_config_declares_repository_import_path() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(ALEMBIC_INI, encoding="utf-8")

    assert parser.get("alembic", "script_location") == "alembic"
    assert parser.get("alembic", "prepend_sys_path") == "%(here)s"
    assert parser.get("alembic", "path_separator") == "os"


def test_migration_environment_uses_normal_package_imports_only() -> None:
    env_path = REPO_ROOT / "alembic/env.py"
    source = env_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(env_path))

    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "sys" not in imported_modules
    assert "sys.path" not in source
    assert "ROOT_DIR" not in source
    assert "noqa: E402" not in source


def test_installed_alembic_and_repository_modules_have_distinct_owners() -> None:
    probe = r"""
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sysconfig

modules = ("alembic", "alembic.config", "alembic.context", "alembic.op")
origins = {}
for name in modules + ("app", "core", "settings"):
    spec = importlib.util.find_spec(name)
    origins[name] = str(Path(spec.origin or "").resolve()) if spec is not None else None
distribution = importlib.metadata.distribution("alembic")
print(json.dumps({
    "origins": origins,
    "purelib": str(Path(sysconfig.get_path("purelib")).resolve()),
    "distribution_root": str(Path(distribution.locate_file("")).resolve()),
    "alembic_root": str(Path(distribution.locate_file("alembic")).resolve()),
}, sort_keys=True))
"""
    completed = _run_python(
        ["-c", probe],
        cwd=REPO_ROOT,
        env=_controlled_env(pythonpath=str(REPO_ROOT)),
    )
    payload: dict[str, Any] = json.loads(completed.stdout)
    origins = payload["origins"]
    purelib = Path(payload["purelib"])
    distribution_root = Path(payload["distribution_root"])
    installed_alembic_root = Path(payload["alembic_root"])

    assert distribution_root == purelib
    assert installed_alembic_root.is_relative_to(purelib)
    for module_name in ("alembic", "alembic.config", "alembic.context", "alembic.op"):
        assert Path(origins[module_name]).is_relative_to(installed_alembic_root)
        assert not Path(origins[module_name]).is_relative_to(REPO_ROOT / "alembic")
    assert Path(origins["app"]) == (REPO_ROOT / "app/__init__.py").resolve()
    assert Path(origins["core"]) == (REPO_ROOT / "core/__init__.py").resolve()
    assert Path(origins["settings"]) == (REPO_ROOT / "settings.py").resolve()


def test_old_top_level_package_carrier_recreates_the_collision(tmp_path: Path) -> None:
    package_root = tmp_path / "alembic"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("# old repository carrier\n", encoding="utf-8")
    probe = r"""
import importlib.util
import json
from pathlib import Path

parent = importlib.util.find_spec("alembic")
try:
    child = importlib.util.find_spec("alembic.config")
except ModuleNotFoundError:
    child = None
print(json.dumps({
    "parent": str(Path(parent.origin or "").resolve()) if parent is not None else None,
    "child": child is not None,
}, sort_keys=True))
"""
    completed = _run_python(
        ["-c", probe],
        cwd=tmp_path,
        env=_controlled_env(pythonpath=str(tmp_path)),
    )
    payload = json.loads(completed.stdout)

    assert Path(payload["parent"]) == (package_root / "__init__.py").resolve()
    assert payload["child"] is False


def test_fresh_sqlite_upgrade_current_and_second_upgrade_are_deterministic(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "alembic-contract.sqlite3"
    database_url = f"sqlite:///{database_path.as_posix()}"
    env = _controlled_env(pythonpath=None)
    env["DATABASE_URL"] = database_url
    command_prefix = ["-m", "alembic", "-c", str(ALEMBIC_INI)]

    _run_python([*command_prefix, "upgrade", "head"], cwd=REPO_ROOT, env=env)
    heads = _script_heads()
    assert len(heads) == 1
    assert heads[0]
    first_projection = _project_sqlite_migration_state(database_path)
    assert first_projection.head == heads[0]

    current = _run_python(
        [*command_prefix, "current", "--check-heads"],
        cwd=REPO_ROOT,
        env=env,
    )
    assert heads[0] in current.stdout

    _run_python([*command_prefix, "upgrade", "head"], cwd=REPO_ROOT, env=env)
    assert _project_sqlite_migration_state(database_path) == first_projection


def _docker_marker_block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start) + len(end_marker)
    return source[start:end]


def _docker_python_heredoc(block: str) -> str:
    return block.split("<<'PY'\n", maxsplit=1)[1].rsplit("\nPY", maxsplit=1)[0]


def test_final_image_guards_are_separate_ordered_non_root_runs() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    production = dockerfile.split("FROM runtime-base AS production", maxsplit=1)[1]
    precheck_start = production.index("# ALEMBIC-FILESYSTEM-CARRIER-PRECHECK-START")
    ownership_start = production.index("# ALEMBIC-INSTALLED-OWNERSHIP-GUARD-START")
    cli_start = production.index("# ALEMBIC-CLI-HEADS-GUARD-START")
    staging_start = production.index("FROM production AS staging")
    final_user = production.rindex("USER pulseplate", 0, precheck_start)
    precheck = _docker_marker_block(
        production,
        "# ALEMBIC-FILESYSTEM-CARRIER-PRECHECK-START",
        "# ALEMBIC-FILESYSTEM-CARRIER-PRECHECK-END",
    )
    ownership = _docker_marker_block(
        production,
        "# ALEMBIC-INSTALLED-OWNERSHIP-GUARD-START",
        "# ALEMBIC-INSTALLED-OWNERSHIP-GUARD-END",
    )
    cli = _docker_marker_block(
        production,
        "# ALEMBIC-CLI-HEADS-GUARD-START",
        "# ALEMBIC-CLI-HEADS-GUARD-END",
    )

    assert final_user < precheck_start < ownership_start < cli_start < staging_start
    assert "USER root" not in production[final_user:staging_start]
    assert precheck.count("\nRUN ") == ownership.count("\nRUN ") == cli.count("\nRUN ") == 1

    precheck_tree = ast.parse(_docker_python_heredoc(precheck))
    imported_modules = {
        alias.name
        for node in ast.walk(precheck_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module
        for node in ast.walk(precheck_tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    assert imported_modules <= {"pathlib", "sys"}
    assert not any(
        module == "alembic" or module.startswith("alembic.") for module in imported_modules
    )
    assert "/opt/venv/bin/alembic" not in precheck
    assert 'literal_app_root = Path("/app")' in precheck
    assert 'literal_migration_root = Path("/app/alembic")' in precheck
    assert "path.is_symlink() or not path.is_dir()" in precheck
    assert "app_root != literal_app_root" in precheck
    assert "migration_root != literal_migration_root" in precheck
    assert "migration_root.is_relative_to(app_root)" in precheck
    assert 'migration_root.rglob("*")' in precheck
    assert "if path.is_symlink()" in precheck
    assert "if package_carrier.exists() or package_carrier.is_symlink():" in precheck
    assert 'migration_root.rglob("__pycache__")' in precheck
    assert 'migration_root.rglob("*.pyc")' in precheck
    assert 'migration_root.rglob("*.pyo")' in precheck

    assert "RUN /opt/venv/bin/python - <<'PY'" in ownership
    assert "venv_root = Path(sys.prefix).resolve()" in ownership
    assert 'if venv_root != Path("/opt/venv"):' in ownership
    assert 'importlib.metadata.distribution("alembic")' in ownership
    assert 'sysconfig.get_path("purelib")' in ownership
    assert "from alembic.config import Config" in ownership
    assert "from alembic.script import ScriptDirectory" in ownership
    assert "ScriptDirectory.from_config(config)" in ownership
    assert "len(heads) != 1" in ownership
    assert all(name in ownership for name in ("alembic.config", "alembic.context", "alembic.op"))
    assert all(name in ownership for name in ('"app"', '"core"', '"settings"'))
    assert "not expected_origin.is_file() or expected_origin.is_symlink()" in ownership

    assert "RUN /opt/venv/bin/alembic -c /app/alembic.ini heads" in cli
    combined_guards = precheck + ownership + cli
    assert "upgrade" not in combined_guards.lower()
    assert "DATABASE_URL" not in combined_guards
    assert "urllib" not in combined_guards
    assert "socket" not in combined_guards
    assert re.search(r"python3\.\d+", combined_guards) is None


def test_docker_context_excludes_python_bytecode_after_allowlists() -> None:
    lines = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    allowlist_end = lines.index("!bodyfat.py")

    for pattern in ("**/__pycache__/", "**/*.pyc", "**/*.pyo"):
        assert lines.index(pattern) > allowlist_end

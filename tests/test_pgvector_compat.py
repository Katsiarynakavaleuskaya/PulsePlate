"""Compatibility proof for the pgvector 0.5 Python binding and PostgreSQL 0.8.2.

The source/lock and import canaries always run.  The database assertions run
when ``PGVECTOR_COMPAT_DATABASE_URL`` is configured; CI makes that contract
mandatory with ``PGVECTOR_COMPAT_REQUIRED=1``.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import ModuleType
from typing import NoReturn
from urllib.parse import quote
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    BigInteger,
    Column,
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
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
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


def require_feature(feature_key: str, reason: str) -> NoReturn:
    """Use the repository skip protocol for optional compatibility dependencies."""

    assert feature_key in {PGVECTOR_BINDING_FEATURE, PGVECTOR_DATABASE_FEATURE}
    pytest.skip(f"feature_disabled:{feature_key} {reason}")


def _skip_or_fail_binding(reason: str) -> NoReturn:
    if os.getenv("PRE_COMMIT", "").strip() == "1":
        require_feature(PGVECTOR_BINDING_FEATURE, reason)
    pytest.fail(reason)


def _skip_or_fail_database(reason: str, *, required: bool) -> NoReturn:
    if required:
        pytest.fail(reason)
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

    return engine.dialect.identifier_preparer.quote_identifier(identifier)


def _required_ci_pgvector_url(environment: Mapping[str, str] | None = None) -> URL:
    source = os.environ if environment is None else environment
    required = source.get(PGVECTOR_COMPAT_REQUIRED, "").strip()
    database_url = source.get(PGVECTOR_COMPAT_DATABASE_URL, "").strip()
    if required != "1":
        if environment is None:
            require_feature(
                PGVECTOR_DATABASE_FEATURE,
                "full migration proof requires PGVECTOR_COMPAT_REQUIRED=1",
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


def _run_alembic(database_url: URL, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = _alembic_subprocess_env(database_url)
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(REPO_ROOT / "alembic.ini"), *arguments],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
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


def _postgres_application_tables(engine: Engine) -> tuple[tuple[str, str], ...]:
    with engine.connect() as connection:
        rows = connection.execute(text("""
                SELECT schemaname, tablename
                FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename
                """)).all()
    return tuple((str(row.schemaname), str(row.tablename)) for row in rows)


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
        "tests/test_pgvector_compat.py",
        "tests/test_pgvector_embedding_migration.py",
        "tests/test_vector_rag.py",
        "tests/test_db_rls.py",
    )
    assert all(f"'{path}'" in filter_contract for path in direct_proof_inputs)
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
def test_full_graph_authority_rejects_every_query_parameter(query_key: str) -> None:
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
def test_full_graph_authority_requires_exact_ci_markers(marker: str) -> None:
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


def test_database_failure_aggregation_preserves_primary_and_cleanup_errors() -> None:
    primary = AssertionError("primary migration failure")
    cleanup = RuntimeError("cleanup receipt failure")

    with pytest.raises(BaseExceptionGroup) as grouped:
        _raise_preserved_failures(primary, [cleanup])

    assert grouped.value.exceptions == (primary, cleanup)


def test_full_graph_database_receipt_cleanup_contract_is_fail_closed() -> None:
    source = inspect.getsource(test_full_alembic_graph_upgrades_dedicated_postgres_then_is_noop)

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


def test_full_alembic_graph_upgrades_dedicated_postgres_then_is_noop() -> None:
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
            receipt = _CreatedDatabaseReceipt(database_name=database_name, oid=created_oid)

        target_url = parsed_url.set(database=database_name)
        target_engine = create_engine(target_url, poolclass=NullPool)
        _run_alembic(target_url, "upgrade", "head")

        scripts = ScriptDirectory.from_config(Config(str(REPO_ROOT / "alembic.ini")))
        heads = tuple(scripts.get_heads())
        assert len(heads) == 1
        assert heads[0]
        with target_engine.connect() as connection:
            versions = tuple(
                connection.scalars(text("SELECT version_num FROM alembic_version")).all()
            )
        assert versions == heads
        first_tables = _postgres_application_tables(target_engine)

        _run_alembic(target_url, "current", "--check-heads")
        _run_alembic(target_url, "upgrade", "head")
        with target_engine.connect() as connection:
            repeated_versions = tuple(
                connection.scalars(text("SELECT version_num FROM alembic_version")).all()
            )
        assert repeated_versions == versions
        assert _postgres_application_tables(target_engine) == first_tables
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

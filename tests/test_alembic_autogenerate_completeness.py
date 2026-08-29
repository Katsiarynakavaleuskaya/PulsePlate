"""Focused Phase A tests for bounded Alembic autogenerate ownership."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import cast

from alembic.operations import ops
import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.engine import Connection

import scripts.ci.check_alembic_autogenerate_completeness as checker
from core.db import Base, load_canonical_orm_metadata
import core.db_alembic_ownership as ownership

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / "alembic" / "env.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "ci" / "check_alembic_autogenerate_completeness.py"
CORE_OWNERSHIP_PATH = REPO_ROOT / "core" / "db_alembic_ownership.py"
DOCKERFILE_PATH = REPO_ROOT / "Dockerfile"


def _fake_connection(dialect_name: str) -> Connection:
    return cast(Connection, SimpleNamespace(dialect=SimpleNamespace(name=dialect_name)))


def _raw_expected_tree() -> ops.UpgradeOps:
    return ops.UpgradeOps(
        ops=[
            ops.ModifyTableOps(
                "foods",
                ops=[ops.DropIndexOp("ix_foods_gtin", table_name="foods")],
            ),
            *(ops.DropTableOp(table_name) for table_name in checker.MIGRATION_OWNED_TABLE_KEYS),
        ]
    )


def test_env_wires_canonical_metadata_and_exact_callback_in_both_modes() -> None:
    source = ENV_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ENV_PATH))
    configure_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "configure"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "context"
    ]

    assert len(configure_calls) == 2
    for call in configure_calls:
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        assert isinstance(keywords["compare_type"], ast.Constant)
        assert keywords["compare_type"].value is True
        assert isinstance(keywords["compare_server_default"], ast.Constant)
        assert keywords["compare_server_default"].value is True
        assert isinstance(keywords["include_object"], ast.Name)
        assert keywords["include_object"].id == "include_autogenerate_object"

    assert "from core.db import Base" not in source
    assert "from core.db_alembic_ownership import include_autogenerate_object" in source
    assert "scripts.ci.check_alembic_autogenerate_completeness" not in source
    assert "target_metadata = load_canonical_orm_metadata()" in source
    assert "legacy_app" not in source
    assert "app.main" not in source
    assert "sys.path" not in source
    assert "spec_from_file_location" not in source
    assert load_canonical_orm_metadata() is Base.metadata
    assert checker.include_autogenerate_object is ownership.include_autogenerate_object
    assert checker.MIGRATION_OWNED_TABLE_KEYS is ownership.MIGRATION_OWNED_TABLE_KEYS
    assert checker.DEFAULT_SCHEMA_NAMES is ownership.DEFAULT_SCHEMA_NAMES


def test_core_module_is_the_only_callback_policy_owner() -> None:
    core_source = CORE_OWNERSHIP_PATH.read_text(encoding="utf-8")
    checker_source = CHECKER_PATH.read_text(encoding="utf-8")
    env_source = ENV_PATH.read_text(encoding="utf-8")
    core_tree = ast.parse(core_source, filename=str(CORE_OWNERSHIP_PATH))
    checker_tree = ast.parse(checker_source, filename=str(CHECKER_PATH))
    env_tree = ast.parse(env_source, filename=str(ENV_PATH))

    core_definitions = {
        node.name for node in ast.walk(core_tree) if isinstance(node, ast.FunctionDef)
    }
    checker_definitions = {
        node.name for node in ast.walk(checker_tree) if isinstance(node, ast.FunctionDef)
    }
    assigned_names = {
        tree_name: {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for tree_name, tree in (
            ("core", core_tree),
            ("checker", checker_tree),
            ("env", env_tree),
        )
    }

    assert "include_autogenerate_object" in core_definitions
    assert "include_autogenerate_object" not in checker_definitions
    assert "DEFAULT_SCHEMA_NAMES" in assigned_names["core"]
    assert "MIGRATION_OWNED_TABLE_KEYS" in assigned_names["core"]
    assert "DEFAULT_SCHEMA_NAMES" not in assigned_names["checker"]
    assert "MIGRATION_OWNED_TABLE_KEYS" not in assigned_names["checker"]
    assert "DEFAULT_SCHEMA_NAMES" not in assigned_names["env"]
    assert "MIGRATION_OWNED_TABLE_KEYS" not in assigned_names["env"]


def test_core_callback_module_has_exact_pure_import_topology_and_no_side_effects() -> None:
    source = CORE_OWNERSHIP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CORE_OWNERSHIP_PATH))
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]

    assert len(imports) == 1
    assert isinstance(imports[0], ast.ImportFrom)
    assert imports[0].module == "__future__"
    assert all(
        forbidden not in source
        for forbidden in (
            "from core.db import",
            "MetaData",
            "create_engine",
            "Session",
            "os.environ",
            "getenv",
            "app.",
            "alembic.autogenerate",
            "MigrationContext",
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys; import core.db_alembic_ownership as owner; "
                "print(json.dumps({'core_db': 'core.db' in sys.modules, "
                "'sqlalchemy': 'sqlalchemy' in sys.modules, "
                "'app': 'app' in sys.modules, "
                "'tables': sorted(owner.MIGRATION_OWNED_TABLE_KEYS)}))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "app": False,
        "core_db": False,
        "sqlalchemy": False,
        "tables": sorted(ownership.MIGRATION_OWNED_TABLE_KEYS),
    }


def test_dockerfile_already_carries_the_core_callback_module() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "COPY --chown=pulseplate:pulseplate core/ ./core/" in dockerfile


@pytest.mark.parametrize("schema", [None, "public"])
@pytest.mark.parametrize("name", sorted(checker.MIGRATION_OWNED_TABLE_KEYS))
def test_callback_excludes_only_exact_public_reflected_database_tables(
    schema: str | None,
    name: str,
) -> None:
    table = Table(name, MetaData(), Column("id", Integer), schema=schema)

    assert checker.include_autogenerate_object(table, name, "table", True, None) is False
    assert checker.include_autogenerate_object(table, name, "table", False, None) is True
    assert checker.include_autogenerate_object(table, name, "column", True, None) is True
    assert checker.include_autogenerate_object(table, name, "table", True, table) is True


def test_callback_keeps_unknown_and_nondefault_schema_tables_visible() -> None:
    unknown = Table("unexpected", MetaData(), Column("id", Integer))
    private = Table("foods", MetaData(), Column("id", Integer), schema="private")

    assert (
        checker.include_autogenerate_object(
            unknown,
            "unexpected",
            "table",
            True,
            None,
        )
        is True
    )
    assert checker.include_autogenerate_object(private, "foods", "table", True, None) is True


def test_raw_operation_tree_classifies_exact_migration_owned_drops() -> None:
    records, unknown, reasons = (
        checker._classify_operation_tree(  # pylint: disable=protected-access
            _raw_expected_tree(),
            rail="raw",
        )
    )

    assert unknown == ()
    assert reasons == ()
    assert {record.table_name for record in records if record.operation == "DropTableOp"} == set(
        checker.MIGRATION_OWNED_TABLE_KEYS
    )
    assert len(records) == 7
    assert len({record.path for record in records}) == len(records)
    assert records[0].operation == "UpgradeOps"
    assert records[0].reason_code == "raw_root_container"
    assert any(
        record.operation == "ModifyTableOps"
        and record.reason_code == "expected_migration_table_container"
        for record in records
    )
    assert all(record.disposition in {"structural", "migration_owned"} for record in records)


def test_recursive_operation_tree_fails_closed_for_unknown_and_nested_nodes() -> None:
    nested = ops.UpgradeOps(
        ops=[
            ops.UpgradeOps(ops=[]),
            ops.ModifyTableOps(
                "users",
                ops=[ops.DropIndexOp("ix_unknown", table_name="users")],
            ),
        ]
    )

    records, unknown, reasons = (
        checker._classify_operation_tree(  # pylint: disable=protected-access
            nested,
            rail="raw",
        )
    )

    assert "raw_migration_table_drop_missing" in reasons
    assert any(record.reason_code == "nested_upgrade_container" for record in records)
    assert any(record.reason_code == "raw_unexpected_container" for record in records)
    assert any("DropIndexOp" in key for key in unknown)


def test_unknown_future_container_is_recorded_and_its_children_are_traversed() -> None:
    future_container = ops.OpContainer(ops=[ops.DropTableOp("unexpected")])
    tree = ops.UpgradeOps(
        ops=[
            future_container,
            *(ops.DropTableOp(table_name) for table_name in checker.MIGRATION_OWNED_TABLE_KEYS),
        ]
    )

    records, unknown, reasons = (
        checker._classify_operation_tree(  # pylint: disable=protected-access
            tree,
            rail="raw",
        )
    )

    assert reasons == ()
    by_path = {record.path: record for record in records}
    assert by_path["upgrade/0"].operation == "OpContainer"
    assert by_path["upgrade/0"].reason_code == "raw_unexpected_container"
    assert by_path["upgrade/0/0"].operation == "DropTableOp"
    assert by_path["upgrade/0/0"].reason_code == "raw_operation_not_admitted"
    assert len(unknown) == 2


def test_admitted_tree_rejects_every_remaining_operation() -> None:
    admitted = ops.UpgradeOps(ops=[ops.DropTableOp("foods")])

    records, unknown, reasons = (
        checker._classify_operation_tree(  # pylint: disable=protected-access
            admitted,
            rail="admitted",
        )
    )

    assert reasons == ()
    assert len(records) == 2
    assert records[0].reason_code == "admitted_root_container"
    assert records[1].reason_code == "admitted_operation_present"
    assert len(unknown) == 1


def test_incomplete_metadata_fails_before_connection_use() -> None:
    metadata = MetaData()
    Table("unexpected", metadata, Column("id", Integer))

    report = checker.evaluate_alembic_autogenerate_completeness(
        cast(Connection, object()),
        metadata,
    )

    assert report.result == "fail"
    assert report.reason_codes == ("canonical_metadata_identity_mismatch",)
    assert report.alembic_head is None


def test_exact_name_clone_metadata_fails_identity_before_connection_use() -> None:
    clone = MetaData()
    for table_name in checker.CANONICAL_MAPPED_TABLE_KEYS:
        Table(table_name, clone, Column("id", Integer))

    report = checker.evaluate_alembic_autogenerate_completeness(
        cast(Connection, object()),
        clone,
    )

    assert set(report.canonical_mapped_table_keys) == set(checker.CANONICAL_MAPPED_TABLE_KEYS)
    assert report.reason_codes == ("canonical_metadata_identity_mismatch",)
    assert report.result == "fail"


def test_phase_a_report_is_deterministic_and_explicitly_reserves_phase_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = load_canonical_orm_metadata()
    monkeypatch.setattr(
        checker, "_read_alembic_head", lambda connection: checker.EXPECTED_ALEMBIC_HEAD
    )
    monkeypatch.setattr(
        checker,
        "_reflect_physical_table_keys",
        lambda connection: checker.EXPECTED_PHYSICAL_TABLE_KEYS,
    )

    def fake_ops(
        connection: Connection,
        target_metadata: MetaData,
        *,
        admitted: bool,
    ) -> ops.UpgradeOps:
        del connection, target_metadata
        return ops.UpgradeOps(ops=[]) if admitted else _raw_expected_tree()

    monkeypatch.setattr(checker, "_produce_upgrade_ops", fake_ops)
    first = checker.evaluate_alembic_autogenerate_completeness(
        _fake_connection("postgresql"),
        metadata,
    )
    second = checker.evaluate_alembic_autogenerate_completeness(
        _fake_connection("postgresql"),
        metadata,
    )

    assert first == second
    assert first.material_digest.startswith("sha256:")
    assert first.result == "fail"
    assert first.reason_codes == ("phase_b_postgresql_descriptor_validation_required",)
    assert first.extension_validation == "not_evaluated_phase_b"
    assert first.rls_policy_validation == "not_evaluated_phase_b"
    assert first.check_validation == "not_evaluated_phase_b"
    assert first.sequence_validation == "not_evaluated_phase_b"
    assert first.unknown_objects == ()
    assert first.unknown_operations == ()


def test_material_digest_binds_epoch_inventories_and_validation_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata_keys = frozenset(load_canonical_orm_metadata().tables)
    raw_records, unknown, reasons = (
        checker._classify_operation_tree(  # pylint: disable=protected-access
            _raw_expected_tree(),
            rail="raw",
        )
    )
    assert unknown == ()
    assert reasons == ()
    baseline = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
    )

    original_boundary = checker.CLAIM_BOUNDARY
    monkeypatch.setattr(checker, "CLAIM_BOUNDARY", original_boundary + ";changed=true")
    epoch_changed = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
    )
    monkeypatch.setattr(checker, "CLAIM_BOUNDARY", original_boundary)

    original_indexes = checker.MIGRATION_OWNED_INDEX_KEYS
    monkeypatch.setattr(
        checker,
        "MIGRATION_OWNED_INDEX_KEYS",
        original_indexes | {"ix_phase_a_digest_probe"},
    )
    inventory_changed = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
    )
    monkeypatch.setattr(checker, "MIGRATION_OWNED_INDEX_KEYS", original_indexes)

    status_changed = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
        extension_validation=checker.VALIDATION_PASSED,
    )

    assert (
        len(
            {
                baseline.material_digest,
                epoch_changed.material_digest,
                inventory_changed.material_digest,
                status_changed.material_digest,
            }
        )
        == 4
    )


def test_pass_requires_all_zero_and_validated_postconditions() -> None:
    metadata_keys = frozenset(load_canonical_orm_metadata().tables)
    raw_records, unknown, reasons = (
        checker._classify_operation_tree(  # pylint: disable=protected-access
            _raw_expected_tree(),
            rail="raw",
        )
    )
    assert unknown == ()
    assert reasons == ()
    validated = {
        "extension_validation": checker.VALIDATION_PASSED,
        "rls_policy_validation": checker.VALIDATION_PASSED,
        "check_validation": checker.VALIDATION_PASSED,
        "sequence_validation": checker.VALIDATION_PASSED,
    }
    clean = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
        **validated,
    )
    unknown_object = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
        unknown_objects=("physical_extra:public.shadow",),
        **validated,
    )
    unknown_operation = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
        unknown_operations=("upgrade/9:FutureOp:public.-:-",),
        **validated,
    )
    admitted_operation = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
        admitted_operations=(raw_records[0],),
        **validated,
    )
    pending_validation = checker._make_report(  # pylint: disable=protected-access
        alembic_head=checker.EXPECTED_ALEMBIC_HEAD,
        metadata_keys=metadata_keys,
        raw_operations=raw_records,
    )

    assert clean.result == "pass"
    assert unknown_object.result == "fail"
    assert unknown_operation.result == "fail"
    assert admitted_operation.result == "fail"
    assert pending_validation.result == "fail"


def test_report_never_serializes_connection_failure_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = "-".join(("synthetic", "redaction", "probe"))
    carrier = "".join(("postgresql://", "owner:", marker, "@", "private.invalid", "/pulseplate"))

    def fail_head(connection: Connection) -> str:
        del connection
        raise RuntimeError(carrier)

    monkeypatch.setattr(checker, "_read_alembic_head", fail_head)
    report = checker.evaluate_alembic_autogenerate_completeness(
        _fake_connection("postgresql"),
        load_canonical_orm_metadata(),
    )
    serialized = report.to_json()

    assert report.reason_codes == ("alembic_head_read_failed",)
    assert marker not in serialized
    assert "private.invalid" not in serialized
    assert carrier not in serialized


def test_checker_owns_no_database_lifecycle_environment_or_subprocess() -> None:
    source = CHECKER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CHECKER_PATH))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}

    assert "os" not in imported_modules
    assert "subprocess" not in imported_modules
    assert "sqlalchemy.engine.create" not in imported_from
    assert "DATABASE_URL" not in source
    assert "create_engine" not in source
    assert "engine_from_config" not in source
    assert "docker" not in source.lower()
    assert "psql" not in source.lower()
    assert "drop database" not in source.lower()

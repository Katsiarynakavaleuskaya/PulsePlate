"""Focused tests for bounded Alembic autogenerate admission."""

from __future__ import annotations

import ast
from dataclasses import replace
import inspect as python_inspect
from pathlib import Path
from types import SimpleNamespace
from typing import cast
import warnings

from alembic.operations import ops
import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.engine import Connection

import scripts.ci.check_alembic_autogenerate_completeness as checker
from core.db import Base, load_canonical_orm_metadata
from core.db_alembic_comparison import (
    AUTOGENERATE_EXEMPT_TABLE_ROOTS,
    include_autogenerate_object,
    proven_autogenerate_default_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / "alembic" / "env.py"
COMPARISON_PATH = REPO_ROOT / "core" / "db_alembic_comparison.py"
REMOVED_OWNERSHIP_PATH = REPO_ROOT / "core" / "db_alembic_ownership.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "ci" / "check_alembic_autogenerate_completeness.py"
HEAD = "202608290001"


def _fake_connection(
    *,
    dialect_name: str = "postgresql",
    default_schema_name: str = "public",
) -> Connection:
    return cast(
        Connection,
        SimpleNamespace(
            dialect=SimpleNamespace(
                name=dialect_name,
                default_schema_name=default_schema_name,
            )
        ),
    )


def _raw_tree(
    leaves: tuple[checker.OperationLeaf, ...] = checker.EXPECTED_RAW_LEAVES,
) -> ops.UpgradeOps:
    children: list[ops.MigrateOperation] = []
    index_leaves_by_table: dict[str, list[ops.MigrateOperation]] = {}
    for leaf in leaves:
        if leaf.operation == "DropTableOp":
            children.append(ops.DropTableOp(leaf.table_name, schema=leaf.schema))
        elif leaf.operation == "DropIndexOp":
            index_leaves_by_table.setdefault(leaf.table_name, []).append(
                ops.DropIndexOp(
                    leaf.object_name,
                    table_name=leaf.table_name,
                    schema=leaf.schema,
                )
            )
        else:
            children.append(ops.ExecuteSQLOp("SELECT 1"))
    children.extend(
        ops.ModifyTableOps(table_name, table_leaves, schema="public")
        for table_name, table_leaves in sorted(index_leaves_by_table.items())
    )
    return ops.UpgradeOps(children)


def _public_table_names() -> tuple[str, ...]:
    metadata_names = tuple(table.name for table in load_canonical_orm_metadata().tables.values())
    exempt_names = tuple(name for _, name in AUTOGENERATE_EXEMPT_TABLE_ROOTS)
    return tuple(sorted((*metadata_names, *exempt_names, "alembic_version")))


def _patch_valid_evaluator_inputs(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    admitted_calls: list[bool] = []
    monkeypatch.setattr(checker, "_migration_head", lambda: HEAD)
    monkeypatch.setattr(checker, "_database_head", lambda connection: HEAD)
    monkeypatch.setattr(
        checker,
        "inspect",
        lambda connection: SimpleNamespace(get_table_names=lambda *, schema: _public_table_names()),
    )
    monkeypatch.setattr(checker, "_validate_descriptors", lambda connection: ((), ()))

    def produce(
        connection: Connection,
        target_metadata: MetaData,
        *,
        admitted: bool,
    ) -> tuple[ops.UpgradeOps, tuple[str, ...]]:
        del connection, target_metadata
        admitted_calls.append(admitted)
        return (ops.UpgradeOps([]) if admitted else _raw_tree(), ())

    monkeypatch.setattr(checker, "_produce_upgrade_ops", produce)
    return admitted_calls


def _patch_valid_descriptor_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checker, "_read_columns", lambda connection: checker.EXPECTED_COLUMNS)
    monkeypatch.setattr(
        checker,
        "_read_primary_keys",
        lambda connection: checker.EXPECTED_PRIMARY_KEYS,
    )
    monkeypatch.setattr(
        checker,
        "_read_foreign_keys",
        lambda connection: checker.EXPECTED_FOREIGN_KEYS,
    )
    monkeypatch.setattr(checker, "_read_named_constraints", lambda connection: ())
    monkeypatch.setattr(checker, "_read_indexes", lambda connection: checker.EXPECTED_INDEXES)
    monkeypatch.setattr(
        checker,
        "_read_ownership_rows",
        lambda connection: checker.EXPECTED_OWNERSHIP_ROWS,
    )
    monkeypatch.setattr(checker, "_read_rls", lambda connection: checker.EXPECTED_RLS)
    monkeypatch.setattr(checker, "_read_owned_sequences", lambda connection: ())


def test_env_wires_canonical_metadata_and_comparison_policy_in_both_modes() -> None:
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
        assert isinstance(keywords["compare_server_default"], ast.Name)
        assert keywords["compare_server_default"].id == "compare_postgresql_server_default"
        assert isinstance(keywords["include_object"], ast.Name)
        assert keywords["include_object"].id == "include_autogenerate_object"

    assert "target_metadata = load_canonical_orm_metadata()" in source
    assert "proven_autogenerate_default_schema" in source
    assert "core.db_alembic_ownership" not in source
    assert "scripts.ci.check_alembic_autogenerate_completeness" not in source
    assert load_canonical_orm_metadata() is Base.metadata


def test_online_schema_proof_is_scoped_only_to_autogenerate_execution() -> None:
    source = ENV_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ENV_PATH))
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_is_autogenerate_execution"
    )
    online = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_migrations_online"
    )
    helper_source = ast.get_source_segment(source, helper)
    online_source = ast.get_source_segment(source, online)

    assert helper_source is not None
    assert 'context.get_context().opts.get("revision_context")' in helper_source
    assert 'getattr(revision_context, "command_args", None)' in helper_source
    assert 'command_args.get("autogenerate") is True' in helper_source
    assert online_source is not None
    assert online_source.index("context.configure(") < online_source.index(
        "_is_autogenerate_execution()"
    )
    assert (
        'connection.dialect.name == "postgresql" and _is_autogenerate_execution()' in online_source
    )
    assert online_source.count("proven_autogenerate_default_schema(") == 1
    assert online_source.count("else nullcontext()") == 1


def test_comparison_module_is_the_only_exact_policy_owner() -> None:
    source = COMPARISON_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(COMPARISON_PATH))
    assigned_names = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert AUTOGENERATE_EXEMPT_TABLE_ROOTS == frozenset(
        {
            ("public", "foods"),
            ("public", "pulseplate_migration_ownership"),
            ("public", "restaurant_chains"),
            ("public", "restaurant_menu_items"),
        }
    )
    assert "AUTOGENERATE_EXEMPT_TABLE_ROOTS" in assigned_names
    assert "include_autogenerate_object" in function_names
    assert not REMOVED_OWNERSHIP_PATH.exists()
    callback_source = python_inspect.getsource(include_autogenerate_object)
    assert "startswith" not in callback_source
    assert "fnmatch" not in callback_source
    assert "regex" not in callback_source


@pytest.mark.parametrize("schema", ["public"])
@pytest.mark.parametrize("schema_name,table_name", sorted(AUTOGENERATE_EXEMPT_TABLE_ROOTS))
def test_callback_excludes_only_exact_explicit_public_roots(
    schema: str,
    schema_name: str,
    table_name: str,
) -> None:
    assert schema_name == schema
    table = Table(table_name, MetaData(), Column("id", Integer), schema=schema)

    assert include_autogenerate_object(table, table_name, "table", True, None) is False
    assert include_autogenerate_object(table, table_name, "table", False, None) is True
    assert include_autogenerate_object(table, table_name, "column", True, None) is True
    assert include_autogenerate_object(table, table_name, "table", True, table) is True


def test_callback_normalizes_none_only_inside_proven_public_scope() -> None:
    implicit = Table("foods", MetaData(), Column("id", Integer))
    private = Table("foods", MetaData(), Column("id", Integer), schema="private")
    unknown = Table("foods_archive", MetaData(), Column("id", Integer), schema="public")

    assert include_autogenerate_object(implicit, "foods", "table", True, None) is True
    with proven_autogenerate_default_schema("public"):
        assert include_autogenerate_object(implicit, "foods", "table", True, None) is False
        assert include_autogenerate_object(implicit, None, "table", True, None) is True
        assert include_autogenerate_object(private, "foods", "table", True, None) is True
        assert include_autogenerate_object(unknown, "foods_archive", "table", True, None) is True
    with pytest.raises(ValueError, match="autogenerate_default_schema_not_public"):
        with proven_autogenerate_default_schema("private"):
            pytest.fail("invalid default schema scope must not open")


def test_semantic_tree_counts_only_supported_leaves() -> None:
    leaves, reasons, observed = checker._semantic_leaves(  # pylint: disable=protected-access
        _raw_tree(),
        default_schema_name="public",
    )

    assert leaves == checker.EXPECTED_RAW_LEAVES
    assert len(leaves) == 15
    assert sum(leaf.operation == "DropTableOp" for leaf in leaves) == 4
    assert sum(leaf.operation == "DropIndexOp" for leaf in leaves) == 11
    assert reasons == ()
    assert observed == ()


def test_raw_tree_rejects_extra_empty_modify_table_container() -> None:
    raw_root = _raw_tree()
    raw_root.ops.append(ops.ModifyTableOps("foods", [], schema="public"))

    leaves, reasons, observed = checker._semantic_leaves(  # pylint: disable=protected-access
        raw_root,
        default_schema_name="public",
    )

    assert leaves == checker.EXPECTED_RAW_LEAVES
    assert reasons == ("autogenerate_modify_table_empty",)
    assert observed == ("container:ModifyTableOps:public.foods:empty",)


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_raw_leaf_inventory_rejects_missing_extra_and_duplicate(mutation: str) -> None:
    leaves = list(checker.EXPECTED_RAW_LEAVES)
    if mutation == "missing":
        leaves.pop()
    elif mutation == "extra":
        leaves.append(checker.OperationLeaf("DropTableOp", "public", "unknown", "unknown"))
    else:
        leaves.append(leaves[0])

    reasons, observed = checker._validate_raw_leaves(  # pylint: disable=protected-access
        tuple(leaves)
    )

    assert f"raw_leaf_inventory_{mutation}" in reasons
    assert observed


def test_unknown_semantic_leaf_fails_closed() -> None:
    tree = ops.UpgradeOps([ops.ExecuteSQLOp("SELECT 1")])

    leaves, reasons, observed = checker._semantic_leaves(  # pylint: disable=protected-access
        tree,
        default_schema_name="public",
    )

    assert leaves == ()
    assert reasons == ("autogenerate_operation_unclassified",)
    assert observed == ("operation:ExecuteSQLOp",)


def test_nested_supported_container_is_structurally_rejected_but_leaves_recurse() -> None:
    leaf = checker.OperationLeaf("DropTableOp", "public", "foods", "foods")
    assert leaf in checker.EXPECTED_RAW_LEAVES
    nested = ops.UpgradeOps(
        [ops.UpgradeOps([ops.DropTableOp(leaf.table_name, schema=leaf.schema)])]
    )

    leaves, reasons, observed = checker._semantic_leaves(  # pylint: disable=protected-access
        nested,
        default_schema_name="public",
    )

    assert leaves == (leaf,)
    assert reasons == ("autogenerate_container_topology_invalid",)
    assert observed == ("container:UpgradeOps:nested",)


@pytest.mark.parametrize(
    ("parent_schema", "parent_table", "child_schema", "child_table"),
    (
        ("public", "foods", "public", "restaurant_chains"),
        ("private", "foods", "public", "foods"),
    ),
)
def test_drop_index_leaf_must_match_parent_table_root(
    parent_schema: str,
    parent_table: str,
    child_schema: str,
    child_table: str,
) -> None:
    root = ops.UpgradeOps(
        [
            ops.ModifyTableOps(
                parent_table,
                [
                    ops.DropIndexOp(
                        "ix_foods_gtin",
                        table_name=child_table,
                        schema=child_schema,
                    )
                ],
                schema=parent_schema,
            )
        ]
    )

    leaves, reasons, observed = checker._semantic_leaves(  # pylint: disable=protected-access
        root,
        default_schema_name="public",
    )

    assert leaves == (
        checker.OperationLeaf("DropIndexOp", child_schema, child_table, "ix_foods_gtin"),
    )
    assert reasons == ("autogenerate_drop_index_parent_mismatch",)
    assert observed == (
        "operation:DropIndexOp:"
        f"parent={parent_schema}.{parent_table}:child={child_schema}.{child_table}",
    )


def test_clean_evaluator_returns_only_bounded_pass_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_valid_evaluator_inputs(monkeypatch)

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    assert report.result == "pass"
    assert report.claim == checker.ADMISSION_RESULT_CLAIM
    assert report.migration_head == HEAD
    assert report.database_head == HEAD
    assert report.default_schema_name == "public"
    assert report.descriptor_validation == "passed"
    assert report.raw_leaf_operations == checker.EXPECTED_RAW_LEAVES
    assert report.admitted_leaf_operations == ()
    assert report.warning_categories == ()
    assert report.reason_codes == ()
    assert calls == [False, True]
    assert "production" not in report.to_json().lower()
    assert "deployment" not in report.to_json().lower()


def test_clone_metadata_fails_before_connection_use() -> None:
    clone = MetaData()
    Table("users", clone, Column("id", Integer))

    report = checker.evaluate_alembic_autogenerate_admission(
        cast(Connection, object()),
        clone,
    )

    assert report.result == "fail"
    assert report.claim is None
    assert report.reason_codes == ("canonical_metadata_identity_mismatch",)


def test_invalid_default_schema_fails_before_head_or_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        checker,
        "_migration_head",
        lambda: pytest.fail("head must not be read"),
    )

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(default_schema_name="private"),
        load_canonical_orm_metadata(),
    )

    assert report.reason_codes == ("default_schema_not_public",)


def test_non_singleton_script_head_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_valid_evaluator_inputs(monkeypatch)
    monkeypatch.setattr(checker, "_migration_head", lambda: None)

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    assert report.reason_codes == ("migration_head_not_singleton",)
    assert report.database_head is None


def test_database_head_mismatch_fails_before_census(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_valid_evaluator_inputs(monkeypatch)
    monkeypatch.setattr(checker, "_database_head", lambda connection: "older-head")
    monkeypatch.setattr(
        checker,
        "inspect",
        lambda connection: pytest.fail("census must not run"),
    )

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    assert report.reason_codes == ("database_head_mismatch",)
    assert report.database_head == "older-head"


def test_public_census_rejects_missing_exempt_and_unknown_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_valid_evaluator_inputs(monkeypatch)
    table_names = set(_public_table_names())
    table_names.remove("foods")
    table_names.add("future_table")
    monkeypatch.setattr(
        checker,
        "inspect",
        lambda connection: SimpleNamespace(
            get_table_names=lambda *, schema: tuple(sorted(table_names))
        ),
    )

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    assert report.reason_codes == ("public_table_root_partition_mismatch",)
    assert "public_missing:public.foods" in report.observed_identities
    assert "public_extra:public.future_table" in report.observed_identities


def test_raw_warning_blocks_descriptors_and_admitted_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_valid_evaluator_inputs(monkeypatch)

    def warning_produce(
        connection: Connection,
        target_metadata: MetaData,
        *,
        admitted: bool,
    ) -> tuple[ops.UpgradeOps, tuple[str, ...]]:
        del connection, target_metadata
        calls.append(admitted)
        return _raw_tree(), ("SAWarning",)

    monkeypatch.setattr(checker, "_produce_upgrade_ops", warning_produce)
    monkeypatch.setattr(
        checker,
        "_validate_descriptors",
        lambda connection: pytest.fail("descriptors must not run"),
    )

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    assert report.reason_codes == ("raw_autogenerate_warning",)
    assert report.warning_categories == ("raw:SAWarning",)
    assert calls == [False]


def test_migration_context_configuration_warning_is_captured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def configure(connection: Connection, *, opts: dict[str, object]) -> object:
        del connection, opts
        warnings.warn("configuration warning", UserWarning, stacklevel=1)
        return object()

    monkeypatch.setattr(checker.MigrationContext, "configure", configure)
    monkeypatch.setattr(
        checker,
        "produce_migrations",
        lambda context, metadata: SimpleNamespace(upgrade_ops=ops.UpgradeOps([])),
    )

    root, categories = checker._produce_upgrade_ops(  # pylint: disable=protected-access
        _fake_connection(),
        MetaData(),
        admitted=False,
    )

    assert root.is_empty()
    assert categories == ("UserWarning",)


def test_descriptor_failure_blocks_admitted_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_valid_evaluator_inputs(monkeypatch)
    monkeypatch.setattr(
        checker,
        "_validate_descriptors",
        lambda connection: (
            ("migration_index_descriptor_mismatch",),
            ("descriptor:indexes",),
        ),
    )

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    assert report.descriptor_validation == "failed"
    assert report.reason_codes == ("migration_index_descriptor_mismatch",)
    assert calls == [False]


@pytest.mark.parametrize("admitted_failure", ["warning", "operation"])
def test_admitted_comparison_rejects_warning_and_nonempty_operation(
    monkeypatch: pytest.MonkeyPatch,
    admitted_failure: str,
) -> None:
    calls = _patch_valid_evaluator_inputs(monkeypatch)

    def produce(
        connection: Connection,
        target_metadata: MetaData,
        *,
        admitted: bool,
    ) -> tuple[ops.UpgradeOps, tuple[str, ...]]:
        del connection, target_metadata
        calls.append(admitted)
        if not admitted:
            return _raw_tree(), ()
        if admitted_failure == "warning":
            return ops.UpgradeOps([]), ("SAWarning",)
        return ops.UpgradeOps([ops.DropTableOp("foods", schema="public")]), ()

    monkeypatch.setattr(checker, "_produce_upgrade_ops", produce)

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    expected_reason = (
        "admitted_autogenerate_warning"
        if admitted_failure == "warning"
        else "admitted_operation_tree_not_empty"
    )
    assert report.reason_codes == (expected_reason,)
    assert calls == [False, True]
    if admitted_failure == "warning":
        assert report.warning_categories == ("admitted:SAWarning",)
    else:
        assert report.admitted_leaf_operations == (
            checker.OperationLeaf("DropTableOp", "public", "foods", "foods"),
        )


def test_admitted_comparison_rejects_empty_modify_table_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_valid_evaluator_inputs(monkeypatch)

    def produce(
        connection: Connection,
        target_metadata: MetaData,
        *,
        admitted: bool,
    ) -> tuple[ops.UpgradeOps, tuple[str, ...]]:
        del connection, target_metadata
        calls.append(admitted)
        if not admitted:
            return _raw_tree(), ()
        return ops.UpgradeOps([ops.ModifyTableOps("foods", [], schema="public")]), ()

    monkeypatch.setattr(checker, "_produce_upgrade_ops", produce)

    report = checker.evaluate_alembic_autogenerate_admission(
        _fake_connection(),
        load_canonical_orm_metadata(),
    )

    assert report.reason_codes == (
        "admitted_operation_tree_not_empty",
        "autogenerate_modify_table_empty",
    )
    assert report.admitted_leaf_operations == ()
    assert calls == [False, True]


@pytest.mark.parametrize(
    ("reader_name", "replacement", "reason_code"),
    (
        (
            "_read_columns",
            (replace(checker.EXPECTED_COLUMNS[0], formatted_type="integer"),)
            + checker.EXPECTED_COLUMNS[1:],
            "migration_column_descriptor_mismatch",
        ),
        (
            "_read_columns",
            (replace(checker.EXPECTED_COLUMNS[0], nullable=True),) + checker.EXPECTED_COLUMNS[1:],
            "migration_column_descriptor_mismatch",
        ),
        (
            "_read_columns",
            (replace(checker.EXPECTED_COLUMNS[0], default="unexpected"),)
            + checker.EXPECTED_COLUMNS[1:],
            "migration_column_descriptor_mismatch",
        ),
        (
            "_read_columns",
            (
                checker.EXPECTED_COLUMNS[1],
                checker.EXPECTED_COLUMNS[0],
                *checker.EXPECTED_COLUMNS[2:],
            ),
            "migration_column_descriptor_mismatch",
        ),
        (
            "_read_columns",
            (replace(checker.EXPECTED_COLUMNS[0], name="renamed_column"),)
            + checker.EXPECTED_COLUMNS[1:],
            "migration_column_descriptor_mismatch",
        ),
        (
            "_read_columns",
            (replace(checker.EXPECTED_COLUMNS[0], identity="a"),) + checker.EXPECTED_COLUMNS[1:],
            "migration_column_descriptor_mismatch",
        ),
        (
            "_read_columns",
            (replace(checker.EXPECTED_COLUMNS[0], generated="s"),) + checker.EXPECTED_COLUMNS[1:],
            "migration_column_descriptor_mismatch",
        ),
        (
            "_read_primary_keys",
            checker.EXPECTED_PRIMARY_KEYS[:-1],
            "migration_primary_key_mismatch",
        ),
        (
            "_read_foreign_keys",
            (
                replace(checker.EXPECTED_FOREIGN_KEYS[0], on_delete="NO ACTION"),
                checker.EXPECTED_FOREIGN_KEYS[1],
            ),
            "migration_foreign_key_mismatch",
        ),
        (
            "_read_foreign_keys",
            (
                checker.EXPECTED_FOREIGN_KEYS[0],
                replace(checker.EXPECTED_FOREIGN_KEYS[1], on_delete="CASCADE"),
            ),
            "migration_foreign_key_mismatch",
        ),
        (
            "_read_named_constraints",
            (checker.NamedConstraintDescriptor("foods", "c", "unexpected", "CHECK (true)"),),
            "migration_unique_or_check_constraint_mismatch",
        ),
        (
            "_read_indexes",
            checker.EXPECTED_INDEXES[:-1],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], opclasses=("text_pattern_ops",)),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            checker.EXPECTED_INDEXES
            + (replace(checker.EXPECTED_INDEXES[-1], name="ix_unexpected"),),
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], name="ix_renamed"),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], access_method="hash"),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], included_columns=("source",)),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], key_options=(1,)),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], unique=True),) + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], valid=False),) + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], ready=False),) + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], live=False),) + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], nulls_not_distinct=True),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], predicate="brand IS NOT NULL"),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], expression="lower(brand)"),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_indexes",
            (replace(checker.EXPECTED_INDEXES[0], constraint_owner="unexpected_owner"),)
            + checker.EXPECTED_INDEXES[1:],
            "migration_index_descriptor_mismatch",
        ),
        (
            "_read_ownership_rows",
            checker.EXPECTED_OWNERSHIP_ROWS[:-1],
            "migration_ownership_registry_mismatch",
        ),
        (
            "_read_ownership_rows",
            checker.EXPECTED_OWNERSHIP_ROWS + (("209901010001", "table", "future", "future"),),
            "migration_ownership_registry_mismatch",
        ),
        (
            "_read_ownership_rows",
            (("209901010001", *checker.EXPECTED_OWNERSHIP_ROWS[0][1:]),)
            + checker.EXPECTED_OWNERSHIP_ROWS[1:],
            "migration_ownership_registry_mismatch",
        ),
        (
            "_read_rls",
            (replace(checker.EXPECTED_RLS[0], enabled=True),) + checker.EXPECTED_RLS[1:],
            "migration_rls_or_policy_mismatch",
        ),
        (
            "_read_rls",
            (replace(checker.EXPECTED_RLS[0], forced=True),) + checker.EXPECTED_RLS[1:],
            "migration_rls_or_policy_mismatch",
        ),
        (
            "_read_rls",
            (replace(checker.EXPECTED_RLS[0], policy_count=1),) + checker.EXPECTED_RLS[1:],
            "migration_rls_or_policy_mismatch",
        ),
        (
            "_read_owned_sequences",
            ("foods_id_seq",),
            "migration_owned_sequence_present",
        ),
    ),
)
def test_descriptor_surfaces_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    reader_name: str,
    replacement: object,
    reason_code: str,
) -> None:
    _patch_valid_descriptor_readers(monkeypatch)
    monkeypatch.setattr(checker, reader_name, lambda connection: replacement)

    reasons, observed = checker._validate_descriptors(  # pylint: disable=protected-access
        _fake_connection()
    )

    assert reason_code in reasons
    assert observed


def test_checker_has_no_database_lifecycle_or_external_execution() -> None:
    source = CHECKER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CHECKER_PATH))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert "subprocess" not in imported_modules
    assert "os" not in imported_modules
    assert "sqlalchemy.create_engine" not in source
    assert "create_engine(" not in source
    assert "DATABASE_URL" not in source
    assert "DROP DATABASE" not in source
    assert "CREATE DATABASE" not in source
    assert "CLAIM_BOUNDARY" not in source
    assert "material_digest" not in source
    assert "EXPECTED_ALEMBIC_HEAD" not in source
    assert "CANONICAL_MAPPED_TABLE_KEYS" not in source
    assert "EXPECTED_EXTENSIONS" not in source
    assert "EXPECTED_CRITICAL_CHECKS" not in source

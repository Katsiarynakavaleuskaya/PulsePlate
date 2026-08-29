"""Expected-red contract for the finite PostgreSQL ORM/Alembic drift lane.

This file is authored by the ordered security-auditor pass.  It freezes the
exact 23-leaf lower-bound inventory discovered on a fresh PostgreSQL database
before the backend writer reconciles models and authors the sole forward
revision.  Unknown leaves and unresolved comparison warnings remain terminal.
"""

from __future__ import annotations

from dataclasses import dataclass
import ast
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Literal

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import JSON, Column, Integer, Table, Text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.dialects.postgresql.base import ischema_names

from app.models import (
    PaywallExposureLedger,
    RAGFeedback,
    UserKnowledge,
    VipLlmMonthlyUsage,
    WeeklyPlan,
)
from core.models import FoodItem, Meal, Recipe

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
BASE_ALEMBIC_HEAD = "202608270001"
COMPARISON_HELPER_MODULE = "core.db_alembic_comparison"

DriftClassification = Literal["TRUE_MODEL_DRIFT", "TRUE_SCHEMA_DRIFT"]


@dataclass(frozen=True, slots=True)
class DriftLeaf:
    """Exact operation identity frozen by the pre-fix PostgreSQL probe."""

    leaf_id: int
    classification: DriftClassification
    operation: str
    object_key: str


EXPECTED_DRIFT_LEAVES = (
    DriftLeaf(
        1,
        "TRUE_SCHEMA_DRIFT",
        "DropIndexOp",
        "public.analyzer_state.uq_analyzer_state_user_key",
    ),
    DriftLeaf(
        2,
        "TRUE_SCHEMA_DRIFT",
        "CreateUniqueConstraintOp",
        "public.analyzer_state.uq_analyzer_state_user_key",
    ),
    DriftLeaf(
        3,
        "TRUE_SCHEMA_DRIFT",
        "DropIndexOp",
        "public.day_plans.ix_day_plans_user_date",
    ),
    DriftLeaf(
        4,
        "TRUE_SCHEMA_DRIFT",
        "CreateUniqueConstraintOp",
        "public.day_plans.uq_day_plans_user_date",
    ),
    DriftLeaf(
        5,
        "TRUE_MODEL_DRIFT",
        "AlterColumnOp",
        "public.food_items.protein_g_per_100g",
    ),
    DriftLeaf(
        6,
        "TRUE_MODEL_DRIFT",
        "AlterColumnOp",
        "public.food_items.fat_g_per_100g",
    ),
    DriftLeaf(
        7,
        "TRUE_MODEL_DRIFT",
        "AlterColumnOp",
        "public.food_items.carbs_g_per_100g",
    ),
    DriftLeaf(
        8,
        "TRUE_MODEL_DRIFT",
        "AlterColumnOp",
        "public.food_items.fiber_g_per_100g",
    ),
    DriftLeaf(9, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.meals.protein_g"),
    DriftLeaf(10, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.meals.fat_g"),
    DriftLeaf(11, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.meals.carbs_g"),
    DriftLeaf(12, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.meals.fiber_g"),
    DriftLeaf(
        13,
        "TRUE_MODEL_DRIFT",
        "AlterColumnOp",
        "public.paywall_exposure_ledger.metadata_json",
    ),
    DriftLeaf(
        14,
        "TRUE_MODEL_DRIFT",
        "DropIndexOp",
        "public.rag_feedback.idx_rag_feedback_user_id",
    ),
    DriftLeaf(
        15,
        "TRUE_MODEL_DRIFT",
        "CreateIndexOp",
        "public.rag_feedback.ix_rag_feedback_user_id",
    ),
    DriftLeaf(16, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.recipes.protein_g"),
    DriftLeaf(17, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.recipes.fat_g"),
    DriftLeaf(18, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.recipes.carbs_g"),
    DriftLeaf(19, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.recipes.fiber_g"),
    DriftLeaf(20, "TRUE_MODEL_DRIFT", "AlterColumnOp", "public.recipes.servings"),
    DriftLeaf(
        21,
        "TRUE_MODEL_DRIFT",
        "CreateIndexOp",
        "public.user_knowledge.ix_user_knowledge_user_id",
    ),
    DriftLeaf(
        22,
        "TRUE_MODEL_DRIFT",
        "AlterColumnOp",
        "public.vip_llm_monthly_usage.used_requests",
    ),
    DriftLeaf(
        23,
        "TRUE_MODEL_DRIFT",
        "DropIndexOp",
        "public.weekly_plans.ix_weekly_plans_user_date",
    ),
)


def _leaf_identity(leaf: DriftLeaf) -> tuple[str, str]:
    return leaf.operation, leaf.object_key


def require_exact_drift_inventory(observed: tuple[DriftLeaf, ...]) -> None:
    """Reject an omitted, duplicated, reclassified, or unknown 24th leaf."""

    expected_by_id = {leaf.leaf_id: leaf for leaf in EXPECTED_DRIFT_LEAVES}
    observed_by_id = {leaf.leaf_id: leaf for leaf in observed}
    if len(observed_by_id) != len(observed):
        raise ValueError("duplicate_drift_leaf_id")
    if observed_by_id != expected_by_id:
        raise ValueError("drift_inventory_mismatch")
    identities = {_leaf_identity(leaf) for leaf in observed}
    if len(identities) != len(observed):
        raise ValueError("duplicate_drift_leaf_identity")


def _server_default_text(model: type[object], column_name: str) -> str | None:
    table = getattr(model, "__table__")
    assert isinstance(table, Table)
    column = table.c[column_name]
    default = column.server_default
    return None if default is None else str(default.arg)


def _index_signature(model: type[object]) -> set[tuple[str, tuple[str, ...], bool]]:
    table = getattr(model, "__table__")
    assert isinstance(table, Table)
    return {
        (str(index.name), tuple(column.name for column in index.columns), bool(index.unique))
        for index in table.indexes
    }


def _load_comparison_helper() -> object:
    if importlib.util.find_spec(COMPARISON_HELPER_MODULE) is None:
        pytest.fail("comparison_helper_missing:core.db_alembic_comparison")
    return importlib.import_module(COMPARISON_HELPER_MODULE)


def _operation_calls(function: ast.FunctionDef) -> list[tuple[str, str | None, str | None]]:
    calls: list[tuple[str, str | None, str | None]] = []
    for node in ast.walk(function):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
        ):
            continue
        first_arg = None
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            first_arg = node.args[0].value
        table_name = next(
            (
                keyword.value.value
                for keyword in node.keywords
                if keyword.arg == "table_name"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ),
            None,
        )
        calls.append((node.func.attr, first_arg, table_name))
    return calls


def test_frozen_inventory_is_exact_disjoint_and_complete_for_observed_lower_bound() -> None:
    require_exact_drift_inventory(EXPECTED_DRIFT_LEAVES)

    assert tuple(leaf.leaf_id for leaf in EXPECTED_DRIFT_LEAVES) == tuple(range(1, 24))
    assert sum(leaf.classification == "TRUE_MODEL_DRIFT" for leaf in EXPECTED_DRIFT_LEAVES) == 19
    assert sum(leaf.classification == "TRUE_SCHEMA_DRIFT" for leaf in EXPECTED_DRIFT_LEAVES) == 4
    assert {
        leaf.leaf_id for leaf in EXPECTED_DRIFT_LEAVES if leaf.classification == "TRUE_MODEL_DRIFT"
    }.isdisjoint(
        {
            leaf.leaf_id
            for leaf in EXPECTED_DRIFT_LEAVES
            if leaf.classification == "TRUE_SCHEMA_DRIFT"
        }
    )


def test_unknown_24th_leaf_and_reclassification_fail_closed() -> None:
    unknown = DriftLeaf(24, "TRUE_MODEL_DRIFT", "CreateIndexOp", "public.extra.ix_extra")
    with pytest.raises(ValueError, match="drift_inventory_mismatch"):
        require_exact_drift_inventory(EXPECTED_DRIFT_LEAVES + (unknown,))

    reclassified = list(EXPECTED_DRIFT_LEAVES)
    reclassified[0] = DriftLeaf(
        1,
        "TRUE_MODEL_DRIFT",
        reclassified[0].operation,
        reclassified[0].object_key,
    )
    with pytest.raises(ValueError, match="drift_inventory_mismatch"):
        require_exact_drift_inventory(tuple(reclassified))


def test_json_default_comparator_is_exact_typed_and_non_suppressing() -> None:
    helper = _load_comparison_helper()
    comparator = getattr(helper, "compare_postgresql_server_default", None)
    assert callable(comparator), "comparison_helper_api_missing"
    assert tuple(inspect.signature(comparator).parameters) == (
        "context",
        "inspected_column",
        "metadata_column",
        "inspected_default",
        "metadata_default",
        "rendered_metadata_default",
    )

    inspected_json = Column("payload", postgresql.JSON())
    metadata_json = Column("payload", JSON())
    assert comparator(None, inspected_json, metadata_json, "'{}'::json", None, "{}") is False
    for raw_payload in ("[1,2.0,3e4000]", "true", "false", "1", "1.0", "1e999999"):
        assert (
            comparator(
                None,
                inspected_json,
                metadata_json,
                f"'{raw_payload}'::json",
                None,
                raw_payload,
            )
            is False
        )
    equal_pairs = (
        ("{}", "{}"),
        ("true", "true"),
        ("false", "false"),
        (
            '{"outer":{"flag":true,"items":[1,2.0,3e4000]}}',
            '{"outer":{"items":[1,2.0,3e4000],"flag":true}}',
        ),
        (
            "123456789012345678901234567890.12345678901234567890",
            "123456789012345678901234567890.12345678901234567890",
        ),
        ("1", "1.0"),
        ("1", "10e-1"),
        ("1e10000", "10e9999"),
    )
    for inspected_payload, metadata_payload in equal_pairs:
        assert (
            comparator(
                None,
                inspected_json,
                metadata_json,
                f"'{inspected_payload}'::json",
                None,
                f"'{metadata_payload}'",
            )
            is False
        )

    different_pairs = (
        ("true", "1"),
        ("false", "0"),
        ("[1,2]", "[2,1]"),
        ("0.123456789012345678901", "0.123456789012345678902"),
    )
    for inspected_payload, metadata_payload in different_pairs:
        assert (
            comparator(
                None,
                inspected_json,
                metadata_json,
                f"'{inspected_payload}'::json",
                None,
                f"'{metadata_payload}'",
            )
            is True
        )

    for terminal_payload in ("{broken", '{"x":1,"x":2}', "NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError, match="postgresql_json_default_unparseable"):
            comparator(
                None,
                inspected_json,
                metadata_json,
                f"'{terminal_payload}'::json",
                None,
                "'{}'",
            )
    for sql_expression in (
        "('{}'::json)",
        "json_build_object('x', 1)",
        "CAST('{}' AS json)",
        "1 + 1",
    ):
        with pytest.raises(ValueError, match="postgresql_json_default_unparseable"):
            comparator(
                None,
                inspected_json,
                metadata_json,
                "'{}'::json",
                None,
                sql_expression,
            )

    inspected_integer = Column("count", Integer())
    metadata_integer = Column("count", Integer())
    assert comparator(None, inspected_integer, metadata_integer, "0", None, "0") is None


def test_vector_factory_selection_and_registry_ownership_fail_closed() -> None:
    model_module = importlib.import_module("app.models.rag_feedback")
    select_factory = getattr(model_module, "_select_vector_type_factory")
    register_owner = getattr(model_module, "_register_vector_type_owner")
    fallback_type = getattr(model_module, "_FallbackVectorType")
    selected_type = getattr(model_module, "_vector_type_factory")

    assert select_factory(selected_type, None) is selected_type
    absent = ModuleNotFoundError("No module named 'pgvector'", name="pgvector")
    assert select_factory(None, absent) is fallback_type

    broken_errors: tuple[BaseException, ...] = (
        ModuleNotFoundError("No module named 'pgvector.sqlalchemy'", name="pgvector.sqlalchemy"),
        ModuleNotFoundError("No module named 'pgvector_internal'", name="pgvector_internal"),
        ImportError("broken pgvector transitive dependency"),
    )
    for broken in broken_errors:
        with pytest.raises(type(broken)) as raised:
            select_factory(None, broken)
        assert raised.value is broken

    empty_registry: dict[str, object] = {}
    assert register_owner(empty_registry, selected_type) is selected_type
    assert empty_registry == {"vector": selected_type}

    compatible_registry: dict[str, object] = {"vector": selected_type}
    assert register_owner(compatible_registry, selected_type) is selected_type
    assert compatible_registry == {"vector": selected_type}

    incompatible_registry: dict[str, object] = {"vector": object()}
    with pytest.raises(RuntimeError, match="postgresql_vector_registry_owner_incompatible"):
        register_owner(incompatible_registry, selected_type)

    fallback = fallback_type(768)
    assert fallback.dim == 768
    assert str(fallback.compile(dialect=postgresql.dialect())) == "VECTOR(768)"


def test_vector_fallback_bind_processor_is_package_free_and_exact() -> None:
    model_module = importlib.import_module("app.models.rag_feedback")
    fallback_type = getattr(model_module, "_FallbackVectorType")
    adapter_type = getattr(model_module, "_VectorText")
    adapter = adapter_type(fallback_type)
    values = [float(index) / 768 for index in range(768)]
    payload = json.dumps(values, separators=(",", ":"))

    assert adapter.process_bind_param(payload, postgresql.dialect()) == payload
    fallback_impl = adapter.load_dialect_impl(postgresql.dialect())
    assert isinstance(fallback_impl, fallback_type)
    assert fallback_impl.dim == 768

    for invalid_payload in (
        "not-json",
        "[0.0]",
        json.dumps([True] * 768),
        "[NaN," + ",".join("0" for _ in range(767)) + "]",
    ):
        with pytest.raises(ValueError, match="vector_embedding_"):
            adapter.process_bind_param(invalid_payload, postgresql.dialect())


def test_vector_model_variant_binding_and_reflection_are_exact() -> None:
    column_type = UserKnowledge.__table__.c.embedding.type
    sqlite_type = column_type.dialect_impl(sqlite.dialect())
    assert isinstance(sqlite_type.impl, Text)
    postgres_type = column_type.dialect_impl(postgresql.dialect())
    registered_vector_type = ischema_names.get("vector")
    assert isinstance(registered_vector_type, type)
    assert isinstance(postgres_type.impl, registered_vector_type)
    assert getattr(postgres_type.impl, "dim") == 768
    assert str(postgres_type.compile(dialect=postgresql.dialect())) == "VECTOR(768)"

    payload = json.dumps([float(index) / 768 for index in range(768)])
    bind_processor = postgres_type.bind_processor(postgresql.dialect())
    result_processor = postgres_type.result_processor(postgresql.dialect(), None)
    assert bind_processor is not None
    assert result_processor is not None
    encoded = bind_processor(payload)
    assert isinstance(encoded, str)
    round_tripped = result_processor(encoded)
    assert isinstance(round_tripped, str)
    assert json.loads(round_tripped) == pytest.approx(json.loads(payload))

    sqlite_bind_processor = sqlite_type.bind_processor(sqlite.dialect())
    assert sqlite_bind_processor is not None
    assert sqlite_bind_processor("[0.1,0.2]") == "[0.1,0.2]"

    invalid_payloads = (
        "not-json",
        "[0.0]",
        json.dumps([True] * 768),
        "[NaN," + ",".join("0" for _ in range(767)) + "]",
        "[Infinity," + ",".join("0" for _ in range(767)) + "]",
    )
    for invalid_payload in invalid_payloads:
        with pytest.raises(ValueError, match="vector_embedding_"):
            bind_processor(invalid_payload)
    with pytest.raises(ValueError, match="vector_embedding_postgresql_value_must_be_text"):
        bind_processor([0.0] * 768)


def test_model_only_drift_is_closed_without_physical_schema_changes() -> None:
    default_expectations = {
        Recipe: {
            "protein_g": "0.0",
            "fat_g": "0.0",
            "carbs_g": "0.0",
            "fiber_g": "0.0",
            "servings": "1",
        },
        Meal: {"protein_g": "0.0", "fat_g": "0.0", "carbs_g": "0.0", "fiber_g": "0.0"},
        FoodItem: {
            "protein_g_per_100g": "0.0",
            "fat_g_per_100g": "0.0",
            "carbs_g_per_100g": "0.0",
            "fiber_g_per_100g": "0.0",
        },
        VipLlmMonthlyUsage: {"used_requests": "0"},
    }
    for model, columns in default_expectations.items():
        for column_name, expected in columns.items():
            assert _server_default_text(model, column_name) == expected

    paywall_type = PaywallExposureLedger.__table__.c.metadata_json.type
    assert isinstance(paywall_type.dialect_impl(postgresql.dialect()), postgresql.JSONB)

    rag_indexes = _index_signature(RAGFeedback)
    assert ("idx_rag_feedback_user_id", ("user_id",), False) in rag_indexes
    assert ("ix_rag_feedback_user_id", ("user_id",), False) not in rag_indexes

    knowledge_indexes = _index_signature(UserKnowledge)
    assert ("idx_user_knowledge_user", ("user_id",), False) in knowledge_indexes
    assert ("ix_user_knowledge_user_id", ("user_id",), False) not in knowledge_indexes

    weekly_indexes = _index_signature(WeeklyPlan)
    assert ("ix_weekly_plans_user_date", ("user_id", "start_date"), True) in weekly_indexes


def test_single_forward_revision_contains_only_schema_owned_operations() -> None:
    scripts = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    heads = scripts.get_heads()
    assert len(heads) == 1
    assert heads[0] != BASE_ALEMBIC_HEAD, "forward_revision_missing"

    revision = scripts.get_revision(heads[0])
    assert revision is not None
    assert revision.down_revision == BASE_ALEMBIC_HEAD
    revision_path = Path(revision.path)
    assert revision_path.parent == REPO_ROOT / "alembic" / "versions"

    tree = ast.parse(revision_path.read_text(encoding="utf-8"), filename=str(revision_path))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert set(functions) >= {"upgrade", "downgrade"}
    assert _operation_calls(functions["upgrade"]) == [
        ("get_bind", None, None),
        ("execute", "SET LOCAL search_path TO pg_catalog, public", None),
        (
            "execute",
            "ALTER TABLE public.analyzer_state ADD CONSTRAINT uq_analyzer_state_user_key "
            "UNIQUE USING INDEX uq_analyzer_state_user_key",
            None,
        ),
        (
            "execute",
            "ALTER TABLE public.day_plans ADD CONSTRAINT uq_day_plans_user_date "
            "UNIQUE USING INDEX ix_day_plans_user_date",
            None,
        ),
    ]
    assert _operation_calls(functions["downgrade"]) == [
        (
            "execute",
            "CREATE UNIQUE INDEX ix_day_plans_user_date_restore "
            "ON public.day_plans (user_id, date)",
            None,
        ),
        (
            "execute",
            "ALTER TABLE public.day_plans DROP CONSTRAINT uq_day_plans_user_date",
            None,
        ),
        (
            "execute",
            "ALTER INDEX public.ix_day_plans_user_date_restore RENAME TO ix_day_plans_user_date",
            None,
        ),
        (
            "execute",
            "CREATE UNIQUE INDEX uq_analyzer_state_user_key_restore "
            "ON public.analyzer_state (user_id, analyzer_key)",
            None,
        ),
        (
            "execute",
            "ALTER TABLE public.analyzer_state DROP CONSTRAINT uq_analyzer_state_user_key",
            None,
        ),
        (
            "execute",
            "ALTER INDEX public.uq_analyzer_state_user_key_restore "
            "RENAME TO uq_analyzer_state_user_key",
            None,
        ),
        ("get_bind", None, None),
    ]

    env_source = (REPO_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert env_source.count("compare_type=True") == 2


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "reason"),
    (
        ("table_schema", "hostile", "table_schema"),
        ("table_name", "other", "table_name"),
        ("index_schema", "hostile", "index_schema"),
        ("index_name", "other", "index_name"),
        ("key_columns", ("analyzer_key", "user_id"), "key_columns"),
        ("access_method", "hash", "access_method"),
        ("is_unique", False, "unique"),
        ("is_valid", False, "valid"),
        ("is_ready", False, "ready"),
        ("is_live", False, "live"),
        ("nulls_not_distinct", True, "nulls_not_distinct"),
        ("key_options", (1, 0), "key_options"),
        ("key_opclasses_default", (True, False), "key_opclasses"),
        ("key_collations_match", (True, False), "key_collations"),
        ("predicate", "user_id > 0", "predicate"),
        ("expressions", "lower(analyzer_key)", "expressions"),
        ("included_column_count", 1, "include_columns"),
        ("constraint_owner", "already_owned", "constraint_owner"),
    ),
)
def test_forward_revision_index_admission_is_exact_and_fail_closed(
    field_name: str,
    invalid_value: object,
    reason: str,
) -> None:
    scripts = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    revision = scripts.get_revision(scripts.get_current_head())
    assert revision is not None
    module = revision.module
    descriptor_type = getattr(module, "_IndexDescriptor")
    expected = getattr(module, "_EXPECTED_INDEXES")[0]
    require_adoptable = getattr(module, "_require_adoptable_index")

    valid = descriptor_type(
        table_schema="public",
        table_name="analyzer_state",
        index_schema="public",
        index_name="uq_analyzer_state_user_key",
        key_columns=("user_id", "analyzer_key"),
        access_method="btree",
        is_unique=True,
        is_valid=True,
        is_ready=True,
        is_live=True,
        nulls_not_distinct=False,
        key_options=(0, 0),
        key_opclasses_default=(True, True),
        key_collations_match=(True, True),
        predicate=None,
        expressions=None,
        included_column_count=0,
        constraint_owner=None,
    )
    require_adoptable(valid, expected)
    invalid = valid._replace(**{field_name: invalid_value})
    with pytest.raises(
        RuntimeError,
        match=rf"index_admission_failed:uq_analyzer_state_user_key:{reason}",
    ):
        require_adoptable(invalid, expected)

    upgrade_source = inspect.getsource(module.upgrade)
    search_path_index = upgrade_source.index("SET LOCAL search_path TO pg_catalog, public")
    descriptor_load_index = upgrade_source.index("_load_index_descriptor")
    admission_index = upgrade_source.index("_require_adoptable_index")
    analyzer_adoption_index = upgrade_source.index("ALTER TABLE public.analyzer_state")
    day_adoption_index = upgrade_source.index("ALTER TABLE public.day_plans")
    assert (
        search_path_index
        < descriptor_load_index
        < admission_index
        < analyzer_adoption_index
        < day_adoption_index
    )
    assert "FROM pg_catalog.unnest(index_state.indkey)" in Path(revision.path).read_text(
        encoding="utf-8"
    )

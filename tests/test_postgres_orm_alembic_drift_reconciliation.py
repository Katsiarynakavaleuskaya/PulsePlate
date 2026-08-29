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
    assert comparator(None, inspected_json, metadata_json, "'{}'::json", None, "'{}'") is False
    assert (
        comparator(None, inspected_json, metadata_json, "'{\"x\":1}'::json", None, "'{\"x\":2}'")
        is True
    )
    with pytest.raises(ValueError, match="postgresql_json_default_unparseable"):
        comparator(None, inspected_json, metadata_json, "'{broken'::json", None, "'{}'")

    inspected_integer = Column("count", Integer())
    metadata_integer = Column("count", Integer())
    assert comparator(None, inspected_integer, metadata_integer, "0", None, "0") is None


def test_vector_model_variant_and_reflection_are_exact() -> None:
    from pgvector.sqlalchemy import VECTOR

    column_type = UserKnowledge.__table__.c.embedding.type
    assert isinstance(column_type.dialect_impl(sqlite.dialect()), Text)
    postgres_type = column_type.dialect_impl(postgresql.dialect())
    assert isinstance(postgres_type, VECTOR)
    assert postgres_type.dim == 768
    assert ischema_names.get("vector") is VECTOR


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
        (
            "execute",
            "ALTER TABLE analyzer_state ADD CONSTRAINT uq_analyzer_state_user_key "
            "UNIQUE USING INDEX uq_analyzer_state_user_key",
            None,
        ),
        (
            "execute",
            "ALTER TABLE day_plans ADD CONSTRAINT uq_day_plans_user_date "
            "UNIQUE USING INDEX ix_day_plans_user_date",
            None,
        ),
        ("get_bind", None, None),
    ]
    assert _operation_calls(functions["downgrade"]) == [
        (
            "execute",
            "CREATE UNIQUE INDEX ix_day_plans_user_date_restore " "ON day_plans (user_id, date)",
            None,
        ),
        (
            "execute",
            "ALTER TABLE day_plans DROP CONSTRAINT uq_day_plans_user_date",
            None,
        ),
        (
            "execute",
            "ALTER INDEX ix_day_plans_user_date_restore RENAME TO ix_day_plans_user_date",
            None,
        ),
        (
            "execute",
            "CREATE UNIQUE INDEX uq_analyzer_state_user_key_restore "
            "ON analyzer_state (user_id, analyzer_key)",
            None,
        ),
        (
            "execute",
            "ALTER TABLE analyzer_state DROP CONSTRAINT uq_analyzer_state_user_key",
            None,
        ),
        (
            "execute",
            "ALTER INDEX uq_analyzer_state_user_key_restore "
            "RENAME TO uq_analyzer_state_user_key",
            None,
        ),
        ("get_bind", None, None),
    ]

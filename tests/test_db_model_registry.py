"""Behavioral tests for the bounded canonical ORM metadata loader."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

EXPECTED_CLASSES = [
    "AnalyzerStateModel",
    "ContextEntry",
    "DayPlan",
    "FitChefSupportOutcomeEvent",
    "FoodItem",
    "Meal",
    "NutritionEvent",
    "PaywallExposureLedger",
    "RAGFeedback",
    "Recipe",
    "Subscription",
    "SubscriptionActivationAudit",
    "User",
    "UserKnowledge",
    "VipLlmMonthlyUsage",
    "WeeklyPlan",
]

EXPECTED_TABLES = [
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
]

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_probe(source: str) -> dict[str, object]:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "ENVIRONMENT": "test",
            "TESTING": "true",
            "SERVER_SALT": "db-model-registry-test-salt",
        }
    )
    env.pop("DATABASE_ASYNC_URL", None)
    env.pop("DATABASE_USE_ASYNC", None)
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        stdout_tail = completed.stdout[-4000:]
        stderr_tail = completed.stderr[-4000:]
        pytest.fail(
            "fresh ORM registry subprocess failed "
            f"(exit={completed.returncode})\nstdout tail:\n{stdout_tail}\nstderr tail:\n{stderr_tail}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"ORM registry subprocess returned invalid JSON: {completed.stdout[-4000:]}")
    assert isinstance(result, dict)
    return result


def test_base_import_alone_registers_no_models_or_tables() -> None:
    result = _run_probe("""
        import json
        from core.db import Base

        print(json.dumps({
            "classes": sorted(mapper.class_.__name__ for mapper in Base.registry.mappers),
            "tables": sorted(Base.metadata.tables),
        }))
        """)

    assert result == {"classes": [], "tables": []}


@pytest.mark.parametrize(
    "load_sequence",
    [
        "metadata = load_canonical_orm_metadata(); repeated_metadata_identity = True",
        (
            "import core.models; metadata = load_canonical_orm_metadata(); "
            "repeated_metadata_identity = True"
        ),
        (
            "import app.models; metadata = load_canonical_orm_metadata(); "
            "repeated_metadata_identity = True"
        ),
        (
            "from app.models import FitChefSupportOutcomeEvent; "
            "metadata = load_canonical_orm_metadata(); repeated_metadata_identity = True"
        ),
        (
            "metadata = load_canonical_orm_metadata(); "
            "repeated_metadata = load_canonical_orm_metadata(); "
            "repeated_metadata_identity = repeated_metadata is metadata"
        ),
    ],
    ids=["helper-first", "core-first", "app-first", "fitchef-lazy-first", "repeated"],
)
def test_loader_registers_exact_packet_bound_universe_for_import_orders(
    load_sequence: str,
) -> None:
    result = _run_probe(f"""
        import json
        from core.db import Base, load_canonical_orm_metadata

        {load_sequence}
        import app.models as app_models
        import core.models as core_models

        expected_class_objects = {{
            core_models.User,
            core_models.Recipe,
            core_models.Meal,
            core_models.FoodItem,
            core_models.ContextEntry,
            core_models.AnalyzerStateModel,
            app_models.NutritionEvent,
            app_models.VipLlmMonthlyUsage,
            app_models.PaywallExposureLedger,
            app_models.WeeklyPlan,
            app_models.DayPlan,
            app_models.RAGFeedback,
            app_models.UserKnowledge,
            app_models.Subscription,
            app_models.SubscriptionActivationAudit,
            app_models.FitChefSupportOutcomeEvent,
        }}
        mappers = tuple(Base.registry.mappers)
        mapped_class_objects = {{mapper.class_ for mapper in mappers}}
        assert mapped_class_objects == expected_class_objects
        assert len(mappers) == 16
        mapper_registry_identity = all(mapper.registry is Base.registry for mapper in mappers)
        mapper_metadata_identity = all(
            mapper.local_table.metadata is metadata for mapper in mappers
        )
        assert mapper_registry_identity
        assert mapper_metadata_identity
        assert repeated_metadata_identity
        print(json.dumps({{
            "classes": sorted(cls.__name__ for cls in mapped_class_objects),
            "exact_class_objects": True,
            "mapper_count": len(mappers),
            "mapper_metadata_identity": mapper_metadata_identity,
            "mapper_registry_identity": mapper_registry_identity,
            "metadata_identity": metadata is Base.metadata,
            "repeated_metadata_identity": repeated_metadata_identity,
            "tables": sorted(metadata.tables),
        }}))
        """)

    assert result == {
        "classes": EXPECTED_CLASSES,
        "exact_class_objects": True,
        "mapper_count": 16,
        "mapper_metadata_identity": True,
        "mapper_registry_identity": True,
        "metadata_identity": True,
        "repeated_metadata_identity": True,
        "tables": EXPECTED_TABLES,
    }


def test_shared_conftest_has_exact_canonical_registry_loader_ownership() -> None:
    source_path = REPO_ROOT / "tests" / "conftest.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    loader_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "load_canonical_orm_metadata"
    ]
    manual_model_imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name in {"app.models", "core.models"}
    ]

    assert len(loader_calls) == 2
    assert manual_model_imports == []


def test_loader_has_no_database_or_fastapi_bootstrap_side_effects() -> None:
    result = _run_probe("""
        import json
        import sys
        import core.db as db

        db.load_canonical_orm_metadata()
        print(json.dumps({
            "app_main_loaded": "app.main" in sys.modules,
            "async_engine": db._ASYNC_ENGINE is None,
            "async_session": db.AsyncSessionLocal is None,
            "fastapi_bootstrap_loaded": "app.bootstrap.application" in sys.modules,
            "legacy_loaded": "legacy_app" in sys.modules,
            "raw_engine": db._RAW_ENGINE is None,
            "session": db.SessionLocal is None,
        }))
        """)

    assert result == {
        "app_main_loaded": False,
        "async_engine": True,
        "async_session": True,
        "fastapi_bootstrap_loaded": False,
        "legacy_loaded": False,
        "raw_engine": True,
        "session": True,
    }


def test_fallback_registration_failure_cannot_create_partial_schema() -> None:
    result = _run_probe("""
        import json
        import tempfile
        from pathlib import Path
        import core.db as db
        from core.db_fallback import _initialize_fallback_engine

        class RegistrationFailure(RuntimeError):
            pass

        def fail_registration():
            raise RegistrationFailure("registry failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "partial.sqlite"
            db.load_canonical_orm_metadata = fail_registration
            primary_error = RuntimeError("primary failed")
            try:
                _initialize_fallback_engine(f"sqlite:///{database_path}", primary_error)
            except RegistrationFailure as exc:
                result = {
                    "cause": exc.__cause__ is None,
                    "database_exists": database_path.exists(),
                    "message": str(exc),
                    "raised_registration": True,
                }
            else:
                raise AssertionError("fallback unexpectedly succeeded")
            print(json.dumps(result))
        """)

    assert result == {
        "cause": True,
        "database_exists": False,
        "message": "registry failed",
        "raised_registration": True,
    }


@pytest.mark.parametrize(
    ("contamination", "expected_error_type", "expected_message_fragment"),
    [
        (
            "from sqlalchemy import Integer; from sqlalchemy.orm import mapped_column; "
            'UnexpectedRegistryModel = type("UnexpectedRegistryModel", (Base,), '
            '{"__tablename__": "unexpected_registry_table", '
            '"id": mapped_column(Integer, primary_key=True)})',
            "RuntimeError",
            "extra_classes=['__main__.UnexpectedRegistryModel']",
        ),
        (
            "from sqlalchemy import Column, Integer, Table; "
            'Table("unexpected_raw_table", Base.metadata, '
            'Column("id", Integer, primary_key=True))',
            "RuntimeError",
            "extra_tables=['unexpected_raw_table']",
        ),
        (
            "import core.models; from sqlalchemy.orm import relationship; "
            'core.models.User.invalid_registry_relationship = relationship("MissingRegistryTarget")',
            "InvalidRequestError",
            "MissingRegistryTarget",
        ),
    ],
    ids=["extra-mapped-class", "extra-raw-table", "invalid-relationship"],
)
@pytest.mark.parametrize(
    "operation",
    ["init_db", "create_tables", "init_db_async", "db_fallback"],
)
def test_schema_consumers_fail_before_physical_schema_on_registry_contamination(
    contamination: str,
    expected_error_type: str,
    expected_message_fragment: str,
    operation: str,
) -> None:
    result = _run_probe(f"""
        import asyncio
        import json
        import os
        import tempfile
        from pathlib import Path
        import core.db as db
        from core.db import Base

        {contamination}
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "blocked.sqlite"
            database_url = f"sqlite:///{{database_path}}"
            os.environ["DATABASE_URL"] = database_url
            primary_error = RuntimeError("primary failed")
            try:
                operation = {operation!r}
                if operation == "init_db":
                    db.init_db(database_url)
                elif operation == "create_tables":
                    db.create_tables()
                elif operation == "init_db_async":
                    asyncio.run(db.init_db_async())
                else:
                    from core.db_fallback import _initialize_fallback_engine

                    _initialize_fallback_engine(database_url, primary_error)
            except Exception as exc:
                result = {{
                    "async_engine_is_none": db._ASYNC_ENGINE is None,
                    "database_exists": database_path.exists(),
                    "error_message": str(exc),
                    "error_type": type(exc).__name__,
                    "raised_primary": exc is primary_error,
                    "raw_engine_is_none": db._RAW_ENGINE is None,
                    "session_is_none": db.SessionLocal is None,
                }}
            else:
                raise AssertionError("contaminated registry unexpectedly created a schema")
            print(json.dumps(result))
        """)

    assert result["error_type"] == expected_error_type
    assert expected_message_fragment in str(result["error_message"])
    assert result["database_exists"] is False
    assert result["raised_primary"] is False
    assert result["raw_engine_is_none"] is True
    assert result["session_is_none"] is True
    assert result["async_engine_is_none"] is True


@pytest.mark.parametrize(
    "operation",
    ["init_db", "create_tables", "init_db_async", "db_fallback"],
)
def test_schema_creation_consumers_create_exact_packet_bound_tables(operation: str) -> None:
    result = _run_probe(f"""
        import asyncio
        import json
        import os
        import tempfile
        from pathlib import Path
        from sqlalchemy import inspect

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "registry.sqlite"
            database_url = f"sqlite:///{{database_path}}"
            os.environ["DATABASE_URL"] = database_url
            import core.db as db

            operation = {operation!r}
            if operation == "init_db":
                engine = db.init_db(database_url)
            elif operation == "create_tables":
                db.create_tables()
                db.create_tables()
                engine = db._RAW_ENGINE
            elif operation == "init_db_async":
                asyncio.run(db.init_db_async())
                engine = db._RAW_ENGINE
            else:
                from core.db_fallback import _initialize_fallback_engine

                engine = _initialize_fallback_engine(database_url, RuntimeError("primary failed"))

            assert engine is not None
            tables = sorted(inspect(engine).get_table_names())
            engine.dispose()
            print(json.dumps({{"tables": tables}}))
        """)

    assert result == {"tables": EXPECTED_TABLES}

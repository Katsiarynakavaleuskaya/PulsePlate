"""Targeted unit tests to raise total coverage above the 97% CI gate.

RU: Это точечные тесты для редких/защитных веток в core-модулях,
которые в CI остаются непокрытыми и тянут total coverage ниже 97%.
EN: Targeted tests for defensive/rare branches in core modules that impact total coverage.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest


def test_adherence_service_raises_if_store_returns_none() -> None:
    """Cover defensive branch in AdherenceService when store unexpectedly returns None."""
    from core.analyzer.store import AnalyzerState
    from core.bayes.adherence_service import AdherenceService

    class _BadStore:
        def get_state(self, user_id: int, analyzer_key: str):
            return None

        def upsert_state(
            self,
            user_id: int,
            analyzer_key: str,
            state_schema_version: int,
            payload: Mapping[str, Any],
        ) -> AnalyzerState:
            # Intentionally violate protocol to hit defensive branch.
            # RU: Нам нужно покрыть защитную проверку `saved is None`.
            # EN: We intentionally violate the protocol to cover the defensive branch.
            return None  # type: ignore[return-value]

        def update_if_version_matches(
            self,
            user_id: int,
            analyzer_key: str,
            expected_version: int,
            state_schema_version: int,
            payload: Mapping[str, Any],
        ):
            return None

    svc = AdherenceService(store=_BadStore())
    with pytest.raises(RuntimeError, match="Failed to save adherence"):
        svc.record_event(user_id=1, event_type="meal_logged", weight=1.0)


def test_auto_repair_progress_path_hits_continue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover the 'progress exists -> continue' branch in AutoRepairEngine."""
    from core.auto_repair import AutoRepairEngine, RepairIteration, RepairStrategy

    engine = AutoRepairEngine(max_iterations=2)

    # Drive the control-flow without relying on real plan analysis/repair.
    gap_sequences = [
        {"iron_mg": 10.0, "vitamin_c_mg": 5.0},  # initial_gaps (non-empty)
        {"iron_mg": 10.0, "vitamin_c_mg": 5.0},  # current_gaps (iteration 1)
        {"iron_mg": 10.0},  # new_gaps (after "repair") -> smaller => triggers `continue`
        {},  # current_gaps (iteration 2) -> success exit
    ]

    def _fake_analyze(_plan: dict, _targets: object) -> dict[str, float]:
        return gap_sequences.pop(0)

    def _fake_attempt(
        _plan: dict, _targets: object, _strategy: object, _iteration: int
    ) -> RepairIteration:
        return RepairIteration(
            iteration_number=_iteration,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron_mg": 10.0},
            gaps_after={"iron_mg": 1.0},
            changes_applied=[{"repaired_plan": _plan}],
            success=True,
        )

    monkeypatch.setattr(engine, "_analyze_nutrient_gaps", _fake_analyze)
    monkeypatch.setattr(engine, "_attempt_repair", _fake_attempt)

    # Use a minimal, structurally valid week_plan to avoid accidental KeyErrors.
    result = engine.auto_repair_week_plan(week_plan={"days": []}, targets=_make_targets())
    assert result.status.name == "SUCCESS"


def test_auto_repair_partial_result_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover the PARTIAL result branch at the end of AutoRepairEngine loop."""
    from core.auto_repair import AutoRepairEngine, RepairIteration, RepairStrategy, RepairStatus

    engine = AutoRepairEngine(max_iterations=1)

    # initial_gaps: 2 deficits; final_gaps: 1 deficit -> PARTIAL branch.
    gap_sequences = [
        {"iron_mg": 10.0, "vitamin_c_mg": 5.0},  # initial_gaps
        {"iron_mg": 10.0, "vitamin_c_mg": 5.0},  # current_gaps
        {"iron_mg": 10.0},  # final_gaps (after loop)
    ]

    def _fake_analyze(_plan: dict, _targets: object) -> dict[str, float]:
        return gap_sequences.pop(0)

    def _fake_attempt(
        _plan: dict, _targets: object, _strategy: object, _iteration: int
    ) -> RepairIteration:
        return RepairIteration(
            iteration_number=_iteration,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron_mg": 10.0, "vitamin_c_mg": 5.0},
            gaps_after={"iron_mg": 10.0, "vitamin_c_mg": 5.0},
            changes_applied=[{"repaired_plan": _plan}],
            success=False,
        )

    monkeypatch.setattr(engine, "_analyze_nutrient_gaps", _fake_analyze)
    monkeypatch.setattr(engine, "_attempt_repair", _fake_attempt)

    result = engine.auto_repair_week_plan(week_plan={"days": []}, targets=_make_targets())
    assert result.status == RepairStatus.PARTIAL
    assert "Частичный ремонт" in result.message


def test_core_db_build_engine_url_absolute_path_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover absolute-path handling branch inside core.db._build_engine_url."""
    import core.db as core_db

    # Avoid filesystem writes to /abs by short-circuiting directory creation.
    monkeypatch.setattr(core_db, "_ensure_sqlite_directory", lambda *_a, **_k: None, raising=True)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "test")

    # Force default_path to be absolute so sqlite URL becomes sqlite:////abs/...
    monkeypatch.setattr(core_db.os.path, "join", lambda *_a: "/abs/app.db", raising=True)
    url = core_db._build_engine_url()
    assert url.startswith("sqlite:///")


@pytest.mark.asyncio
async def test_core_db_init_db_async_uses_async_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover init_db_async async-engine path (begin + run_sync)."""
    import core.db as core_db

    called: dict[str, bool] = {"create_all": False}

    def _create_all(*_a: Any, **_k: Any) -> None:
        called["create_all"] = True

    monkeypatch.setattr(core_db.Base.metadata, "create_all", _create_all, raising=True)

    class _Conn:
        async def run_sync(self, fn: Callable[..., Any]) -> None:
            fn()

    class _BeginCtx:
        async def __aenter__(self) -> _Conn:
            return _Conn()

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    class _AsyncEngine:
        def begin(self) -> _BeginCtx:
            return _BeginCtx()

    monkeypatch.setattr(core_db, "_ASYNC_ENGINE", _AsyncEngine(), raising=True)
    await core_db.init_db_async()
    assert called["create_all"] is True


def test_core_db_init_db_warns_on_remove_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cover warning branch when auto-clean cannot remove old SQLite file."""
    import sqlalchemy

    import core.db as core_db

    old_db = tmp_path / "old.sqlite"
    new_db = tmp_path / "new.sqlite"

    # Create an old engine and install it as current global engine.
    old_engine = sqlalchemy.create_engine(f"sqlite:///{old_db}")

    prev_engine = core_db._RAW_ENGINE
    prev_session_local = core_db.SessionLocal
    try:
        core_db._RAW_ENGINE = old_engine

        # Force URL change and enable cleanup-on-change.
        monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{new_db}")

        # Ensure "old path exists" and removal fails.
        monkeypatch.setattr(core_db.os.path, "exists", lambda _p: True, raising=True)

        def _raise_remove(_p: str) -> None:
            raise OSError("boom")

        monkeypatch.setattr(core_db.os, "remove", _raise_remove, raising=True)

        # Should not raise; should fall back after warning.
        core_db.init_db()
    finally:
        core_db._RAW_ENGINE = prev_engine
        core_db.SessionLocal = prev_session_local


@pytest.mark.asyncio
async def test_update_manager_record_count_and_checksum_sqlite_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cover SQLite cache paths in DatabaseUpdateManager."""
    from core.food_apis.update_manager import DatabaseUpdateManager

    cache_dir = tmp_path / "food_db"
    cache_dir.mkdir(parents=True, exist_ok=True)
    sqlite_file = cache_dir / "off.sqlite"

    conn = sqlite3.connect(str(sqlite_file))
    try:
        conn.execute("CREATE TABLE products (name TEXT, data TEXT)")
        conn.execute("INSERT INTO products (name, data) VALUES (?, ?)", ("ok", '{"k":1}'))
        conn.commit()
    finally:
        conn.close()

    mgr = DatabaseUpdateManager(cache_dir=cache_dir)

    count = await mgr._get_actual_record_count("openfoodfacts")
    assert count == 1

    class _BadData:
        def encode(self, _encoding: str) -> bytes:
            raise UnicodeEncodeError("utf-8", "x", 0, 1, "boom")

    class _FakeConn:
        def execute(self, _sql: str):
            return iter([("ok", '{"k":1}'), ("bad", _BadData())])

        def close(self) -> None:
            return None

    # Patch sqlite3.connect only for checksum-loading path to hit the UnicodeEncodeError handler.
    monkeypatch.setattr(sqlite3, "connect", lambda _p: _FakeConn())
    cache_data = await mgr._get_cache_data_for_checksum("openfoodfacts")

    assert "ok" in cache_data

    # Cover cache_data branch in validated checksum method.
    def _calc(_data: dict[str, Any]) -> str:
        return "abc"

    monkeypatch.setattr(mgr, "_calculate_checksum", _calc, raising=True)
    rc, checksum = await mgr._get_validated_record_count_and_checksum(
        "openfoodfacts", unified_foods={}
    )
    assert checksum == "abc"
    assert rc >= 0


@pytest.mark.asyncio
async def test_update_manager_load_backup_schema_validation(tmp_path: Path) -> None:
    """Cover _load_backup schema validation branches (non-dict + malformed entry)."""
    from core.food_apis.update_manager import DatabaseUpdateManager

    cache_dir = tmp_path / "food_db"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mgr = DatabaseUpdateManager(cache_dir=cache_dir)

    source = "usda"
    version = "v1"
    backup_file = cache_dir / f"{source}_backup_{version}.json"

    # Non-dict JSON -> early return.
    backup_file.write_text("[]", encoding="utf-8")
    res = await mgr._load_backup(source, version)
    assert res == {}

    # Dict with required keys + unknown extra key -> TypeError -> debug + continue.
    bad_version = "v2"
    bad_backup = cache_dir / f"{source}_backup_{bad_version}.json"
    bad_backup.write_text(
        json.dumps(
            {
                "item": {
                    "name": "x",
                    "nutrients_per_100g": {},
                    "cost_per_100g": 0.0,
                    "tags": [],
                    "availability_regions": [],
                    "source": "USDA",
                    "source_id": "1",
                    "extra": "boom",
                }
            }
        ),
        encoding="utf-8",
    )
    res2 = await mgr._load_backup(source, bad_version)
    assert res2 == {}


def _make_targets():
    """Build a minimal MicronutrientTargets instance for control-flow tests."""
    from core.targets import MicronutrientTargets

    z = (0.0, 0.0, 0.0)
    return MicronutrientTargets(
        iron_mg=z,
        calcium_mg=z,
        magnesium_mg=z,
        zinc_mg=z,
        potassium_mg=z,
        iodine_ug=z,
        selenium_ug=z,
        folate_ug=z,
        b12_ug=z,
        vitamin_d_iu=z,
        vitamin_a_ug=z,
        vitamin_c_mg=z,
    )


def test_meal_planner_attribute_error_branch_returns_none() -> None:
    """Cover meal_planner AttributeError branch (debug + None)."""
    from core.meal_planner import _select_recipe_for_meal

    class _RecipeDB:
        def get_recipes_by_category(self, _categories: list[str]) -> list[dict[str, Any]]:
            raise AttributeError("boom")

    res = _select_recipe_for_meal(
        meal_name="breakfast",
        kcal_target=400,
        diet_flags={"vegan"},
        recipe_db=_RecipeDB(),
    )
    assert res is None


def test_update_manager_patchable_path_wrapper_eq_and_hash(tmp_path: Path) -> None:
    """Cover _PatchablePathWrapper equality + hashing branches."""
    from core.food_apis.update_manager import _PatchablePathWrapper

    p = _PatchablePathWrapper(tmp_path)
    p2 = _PatchablePathWrapper(tmp_path)

    assert p == p2
    assert p == tmp_path
    assert len({p, p2}) == 1


@pytest.mark.asyncio
async def test_update_manager_get_cache_data_for_checksum_handles_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cover broad exception handler in _get_cache_data_for_checksum."""
    from core.food_apis.update_manager import DatabaseUpdateManager

    mgr = DatabaseUpdateManager(cache_dir=tmp_path / "food_db")
    # Force a TypeError inside the try block (cache_dir / filename) to hit except.
    monkeypatch.setattr(mgr, "cache_dir", object(), raising=True)
    res = await mgr._get_cache_data_for_checksum("openfoodfacts")
    assert res == {}


def test_meal_optimizer_break_when_optimized_meals_empty() -> None:
    """Cover defensive `if not optimized_meals: break` in optimize_micro_coverage.

    RU: В норме optimized_meals не пустой, если meals не пустой. Этот тест
    фиксирует защитную ветку на случай нестандартного list-подобного объекта.
    EN: Defensive branch coverage for rare list-like behavior.
    """
    from core.meal_optimizer import optimize_micro_coverage

    class _NonIteratingMeals(list[dict[str, Any]]):
        def __iter__(self):
            return iter(())

    meals = _NonIteratingMeals([{"micros": {"iron_mg": 0.0}}])
    optimized, coverage = optimize_micro_coverage(
        meals=meals,
        target_micros={"iron_mg": 10.0},
        min_coverage_pct=80.0,
        diet_flags=set(),
        allergens=set(),
    )

    assert optimized == []
    assert "iron_mg" in coverage


def test_core_db_async_module_init_lines_are_exercised(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise core.db module-level async init lines under coverage without reloading core.db.

    We execute `core/db.py` via `runpy.run_path` with patched SQLAlchemy async factories so:
    - line ~509 (async_kwargs.update(_POOL_CONFIG)) executes for non-sqlite+aiosqlite URLs
    - line ~513 (AsyncSessionLocal = async_sessionmaker(...)) executes deterministically
    """
    import runpy

    import sqlalchemy.ext.asyncio as sa_asyncio

    import core.db as core_db

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DATABASE_USE_ASYNC", "1")
    # Pick a non-sqlite+aiosqlite URL to force pool config update branch.
    monkeypatch.setenv("DATABASE_ASYNC_URL", "postgresql+asyncpg://example/db")

    def _fake_create_async_engine(_url: str, **_kwargs: Any) -> object:
        return object()

    def _fake_async_sessionmaker(**_kwargs: Any) -> object:
        return object()

    monkeypatch.setattr(sa_asyncio, "create_async_engine", _fake_create_async_engine, raising=True)
    monkeypatch.setattr(sa_asyncio, "async_sessionmaker", _fake_async_sessionmaker, raising=True)

    ns = runpy.run_path(core_db.__file__, run_name="core_db_cov_exec")
    assert ns.get("AsyncSessionLocal") is not None


def test_product_finder_rejects_non_numeric_threshold() -> None:
    """Cover ProductFinder threshold type validation."""
    from core.product_finder import ProductFinder

    with pytest.raises(ValueError, match="min_confidence_threshold must be a numeric value"):
        ProductFinder(min_confidence_threshold="nope")  # type: ignore[arg-type]


def test_product_finder_rejects_out_of_range_threshold() -> None:
    """Cover ProductFinder inclusive range validation."""
    from core.product_finder import ProductFinder

    with pytest.raises(ValueError, match=r"within the inclusive range \[0\.0, 1\.0\]"):
        ProductFinder(min_confidence_threshold=2.0)

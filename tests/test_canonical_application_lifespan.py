from __future__ import annotations

import ast
import asyncio
import json
import logging
import threading
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import yaml

import app.bootstrap.lifespan as lifespan_module
from app.bootstrap.food_search import FoodSearchLifecycleLease
from app.bootstrap.lifespan import (
    LifespanHooks,
    UnifiedFoodLifecycleLease,
    _application_lifespan_with_hooks,
)
import core.food_apis.unified_db as unified_db_module
from core.food_apis.unified_db import UnifiedFoodDatabase
from core.food_apis.scheduler_runtime import SchedulerMode
from core.menu_engine import _get_default_food_db
from tests._client import open_test_client
from tests._helpers.vip_contracts import assert_json_response_payload

REPO_ROOT = Path(__file__).resolve().parents[1]


class _ClosingClient:
    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1
        if self.error is not None:
            raise self.error


def _replace_registered_unified_food(
    replacement: UnifiedFoodDatabase | None,
) -> UnifiedFoodDatabase | None:
    """Install one test register value through an identity-safe CAS."""

    observed = unified_db_module._read_unified_db_instance()
    replaced, current = unified_db_module._compare_exchange_unified_db_instance(
        observed,
        replacement,
    )
    assert replaced
    assert current is replacement
    return observed


@pytest.fixture(autouse=True)
def _restore_unified_food_register() -> Iterator[None]:
    """Restore the exact pre-test register identity without direct assignment."""

    read_register = unified_db_module._read_unified_db_instance
    compare_exchange = unified_db_module._compare_exchange_unified_db_instance
    original = read_register()
    yield
    current = read_register()
    restored, observed = compare_exchange(
        current,
        original,
    )
    assert restored
    assert observed is original


def _base_hooks(events: list[str]) -> LifespanHooks:
    async def _start(update_interval_hours: int = 24) -> None:
        events.append(f"scheduler-start:{update_interval_hours}")

    async def _stop() -> None:
        events.append("scheduler-stop")

    def _configure(_app: FastAPI) -> FoodSearchLifecycleLease:
        events.append("food-configure")
        return FoodSearchLifecycleLease()

    def _dispose(_app: FastAPI, _lease: FoodSearchLifecycleLease) -> None:
        events.append("food-dispose")

    unified_instance = cast(UnifiedFoodDatabase, SimpleNamespace())

    async def _acquire_unified_food() -> UnifiedFoodLifecycleLease:
        events.append("unified-acquire")
        return UnifiedFoodLifecycleLease(
            instance=unified_instance,
            owns_instance=False,
        )

    async def _release_unified_food(_lease: UnifiedFoodLifecycleLease) -> None:
        events.append("unified-release")

    return LifespanHooks(
        run_startup_guards=lambda _app: events.append("guards"),
        initialize_database=lambda: events.append("database"),
        clear_database_fallback=lambda: events.append("fallback-clear"),
        attempt_database_fallback=lambda _env, _prod, _err: events.append("fallback-attempt"),
        validate_templates=lambda: events.append("templates"),
        acquire_unified_food=_acquire_unified_food,
        release_unified_food=_release_unified_food,
        configure_food_search=_configure,
        dispose_food_search=_dispose,
        start_background_updates=_start,
        stop_background_updates=_stop,
    )


def _run_lifespan(
    hooks: LifespanHooks,
    *,
    body: Callable[[], Awaitable[None]] | None = None,
    scheduler_mode: SchedulerMode | None = SchedulerMode.IN_PROCESS_DEV,
) -> None:
    async def _scenario() -> None:
        async with _application_lifespan_with_hooks(
            FastAPI(),
            hooks=hooks,
            scheduler_mode=scheduler_mode,
        ):
            if body is not None:
                await body()

    asyncio.run(_scenario())


def _ordered_indexes(path: str, lines: list[str], expected: list[str]) -> list[int]:
    indexes: list[int] = []
    search_start = 0
    for line in expected:
        try:
            found = lines.index(line, search_start)
        except ValueError:
            pytest.fail(f"{path} is missing the expected step: {line!r}")
        indexes.append(found)
        search_start = found + 1
    return indexes


def test_ordered_indexes_advances_past_duplicate_steps() -> None:
    lines = ["prepare", "worker", "migrate", "worker"]

    assert _ordered_indexes("deploy.sh", lines, ["worker", "worker"]) == [1, 3]


def test_canonical_lifespan_uses_exact_startup_and_cleanup_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.delenv("DISABLE_BACKGROUND_UPDATES", raising=False)

    async def _body() -> None:
        events.append("body")

    _run_lifespan(_base_hooks(events), body=_body)

    assert events == [
        "guards",
        "database",
        "fallback-clear",
        "templates",
        "unified-acquire",
        "food-configure",
        "scheduler-start:24",
        "body",
        "scheduler-stop",
        "food-dispose",
        "unified-release",
    ]


def test_missing_optional_scheduler_uses_best_effort_noop_hooks(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        lifespan_module,
        "_import_background_update_hooks",
        lambda: (_ for _ in ()).throw(ImportError("optional scheduler dependency unavailable")),
    )
    with caplog.at_level(logging.WARNING, logger="app.bootstrap.lifespan"):
        starter, stopper = lifespan_module._load_background_update_hooks()

    async def _run_hooks() -> None:
        await starter()
        await stopper()

    asyncio.run(_run_hooks())
    assert "scheduler is unavailable" in caplog.text


def test_startup_guard_failure_stops_all_later_work() -> None:
    events: list[str] = []
    hooks = replace(
        _base_hooks(events),
        run_startup_guards=lambda _app: (_ for _ in ()).throw(RuntimeError("guard")),
    )

    with pytest.raises(RuntimeError, match="guard"):
        _run_lifespan(hooks)

    assert events == []


def test_scheduler_mode_validation_runs_after_startup_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    def _resolve_scheduler_mode() -> SchedulerMode:
        events.append("scheduler-mode")
        raise RuntimeError("scheduler configuration")

    monkeypatch.setattr(
        lifespan_module,
        "resolve_scheduler_mode",
        _resolve_scheduler_mode,
    )

    with pytest.raises(RuntimeError, match="scheduler configuration"):
        _run_lifespan(_base_hooks(events), scheduler_mode=None)

    assert events == ["guards", "scheduler-mode"]


def test_database_failure_delegates_to_public_fallback_without_clearing_state() -> None:
    events: list[str] = []
    database_error = OSError("database unavailable")

    def _initialize() -> None:
        events.append("database")
        raise database_error

    def _fallback(_env: str | None, _prod: bool, error: Exception) -> None:
        assert error is database_error
        events.append("fallback-attempt")

    hooks = replace(
        _base_hooks(events),
        initialize_database=_initialize,
        attempt_database_fallback=_fallback,
    )
    _run_lifespan(hooks)

    assert events[:5] == [
        "guards",
        "database",
        "fallback-attempt",
        "templates",
        "unified-acquire",
    ]
    assert "fallback-clear" not in events


def test_production_database_failure_propagates() -> None:
    events: list[str] = []
    database_error = RuntimeError("production database unavailable")

    def _raise_database_error() -> None:
        raise database_error

    def _reject_fallback(_env: str | None, _prod: bool, error: Exception) -> None:
        raise error

    hooks = replace(
        _base_hooks(events),
        initialize_database=_raise_database_error,
        attempt_database_fallback=_reject_fallback,
    )

    with pytest.raises(RuntimeError, match="production database unavailable"):
        _run_lifespan(hooks)
    assert events == ["guards"]


def test_template_failure_prevents_resource_acquisition() -> None:
    events: list[str] = []
    hooks = replace(
        _base_hooks(events),
        validate_templates=lambda: (_ for _ in ()).throw(RuntimeError("templates")),
    )

    with pytest.raises(RuntimeError, match="templates"):
        _run_lifespan(hooks)

    assert events == ["guards", "database", "fallback-clear"]


def test_unified_food_acquisition_failure_stops_later_startup() -> None:
    events: list[str] = []

    async def _fail_acquisition() -> UnifiedFoodLifecycleLease:
        events.append("unified-acquire-failed")
        raise RuntimeError("unified acquisition")

    hooks = replace(
        _base_hooks(events),
        acquire_unified_food=_fail_acquisition,
    )

    with pytest.raises(RuntimeError, match="unified acquisition"):
        _run_lifespan(hooks)

    assert events == [
        "guards",
        "database",
        "fallback-clear",
        "templates",
        "unified-acquire-failed",
    ]


@pytest.mark.parametrize("cache_exists", [True, False], ids=["cached", "missing-cache"])
def test_default_unified_food_lifecycle_is_cached_only_and_owned(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    cache_exists: bool,
) -> None:
    events: list[str] = []
    calls = {"build": 0, "search": 0, "save": 0, "sleep": 0}
    usda_client = _ClosingClient()
    off_client = _ClosingClient()
    monkeypatch.chdir(tmp_path)
    _replace_registered_unified_food(None)
    monkeypatch.setattr(unified_db_module, "USDAClient", lambda: usda_client)
    monkeypatch.setattr(unified_db_module, "OFFClient", lambda: off_client)
    monkeypatch.setattr(unified_db_module, "OFF_AVAILABLE", True)

    cache_dir = tmp_path / "cache" / "food_db"
    if cache_exists:
        cache_dir.mkdir(parents=True)
        (cache_dir / "common_foods.json").write_text(
            json.dumps(
                {
                    "iron": {
                        "name": "Cached iron food",
                        "nutrients_per_100g": {"iron_mg": 10.0},
                        "cost_per_100g": 1.0,
                        "tags": [],
                        "availability_regions": ["BY"],
                        "source": "fixture",
                        "source_id": "iron-1",
                        "nutrition_inputs": [
                            {
                                "source": "estimate",
                                "record_id": "iron-1",
                                "nutrients": {"iron_mg": 10.0},
                            }
                        ],
                        "nutrition_provenance": {"iron_mg": "estimate"},
                        "nutrition_nutrient_confidence": {"iron_mg": 0.4},
                        "nutrition_confidence": 0.4,
                    }
                }
            ),
            encoding="utf-8",
        )

    async def _forbidden_build(*_args: object, **_kwargs: object) -> object:
        calls["build"] += 1
        raise AssertionError("common-food build must not run during lifespan")

    async def _forbidden_search(*_args: object, **_kwargs: object) -> object:
        calls["search"] += 1
        raise AssertionError("provider search must not run during lifespan")

    def _forbidden_save(*_args: object, **_kwargs: object) -> None:
        calls["save"] += 1
        raise AssertionError("cache save must not run during lifespan")

    async def _forbidden_sleep(*_args: object, **_kwargs: object) -> None:
        calls["sleep"] += 1
        raise AssertionError("throttle sleep must not run during lifespan")

    monkeypatch.setattr(
        unified_db_module.UnifiedFoodDatabase,
        "get_common_foods_database",
        _forbidden_build,
    )
    monkeypatch.setattr(
        unified_db_module.UnifiedFoodDatabase,
        "search_food",
        _forbidden_search,
    )
    monkeypatch.setattr(
        unified_db_module.UnifiedFoodDatabase,
        "_save_cache",
        _forbidden_save,
    )
    monkeypatch.setattr(unified_db_module.asyncio, "sleep", _forbidden_sleep)

    async def _body() -> None:
        snapshot = unified_db_module.get_cached_common_foods_snapshot()
        if cache_exists:
            assert snapshot["iron"].name == "Cached iron food"
        else:
            assert snapshot == {}
            assert not cache_dir.exists()

    hooks = replace(
        _base_hooks(events),
        acquire_unified_food=lifespan_module._acquire_unified_food_database,
        release_unified_food=lifespan_module._release_unified_food_database,
    )
    _run_lifespan(hooks, body=_body, scheduler_mode=SchedulerMode.DISABLED)

    assert calls == {"build": 0, "search": 0, "save": 0, "sleep": 0}
    assert usda_client.close_calls == 1
    assert off_client.close_calls == 1
    assert unified_db_module._read_unified_db_instance() is None


def test_unified_food_foreign_preinit_fails_and_replacement_preserves_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    borrowed_usda = _ClosingClient()
    borrowed_off = _ClosingClient()
    borrowed_instance = cast(
        UnifiedFoodDatabase,
        SimpleNamespace(usda_client=borrowed_usda, off_client=borrowed_off),
    )
    _replace_registered_unified_food(borrowed_instance)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)

    with pytest.raises(
        RuntimeError,
        match="^Unified-food singleton is not lifecycle-managed$",
    ):
        asyncio.run(lifespan_module._acquire_unified_food_database())

    events: list[str] = []

    async def _acquire_foreign() -> UnifiedFoodLifecycleLease:
        events.append("unified-acquire")
        return await lifespan_module._acquire_unified_food_database()

    async def _body() -> None:
        events.append("body")

    hooks = replace(
        _base_hooks(events),
        acquire_unified_food=_acquire_foreign,
        release_unified_food=lifespan_module._release_unified_food_database,
    )
    with pytest.raises(
        RuntimeError,
        match="^Unified-food singleton is not lifecycle-managed$",
    ):
        _run_lifespan(hooks, body=_body)

    assert events == [
        "guards",
        "database",
        "fallback-clear",
        "templates",
        "unified-acquire",
    ]
    assert borrowed_usda.close_calls == 0
    assert borrowed_off.close_calls == 0
    assert unified_db_module._read_unified_db_instance() is borrowed_instance
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0

    _replace_registered_unified_food(None)

    owned_usda = _ClosingClient(RuntimeError("USDA close failed"))
    owned_off = _ClosingClient()
    monkeypatch.chdir(tmp_path)
    _replace_registered_unified_food(None)
    monkeypatch.setattr(unified_db_module, "USDAClient", lambda: owned_usda)
    monkeypatch.setattr(unified_db_module, "OFFClient", lambda: owned_off)
    monkeypatch.setattr(unified_db_module, "OFF_AVAILABLE", True)
    owned_lease = asyncio.run(lifespan_module._acquire_unified_food_database())
    replacement = cast(UnifiedFoodDatabase, SimpleNamespace())
    _replace_registered_unified_food(replacement)

    with pytest.raises(
        unified_db_module.UnifiedFoodClientCleanupError,
        match=f"^{unified_db_module.UNIFIED_FOOD_CLEANUP_ERROR_MESSAGE}$",
    ) as cleanup_exc:
        asyncio.run(lifespan_module._release_unified_food_database(owned_lease))
    assert cleanup_exc.value.__cause__ is None
    assert cleanup_exc.value.__context__ is None
    asyncio.run(lifespan_module._release_unified_food_database(owned_lease))

    assert owned_usda.close_calls == 1
    assert owned_off.close_calls == 1
    assert unified_db_module._read_unified_db_instance() is replacement
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0


def test_menu_default_food_consumer_yields_to_managed_testclient_lifespan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    vip_headers: dict[str, str],
) -> None:
    """A direct menu read cannot preempt later canonical lifespan ownership."""
    events: list[str] = []

    class _OrderedClosingClient:
        def __init__(self, label: str) -> None:
            self.label = label

        async def close(self) -> None:
            events.append(f"{self.label}-close")

    previous = _replace_registered_unified_food(None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)

    events.append("direct-default-consumer")
    direct_defaults = _get_default_food_db()
    assert set(direct_defaults) == {"chicken_breast", "lentils"}
    assert unified_db_module._read_unified_db_instance() is None

    usda_client = _OrderedClosingClient("usda")
    off_client = _OrderedClosingClient("off")

    def _initialize_managed_sentinel(
        instance: UnifiedFoodDatabase,
        cache_dir: str | None = None,
        *,
        create_cache_dir: bool = True,
    ) -> None:
        del cache_dir
        assert create_cache_dir is False
        events.append("managed-init")
        instance.cache_dir = tmp_path / "managed-cache"
        instance.usda_client = usda_client
        instance.off_client = off_client

    monkeypatch.setattr(
        unified_db_module.UnifiedFoodDatabase,
        "__init__",
        _initialize_managed_sentinel,
    )

    with open_test_client() as client:
        managed = unified_db_module._read_unified_db_instance()
        assert managed is not None
        assert managed is lifespan_module._managed_unified_food_instance
        events.append("managed-active")
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert assert_json_response_payload(response)["status"] == "success"
        events.append("request-success")

    assert unified_db_module._read_unified_db_instance() is None
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0
    _replace_registered_unified_food(previous)
    assert unified_db_module._read_unified_db_instance() is previous
    events.append("prior-restored")
    assert events == [
        "direct-default-consumer",
        "managed-init",
        "managed-active",
        "request-success",
        "usda-close",
        "off-close",
        "prior-restored",
    ]


@pytest.mark.parametrize("release_owner_first", [True, False])
def test_overlapping_managed_unified_food_leases_close_only_after_final_release(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    release_owner_first: bool,
) -> None:
    usda_client = _ClosingClient()
    off_client = _ClosingClient()
    monkeypatch.chdir(tmp_path)
    _replace_registered_unified_food(None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)
    monkeypatch.setattr(unified_db_module, "USDAClient", lambda: usda_client)
    monkeypatch.setattr(unified_db_module, "OFFClient", lambda: off_client)
    monkeypatch.setattr(unified_db_module, "OFF_AVAILABLE", True)

    owner_lease = asyncio.run(lifespan_module._acquire_unified_food_database())
    borrower_lease = asyncio.run(lifespan_module._acquire_unified_food_database())

    assert owner_lease.owns_instance is True
    assert borrower_lease.owns_instance is False
    assert owner_lease.managed_lifetime is True
    assert borrower_lease.managed_lifetime is True
    assert borrower_lease.instance is owner_lease.instance
    assert lifespan_module._managed_unified_food_active_leases == 2

    first_lease, final_lease = (
        (owner_lease, borrower_lease) if release_owner_first else (borrower_lease, owner_lease)
    )
    asyncio.run(lifespan_module._release_unified_food_database(first_lease))
    assert usda_client.close_calls == 0
    assert off_client.close_calls == 0
    assert unified_db_module._read_unified_db_instance() is owner_lease.instance
    assert lifespan_module._managed_unified_food_active_leases == 1

    asyncio.run(lifespan_module._release_unified_food_database(final_lease))
    asyncio.run(lifespan_module._release_unified_food_database(final_lease))
    assert usda_client.close_calls == 1
    assert off_client.close_calls == 1
    assert unified_db_module._read_unified_db_instance() is None
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0


def test_simultaneous_threaded_unified_food_acquisition_closes_local_loser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    start_barrier = threading.Barrier(3)
    construction_barrier = threading.Barrier(2)
    result_lock = threading.Lock()
    created: list[tuple[UnifiedFoodDatabase, _ClosingClient, _ClosingClient]] = []
    leases: list[UnifiedFoodLifecycleLease] = []
    errors: list[BaseException] = []

    def _initialize(
        instance: UnifiedFoodDatabase,
        cache_dir: str | None = None,
        *,
        create_cache_dir: bool = True,
    ) -> None:
        del cache_dir
        assert create_cache_dir is False
        usda_client = _ClosingClient()
        off_client = _ClosingClient()
        instance.usda_client = usda_client
        instance.off_client = off_client
        with result_lock:
            created.append((instance, usda_client, off_client))
        construction_barrier.wait(timeout=2)

    def _worker() -> None:
        try:
            start_barrier.wait(timeout=2)
            lease = asyncio.run(lifespan_module._acquire_unified_food_database())
            with result_lock:
                leases.append(lease)
        except BaseException as exc:
            with result_lock:
                errors.append(exc)

    _replace_registered_unified_food(None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_lock", threading.Lock())
    monkeypatch.setattr(unified_db_module.UnifiedFoodDatabase, "__init__", _initialize)

    workers = [threading.Thread(target=_worker) for _ in range(2)]
    for worker in workers:
        worker.start()
    start_barrier.wait(timeout=2)
    for worker in workers:
        worker.join(timeout=2)

    assert not any(worker.is_alive() for worker in workers)
    assert errors == []
    assert len(created) == 2
    assert len(leases) == 2
    assert leases[0].instance is leases[1].instance
    assert sum(lease.owns_instance for lease in leases) == 1
    assert all(lease.managed_lifetime for lease in leases)
    assert lifespan_module._managed_unified_food_active_leases == 2

    managed_instance = leases[0].instance
    managed_record = next(record for record in created if record[0] is managed_instance)
    loser_record = next(record for record in created if record[0] is not managed_instance)
    assert loser_record[1].close_calls == 1
    assert loser_record[2].close_calls == 1
    assert managed_record[1].close_calls == 0
    assert managed_record[2].close_calls == 0

    asyncio.run(lifespan_module._release_unified_food_database(leases[0]))
    assert managed_record[1].close_calls == 0
    assert managed_record[2].close_calls == 0
    assert unified_db_module._read_unified_db_instance() is managed_instance

    asyncio.run(lifespan_module._release_unified_food_database(leases[1]))
    assert managed_record[1].close_calls == 1
    assert managed_record[2].close_calls == 1
    assert unified_db_module._read_unified_db_instance() is None
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0


def test_partial_unified_food_acquisition_closes_all_local_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    usda_client = _ClosingClient(RuntimeError("cleanup failed"))
    off_client = _ClosingClient()

    def _fail_initialization(
        instance: UnifiedFoodDatabase,
        cache_dir: str | None = None,
        *,
        create_cache_dir: bool = True,
    ) -> None:
        del cache_dir
        assert create_cache_dir is False
        instance.usda_client = usda_client
        instance.off_client = off_client
        raise RuntimeError("partial initialization")

    _replace_registered_unified_food(None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)
    monkeypatch.setattr(
        unified_db_module.UnifiedFoodDatabase,
        "__init__",
        _fail_initialization,
    )

    with pytest.raises(
        RuntimeError,
        match=f"^{unified_db_module.UNIFIED_FOOD_INITIALIZATION_ERROR_MESSAGE}$",
    ) as initialization_exc:
        asyncio.run(lifespan_module._acquire_unified_food_database())
    assert initialization_exc.value.__cause__ is None
    assert initialization_exc.value.__context__ is None

    assert usda_client.close_calls == 1
    assert off_client.close_calls == 1
    assert unified_db_module._read_unified_db_instance() is None
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0


def test_partial_unified_food_acquisition_cleanup_cancellation_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[str] = []

    class _FirstClient:
        async def close(self) -> None:
            attempted.append("first")

    class _SecondClient:
        def __init__(self, started: asyncio.Event) -> None:
            self.started = started

        async def close(self) -> None:
            attempted.append("second")
            self.started.set()
            await asyncio.Event().wait()

    async def _scenario() -> None:
        second_started = asyncio.Event()

        def _fail_initialization(
            instance: UnifiedFoodDatabase,
            cache_dir: str | None = None,
            *,
            create_cache_dir: bool = True,
        ) -> None:
            del cache_dir
            assert create_cache_dir is False
            instance.usda_client = _FirstClient()
            instance.off_client = _SecondClient(second_started)
            raise RuntimeError("initialization failed")

        _replace_registered_unified_food(None)
        monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
        monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)
        monkeypatch.setattr(
            unified_db_module.UnifiedFoodDatabase,
            "__init__",
            _fail_initialization,
        )
        acquire_task = asyncio.create_task(lifespan_module._acquire_unified_food_database())
        await second_started.wait()
        acquire_task.cancel()
        with pytest.raises(
            asyncio.CancelledError,
            match=f"^{unified_db_module.UNIFIED_FOOD_CLEANUP_CANCELLED_MESSAGE}$",
        ) as exc_info:
            await acquire_task
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert (
            str(exc_info.value.__cause__)
            == unified_db_module.UNIFIED_FOOD_INITIALIZATION_ERROR_MESSAGE
        )
        assert exc_info.value.__cause__.__cause__ is None

    asyncio.run(_scenario())
    assert attempted == ["first", "second"]
    assert unified_db_module._read_unified_db_instance() is None
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0


@pytest.mark.parametrize("process_first", [True, False])
def test_partial_unified_food_acquisition_uses_process_cancel_ordinary_chain(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    process_first: bool,
) -> None:
    attempted: list[str] = []

    class _ProcessClient:
        async def close(self) -> None:
            attempted.append("process")
            raise KeyboardInterrupt("raw-process")

    class _CancelClient:
        async def close(self) -> None:
            attempted.append("cancel")
            raise asyncio.CancelledError("raw-cancel")

    def _fail_initialization(
        instance: UnifiedFoodDatabase,
        cache_dir: str | None = None,
        *,
        create_cache_dir: bool = True,
    ) -> None:
        del cache_dir
        assert create_cache_dir is False
        clients = (_ProcessClient(), _CancelClient())
        if not process_first:
            clients = (clients[1], clients[0])
        instance.usda_client, instance.off_client = clients
        raise RuntimeError("raw-initialization")

    async def _scenario() -> KeyboardInterrupt:
        try:
            await lifespan_module._acquire_unified_food_database()
        except KeyboardInterrupt as error:
            return error
        raise AssertionError("process-tier cleanup signal must propagate")

    _replace_registered_unified_food(None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
    monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)
    monkeypatch.setattr(
        unified_db_module.UnifiedFoodDatabase,
        "__init__",
        _fail_initialization,
    )
    process_error = asyncio.run(_scenario())

    assert attempted == (["process", "cancel"] if process_first else ["cancel", "process"])
    assert str(process_error) == ""
    assert process_error.__context__ is None
    cancellation = process_error.__cause__
    assert isinstance(cancellation, asyncio.CancelledError)
    assert str(cancellation) == unified_db_module.UNIFIED_FOOD_CLEANUP_CANCELLED_MESSAGE
    initialization = cancellation.__cause__
    assert isinstance(initialization, RuntimeError)
    assert str(initialization) == unified_db_module.UNIFIED_FOOD_INITIALIZATION_ERROR_MESSAGE
    assert initialization.__cause__ is None
    assert "raw-" not in caplog.text


def test_unified_food_client_cleanup_skips_missing_duplicate_and_noncallable_clients() -> None:
    client = _ClosingClient()
    missing = cast(
        UnifiedFoodDatabase,
        SimpleNamespace(usda_client=None, off_client=SimpleNamespace(close=None)),
    )
    duplicate = cast(
        UnifiedFoodDatabase,
        SimpleNamespace(usda_client=client, off_client=client),
    )

    asyncio.run(unified_db_module.close_unified_food_clients(missing))
    asyncio.run(unified_db_module.close_unified_food_clients(duplicate))

    assert client.close_calls == 1


def test_unified_food_external_cancellation_outranks_earlier_close_error() -> None:
    attempted: list[str] = []

    class _FirstClient:
        async def close(self) -> None:
            attempted.append("first")
            raise RuntimeError("first close failed")

    class _SecondClient:
        def __init__(self, started: asyncio.Event) -> None:
            self.started = started

        async def close(self) -> None:
            attempted.append("second")
            self.started.set()
            await asyncio.Event().wait()

    async def _scenario() -> None:
        second_started = asyncio.Event()
        instance = cast(
            UnifiedFoodDatabase,
            SimpleNamespace(
                usda_client=_FirstClient(),
                off_client=_SecondClient(second_started),
            ),
        )
        cleanup_task = asyncio.create_task(unified_db_module.close_unified_food_clients(instance))
        await second_started.wait()
        cleanup_task.cancel()
        with pytest.raises(
            asyncio.CancelledError,
            match=f"^{unified_db_module.UNIFIED_FOOD_CLEANUP_CANCELLED_MESSAGE}$",
        ) as exc_info:
            await cleanup_task
        assert isinstance(
            exc_info.value.__cause__,
            unified_db_module.UnifiedFoodClientCleanupError,
        )
        assert str(exc_info.value.__cause__) == unified_db_module.UNIFIED_FOOD_CLEANUP_ERROR_MESSAGE
        assert exc_info.value.__cause__.__cause__ is None
        assert cleanup_task.cancelling() == 1

    asyncio.run(_scenario())
    assert attempted == ["first", "second"]


def test_unified_food_acquisition_race_rejects_replacement_and_closes_only_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_usda = _ClosingClient(RuntimeError("local close failed"))
    local_off = _ClosingClient()
    replacement = cast(UnifiedFoodDatabase, SimpleNamespace())

    def _initialize_with_replacement(
        instance: UnifiedFoodDatabase,
        cache_dir: str | None = None,
        *,
        create_cache_dir: bool = True,
    ) -> None:
        del cache_dir
        assert create_cache_dir is False
        instance.usda_client = local_usda
        instance.off_client = local_off
        _replace_registered_unified_food(replacement)

    _replace_registered_unified_food(None)
    monkeypatch.setattr(
        unified_db_module.UnifiedFoodDatabase,
        "__init__",
        _initialize_with_replacement,
    )

    with pytest.raises(
        RuntimeError,
        match="^Unified-food singleton changed during acquisition$",
    ):
        asyncio.run(lifespan_module._acquire_unified_food_database())

    assert local_usda.close_calls == 1
    assert local_off.close_calls == 1
    assert unified_db_module._read_unified_db_instance() is replacement
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0


def test_unified_food_acquisition_race_cleanup_cancellation_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[str] = []
    replacement = cast(UnifiedFoodDatabase, SimpleNamespace())

    class _FirstClient:
        async def close(self) -> None:
            attempted.append("first")
            raise RuntimeError("first close failed")

    class _SecondClient:
        def __init__(self, started: asyncio.Event) -> None:
            self.started = started

        async def close(self) -> None:
            attempted.append("second")
            self.started.set()
            await asyncio.Event().wait()

    async def _scenario() -> None:
        second_started = asyncio.Event()

        def _initialize_with_replacement(
            instance: UnifiedFoodDatabase,
            cache_dir: str | None = None,
            *,
            create_cache_dir: bool = True,
        ) -> None:
            del cache_dir
            assert create_cache_dir is False
            instance.usda_client = _FirstClient()
            instance.off_client = _SecondClient(second_started)
            _replace_registered_unified_food(replacement)

        _replace_registered_unified_food(None)
        monkeypatch.setattr(lifespan_module, "_managed_unified_food_instance", None)
        monkeypatch.setattr(lifespan_module, "_managed_unified_food_active_leases", 0)
        monkeypatch.setattr(
            unified_db_module.UnifiedFoodDatabase,
            "__init__",
            _initialize_with_replacement,
        )

        acquire_task = asyncio.create_task(lifespan_module._acquire_unified_food_database())
        await second_started.wait()
        acquire_task.cancel()
        with pytest.raises(
            asyncio.CancelledError,
            match=f"^{unified_db_module.UNIFIED_FOOD_CLEANUP_CANCELLED_MESSAGE}$",
        ) as exc_info:
            await acquire_task
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert str(exc_info.value.__cause__) == "Unified-food singleton changed during acquisition"
        assert exc_info.value.__cause__.__cause__ is None

    asyncio.run(_scenario())
    assert attempted == ["first", "second"]
    assert unified_db_module._read_unified_db_instance() is replacement
    assert lifespan_module._managed_unified_food_instance is None
    assert lifespan_module._managed_unified_food_active_leases == 0


def test_food_configuration_failure_prevents_scheduler_start() -> None:
    events: list[str] = []

    def _fail_configure(_app: FastAPI) -> FoodSearchLifecycleLease:
        events.append("food-configure")
        raise RuntimeError("food")

    hooks = replace(_base_hooks(events), configure_food_search=_fail_configure)

    with pytest.raises(RuntimeError, match="food"):
        _run_lifespan(hooks)

    assert events[-2:] == ["food-configure", "unified-release"]
    assert "scheduler-start:24" not in events
    assert "scheduler-stop" not in events


@pytest.mark.parametrize(
    ("testing", "ci", "force", "disable", "should_start"),
    [
        ("true", None, None, None, False),
        (None, "true", None, None, False),
        ("true", None, "true", None, True),
        ("true", None, "true", "true", False),
        (None, None, None, None, True),
    ],
)
def test_scheduler_environment_precedence(
    monkeypatch: pytest.MonkeyPatch,
    testing: str | None,
    ci: str | None,
    force: str | None,
    disable: str | None,
    should_start: bool,
) -> None:
    for name, value in {
        "TESTING": testing,
        "CI": ci,
        "FORCE_BACKGROUND_UPDATES": force,
        "DISABLE_BACKGROUND_UPDATES": disable,
    }.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    events: list[str] = []

    _run_lifespan(_base_hooks(events))

    assert ("scheduler-start:24" in events) is should_start
    if should_start:
        assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release"]
    else:
        assert "scheduler-stop" not in events
        assert events[-2:] == ["food-dispose", "unified-release"]


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, 10.0),
        ("0.25", 0.25),
        ("60", 60.0),
        ("bad", 10.0),
        ("0", 10.0),
        ("-1", 10.0),
        ("61", 10.0),
        ("nan", 10.0),
        ("inf", 10.0),
        ("-inf", 10.0),
    ],
)
def test_background_timeout_is_finite_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str | None,
    expected: float,
) -> None:
    if raw_value is None:
        monkeypatch.delenv("BACKGROUND_START_TIMEOUT_SEC", raising=False)
    else:
        monkeypatch.setenv("BACKGROUND_START_TIMEOUT_SEC", raw_value)

    assert lifespan_module._background_start_timeout_seconds() == expected


def test_timeout_cancels_and_drains_start_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancelled = False

    async def _start(update_interval_hours: int = 24) -> None:
        nonlocal cancelled
        assert update_interval_hours == 24
        try:
            await asyncio.Event().wait()
        finally:
            cancelled = True

    async def _timeout(task: asyncio.Task[None], *, timeout: float) -> None:
        assert timeout == 10.0
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        raise TimeoutError

    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    monkeypatch.setattr(lifespan_module.asyncio, "wait_for", _timeout)
    events: list[str] = []
    hooks = replace(_base_hooks(events), start_background_updates=_start)

    _run_lifespan(hooks)

    assert cancelled is True
    assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release"]


def test_drain_cancelled_task_cancels_a_pending_task() -> None:
    async def _scenario() -> None:
        async def _wait_forever() -> None:
            await asyncio.Event().wait()

        task = asyncio.create_task(_wait_forever())
        await asyncio.sleep(0)
        await lifespan_module._drain_cancelled_task(task)
        assert task.cancelled()

    asyncio.run(_scenario())


def test_scheduler_start_cancellation_propagates_after_drain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stopped = False

    async def _start(update_interval_hours: int = 24) -> None:
        assert update_interval_hours == 24
        await asyncio.Event().wait()

    async def _stop() -> None:
        nonlocal stopped
        stopped = True

    async def _scenario() -> None:
        monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
        task = asyncio.create_task(
            lifespan_module._start_background_updates_best_effort(
                _start,
                failed_start_stopper=_stop,
            )
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_scenario())
    assert stopped is True


def test_failed_scheduler_start_cleanup_never_masks_primary_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _stop() -> None:
        raise asyncio.CancelledError

    with caplog.at_level("ERROR", logger="app.bootstrap.lifespan"):
        asyncio.run(lifespan_module._stop_after_failed_background_start(_stop))

    assert "Error cleaning up a failed background scheduler start" in caplog.text


def test_failed_scheduler_start_cleanup_contains_non_cancellation_base_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _stop() -> None:
        raise KeyboardInterrupt

    with caplog.at_level("ERROR", logger="app.bootstrap.lifespan"):
        asyncio.run(lifespan_module._stop_after_failed_background_start(_stop))

    assert "Error cleaning up a failed background scheduler start" in caplog.text


def test_failed_scheduler_start_cleanup_propagates_external_cancellation() -> None:
    async def _scenario() -> None:
        stop_started = asyncio.Event()

        async def _stop() -> None:
            stop_started.set()
            await asyncio.Event().wait()

        cleanup_task = asyncio.create_task(
            lifespan_module._stop_after_failed_background_start(_stop)
        )
        await stop_started.wait()
        cleanup_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cleanup_task

    asyncio.run(_scenario())


def test_body_exception_is_not_masked_by_cleanup_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _stop() -> None:
        events.append("scheduler-stop")
        raise RuntimeError("stop failed")

    def _dispose(_app: FastAPI, _lease: FoodSearchLifecycleLease) -> None:
        events.append("food-dispose")
        raise RuntimeError("dispose failed")

    async def _body() -> None:
        raise ValueError("body failed")

    hooks = replace(
        _base_hooks(events),
        stop_background_updates=_stop,
        dispose_food_search=_dispose,
    )
    with pytest.raises(ValueError, match="body failed"):
        _run_lifespan(hooks, body=_body)

    assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release"]


def test_unified_food_cleanup_error_never_masks_body_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _release(_lease: UnifiedFoodLifecycleLease) -> None:
        events.append("unified-release-failed")
        raise RuntimeError("unified release failed")

    async def _body() -> None:
        raise ValueError("body failed")

    hooks = replace(
        _base_hooks(events),
        release_unified_food=_release,
    )
    with caplog.at_level("ERROR", logger="app.bootstrap.lifespan"):
        with pytest.raises(ValueError, match="body failed"):
            _run_lifespan(hooks, body=_body)

    assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release-failed"]
    assert "Error releasing unified-food resources" in caplog.text


def test_unified_food_cleanup_cancellation_propagates_without_primary_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _release(_lease: UnifiedFoodLifecycleLease) -> None:
        events.append("unified-release-cancelled")
        raise asyncio.CancelledError

    hooks = replace(
        _base_hooks(events),
        release_unified_food=_release,
    )
    with pytest.raises(asyncio.CancelledError):
        _run_lifespan(hooks)

    assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release-cancelled"]


def test_unified_food_cleanup_cancellation_does_not_mask_body_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _release(_lease: UnifiedFoodLifecycleLease) -> None:
        events.append("unified-release-cancelled")
        raise asyncio.CancelledError

    async def _body() -> None:
        raise ValueError("body failed")

    hooks = replace(_base_hooks(events), release_unified_food=_release)
    with caplog.at_level("ERROR", logger="app.bootstrap.lifespan"):
        with pytest.raises(ValueError, match="body failed"):
            _run_lifespan(hooks, body=_body)

    assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release-cancelled"]
    assert "Unified-food shutdown was cancelled" in caplog.text


def test_stop_cancellation_does_not_mask_body_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _stop() -> None:
        events.append("scheduler-stop")
        raise asyncio.CancelledError

    async def _body() -> None:
        raise ValueError("body failed")

    hooks = replace(_base_hooks(events), stop_background_updates=_stop)
    with pytest.raises(ValueError, match="body failed"):
        _run_lifespan(hooks, body=_body)

    assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release"]


def test_stop_cancellation_propagates_without_primary_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _stop() -> None:
        events.append("scheduler-stop")
        raise asyncio.CancelledError

    hooks = replace(_base_hooks(events), stop_background_updates=_stop)
    with pytest.raises(asyncio.CancelledError):
        _run_lifespan(hooks)

    assert events[-3:] == ["scheduler-stop", "food-dispose", "unified-release"]


def test_body_cancellation_propagates_after_reverse_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _body() -> None:
        events.append("body")
        raise asyncio.CancelledError("body cancelled")

    with pytest.raises(asyncio.CancelledError, match="body cancelled"):
        _run_lifespan(_base_hooks(events), body=_body)

    assert events[-4:] == ["body", "scheduler-stop", "food-dispose", "unified-release"]


def test_scheduler_start_exception_logs_continues_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")
    events: list[str] = []

    async def _start(update_interval_hours: int = 24) -> None:
        assert update_interval_hours == 24
        events.append("scheduler-start-failed")
        raise RuntimeError("start failed")

    async def _body() -> None:
        events.append("body")

    hooks = replace(_base_hooks(events), start_background_updates=_start)
    with caplog.at_level("ERROR", logger="app.bootstrap.lifespan"):
        _run_lifespan(hooks, body=_body)

    assert "Failed to start background updates" in caplog.text
    assert events[-5:] == [
        "scheduler-start-failed",
        "scheduler-stop",
        "body",
        "food-dispose",
        "unified-release",
    ]


@pytest.mark.parametrize("body_raises", [False, True])
def test_legacy_created_app_runs_real_food_search_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    body_raises: bool,
) -> None:
    import app
    import app.bootstrap.food_search as food_search_module
    import app.main as app_main
    import legacy_app
    from app.bootstrap.lifespan import application_lifespan
    from app.services import food_store

    class _PreviousBackend:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            del query, limit, offset
            return []

    class _Client:
        def __init__(self) -> None:
            self.is_closed = False

        def close(self) -> None:
            self.is_closed = True

    previous_backend = _PreviousBackend()
    clients: list[_Client] = []

    def _client_factory() -> _Client:
        client = _Client()
        clients.append(client)
        return client

    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    monkeypatch.setattr(food_search_module, "_build_meili_http_client", _client_factory)
    food_store.register_strategy_search_backend_adapter(previous_backend)
    try:
        assert app.lifespan is application_lifespan
        assert legacy_app.lifespan is application_lifespan
        assert app.app is legacy_app.app
        assert app_main.app is legacy_app.app

        if body_raises:
            with pytest.raises(RuntimeError, match="body failed"):
                with TestClient(legacy_app.app):
                    assert food_store.get_registered_strategy_search_backend_adapter() is not (
                        previous_backend
                    )
                    assert clients and clients[-1].is_closed is False
                    raise RuntimeError("body failed")
        else:
            with TestClient(legacy_app.app):
                assert food_store.get_registered_strategy_search_backend_adapter() is not (
                    previous_backend
                )
                assert clients and clients[-1].is_closed is False

        assert clients[-1].is_closed is True
        assert getattr(legacy_app.app.state, "meili_http_client", None) is None
        assert getattr(legacy_app.app.state, "meili_http_shutdown_event", None) is None
        assert food_store.get_registered_strategy_search_backend_adapter() is previous_backend
    finally:
        food_store.reset_strategy_search_backend_adapter()


@pytest.mark.parametrize(
    "scheduler_mode",
    [SchedulerMode.EXTERNAL, SchedulerMode.DISABLED],
)
def test_non_in_process_modes_never_start_or_stop_scheduler_hooks(
    monkeypatch: pytest.MonkeyPatch,
    scheduler_mode: SchedulerMode,
) -> None:
    events: list[str] = []
    monkeypatch.setenv("FORCE_BACKGROUND_UPDATES", "true")

    async def _body() -> None:
        events.append("body")

    _run_lifespan(
        _base_hooks(events),
        body=_body,
        scheduler_mode=scheduler_mode,
    )

    assert events == [
        "guards",
        "database",
        "fallback-clear",
        "templates",
        "unified-acquire",
        "food-configure",
        "body",
        "food-dispose",
        "unified-release",
    ]


def test_external_default_hooks_do_not_import_scheduler_execution_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_loaded() -> tuple[object, object]:
        raise AssertionError("external API process must not load scheduler hooks")

    monkeypatch.setattr(lifespan_module, "_load_background_update_hooks", fail_if_loaded)

    hooks = lifespan_module.build_default_lifespan_hooks(scheduler_mode=SchedulerMode.EXTERNAL)

    assert hooks.start_background_updates is lifespan_module._unavailable_background_update_start
    assert hooks.stop_background_updates is lifespan_module._unavailable_background_update_stop


def test_in_process_default_hooks_load_scheduler_execution_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _start(update_interval_hours: int = 24) -> None:
        assert update_interval_hours == 24

    async def _stop() -> None:
        return None

    monkeypatch.setattr(
        lifespan_module,
        "_load_background_update_hooks",
        lambda: (_start, _stop),
    )

    hooks = lifespan_module.build_default_lifespan_hooks(
        scheduler_mode=SchedulerMode.IN_PROCESS_DEV,
    )

    assert hooks.start_background_updates is _start
    assert hooks.stop_background_updates is _stop


@pytest.mark.parametrize(
    ("relative_path", "expected_image", "expected_environment"),
    [
        (
            "deploy/docker-compose.production.yaml",
            "${IMAGE_REF:?IMAGE_REF is required}",
            "ENVIRONMENT=production",
        ),
        (
            "deploy/docker-compose.production.selfhosted.yaml",
            "${IMAGE_REF:?IMAGE_REF is required}",
            "ENVIRONMENT=production",
        ),
        (
            "deploy/docker-compose.staging.yaml",
            "${STAGING_IMAGE_REF:?STAGING_IMAGE_REF is required}",
            "ENVIRONMENT=staging",
        ),
    ],
)
def test_compose_uses_one_no_ingress_worker_from_exact_backend_image(
    relative_path: str,
    expected_image: str,
    expected_environment: str,
) -> None:
    compose = yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    services = compose["services"]
    app_service = services["app"]
    worker = services["worker"]

    assert worker["image"] == expected_image
    assert worker["image"] == app_service["image"]
    assert worker["command"] == "python -m core.food_apis.scheduler --serve"
    assert worker["depends_on"]["app"]["condition"] == "service_healthy"
    assert worker["healthcheck"] == {"disable": True}
    assert worker["profiles"] == ["scheduler-external"]
    assert worker["restart"] == "unless-stopped"
    assert "ports" not in worker
    assert "expose" not in worker
    assert "env_file" not in worker

    worker_environment = set(worker["environment"])
    app_environment = set(app_service["environment"])
    assert expected_environment in worker_environment
    mode_contract = "FOOD_UPDATE_SCHEDULER_MODE=${FOOD_UPDATE_SCHEDULER_MODE:-external}"
    assert mode_contract in worker_environment
    assert mode_contract in app_environment
    assert "food_db_cache:/app/cache/food_db" in worker["volumes"]
    assert "food_db_cache:/app/cache/food_db" in app_service["volumes"]
    assert "food_db_cache" in compose["volumes"]


def test_deploy_scripts_quiesce_migrate_start_and_prove_worker_in_order() -> None:
    production_lines = (
        (REPO_ROOT / "scripts/deploy_production.sh").read_text(encoding="utf-8").splitlines()
    )
    production_order = [
        "sync_shell_bundle compose-only",
        "dc config --quiet",
        "dc pull app",
        "dc pull worker",
        "dc stop worker",
        "  dc rm -f worker",
        "if dc run --rm --no-deps app alembic upgrade head; then",
        "sync_shell_bundle",
        "dc up -d --remove-orphans app",
        "  dc up -d --pull never --wait --wait-timeout 30 worker",
        "dc up -d --remove-orphans caddy",
        "  dc up -d --pull never --no-recreate --wait --wait-timeout 30 worker",
    ]
    production_indexes = _ordered_indexes(
        "scripts/deploy_production.sh",
        production_lines,
        production_order,
    )
    assert production_indexes == sorted(production_indexes)
    assert 'if [ "$FOOD_UPDATE_SCHEDULER_MODE" = "external" ]; then' in production_lines
    assert (
        '  echo "Scheduler mode is disabled; worker container remains absent"' in production_lines
    )
    assert (
        '      echo "❌ Production deploy forbids FOOD_UPDATE_SCHEDULER_MODE=in_process_dev" >&2'
    ) in production_lines

    staging_lines = (REPO_ROOT / "scripts/deploy.sh").read_text(encoding="utf-8").splitlines()
    staging_order = [
        '"${COMPOSE[@]}" pull worker',
        '"${COMPOSE[@]}" stop worker',
        '  "${COMPOSE[@]}" rm -f worker',
        'echo "[3/5] Start Postgres and create a pre-migration backup"',
        'if "${COMPOSE[@]}" run --rm --no-deps app alembic upgrade head; then',
        '"${COMPOSE[@]}" up -d --pull never app',
        '  "${COMPOSE[@]}" up -d --pull never --wait --wait-timeout 30 worker',
        '"${COMPOSE[@]}" up -d --pull never caddy',
        ('  "${COMPOSE[@]}" up -d --pull never --no-recreate --wait --wait-timeout 30 worker'),
    ]
    staging_indexes = _ordered_indexes(
        "scripts/deploy.sh",
        staging_lines,
        staging_order,
    )
    assert staging_indexes == sorted(staging_indexes)
    assert 'if [ "$FOOD_UPDATE_SCHEDULER_MODE" = "external" ]; then' in staging_lines
    assert '  echo "Scheduler mode is disabled; worker container remains absent"' in staging_lines
    assert (
        '    echo "❌ Staging deploy forbids FOOD_UPDATE_SCHEDULER_MODE=in_process_dev" >&2'
    ) in staging_lines


def test_scheduler_worker_module_has_no_api_ingress_dependencies() -> None:
    scheduler_path = REPO_ROOT / "core/food_apis/scheduler.py"
    tree = ast.parse(scheduler_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            imported_modules.add(node.module)

    forbidden_roots = {"app", "fastapi", "starlette", "uvicorn"}
    violations = {
        module for module in imported_modules if module.split(".", maxsplit=1)[0] in forbidden_roots
    }
    assert not violations, f"scheduler worker must not import API ingress modules: {violations}"

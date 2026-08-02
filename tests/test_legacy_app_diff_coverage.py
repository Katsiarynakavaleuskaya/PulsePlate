# -*- coding: utf-8 -*-
"""
RU: Тесты для diff-coverage по legacy_app.py (точечно исполняем ветки из CI missing-list).
EN: Tests for diff-coverage on legacy_app.py (execute branches reported missing by CI).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import importlib
import logging
import math
from pathlib import Path
import sys
from typing import Any, Callable

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine

from app.routers import legacy_premium_weekly_plan
from app.routers import health as health_router
import app.services.bmi_compat as bmi_compat_service
import app.services.legacy_premium_weekly_plan as weekly_plan_service
from app.services import pro_nutrition_plate as plate_service
import legacy_app
from tests.helpers.module_resolve import resolve_module


class _InsightProviderStub:
    name = "stub"

    async def generate(self, text: str) -> str:
        return text


@dataclass
class _StructuredRAGChunkStub:
    chunk_id: str
    file: str
    content: str
    score: float
    hop: int = 1


@dataclass
class _StructuredRAGContextStub:
    query: str
    refined_queries: list[str]
    chunks: list[_StructuredRAGChunkStub]
    confidence: float
    hops: int
    latency_ms: int
    agent_id: str | None = None
    user_tier: str | None = None


def _patch_stub_insight_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    insight_compat = resolve_module("app.services.insight_compat")
    monkeypatch.setattr(
        insight_compat,
        "_load_llm_get_provider",
        lambda: (lambda: _InsightProviderStub()),
        raising=True,
    )


def _patch_structured_rag_context(
    monkeypatch: pytest.MonkeyPatch,
    *,
    query: str,
    content: str,
) -> None:
    import core.rag.vector_rag as vector_rag

    def _fake_structured(*_a: object, **_k: object) -> _StructuredRAGContextStub:
        return _StructuredRAGContextStub(
            query=query,
            refined_queries=[query],
            chunks=[
                _StructuredRAGChunkStub(
                    chunk_id="a:1",
                    file="a.md",
                    content=content,
                    score=0.9,
                )
            ],
            confidence=0.9,
            hops=1,
            latency_ms=10,
        )

    monkeypatch.setattr(vector_rag, "retrieve_context_structured", _fake_structured)


def _patch_long_prompt_orchestration(
    monkeypatch: pytest.MonkeyPatch,
    *,
    prompt: str,
) -> None:
    from core.rag.contracts import RAGChunk
    from core.rag.orchestration import RAGOrchestrationResult
    import core.rag.orchestration as orch_mod

    chunk = RAGChunk(chunk_id="a:1", file="a.md", content="ctx", score=0.9)

    async def _mock_orchestration(*_a: object, **_k: object) -> RAGOrchestrationResult:
        return RAGOrchestrationResult(
            chunks=[chunk],
            formatted_prompt=prompt,
            rag_actually_used=True,
            confidence=0.9,
            hops=1,
            latency_ms=10,
            warnings=[],
            chunks_retrieved=1,
            chunks_filtered=0,
        )

    monkeypatch.setattr(orch_mod, "retrieve_and_validate_rag", _mock_orchestration)


def _legacy_week_plan_request() -> legacy_app.LegacyWeekPlanRequest:
    return legacy_app.LegacyWeekPlanRequest.model_construct(
        sex="female",
        age=30,
        height_cm=168.0,
        weight_kg=62.0,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
        targets=None,
        life_stage=None,
        lang="en",
    )


def test_week_plan_schema_preserves_legacy_aliases_and_request_modes() -> None:
    """Cover the canonical schema through the legacy_app compatibility export."""

    base_payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168.0,
        "weight_kg": 62.0,
        "activity": "moderate",
    }

    assert (
        legacy_app.LegacyWeekPlanRequest.model_validate(
            {**base_payload, "goal": "weight_loss"}
        ).goal
        == "loss"
    )
    assert (
        legacy_app.LegacyWeekPlanRequest.model_validate(
            {**base_payload, "goal": "maintenance"}
        ).goal
        == "maintain"
    )
    assert (
        legacy_app.LegacyWeekPlanRequest.model_validate(
            {**base_payload, "goal": "weight_gain"}
        ).goal
        == "gain"
    )
    with pytest.raises(ValidationError):
        legacy_app.LegacyWeekPlanRequest.model_validate({**base_payload, "goal": "unsupported"})
    with pytest.raises(ValidationError, match="Invalid targets payload"):
        legacy_app.LegacyWeekPlanRequest.model_validate(
            {
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein": "bad"},
                    "micro": {},
                    "water_ml": 1000,
                }
            }
        )
    with pytest.raises(ValidationError, match="Either 'targets' must be provided"):
        legacy_app.LegacyWeekPlanRequest.model_validate({"goal": "maintain"})

    request = legacy_app.LegacyWeekPlanRequest.model_construct(targets={"calories": 1800})
    assert legacy_app.LegacyWeekPlanRequest._normalize_values(request) is request


def test_week_plan_response_builder_filters_and_normalizes_malformed_values() -> None:
    """Cover legacy weekly-menu response normalization through the public service seam."""

    huge_number = 10**1000

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                "bad-day-entry",
                {"date": "", "meals": [], "total_kcal": 0, "daily_cost": 0},
                {
                    "date": "2026-03-09",
                    "meals": "bad-meals",
                    "total_kcal": 0,
                    "daily_cost": 0,
                },
                {
                    "date": "2026-03-10",
                    "meals": [
                        {"title": "Breakfast", "kcal": True},
                        {"title": "Snack", "kcal": math.nan},
                        {"title": "Dinner", "kcal": huge_number},
                        {"title": "Lunch", "kcal": 420},
                    ],
                    "total_kcal": huge_number,
                    "daily_cost": math.inf,
                    "estimated_cost": 14.5,
                },
                {
                    "date": "2026-03-11",
                    "meals": [],
                    "total_kcal": 500,
                    "daily_cost": 20.0,
                },
            ],
            "weekly_coverage": "bad-map",
            "shopping_list": {
                "oats": huge_number,
                "rice": 250.0,
                123: 5.0,
                "salt": True,
                "oil": math.inf,
            },
            "total_cost": huge_number,
            "adherence_score": True,
        }
    )

    assert [day["date"] for day in response.daily_menus] == [
        "2026-03-10",
        "2026-03-11",
    ]
    assert response.daily_menus[0]["total_kcal"] == 420.0
    assert response.daily_menus[0]["daily_cost"] == 14.5
    assert response.daily_menus[1]["total_kcal"] == 500.0
    assert response.daily_menus[1]["daily_cost"] == 20.0
    assert response.week_summary["total_days"] == 2
    assert response.week_summary["avg_daily_cost"] == 17.25
    assert response.weekly_coverage == {}
    assert response.shopping_list == {"rice": 250.0}
    assert response.total_cost == 0.0
    assert response.adherence_score == 0.0

    non_numeric_response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "daily_menus": [],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": "bad",
            "adherence_score": "bad",
        }
    )

    assert non_numeric_response.total_cost == 0.0
    assert non_numeric_response.adherence_score == 0.0


def test_language_cookie_has_samesite_and_secure_guard() -> None:
    """Security: language cookie must include SameSite and Secure-on-HTTPS guard."""
    client = TestClient(legacy_app.app)
    resp = client.get("/legacy/bmi-calculator")
    assert resp.status_code == 200
    assert "SameSite=Lax" in resp.text
    assert "window.location.protocol === 'https:'" in resp.text
    assert "; Secure" in resp.text


def test_readiness_logs_warning_when_insight_runtime_probe_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _run() -> None:
        """Cover `/ready` fallback when insight runtime readiness probe raises."""

        async def _database_health_stub(*, session: Any) -> dict[str, Any]:
            assert session is None
            return {"status": "ok"}

        def _raise_runtime_probe() -> dict[str, Any]:
            raise RuntimeError("insight runtime boom")

        import llm

        monkeypatch.setattr(health_router, "database_health", _database_health_stub)
        monkeypatch.setattr(llm, "get_insight_runtime_readiness", _raise_runtime_probe)

        with caplog.at_level(logging.WARNING):
            payload = await health_router.ready(session=None)

        assert payload["status"] == "ok"
        assert payload["insight_runtime"] == {"status": "unavailable"}
        assert any(
            "Insight runtime readiness unavailable" in record.message for record in caplog.records
        )

    asyncio.run(_run())


def test_export_daily_csv_preserves_503_when_helper_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure 503 helper-missing isn't wrapped into a 500."""
    client = TestClient(legacy_app.app)

    # Ensure helper resolves to a non-callable, triggering the explicit 503.
    import app as app_pkg

    monkeypatch.setattr(app_pkg, "to_csv_day", None, raising=False)
    monkeypatch.setattr(legacy_app, "to_csv_day", None, raising=False)

    resp = client.get("/api/v1/premium/exports/day/test.csv", headers={"x-api-key": "test_key"})
    assert resp.status_code == 503


def test_aggregate_day_micros_accepts_sync_callable() -> None:
    """Canonical Plate aggregation supports an explicit synchronous dependency."""
    result = asyncio.run(
        plate_service.aggregate_day_micros(
            meals=[],
            aggregator=lambda _meals: {"iron_mg": 1.0},
        )
    )

    assert result == {"iron_mg": 1.0}


def test_legacy_scheduler_stop_wrapper_executes() -> None:
    """Covers the wrapper that delegates to app.scheduler_helpers.resolve_stop_callable."""
    from app.scheduler_helpers import resolve_stop_callable

    stopper = resolve_stop_callable(
        pkg=None,
        alias_pkg=None,
        globs=legacy_app.__dict__,
        default_stopper=legacy_app._scheduler_stop_background_updates,
    )
    assert callable(stopper)


def test_get_update_scheduler_delegates_to_core_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        """The compatibility export delegates through the lazy service seam."""

        async def _late_getter() -> Any:
            return object()

        import core.food_apis.scheduler as sched

        monkeypatch.setattr(sched, "get_update_scheduler", _late_getter)
        res = await legacy_app.get_update_scheduler()
        assert res is not None

    asyncio.run(_run())


def test_configure_session_bindings_sets_sessionlocal_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover SessionLocal assignment in core.db_fallback._configure_session_bindings.

    Fallback mutates core.db (core/db.py); save/restore globals and ENV for isolation.
    """
    import os

    from core import db as core_db
    from core.db_fallback import _configure_session_bindings
    from core.db_fallback import reset_fallback_state

    orig_sessionlocal = core_db.SessionLocal
    orig_raw_engine = getattr(core_db, "_RAW_ENGINE", None)
    orig_engine = getattr(core_db, "engine", None)
    env_keys = ("DB_HEALTH_DEGRADED", "DB_FALLBACK_URL", "DATABASE_URL")
    env_snapshot = {k: os.environ.get(k) for k in env_keys}
    try:
        for k in env_keys:
            monkeypatch.delenv(k, raising=False)
        core_db.SessionLocal = None
        engine = create_engine("sqlite:///:memory:")
        _configure_session_bindings(
            engine=engine,
            is_production=False,
            fallback_url="sqlite:///:memory:",
            env_name="test",
        )
        assert core_db.SessionLocal is not None
    finally:
        # Restore globals via direct assignment (NOT via monkeypatch) to avoid
        # monkeypatch teardown reverting to the fallback-mutated values.
        core_db.SessionLocal = orig_sessionlocal
        core_db._RAW_ENGINE = orig_raw_engine
        core_db.engine = orig_engine
        reset_fallback_state()
        for k, v in env_snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        # Re-initialize the canonical test DB bindings after fallback mutation
        # to prevent cross-test pollution (SessionLocal/env were temporarily rebound).
        core_db.init_db()


def test_configure_session_bindings_replaces_sessionlocal_on_repeat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover _configure_session_bindings: two calls replace SessionLocal (no .configure()).

    Fallback always recreates sessionmaker; restore core_db.SessionLocal and ENV in finally.
    """
    import os

    from core import db as core_db
    from core.db_fallback import _configure_session_bindings
    from core.db_fallback import reset_fallback_state

    orig_sessionlocal = getattr(core_db, "SessionLocal", None)
    orig_raw_engine = getattr(core_db, "_RAW_ENGINE", None)
    orig_engine = getattr(core_db, "engine", None)
    orig_env = {
        k: os.environ.get(k) for k in ("DB_HEALTH_DEGRADED", "DB_FALLBACK_URL", "DATABASE_URL")
    }
    try:
        engine1 = create_engine("sqlite:///:memory:", future=True)
        engine2 = create_engine("sqlite:///:memory:", future=True)
        _configure_session_bindings(
            engine=engine1,
            is_production=False,
            fallback_url="sqlite:///:memory:",
            env_name="test",
        )
        _configure_session_bindings(
            engine=engine2,
            is_production=False,
            fallback_url="sqlite:///:memory:",
            env_name="test",
        )
        assert core_db.SessionLocal is not None
    finally:
        core_db.SessionLocal = orig_sessionlocal
        core_db._RAW_ENGINE = orig_raw_engine
        core_db.engine = orig_engine
        reset_fallback_state()
        for k, v in orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        core_db.init_db()


def test_bmi_request_normalizes_with_visualization_values() -> None:
    """Cover BMIRequest normalization for with_visualization -> include_chart."""
    payload: dict[str, Any] = {
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "with_visualization": "yes",
    }
    m = legacy_app.BMIRequest.model_validate(payload)
    assert getattr(m, "include_chart", False) is True

    payload["with_visualization"] = "no"
    m2 = legacy_app.BMIRequest.model_validate(payload)
    assert getattr(m2, "include_chart", True) is False

    payload["with_visualization"] = "maybe"
    m3 = legacy_app.BMIRequest.model_validate(payload)
    assert getattr(m3, "include_chart", False) is True

    # Non-string branch (bool)
    payload["with_visualization"] = True
    m4 = legacy_app.BMIRequest.model_validate(payload)
    assert getattr(m4, "include_chart", False) is True


def test_add_visualization_calls_generate_bmi_visualization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover add_visualization_if_requested call into viz function (line ~1479)."""
    monkeypatch.setattr(bmi_compat_service, "MATPLOTLIB_AVAILABLE", True)

    def _viz(**_kw: Any) -> dict[str, Any]:
        return {"available": True, "ok": True}

    monkeypatch.setattr(bmi_compat_service, "generate_bmi_visualization", _viz)

    req = legacy_app.BMIRequest.model_validate(
        {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en",
            "with_visualization": "yes",
        }
    )
    result: dict[str, Any] = {"bmi": 24.2}
    legacy_app.add_visualization_if_requested(result, req)
    assert result.get("visualization", {}).get("available") is True


def test_insight_v1_rag_path_builds_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover RAG path in insight_v1 where ctx is retrieved and prompt is rebuilt."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")

        _patch_stub_insight_provider(monkeypatch)
        _patch_structured_rag_context(monkeypatch, query="question", content="ctx")

        req = legacy_app.InsightRequest(text="question")
        out = await legacy_app.insight_v1(req)
        assert out.provider == "stub"
        assert "Context:" in out.insight

    asyncio.run(_run())


def test_insight_v1_trims_prompt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover prompt_text trimming in insight_v1 (line ~2159)."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")

        _patch_stub_insight_provider(monkeypatch)
        long_prompt = "x" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH + 5)
        _patch_long_prompt_orchestration(monkeypatch, prompt=long_prompt)

        out = await legacy_app.insight_v1(legacy_app.InsightRequest(text="q"))
        assert len(out.insight) == legacy_app.INSIGHT_TEXT_MAX_LENGTH

    asyncio.run(_run())


def test_legacy_insight_rag_path_trims(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover legacy /insight RAG branch and prompt trimming (lines ~2182-2202)."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")

        _patch_stub_insight_provider(monkeypatch)
        # Return a large context to force prompt trimming
        big_content = "c" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH * 2)
        _patch_structured_rag_context(monkeypatch, query="q", content=big_content)

        req = legacy_app.InsightRequest(text="q")
        out = await legacy_app.insight(req)
        assert out.provider == "stub"
        assert len(out.insight) <= legacy_app.INSIGHT_TEXT_MAX_LENGTH

    asyncio.run(_run())


def test_legacy_insight_trims_prompt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover prompt_text trimming in legacy insight (line ~2202)."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")

        _patch_stub_insight_provider(monkeypatch)
        long_prompt = "x" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH + 5)
        _patch_long_prompt_orchestration(monkeypatch, prompt=long_prompt)

        out = await legacy_app.insight(legacy_app.InsightRequest(text="q"))
        assert len(out.insight) == legacy_app.INSIGHT_TEXT_MAX_LENGTH

    asyncio.run(_run())


def test_week_plan_missing_required_fields_raises_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        """Cover the required-fields 422 branch inside api_weekly_menu.

        NOTE: WeekPlanRequest validators enforce required profile fields when targets is None.
        To exercise the handler's internal guard (diff-coverage), we bypass validation via
        model_construct.
        """
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
        req = legacy_app.LegacyWeekPlanRequest.model_construct(
            sex=None,
            age=None,
            height_cm=None,
            weight_kg=None,
            activity=None,
            goal="maintain",
            deficit_pct=None,
            surplus_pct=None,
            bodyfat=None,
            diet_flags=set(),
            targets=None,
            life_stage=None,
            lang="en",
        )
        with pytest.raises(HTTPException) as exc:
            await legacy_premium_weekly_plan.api_weekly_menu(req)
        assert exc.value.status_code == 422

    asyncio.run(_run())


def test_week_plan_rejects_explicitly_disabled_vip_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        monkeypatch.setenv("VIP_MODULE_ENABLED", "false")

        with pytest.raises(HTTPException) as exc:
            await legacy_premium_weekly_plan.api_weekly_menu(_legacy_week_plan_request())

        assert exc.value.status_code == 503
        assert exc.value.detail == "VIP module is disabled"

    asyncio.run(_run())


def test_week_plan_rejects_disabled_vip_module_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        monkeypatch.delenv("VIP_MODULE_ENABLED", raising=False)
        monkeypatch.setattr(legacy_premium_weekly_plan, "is_vip_module_enabled", lambda: False)

        with pytest.raises(HTTPException) as exc:
            await legacy_premium_weekly_plan.api_weekly_menu(_legacy_week_plan_request())

        assert exc.value.status_code == 503
        assert exc.value.detail == "VIP module is disabled"

    asyncio.run(_run())


def test_week_plan_rejects_missing_menu_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
        monkeypatch.setattr(
            legacy_premium_weekly_plan,
            "get_weekly_menu_builder",
            lambda: None,
        )

        with pytest.raises(HTTPException) as exc:
            await legacy_premium_weekly_plan.api_weekly_menu(_legacy_week_plan_request())

        assert exc.value.status_code == 503
        assert exc.value.detail == "Weekly menu generation feature not available"

    asyncio.run(_run())


def test_week_plan_handler_returns_normalized_weekly_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
        monkeypatch.setattr(
            legacy_premium_weekly_plan,
            "get_weekly_menu_builder",
            lambda: object(),
        )

        vip_router = importlib.import_module("app.routers.vip")

        async def _return_weekly_menu(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {
                "week_start": "2026-03-09",
                "daily_menus": [
                    {
                        "date": "2026-03-10",
                        "meals": [{"title": "Lunch", "kcal": 420}],
                        "total_kcal": 420,
                        "daily_cost": 12.25,
                    }
                ],
                "weekly_coverage": {"fiber": 0.84},
                "shopping_list": {"rice": 250.0},
                "total_cost": 12.25,
                "adherence_score": 0.1,
            }

        monkeypatch.setattr(
            vip_router,
            "execute_legacy_premium_week_alias_payload",
            _return_weekly_menu,
        )

        response = await legacy_premium_weekly_plan.api_weekly_menu(_legacy_week_plan_request())

        assert response.week_summary["week_start"] == "2026-03-09"
        assert response.daily_menus[0]["daily_cost"] == 12.25

    asyncio.run(_run())


def test_week_plan_wraps_value_error_with_client_safe_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
        monkeypatch.setattr(
            legacy_premium_weekly_plan,
            "get_weekly_menu_builder",
            lambda: object(),
        )

        vip_router = importlib.import_module("app.routers.vip")

        async def _raise_value_error(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise ValueError("internal validation detail")

        monkeypatch.setattr(
            vip_router,
            "execute_legacy_premium_week_alias_payload",
            _raise_value_error,
        )

        with pytest.raises(HTTPException) as exc:
            await legacy_premium_weekly_plan.api_weekly_menu(_legacy_week_plan_request())

        assert exc.value.status_code == 400
        assert exc.value.detail == "Invalid input"

    asyncio.run(_run())


def test_week_plan_wraps_unexpected_error_with_client_safe_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
        monkeypatch.setattr(
            legacy_premium_weekly_plan,
            "get_weekly_menu_builder",
            lambda: object(),
        )

        vip_router = importlib.import_module("app.routers.vip")

        async def _raise_runtime_error(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("internal runtime detail")

        monkeypatch.setattr(
            vip_router,
            "execute_legacy_premium_week_alias_payload",
            _raise_runtime_error,
        )

        with pytest.raises(HTTPException) as exc:
            await legacy_premium_weekly_plan.api_weekly_menu(_legacy_week_plan_request())

        assert exc.value.status_code == 500
        assert exc.value.detail == "Weekly menu generation failed"

    asyncio.run(_run())


def test_week_plan_registration_requires_api_key_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.main as app_main

    monkeypatch.setattr(app_main, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Legacy premium weekly-plan API key dependency is unavailable",
    ):
        app_main._include_legacy_premium_weekly_plan_router_if_needed(FastAPI())


def test_export_day_csv_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover export_daily_plan_csv exception handling (500 path)."""
        if not getattr(legacy_app, "EXPORTS_ENABLED", False):
            pytest.skip("Exports are not enabled in this environment.")

        async def _call() -> Any:
            return await legacy_app.export_daily_plan_csv("p1")

        def boom(_: Any) -> bytes:
            raise RuntimeError("boom")

        # Ensure dynamic helper resolution uses our boom() function.
        import app as app_pkg

        monkeypatch.setattr(app_pkg, "to_csv_day", boom, raising=False)
        monkeypatch.setattr(legacy_app, "to_csv_day", boom, raising=False)
        with pytest.raises(HTTPException) as exc:
            await _call()
        assert exc.value.status_code == 500

    asyncio.run(_run())


def test_export_week_csv_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover export_weekly_plan_csv exception -> 500."""
        if not getattr(legacy_app, "EXPORTS_ENABLED", False):
            pytest.skip("Exports are not enabled in this environment.")

        def boom(_: Any) -> bytes:
            raise RuntimeError("boom")

        monkeypatch.setattr(legacy_app, "to_csv_week", boom, raising=False)
        with pytest.raises(HTTPException) as exc:
            await legacy_app.export_weekly_plan_csv("p1")
        assert exc.value.status_code == 500

    asyncio.run(_run())


def test_export_day_csv_helper_missing_503(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover CSV helper-not-callable branch (line ~4915)."""
        if not getattr(legacy_app, "EXPORTS_ENABLED", False):
            pytest.skip("Exports are not enabled in this environment.")
        import app as app_pkg

        monkeypatch.setattr(app_pkg, "to_csv_day", None, raising=False)
        monkeypatch.setattr(legacy_app, "to_csv_day", None, raising=False)
        with pytest.raises(HTTPException) as exc:
            await legacy_app.export_daily_plan_csv("p1")
        # Preserve the explicit "helper missing" semantics as 503.
        assert exc.value.status_code == 503
        assert "CSV export helper is not available" in str(exc.value.detail)

    asyncio.run(_run())


def test_export_day_csv_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        """Cover CSV success path returning Response (line ~4919)."""
        if not getattr(legacy_app, "EXPORTS_ENABLED", False):
            pytest.skip("Exports are not enabled in this environment.")

        monkeypatch.setattr(legacy_app, "to_csv_day", lambda _p: b"a,b\n", raising=False)
        resp = await legacy_app.export_daily_plan_csv("p1")
        assert resp.media_type == "text/csv"

    asyncio.run(_run())


def test_export_week_csv_fallback_when_helper_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        """Cover weekly CSV fallback Response when helper missing (line ~5069)."""
        if not getattr(legacy_app, "EXPORTS_ENABLED", False):
            pytest.skip("Exports are not enabled in this environment.")

        monkeypatch.setattr(legacy_app, "to_csv_week", None, raising=False)
        resp = await legacy_app.export_weekly_plan_csv("p1")
        assert resp.media_type == "text/csv"
        assert b"plan_id" in resp.body

    asyncio.run(_run())


def test_rollback_database_coroutine_callable_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def _run() -> None:
        """Cover coroutine rollback_callable branch (line ~4782)."""

        class _UpdateManager:
            versions_file = tmp_path / "database-versions.json"
            versions: dict[str, object] = {}

            def _load_versions(self) -> dict[str, object]:
                return {}

            async def rollback_database(self, source: str, target_version: str) -> bool:
                return True

        class _Scheduler:
            update_manager = _UpdateManager()

        async def _getter() -> Any:
            return _Scheduler()

        from app.services import admin_operations

        monkeypatch.setattr(admin_operations, "get_update_scheduler", _getter)
        out = await legacy_app.rollback_database("usda", "v1")
        assert out["success"] is True

    asyncio.run(_run())


def test_legacy_plate_entrypoints_are_exact_canonical_aliases() -> None:
    """Legacy Plate execution cannot diverge from canonical service ownership."""
    assert legacy_app._compute_premium_plate is plate_service.generate_plate_response
    assert legacy_app.api_premium_plate is plate_service.generate_plate_response
    assert not hasattr(legacy_app, "_plate_deps")


def test_legacy_plate_dependencies_preserve_direct_import_shape() -> None:
    """Legacy Python callers retain the pre-extraction dependency container API."""

    def _make_plate(**_kwargs: Any) -> dict[str, Any]:
        return {}

    def _build_targets(_profile: object) -> object:
        return object()

    def _calculate_bmr(*_args: object) -> dict[str, float]:
        return {}

    def _calculate_tdee(*_args: object) -> dict[str, float]:
        return {}

    def _aggregate_micros(_meals: list[dict[str, Any]]) -> dict[str, float]:
        return {}

    empty = legacy_app.PlateDependencies()
    assert empty.make_plate_fn is None
    assert empty.make_plate is None
    assert empty.build_nutrition_targets_fn is None
    assert empty.build_nutrition_targets is None
    assert empty.calculate_all_bmr_fn is None
    assert empty.calculate_all_bmr is None
    assert empty.calculate_all_tdee_fn is None
    assert empty.calculate_all_tdee is None
    assert empty.aggregate_day_micronutrients_fn is None
    assert empty._aggregate_day_micronutrients is None

    dependencies = legacy_app.PlateDependencies(
        make_plate_fn=_make_plate,
        build_nutrition_targets_fn=_build_targets,
        calculate_all_bmr_fn=_calculate_bmr,
        calculate_all_tdee_fn=_calculate_tdee,
        aggregate_day_micronutrients_fn=_aggregate_micros,
    )

    assert dependencies.make_plate_fn is _make_plate
    assert dependencies.make_plate is _make_plate
    assert dependencies.build_nutrition_targets_fn is _build_targets
    assert dependencies.build_nutrition_targets is _build_targets
    assert dependencies.calculate_all_bmr_fn is _calculate_bmr
    assert dependencies.calculate_all_bmr is _calculate_bmr
    assert dependencies.calculate_all_tdee_fn is _calculate_tdee
    assert dependencies.calculate_all_tdee is _calculate_tdee
    assert dependencies.aggregate_day_micronutrients_fn is _aggregate_micros
    assert dependencies._aggregate_day_micronutrients is _aggregate_micros
    assert legacy_app.PlateServiceDependencies is plate_service.PlateServiceDependencies


def test_build_fallback_plate_invalid_fiber_uses_fiber_min() -> None:
    """Canonical fallback replaces an invalid target fiber with the minimum."""

    class _Macros:
        protein_g = 120
        fat_g = 50
        carbs_g = 200
        fiber_g = "bad"

    class _Targets:
        kcal_daily = 2000
        macros = _Macros()
        water_ml_daily = 2500

        @staticmethod
        def validate_consistency() -> bool:
            return True

    req = legacy_app.PlateRequest(
        sex="male",
        age=30,
        height_cm=175.0,
        weight_kg=70.0,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
        life_stage="adult",
        lang="en",
    )
    out = plate_service.build_fallback_plate(
        req,
        targets_builder=lambda _profile: _Targets(),
    )

    assert out.macros["fiber_g"] == int(round(legacy_app.FIBER_MIN_G))


def test_aggregate_day_micros_awaits_resolved_callable() -> None:
    """Canonical Plate aggregation awaits an explicit asynchronous dependency."""

    async def _agg(_meals: list[dict[str, Any]]) -> dict[str, float]:
        return {"iron_mg": 1.0}

    result = asyncio.run(
        plate_service.aggregate_day_micros(
            meals=[{"x": 1}],
            aggregator=_agg,
        )
    )

    assert result == {"iron_mg": 1.0}


def test_premium_plate_calls_bmr_tdee_and_make_plate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Canonical Plate calls each explicit core dependency exactly once."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    calls: list[str] = []

    def _calculate_bmr(*_args: Any, **_kwargs: Any) -> dict[str, float]:
        calls.append("bmr")
        return {"mifflin": 1500.0}

    def _calculate_tdee(
        _bmr_results: dict[str, float],
        _activity: str,
    ) -> dict[str, float]:
        calls.append("tdee")
        return {"mifflin": 2000.0}

    def _make_plate(**_kwargs: Any) -> dict[str, Any]:
        calls.append("plate")
        return {
            "kcal": 2000,
            "macros": {
                "protein_g": 120,
                "fat_g": 50,
                "carbs_g": 200,
                "fiber_g": 25,
            },
            "portions": {
                "protein_palm": 1.0,
                "fat_thumbs": 1.0,
                "carb_cups": 1.0,
                "veg_cups": 1.0,
            },
            "layout": [
                {
                    "kind": "plate_sector",
                    "fraction": 1.0,
                    "label": "x",
                    "tooltip": "x",
                }
            ],
            "meals": [],
        }

    def _empty_micros(
        _meals: list[dict[str, Any]],
    ) -> dict[str, float]:
        calls.append("micros")
        return {}

    dependencies = plate_service.PlateServiceDependencies(
        make_plate=_make_plate,
        calculate_all_bmr=_calculate_bmr,
        calculate_all_tdee=_calculate_tdee,
        build_nutrition_targets=None,
        aggregate_day_micronutrients=_empty_micros,
    )
    request = legacy_app.PlateRequest(
        sex="male",
        age=30,
        height_cm=175.0,
        weight_kg=70.0,
        activity="moderate",
        goal="maintain",
        deficit_pct=None,
        surplus_pct=None,
        bodyfat=None,
        diet_flags=set(),
        life_stage="adult",
        lang="en",
    )

    response = asyncio.run(
        plate_service.generate_plate_response(
            request,
            dependencies=dependencies,
        )
    )

    assert response.kcal == 2000
    assert calls == ["bmr", "tdee", "plate", "micros"]


def test_exports_flag_warning_outside_tests_is_coverable(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Cover module-level export gating branch that warns outside tests.

    We temporarily remove sys.modules['pytest'] so legacy_app's import-time heuristic
    doesn't auto-detect tests and flip _export_testing_flag to True.
    """
    caplog.set_level(logging.WARNING)

    saved_pytest = sys.modules.get("pytest")
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    monkeypatch.setenv("FEATURE_EXPORTS", "true")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "prod")
    try:
        importlib.reload(legacy_app)
        assert getattr(legacy_app, "EXPORTS_ENABLED", False) is True
        assert any("Export endpoints enabled outside tests" in r.message for r in caplog.records)
    finally:
        if saved_pytest is not None:
            monkeypatch.setitem(sys.modules, "pytest", saved_pytest)
        # Restore a normal testing reload for other tests.
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        importlib.reload(legacy_app)


def test_exports_testing_flag_is_set_for_ci_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export testing flag detection for APP_ENV=ci (line ~4837)."""
    monkeypatch.setenv("FEATURE_EXPORTS", "true")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "ci")
    try:
        importlib.reload(legacy_app)
        assert getattr(legacy_app, "EXPORTS_ENABLED", False) is True
    finally:
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        importlib.reload(legacy_app)


def test_exports_testing_flag_is_set_when_pytest_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export testing flag detection via pytest heuristic (line ~4839)."""
    monkeypatch.setenv("FEATURE_EXPORTS", "true")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "prod")
    try:
        importlib.reload(legacy_app)
        assert getattr(legacy_app, "EXPORTS_ENABLED", False) is True
    finally:
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        importlib.reload(legacy_app)

# -*- coding: utf-8 -*-
"""
RU: Тесты для diff-coverage по legacy_app.py (точечно исполняем ветки из CI missing-list).
EN: Tests for diff-coverage on legacy_app.py (execute branches reported missing by CI).
"""

from __future__ import annotations

import importlib
import logging
import sys
from types import ModuleType
from typing import Any, Callable

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import legacy_app


def test_language_cookie_has_samesite_and_secure_guard() -> None:
    """Security: language cookie must include SameSite and Secure-on-HTTPS guard."""
    client = TestClient(legacy_app.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "SameSite=Lax" in resp.text
    assert "window.location.protocol === 'https:'" in resp.text
    assert "; Secure" in resp.text


def test_export_pdf_generic_requires_api_key() -> None:
    """Security: /api/v1/export/pdf must not be unauthenticated."""
    client = TestClient(legacy_app.app)
    resp = client.post("/api/v1/export/pdf", json={"meals": []})
    assert resp.status_code in {401, 403}


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


@pytest.mark.asyncio
async def test_aggregate_day_micros_accepts_sync_callable() -> None:
    """Support sync callable result per contract comment in aggregate_day_micros."""
    sync_mod = ModuleType("sync_candidate")
    setattr(sync_mod, "_aggregate_day_micronutrients", lambda _meals: {"iron_mg": 1.0})
    res = await legacy_app.aggregate_day_micros(meals=[], candidates=[sync_mod])
    assert res == {"iron_mg": 1.0}


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


@pytest.mark.asyncio
async def test_get_update_scheduler_late_getter_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover legacy_app.get_update_scheduler branch that uses late getter (line ~386)."""

    async def _late_getter() -> Any:
        return object()

    monkeypatch.setattr(legacy_app, "_scheduler_getter", None, raising=False)

    import core.food_apis.scheduler as sched

    monkeypatch.setattr(sched, "get_update_scheduler", _late_getter)
    res = await legacy_app.get_update_scheduler()
    assert res is not None


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
    monkeypatch.setattr(legacy_app, "MATPLOTLIB_AVAILABLE", True, raising=False)
    import app as app_pkg

    monkeypatch.setattr(app_pkg, "MATPLOTLIB_AVAILABLE", True, raising=False)

    def _viz(**_kw: Any) -> dict[str, Any]:
        return {"available": True, "ok": True}

    monkeypatch.setattr(legacy_app, "generate_bmi_visualization", _viz, raising=False)

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


def test_insight_prompt_helpers_cover_limits() -> None:
    """Cover _ensure_insight_text_length and _build_insight_prompt trimming paths."""
    too_long = "x" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH + 1)
    with pytest.raises(HTTPException) as exc:
        legacy_app._ensure_insight_text_length(too_long)
    assert exc.value.status_code == 413

    # Build prompt with context trimming
    text = "hello"
    context = "c" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH * 2)
    prompt = legacy_app._build_insight_prompt(text, context)
    assert isinstance(prompt, str)
    assert len(prompt) <= legacy_app.INSIGHT_TEXT_MAX_LENGTH

    # Cover "no context" branch
    assert legacy_app._build_insight_prompt("q", "") == "q"

    # Cover max_context_len <= 0 branch
    huge_text = "x" * legacy_app.INSIGHT_TEXT_MAX_LENGTH
    out = legacy_app._build_insight_prompt(huge_text, "ctx")
    assert len(out) <= legacy_app.INSIGHT_TEXT_MAX_LENGTH


def test_build_insight_prompt_final_truncation_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the final prompt_text length check branch (line ~2124) via a side-effect context."""
    original_max = legacy_app.INSIGHT_TEXT_MAX_LENGTH

    class _WeirdContext:
        def __bool__(self) -> bool:
            return True

        def __getitem__(self, _s: slice) -> str:
            # Shrink max length after max_context_len is computed.
            monkeypatch.setattr(legacy_app, "INSIGHT_TEXT_MAX_LENGTH", 10, raising=False)
            return "c" * 50

    try:
        monkeypatch.setattr(legacy_app, "INSIGHT_TEXT_MAX_LENGTH", 200, raising=False)
        prompt = legacy_app._build_insight_prompt("question", _WeirdContext())  # type: ignore[arg-type]
        assert len(prompt) <= 10
    finally:
        monkeypatch.setattr(legacy_app, "INSIGHT_TEXT_MAX_LENGTH", original_max, raising=False)


@pytest.mark.asyncio
async def test_insight_v1_rag_path_builds_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover RAG path in insight_v1 where ctx is retrieved and prompt is rebuilt."""
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("FEATURE_RAG", "true")

    class _Provider:
        name = "stub"

        async def generate(self, text: str) -> str:
            return text

    # Patch llm.get_provider import inside legacy_app endpoints
    import llm

    monkeypatch.setattr(llm, "get_provider", lambda: _Provider())

    # Patch retrieve_context_structured to return a context with chunks
    import core.rag.simple_rag as simple_rag
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class _Chunk:
        chunk_id: str
        file: str
        content: str
        score: float
        hop: int = 1

    @dataclass
    class _Ctx:
        query: str
        refined_queries: list[str]
        chunks: list[_Chunk]
        confidence: float
        hops: int
        latency_ms: int
        agent_id: Optional[str] = None
        user_tier: Optional[str] = None

    def _fake_structured(*_a: object, **_k: object) -> _Ctx:
        return _Ctx(
            query="question",
            refined_queries=["question"],
            chunks=[_Chunk(chunk_id="a:1", file="a.md", content="ctx", score=0.9)],
            confidence=0.9,
            hops=1,
            latency_ms=10,
        )

    monkeypatch.setattr(simple_rag, "retrieve_context_structured", _fake_structured)

    req = legacy_app.InsightRequest(text="question")
    out = await legacy_app.insight_v1(req)
    assert out.provider == "stub"
    assert "Context:" in out.insight


@pytest.mark.asyncio
async def test_insight_v1_trims_prompt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover prompt_text trimming in insight_v1 (line ~2159)."""
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("FEATURE_RAG", "true")

    class _Provider:
        name = "stub"

        async def generate(self, text: str) -> str:
            return text

    import llm

    monkeypatch.setattr(llm, "get_provider", lambda: _Provider())
    import core.rag.simple_rag as simple_rag
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class _Chunk:
        chunk_id: str
        file: str
        content: str
        score: float
        hop: int = 1

    @dataclass
    class _Ctx:
        query: str
        refined_queries: list[str]
        chunks: list[_Chunk]
        confidence: float
        hops: int
        latency_ms: int
        agent_id: Optional[str] = None
        user_tier: Optional[str] = None

    def _fake_structured(*_a: object, **_k: object) -> _Ctx:
        return _Ctx(
            query="q",
            refined_queries=["q"],
            chunks=[_Chunk(chunk_id="a:1", file="a.md", content="ctx", score=0.9)],
            confidence=0.9,
            hops=1,
            latency_ms=10,
        )

    monkeypatch.setattr(simple_rag, "retrieve_context_structured", _fake_structured)
    monkeypatch.setattr(
        legacy_app,
        "_build_insight_prompt",
        lambda _t, _c: "x" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH + 5),
        raising=False,
    )

    out = await legacy_app.insight_v1(legacy_app.InsightRequest(text="q"))
    assert len(out.insight) == legacy_app.INSIGHT_TEXT_MAX_LENGTH


@pytest.mark.asyncio
async def test_legacy_insight_rag_path_trims(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover legacy /insight RAG branch and prompt trimming (lines ~2182-2202)."""
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("FEATURE_RAG", "true")

    class _Provider:
        name = "stub"

        async def generate(self, text: str) -> str:
            return text

    import llm

    monkeypatch.setattr(llm, "get_provider", lambda: _Provider())
    import core.rag.simple_rag as simple_rag
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class _Chunk:
        chunk_id: str
        file: str
        content: str
        score: float
        hop: int = 1

    @dataclass
    class _Ctx:
        query: str
        refined_queries: list[str]
        chunks: list[_Chunk]
        confidence: float
        hops: int
        latency_ms: int
        agent_id: Optional[str] = None
        user_tier: Optional[str] = None

    # Return a large context to force prompt trimming
    big_content = "c" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH * 2)

    def _fake_structured(*_a: object, **_k: object) -> _Ctx:
        return _Ctx(
            query="q",
            refined_queries=["q"],
            chunks=[_Chunk(chunk_id="a:1", file="a.md", content=big_content, score=0.9)],
            confidence=0.9,
            hops=1,
            latency_ms=10,
        )

    monkeypatch.setattr(simple_rag, "retrieve_context_structured", _fake_structured)

    req = legacy_app.InsightRequest(text="q")
    out = await legacy_app.insight(req)
    assert out.provider == "stub"
    assert len(out.insight) <= legacy_app.INSIGHT_TEXT_MAX_LENGTH


@pytest.mark.asyncio
async def test_legacy_insight_trims_prompt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover prompt_text trimming in legacy insight (line ~2202)."""
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("FEATURE_RAG", "true")

    class _Provider:
        name = "stub"

        async def generate(self, text: str) -> str:
            return text

    import llm

    monkeypatch.setattr(llm, "get_provider", lambda: _Provider())
    import core.rag.simple_rag as simple_rag
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class _Chunk:
        chunk_id: str
        file: str
        content: str
        score: float
        hop: int = 1

    @dataclass
    class _Ctx:
        query: str
        refined_queries: list[str]
        chunks: list[_Chunk]
        confidence: float
        hops: int
        latency_ms: int
        agent_id: Optional[str] = None
        user_tier: Optional[str] = None

    def _fake_structured(*_a: object, **_k: object) -> _Ctx:
        return _Ctx(
            query="q",
            refined_queries=["q"],
            chunks=[_Chunk(chunk_id="a:1", file="a.md", content="ctx", score=0.9)],
            confidence=0.9,
            hops=1,
            latency_ms=10,
        )

    monkeypatch.setattr(simple_rag, "retrieve_context_structured", _fake_structured)
    monkeypatch.setattr(
        legacy_app,
        "_build_insight_prompt",
        lambda _t, _c: "x" * (legacy_app.INSIGHT_TEXT_MAX_LENGTH + 5),
        raising=False,
    )
    out = await legacy_app.insight(legacy_app.InsightRequest(text="q"))
    assert len(out.insight) == legacy_app.INSIGHT_TEXT_MAX_LENGTH


@pytest.mark.asyncio
async def test_premium_bmr_resolve_wrapper_prefers_patched_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover api_premium_bmr wrapper resolution that returns patched callable from app package."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    # Patch wrappers on app package so api_premium_bmr picks them up via sys.modules["app"].
    import app as app_pkg

    def bmr_wrapper(*_a: Any, **_kw: Any) -> dict[str, float]:
        return {"mifflin": 1000.0}

    def tdee_wrapper(*_a: Any, **_kw: Any) -> dict[str, float]:
        return {"mifflin": 2000.0}

    monkeypatch.setattr(app_pkg, "_calculate_all_bmr_wrapper", bmr_wrapper, raising=False)
    monkeypatch.setattr(app_pkg, "_calculate_all_tdee_wrapper", tdee_wrapper, raising=False)

    req = legacy_app.BMRRequest(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        sex="male",
        activity="moderate",
        bodyfat=None,
        lang="en",
    )
    resp = await legacy_app.api_premium_bmr(req)
    assert resp.bmr


@pytest.mark.asyncio
async def test_premium_bmr_resolve_wrapper_uses_pkg_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover api_premium_bmr wrapper resolution that returns a candidate from _iter_app_modules."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    dummy_mod = ModuleType("dummy_app_module")

    def bmr_wrapper(*_a: Any, **_kw: Any) -> dict[str, float]:
        return {"mifflin": 1100.0}

    def tdee_wrapper(*_a: Any, **_kw: Any) -> dict[str, float]:
        return {"mifflin": 2100.0}

    setattr(dummy_mod, "_calculate_all_bmr_wrapper", bmr_wrapper)
    setattr(dummy_mod, "_calculate_all_tdee_wrapper", tdee_wrapper)

    # Ensure sys.modules["app"] doesn't short-circuit the resolution
    import app as app_pkg

    # app is a PEP 562 forwarding module; delattr() would trigger __getattr__ and fail even when
    # the attribute is not actually present on the module. Remove only real module attributes.
    monkeypatch.delitem(app_pkg.__dict__, "_calculate_all_bmr_wrapper", raising=False)
    monkeypatch.delitem(app_pkg.__dict__, "_calculate_all_tdee_wrapper", raising=False)

    monkeypatch.setattr(legacy_app, "_iter_app_modules", lambda: [dummy_mod])

    req = legacy_app.BMRRequest(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        sex="male",
        activity="moderate",
        bodyfat=None,
        lang="en",
    )
    resp = await legacy_app.api_premium_bmr(req)
    assert resp.tdee


@pytest.mark.asyncio
async def test_premium_bmr_legacy_executes_wrapper_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover premium_bmr_legacy wrapper resolution return path."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    def bmr_wrapper(*_a: Any, **_kw: Any) -> dict[str, float]:
        return {"mifflin": 1000.0}

    def tdee_wrapper(*_a: Any, **_kw: Any) -> dict[str, float]:
        return {"mifflin": 2000.0}

    import app as app_pkg

    monkeypatch.setattr(app_pkg, "_calculate_all_bmr_wrapper", bmr_wrapper, raising=False)
    monkeypatch.setattr(app_pkg, "_calculate_all_tdee_wrapper", tdee_wrapper, raising=False)

    req = legacy_app.BMRRequestLegacy(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        sex="male",
        activity="moderate",
        bodyfat=None,
        lang="en",
    )
    resp = await legacy_app.premium_bmr_legacy(req)
    assert resp.bmr


@pytest.mark.asyncio
async def test_week_plan_missing_required_fields_raises_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        diet_flags=[],
        targets=None,
        life_stage=None,
        lang="en",
    )
    with pytest.raises(HTTPException) as exc:
        await legacy_app.api_weekly_menu(req)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_export_day_csv_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
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


@pytest.mark.asyncio
async def test_export_pdf_generic_success_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export_pdf_generic helper import and error paths."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")

    import app as app_pkg

    # Ensure helper resolution sees a callable (it prefers app.to_pdf_day if present).
    monkeypatch.setattr(app_pkg, "to_pdf_day", lambda _p: b"%PDF", raising=False)
    monkeypatch.setattr(legacy_app, "to_pdf_day", lambda _p: b"%PDF", raising=False)
    resp = await legacy_app.export_pdf_generic({"meals": [], "totals": {}})
    assert resp.media_type == "application/pdf"

    def boom(_: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(app_pkg, "to_pdf_day", boom, raising=False)
    monkeypatch.setattr(legacy_app, "to_pdf_day", boom, raising=False)
    with pytest.raises(HTTPException) as exc:
        await legacy_app.export_pdf_generic({"meals": [], "totals": {}})
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_export_week_csv_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export_weekly_plan_csv exception -> 500."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")

    def boom(_: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(legacy_app, "to_csv_week", boom, raising=False)
    with pytest.raises(HTTPException) as exc:
        await legacy_app.export_weekly_plan_csv("p1")
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_export_day_pdf_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export_daily_plan_pdf success, importerror, and generic error paths."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")

    import app as app_pkg

    # export_daily_plan_pdf may resolve PDF helper via app.to_pdf_day if present.
    monkeypatch.setattr(app_pkg, "to_pdf_day", lambda _p: b"pdf", raising=False)
    monkeypatch.setattr(legacy_app, "to_pdf_day", lambda _p: b"pdf", raising=False)
    resp = await legacy_app.export_daily_plan_pdf("p1")
    assert resp.media_type == "application/pdf"

    def raise_import(_: Any) -> bytes:
        raise ImportError("no reportlab")

    monkeypatch.setattr(app_pkg, "to_pdf_day", raise_import, raising=False)
    monkeypatch.setattr(legacy_app, "to_pdf_day", raise_import, raising=False)
    with pytest.raises(HTTPException) as exc:
        await legacy_app.export_daily_plan_pdf("p1")
    assert exc.value.status_code == 500

    def raise_generic(_: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(app_pkg, "to_pdf_day", raise_generic, raising=False)
    monkeypatch.setattr(legacy_app, "to_pdf_day", raise_generic, raising=False)
    with pytest.raises(HTTPException) as exc2:
        await legacy_app.export_daily_plan_pdf("p1")
    assert exc2.value.status_code == 500


@pytest.mark.asyncio
async def test_export_day_csv_helper_missing_503(monkeypatch: pytest.MonkeyPatch) -> None:
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


@pytest.mark.asyncio
async def test_export_day_csv_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover CSV success path returning Response (line ~4919)."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")

    monkeypatch.setattr(legacy_app, "to_csv_day", lambda _p: b"a,b\n", raising=False)
    resp = await legacy_app.export_daily_plan_csv("p1")
    assert resp.media_type == "text/csv"


@pytest.mark.asyncio
async def test_export_pdf_generic_empty_payload_400() -> None:
    """Cover empty payload guard (line ~4946)."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")
    with pytest.raises(HTTPException) as exc:
        await legacy_app.export_pdf_generic({})
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_export_pdf_generic_helper_missing_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover PDF helper missing -> HTTPException passthrough (lines ~4959, ~4972)."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")
    import app as app_pkg

    monkeypatch.setattr(app_pkg, "to_pdf_day", None, raising=False)
    monkeypatch.setattr(legacy_app, "to_pdf_day", None, raising=False)
    with pytest.raises(HTTPException) as exc:
        await legacy_app.export_pdf_generic({"x": 1})
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_export_week_csv_fallback_when_helper_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover weekly CSV fallback Response when helper missing (line ~5069)."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")

    monkeypatch.setattr(legacy_app, "to_csv_week", None, raising=False)
    resp = await legacy_app.export_weekly_plan_csv("p1")
    assert resp.media_type == "text/csv"
    assert b"plan_id" in resp.body


@pytest.mark.asyncio
async def test_export_day_pdf_helper_missing_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export_daily_plan_pdf helper-missing path (lines ~5151, ~5165)."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")
    monkeypatch.setattr(legacy_app, "to_pdf_day", None, raising=False)
    with pytest.raises(HTTPException) as exc:
        await legacy_app.export_daily_plan_pdf("p1")
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_export_week_pdf_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export_weekly_plan_pdf success, missing helper, importerror, and generic error paths."""
    if not getattr(legacy_app, "EXPORTS_ENABLED", False):
        pytest.skip("Exports are not enabled in this environment.")

    monkeypatch.setattr(legacy_app, "to_pdf_week", lambda _p: b"pdf", raising=False)
    resp = await legacy_app.export_weekly_plan_pdf("p1")
    assert resp.media_type == "application/pdf"

    monkeypatch.setattr(legacy_app, "to_pdf_week", None, raising=False)
    with pytest.raises(HTTPException) as exc:
        await legacy_app.export_weekly_plan_pdf("p1")
    assert exc.value.status_code == 503

    def raise_import(_: Any) -> bytes:
        raise ImportError("no reportlab")

    monkeypatch.setattr(legacy_app, "to_pdf_week", raise_import, raising=False)
    with pytest.raises(HTTPException) as exc2:
        await legacy_app.export_weekly_plan_pdf("p1")
    assert exc2.value.status_code == 500

    def raise_generic(_: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(legacy_app, "to_pdf_week", raise_generic, raising=False)
    with pytest.raises(HTTPException) as exc3:
        await legacy_app.export_weekly_plan_pdf("p1")
    assert exc3.value.status_code == 500


@pytest.mark.asyncio
async def test_rollback_database_coroutine_callable_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover coroutine rollback_callable branch (line ~4782)."""

    class _UpdateManager:
        async def rollback_database(self, source: str, target_version: str) -> bool:
            return True

    class _Scheduler:
        update_manager = _UpdateManager()

    async def _getter() -> Any:
        return _Scheduler()

    import app as app_pkg

    monkeypatch.setattr(app_pkg, "get_update_scheduler", _getter, raising=False)
    out = await legacy_app.rollback_database("usda", "v1")
    assert out["success"] is True


def test_targets_disabled_detects_explicit_none_on_app_and_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover explicit build_nutrition_targets=None checks (lines ~2339, ~2341)."""
    # Reset cache so we don't short-circuit before reaching the explicit-none checks.
    monkeypatch.setattr(legacy_app, "_targets_disabled_cache", None, raising=False)
    monkeypatch.setattr(legacy_app, "_targets_disabled_cache_time", 0.0, raising=False)

    # Ensure pkg_explicit_none does not short-circuit.
    dummy_pkg = ModuleType("dummy_pkg")
    monkeypatch.setattr(legacy_app, "_APP_PACKAGE_REF", dummy_pkg, raising=False)

    import app as app_pkg

    # primary app module case (line ~2339)
    monkeypatch.setattr(app_pkg, "build_nutrition_targets", None, raising=False)
    assert legacy_app.targets_disabled() is True

    # alias module case (line ~2341)
    alias = ModuleType("app_module")
    alias.build_nutrition_targets = None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app_module", alias)
    monkeypatch.setattr(legacy_app, "_targets_disabled_cache", None, raising=False)
    assert legacy_app.targets_disabled() is True


def test_build_fallback_plate_invalid_fiber_uses_fiber_min(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover invalid fiber_g conversion branch (line ~3263)."""

    class _Macros:
        protein_g = 120
        fat_g = 50
        carbs_g = 200
        fiber_g = "bad"

    class _Targets:
        kcal_daily = 2000
        macros = _Macros()

    monkeypatch.setattr(legacy_app, "_evaluate_targets_disabled", lambda: False, raising=False)
    monkeypatch.setattr(
        legacy_app, "_resolve_build_targets_callable", lambda: (lambda _p: _Targets())
    )

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
    out = legacy_app.build_fallback_plate(req, candidates=[])
    assert out.macros["fiber_g"] >= int(round(legacy_app.FIBER_MIN_G))


@pytest.mark.asyncio
async def test_aggregate_day_micros_awaits_resolved_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover await path in aggregate_day_micros (line ~3565)."""

    async def _agg(_meals: Any) -> dict[str, float]:
        return {"iron_mg": 1.0}

    monkeypatch.setattr(legacy_app.core_utils, "resolve_attr", lambda *_a, **_k: _agg)
    out = await legacy_app.aggregate_day_micros(meals=[{"x": 1}], candidates=[])
    assert out["iron_mg"] == 1.0


@pytest.mark.asyncio
async def test_premium_plate_calls_bmr_tdee_and_make_plate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover BMR/TDEE + make_plate call path in api_premium_plate (lines ~3684-3690)."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    monkeypatch.setattr(legacy_app, "sanitize_plate_data", lambda x: x, raising=False)

    async def _empty_micros(*_a: Any, **_k: Any) -> dict[str, float]:
        return {}

    monkeypatch.setattr(legacy_app, "aggregate_day_micros", _empty_micros, raising=False)
    monkeypatch.setattr(
        legacy_app,
        "align_macros_with_targets",
        lambda *_a, **_k: (
            {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25},
            None,
            False,
        ),
        raising=False,
    )

    monkeypatch.setattr(
        legacy_app, "calculate_all_bmr", lambda *_a, **_k: {"mifflin": 1500.0}, raising=False
    )
    monkeypatch.setattr(
        legacy_app, "calculate_all_tdee", lambda *_a, **_k: {"mifflin": 2000.0}, raising=False
    )

    def _make_plate(**_kw: Any) -> dict[str, Any]:
        return {
            "kcal": 2000,
            "macros": {"protein_g": 120, "fat_g": 50, "carbs_g": 200, "fiber_g": 25},
            "portions": {
                "protein_palm": 1.0,
                "fat_thumbs": 1.0,
                "carb_cups": 1.0,
                "veg_cups": 1.0,
            },
            "layout": [{"kind": "plate_sector", "fraction": 1.0, "label": "x", "tooltip": "x"}],
            "meals": [{"title": "m", "kcal": 500, "protein_g": 30, "fat_g": 10, "carbs_g": 60}],
        }

    monkeypatch.setattr(legacy_app, "make_plate", _make_plate, raising=False)

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
    out = await legacy_app.api_premium_plate(req)
    assert out.kcal >= 0


@pytest.mark.asyncio
async def test_premium_bmr_legacy_hits_globals_fallback_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover premium_bmr_legacy _resolve_wrapper final globals() return (line ~4007)."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    import app as app_pkg

    # app is a PEP 562 forwarding module; delattr() would trigger __getattr__ and fail even when
    # the attribute is not actually present on the module. Remove only real module attributes.
    monkeypatch.delitem(app_pkg.__dict__, "_calculate_all_bmr_wrapper", raising=False)
    monkeypatch.delitem(app_pkg.__dict__, "_calculate_all_tdee_wrapper", raising=False)

    monkeypatch.setattr(
        legacy_app, "_calculate_all_bmr_wrapper", lambda *_a, **_k: {"mifflin": 1000.0}
    )
    monkeypatch.setattr(
        legacy_app, "_calculate_all_tdee_wrapper", lambda *_a, **_k: {"mifflin": 2000.0}
    )

    req = legacy_app.BMRRequestLegacy(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        sex="male",
        activity="moderate",
        bodyfat=None,
        lang="en",
    )
    resp = await legacy_app.premium_bmr_legacy(req)
    assert resp.bmr


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
    monkeypatch.setenv("APP_ENV", "prod")
    try:
        importlib.reload(legacy_app)
        assert getattr(legacy_app, "EXPORTS_ENABLED", False) is True
        assert any("Export endpoints enabled outside tests" in r.message for r in caplog.records)
    finally:
        if saved_pytest is not None:
            sys.modules["pytest"] = saved_pytest
        # Restore a normal testing reload for other tests.
        monkeypatch.setenv("TESTING", "true")
        importlib.reload(legacy_app)


def test_exports_testing_flag_is_set_for_ci_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export testing flag detection for APP_ENV=ci (line ~4837)."""
    monkeypatch.setenv("FEATURE_EXPORTS", "true")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setenv("APP_ENV", "ci")
    importlib.reload(legacy_app)
    assert getattr(legacy_app, "EXPORTS_ENABLED", False) is True


def test_exports_testing_flag_is_set_when_pytest_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover export testing flag detection via pytest heuristic (line ~4839)."""
    monkeypatch.setenv("FEATURE_EXPORTS", "true")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setenv("APP_ENV", "prod")
    importlib.reload(legacy_app)
    assert getattr(legacy_app, "EXPORTS_ENABLED", False) is True

"""Tests for the legacy premium weekly-plan alias shim."""

from __future__ import annotations

import asyncio
import logging
import math
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, NoReturn, cast
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.effective_routes import (
    iter_effective_route_candidates,
    route_endpoint,
    route_methods,
    route_path,
)
from app.schemas.legacy_premium_weekly_plan import (
    LegacyWeekPlanRequest,
    WeeklyMenuResponse,
)
import app.services.legacy_premium_weekly_plan as weekly_plan_service
import legacy_app
import app.routers.legacy_premium_weekly_plan as weekly_plan_router
import app.routers.vip as vip_router

if TYPE_CHECKING:
    from httpx2 import Response

_TARGETS_ONLY_DETAIL = (
    "Targets-based weekly plans are not supported on this endpoint. "
    "Provide full profile data or use /api/v1/premium/plan/week-flexible."
)
_INVALID_WEEKLY_PAYLOAD_DETAIL = "Invalid weekly plan request payload"


def _assert_json_response(response: Response) -> dict[str, Any]:
    assert response.headers.get("Content-Type", "").startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def _fake_weekly_menu_builder(profile: object) -> dict[str, Any]:
    """Return a deterministic weekly menu payload for alias/canonical parity tests.

    RU: Вернуть детерминированный weekly menu payload для parity тестов.
    EN: Return a deterministic weekly menu payload for alias/canonical parity tests.
    """
    return {
        "week_start": "2026-03-09",
        "daily_menus": [
            {
                "date": "2026-03-09",
                "meals": [
                    {"title": "Breakfast", "kcal": 320},
                    {"title": "Lunch", "kcal": 610},
                ],
                "total_kcal": 930,
                "daily_cost": 11.5,
            },
            {
                "date": "2026-03-10",
                "meals": [{"title": "Dinner", "kcal": 540}],
                "total_kcal": 540,
                "daily_cost": 9.25,
            },
        ],
        "weekly_coverage": {"protein": 0.91, "fiber": 0.84},
        "shopping_list": {"oats": 400.0, "chicken": 900.0},
        "total_cost": 72.8,
        "adherence_score": 0.67,
    }


def _valid_payload() -> dict[str, Any]:
    return {
        "sex": "female",
        "age": 30,
        "height_cm": 168.0,
        "weight_kg": 62.0,
        "activity": "moderate",
        "goal": "maintain",
        "diet_flags": [],
        "lang": "en",
    }


def _valid_targets() -> dict[str, Any]:
    return {
        "kcal": 2000,
        "macros": {"protein_g": 120},
        "micro": {"iron_mg": 18},
        "water_ml": 2200,
    }


def _patch_invalid_request_work_spies(
    monkeypatch: pytest.MonkeyPatch,
) -> SimpleNamespace:
    """Install request-work spies that must stay untouched on manual validation failure."""

    feature_getter = Mock(return_value=True)
    menu_builder = Mock()
    builder_getter = Mock(return_value=menu_builder)
    executor = AsyncMock()
    profile_builder = Mock()
    threadpool = Mock()
    monkeypatch.setattr(weekly_plan_router, "is_vip_module_enabled", feature_getter)
    monkeypatch.setattr(weekly_plan_router, "get_weekly_menu_builder", builder_getter)
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)
    monkeypatch.setattr(vip_router.fitchef_runtime, "build_weekly_user_profile", profile_builder)
    monkeypatch.setattr(vip_router.fitchef_runtime, "run_in_threadpool", threadpool)
    return SimpleNamespace(
        feature_getter=feature_getter,
        builder_getter=builder_getter,
        executor=executor,
        profile_builder=profile_builder,
        threadpool=threadpool,
        menu_builder=menu_builder,
    )


def _assert_invalid_request_work_not_started(spies: SimpleNamespace) -> None:
    spies.feature_getter.assert_not_called()
    spies.builder_getter.assert_not_called()
    spies.executor.assert_not_awaited()
    spies.profile_builder.assert_not_called()
    spies.threadpool.assert_not_called()
    spies.menu_builder.assert_not_called()


def _assert_static_invalid_weekly_payload(response: Response) -> None:
    assert response.status_code == 422, response.text
    assert _assert_json_response(response) == {"detail": _INVALID_WEEKLY_PAYLOAD_DETAIL}


def test_legacy_weekly_alias_matches_canonical_vip_menu(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy premium alias must be a thin adapter over canonical VIP weekly menu logic."""

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(vip_router, "make_weekly_menu", _fake_weekly_menu_builder, raising=False)

    client_app = cast(FastAPI, client.app)
    vip_route = next(
        (
            route
            for route in iter_effective_route_candidates(client_app.routes)
            if route_path(route) == "/api/v1/vip/menu/weekly/plan"
            and "POST" in route_methods(route)
        ),
        None,
    )
    assert vip_route is not None, "POST /api/v1/vip/menu/weekly/plan route not found"
    endpoint_globals = getattr(route_endpoint(vip_route), "__globals__", None)
    assert isinstance(endpoint_globals, dict)
    monkeypatch.setitem(
        endpoint_globals,
        "make_weekly_menu",
        _fake_weekly_menu_builder,
    )

    payload = _valid_payload()
    legacy_response = client.post("/api/v1/premium/plan/week", json=payload, headers=vip_headers)
    canonical_response = client.post(
        "/api/v1/vip/menu/weekly/plan",
        json=payload,
        headers=vip_headers,
    )

    assert legacy_response.status_code == 200, legacy_response.text
    assert canonical_response.status_code == 200, canonical_response.text
    assert legacy_response.headers.get("Content-Type", "").startswith("application/json")
    assert canonical_response.headers.get("Content-Type", "").startswith("application/json")

    legacy_data = legacy_response.json()
    canonical_menu = canonical_response.json()["menu"]

    assert legacy_data["daily_menus"] == canonical_menu["daily_menus"]
    assert legacy_data["weekly_coverage"] == canonical_menu["weekly_coverage"]
    assert legacy_data["shopping_list"] == canonical_menu["shopping_list"]
    assert legacy_data["total_cost"] == canonical_menu["total_cost"]
    assert legacy_data["adherence_score"] == canonical_menu["adherence_score"]
    assert legacy_data["week_summary"]["week_start"] == canonical_menu["week_start"]
    assert legacy_data["week_summary"]["total_days"] == len(canonical_menu["daily_menus"])
    returned_day_cost_total = sum(
        float(day.get("daily_cost", 0.0)) for day in canonical_menu["daily_menus"]
    )
    assert legacy_data["week_summary"]["avg_daily_cost"] == round(
        returned_day_cost_total / len(canonical_menu["daily_menus"]), 2
    )


def test_legacy_weekly_alias_delegates_to_canonical_vip_execution(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy alias must delegate through the canonical VIP execution seam."""

    captured: dict[str, Any] = {}

    async def _fake_run_weekly_plan_task(
        task: Any,
        *,
        menu_builder: Any = None,
    ) -> Any:
        captured["payload"] = task.input.request_data
        captured["menu_builder"] = menu_builder
        return SimpleNamespace(menu=_fake_weekly_menu_builder(object()))

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(
        vip_router.fitchef_runtime,
        "run_weekly_plan_task",
        _fake_run_weekly_plan_task,
    )

    response = client.post("/api/v1/premium/plan/week", json=_valid_payload(), headers=vip_headers)

    assert response.status_code == 200, response.text
    assert captured["menu_builder"] is _fake_weekly_menu_builder
    assert captured["payload"]["sex"] == "female"
    assert response.json()["daily_menus"] == _fake_weekly_menu_builder(object())["daily_menus"]


def test_legacy_weekly_alias_rejects_targets_only_payload_with_guidance(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Targets-only legacy payload must keep the legacy guidance contract."""

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )

    response = client.post(
        "/api/v1/premium/plan/week",
        json={
            "targets": {
                "kcal": 2000,
                "macros": {"protein_g": 120},
                "micro": {"iron_mg": 18},
                "water_ml": 2200,
            }
        },
        headers=vip_headers,
    )

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    detail = response.json()["detail"]
    assert "Targets-based weekly plans are not supported on this endpoint." in detail
    assert "/api/v1/premium/plan/week-flexible" in detail


@pytest.mark.parametrize(
    "missing_field", ("sex", "age", "height_cm", "weight_kg", "activity", "goal")
)
def test_legacy_weekly_alias_rejects_targets_with_incomplete_profile_before_route_body(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    missing_field: str,
) -> None:
    """Targets plus any incomplete six-field profile cannot enter route work."""

    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    payload = {**_valid_payload(), "targets": _valid_targets()}
    del payload[missing_field]

    response = client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers=vip_headers,
    )

    _assert_static_invalid_weekly_payload(response)
    _assert_invalid_request_work_not_started(spies)


def test_legacy_weekly_alias_targets_with_complete_profile_delegates(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Targets plus all six core fields remain profile-mode input."""

    getter = Mock(return_value=_fake_weekly_menu_builder)
    executor = AsyncMock(return_value=_fake_weekly_menu_builder(object()))
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(weekly_plan_router, "get_weekly_menu_builder", getter)
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)
    payload = {**_valid_payload(), "targets": _valid_targets()}

    response = client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers=vip_headers,
    )

    assert response.status_code == 200, response.text
    getter.assert_called_once_with()
    executor.assert_awaited_once()
    delegated_payload = executor.await_args.args[0]
    assert all(
        delegated_payload[field] is not None
        for field in vip_router.fitchef_runtime.CORE_WEEKLY_PROFILE_FIELDS
    )
    assert delegated_payload["targets"]["macros"]["protein_g"] == 120.0


def test_legacy_alias_executor_treats_targets_plus_goal_as_partial_profile() -> None:
    """A non-null goal prevents direct executor input from being classified targets-only."""

    builder = Mock(side_effect=AssertionError("builder must not run"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            vip_router.execute_legacy_premium_week_alias_payload(
                {"targets": _valid_targets(), "goal": "maintain"},
                menu_builder=builder,
            )
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == _INVALID_WEEKLY_PAYLOAD_DETAIL
    builder.assert_not_called()


def test_legacy_weekly_alias_returns_503_when_vip_module_disabled(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VIP feature flag must short-circuit before canonical weekly-plan delegation."""

    getter = Mock(return_value=_fake_weekly_menu_builder)
    monkeypatch.setenv("VIP_MODULE_ENABLED", "false")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(weekly_plan_router, "get_weekly_menu_builder", getter)

    response = client.post("/api/v1/premium/plan/week", json=_valid_payload(), headers=vip_headers)

    assert response.status_code == 503, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json()["detail"] == "VIP module is disabled"
    getter.assert_not_called()


def test_legacy_weekly_alias_returns_503_when_builder_is_unavailable(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The canonical getter's explicit unavailable result keeps the legacy 503."""

    executor = AsyncMock()
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(weekly_plan_router, "get_weekly_menu_builder", lambda: None)
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)

    response = client.post("/api/v1/premium/plan/week", json=_valid_payload(), headers=vip_headers)

    assert response.status_code == 503, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    assert response.json()["detail"] == "Weekly menu generation feature not available"
    executor.assert_not_awaited()


def test_legacy_weekly_plan_contracts_are_canonically_owned() -> None:
    """legacy_app keeps import compatibility, while app modules own the contracts."""

    import app.routers.legacy_premium_weekly_plan as weekly_plan_router

    assert legacy_app.LegacyWeekPlanRequest is LegacyWeekPlanRequest
    assert legacy_app.WeeklyMenuResponse is WeeklyMenuResponse
    assert weekly_plan_router.LegacyWeekPlanRequest is LegacyWeekPlanRequest
    assert weekly_plan_router.WeeklyMenuResponse is WeeklyMenuResponse
    assert weekly_plan_router.build_legacy_weekly_menu_response is (
        weekly_plan_service.build_legacy_weekly_menu_response
    )
    assert weekly_plan_router.get_weekly_menu_builder is (
        weekly_plan_service.get_weekly_menu_builder
    )
    assert not hasattr(weekly_plan_router, "_legacy_module")


@pytest.mark.parametrize(
    "request_headers",
    ({}, {"X-API-Key": "invalid-weekly-key"}),
    ids=("missing-key", "invalid-key"),
)
def test_legacy_weekly_alias_auth_short_circuits_invalid_body(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    request_headers: dict[str, str],
) -> None:
    """Authentication remains authoritative before body validation and builder access."""

    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])

    response = client.post(
        "/api/v1/premium/plan/week",
        json={},
        headers=request_headers,
    )

    assert response.status_code == 403, response.text
    assert _assert_json_response(response) == {"detail": "Invalid API Key"}
    _assert_invalid_request_work_not_started(spies)


def test_legacy_weekly_alias_valid_key_invalid_body_skips_builder(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request validation remains a 422 and does not enter the route body."""

    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])

    response = client.post(
        "/api/v1/premium/plan/week",
        json={},
        headers=vip_headers,
    )

    _assert_static_invalid_weekly_payload(response)
    _assert_invalid_request_work_not_started(spies)


@pytest.mark.parametrize(
    "missing_field", ("sex", "age", "height_cm", "weight_kg", "activity", "goal")
)
def test_legacy_weekly_alias_incomplete_profile_never_enters_route_body(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    missing_field: str,
) -> None:
    """Every omitted core profile field is rejected before feature or builder work."""

    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    payload = _valid_payload()
    del payload[missing_field]

    response = client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers=vip_headers,
    )

    _assert_static_invalid_weekly_payload(response)
    _assert_invalid_request_work_not_started(spies)


@pytest.mark.parametrize("field", ("age", "height_cm", "weight_kg"))
def test_legacy_weekly_alias_rejects_boolean_numeric_profile_fields_before_route_body(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Raw booleans cannot be coerced into legacy profile numbers."""

    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    payload = _valid_payload()
    payload[field] = True

    response = client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers=vip_headers,
    )

    _assert_static_invalid_weekly_payload(response)
    _assert_invalid_request_work_not_started(spies)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sex", None),
        ("age", None),
        ("height_cm", None),
        ("weight_kg", None),
        ("activity", None),
        ("goal", None),
        ("sex", "unknown-sex"),
        ("activity", "unknown-activity"),
        ("goal", "unknown-goal"),
        ("age", -1),
        ("age", 0),
        ("age", 121),
        ("height_cm", -1),
        ("height_cm", 0),
        ("weight_kg", -1),
        ("weight_kg", 0),
    ),
)
def test_legacy_weekly_alias_maps_invalid_profile_values_to_static_422_before_work(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    """Handler-delivered null, literal, and range failures never enter request work."""

    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    payload = _valid_payload()
    payload[field] = value

    response = client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers=vip_headers,
    )

    _assert_static_invalid_weekly_payload(response)
    _assert_invalid_request_work_not_started(spies)


@pytest.mark.parametrize(
    "raw_body",
    ("parsed-scalar-profile-marker", ["parsed-list-profile-marker"]),
    ids=("scalar", "list"),
)
def test_legacy_weekly_alias_manual_recognizer_rejects_parsed_scalar_and_list(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    raw_body: object,
) -> None:
    """Parsed non-object JSON reaches the manual recognizer and receives the static boundary."""

    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])

    response = client.post(
        "/api/v1/premium/plan/week",
        json=raw_body,
        headers=vip_headers,
    )

    _assert_static_invalid_weekly_payload(response)
    _assert_invalid_request_work_not_started(spies)


def test_legacy_weekly_alias_invalid_profile_never_reflects_raw_marker(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rejected profile values never cross response, header, or logging boundaries."""

    marker = "sec-e1-01-07-private-profile-marker-7d2f"
    spies = _patch_invalid_request_work_spies(monkeypatch)
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    caplog.set_level(logging.DEBUG, logger=weekly_plan_router.__name__)
    payload = {**_valid_payload(), "goal": marker}

    response = client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers=vip_headers,
    )

    _assert_static_invalid_weekly_payload(response)
    assert marker not in response.text
    assert marker not in repr(dict(response.headers))
    assert marker not in caplog.text
    _assert_invalid_request_work_not_started(spies)


def test_legacy_weekly_alias_framework_body_prefix_controls(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed JSON, a missing body, and top-level null remain framework-prefix failures."""

    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    request_headers = {**vip_headers, "Content-Type": "application/json"}
    responses = (
        client.post(
            "/api/v1/premium/plan/week",
            content=b'{"goal":',
            headers=request_headers,
        ),
        client.post(
            "/api/v1/premium/plan/week",
            headers=vip_headers,
        ),
        client.post(
            "/api/v1/premium/plan/week",
            content=b"null",
            headers=request_headers,
        ),
    )

    for response in responses:
        assert response.status_code == 422, response.text
        payload = _assert_json_response(response)
        assert "detail" in payload


def test_api_weekly_menu_direct_model_instance_validates_once_and_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct compatibility calls may still supply an already-validated request model."""

    request_model = LegacyWeekPlanRequest.model_validate(_valid_payload())
    original_model_validate = LegacyWeekPlanRequest.model_validate
    validation_spy = Mock(wraps=original_model_validate)
    menu_builder = Mock()
    executor = AsyncMock(return_value=_fake_weekly_menu_builder(object()))
    monkeypatch.setattr(LegacyWeekPlanRequest, "model_validate", validation_spy)
    monkeypatch.setattr(weekly_plan_router, "is_vip_module_enabled", Mock(return_value=True))
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        Mock(return_value=menu_builder),
    )
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)

    result = asyncio.run(weekly_plan_router.api_weekly_menu(request_model))

    assert isinstance(result, WeeklyMenuResponse)
    validation_spy.assert_called_once_with(request_model)
    executor.assert_awaited_once()
    assert executor.await_args.kwargs["menu_builder"] is menu_builder
    assert executor.await_args.args[0]["goal"] == "maintain"


@pytest.mark.parametrize(
    ("legacy_goal", "canonical_goal"),
    (
        ("lose", "loss"),
        ("loss", "loss"),
        ("weight_loss", "loss"),
        ("maintain", "maintain"),
        ("maintenance", "maintain"),
        ("gain", "gain"),
        ("weight_gain", "gain"),
    ),
)
def test_legacy_weekly_alias_accepts_explicit_legacy_goal_aliases(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    legacy_goal: str,
    canonical_goal: str,
) -> None:
    """Explicit legacy goal aliases stay compatible without an omitted-goal default."""

    executor = AsyncMock(return_value=_fake_weekly_menu_builder(object()))
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)
    payload = {**_valid_payload(), "goal": legacy_goal}

    response = client.post(
        "/api/v1/premium/plan/week",
        json=payload,
        headers=vip_headers,
    )

    assert response.status_code == 200, response.text
    executor.assert_awaited_once()
    delegated_payload = executor.await_args.args[0]
    assert delegated_payload["goal"] == canonical_goal


@pytest.mark.parametrize(
    "failure",
    (
        RuntimeError("private flag failure"),
        HTTPException(status_code=418, detail="private flag HTTP detail"),
    ),
    ids=("runtime", "http"),
)
def test_legacy_weekly_alias_sanitizes_feature_flag_failure(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    failure: Exception,
) -> None:
    """A broken feature-flag resolver is a server failure, not feature disablement."""

    getter = Mock(return_value=_fake_weekly_menu_builder)

    def _raise_flag_error() -> bool:
        raise failure

    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(weekly_plan_router, "is_vip_module_enabled", _raise_flag_error)
    monkeypatch.setattr(weekly_plan_router, "get_weekly_menu_builder", getter)
    caplog.set_level(logging.ERROR, logger=weekly_plan_router.__name__)

    response = client.post(
        "/api/v1/premium/plan/week",
        json=_valid_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 500, response.text
    assert _assert_json_response(response) == {"detail": "Weekly menu generation failed"}
    assert any(
        record.name == weekly_plan_router.__name__
        and record.getMessage() == "Legacy weekly menu generation failed"
        and record.exc_info is not None
        for record in caplog.records
    )
    getter.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    (
        RuntimeError("private runtime failure"),
        ValueError("private getter value failure"),
        ImportError("private missing symbol failure"),
        ModuleNotFoundError("private transitive failure", name="optional_provider"),
        HTTPException(status_code=422, detail=_INVALID_WEEKLY_PAYLOAD_DETAIL),
    ),
    ids=("runtime", "value", "import", "transitive-module", "http"),
)
def test_legacy_weekly_alias_sanitizes_getter_failures(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    failure: Exception,
) -> None:
    """Every getter failure is a broken runtime and must use the generic 500 boundary."""

    executor = AsyncMock()

    def _raise_getter_failure() -> NoReturn:
        raise failure

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(weekly_plan_router, "get_weekly_menu_builder", _raise_getter_failure)
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)
    caplog.set_level(logging.ERROR, logger=weekly_plan_router.__name__)

    response = client.post(
        "/api/v1/premium/plan/week",
        json=_valid_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 500, response.text
    assert _assert_json_response(response) == {"detail": "Weekly menu generation failed"}
    assert any(
        record.name == weekly_plan_router.__name__
        and record.getMessage() == "Legacy weekly menu generation failed"
        and record.exc_info is not None
        for record in caplog.records
    )
    executor.assert_not_awaited()


def test_legacy_weekly_alias_maps_executor_value_error_to_static_400(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only canonical execution ValueError keeps the legacy input-error contract."""

    executor = AsyncMock(side_effect=ValueError("private executor detail"))
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)

    response = client.post(
        "/api/v1/premium/plan/week",
        json=_valid_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 400, response.text
    assert _assert_json_response(response) == {"detail": "Invalid input"}
    assert "private executor detail" not in response.text


@pytest.mark.parametrize(
    "detail",
    (_TARGETS_ONLY_DETAIL, _INVALID_WEEKLY_PAYLOAD_DETAIL),
    ids=("targets-only", "invalid-payload"),
)
def test_legacy_weekly_alias_passes_only_known_safe_422_errors(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    detail: str,
) -> None:
    """The two static migration/validation errors remain exact pass-through contracts."""

    executor = AsyncMock(side_effect=HTTPException(status_code=422, detail=detail))
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)

    response = client.post(
        "/api/v1/premium/plan/week",
        json=_valid_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 422, response.text
    assert _assert_json_response(response) == {"detail": detail}


@pytest.mark.parametrize(
    ("status_code", "detail", "headers"),
    (
        (409, _TARGETS_ONLY_DETAIL, None),
        (422, "private downstream detail", None),
        (422, {"debug": "private"}, None),
        (422, ["private"], None),
        (422, _INVALID_WEEKLY_PAYLOAD_DETAIL, {"X-Internal-Debug": "private"}),
    ),
    ids=("wrong-status", "unknown-text", "dict-detail", "list-detail", "headers"),
)
def test_legacy_weekly_alias_sanitizes_unknown_downstream_http_errors(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status_code: int,
    detail: Any,
    headers: dict[str, str] | None,
) -> None:
    """Unknown HTTP details and headers never cross the compatibility boundary."""

    executor = AsyncMock(
        side_effect=HTTPException(status_code=status_code, detail=detail, headers=headers)
    )
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)
    caplog.set_level(logging.ERROR, logger=weekly_plan_router.__name__)

    response = client.post(
        "/api/v1/premium/plan/week",
        json=_valid_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 500, response.text
    assert _assert_json_response(response) == {"detail": "Weekly menu generation failed"}
    assert "X-Internal-Debug" not in response.headers
    assert any(
        record.name == weekly_plan_router.__name__
        and record.getMessage() == "Legacy weekly menu generation failed"
        and record.exc_info is not None
        for record in caplog.records
    )


def test_legacy_weekly_alias_sanitizes_unexpected_executor_failure(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unexpected canonical execution failures use the same fixed server boundary."""

    executor = AsyncMock(side_effect=RuntimeError("private executor runtime detail"))
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)
    caplog.set_level(logging.ERROR, logger=weekly_plan_router.__name__)

    response = client.post(
        "/api/v1/premium/plan/week",
        json=_valid_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 500, response.text
    assert _assert_json_response(response) == {"detail": "Weekly menu generation failed"}
    assert "private executor runtime detail" not in response.text
    assert any(
        record.name == weekly_plan_router.__name__
        and record.getMessage() == "Legacy weekly menu generation failed"
        and record.exc_info is not None
        for record in caplog.records
    )


def test_legacy_weekly_alias_does_not_classify_response_shaping_value_error_as_input(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A response-adapter defect is a server failure, not a client input error."""

    executor = AsyncMock(return_value=_fake_weekly_menu_builder(object()))

    def _raise_response_error(_payload: dict[str, Any]) -> WeeklyMenuResponse:
        raise ValueError("private response adapter detail")

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _fake_weekly_menu_builder,
    )
    monkeypatch.setattr(vip_router, "execute_legacy_premium_week_alias_payload", executor)
    monkeypatch.setattr(
        weekly_plan_router,
        "build_legacy_weekly_menu_response",
        _raise_response_error,
    )
    caplog.set_level(logging.ERROR, logger=weekly_plan_router.__name__)

    response = client.post(
        "/api/v1/premium/plan/week",
        json=_valid_payload(),
        headers=vip_headers,
    )

    assert response.status_code == 500, response.text
    assert _assert_json_response(response) == {"detail": "Weekly menu generation failed"}
    assert "private response adapter detail" not in response.text
    assert any(
        record.name == weekly_plan_router.__name__
        and record.getMessage() == "Legacy weekly menu generation failed"
        and record.exc_info is not None
        for record in caplog.records
    )


@pytest.mark.parametrize(
    ("legacy_goal", "canonical_goal"),
    (
        ("lose", "loss"),
        ("loss", "loss"),
        ("weight_loss", "loss"),
        ("maintain", "maintain"),
        ("maintenance", "maintain"),
        ("gain", "gain"),
        ("weight_gain", "gain"),
    ),
)
def test_legacy_week_plan_request_normalizes_legacy_goal_aliases(
    legacy_goal: str,
    canonical_goal: str,
) -> None:
    """Legacy goal aliases must keep the pre-extraction request contract."""

    base_payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168.0,
        "weight_kg": 62.0,
        "activity": "moderate",
    }

    assert (
        LegacyWeekPlanRequest.model_validate({**base_payload, "goal": legacy_goal}).goal
        == canonical_goal
    )


def test_legacy_week_plan_request_rejects_unknown_goal() -> None:
    """Unknown explicit legacy goals remain invalid."""

    base_payload = {
        "sex": "female",
        "age": 30,
        "height_cm": 168.0,
        "weight_kg": 62.0,
        "activity": "moderate",
    }

    with pytest.raises(ValidationError):
        LegacyWeekPlanRequest.model_validate({**base_payload, "goal": "unsupported"})


def test_legacy_week_plan_request_keeps_omitted_and_null_goal_absent_for_targets_mode() -> None:
    """Targets-only schema admission does not synthesize a maintain goal."""

    targets = {
        "kcal": 2000,
        "macros": {"protein_g": 120},
        "micro": {"iron_mg": 18},
        "water_ml": 2200,
    }

    omitted = LegacyWeekPlanRequest.model_validate({"targets": targets})
    explicit_null = LegacyWeekPlanRequest.model_validate({"targets": targets, "goal": None})

    assert omitted.goal is None
    assert explicit_null.goal is None
    assert "goal" not in omitted.model_dump(exclude_none=True)
    assert "goal" not in explicit_null.model_dump(exclude_none=True)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sex", "female"),
        ("age", 30),
        ("height_cm", 168.0),
        ("weight_kg", 62.0),
        ("activity", "moderate"),
        ("goal", "maintain"),
    ),
)
def test_legacy_week_plan_request_rejects_targets_with_partial_profile(
    field: str,
    value: object,
) -> None:
    """Any non-null profile field selects profile mode and requires all six."""

    with pytest.raises(ValidationError, match="without profile fields"):
        LegacyWeekPlanRequest.model_validate({"targets": _valid_targets(), field: value})


def test_legacy_week_plan_request_preserves_http_numeric_string_normalization() -> None:
    """Compatible JSON numeric strings remain normalized by the legacy schema."""

    request = LegacyWeekPlanRequest.model_validate(
        {
            "sex": "female",
            "age": "30",
            "height_cm": "168.5",
            "weight_kg": "62",
            "activity": "moderate",
            "goal": "maintain",
        }
    )

    assert request.age == 30
    assert request.height_cm == 168.5
    assert request.weight_kg == 62.0


def test_legacy_week_plan_request_validates_structured_targets() -> None:
    """Structured targets still flow through the canonical TargetsIn validator."""

    with pytest.raises(ValidationError, match="Invalid targets payload"):
        LegacyWeekPlanRequest.model_validate(
            {
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein": "bad"},
                    "micro": {},
                    "water_ml": 1000,
                }
            }
        )


def test_legacy_week_plan_request_requires_targets_or_profile_fields() -> None:
    """Profile-mode requests must still require the full legacy profile."""

    with pytest.raises(ValidationError, match="Either 'targets' must be provided"):
        LegacyWeekPlanRequest.model_validate({"goal": "maintain"})


def test_legacy_week_plan_request_normalizer_preserves_non_dict_values() -> None:
    """Non-dict validator inputs should pass through unchanged."""

    request = LegacyWeekPlanRequest.model_construct(targets={"calories": 1800})

    assert LegacyWeekPlanRequest.model_validate(request) is request


def test_build_legacy_weekly_menu_response_ignores_non_dict_days() -> None:
    """Legacy adapter must skip malformed daily menu entries without crashing."""

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                "bad-day-entry",
                {
                    "date": "",
                    "meals": [],
                    "total_kcal": 0,
                    "daily_cost": 0,
                },
                {
                    "date": "2026-03-09",
                    "meals": "bad-meals",
                    "total_kcal": 0,
                    "daily_cost": 0,
                },
                {
                    "date": "2026-03-10",
                    "meals": [],
                    "total_kcal": 0,
                    "daily_cost": 0,
                },
            ],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 7.0,
            "adherence_score": 0.1,
        }
    )

    assert len(response.daily_menus) == 1
    assert response.daily_menus[0]["date"] == "2026-03-10"


def test_build_legacy_weekly_menu_response_accepts_estimated_cost_fallback() -> None:
    """Canonical day menus may expose estimated_cost instead of daily_cost."""

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                {
                    "date": "2026-03-10",
                    "meals": [],
                    "total_kcal": 0,
                    "estimated_cost": 12.75,
                }
            ],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 12.75,
            "adherence_score": 0.1,
        }
    )

    assert response.daily_menus[0]["daily_cost"] == 12.75


def test_build_legacy_weekly_menu_response_uses_returned_days_for_avg_cost() -> None:
    """Week summary average must derive from returned day payloads, not top-level total_cost."""

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                {
                    "date": "2026-03-10",
                    "meals": [],
                    "total_kcal": 0,
                    "daily_cost": 10.0,
                },
                {
                    "date": "2026-03-11",
                    "meals": [],
                    "total_kcal": 0,
                    "daily_cost": 20.0,
                },
            ],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 999.0,
            "adherence_score": 0.1,
        }
    )

    assert response.week_summary["total_days"] == 2
    assert response.week_summary["avg_daily_cost"] == 15.0


def test_build_legacy_weekly_menu_response_rejects_bool_numeric_values() -> None:
    """Boolean-like numeric fields must fall back to defaults in the legacy adapter."""

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [],
            "weekly_coverage": {"protein": True, "fiber": 0.84},
            "shopping_list": {"oats": True, "rice": 250.0},
            "total_cost": True,
            "adherence_score": False,
        }
    )

    assert response.weekly_coverage == {"fiber": 0.84}
    assert response.shopping_list == {"rice": 250.0}
    assert response.total_cost == 0.0
    assert response.adherence_score == 0.0


def test_build_legacy_weekly_menu_response_recovers_from_bool_day_values() -> None:
    """Bool day numerics must fall back instead of zeroing valid day data."""

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                {
                    "date": "2026-03-10",
                    "meals": [
                        {"title": "Breakfast", "kcal": True},
                        {"title": "Lunch", "kcal": 420},
                    ],
                    "total_kcal": True,
                    "daily_cost": True,
                    "estimated_cost": 14.5,
                }
            ],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 14.5,
            "adherence_score": 0.25,
        }
    )

    assert response.daily_menus[0]["total_kcal"] == 420.0
    assert response.daily_menus[0]["daily_cost"] == 14.5


def test_build_legacy_weekly_menu_response_rejects_non_finite_numeric_values() -> None:
    """NaN and Infinity must collapse to safe legacy defaults instead of leaking to JSON."""

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                {
                    "date": "2026-03-10",
                    "meals": [],
                    "total_kcal": math.nan,
                    "daily_cost": math.inf,
                }
            ],
            "weekly_coverage": {"protein": math.inf, "fiber": 0.84},
            "shopping_list": {"oats": math.nan, "rice": 250.0},
            "total_cost": math.inf,
            "adherence_score": math.nan,
        }
    )

    assert response.daily_menus[0]["total_kcal"] == 0.0
    assert response.daily_menus[0]["daily_cost"] == 0.0
    assert response.weekly_coverage == {"fiber": 0.84}
    assert response.shopping_list == {"rice": 250.0}
    assert response.total_cost == 0.0
    assert response.adherence_score == 0.0


def test_build_legacy_weekly_menu_response_recovers_from_non_finite_day_values() -> None:
    """Non-finite day numerics must still recover valid meal sum and estimated cost."""

    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                {
                    "date": "2026-03-10",
                    "meals": [
                        {"title": "Breakfast", "kcal": math.nan},
                        {"title": "Lunch", "kcal": 420},
                    ],
                    "total_kcal": math.nan,
                    "daily_cost": math.inf,
                    "estimated_cost": 14.5,
                }
            ],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 14.5,
            "adherence_score": 0.25,
        }
    )

    assert response.daily_menus[0]["total_kcal"] == 420.0
    assert response.daily_menus[0]["daily_cost"] == 14.5


def test_build_legacy_weekly_menu_response_rejects_overflow_numeric_values() -> None:
    """Huge integer numerics must be dropped instead of raising overflow errors."""

    huge_number = 10**1000
    response = weekly_plan_service.build_legacy_weekly_menu_response(
        {
            "week_start": "2026-03-09",
            "daily_menus": [
                {
                    "date": "2026-03-10",
                    "meals": [
                        {"title": "Lunch", "kcal": huge_number},
                        {"title": "Dinner", "kcal": 420},
                    ],
                    "total_kcal": huge_number,
                    "daily_cost": huge_number,
                    "estimated_cost": 14.5,
                }
            ],
            "weekly_coverage": {"protein": huge_number, "fiber": 0.84},
            "shopping_list": {"oats": huge_number, "rice": 250.0},
            "total_cost": huge_number,
            "adherence_score": huge_number,
        }
    )

    assert response.daily_menus[0]["total_kcal"] == 420.0
    assert response.daily_menus[0]["daily_cost"] == 14.5
    assert response.weekly_coverage == {"fiber": 0.84}
    assert response.shopping_list == {"rice": 250.0}
    assert response.total_cost == 0.0
    assert response.adherence_score == 0.0

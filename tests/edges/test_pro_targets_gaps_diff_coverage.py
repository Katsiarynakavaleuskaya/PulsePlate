"""CI-selected production scenarios for canonical PRO targets and gaps."""

from __future__ import annotations

import ast
import asyncio
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

import legacy_app
from app import app
from app.middleware.api_tiers import TEST_KEY_PRO
from app.schemas.premium_contracts import (
    NutrientGapsRequest,
    NutrientGapsResponse,
    PlateRequest,
    WHOTargetsRequest,
)
from app.services import pro_nutrition_plate as plate_service
from app.services import pro_nutrition_targets as service
from core.nutrition_utils import alias_micros, clamp_daily_kcal, ensure_priority_micros

_LEGACY_HEADER_VALUE = "targets-gaps-edge-value"
_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("API_KEY", _LEGACY_HEADER_VALUE)
    with TestClient(app) as test_client:
        yield test_client


def _request(
    *,
    goal: str = "maintain",
    life_stage: str = "adult",
    lang: str = "en",
) -> WHOTargetsRequest:
    return WHOTargetsRequest.model_validate(
        {
            "sex": "female",
            "age": 34,
            "height_cm": 168,
            "weight_kg": 62,
            "activity": "light",
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }
    )


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sex": "female",
        "age": 34,
        "height_cm": 168,
        "weight_kg": 62,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }
    payload.update(overrides)
    return payload


def _gaps_request(*, consumed: dict[str, float] | None = None) -> NutrientGapsRequest:
    return NutrientGapsRequest(
        user_profile=_request(),
        consumed_nutrients=consumed
        or {
            "protein_g": 10.0,
            "iron_mg": 1.0,
            "calcium_mg": 100.0,
        },
    )


def _assert_http_exception(
    callable_under_test: Callable[[], object],
    *,
    status_code: int,
    detail: str,
) -> None:
    with pytest.raises(HTTPException) as raised:
        callable_under_test()

    assert raised.value.status_code == status_code
    assert raised.value.detail == detail


def test_canonical_targets_route_and_deprecated_validation_envelope(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        lambda _targets: ["Keep hydration within the calculated range"],
    )

    canonical = client.post(
        "/api/v1/pro/nutrition/targets",
        headers={"X-API-Key": TEST_KEY_PRO},
        json=_payload(lang="es"),
    )

    assert canonical.status_code == 200
    assert canonical.headers["content-type"].startswith("application/json")
    canonical_payload = canonical.json()
    assert canonical_payload["ui_labels"]["kcal_daily"] == "Calorías diarias"
    assert {
        "code": "safety",
        "message": "Keep hydration within the calculated range",
    } in canonical_payload["warnings"]

    deprecated_invalid = client.post(
        "/api/v1/premium/targets",
        headers={"X-API-Key": _LEGACY_HEADER_VALUE},
        json=_payload(unexpected="not-part-of-the-wire-contract"),
    )

    assert deprecated_invalid.status_code == 422
    assert deprecated_invalid.headers["content-type"].startswith("application/json")
    assert deprecated_invalid.json()["detail"]


def test_legacy_target_and_gaps_routes_execute_canonical_services(
    client: TestClient,
) -> None:
    headers = {"X-API-Key": _LEGACY_HEADER_VALUE}

    deprecated_targets = client.post(
        "/api/v1/premium/targets",
        headers=headers,
        json=_payload(),
    )
    strict_targets = client.post(
        "/premium_targets",
        headers=headers,
        json=_payload(),
    )
    gaps = client.post(
        "/api/v1/premium/gaps",
        headers=headers,
        json={
            "user_profile": _payload(lang="ru_RU"),
            "consumed_nutrients": {
                "protein_g": 10.0,
                "iron_mg": 1.0,
                "calcium_mg": 100.0,
            },
        },
    )

    assert deprecated_targets.status_code == 200
    assert strict_targets.status_code == 200
    assert gaps.status_code == 200
    assert gaps.headers["content-type"].startswith("application/json")
    gaps_payload = gaps.json()
    assert gaps_payload["gaps"]["iron_mg"]["priority"] == "high"
    assert gaps_payload["food_recommendations"]
    assert gaps_payload["adherence_score"] == 0.0


@pytest.mark.parametrize(
    "invalid_measurement",
    [
        pytest.param(10**4000, id="overflowing-integer"),
        pytest.param(object(), id="non-numeric-object"),
        pytest.param(float("inf"), id="non-finite-float"),
    ],
)
def test_target_schema_rejects_unsafe_measurements(
    invalid_measurement: object,
) -> None:
    with pytest.raises(ValidationError):
        WHOTargetsRequest.model_validate(_payload(height_cm=invalid_measurement))


def test_fallback_targets_cover_goal_and_warning_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _warning_failure(_age: int, _life_stage: str, _lang: str) -> list[dict[str, str]]:
        raise RuntimeError("optional warning provider unavailable")

    loss = service.fallback_targets_response(
        _request(goal="loss", life_stage="pregnant", lang="es-MX"),
        reason="Profile validation fallback.",
        include_extra_iodine=True,
        life_stage_warning_factory=_warning_failure,
    )

    assert loss.priority_micros["iodine_ug"] == 150.0
    assert {
        "code": "pregnant",
        "message": "Embarazo: los requisitos difieren; consulte guías especializadas.",
    } in loss.warnings
    assert {"code": "life_stage", "message": "Profile validation fallback."} in loss.warnings

    monkeypatch.setattr(service, "_DEFAULT_LIFE_STAGE_MESSAGES", {})
    gain = service.fallback_targets_response(
        _request(goal="gain", life_stage="pregnant"),
        reason="",
        life_stage_warning_factory=lambda _age, _stage, _lang: [],
        include_generic_life_stage_note=True,
    )

    assert gain.kcal_daily > 0
    assert gain.warnings == [
        {
            "code": "life_stage",
            "message": "Special nutrition considerations apply",
        }
    ]


@pytest.mark.parametrize("validator_mode", ["raises", "invalid-shape"])
def test_targets_safety_validation_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    validator_mode: str,
) -> None:
    def _raising_validator(_targets: object) -> object:
        raise RuntimeError("private-validator-detail")

    def _invalid_shape_validator(_targets: object) -> object:
        return ("not-a-list",)

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        _raising_validator if validator_mode == "raises" else _invalid_shape_validator,
    )

    _assert_http_exception(
        lambda: service.generate_who_targets_response(_request()),
        status_code=500,
        detail=service.WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL,
    )


def test_targets_missing_builder_preserves_strict_and_fallback_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        None,
    )

    fallback = service.generate_who_targets_response(_request())
    assert 1200 <= fallback.kcal_daily <= 5000

    _assert_http_exception(
        lambda: service.generate_who_targets_response(
            _request(),
            allow_backend_fallback=False,
        ),
        status_code=503,
        detail=service.WHO_TARGETS_UNAVAILABLE_DETAIL,
    )


def test_targets_profile_and_builder_value_errors_use_stable_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _invalid_profile(_request: WHOTargetsRequest) -> object:
        raise ValueError("private-profile-detail")

    with monkeypatch.context() as patch:
        patch.setattr(service, "_build_user_profile", _invalid_profile)
        _assert_http_exception(
            lambda: service.generate_who_targets_response(_request()),
            status_code=400,
            detail=service.INVALID_TARGETS_INPUT_DETAIL,
        )

    def _rejected_builder(_profile: object) -> object:
        raise ValueError("private-builder-detail")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _rejected_builder,
    )
    fallback = service.generate_who_targets_response(_request(goal="loss", life_stage="pregnant"))

    assert fallback.priority_micros["iodine_ug"] == 150.0
    assert any(warning["code"] == "life_stage" for warning in fallback.warnings)


def test_targets_import_and_unexpected_builder_errors_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _missing_builder(_profile: object) -> object:
        raise ImportError("private-optional-dependency")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _missing_builder,
    )
    fallback = service.generate_who_targets_response(_request())
    assert 1200 <= fallback.kcal_daily <= 5000

    _assert_http_exception(
        lambda: service.generate_who_targets_response(
            _request(),
            allow_backend_fallback=False,
        ),
        status_code=503,
        detail=service.WHO_TARGETS_UNAVAILABLE_DETAIL,
    )

    def _broken_builder(_profile: object) -> object:
        raise RuntimeError("private-provider-detail")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _broken_builder,
    )
    _assert_http_exception(
        lambda: service.generate_who_targets_response(_request()),
        status_code=500,
        detail=service.WHO_TARGETS_CALCULATION_FAILED_DETAIL,
    )


def test_targets_response_mapping_failure_is_stable_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_builder = service.nutrition_recommendations.build_nutrition_targets
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        lambda _targets: [],
    )

    def _broken_alias_mapping(_micros: dict[str, float]) -> dict[str, float]:
        raise RuntimeError("private-response-mapping-detail")

    monkeypatch.setattr(service, "alias_micros", _broken_alias_mapping)

    _assert_http_exception(
        lambda: service.generate_who_targets_response(
            _request(),
            targets_builder=real_builder,
        ),
        status_code=500,
        detail=service.WHO_TARGETS_CALCULATION_FAILED_DETAIL,
    )


def test_gaps_reject_invalid_intake_before_optional_backends() -> None:
    _assert_http_exception(
        lambda: service.analyze_nutrient_gaps_response(_gaps_request(consumed={"iron_mg": -0.01})),
        status_code=400,
        detail=service.INVALID_NUTRIENT_GAPS_INPUT_DETAIL,
    )


def test_gaps_missing_backends_preserve_distinct_503_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(service, "_resolve_nutrient_gaps_analyzer", lambda: None)
        _assert_http_exception(
            lambda: service.analyze_nutrient_gaps_response(_gaps_request()),
            status_code=503,
            detail=service.NUTRIENT_GAPS_UNAVAILABLE_DETAIL,
        )

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        None,
    )
    _assert_http_exception(
        lambda: service.analyze_nutrient_gaps_response(_gaps_request()),
        status_code=503,
        detail=service.NUTRITION_TARGETS_UNAVAILABLE_DETAIL,
    )


def test_gaps_profile_and_builder_rejections_are_stable_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _invalid_profile(_request: WHOTargetsRequest) -> object:
        raise ValueError("private-profile-detail")

    with monkeypatch.context() as patch:
        patch.setattr(service, "_build_user_profile", _invalid_profile)
        _assert_http_exception(
            lambda: service.analyze_nutrient_gaps_response(_gaps_request()),
            status_code=400,
            detail=service.INVALID_NUTRIENT_GAPS_INPUT_DETAIL,
        )

    def _rejected_builder(_profile: object) -> object:
        raise ValueError("private-builder-detail")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _rejected_builder,
    )
    _assert_http_exception(
        lambda: service.analyze_nutrient_gaps_response(_gaps_request()),
        status_code=400,
        detail=service.INVALID_NUTRIENT_GAPS_INPUT_DETAIL,
    )


def test_gaps_optional_import_and_unexpected_failures_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _missing_analyzer() -> service.NutrientGapsAnalyzer:
        raise ImportError("private-optional-dependency")

    with monkeypatch.context() as patch:
        patch.setattr(
            service,
            "_resolve_nutrient_gaps_analyzer",
            _missing_analyzer,
        )
        _assert_http_exception(
            lambda: service.analyze_nutrient_gaps_response(_gaps_request()),
            status_code=503,
            detail=service.NUTRIENT_GAPS_UNAVAILABLE_DETAIL,
        )

    def _broken_analyzer(_targets: object, _consumed: object) -> object:
        raise RuntimeError("private-analyzer-detail")

    monkeypatch.setattr(
        service,
        "_resolve_nutrient_gaps_analyzer",
        lambda: _broken_analyzer,
    )
    _assert_http_exception(
        lambda: service.analyze_nutrient_gaps_response(_gaps_request()),
        status_code=500,
        detail=service.NUTRIENT_GAPS_FAILED_DETAIL,
    )


def test_nutrition_helpers_reject_bad_shapes_and_sync_present_aliases() -> None:
    with pytest.raises(TypeError, match="values must be a dict"):
        alias_micros(cast(dict[str, float], ["not", "a", "mapping"]))

    with pytest.raises(ValueError, match="must be numeric"):
        alias_micros({"iron_mg": cast(float, "not-a-number")})

    micros = {"iodine_ug": float("nan"), "iodine": 20.0}
    result = ensure_priority_micros(micros)

    assert result is micros
    assert micros == {"iodine_ug": 150.0, "iodine": 150.0}


def test_plate_alignment_uses_resolved_builder_override() -> None:
    canonical_builder = service.nutrition_recommendations.build_nutrition_targets
    calls: list[object] = []

    def _resolved_builder(profile: object) -> object:
        calls.append(profile)
        return canonical_builder(profile)

    request = PlateRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
        goal="maintain",
        life_stage="adult",
        lang="en",
    )

    macros, kcal, aligned = plate_service.align_macros_with_targets(
        request,
        {
            "macros": {
                "protein_g": 80,
                "fat_g": 50,
                "carbs_g": 200,
                "fiber_g": 20,
            }
        },
        targets_builder=_resolved_builder,
    )

    assert len(calls) == 1
    assert macros["protein_g"] > 0
    assert kcal is not None and kcal > 0
    assert aligned is True


def test_legacy_compatibility_shims_delegate_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_calls: list[tuple[WHOTargetsRequest, bool]] = []
    gaps_calls: list[NutrientGapsRequest] = []
    target_marker = object()
    gaps_marker = object()

    def _targets_delegate(
        request: WHOTargetsRequest,
        *,
        allow_backend_fallback: bool = True,
    ) -> object:
        target_calls.append((request, allow_backend_fallback))
        return target_marker

    def _gaps_delegate(request: NutrientGapsRequest) -> object:
        gaps_calls.append(request)
        return gaps_marker

    monkeypatch.setattr(
        legacy_app,
        "_generate_who_targets_response",
        _targets_delegate,
    )
    monkeypatch.setattr(
        legacy_app,
        "analyze_nutrient_gaps_response",
        _gaps_delegate,
    )
    request = _request()
    gaps_request = _gaps_request()

    strict_result = asyncio.run(legacy_app.premium_targets_legacy(request))
    alias_result = asyncio.run(legacy_app.api_who_targets(_payload()))
    gaps_result = asyncio.run(legacy_app.api_nutrient_gaps(gaps_request))

    assert strict_result is target_marker
    assert alias_result is target_marker
    assert gaps_result is gaps_marker
    assert target_calls == [(request, False), (request, True)]
    assert gaps_calls == [gaps_request]


def _function_node(path: Path, function_name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    )


def _assert_no_legacy_or_sys_modules(node: ast.AST) -> None:
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            assert all(alias.name != "legacy_app" for alias in child.names)
        if isinstance(child, ast.ImportFrom):
            assert child.module != "legacy_app"
        if isinstance(child, ast.Attribute) and child.attr == "modules":
            assert not isinstance(child.value, ast.Name) or child.value.id not in {
                "sys",
                "_sys",
            }


def _module_scope_nodes(node: ast.AST) -> Iterator[ast.AST]:
    for child in ast.iter_child_nodes(node):
        if isinstance(
            child,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
        ):
            continue
        yield child
        yield from _module_scope_nodes(child)


def _assert_no_module_scope_legacy_imports(tree: ast.Module) -> None:
    for node in _module_scope_nodes(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name != "legacy_app" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module != "legacy_app"


def test_targets_and_gaps_runtime_owners_do_not_resolve_through_legacy_facades() -> None:
    service_path = _REPO_ROOT / "app/services/pro_nutrition_targets.py"
    service_tree = ast.parse(service_path.read_text(encoding="utf-8"))
    _assert_no_legacy_or_sys_modules(service_tree)
    module_scope_imports = {
        alias.name
        for node in _module_scope_nodes(service_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    module_scope_imports.update(
        node.module
        for node in _module_scope_nodes(service_tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    assert "core.menu_engine" not in module_scope_imports
    assert {"core.recommendations", "core.targets"} <= module_scope_imports

    pro_router = _REPO_ROOT / "app/routers/pro_nutrition_contracts.py"
    legacy_router = _REPO_ROOT / "app/routers/legacy_premium_nutrition.py"
    for path, function_names in (
        (pro_router, ("pro_nutrition_targets",)),
        (
            legacy_router,
            ("api_who_targets", "premium_targets_legacy", "api_nutrient_gaps"),
        ),
    ):
        router_tree = ast.parse(path.read_text(encoding="utf-8"))
        _assert_no_module_scope_legacy_imports(router_tree)
        for function_name in function_names:
            _assert_no_legacy_or_sys_modules(_function_node(path, function_name))


def test_legacy_targets_gaps_and_shared_helpers_are_exact_aliases() -> None:
    assert legacy_app.NutrientGapsRequest is NutrientGapsRequest
    assert legacy_app.NutrientGapsResponse is NutrientGapsResponse
    assert legacy_app._generate_who_targets_response is service.generate_who_targets_response
    assert legacy_app._fallback_targets_response is service.fallback_targets_response
    assert legacy_app._clamp_daily_kcal is clamp_daily_kcal
    assert legacy_app._alias_micros is alias_micros
    assert legacy_app._ensure_priority_micros is ensure_priority_micros

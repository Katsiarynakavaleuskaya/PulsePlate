"""Production-path tests for canonical PRO targets and nutrient-gap ownership."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import legacy_app
from app.schemas.premium_contracts import (
    NutrientGapsRequest,
    NutrientGapsResponse,
    WHOTargetsRequest,
)
from app.services import pro_nutrition_targets as service
from core.bmr import FALLBACK_BMR_KCAL_PER_KG_PER_DAY
from core.nutrition_utils import (
    alias_micros,
    clamp_daily_kcal,
    ensure_priority_micros,
)
from core.utils import get_activity_factor

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _profile(*, lang: str = "en", life_stage: str = "adult") -> WHOTargetsRequest:
    return WHOTargetsRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
        goal="maintain",
        life_stage=life_stage,
        lang=lang,
    )


def _gaps_request(*, lang: str = "en") -> NutrientGapsRequest:
    return NutrientGapsRequest(
        user_profile=_profile(lang=lang),
        consumed_nutrients={
            "protein_g": 10.0,
            "iron_mg": 1.0,
            "calcium_mg": 100.0,
        },
    )


def test_generate_targets_success_preserves_contract_and_safety_bounds() -> None:
    response = service.generate_who_targets_response(_profile(lang="es"))

    assert 1200 <= response.kcal_daily <= 5000
    assert response.macros["protein_g"] > 0
    assert response.water_ml > 0
    assert response.priority_micros["iron"] == response.priority_micros["iron_mg"]
    assert response.priority_micros["fe"] == response.priority_micros["iron_mg"]
    assert response.priority_micros["iodine_ug"] > 0
    assert response.ui_labels.kcal_daily == "Calorías diarias"
    assert response.next_best_action is not None
    assert response.next_best_action.recommended_tier == "PRO"


def test_generate_targets_value_error_uses_documented_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _reject_profile(_profile: object) -> object:
        raise ValueError("profile cannot be calculated")

    monkeypatch.setattr(
        service.nutrition_recommendations, "build_nutrition_targets", _reject_profile
    )
    monkeypatch.setattr(service.time, "strftime", lambda _format: "2026-07-19")
    request = WHOTargetsRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=65,
        activity="moderate",
        goal="loss",
        life_stage="pregnant",
    )

    response = service.generate_who_targets_response(request)

    tdee = int(
        FALLBACK_BMR_KCAL_PER_KG_PER_DAY * request.weight_kg * get_activity_factor(request.activity)
    )
    assert response.kcal_daily == clamp_daily_kcal(int(tdee * 0.85))
    assert response.macros == {
        "protein_g": 104,
        "fat_g": 58,
        "carbs_g": 279,
        "fiber_g": 25,
    }
    assert response.calculation_date == "2026-07-19"
    assert response.priority_micros["iodine_ug"] == 150.0
    assert any(warning["code"] == "pregnant" for warning in response.warnings)
    assert any(warning["code"] == "life_stage" for warning in response.warnings)


@pytest.mark.parametrize(
    ("lang", "message"),
    [
        (
            "es-MX",
            "Embarazo: los requisitos difieren; consulte guías especializadas.",
        ),
        (
            "ru_RU",
            "Беременность: нормы отличаются; обратитесь к специализированным рекомендациям.",
        ),
    ],
)
def test_generate_targets_success_normalizes_life_stage_warning_locale(
    lang: str,
    message: str,
) -> None:
    response = service.generate_who_targets_response(_profile(lang=lang, life_stage="pregnant"))

    assert {"code": "pregnant", "message": message} in response.warnings


@pytest.mark.parametrize(
    ("lang", "message"),
    [
        (
            "es-MX",
            "Embarazo: los requisitos difieren; consulte guías especializadas.",
        ),
        (
            "ru_RU",
            "Беременность: нормы отличаются; обратитесь к специализированным рекомендациям.",
        ),
    ],
)
def test_generate_targets_fallback_normalizes_life_stage_warning_locale(
    monkeypatch: pytest.MonkeyPatch,
    lang: str,
    message: str,
) -> None:
    def _reject_profile(_profile: object) -> object:
        raise ValueError("profile cannot be calculated")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _reject_profile,
    )

    response = service.generate_who_targets_response(_profile(lang=lang, life_stage="pregnant"))

    assert {"code": "pregnant", "message": message} in response.warnings


def test_generate_targets_unexpected_failure_is_stable_and_does_not_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _crash(_profile: object) -> object:
        raise RuntimeError("provider-secret-value")

    monkeypatch.setattr(service.nutrition_recommendations, "build_nutrition_targets", _crash)

    with pytest.raises(HTTPException) as raised:
        service.generate_who_targets_response(_profile())

    assert raised.value.status_code == 500
    assert raised.value.detail == service.WHO_TARGETS_CALCULATION_FAILED_DETAIL
    assert "provider-secret-value" not in str(raised.value.detail)


def test_malformed_target_value_error_is_stable_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    malformed_target = SimpleNamespace(
        kcal_daily=2100,
        macros=SimpleNamespace(protein_g=100, fat_g=70, carbs_g=250, fiber_g=30),
        water_ml_daily=2200,
        micros=SimpleNamespace(
            get_priority_nutrients=lambda: {"iron_mg": "private-nonnumeric-value"}
        ),
        activity=SimpleNamespace(
            moderate_aerobic_min=150,
            strength_sessions=2,
            steps_daily=8000,
        ),
        calculation_date="2026-07-19",
    )
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        lambda _profile: malformed_target,
    )
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        lambda _targets: [],
    )

    with pytest.raises(HTTPException) as raised:
        service.generate_who_targets_response(_profile())

    assert raised.value.status_code == 500
    assert raised.value.detail == service.WHO_TARGETS_CALCULATION_FAILED_DETAIL
    assert "private-nonnumeric-value" not in str(raised.value.detail)


def test_generate_targets_missing_builder_falls_back_only_when_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.nutrition_recommendations, "build_nutrition_targets", None)

    fallback = service.generate_who_targets_response(_profile())
    assert 1200 <= fallback.kcal_daily <= 5000

    with pytest.raises(HTTPException) as raised:
        service.generate_who_targets_response(_profile(), allow_backend_fallback=False)

    assert raised.value.status_code == 503
    assert raised.value.detail == service.WHO_TARGETS_UNAVAILABLE_DETAIL


def test_safety_validator_success_is_returned_as_structured_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        lambda _targets: ["Hydration target above safe maximum"],
    )

    response = service.generate_who_targets_response(_profile())

    assert {"code": "safety", "message": "Hydration target above safe maximum"} in response.warnings


@pytest.mark.parametrize(
    "validator",
    [
        lambda _targets: (_ for _ in ()).throw(RuntimeError("validator-secret")),
        lambda _targets: ("invalid",),
        lambda _targets: [object()],
    ],
)
def test_safety_validator_fails_closed_with_stable_detail(
    monkeypatch: pytest.MonkeyPatch,
    validator: object,
) -> None:
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        validator,
    )

    with pytest.raises(HTTPException) as raised:
        service.generate_who_targets_response(_profile())

    assert raised.value.status_code == 500
    assert raised.value.detail == service.WHO_TARGETS_SAFETY_VALIDATION_FAILED_DETAIL
    assert "validator-secret" not in str(raised.value.detail)


@pytest.mark.parametrize(
    ("lang", "prefix"),
    [
        ("ru", "Для "),
        ("ru_RU", "Для "),
        ("es", "Para "),
        ("ES", "Para "),
        ("es-MX", "Para "),
    ],
)
def test_nutrient_gaps_uses_profile_language_for_food_first_recommendations(
    lang: str,
    prefix: str,
) -> None:
    response = service.analyze_nutrient_gaps_response(_gaps_request(lang=lang))

    assert response.gaps["iron_mg"]["priority"] == "high"
    assert response.food_recommendations
    assert all(
        recommendation.startswith(prefix) for recommendation in response.food_recommendations
    )
    assert response.adherence_score == 0.0


@pytest.mark.parametrize(
    "invalid_value",
    [
        pytest.param(-0.01, id="negative"),
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="infinity"),
    ],
)
def test_nutrient_gaps_rejects_invalid_consumed_values_before_core_calls(
    monkeypatch: pytest.MonkeyPatch,
    invalid_value: float,
) -> None:
    core_calls: list[str] = []

    def _unexpected_core_call(*_args: object) -> object:
        core_calls.append("called")
        raise AssertionError("core must not receive invalid consumed nutrients")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _unexpected_core_call,
    )
    monkeypatch.setattr(
        service,
        "_resolve_nutrient_gaps_analyzer",
        lambda: _unexpected_core_call,
    )
    request = _gaps_request()
    request.consumed_nutrients = {"iron_mg": invalid_value}

    with pytest.raises(HTTPException) as raised:
        service.analyze_nutrient_gaps_response(request)

    assert raised.value.status_code == 400
    assert raised.value.detail == service.INVALID_NUTRIENT_GAPS_INPUT_DETAIL
    assert core_calls == []


def test_nutrient_gaps_accepts_finite_non_negative_consumed_values() -> None:
    request = _gaps_request()
    request.consumed_nutrients = {
        "protein_g": 0.0,
        "iron_mg": 8.0,
        "calcium_mg": 1000.0,
    }

    response = service.analyze_nutrient_gaps_response(request)

    assert response.gaps["iron_mg"]["current_intake"] == 8.0
    assert 0.0 <= response.adherence_score <= 100.0


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (ValueError("private-analyzer-value"), 500, service.NUTRIENT_GAPS_FAILED_DETAIL),
        (RuntimeError("private-provider-value"), 500, service.NUTRIENT_GAPS_FAILED_DETAIL),
    ],
)
def test_nutrient_gaps_errors_use_stable_safe_envelopes(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    def _raise(_targets: object, _consumed: object) -> object:
        raise error

    monkeypatch.setattr(
        service,
        "_resolve_nutrient_gaps_analyzer",
        lambda: _raise,
    )

    with pytest.raises(HTTPException) as raised:
        service.analyze_nutrient_gaps_response(_gaps_request())

    assert raised.value.status_code == status_code
    assert raised.value.detail == detail
    assert "private-" not in str(raised.value.detail)


def test_nutrient_gaps_builder_value_error_remains_stable_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _reject_profile(_profile: object) -> object:
        raise ValueError("private-profile-value")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _reject_profile,
    )

    with pytest.raises(HTTPException) as raised:
        service.analyze_nutrient_gaps_response(_gaps_request())

    assert raised.value.status_code == 400
    assert raised.value.detail == service.INVALID_NUTRIENT_GAPS_INPUT_DETAIL
    assert "private-profile-value" not in str(raised.value.detail)


def test_nutrient_gaps_missing_dependencies_are_exact_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "_resolve_nutrient_gaps_analyzer", lambda: None)

    with pytest.raises(HTTPException) as missing_analyzer:
        service.analyze_nutrient_gaps_response(_gaps_request())
    assert missing_analyzer.value.status_code == 503
    assert missing_analyzer.value.detail == service.NUTRIENT_GAPS_UNAVAILABLE_DETAIL

    monkeypatch.undo()
    monkeypatch.setattr(service.nutrition_recommendations, "build_nutrition_targets", None)

    with pytest.raises(HTTPException) as missing_builder:
        service.analyze_nutrient_gaps_response(_gaps_request())
    assert missing_builder.value.status_code == 503
    assert missing_builder.value.detail == service.NUTRITION_TARGETS_UNAVAILABLE_DETAIL


def test_nutrient_gaps_resolver_import_error_is_stable_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _missing_analyzer() -> service.NutrientGapsAnalyzer:
        raise ImportError("private-optional-backend-name")

    monkeypatch.setattr(
        service,
        "_resolve_nutrient_gaps_analyzer",
        _missing_analyzer,
    )

    with pytest.raises(HTTPException) as raised:
        service.analyze_nutrient_gaps_response(_gaps_request())

    assert raised.value.status_code == 503
    assert raised.value.detail == service.NUTRIENT_GAPS_UNAVAILABLE_DETAIL
    assert "private-optional-backend-name" not in str(raised.value.detail)


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
            assert not isinstance(child.value, ast.Name) or child.value.id not in {"sys", "_sys"}


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


def test_ensure_priority_micros_preserves_legacy_in_place_identity() -> None:
    micros = {"iron_mg": 18.0, "iodine_ug": 0.0}

    result = ensure_priority_micros(micros)

    assert result is micros
    assert micros["iodine_ug"] == 150.0


@pytest.mark.parametrize(
    "invalid_value",
    [
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="positive-infinity"),
        pytest.param(float("-inf"), id="negative-infinity"),
    ],
)
def test_ensure_priority_micros_defaults_non_finite_value_and_present_alias(
    invalid_value: float,
) -> None:
    micros = {"iodine_ug": invalid_value, "iodine": 75.0}

    result = ensure_priority_micros(micros)

    assert result is micros
    assert micros == {"iodine_ug": 150.0, "iodine": 150.0}


def test_ensure_priority_micros_does_not_add_absent_alias() -> None:
    micros = {"iodine_ug": float("nan")}

    result = ensure_priority_micros(micros)

    assert result is micros
    assert micros == {"iodine_ug": 150.0}
    assert "iodine" not in micros


def test_ensure_priority_micros_preserves_finite_values_and_alias() -> None:
    micros = {"iodine_ug": 175.0, "iodine": 160.0}

    result = ensure_priority_micros(micros)

    assert result is micros
    assert micros == {"iodine_ug": 175.0, "iodine": 160.0}


def test_plate_alignment_passes_and_service_honors_resolved_targets_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = SimpleNamespace(
        kcal_daily=2250,
        macros=SimpleNamespace(
            protein_g=120,
            fat_g=70,
            carbs_g=280,
            fiber_g=30,
        ),
        water_ml_daily=2200,
        micros=SimpleNamespace(
            get_priority_nutrients=lambda: {
                "iron_mg": 18.0,
                "calcium_mg": 1000.0,
            }
        ),
        activity=SimpleNamespace(
            moderate_aerobic_min=150,
            strength_sessions=2,
            steps_daily=8000,
        ),
        calculation_date="2026-07-20",
    )
    resolved_calls: list[object] = []
    resolved_builders: list[object] = []

    def _resolved_builder(profile: object) -> object:
        resolved_calls.append(profile)
        return target

    def _unexpected_canonical_builder(_profile: object) -> object:
        raise AssertionError("Plate override must not use the canonical default builder")

    def _generate_with_observation(
        request: WHOTargetsRequest,
        *,
        allow_backend_fallback: bool = True,
        targets_builder: service.TargetsBuilder | None = None,
    ) -> object:
        resolved_builders.append(targets_builder)
        return service.generate_who_targets_response(
            request,
            allow_backend_fallback=allow_backend_fallback,
            targets_builder=targets_builder,
        )

    monkeypatch.setattr(legacy_app, "targets_disabled", lambda: False)
    monkeypatch.setattr(
        legacy_app,
        "_resolve_build_targets_callable",
        lambda: _resolved_builder,
    )
    monkeypatch.setattr(
        legacy_app,
        "_generate_who_targets_response",
        _generate_with_observation,
    )
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _unexpected_canonical_builder,
    )
    monkeypatch.setattr(
        service.nutrition_recommendations,
        "validate_targets_safety",
        lambda _targets: [],
    )
    request = legacy_app.PlateRequest(
        sex="female",
        age=34,
        height_cm=168,
        weight_kg=62,
        activity="light",
        goal="maintain",
        life_stage="adult",
        lang="en",
    )

    macros, kcal, aligned = legacy_app.align_macros_with_targets(
        request,
        {
            "macros": {
                "protein_g": 80,
                "fat_g": 50,
                "carbs_g": 200,
                "fiber_g": 20,
            }
        },
        [],
    )

    assert resolved_builders == [_resolved_builder]
    assert len(resolved_calls) == 1
    assert macros == {
        "protein_g": 120,
        "fat_g": 70,
        "carbs_g": 280,
        "fiber_g": 30,
    }
    assert kcal == 2250
    assert aligned is True


def test_legacy_targets_gaps_and_shared_helpers_are_exact_aliases() -> None:
    assert legacy_app.NutrientGapsRequest is NutrientGapsRequest
    assert legacy_app.NutrientGapsResponse is NutrientGapsResponse
    assert legacy_app._generate_who_targets_response is service.generate_who_targets_response
    assert legacy_app._fallback_targets_response is service.fallback_targets_response
    assert legacy_app._clamp_daily_kcal is clamp_daily_kcal
    assert legacy_app._alias_micros is alias_micros
    assert legacy_app._ensure_priority_micros is ensure_priority_micros

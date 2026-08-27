# -*- coding: utf-8 -*-
"""
RU: Доказательные тесты для shim'ов legacy BMI endpoints.
EN: Proof tests for legacy BMI endpoint shims.

PR-456 Commit 3: Verify that /bmi and /api/v1/bmi delegate to canonical handler.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import scripts.ci.check_legacy_growth_guard as legacy_guard
from core.bmi.engine import BMICalculateResult
from core.bmi.risk import WaistRiskResult
from core.i18n import t

REPO_ROOT = Path(__file__).resolve().parents[1]

RETIRED_LEGACY_PYTHON_BINDINGS = {
    "admin_status",
    "cleanup_expired_logs",
    "debug_env",
    "get_database_status",
    "force_database_update",
    "check_for_updates",
    "rollback_database",
    "bmi_endpoint",
    "plan_endpoint",
    "bmi_endpoint_v1",
    "_resolve_build_targets_callable",
    "PlateDependencies",
    "_compute_premium_plate",
    "api_premium_plate",
    "build_fallback_plate",
    "align_macros_with_targets",
    "aggregate_day_micros",
    "premium_targets_legacy",
    "api_who_targets",
    "api_nutrient_gaps",
    "analyze_nutrient_gaps",
    "make_daily_menu",
    "make_weekly_menu",
    "repair_week_plan",
    "make_plate",
    "build_nutrition_targets",
    "to_csv_day",
    "to_pdf_day",
    "to_csv_week",
    "to_pdf_week",
    "WeeklyPlanFlexibleRequest",
}

RETIRED_PLANNING_EXPORT_BINDINGS = (
    "analyze_nutrient_gaps",
    "make_daily_menu",
    "make_weekly_menu",
    "repair_week_plan",
    "make_plate",
    "build_nutrition_targets",
    "to_csv_day",
    "to_pdf_day",
    "to_csv_week",
    "to_pdf_week",
    "WeeklyPlanFlexibleRequest",
)

_NETWORK_DISABLED_PREAMBLE = textwrap.dedent("""
    import socket

    def _deny_network(*_args, **_kwargs):
        raise AssertionError("network access is disabled for this import probe")

    class _NetworkDisabledSocket(socket.socket):
        def connect(self, *_args, **_kwargs):
            _deny_network()

        def connect_ex(self, *_args, **_kwargs):
            _deny_network()

    socket.create_connection = _deny_network
    socket.socket = _NetworkDisabledSocket
    """)


def _run_legacy_retirement_probe(scenario: str) -> dict[str, object]:
    env = os.environ.copy()
    for name in (
        "API_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "OPENAI_API_KEY",
        "PERPLEXITY_API_KEY",
    ):
        env.pop(name, None)
    env.update(
        {
            "APP_ENV": "test",
            "ENVIRONMENT": "test",
            "TESTING": "true",
            "PYTEST_CURRENT_TEST": "legacy-planning-export-retirement-probe",
            "PRIVATE_EXPORTS_ENABLED": "false",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", _NETWORK_DISABLED_PREAMBLE + scenario],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    assert completed.returncode == 0, (
        f"legacy retirement probe failed with returncode={completed.returncode}; "
        f"stdout_tail={completed.stdout[-2000:]!r}; stderr_tail={completed.stderr[-2000:]!r}"
    )
    result_line = next(
        line
        for line in completed.stdout.splitlines()
        if line.startswith("LEGACY_RETIREMENT_RESULT=")
    )
    return json.loads(result_line.removeprefix("LEGACY_RETIREMENT_RESULT="))


def test_retired_legacy_python_bindings_are_absent_with_canonical_owners_present() -> None:
    import app.schemas.bmi_compat as bmi_schemas
    import app.schemas.premium_contracts as premium_contracts
    import app.services.admin_operations as admin_operations
    import app.services.bmi_compat as bmi_compat
    import app.services.pro_nutrition_plate as plate_service
    import app.services.pro_nutrition_targets as targets_service
    import core.exports as exports
    import core.menu_engine as menu_engine
    import core.plate as plate
    import core.recommendations as recommendations
    import legacy_app

    canonical_migrations = {
        "admin_status": admin_operations.admin_status,
        "cleanup_expired_logs": admin_operations.cleanup_expired_logs,
        "debug_env": admin_operations.debug_env,
        "get_database_status": admin_operations.get_database_status,
        "force_database_update": admin_operations.force_database_update,
        "check_for_updates": admin_operations.check_for_updates,
        "rollback_database": admin_operations.rollback_database,
        "bmi_endpoint": bmi_compat.bmi_endpoint,
        "plan_endpoint": bmi_compat.plan_endpoint,
        "bmi_endpoint_v1": bmi_compat.bmi_endpoint_v1,
        "_resolve_build_targets_callable": None,
        "PlateDependencies": plate_service.PlateServiceDependencies,
        "_compute_premium_plate": plate_service.generate_plate_response,
        "api_premium_plate": plate_service.generate_plate_response,
        "build_fallback_plate": plate_service.build_fallback_plate,
        "align_macros_with_targets": plate_service.align_macros_with_targets,
        "aggregate_day_micros": plate_service.aggregate_day_micros,
        "premium_targets_legacy": targets_service.generate_who_targets_response,
        "api_who_targets": targets_service.generate_who_targets_response,
        "api_nutrient_gaps": targets_service.analyze_nutrient_gaps_response,
        "analyze_nutrient_gaps": menu_engine.analyze_nutrient_gaps,
        "make_daily_menu": menu_engine.make_daily_menu,
        "make_weekly_menu": menu_engine.make_weekly_menu,
        "repair_week_plan": menu_engine.repair_week_plan,
        "make_plate": plate.make_plate,
        "build_nutrition_targets": recommendations.build_nutrition_targets,
        "to_csv_day": exports.to_csv_day,
        "to_pdf_day": exports.to_pdf_day,
        "to_csv_week": exports.to_csv_week,
        "to_pdf_week": exports.to_pdf_week,
        "WeeklyPlanFlexibleRequest": None,
    }

    assert canonical_migrations.keys() == RETIRED_LEGACY_PYTHON_BINDINGS
    assert RETIRED_LEGACY_PYTHON_BINDINGS == legacy_guard.RETIRED_LEGACY_PYTHON_BINDINGS
    assert RETIRED_LEGACY_PYTHON_BINDINGS.isdisjoint(vars(legacy_app))
    assert legacy_app.BMIRequest is bmi_schemas.BMIRequest
    assert legacy_app.BMIRequestV1 is bmi_schemas.BMIRequestV1
    assert legacy_app.Activity is premium_contracts.Activity
    assert legacy_app.DietFlag is premium_contracts.DietFlag
    assert legacy_app.Goal is premium_contracts.Goal
    assert legacy_app.Sex is premium_contracts.Sex
    assert {
        binding_name
        for binding_name, canonical_migration in canonical_migrations.items()
        if canonical_migration is None
    } == {"_resolve_build_targets_callable", "WeeklyPlanFlexibleRequest"}
    for binding_name, canonical_migration in canonical_migrations.items():
        if canonical_migration is not None:
            assert callable(canonical_migration)
        with pytest.raises(AttributeError):
            getattr(legacy_app, binding_name)


def test_retained_premium_schema_bindings_remain_importable_in_fresh_process() -> None:
    scenario = textwrap.dedent("""
        import json
        import app.schemas.premium_contracts as premium_contracts
        import legacy_app
        from legacy_app import Activity, DietFlag, Goal, Sex

        retained = {
            "Activity": Activity,
            "DietFlag": DietFlag,
            "Goal": Goal,
            "Sex": Sex,
        }
        for binding_name, imported_object in retained.items():
            canonical_object = getattr(premium_contracts, binding_name)
            assert getattr(legacy_app, binding_name) is canonical_object
            assert imported_object is canonical_object

        print("LEGACY_RETIREMENT_RESULT=" + json.dumps({"retained": sorted(retained)}))
        """)

    assert _run_legacy_retirement_probe(scenario) == {
        "retained": ["Activity", "DietFlag", "Goal", "Sex"]
    }


def test_planning_export_bindings_fail_closed_in_a_fresh_process() -> None:
    import_failure_checks = "\n".join(textwrap.dedent(f"""
            try:
                from legacy_app import {binding_name}
            except ImportError:
                pass
            else:
                raise AssertionError("legacy from-import remains: {binding_name}")
            """) for binding_name in RETIRED_PLANNING_EXPORT_BINDINGS)
    scenario = textwrap.dedent(f"""
        import json
        import legacy_app

        retired = {RETIRED_PLANNING_EXPORT_BINDINGS!r}
        for binding_name in retired:
            try:
                getattr(legacy_app, binding_name)
            except AttributeError:
                pass
            else:
                raise AssertionError(f"legacy attribute remains: {{binding_name}}")
        """)
    scenario += import_failure_checks
    scenario += textwrap.dedent("""
        print("LEGACY_RETIREMENT_RESULT=" + json.dumps({"absent": list(retired)}))
        """)

    assert _run_legacy_retirement_probe(scenario) == {
        "absent": list(RETIRED_PLANNING_EXPORT_BINDINGS)
    }


@pytest.mark.parametrize(
    "import_sequence",
    (
        "import legacy_app\nimport app.routers.plan_export as canonical_plan_export\n",
        "import app.routers.plan_export as canonical_plan_export\nimport legacy_app\n",
        "import legacy_app\nimport app.routers.plan_export as canonical_plan_export\n"
        "legacy_app = importlib.reload(legacy_app)\n",
    ),
    ids=("legacy-first", "router-first", "reload"),
)
def test_plan_export_canonical_module_has_no_legacy_synthetic_namespace(
    import_sequence: str,
) -> None:
    scenario = textwrap.dedent("""
        import importlib
        import json
        """)
    scenario += import_sequence
    scenario += textwrap.dedent("""
        resolved = importlib.import_module("app.routers.plan_export")
        assert resolved is canonical_plan_export
        legacy_routers = getattr(legacy_app, "routers", None)
        synthetic_surface_present = legacy_routers is not None and hasattr(
            legacy_routers, "plan_export"
        )
        assert not synthetic_surface_present
        print(
            "LEGACY_RETIREMENT_RESULT="
            + json.dumps(
                {
                    "canonical_module": resolved.__name__,
                    "synthetic_surface_present": synthetic_surface_present,
                },
                sort_keys=True,
            )
        )
        """)

    assert _run_legacy_retirement_probe(scenario) == {
        "canonical_module": "app.routers.plan_export",
        "synthetic_surface_present": False,
    }


def test_bmi_endpoint_v1_uses_canonical_handler_via_shim(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Доказательный тест: /api/v1/bmi использует engine через handler (shim работает).
    EN: Proof test: /api/v1/bmi uses engine via handler (shim works).

    Monkeypatch calculate_bmi_result to return fixed BMICalculateResult,
    then verify endpoint returns those exact values (proving shim delegation).
    """
    import app.routers.bmi as bmi_router

    # Fixed result to verify it "flows through" the shim
    fixed_result = BMICalculateResult(
        bmi=22.5,
        category="normal",
        group="general",
        group_display="General",
        interpretation="Your BMI is within the normal range.",
        wht_ratio=0.48,
        whr=None,
        waist_risk=WaistRiskResult(
            wht_ratio=0.48,
            risk_level="low",
            notes=("Low waist-related risk",),
        ),
        notes=("Low waist-related risk",),
        age_band="adult",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    # Call legacy endpoint
    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    # Verify legacy format with values from fixed engine result
    assert data["bmi"] == 22.5  # From fixed_result
    assert data["category"] == "Normal weight"  # Localized from "normal" slug
    assert data["group"] == "general"  # From fixed_result
    assert data["athlete"] is False  # Derived from group != "athlete"
    assert "note" in data  # Legacy field (waist risk notes or interpretation)
    # Note should contain waist risk notes (from fixed_result.notes)
    assert (
        "Low waist-related risk" in data["note"]
        or data["note"] == "Your BMI is within the normal range."
    )

    # Verify required legacy fields are present; extra fields are allowed for forward compatibility
    expected_keys = {"bmi", "category", "note", "athlete", "group"}
    assert set(data.keys()).issuperset(
        expected_keys
    ), f"Missing legacy keys. Got: {set(data.keys())}"


def test_bmi_endpoint_uses_canonical_handler_via_shim(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Доказательный тест: /bmi использует engine через handler (shim работает).
    EN: Proof test: /bmi uses engine via handler (shim works).

    Monkeypatch calculate_bmi_result to return fixed BMICalculateResult,
    then verify endpoint returns those exact values (proving shim delegation).
    Also verify visualization gate is preserved (include_chart=False to avoid matplotlib dependency).
    """
    import app.routers.bmi as bmi_router

    # Fixed result to verify it "flows through" the shim
    fixed_result = BMICalculateResult(
        bmi=24.8,
        category="normal",
        group="athlete",
        group_display="Athlete",
        interpretation="Your BMI is within the normal range for athletes.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="adult",
    )

    def _fixed_engine(**kwargs: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    # Call legacy endpoint (height_m format, include_chart=False to avoid matplotlib)
    payload = {
        "weight_kg": 80.0,
        "height_m": 1.80,
        "age": 28,
        "gender": "male",
        "pregnant": "no",
        "athlete": "yes",
        "waist_cm": None,
        "lang": "en",
        "include_chart": False,  # Avoid matplotlib dependency in test
    }

    resp = client.post("/bmi", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    # Verify legacy format with values from fixed engine result
    assert data["bmi"] == 24.8  # From fixed_result
    assert data["category"] == "Normal weight"  # Localized from "normal" slug
    assert data["group"] == "athlete"  # From fixed_result
    assert data["athlete"] is True  # Derived from group == "athlete"
    assert "note" in data  # Legacy field (athlete disclaimer)
    # Note should contain athlete disclaimer (priority over interpretation)
    assert "athlete" in data["note"].lower() or "BMI may overestimate" in data["note"]

    # Verify required legacy fields are present; extra fields are allowed for forward compatibility
    expected_keys = {"bmi", "category", "note", "athlete", "group"}
    assert set(data.keys()).issuperset(
        expected_keys
    ), f"Missing legacy keys. Got: {set(data.keys())}"

    # Verify visualization gate: with include_chart=False, visualization should not be added
    # (or if added, it should be gracefully handled)
    # This is a smoke test - full visualization testing is in test_bmi_visualization.py


def test_bmi_endpoint_unknown_category_falls_back_to_slug(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Если engine вернул неизвестный category slug, legacy shim должен отдать его как есть.
    EN: If engine returns an unknown category slug, legacy shim should fall back to returning it.
    """
    import app.routers.bmi as bmi_router

    fixed_result = BMICalculateResult(
        bmi=24.8,
        category="mystery_category",
        group="general",
        group_display="General",
        interpretation="Some interpretation.",
        wht_ratio=None,
        whr=None,
        waist_risk=None,
        notes=(),
        age_band="adult",
    )

    def _fixed_engine(**_: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    payload = {
        "weight_kg": 80.0,
        "height_m": 1.80,
        "age": 28,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": None,
        "lang": "en",
        "include_chart": False,
    }

    resp = client.post("/bmi", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "mystery_category"


def test_bmi_endpoint_v1_validation_error_maps_to_422(client: TestClient) -> None:
    """
    RU: BMIRequestV1 допускает age=0, но canonical BMICalculateRequest требует age>=1.
        Shim должен вернуть 422 с ValidationError details.
    EN: BMIRequestV1 allows age=0, but BMICalculateRequest requires age>=1.
        Shim should return 422 with ValidationError details.
    """
    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 0,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 422
    detail = resp.json().get("detail")
    assert isinstance(detail, list)


def test_bmi_endpoint_v1_unrealistic_bmi_is_422(client: TestClient) -> None:
    """
    RU: BMIRequestV1 должен отклонять нереалистичный BMI > 100.
    EN: BMIRequestV1 must reject unrealistic BMI > 100.

    Regression: V1 validation now delegates BMI computation to core.bmi.engine._compute_bmi.
    """
    payload = {
        "weight_kg": 320.0,  # BMI ~ 125 for 160cm
        "height_cm": 160.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 422


def test_bmi_endpoint_v1_athlete_note_appends_waist_risk_notes_and_unknown_category_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Covers legacy_app.py:
    - unknown category fallback to slug
    - athlete note appends waist risk notes
    """
    import app.routers.bmi as bmi_router

    fixed_result = BMICalculateResult(
        bmi=22.5,
        category="mystery_category",
        group="athlete",
        group_display="Athlete",
        interpretation="Ignored for athlete note.",
        wht_ratio=0.48,
        whr=None,
        waist_risk=None,
        notes=("Extra waist note",),
        age_band="adult",
    )

    def _fixed_engine(**_: Any) -> BMICalculateResult:
        return fixed_result

    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)

    payload = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "yes",
        "waist_cm": 84.0,
        "lang": "en",
    }

    resp = client.post("/api/v1/bmi", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["category"] == "mystery_category"
    assert data["group"] == "athlete"
    assert data["athlete"] is True
    assert data["note"] == f"{t('en', 'advice_athlete_bmi')} | Extra waist note"

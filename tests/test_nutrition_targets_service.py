"""Tests for profile-derived weekly planning target adapters."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.services import nutrition_targets
from core.targets import UserProfile


def test_estimate_targets_from_profile_builds_profile_and_maps_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_profiles: list[UserProfile] = []
    priority_micros = {
        "iron_mg": 18.0,
        "calcium_mg": 1000.0,
        "vitamin_d_iu": 600.0,
    }

    mock_targets = SimpleNamespace(
        kcal_daily=2075,
        macros=SimpleNamespace(
            protein_g=118,
            fat_g=69,
            carbs_g=246,
            fiber_g=31,
        ),
        micros=SimpleNamespace(
            get_priority_nutrients=lambda: dict(priority_micros),
        ),
        water_ml_daily=2300,
        activity=SimpleNamespace(
            moderate_aerobic_min=150,
            vigorous_aerobic_min=75,
            strength_sessions=2,
            steps_daily=8500,
        ),
    )

    def fake_build_nutrition_targets(profile: UserProfile) -> Any:
        captured_profiles.append(profile)
        return mock_targets

    monkeypatch.setattr(
        nutrition_targets,
        "build_nutrition_targets",
        fake_build_nutrition_targets,
    )

    payload = nutrition_targets.estimate_targets_from_profile(
        sex="female",
        age=34,
        height_cm=168.5,
        weight_kg=64.2,
        activity="active",
        goal="maintain",
    )

    assert len(captured_profiles) == 1
    profile = captured_profiles[0]
    assert profile == UserProfile(
        sex="female",
        age=34,
        height_cm=168.5,
        weight_kg=64.2,
        activity="active",
        goal="maintain",
    )
    assert set(payload) == {"kcal", "macros", "micro", "water_ml", "activity_week"}
    assert payload["kcal"] == 2075
    assert payload["macros"] == {
        "protein_g": 118,
        "fat_g": 69,
        "carbs_g": 246,
        "fiber_g": 31,
    }
    assert payload["micro"] == priority_micros
    assert payload["water_ml"] == 2300
    assert payload["activity_week"] == {
        "moderate_aerobic_min": 150,
        "vigorous_aerobic_min": 75,
        "strength_sessions": 2,
        "steps_daily": 8500,
    }


@pytest.mark.parametrize(
    "targets, expected",
    [
        ({}, False),
        ({"kcal": 2000}, False),
        (
            {
                "kcal": 2000,
                "macros": "invalid",
                "micro": {"iron_mg": 18.0},
                "water_ml": 2000,
            },
            False,
        ),
        (
            {
                "kcal": 2000,
                "macros": {"protein_g": 110},
                "micro": "invalid",
                "water_ml": 2000,
            },
            False,
        ),
        (
            {
                "kcal": 2000,
                "macros": {},
                "micro": {"iron_mg": 18.0},
                "water_ml": 2000,
            },
            False,
        ),
        (
            {
                "kcal": 2000,
                "macros": {"protein_g": 110},
                "micro": {},
                "water_ml": 2000,
            },
            False,
        ),
        (
            {
                "kcal": 2000,
                "macros": {"protein_g": 110},
                "micro": {"iron_mg": 18.0},
                "water_ml": 2000,
                "activity_week": "invalid",
            },
            False,
        ),
        (
            {
                "kcal": 2000,
                "macros": {"protein_g": 110},
                "micro": {"iron_mg": 18.0},
                "water_ml": 2000,
            },
            True,
        ),
        (
            {
                "kcal": 2000,
                "macros": {"protein_g": 110},
                "micro": {"iron_mg": 18.0},
                "water_ml": 2000,
                "activity_week": {"steps_daily": 8000},
            },
            True,
        ),
    ],
)
def test_is_complete_planning_targets(targets: dict[str, Any], expected: bool) -> None:
    assert nutrition_targets.is_complete_planning_targets(targets) is expected


def test_service_has_no_fastapi_or_pydantic_imports() -> None:
    source_path = Path(nutrition_targets.__file__).resolve()
    tree = ast.parse(source_path.read_text())

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", maxsplit=1)[0])

    assert "fastapi" not in imported_roots
    assert "pydantic" not in imported_roots

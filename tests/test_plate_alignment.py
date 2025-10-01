from __future__ import annotations

import importlib
from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_plate_alignment_with_targets(monkeypatch):
    """Plate API aligns macros to targets when deviation is large."""
    app_mod = importlib.import_module("app")

    # Provide a build_nutrition_targets that returns macros far from plate defaults
    # to ensure alignment path is taken.
    class FakeTargets:
        def __init__(self):
            # Make carbs high enough to force deviation >= 40%
            self.macros = SimpleNamespace(
                protein_g=96,  # arbitrary, near typical
                fat_g=54,
                carbs_g=186,  # target carbs reference used in failing case previously
                fiber_g=25,
            )
            # minimal attributes used by other routes (not relevant here)
            self.kcal_daily = 2200
            self.activity = SimpleNamespace(
                moderate_aerobic_min=150, strength_sessions=2, steps_daily=8000
            )
            self.micros = SimpleNamespace(get_priority_nutrients=lambda: {})
            self.calculation_date = "2025-01-01"

    def fake_build_targets(_profile):
        return FakeTargets()

    monkeypatch.setattr(app_mod, "build_nutrition_targets", fake_build_targets, raising=False)

    with TestClient(app_mod.app) as client:
        payload = {
            "sex": "male",
            "age": 59,
            "height_cm": 150.0,
            "weight_kg": 53.0,
            "activity": "sedentary",
            "goal": "loss",
        }
        r = client.post("/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"})
        assert r.status_code == 200
        data = r.json()
        # Expect carbs aligned to target value when deviation exceeds threshold
        assert data["macros"]["carbs_g"] == 186

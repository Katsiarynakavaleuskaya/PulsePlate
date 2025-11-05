import logging
from typing import Any, Dict

import pytest
from starlette.requests import Request

from app.routers import plan_export


@pytest.mark.parametrize("days_count", [0, 1, 2])
def test_build_pdf_week_debug_branch(
    caplog: pytest.LogCaptureFixture, days_count: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover the debug branch guarded by logger.isEnabledFor(logging.DEBUG).

    We patch internals to avoid external dependencies and call the route handler directly.
    """
    # Minimal week
    days: list[Dict[str, Any]] = []
    for i in range(days_count):
        days.append(
            {
                "date": f"2025-01-0{i+1}",
                "meals": [
                    {
                        "title": "Meal",
                        "items": [
                            {
                                "name": "apple",
                                "quantity": 1,
                                "unit": "pcs",
                                "kcal": 52,
                                "protein_g": 0.3,
                                "fat_g": 0.2,
                                "carbs_g": 14,
                            }
                        ],
                        "totals": {
                            "kcal": 52,
                            "protein_g": 0.3,
                            "fat_g": 0.2,
                            "carbs_g": 14,
                        },
                    }
                ],
                "totals": {
                    "energy_kcal": 52,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbs_g": 14,
                },
            }
        )

    week: Dict[str, Any] = {
        "week_start": "2025-01-01",
        "days": days,
        "totals": {
            "energy_kcal": 52 * max(1, days_count),
            "protein_g": 0.3 * max(1, days_count),
            "fat_g": 0.2 * max(1, days_count),
            "carbs_g": 14 * max(1, days_count),
        },
    }

    # Patch internals to be deterministic and dependency-light
    monkeypatch.setattr(plan_export, "_get_week_plan", lambda: week)
    monkeypatch.setattr(plan_export, "_register_font", lambda: "Helvetica")
    monkeypatch.setattr(plan_export, "_require_valid_token", lambda: None)

    # Build a minimal ASGI scope for Request
    scope = {"type": "http", "method": "GET", "path": "/api/v1/plan/week/export.pdf", "headers": []}
    request = Request(scope)  # type: ignore[arg-type]

    logger = logging.getLogger(plan_export.__name__)
    prev_level = logger.level
    logger.setLevel(logging.DEBUG)

    with caplog.at_level(logging.DEBUG, logger=plan_export.__name__):
        response = plan_export.export_week_pdf(request, lang="en")  # type: ignore[call-arg]
        # Ensure PDF bytes returned
        assert response.status_code == 200
        assert response.media_type == "application/pdf"
        body = response.body
        assert isinstance(body, (bytes, bytearray)) and len(body) > 0

    logger.setLevel(prev_level)

    # Assert that the debug message about story components was emitted
    assert any(
        "Story components count=" in rec.getMessage() for rec in caplog.records
    ), "Expected debug message with story component counts not found"

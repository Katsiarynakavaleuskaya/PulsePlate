"""Weekly plan export endpoints (CSV)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
import csv
from typing import Any, Dict, Iterable, List

from fastapi import APIRouter, Response

plan_router = APIRouter(prefix="/api/v1/plan", tags=["plan"])


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _get_week_plan() -> Dict[str, Any]:
    """Return a demo week plan structure.

    Replace this stub with the real planner integration when available.
    """

    return {
        "days": [
            {
                "date": "2025-09-29",
                "meals": [
                    {
                        "name": "Завтрак",
                        "items": [
                            {
                                "name": "Овсянка",
                                "qty": 60,
                                "unit": "g",
                                "energy_kcal": 230,
                                "protein_g": 8,
                                "carbs_g": 40,
                                "fat_g": 4,
                                "note": "с ягодами",
                            },
                            {
                                "name": "Йогурт",
                                "qty": 1,
                                "unit": "pcs",
                                "energy_kcal": 61,
                                "protein_g": 5,
                                "carbs_g": 4,
                                "fat_g": 3,
                            },
                        ],
                    },
                    {
                        "name": "Обед",
                        "items": [
                            {
                                "name": "Курица",
                                "qty": 150,
                                "unit": "g",
                                "energy_kcal": 248,
                                "protein_g": 35,
                                "fat_g": 10,
                                "note": "запечённая",
                            },
                        ],
                    },
                ],
            }
        ]
    }


def _iter_rows(week: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    days: List[Dict[str, Any]] = list(week.get("days") or [])
    for di, day in enumerate(days, start=1):
        date = day.get("date") or ""
        meals = day.get("meals") or []
        for meal in meals:
            meal_name = meal.get("name") or meal.get("meal") or ""
            for item in meal.get("items") or []:
                yield {
                    "date": date,
                    "day_idx": di,
                    "meal": meal_name,
                    "item": item.get("name") or item.get("title") or "",
                    "qty": item.get("qty") or "",
                    "unit": item.get("unit") or "",
                    "energy_kcal": item.get("energy_kcal") or "",
                    "protein_g": item.get("protein_g") or "",
                    "carbs_g": item.get("carbs_g") or "",
                    "fat_g": item.get("fat_g") or "",
                    "note": item.get("note") or "",
                }


@plan_router.get("/week/export.csv")
def export_week_csv() -> Response:
    week = _get_week_plan()
    buffer = StringIO()
    fieldnames = [
        "date",
        "day_idx",
        "meal",
        "item",
        "qty",
        "unit",
        "energy_kcal",
        "protein_g",
        "carbs_g",
        "fat_g",
        "note",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in _iter_rows(week):
        writer.writerow(row)

    filename = f"week_plan_{_current_timestamp()}.csv"
    return Response(
        content=buffer.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["plan_router"]

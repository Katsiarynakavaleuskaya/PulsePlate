"""Tests for weekly plan CSV export."""

from fastapi.testclient import TestClient

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from app.py file
import importlib.util

spec = importlib.util.spec_from_file_location("app_module", "app.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load app.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app
from app.routers import plan_export as plan


client = TestClient(app)


def _signed_csv_url() -> str:
    response = client.post("/api/v1/export/sign", json={"path": "/api/v1/plan/week/export.csv"})
    assert response.status_code == 200
    return response.json()["url"]


def test_week_export_csv_ok() -> None:
    url = _signed_csv_url()
    response = client.get(url)
    assert response.status_code == 200

    content_type = response.headers.get("content-type", "")
    disposition = response.headers.get("content-disposition", "")
    assert "text/csv" in content_type
    assert "attachment" in disposition

    lines = response.text.splitlines()
    assert lines
    assert lines[0].startswith("# WEEK_TOTALS:")
    assert "energy_kcal=" in lines[0]
    assert "protein_g=" in lines[0]
    assert "carbs_g=" in lines[0]
    assert "fat_g=" in lines[0]
    assert lines[1] == "date,day_idx,meal,item,qty,unit,energy_kcal,protein_g,carbs_g,fat_g,note"


def test_sum_week_macros_handles_types() -> None:
    week = {
        "days": [
            {
                "meals": [
                    {
                        "items": [
                            {
                                "energy_kcal": "100",
                                "protein_g": 10,
                                "carbs_g": 20.5,
                                "fat_g": None,
                            },
                            {
                                "energy_kcal": 50,
                                "protein_g": "5",
                                "carbs_g": "bad",
                                "fat_g": 1,
                            },
                        ]
                    }
                ]
            }
        ]
    }

    totals = plan.sum_week_macros(week)
    assert totals["energy_kcal"] == 150.0
    assert totals["protein_g"] == 15.0
    assert totals["carbs_g"] == 20.5
    assert totals["fat_g"] == 1.0

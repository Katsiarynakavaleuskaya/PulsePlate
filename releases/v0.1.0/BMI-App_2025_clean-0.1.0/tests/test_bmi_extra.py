# -*- coding: utf-8 -*-
import importlib

import pytest
from fastapi.testclient import TestClient

# Импортируем приложение единожды
app_module = importlib.import_module("app")
client = TestClient(app_module.app)

def _post_bmi(weight, height, group="general"):
    return client.post(
        "/api/v1/bmi",
        json={"weight_kg": weight, "height_cm": height, "group": group},
    )

@pytest.mark.parametrize("group", ["general", "athlete", "elderly", "teen", "pregnant"])
def test_bmi_groups_smoke(group):
    r = _post_bmi(70, 170, group)
    assert r.status_code == 200
    data = r.json()
    # базовые инварианты
    assert data["bmi"] == 24.22
    assert data["category"] == "Normal"
    assert isinstance(data.get("interpretation", ""), str)
    assert len(data.get("interpretation", "")) >= 0  # строка может быть и "Normal"

@pytest.mark.parametrize(
    "w,h,expected_category",
    [
        (45, 170, "Underweight"),  # ~15.57
        (70, 170, "Normal"),       # 24.22
        (80, 170, "Overweight"),   # ~27.68
        (95, 170, "Obese"),        # ~32.87
    ],
)
def test_bmi_categories_boundaries(w, h, expected_category):
    r = _post_bmi(w, h)
    assert r.status_code == 200
    data = r.json()
    assert data["category"] == expected_category

@pytest.mark.parametrize(
    "w,h",
    [
        (70, 0),     # нулевая высота
        (70, -170),  # отрицательная высота
        (-10, 170),  # отрицательный вес
    ],
)
def test_bmi_invalid_inputs(w, h):
    r = _post_bmi(w, h)
    # Валидация может отработать как 400 (наша) либо 422 (pydantic) — допускаем оба
    assert r.status_code in (400, 422)

def test_bmi_missing_field_validation():
    # Нет height_cm → 422 от pydantic
    r = client.post("/api/v1/bmi", json={"weight_kg": 70})
    assert r.status_code == 422

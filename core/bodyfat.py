from __future__ import annotations

import math
from typing import Mapping


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("bool is not a valid float input")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"Unsupported float input type: {type(value).__name__}")


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("bool is not a valid int input")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("float value must be an integer")
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Unsupported int input type: {type(value).__name__}")


def bf_deurenberg(bmi: float, age: int, gender: str) -> float:
    sex = 1 if gender.lower().startswith("male") else 0
    return 1.20 * bmi + 0.23 * age - 10.8 * sex - 5.4


def bf_us_navy(
    height_cm: float,
    neck_cm: float,
    waist_cm: float,
    gender: str,
    hip_cm: float | None = None,
) -> float:
    g = gender.lower()
    if g.startswith("male"):
        return 86.010 * math.log10(waist_cm - neck_cm) - 70.041 * math.log10(height_cm) + 36.76

    if hip_cm is None:
        raise ValueError("hip_cm required for female")
    return (
        163.205 * math.log10(waist_cm + hip_cm - neck_cm) - 97.684 * math.log10(height_cm) - 78.387
    )


def bf_ymca(weight_kg: float, waist_cm: float, gender: str) -> float:
    weight_lb = weight_kg * 2.20462
    waist_in = waist_cm / 2.54
    if gender.lower().startswith("male"):
        body_fat = (weight_lb * 1.082 + 94.42) - (waist_in * 4.15)
    else:
        body_fat = (weight_lb * 0.732 + 8.987) + (waist_in / 3.14)
    return (body_fat / weight_lb) * 100.0


def estimate_all(data: Mapping[str, object]) -> dict[str, object]:
    results: dict[str, float] = {}

    if {"bmi", "age", "gender"} <= data.keys():
        try:
            bmi = _as_float(data["bmi"])
            age = _as_int(data["age"])
            gender = str(data["gender"])
        except (ValueError, TypeError, KeyError):
            pass
        else:
            results["deurenberg"] = bf_deurenberg(bmi, age, gender)

    if {"height_cm", "neck_cm", "waist_cm", "gender"} <= data.keys():
        try:
            height_cm = _as_float(data["height_cm"])
            neck_cm = _as_float(data["neck_cm"])
            waist_cm = _as_float(data["waist_cm"])
            gender = str(data["gender"])
            hip_cm_val = data.get("hip_cm")
            hip_cm = _as_float(hip_cm_val) if hip_cm_val is not None else None
        except (ValueError, TypeError, KeyError):
            pass
        else:
            try:
                results["us_navy"] = bf_us_navy(height_cm, neck_cm, waist_cm, gender, hip_cm)
            except (ValueError, TypeError):
                pass

    if {"weight_kg", "waist_cm", "gender"} <= data.keys():
        try:
            weight_kg = _as_float(data["weight_kg"])
            waist_cm = _as_float(data["waist_cm"])
            gender = str(data["gender"])
        except (ValueError, TypeError, KeyError):
            pass
        else:
            results["ymca"] = bf_ymca(weight_kg, waist_cm, gender)

    rounded = {k: round(v, 2) for k, v in results.items()}
    values = list(rounded.values())
    median = round(sorted(values)[len(values) // 2], 2) if values else None
    return {"methods": rounded, "median": median}

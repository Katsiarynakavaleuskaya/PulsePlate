"""
My Plate Generator - Visual Plate Portions and Nutrition Planning

RU: Генератор «Моей Тарелки» с визуальными секторами и порциями в чашках/ладонях.
EN: Generates 'My Plate' with visual sectors and cup/palm portions.

This module provides plate visualization logic for daily nutrition recommendations,
converting macro targets into understandable visual portions using the hand/cup method.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Set

Goal = Literal["loss", "maintain", "gain"]

# RU: Базовые нормы порционирования (на 1 приём пищи) по методу ладони/чашки.
# EN: Base serving heuristics per meal (hand/cup method).
SERVE = {
    "protein_palm_g": 30,   # 1 ладонь белка ≈ 25–35 г белка
    "fat_thumb_g": 12,      # 1 «большой палец» жира ≈ 10–15 г жира
    "carb_cup_g": 40,       # 1 чашка крахмалов ≈ 35–45 г углеводов (сухой вес в пересчёте)
    "veg_cup_g": 80,        # 1 чашка овощей ≈ 70–100 г (низкокалор.)
}


def _target_kcal(tdee_val: float, goal: Goal, deficit_pct: Optional[float], surplus_pct: Optional[float]) -> int:
    """RU: Выставляем целевую калорийность под цель.
    EN: Set target kcal per goal.
    """
    if goal == "maintain":
        return int(round(tdee_val))
    if goal == "loss":
        pct = (deficit_pct or 15) / 100.0
        return max(1200, int(round(tdee_val * (1 - pct))))
    # gain
    pct = (surplus_pct or 12) / 100.0
    return int(round(tdee_val * (1 + pct)))


def _macros_by_rules(weight_kg: float, kcal: int, goal: Goal) -> Dict[str, int]:
    """RU: Макросы из простых правил: белок 1.6–2.0 г/кг, жир 0.8–1.0 г/кг, углеводы — остаток.
    EN: Macros via rules: protein 1.6–2.0 g/kg, fat 0.8–1.0 g/kg, carbs = rest.
    """
    # Чуть варьируем по цели
    if goal == "loss":
        protein_g = round(max(1.8 * weight_kg, 1.6 * weight_kg))
        fat_g = round(0.8 * weight_kg)
    elif goal == "gain":
        protein_g = round(1.6 * weight_kg)
        fat_g = round(1.0 * weight_kg)
    else:  # maintain
        protein_g = round(1.7 * weight_kg)
        fat_g = round(0.9 * weight_kg)

    # Углеводы из остатка калорий (4/9/4 правило)
    kcal_pro = protein_g * 4
    kcal_fat = fat_g * 9
    carbs_g = max(0, round((kcal - kcal_pro - kcal_fat) / 4))
    # Клетчатка целимся 25–35 г/сут (зависит от калорийности, дадим минимум 25)
    fiber_g = 25 if kcal < 2200 else 30

    return {
        "protein_g": int(protein_g),
        "fat_g": int(fat_g),
        "carbs_g": int(carbs_g),
        "fiber_g": int(fiber_g),
    }


def _portions_from_macros(macros: Dict[str, int], meals_per_day: int = 3) -> Dict[str, Any]:
    """RU: Переводим макросы в «ладони/чашки» для интерфейса.
    EN: Convert macros to palms/cups portions for UI.
    """
    p_palm = macros["protein_g"] / (SERVE["protein_palm_g"] * meals_per_day)
    f_thumb = macros["fat_g"] / (SERVE["fat_thumb_g"] * meals_per_day)
    c_cup = macros["carbs_g"] / (SERVE["carb_cup_g"] * meals_per_day)
    v_cup = (macros["fiber_g"] * 10) / (SERVE["veg_cup_g"] * meals_per_day)  # эвристика

    return {
        "protein_palm": round(p_palm, 1),
        "fat_thumbs": round(f_thumb, 1),
        "carb_cups": round(c_cup, 1),
        "veg_cups": round(v_cup, 1),
        "meals_per_day": meals_per_day,
    }


def _visual_layout(macros: Dict[str, int]) -> List[Dict[str, Any]]:
    """RU: Возвращаем спеку для тарелки: 4 сектора + 2 чашки.
    EN: Return visual spec: 4 sectors + 2 bowls.
    """
    total = macros["protein_g"] + macros["fat_g"] + macros["carbs_g"]
    # Доли с защитой от деления на ноль
    frac = {
        "protein": (macros["protein_g"] / total) if total else 0.33,
        "carbs": (macros["carbs_g"] / total) if total else 0.33,
        "fat": (macros["fat_g"] / total) if total else 0.34,
        "veg": 0.30,  # фиксированная доля тарелки под овощи/зелень на глаз
    }
    # Нормируем: белки/угли/жиры распределяем на 70% площади тарелки; овощи — 30%
    energy_part = 0.70
    energy_sum = frac["protein"] + frac["carbs"] + frac["fat"]
    k = (energy_part / energy_sum) if energy_sum else 1.0

    layout = [
        {"kind": "plate_sector", "fraction": round(frac["veg"], 2), "label": "Овощи/Зелень",
         "tooltip": "Низкая калорийность, клетчатка 25–35 г/сут"},
        {"kind": "plate_sector", "fraction": round(frac["protein"] * k, 2), "label": "Белок",
         "tooltip": f"{macros['protein_g']} г/сут"},
        {"kind": "plate_sector", "fraction": round(frac["carbs"] * k, 2), "label": "Крахмалы/Зерно",
         "tooltip": f"{macros['carbs_g']} г/сут"},
        {"kind": "plate_sector", "fraction": round(frac["fat"] * k, 2), "label": "Полезные жиры",
         "tooltip": f"{macros['fat_g']} г/сут"},
        {"kind": "bowl", "fraction": 1.0, "label": "Чашка крупы", "tooltip": "≈1 cup/приём"},
        {"kind": "bowl", "fraction": 1.0, "label": "Чашка овощей", "tooltip": "≈1–2 cup/приём"},
    ]
    return layout


def make_plate(*, weight_kg: float, tdee_val: float, goal: Goal,
               deficit_pct: Optional[float], surplus_pct: Optional[float],
               diet_flags: Optional[Set[str]] = None) -> Dict[str, Any]:
    """RU: Главная функция: целевые калории → макросы → порции → визуалка.
    EN: Main: target kcal → macros → portions → visual.
    """
    target = _target_kcal(tdee_val, goal, deficit_pct, surplus_pct)
    macros = _macros_by_rules(weight_kg, target, goal)
    portions = _portions_from_macros(macros, meals_per_day=3)
    layout = _visual_layout(macros)

    # Пример простых блюд под флаги; фронт может показывать карточки
    meals = [
        {"title": "Овсянка + орехи + ягоды", "kcal": int(target*0.25),
         "protein_g": int(macros["protein_g"]*0.25), "fat_g": int(macros["fat_g"]*0.25),
         "carbs_g": int(macros["carbs_g"]*0.25)},
        {"title": "Гречка + курица/тофу + салат", "kcal": int(target*0.35),
         "protein_g": int(macros["protein_g"]*0.35), "fat_g": int(macros["fat_g"]*0.35),
         "carbs_g": int(macros["carbs_g"]*0.35)},
        {"title": "Рис + рыба/нут + овощи", "kcal": int(target*0.40),
         "protein_g": int(macros["protein_g"]*0.40), "fat_g": int(macros["fat_g"]*0.40),
         "carbs_g": int(macros["carbs_g"]*0.40)},
    ]

    # Упрощённые замены под флаги
    if diet_flags:
        if "VEG" in diet_flags:
            for m in meals:
                m["title"] = m["title"].replace("курица/тофу", "тофу").replace("рыба/нут", "нут")
        if "GF" in diet_flags:
            for m in meals:
                m["title"] = m["title"].replace("Овсянка", "Гречка").replace("Рис", "Гречка")
        if "DAIRY_FREE" in diet_flags:
            # просто не добавляем молочку в названиях/рецептах
            pass
        if "LOW_COST" in diet_flags:
            for m in meals:
                m["title"] += " (бюджет)"

    return {
        "kcal": int(target),
        "macros": macros,
        "portions": portions,
        "layout": layout,
        "meals": meals,
    }

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
    "protein_palm_g": 30,  # 1 ладонь белка ≈ 25–35 г белка
    "fat_thumb_g": 12,  # 1 «большой палец» жира ≈ 10–15 г жира
    "carb_cup_g": 40,  # 1 чашка углеводов ≈ 35–45 г углеводов (сухой вес в пересчёте)
    "veg_cup_g": 80,  # 1 чашка овощей ≈ 70–100 г (низкокалор.)
}


def target_kcal(
    tdee_val: float,
    goal: Goal,
    deficit_pct: Optional[float],
    surplus_pct: Optional[float],
) -> int:
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


def macros_by_rules(weight_kg: float, kcal: int, goal: Goal) -> Dict[str, int]:
    """RU: Макросы из простых правил: белок 1.6-2.0 g/kg, жир 0.8-1.0 g/kg, углеводы — остаток.
    EN: Macros via rules: protein 1.6-2.0 g/kg, fat 0.8-1.0 g/kg, carbs = rest.
    """
    # Чуть варьируем по цели
    # Align with tests: loss emphasizes protein (≥1.8 g/kg) and lower fat (0.8 g/kg),
    # maintain uses ~1.7 g/kg protein and 0.9 g/kg fat, gain uses 1.6 g/kg protein and 1.0 g/kg fat.
    if goal == "loss":
        protein_g: float = float(round(1.8 * weight_kg))
        fat_g: float = float(round(0.8 * weight_kg))
    elif goal == "gain":
        protein_g = float(round(1.6 * weight_kg))
        fat_g = float(round(1.0 * weight_kg))
    else:  # maintain
        protein_g = float(round(1.7 * weight_kg))
        fat_g = float(round(0.9 * weight_kg))

    # Углеводы из остатка калорий (4/9/4 правило)
    kcal_pro = protein_g * 4
    kcal_fat = fat_g * 9
    remaining_kcal = kcal - kcal_pro - kcal_fat

    if remaining_kcal < 0:
        # Если белок + жир превышают калории, уменьшаем белок и жир с полами в g/kg
        excess_kcal = -remaining_kcal
        protein_floor = 1.0 * weight_kg
        reduc_pro = min(excess_kcal / 4, max(0.0, protein_g - protein_floor))
        if reduc_pro > 0:
            protein_g -= reduc_pro
            kcal_pro = protein_g * 4
            remaining_kcal = kcal - kcal_pro - kcal_fat

        if remaining_kcal < 0:
            # Если всё ещё отрицательно, уменьшаем жир
            fat_floor = 0.5 * weight_kg
            reduc_fat = min((-remaining_kcal) / 9, max(0.0, fat_g - fat_floor))
            if reduc_fat > 0:
                fat_g -= reduc_fat
                kcal_fat = fat_g * 9
                remaining_kcal = kcal - kcal_pro - kcal_fat

    carbs_g = max(1, round(remaining_kcal / 4))
    # Клетчатка целимся 25–35 г/сут (зависит от калорийности, дадим минимум 25)
    fiber_g = 25 if kcal < 2200 else 30

    return {
        "protein_g": int(protein_g),
        "fat_g": int(fat_g),
        "carbs_g": int(carbs_g),
        "fiber_g": int(fiber_g),
    }


def apply_diet_flag_adjustments(
    macros: Dict[str, int],
    *,
    weight_kg: float,
    kcal: int,
    diet_flags: Optional[Set[str]],
) -> Dict[str, int]:
    """
    RU: Адаптирует макросы под флаги питания (HIGH_PROTEIN, LOW_CARB, MEDITERRANEAN).
    EN: Adjust macros for dietary flags (HIGH_PROTEIN, LOW_CARB, MEDITERRANEAN).
    """
    if not diet_flags:
        return macros

    protein = float(macros["protein_g"])
    fat = float(macros["fat_g"])
    carbs = float(macros["carbs_g"])
    fiber = float(macros["fiber_g"])
    changed = False

    if "HIGH_PROTEIN" in diet_flags:
        target_protein = max(protein, weight_kg * 2.0)
        if target_protein > protein:
            protein = target_protein
            changed = True

    carb_ceiling: Optional[float] = None

    if "LOW_CARB" in diet_flags:
        # Стремимся к 25% калорий из углеводов, но не ниже 40 г
        low_carb_cap = max(40.0, (kcal * 0.25) / 4)
        if carbs > low_carb_cap:
            carbs = low_carb_cap
            changed = True
        carb_ceiling = low_carb_cap

    if "MEDITERRANEAN" in diet_flags:
        # Средиземноморское питание: больше полезных жиров и клетчатки
        # Жир должен быть минимум в 1.2 раза больше белка (здоровая пропорция)
        desired_fat = max(fat, protein * 1.2, (kcal * 0.35) / 9)
        if desired_fat > fat:
            fat = desired_fat
            changed = True
        fiber = max(fiber, 30.0)

    if not changed:
        return macros

    # Перерасчитываем углеводы, чтобы не выходить за предел калорий
    protein_kcal = protein * 4
    fat_kcal = fat * 9
    remaining_kcal = kcal - protein_kcal - fat_kcal

    if remaining_kcal < 0:
        # Сначала уменьшаем жир, но не ниже 0.7 g/kg (здоровый минимум)
        min_fat = 0.7 * weight_kg
        if "MEDITERRANEAN" in diet_flags:
            min_fat = max(min_fat, protein * 1.2)
        if fat > min_fat:
            reduc = min((-remaining_kcal) / 9, fat - min_fat)
            if reduc > 0:
                fat -= reduc
                fat_kcal = fat * 9
                remaining_kcal = kcal - protein_kcal - fat_kcal
        if remaining_kcal < 0:
            # Затем при необходимости слегка уменьшаем белок, но не ниже 1.6 g/kg
            min_protein = 1.6 * weight_kg
            if "HIGH_PROTEIN" in diet_flags:
                min_protein = max(min_protein, 2.0 * weight_kg)
            if protein > min_protein:
                reduc = min((-remaining_kcal) / 4, protein - min_protein)
                if reduc > 0:
                    protein -= reduc
                    protein_kcal = protein * 4
                    remaining_kcal = kcal - protein_kcal - fat_kcal

    # Use 40g floor if LOW_CARB is active, otherwise 30g
    carb_floor = 40.0 if carb_ceiling is not None else 30.0
    computed_carbs = max(carb_floor, remaining_kcal / 4 if remaining_kcal > 0 else carb_floor)
    if carb_ceiling is not None:
        carbs = min(carb_ceiling, computed_carbs)
    else:
        carbs = computed_carbs

    return {
        "protein_g": round(protein),
        "fat_g": round(fat),
        "carbs_g": round(carbs),
        "fiber_g": round(fiber),
    }


def portions_from_macros(macros: Dict[str, int], meals_per_day: int = 3) -> Dict[str, float]:
    """RU: Переводим макросы в «ладони/чашки» для интерфейса.
    EN: Convert macros to palms/cups portions for UI.

    Returns only physical portion measurements (not metadata like meals_per_day).
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
        {
            "kind": "plate_sector",
            "fraction": round(frac["veg"], 2),
            "label": "Овощи/Зелень",
            "tooltip": "Низкая калорийность, клетчатка 25–35 г/сут",
        },
        {
            "kind": "plate_sector",
            "fraction": round(frac["protein"] * k, 2),
            "label": "Белок",
            "tooltip": f"{macros['protein_g']} г/сут",
        },
        {
            "kind": "plate_sector",
            "fraction": round(frac["carbs"] * k, 2),
            "label": "Углеводы",
            "tooltip": f"{macros['carbs_g']} г/сут",
        },
        {
            "kind": "plate_sector",
            "fraction": round(frac["fat"] * k, 2),
            "label": "Полезные жиры",
            "tooltip": f"{macros['fat_g']} г/сут",
        },
        {
            "kind": "bowl",
            "fraction": 1.0,
            "label": "Чашка крупы",
            "tooltip": "≈1 cup/приём",
        },
        {
            "kind": "bowl",
            "fraction": 1.0,
            "label": "Чашка овощей",
            "tooltip": "≈1–2 cup/приём",
        },
    ]
    return layout


def make_plate(
    *,
    weight_kg: float,
    tdee_val: float,
    goal: Goal,
    deficit_pct: Optional[float],
    surplus_pct: Optional[float],
    diet_flags: Optional[Set[str]] = None,
    meals_per_day: int = 3,
) -> Dict[str, Any]:
    """RU: Главная функция: целевые калории → макросы → порции → визуалка.
    EN: Main: target kcal → macros → portions → visual.

    Args:
        weight_kg: Body weight in kilograms.
        tdee_val: Total Daily Energy Expenditure value.
        goal: Nutrition goal: "loss", "maintain", or "gain".
        deficit_pct: Calorie deficit percentage for weight loss (optional).
        surplus_pct: Calorie surplus percentage for weight gain (optional).
        diet_flags: Optional set of dietary flags (e.g., "VEGAN", "KETO", "GF").
        meals_per_day: Number of meals per day for portion calculation (default: 3).

    Returns:
        Dictionary containing kcal, macros, portions, layout, meals, and meals_per_day.

    Raises:
        ValueError: If meals_per_day is not an integer or is outside the valid range [1, 12].
    """
    # Validate meals_per_day parameter
    # RU: Проверяем, что meals_per_day - целое число в разумном диапазоне
    # EN: Validate that meals_per_day is an integer within reasonable range
    if not isinstance(meals_per_day, int):
        raise ValueError(
            f"meals_per_day must be an integer, got {type(meals_per_day).__name__}: {meals_per_day}"
        )
    if not (1 <= meals_per_day <= 12):
        raise ValueError(f"meals_per_day must be between 1 and 12 (inclusive), got {meals_per_day}")

    target = target_kcal(tdee_val, goal, deficit_pct, surplus_pct)
    normalized_flags: Optional[Set[str]] = None
    if diet_flags:
        normalized_flags = set(diet_flags)
        # Resolve incompatible combinations for predictable UX
        if {"KETO", "VEGAN"}.issubset(normalized_flags):
            # Prefer vegan-friendly low-carb/high-protein without keto labeling
            normalized_flags.discard("KETO")
        if "VEGAN" in normalized_flags:
            normalized_flags.add("VEG")
        if "KETO" in normalized_flags:
            normalized_flags.update({"LOW_CARB", "HIGH_PROTEIN"})
        if "PALEO" in normalized_flags:
            normalized_flags.add("HIGH_PROTEIN")
    macros = macros_by_rules(weight_kg, target, goal)
    macros = apply_diet_flag_adjustments(
        macros,
        weight_kg=weight_kg,
        kcal=target,
        diet_flags=normalized_flags,
    )
    portions = portions_from_macros(macros, meals_per_day=meals_per_day)
    layout = _visual_layout(macros)

    # Пример простых блюд под флаги; фронт может показывать карточки
    meals = [
        {
            "title": "Овсянка + орехи + ягоды",
            "kcal": int(target * 0.25),
            "protein_g": int(macros["protein_g"] * 0.25),
            "fat_g": int(macros["fat_g"] * 0.25),
            "carbs_g": int(macros["carbs_g"] * 0.25),
        },
        {
            "title": "Гречка + курица/тофу + салат",
            "kcal": int(target * 0.35),
            "protein_g": int(macros["protein_g"] * 0.35),
            "fat_g": int(macros["fat_g"] * 0.35),
            "carbs_g": int(macros["carbs_g"] * 0.35),
        },
        {
            "title": "Рис + рыба/нут + овощи",
            "kcal": int(target * 0.40),
            "protein_g": int(macros["protein_g"] * 0.40),
            "fat_g": int(macros["fat_g"] * 0.40),
            "carbs_g": int(macros["carbs_g"] * 0.40),
        },
    ]

    # Упрощённые замены под флаги
    if normalized_flags:
        if "VEG" in normalized_flags:
            for m in meals:
                title = str(m.get("title", ""))
                m["title"] = title.replace("курица/тофу", "тофу").replace("рыба/нут", "нут")
        if "VEGAN" in normalized_flags:
            for m in meals:
                title = str(m.get("title", ""))
                m["title"] = title.replace("тофу", "тофу/нут").replace("йогурт", "соевый йогурт")
        if "GF" in normalized_flags:
            for m in meals:
                title = str(m.get("title", ""))
                m["title"] = title.replace("Овсянка", "Гречка").replace("Рис", "Гречка")
        if "DAIRY_FREE" in normalized_flags:
            # просто не добавляем молочку в названиях/рецептах
            pass
        if "LOW_COST" in normalized_flags:
            for m in meals:
                title = str(m.get("title", ""))
                m["title"] = title + " (бюджет)"
        if "HIGH_PROTEIN" in normalized_flags:
            for m in meals:
                m["title"] = f"{m.get('title', '')} (высокобелковое)"
        if "LOW_CARB" in normalized_flags:
            replacements = {
                "Овсянка + орехи + ягоды": "Омлет + овощи + авокадо",
                "Гречка + курица/тофу + салат": "Цветная капуста + курица/тофу + салат",
                "Рис + рыба/нут + овощи": "Киноа + рыба/нут + овощи",
            }
            for m in meals:
                current = str(m.get("title", ""))
                m["title"] = replacements.get(current, current + " (низкоуглеводное)")
        if "MEDITERRANEAN" in normalized_flags:
            mediterranean_upgrades = [
                "с оливковым маслом",
                "с орехами и зеленью",
                "с хумусом и цельнозерновыми",
            ]
            for idx, m in enumerate(meals):
                base = str(m.get("title", ""))
                suffix = mediterranean_upgrades[idx % len(mediterranean_upgrades)]
                m["title"] = f"{base} ({suffix})"
        if "KETO" in normalized_flags:
            for m in meals:
                title = str(m.get("title", ""))
                if "Омлет" not in title and "яйца" not in title.lower():
                    m["title"] = title + " (кето-версия)"
        if "PALEO" in normalized_flags:
            for m in meals:
                title = str(m.get("title", ""))
                m["title"] = title.replace("Гречка", "батат").replace("Овсянка", "чиа пудинг")

    return {
        "kcal": int(target),
        "macros": macros,
        "portions": portions,
        "layout": layout,
        "meals": meals,
        "meals_per_day": meals_per_day,
    }


# =============================================================================
# Planner Engine Facade Functions
# =============================================================================
# These functions provide a simplified API for tests and external callers.


def create_nutrition_plate(foods: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Create a nutrition plate from a list of foods.

    RU: Создание тарелки питания из списка продуктов.
    EN: Create nutrition plate from food list.

    Args:
        foods: List of food items with nutrition info

    Returns:
        Plate info dict or None if creation fails
    """
    if not foods:
        return {}

    try:
        # Calculate totals from foods
        totals: Dict[str, float] = {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "fiber": 0,
        }

        for food in foods:
            if isinstance(food, dict):
                totals["calories"] += food.get("calories", 0) or 0
                totals["protein"] += food.get("protein", 0) or 0
                totals["carbs"] += food.get("carbs", 0) or 0
                totals["fat"] += food.get("fat", 0) or 0
                totals["fiber"] += food.get("fiber", 0) or 0

        # Calculate percentages
        total_cal = totals["calories"] or 1  # Avoid division by zero
        return {
            "totals": totals,
            "protein_g": int(totals["protein"]),
            "carbs_g": int(totals["carbs"]),
            "fat_g": int(totals["fat"]),
            "fiber_g": int(totals["fiber"]),
            "kcal": int(totals["calories"]),
            "protein_pct": round(totals["protein"] * 4 / total_cal * 100, 1),
            "carbs_pct": round(totals["carbs"] * 4 / total_cal * 100, 1),
            "fat_pct": round(totals["fat"] * 9 / total_cal * 100, 1),
        }
    except (TypeError, ValueError):
        return None


def analyze_plate_balance(foods: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Analyze the nutritional balance of a plate.

    RU: Анализ баланса питательных веществ.
    EN: Analyze plate nutritional balance.

    Args:
        foods: List of food items

    Returns:
        Balance analysis dict or None
    """
    plate = create_nutrition_plate(foods)
    if not plate:
        return {}

    kcal = plate.get("kcal", 1) or 1
    protein = plate.get("protein_g", 0)
    carbs = plate.get("carbs_g", 0)
    fat = plate.get("fat_g", 0)

    # Calculate ratios (calories from each macro / total calories)
    protein_ratio = (protein * 4) / kcal if kcal > 0 else 0
    carbs_ratio = (carbs * 4) / kcal if kcal > 0 else 0
    fat_ratio = (fat * 9) / kcal if kcal > 0 else 0

    # Determine balance status based on typical macro guidelines
    # Ideal: 15-25% protein, 45-65% carbs, 20-35% fat
    balance_status = "balanced"
    if protein_ratio < 0.15:
        balance_status = "low_protein"
    elif carbs_ratio < 0.40:
        balance_status = "low_carbs"
    elif fat_ratio > 0.40:
        balance_status = "high_fat"

    return {
        "protein_ratio": round(protein_ratio, 3),
        "carbs_ratio": round(carbs_ratio, 3),
        "fat_ratio": round(fat_ratio, 3),
        "status": balance_status,
        "kcal": kcal,
    }


def get_plate_recommendations(foods: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """
    Get recommendations to improve plate balance.

    RU: Заглушка - рекомендации по улучшению.
    EN: Stub - plate improvement recommendations.

    Args:
        foods: List of food items

    Returns:
        List of recommendations or None
    """
    balance = analyze_plate_balance(foods)
    if not balance:
        return []

    recommendations: List[Dict[str, Any]] = []

    status = balance.get("status", "balanced")
    if status == "low_protein":
        recommendations.append(
            {
                "type": "increase_protein",
                "reason": "Protein intake is below recommended level",
                "suggestion": "Add lean meats, fish, eggs, or legumes",
            }
        )
    elif status == "low_carbs":
        recommendations.append(
            {
                "type": "increase_carbs",
                "reason": "Carbohydrate intake is below recommended level",
                "suggestion": "Add whole grains, fruits, or vegetables",
            }
        )
    elif status == "high_fat":
        recommendations.append(
            {
                "type": "reduce_fat",
                "reason": "Fat intake exceeds recommended level",
                "suggestion": "Choose leaner protein sources and reduce oils",
            }
        )

    return recommendations


def calculate_plate_score(foods: List[Dict[str, Any]]) -> Optional[float]:
    """
    Calculate a quality score for the plate (0-100).

    RU: Расчёт оценки качества тарелки.
    EN: Calculate plate quality score.

    Args:
        foods: List of food items

    Returns:
        Score from 0 to 100 or None
    """
    balance = analyze_plate_balance(foods)
    if not balance:
        return 0.0

    score = 100.0

    # Penalize for imbalances
    protein_ratio = balance.get("protein_ratio", 0)
    carbs_ratio = balance.get("carbs_ratio", 0)
    fat_ratio = balance.get("fat_ratio", 0)

    # Ideal ranges: protein 0.15-0.25, carbs 0.45-0.65, fat 0.20-0.35
    if protein_ratio < 0.15:
        score -= (0.15 - protein_ratio) * 100
    elif protein_ratio > 0.25:
        score -= (protein_ratio - 0.25) * 50

    if carbs_ratio < 0.45:
        score -= (0.45 - carbs_ratio) * 50
    elif carbs_ratio > 0.65:
        score -= (carbs_ratio - 0.65) * 50

    if fat_ratio < 0.20:
        score -= (0.20 - fat_ratio) * 30
    elif fat_ratio > 0.35:
        score -= (fat_ratio - 0.35) * 100

    return max(0.0, min(100.0, score))


def visualize_plate_data(foods: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Generate visualization data for the plate.

    RU: Данные для визуализации тарелки.
    EN: Generate plate visualization data.

    Args:
        foods: List of food items

    Returns:
        Visualization data dict or None
    """
    plate = create_nutrition_plate(foods)
    if not plate:
        return {}

    # Generate sectors for pie chart visualization
    sectors = []
    protein_pct = plate.get("protein_pct", 0)
    carbs_pct = plate.get("carbs_pct", 0)
    fat_pct = plate.get("fat_pct", 0)

    if protein_pct > 0:
        sectors.append({"name": "protein", "percent": protein_pct, "color": "#e74c3c"})
    if carbs_pct > 0:
        sectors.append({"name": "carbs", "percent": carbs_pct, "color": "#3498db"})
    if fat_pct > 0:
        sectors.append({"name": "fat", "percent": fat_pct, "color": "#f39c12"})

    return {
        "type": "pie",
        "sectors": sectors,
        "totals": plate.get("totals", {}),
        "kcal": plate.get("kcal", 0),
    }

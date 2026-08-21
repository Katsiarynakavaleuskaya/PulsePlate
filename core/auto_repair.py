# -*- coding: utf-8 -*-
"""
RU: Модуль для авто-ремонта недельных планов с UX-петлей.
EN: Module for auto-repair of weekly meal plans with UX loop.

Sprint 5: Auto-repair недели (UX-петля)
"""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import math
from numbers import Real
from typing import Any, Dict, List, Optional, cast

from core.menu_engine import (
    DayMenu,
    WeekMenu,
    _calculate_day_nutrients,
    calculate_known_nutrient_gaps,
    has_complete_nutrition_evidence,
    repair_week_plan,
)
from core.targets import MicronutrientTargets, NutritionTargets

_VEGETABLE_TERMS = ("vegetable",)
_PROTEIN_TERMS = ("meat", "chicken", "fish", "beef")


class RepairStrategy(Enum):
    """Стратегии ремонта"""

    CONSERVATIVE = "conservative"  # Минимальные изменения
    BALANCED = "balanced"  # Сбалансированный подход
    AGGRESSIVE = "aggressive"  # Максимальные изменения


class RepairStatus(Enum):
    """Статусы ремонта"""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_MANUAL = "needs_manual"


_CANONICAL_STRATEGY_BY_REPAIR_STRATEGY = {
    RepairStrategy.BALANCED: "boosters_first",
    RepairStrategy.CONSERVATIVE: "replace_ingredients",
    RepairStrategy.AGGRESSIVE: "add_snacks",
}


def _ingredient_name(ingredient: Mapping[str, object]) -> str:
    """Return one normalized ingredient name without coercing malformed values."""
    name = ingredient.get("name")
    return name.strip().lower() if isinstance(name, str) else ""


def _is_vegetable(name: str) -> bool:
    """Recognize only the finite ingredient vocabulary used by this repair seam."""
    return any(term in name for term in _VEGETABLE_TERMS)


def _is_protein(name: str) -> bool:
    """Recognize only the finite ingredient vocabulary used by this repair seam."""
    return any(term in name for term in _PROTEIN_TERMS)


def validate_week_plan(week_plan: object) -> dict[str, object]:
    """Validate the bounded dictionary plan consumed by VIP auto-repair."""
    if not isinstance(week_plan, dict):
        raise ValueError("week_plan must be an object")

    days = week_plan.get("days")
    if not isinstance(days, list) or not days:
        raise ValueError("week_plan.days must be a non-empty list")

    for day in days:
        if not isinstance(day, dict):
            raise ValueError("each week_plan day must be an object")
        meals = day.get("meals")
        if not isinstance(meals, list) or not meals:
            raise ValueError("each week_plan day must contain meals")
        for meal in meals:
            if not isinstance(meal, dict):
                raise ValueError("each meal must be an object")
            ingredients = meal.get("ingredients")
            if not isinstance(ingredients, list) or not ingredients:
                raise ValueError("each meal must contain ingredients")
            for ingredient in ingredients:
                if not isinstance(ingredient, dict) or not _ingredient_name(ingredient):
                    raise ValueError("each ingredient must contain a non-empty name")

    return deepcopy(dict(week_plan))


def _week_menu_from_wire(
    week_plan: dict[str, object],
    nutrition_targets: NutritionTargets,
) -> WeekMenu:
    """Adapt validated wire evidence into the existing canonical menu classes."""
    days = cast(list[dict[str, object]], week_plan["days"])
    daily_menus: List[DayMenu] = []
    for day in days:
        raw_date = day.get("date", day.get("day", day.get("name", "")))
        date = raw_date if isinstance(raw_date, str) else ""
        meals = cast(List[Dict[str, Any]], deepcopy(day["meals"]))
        day_menu = DayMenu(
            date=date,
            meals=meals,
            total_nutrients={},
            targets=nutrition_targets,
            coverage={},
            recommendations=[],
            estimated_cost=0.0,
        )
        day_menu.total_nutrients = _calculate_day_nutrients(day_menu)
        daily_menus.append(day_menu)

    raw_week_start = week_plan.get("week_start", "")
    week_start = raw_week_start if isinstance(raw_week_start, str) else ""
    return WeekMenu(
        week_start=week_start,
        daily_menus=daily_menus,
        weekly_coverage={},
        shopping_list={},
        total_cost=0.0,
        adherence_score=0.0,
    )


def _week_menu_to_wire(
    plan: WeekMenu,
    original_wire_plan: Dict,
) -> dict[str, object]:
    """Project canonical changes onto a deep-copied wire template, preserving metadata."""
    repaired_wire_plan = deepcopy(original_wire_plan)
    original_days = repaired_wire_plan.get("days")
    day_templates = original_days if isinstance(original_days, list) else []
    repaired_days: list[dict[str, object]] = []
    for index, day in enumerate(plan.daily_menus):
        template = day_templates[index] if index < len(day_templates) else {}
        repaired_day = deepcopy(template) if isinstance(template, dict) else {}
        if "date" in repaired_day:
            repaired_day["date"] = day.date
        elif "day" in repaired_day:
            repaired_day["day"] = day.date
        elif "name" in repaired_day:
            repaired_day["name"] = day.date
        else:
            repaired_day["day"] = day.date
        repaired_day["meals"] = deepcopy(day.meals)
        repaired_day["total_nutrients"] = deepcopy(day.total_nutrients)
        for stale_field in ("coverage", "recommendations", "estimated_cost"):
            repaired_day.pop(stale_field, None)
        repaired_days.append(repaired_day)

    repaired_wire_plan["week_start"] = plan.week_start
    repaired_wire_plan["days"] = repaired_days
    for stale_field in (
        "weekly_coverage",
        "shopping_list",
        "total_cost",
        "adherence_score",
    ):
        repaired_wire_plan.pop(stale_field, None)
    return repaired_wire_plan


def _known_nutrient_contributions(before: WeekMenu, after: WeekMenu) -> Dict[str, float]:
    """Report positive deltas only for nutrient keys explicitly present before repair."""
    contributions: Dict[str, float] = {}
    for before_day, after_day in zip(before.daily_menus, after.daily_menus):
        for before_meal, after_meal in zip(before_day.meals, after_day.meals):
            before_nutrients = before_meal.get("nutrients")
            after_nutrients = after_meal.get("nutrients")
            if not isinstance(before_nutrients, dict) or not isinstance(after_nutrients, dict):
                continue
            for nutrient, raw_before in before_nutrients.items():
                raw_after = after_nutrients.get(nutrient)
                if (
                    isinstance(raw_before, bool)
                    or not isinstance(raw_before, Real)
                    or isinstance(raw_after, bool)
                    or not isinstance(raw_after, Real)
                ):
                    continue
                delta = float(raw_after) - float(raw_before)
                if math.isfinite(delta) and delta > 0:
                    contributions[nutrient] = contributions.get(nutrient, 0.0) + delta
    return contributions


def _changes_from_history(history: List["RepairIteration"]) -> List[Dict]:
    """Collect response changes from one invocation-local completed history."""
    return [change for repair_iteration in history for change in repair_iteration.changes_applied]


@dataclass
class RepairResult:
    """Результат ремонта"""

    status: RepairStatus
    repaired_plan: Dict
    original_plan: Dict
    changes_made: List[Dict]
    remaining_gaps: Dict[str, float]
    strategy_used: RepairStrategy
    iterations: int
    message: str
    suggestions: List[str]


@dataclass
class RepairIteration:
    """Итерация ремонта"""

    iteration_number: int
    strategy: RepairStrategy
    gaps_before: Dict[str, float]
    gaps_after: Dict[str, float]
    changes_applied: List[Dict]
    success: bool


class AutoRepairEngine:
    """Движок авто-ремонта с UX-петлей"""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.repair_history: List[RepairIteration] = []

    def auto_repair_week_plan(
        self,
        week_plan: Dict,
        targets: MicronutrientTargets,
        initial_strategy: RepairStrategy = RepairStrategy.BALANCED,
        user_preferences: Optional[Dict] = None,
        nutrition_targets: Optional[NutritionTargets] = None,
    ) -> RepairResult:
        """
        Авто-ремонт недельного плана с UX-петлей

        Args:
            week_plan: Недельный план питания
            targets: Цели по микронутриентам
            initial_strategy: Начальная стратегия ремонта
            user_preferences: Предпочтения пользователя

        Returns:
            Результат ремонта с историей итераций
        """
        if not isinstance(initial_strategy, RepairStrategy):
            raise ValueError("Unknown repair strategy")

        validated_plan = validate_week_plan(week_plan)
        original_plan = deepcopy(validated_plan)
        if nutrition_targets is None:
            raise ValueError("Explicit nutrition targets are required")

        canonical_initial_plan = _week_menu_from_wire(validated_plan, nutrition_targets)
        if has_complete_nutrition_evidence(canonical_initial_plan, targets):
            self._store_completed_history([])
            return RepairResult(
                status=RepairStatus.SUCCESS,
                repaired_plan=deepcopy(validated_plan),
                original_plan=original_plan,
                changes_made=[],
                remaining_gaps={},
                strategy_used=initial_strategy,
                iterations=0,
                message="Plan already satisfies all explicit targets",
                suggestions=[],
            )

        if user_preferences:
            self._store_completed_history([])
            return RepairResult(
                status=RepairStatus.NEEDS_MANUAL,
                repaired_plan=deepcopy(validated_plan),
                original_plan=original_plan,
                changes_made=[],
                remaining_gaps={},
                strategy_used=initial_strategy,
                iterations=0,
                message="Canonical auto-repair does not support these preferences",
                suggestions=[],
            )

        if self.max_iterations <= 0:
            self._store_completed_history([])
            return RepairResult(
                status=RepairStatus.FAILED,
                repaired_plan=deepcopy(validated_plan),
                original_plan=original_plan,
                changes_made=[],
                remaining_gaps={},
                strategy_used=initial_strategy,
                iterations=0,
                message="Auto-repair did not execute",
                suggestions=[],
            )

        invocation_history: List[RepairIteration] = []
        current_plan = deepcopy(validated_plan)
        current_strategy = initial_strategy
        for iteration in range(1, self.max_iterations + 1):
            repair_iteration = self._attempt_repair(
                current_plan,
                targets,
                current_strategy,
                iteration,
                nutrition_targets,
            )
            invocation_history.append(repair_iteration)
            if repair_iteration.success:
                material_change = repair_iteration.changes_applied[0]
                repaired_plan = material_change.get(
                    "repaired_plan",
                    current_plan,
                )
                remaining_gaps = material_change.get("remaining_gaps", {})
                self._store_completed_history(invocation_history)
                return RepairResult(
                    status=RepairStatus.PARTIAL,
                    repaired_plan=repaired_plan,
                    original_plan=original_plan,
                    changes_made=_changes_from_history(invocation_history),
                    remaining_gaps=cast(Dict[str, float], remaining_gaps),
                    strategy_used=current_strategy,
                    iterations=iteration,
                    message=(
                        "Canonical repair produced a changed plan; nutritional completeness "
                        "is not asserted"
                    ),
                    suggestions=[],
                )
            current_strategy = self._get_next_strategy(current_strategy)

        self._store_completed_history(invocation_history)
        return RepairResult(
            status=RepairStatus.FAILED,
            repaired_plan=current_plan,
            original_plan=original_plan,
            changes_made=[],
            remaining_gaps={},
            strategy_used=invocation_history[-1].strategy,
            iterations=self.max_iterations,
            message="Canonical repair made no changes",
            suggestions=self._generate_manual_suggestions({}),
        )

    def _analyze_nutrient_gaps(
        self, week_plan: Dict, targets: MicronutrientTargets
    ) -> Dict[str, float]:
        """Анализирует дефициты микронутриентов"""
        # Упрощенная логика анализа дефицитов
        # В реальном приложении здесь был бы полный анализ плана

        validated_plan = validate_week_plan(week_plan)
        gaps = {}

        # Примерные дефициты для демонстрации
        days = cast(list[dict[str, object]], validated_plan["days"])
        for day in days:
            meals = cast(list[dict[str, object]], day["meals"])
            for meal in meals:
                ingredients = cast(list[dict[str, object]], meal["ingredients"])

                vegetables_count = sum(
                    1 for ingredient in ingredients if _is_vegetable(_ingredient_name(ingredient))
                )
                if vegetables_count < 2:
                    gaps["vitamin_c"] = 50.0
                    gaps["folate"] = 30.0

                protein_count = sum(
                    1 for ingredient in ingredients if _is_protein(_ingredient_name(ingredient))
                )
                if protein_count == 0:
                    gaps["iron"] = 40.0
                    gaps["protein"] = 20.0

        _ = targets
        return gaps

    def _attempt_repair(
        self,
        week_plan: Dict,
        targets: MicronutrientTargets,
        strategy: RepairStrategy,
        iteration: int,
        nutrition_targets: NutritionTargets,
    ) -> RepairIteration:
        """Delegate one adapted plan to the canonical menu-engine repair function."""
        try:
            canonical_strategy = _CANONICAL_STRATEGY_BY_REPAIR_STRATEGY[strategy]
        except KeyError as exc:
            raise ValueError("Unknown repair strategy") from exc
        canonical_plan = _week_menu_from_wire(
            validate_week_plan(week_plan),
            nutrition_targets,
        )
        repaired_canonical_plan = repair_week_plan(canonical_plan, targets, canonical_strategy)
        if not isinstance(repaired_canonical_plan, WeekMenu):
            raise TypeError("Canonical repair returned an invalid result")

        changed = repaired_canonical_plan != canonical_plan
        repaired_plan = (
            _week_menu_to_wire(repaired_canonical_plan, week_plan)
            if changed
            else deepcopy(week_plan)
        )

        changes: List[Dict] = []
        if changed:
            changes.append(
                {
                    "type": "canonical_repair",
                    "strategy": strategy.value,
                    "iteration": iteration,
                    "repaired_plan": repaired_plan,
                    "remaining_gaps": calculate_known_nutrient_gaps(
                        repaired_canonical_plan,
                        targets,
                    ),
                    "nutrient_contributions": _known_nutrient_contributions(
                        canonical_plan,
                        repaired_canonical_plan,
                    ),
                }
            )

        return RepairIteration(
            iteration_number=iteration,
            strategy=strategy,
            gaps_before={},
            gaps_after={},
            changes_applied=changes,
            success=changed,
        )

    def _get_next_strategy(self, current_strategy: RepairStrategy) -> RepairStrategy:
        """Получает следующую стратегию ремонта"""
        if current_strategy == RepairStrategy.CONSERVATIVE:
            return RepairStrategy.BALANCED
        elif current_strategy == RepairStrategy.BALANCED:
            return RepairStrategy.AGGRESSIVE
        else:  # AGGRESSIVE
            return RepairStrategy.CONSERVATIVE

    def _get_all_changes(self) -> List[Dict]:
        """Получает все изменения из истории ремонта"""
        all_changes = []
        for iteration in self.repair_history:
            all_changes.extend(iteration.changes_applied)
        return all_changes

    def _store_completed_history(self, history: List[RepairIteration]) -> None:
        """Publish a completed diagnostic snapshot without using it for this response."""
        self.repair_history = deepcopy(history)

    def _generate_success_suggestions(self) -> List[str]:
        """Генерирует предложения при успешном ремонте"""
        return [
            "План успешно оптимизирован!",
            "Рекомендуется сохранить изменения",
            "Можно экспортировать обновленный план",
            "Проверьте список покупок для новых ингредиентов",
        ]

    def _generate_manual_suggestions(self, remaining_gaps: Dict[str, float]) -> List[str]:
        """Генерирует предложения для ручного ремонта"""
        suggestions = [
            "Автоматический ремонт не смог устранить все дефициты",
            "Рекомендуется ручная корректировка плана",
        ]

        if "iron" in remaining_gaps:
            suggestions.append("Добавьте больше мяса, рыбы или бобовых для железа")

        if "vitamin_c" in remaining_gaps:
            suggestions.append("Увеличьте количество овощей и фруктов для витамина C")

        if "folate" in remaining_gaps:
            suggestions.append("Добавьте листовые овощи для фолиевой кислоты")

        if "protein" in remaining_gaps:
            suggestions.append("Увеличьте порции белковых продуктов")

        return suggestions

    def get_repair_history(self) -> List[RepairIteration]:
        """Возвращает историю ремонта"""
        return self.repair_history

    def suggest_manual_fixes(self, week_plan: Dict, targets: MicronutrientTargets) -> List[Dict]:
        """Предлагает ручные исправления для плана"""
        try:
            gaps = self._analyze_nutrient_gaps(week_plan, targets)
        except ValueError:
            return []
        suggestions = []

        for nutrient, deficit in gaps.items():
            if nutrient == "iron":
                suggestions.append(
                    {
                        "type": "add_ingredient",
                        "nutrient": nutrient,
                        "suggestions": [
                            {"name": "beef", "amount": 150, "unit": "g"},
                            {"name": "salmon", "amount": 200, "unit": "g"},
                            {"name": "lentils", "amount": 100, "unit": "g"},
                        ],
                        "reason": f"Дефицит {nutrient}: {deficit}%",
                    }
                )
            elif nutrient == "vitamin_c":
                suggestions.append(
                    {
                        "type": "add_ingredient",
                        "nutrient": nutrient,
                        "suggestions": [
                            {"name": "bell peppers", "amount": 100, "unit": "g"},
                            {"name": "broccoli", "amount": 150, "unit": "g"},
                            {"name": "oranges", "amount": 200, "unit": "g"},
                        ],
                        "reason": f"Дефицит {nutrient}: {deficit}%",
                    }
                )
            elif nutrient == "folate":
                suggestions.append(
                    {
                        "type": "add_ingredient",
                        "nutrient": nutrient,
                        "suggestions": [
                            {"name": "spinach", "amount": 100, "unit": "g"},
                            {"name": "asparagus", "amount": 150, "unit": "g"},
                            {"name": "avocado", "amount": 100, "unit": "g"},
                        ],
                        "reason": f"Дефицит {nutrient}: {deficit}%",
                    }
                )

        return suggestions


# Глобальный экземпляр движка ремонта
_auto_repair_engine = None


def get_auto_repair_engine() -> AutoRepairEngine:
    """Получает глобальный экземпляр движка авто-ремонта"""
    global _auto_repair_engine
    if _auto_repair_engine is None:
        _auto_repair_engine = AutoRepairEngine()
    return _auto_repair_engine


# Удобные функции для быстрого доступа
def auto_repair_week_plan(
    week_plan: Dict,
    targets: MicronutrientTargets,
    strategy: RepairStrategy = RepairStrategy.BALANCED,
    user_preferences: Optional[Dict] = None,
    nutrition_targets: Optional[NutritionTargets] = None,
) -> RepairResult:
    """Авто-ремонт недельного плана"""
    engine = get_auto_repair_engine()
    return engine.auto_repair_week_plan(
        week_plan,
        targets,
        strategy,
        user_preferences,
        nutrition_targets,
    )


def suggest_manual_fixes(week_plan: Dict, targets: MicronutrientTargets) -> List[Dict]:
    """Предлагает ручные исправления"""
    engine = get_auto_repair_engine()
    return engine.suggest_manual_fixes(week_plan, targets)


# =============================================================================
# Planner Engine Facade Functions
# =============================================================================
# These functions provide a simplified API for tests and external callers.


def analyze_deficiencies(
    current_nutrition: Dict[str, Any], target_nutrition: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze nutrient deficiencies between current and target values.

    RU: Анализ дефицитов нутриентов.
    EN: Analyze nutrient deficiencies.

    Args:
        current_nutrition: Dict with current nutrient values
        target_nutrition: Dict with target nutrient values

    Returns:
        Dict mapping nutrient names to deficiency info
    """
    deficiencies: Dict[str, Any] = {}

    for nutrient, target_val in target_nutrition.items():
        if not isinstance(target_val, (int, float)):
            continue

        current_val = current_nutrition.get(nutrient, 0)
        if not isinstance(current_val, (int, float)):
            current_val = 0

        if current_val < target_val:
            deficiencies[nutrient] = {
                "deficit": target_val - current_val,
                "current": current_val,
                "target": target_val,
                "percent_met": (current_val / target_val * 100) if target_val > 0 else 0,
            }

    return deficiencies


def get_repair_suggestions(deficiencies: Any, foods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get repair suggestions based on deficiencies and available foods.

    RU: Получение предложений по исправлению дефицитов.
    EN: Get repair suggestions for deficiencies.

    Args:
        deficiencies: Dict or list of deficiencies
        foods: List of available foods with nutrient info

    Returns:
        List of repair suggestions
    """
    suggestions: List[Dict[str, Any]] = []

    if not deficiencies or not foods:
        return suggestions

    # Convert deficiencies to dict if needed
    def_dict = deficiencies if isinstance(deficiencies, dict) else {}

    for nutrient, info in def_dict.items():
        if not isinstance(info, dict):
            continue

        deficit = info.get("deficit", 0)
        if deficit <= 0:
            continue

        # Find foods that can help with this deficiency
        for food in foods:
            food_nutrient = food.get(nutrient, 0)
            if isinstance(food_nutrient, (int, float)) and food_nutrient > 0:
                suggestions.append(
                    {
                        "nutrient": nutrient,
                        "food": food.get("name", "unknown"),
                        "amount": food_nutrient,
                        "deficit": deficit,
                    }
                )
                break  # One suggestion per nutrient

    return suggestions


def calculate_repair_priority(deficiency: Dict[str, Any], target: Dict[str, Any]) -> float:
    """
    Calculate priority score for a deficiency repair.

    RU: Расчёт приоритета исправления дефицита.
    EN: Calculate repair priority score.

    Args:
        deficiency: Dict with deficiency info (expects 'deficit' key or numeric value)
        target: Dict with target info (expects matching nutrient key or numeric value)

    Returns:
        Priority score (0-100, higher = more urgent)
    """
    # Handle various input formats
    if isinstance(deficiency, dict) and isinstance(target, dict):
        # Extract values from dicts
        deficit_val = deficiency.get("deficit", 0)
        if isinstance(deficit_val, dict):
            deficit_val = deficit_val.get("deficit", 0)

        # Get first numeric target value
        target_val: float = 0.0
        for v in target.values():
            if isinstance(v, (int, float)):
                target_val = float(v)
                break
    else:
        # Assume numeric inputs
        deficit_val = deficiency if isinstance(deficiency, (int, float)) else 0
        target_val = float(target) if isinstance(target, (int, float)) else 0.0

    if not isinstance(deficit_val, (int, float)) or target_val <= 0:
        return 0.0

    # Calculate percentage deficit
    priority = min(100.0, (deficit_val / target_val) * 100)
    return priority


def find_suitable_foods(*args: Any, **kwargs: Any) -> Optional[List[Dict[str, Any]]]:
    """
    Find foods suitable for repairing deficiencies.

    RU: Заглушка - поиск подходящих продуктов.
    EN: Stub - find suitable foods.

    Note:
        Not yet implemented. See BACKLOG_LEDGER.md for status.
    """
    return None


def optimize_meal_plan(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Optimize a meal plan to meet targets.

    RU: Заглушка - оптимизация плана питания.
    EN: Stub - optimize meal plan.

    Note:
        Not yet implemented. See BACKLOG_LEDGER.md for status.
    """
    return None

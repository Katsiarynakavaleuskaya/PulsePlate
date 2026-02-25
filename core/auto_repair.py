# -*- coding: utf-8 -*-
"""
RU: Модуль для авто-ремонта недельных планов с UX-петлей.
EN: Module for auto-repair of weekly meal plans with UX loop.

Sprint 5: Auto-repair недели (UX-петля)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from core.menu_engine import repair_week_plan
from core.targets import MicronutrientTargets


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
        self.repair_history = []
        original_plan = week_plan.copy()

        # Анализируем начальные дефициты
        initial_gaps = self._analyze_nutrient_gaps(week_plan, targets)

        if not initial_gaps:
            return RepairResult(
                status=RepairStatus.SUCCESS,
                repaired_plan=week_plan,
                original_plan=original_plan,
                changes_made=[],
                remaining_gaps={},
                strategy_used=initial_strategy,
                iterations=0,
                message="План уже соответствует целям",
                suggestions=[],
            )

        # Начинаем итеративный процесс ремонта
        current_plan = week_plan.copy()
        current_strategy = initial_strategy
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            # Анализируем текущие дефициты
            current_gaps = self._analyze_nutrient_gaps(current_plan, targets)

            if not current_gaps:
                # Успех! Все дефициты устранены
                return RepairResult(
                    status=RepairStatus.SUCCESS,
                    repaired_plan=current_plan,
                    original_plan=original_plan,
                    changes_made=self._get_all_changes(),
                    remaining_gaps={},
                    strategy_used=current_strategy,
                    iterations=iteration,
                    message=f"План успешно отремонтирован за {iteration} итераций",
                    suggestions=self._generate_success_suggestions(),
                )

            # Пытаемся отремонтировать с текущей стратегией
            repair_iteration = self._attempt_repair(
                current_plan, targets, current_strategy, iteration
            )

            self.repair_history.append(repair_iteration)

            if repair_iteration.success:
                current_plan = repair_iteration.changes_applied[0].get(
                    "repaired_plan", current_plan
                )

                # Проверяем, нужно ли изменить стратегию
                new_gaps = self._analyze_nutrient_gaps(current_plan, targets)
                if len(new_gaps) < len(current_gaps):
                    # Прогресс есть, продолжаем с той же стратегией
                    continue
                else:
                    # Прогресса нет, меняем стратегию
                    current_strategy = self._get_next_strategy(current_strategy)
            else:
                # Ремонт не удался, пробуем другую стратегию
                current_strategy = self._get_next_strategy(current_strategy)

        # Достигли максимального количества итераций
        final_gaps = self._analyze_nutrient_gaps(current_plan, targets)

        if len(final_gaps) < len(initial_gaps):
            status = RepairStatus.PARTIAL
            fixed = len(initial_gaps) - len(final_gaps)
            total = len(initial_gaps)
            message = f"Частичный ремонт: устранено {fixed} из {total} дефицитов"
        else:
            status = RepairStatus.FAILED
            message = "Не удалось устранить дефициты автоматически"

        return RepairResult(
            status=status,
            repaired_plan=current_plan,
            original_plan=original_plan,
            changes_made=self._get_all_changes(),
            remaining_gaps=final_gaps,
            strategy_used=current_strategy,
            iterations=iteration,
            message=message,
            suggestions=self._generate_manual_suggestions(final_gaps),
        )

    def _analyze_nutrient_gaps(
        self, week_plan: Dict, targets: MicronutrientTargets
    ) -> Dict[str, float]:
        """Анализирует дефициты микронутриентов"""
        # Упрощенная логика анализа дефицитов
        # В реальном приложении здесь был бы полный анализ плана

        gaps = {}

        # Примерные дефициты для демонстрации
        if "days" in week_plan:
            # Анализируем каждый день
            for day in week_plan["days"]:
                if "meals" in day:
                    for meal in day["meals"]:
                        # Простая логика: если мало овощей, то дефицит витаминов
                        if "ingredients" in meal:
                            vegetables_count = sum(
                                1
                                for ing in meal["ingredients"]
                                if "vegetable" in ing.get("name", "").lower()
                            )
                            if vegetables_count < 2:
                                gaps["vitamin_c"] = 50.0
                                gaps["folate"] = 30.0

                        # Если мало мяса/рыбы, то дефицит белка и железа
                        protein_count = sum(
                            1
                            for ing in meal["ingredients"]
                            if any(
                                word in ing.get("name", "").lower()
                                for word in ["meat", "chicken", "fish", "beef"]
                            )
                        )
                        if protein_count == 0:
                            gaps["iron"] = 40.0
                            gaps["protein"] = 20.0

        return gaps

    def _attempt_repair(
        self,
        week_plan: Dict,
        targets: MicronutrientTargets,
        strategy: RepairStrategy,
        iteration: int,
    ) -> RepairIteration:
        """Пытается отремонтировать план с заданной стратегией"""
        gaps_before = self._analyze_nutrient_gaps(week_plan, targets)

        try:
            # Используем существующую функцию ремонта
            repaired_plan = repair_week_plan(week_plan, targets, strategy.value)  # type: ignore

            gaps_after = self._analyze_nutrient_gaps(repaired_plan, targets)  # type: ignore

            changes = [
                {
                    "type": "repair",
                    "strategy": strategy.value,
                    "iteration": iteration,
                    "repaired_plan": repaired_plan,
                    "gaps_before": gaps_before,
                    "gaps_after": gaps_after,
                }
            ]

            success = len(gaps_after) < len(gaps_before)

            return RepairIteration(
                iteration_number=iteration,
                strategy=strategy,
                gaps_before=gaps_before,
                gaps_after=gaps_after,
                changes_applied=changes,
                success=success,
            )

        except Exception:
            # Если ремонт не удался
            return RepairIteration(
                iteration_number=iteration,
                strategy=strategy,
                gaps_before=gaps_before,
                gaps_after=gaps_before,  # Дефициты не изменились
                changes_applied=[],
                success=False,
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
        gaps = self._analyze_nutrient_gaps(week_plan, targets)
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
) -> RepairResult:
    """Авто-ремонт недельного плана"""
    engine = get_auto_repair_engine()
    return engine.auto_repair_week_plan(week_plan, targets, strategy, user_preferences)


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

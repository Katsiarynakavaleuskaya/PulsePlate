#!/usr/bin/env python3
"""
Байесовский анализатор для бизнес-логики питания и здоровья.
Анализирует тесты с точки зрения безопасности данных, корректности расчетов питания,
и соответствия медицинским стандартам.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class NutritionCategory(Enum):
    """Категории проблем в области питания."""

    CALORIE_CALCULATION = "calorie_calculation"
    NUTRIENT_ACCURACY = "nutrient_accuracy"
    BMI_SAFETY = "bmi_safety"
    DIETARY_RESTRICTIONS = "dietary_restrictions"
    ALLERGEN_SAFETY = "allergen_safety"
    MEDICAL_SAFETY = "medical_safety"
    DATA_PRIVACY = "data_privacy"
    NUTRITION_STANDARDS = "nutrition_standards"
    PORTION_CONTROL = "portion_control"
    MEAL_PLANNING = "meal_planning"
    MACRONUTRIENT_BALANCE = "macronutrient_balance"


class NutritionErrorType(Enum):
    """Типы ошибок в области питания."""

    CALORIE_OVERFLOW = "calorie_overflow"
    NUTRIENT_DEFICIENCY = "nutrient_deficiency"
    BMI_DANGEROUS = "bmi_dangerous"
    ALLERGEN_MISSING = "allergen_missing"
    MEDICAL_CONTRADICTION = "medical_contradiction"
    PRIVACY_LEAK = "privacy_leak"
    STANDARD_VIOLATION = "standard_violation"
    PORTION_UNREALISTIC = "portion_unrealistic"
    MEAL_UNBALANCED = "meal_unbalanced"
    CALCULATION_ERROR = "calculation_error"
    PROTEIN_TOO_LOW = "protein_too_low"
    PROTEIN_TOO_HIGH = "protein_too_high"
    FAT_TOO_LOW = "fat_too_low"
    FAT_TOO_HIGH = "fat_too_high"
    CARB_TOO_LOW = "carb_too_low"
    CARB_TOO_HIGH = "carb_too_high"


@dataclass
class NutritionTestResult:
    """Результат теста с точки зрения питания."""

    test_name: str
    success: bool
    nutrition_category: NutritionCategory
    error_type: Optional[NutritionErrorType] = None
    error_message: str = ""
    execution_time: float = 0.0
    file_path: str = ""
    business_impact: str = ""  # Описание влияния на бизнес
    safety_level: str = "safe"  # safe, warning, dangerous
    data_sensitivity: str = "low"  # low, medium, high


class NutritionBayesianAnalyzer:
    """Байесовский анализатор для питания и здоровья."""

    def __init__(self) -> None:
        self.test_results: List[NutritionTestResult] = []
        self.nutrition_knowledge_base = self._load_nutrition_knowledge()
        self.safety_thresholds = self._load_safety_thresholds()
        # Counters for per-analysis outcomes
        self._total_analyses: int = 0
        self._failed_analyses: int = 0

    def _load_nutrition_knowledge(self) -> Dict[str, Any]:
        """Загружает базу знаний о питании."""
        return {
            "bmi_ranges": {
                "underweight": (0, 18.5),
                "normal": (18.5, 25),
                "overweight": (25, 30),
                "obese": (30, 100),
            },
            "calorie_limits": {
                "min_daily": 1200,  # Updated to match calorie_dangerous_low
                "max_daily": 5000,
                "min_meal": 100,
                "max_meal": 2000,
            },
            "nutrient_limits": {
                "protein_min_percent": 10,
                "protein_max_percent": 35,
                "fat_min_percent": 15,
                "fat_max_percent": 35,
                "carbs_min_percent": 45,
                "carbs_max_percent": 65,
            },
            "allergens": ["gluten", "dairy", "nuts", "eggs", "soy", "fish", "shellfish"],
            "medical_conditions": [
                "diabetes",
                "hypertension",
                "heart_disease",
                "celiac",
                "lactose_intolerance",
            ],
        }

    def _load_safety_thresholds(self) -> Dict[str, float]:
        """Загружает пороговые значения безопасности."""
        return {
            "bmi_dangerous_low": 16.0,
            "bmi_dangerous_high": 30.0,
            "calorie_dangerous_low": 1200,
            "calorie_dangerous_high": 6000,
            "nutrient_imbalance_threshold": 0.3,
            "allergen_risk_threshold": 0.8,
        }

    def add_nutrition_test_result(self, result: NutritionTestResult) -> None:
        """Добавляет результат теста с точки зрения питания."""
        self.test_results.append(result)

    def analyze_nutrition_safety(self, test_code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует код теста на предмет безопасности питания."""
        results = []

        # Анализ расчетов калорий
        calorie_issues = self._analyze_calorie_calculations(test_code, test_name)
        results.extend(calorie_issues)

        # Анализ BMI расчетов
        bmi_issues = self._analyze_bmi_calculations(test_code, test_name)
        results.extend(bmi_issues)

        # Анализ аллергенов
        allergen_issues = self._analyze_allergen_safety(test_code, test_name)
        results.extend(allergen_issues)

        # Анализ медицинских ограничений
        medical_issues = self._analyze_medical_safety(test_code, test_name)
        results.extend(medical_issues)

        # Анализ приватности данных
        privacy_issues = self._analyze_data_privacy(test_code, test_name)
        results.extend(privacy_issues)

        # Анализ стандартов питания
        standards_issues = self._analyze_nutrition_standards(test_code, test_name)
        results.extend(standards_issues)

        # Persist results for downstream diagnostics
        self.test_results.extend(results)
        # Update per-analysis counters
        self._total_analyses += 1
        if any(not r.success for r in results):
            self._failed_analyses += 1
        return results

    def _analyze_calorie_calculations(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует корректность расчетов калорий."""
        results = []

        # Поиск расчетов калорий
        calorie_patterns = [
            r"calories?\s*[=:]\s*(\d+)",
            r"kcal\s*[=:]\s*(\d+)",
            r"energy\s*[=:]\s*(\d+)",
        ]

        for pattern in calorie_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                try:
                    calories = int(match.group(1))

                    # Проверка на опасные значения
                    if calories < self.safety_thresholds["calorie_dangerous_low"]:
                        results.append(
                            NutritionTestResult(
                                test_name=test_name,
                                success=False,
                                nutrition_category=NutritionCategory.CALORIE_CALCULATION,
                                error_type=NutritionErrorType.CALORIE_OVERFLOW,
                                error_message=f"Опасно низкое количество калорий: {calories}",
                                business_impact="Риск недоедания и нарушения метаболизма",
                                safety_level="dangerous",
                            )
                        )
                    elif calories > self.safety_thresholds["calorie_dangerous_high"]:
                        results.append(
                            NutritionTestResult(
                                test_name=test_name,
                                success=False,
                                nutrition_category=NutritionCategory.CALORIE_CALCULATION,
                                error_type=NutritionErrorType.CALORIE_OVERFLOW,
                                error_message=f"Опасно высокое количество калорий: {calories}",
                                business_impact="Риск переедания и ожирения",
                                safety_level="dangerous",
                            )
                        )
                except ValueError:
                    continue

        return results

    def _analyze_bmi_calculations(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует корректность расчетов BMI."""
        results = []

        # Поиск BMI расчетов
        bmi_patterns = [r"bmi\s*[=:]\s*([\d.]+)", r"body_mass_index\s*[=:]\s*([\d.]+)"]

        for pattern in bmi_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                try:
                    bmi = float(match.group(1))

                    # Проверка на опасные значения BMI
                    if bmi < self.safety_thresholds["bmi_dangerous_low"]:
                        results.append(
                            NutritionTestResult(
                                test_name=test_name,
                                success=False,
                                nutrition_category=NutritionCategory.BMI_SAFETY,
                                error_type=NutritionErrorType.BMI_DANGEROUS,
                                error_message=f"Опасно низкий BMI: {bmi}",
                                business_impact="Риск анорексии и недоедания",
                                safety_level="dangerous",
                            )
                        )
                    elif bmi > self.safety_thresholds["bmi_dangerous_high"]:
                        results.append(
                            NutritionTestResult(
                                test_name=test_name,
                                success=False,
                                nutrition_category=NutritionCategory.BMI_SAFETY,
                                error_type=NutritionErrorType.BMI_DANGEROUS,
                                error_message=f"Опасно высокий BMI: {bmi}",
                                business_impact="Риск ожирения и сопутствующих заболеваний",
                                safety_level="dangerous",
                            )
                        )
                except ValueError:
                    continue

        return results

    def _analyze_allergen_safety(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует безопасность аллергенов."""
        results = []

        # Поиск упоминаний аллергенов
        allergen_mentions = []
        for allergen in self.nutrition_knowledge_base["allergens"]:
            if allergen.lower() in code.lower():
                allergen_mentions.append(allergen)

        # Проверка на отсутствие проверок аллергенов
        if allergen_mentions and not any(
            keyword in code.lower() for keyword in ["allergen", "allergy", "check", "safe"]
        ):
            results.append(
                NutritionTestResult(
                    test_name=test_name,
                    success=False,
                    nutrition_category=NutritionCategory.ALLERGEN_SAFETY,
                    error_type=NutritionErrorType.ALLERGEN_MISSING,
                    error_message=f"Обнаружены аллергены без проверки: {', '.join(allergen_mentions)}",
                    business_impact="Риск аллергических реакций у пользователей",
                    safety_level="warning",
                )
            )

        return results

    def _analyze_medical_safety(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует медицинскую безопасность."""
        results = []

        # Поиск медицинских условий
        medical_mentions = []
        for condition in self.nutrition_knowledge_base["medical_conditions"]:
            if condition.lower() in code.lower():
                medical_mentions.append(condition)

        # Проверка на противоречия в медицинских рекомендациях
        if medical_mentions:
            # Проверка на диабет и высокое содержание сахара
            if (
                "diabetes" in medical_mentions
                and "sugar" in code.lower()
                and "limit" not in code.lower()
            ):
                results.append(
                    NutritionTestResult(
                        test_name=test_name,
                        success=False,
                        nutrition_category=NutritionCategory.MEDICAL_SAFETY,
                        error_type=NutritionErrorType.MEDICAL_CONTRADICTION,
                        error_message="Диабет обнаружен, но нет ограничений на сахар",
                        business_impact="Риск ухудшения состояния диабетиков",
                        safety_level="warning",
                    )
                )

        return results

    def _analyze_data_privacy(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует приватность данных."""
        results = []

        # Поиск чувствительных данных
        sensitive_patterns = [
            r'password\s*[=:]\s*["\'][^"\']+["\']',
            r'api_key\s*[=:]\s*["\'][^"\']+["\']',
            r'token\s*[=:]\s*["\'][^"\']+["\']',
            r'secret\s*[=:]\s*["\'][^"\']+["\']',
        ]

        for pattern in sensitive_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                results.append(
                    NutritionTestResult(
                        test_name=test_name,
                        success=False,
                        nutrition_category=NutritionCategory.DATA_PRIVACY,
                        error_type=NutritionErrorType.PRIVACY_LEAK,
                        error_message="Обнаружены чувствительные данные в коде",
                        business_impact="Риск утечки конфиденциальной информации",
                        safety_level="dangerous",
                        data_sensitivity="high",
                    )
                )

        return results

    def _analyze_nutrition_standards(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует соответствие стандартам питания."""
        results = []

        # Поиск макронутриентов
        macro_patterns = {
            "protein": r"protein\s*[=:]\s*(\d+)",
            "fat": r"fat\s*[=:]\s*(\d+)",
            "carbs": r"carbs?\s*[=:]\s*(\d+)",
        }

        macro_values = {}
        for macro, pattern in macro_patterns.items():
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                macro_values[macro] = int(match.group(1))

        # Проверка баланса макронутриентов
        if len(macro_values) >= 2:
            total = sum(macro_values.values())
            if total > 0:
                protein_pct = macro_values.get("protein", 0) / total
                fat_pct = macro_values.get("fat", 0) / total
                carb_pct = macro_values.get("carbs", 0) / total

                limits = self.nutrition_knowledge_base["nutrient_limits"]

                # Protein checks
                if protein_pct < limits["protein_min_percent"] / 100:
                    results.append(
                        NutritionTestResult(
                            test_name=test_name,
                            success=False,
                            nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                            error_type=NutritionErrorType.PROTEIN_TOO_LOW,
                            error_message=f"Слишком низкий процент белка: {protein_pct:.2%}",
                            business_impact="Риск недостатка белка",
                            safety_level="dangerous",
                        )
                    )
                if protein_pct > limits["protein_max_percent"] / 100:
                    results.append(
                        NutritionTestResult(
                            test_name=test_name,
                            success=False,
                            nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                            error_type=NutritionErrorType.PROTEIN_TOO_HIGH,
                            error_message=f"Слишком высокий процент белка: {protein_pct:.2%}",
                            business_impact="Риск перегрузки белком",
                            safety_level="dangerous",
                        )
                    )

                # Fat checks
                if fat_pct < limits["fat_min_percent"] / 100:
                    results.append(
                        NutritionTestResult(
                            test_name=test_name,
                            success=False,
                            nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                            error_type=NutritionErrorType.FAT_TOO_LOW,
                            error_message=f"Слишком низкий процент жиров: {fat_pct:.2%}",
                            business_impact="Риск недостатка жиров",
                            safety_level="dangerous",
                        )
                    )
                if fat_pct > limits["fat_max_percent"] / 100:
                    results.append(
                        NutritionTestResult(
                            test_name=test_name,
                            success=False,
                            nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                            error_type=NutritionErrorType.FAT_TOO_HIGH,
                            error_message=f"Слишком высокий процент жиров: {fat_pct:.2%}",
                            business_impact="Риск перегрузки жирами",
                            safety_level="dangerous",
                        )
                    )

                # Carbohydrate checks
                if carb_pct < limits["carbs_min_percent"] / 100:
                    results.append(
                        NutritionTestResult(
                            test_name=test_name,
                            success=False,
                            nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                            error_type=NutritionErrorType.CARB_TOO_LOW,
                            error_message=f"Слишком низкий процент углеводов: {carb_pct:.2%}",
                            business_impact="Риск недостатка углеводов",
                            safety_level="dangerous",
                        )
                    )
                if carb_pct > limits["carbs_max_percent"] / 100:
                    results.append(
                        NutritionTestResult(
                            test_name=test_name,
                            success=False,
                            nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                            error_type=NutritionErrorType.CARB_TOO_HIGH,
                            error_message=f"Слишком высокий процент углеводов: {carb_pct:.2%}",
                            business_impact="Риск перегрузки углеводами",
                            safety_level="dangerous",
                        )
                    )

        return results

    def diagnose_nutrition_issues(self) -> Dict[NutritionCategory, float]:
        """Диагностирует проблемы в области питания."""
        if not self.test_results:
            return {}

        # Подсчитываем проблемы по категориям
        category_counts: Dict[NutritionCategory, int] = {}
        total_issues = 0

        for result in self.test_results:
            if not result.success:
                category = result.nutrition_category
                category_counts[category] = category_counts.get(category, 0) + 1
                total_issues += 1

        # Вычисляем вероятности
        probabilities: Dict[NutritionCategory, float] = {}
        for category, count in category_counts.items():
            probabilities[category] = count / total_issues if total_issues > 0 else 0.0

        return probabilities

    def generate_nutrition_recommendations(self) -> List[str]:
        """Генерирует рекомендации по улучшению питания и безопасности."""
        recommendations = []

        # Анализируем проблемы
        issues = self.diagnose_nutrition_issues()

        # Рекомендации по категориям
        if NutritionCategory.CALORIE_CALCULATION in issues:
            recommendations.append(
                "Добавить проверки на разумные пределы калорий (1200-6000 ккал/день)"
            )

        if NutritionCategory.BMI_SAFETY in issues:
            recommendations.append(
                "Добавить предупреждения для опасных значений BMI (<16 или >=30)"
            )

        if NutritionCategory.ALLERGEN_SAFETY in issues:
            recommendations.append(
                "Реализовать обязательные проверки аллергенов для всех продуктов"
            )

        if NutritionCategory.MEDICAL_SAFETY in issues:
            recommendations.append(
                "Добавить медицинские ограничения для пользователей с хроническими заболеваниями"
            )

        if NutritionCategory.DATA_PRIVACY in issues:
            recommendations.append("Удалить или зашифровать чувствительные данные в тестах")

        if NutritionCategory.NUTRITION_STANDARDS in issues:
            recommendations.append(
                "Проверять баланс макронутриентов согласно медицинским стандартам"
            )

        return recommendations

    def get_safety_score(self) -> float:
        """Вычисляет общий балл безопасности питания."""
        if self._total_analyses == 0:
            return 1.0

        base_score = (self._total_analyses - self._failed_analyses) / self._total_analyses

        # Smaller per-issue penalty to avoid over-penalizing when many findings are logged
        critical_penalty = sum(
            0.05
            for result in self.test_results
            if not result.success and result.safety_level == "dangerous"
        )

        return max(0.0, min(1.0, base_score - critical_penalty))

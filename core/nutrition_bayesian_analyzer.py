#!/usr/bin/env python3
"""
Байесовский анализатор для бизнес-логики питания и здоровья.
Анализирует тесты с точки зрения безопасности данных, корректности расчетов питания,
и соответствия медицинским стандартам.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from core.bmi.engine import _compute_bmi
from core.nutrition_constants import (
    BMI_DANGEROUS_LOW,
    BMI_OBESITY_THRESHOLD,
    CARBS_MAX_PERCENT,
    CARBS_MIN_PERCENT,
    FAT_MAX_PERCENT,
    FAT_MIN_PERCENT,
    KCAL_MAX_SAFE,
    KCAL_MIN_SAFE,
    PROTEIN_MAX_PERCENT,
    PROTEIN_MIN_PERCENT,
    is_meal_level_value,
)


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
    CALORIE_UNDERFLOW = "calorie_underflow"
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
    MACRONUTRIENT_SUM_INVALID = "macronutrient_sum_invalid"


# Type aliases for safety_level and data_sensitivity fields
SafetyLevel = Literal["safe", "warning", "dangerous"]
DataSensitivity = Literal["low", "medium", "high"]


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
    safety_level: SafetyLevel = "safe"  # safe, warning, dangerous
    data_sensitivity: DataSensitivity = "low"  # low, medium, high


class NutritionBayesianAnalyzer:
    """Байесовский анализатор для питания и здоровья."""

    # Safety score penalty constants
    # RU: Константы штрафов для балла безопасности
    # EN: Penalty values for safety score calculation
    DANGEROUS_PENALTY = 0.05  # Per-issue penalty for dangerous safety findings
    MAX_TOTAL_PENALTY = 0.5  # Maximum cumulative penalty to prevent over-penalization

    def __init__(self) -> None:
        self.test_results: List[NutritionTestResult] = []
        self.nutrition_knowledge_base = self._load_nutrition_knowledge()
        self.safety_thresholds = self._load_safety_thresholds()
        # Counters for per-analysis outcomes
        self._total_analyses: int = 0
        self._failed_analyses: int = 0

    def _is_in_test_or_mock_context(self, code: str, test_name: str = "") -> bool:
        """
        Lightweight test-context detector to avoid false positives in test/mock contexts.

        Checks for indicators like "def test_", "pytest", "unittest", "mock", "fixture",
        "test_", "Fake", or comment markers in file names or surrounding code.
        """
        # Check test name first (simple and fast)
        if test_name.lower().startswith("test_"):
            return True

        # Check for common test/mock context indicators in the code
        test_indicators = [
            r"\bdef\s+test_",  # test function definitions
            r"\bclass\s+Test",  # test class definitions
            r"\b@pytest\.fixture\b",  # pytest fixture decorator
            r"\b@mock\.",  # mock decorators
            r"\bunittest\b",  # unittest module
            r"\bMock\(",  # Mock instantiation
            r"\bMagicMock\(",  # MagicMock instantiation
            r"\bpatch\(",  # patch function
            r"\bfixture\s*=",  # fixture assignments
            r"\bmock_",  # mock variable prefixes
            r"\bfake_",  # fake variable prefixes
            r"\btest_data\b",  # test data variables
        ]

        # Combine all indicators into one pattern for efficiency
        combined_pattern = "|".join(test_indicators)
        if re.search(combined_pattern, code, re.IGNORECASE):
            return True

        # Check for import statements that indicate test/mock context
        import_patterns = [
            r"^\s*import\s+pytest",
            r"^\s*import\s+unittest",
            r"^\s*import\s+mock",
            r"^\s*from\s+unittest\s+import",
            r"^\s*from\s+mock\s+import",
            r"^\s*from\s+pytest\s+import",
        ]

        for pattern in import_patterns:
            if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                return True

        return False

    def _load_nutrition_knowledge(self) -> Dict[str, Any]:
        """Загружает базу знаний о питании.

        RU: Макронутриентные диапазоны базируются на USDA Dietary Guidelines 2020-2025
        и рекомендациях ВОЗ по здоровому питанию.
        EN: Macronutrient ranges based on USDA Dietary Guidelines 2020-2025
        and WHO Healthy Diet guidance.

        Note: Constants imported from core.nutrition_constants for consistency.
        """
        return {
            "nutrient_limits": {
                "protein_min_percent": PROTEIN_MIN_PERCENT,  # 10% per USDA DG 2020-2025
                "protein_max_percent": PROTEIN_MAX_PERCENT,  # 35% per USDA DG 2020-2025
                "fat_min_percent": FAT_MIN_PERCENT,  # 20% per USDA DG 2020-2025
                "fat_max_percent": FAT_MAX_PERCENT,  # 35% per USDA DG 2020-2025
                "carbs_min_percent": CARBS_MIN_PERCENT,  # 45% per USDA DG 2020-2025
                "carbs_max_percent": CARBS_MAX_PERCENT,  # 65% per USDA DG 2020-2025
            },
            "allergens": [
                "milk",
                "eggs",
                "fish",
                "crustacean_shellfish",
                "tree_nuts",
                "peanuts",
                "wheat",
                "soybeans",
                "sesame",
            ],
            "medical_conditions": [
                "diabetes",
                "hypertension",
                "heart_disease",
                "celiac",
                "lactose_intolerance",
            ],
        }

    def _load_safety_thresholds(self) -> Dict[str, float]:
        """Загружает пороговые значения безопасности.

        RU: Использует централизованные константы из core.nutrition_constants.
        EN: Uses centralized constants from core.nutrition_constants.
        """
        return {
            "bmi_dangerous_low": BMI_DANGEROUS_LOW,  # From nutrition_constants
            "bmi_dangerous_high": BMI_OBESITY_THRESHOLD,  # From nutrition_constants
            "calorie_dangerous_low": KCAL_MIN_SAFE,  # From nutrition_constants
            "calorie_dangerous_high": KCAL_MAX_SAFE,  # From nutrition_constants
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
        # Support both integer and decimal values (e.g., "kcal = 1234.5")
        calorie_patterns = [
            r"calories?\s*[=:]\s*(\d+(?:\.\d+)?)",
            r"kcal\s*[=:]\s*(\d+(?:\.\d+)?)",
            r"energy\s*[=:]\s*(\d+(?:\.\d+)?)",
        ]

        for pattern in calorie_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                try:
                    calories = float(match.group(1))

                    # Extract surrounding context (40 chars before match) to detect meal identifiers
                    context_start = max(0, match.start() - 40)
                    context_snippet = f"{test_name} {code[context_start : match.end()]}"

                    # Skip meal-level values (detect via keywords and heuristics)
                    # Only flag daily totals as dangerous
                    if is_meal_level_value(calories, context=context_snippet):
                        continue

                    # Проверка на опасные значения (только для daily totals)
                    if calories < self.safety_thresholds["calorie_dangerous_low"]:
                        results.append(
                            NutritionTestResult(
                                test_name=test_name,
                                success=False,
                                nutrition_category=NutritionCategory.CALORIE_CALCULATION,
                                error_type=NutritionErrorType.CALORIE_UNDERFLOW,
                                error_message=f"Опасно низкое количество калорий (daily): {calories}",
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

        # Detect explicit calorie consumption calls (e.g., consume_calories(10000))
        consume_call_pattern = re.compile(r"consume_calories\s*\(\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
        for match in consume_call_pattern.finditer(code):
            try:
                calories = float(match.group(1))
                if calories > self.safety_thresholds["calorie_dangerous_high"]:
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
                    elif bmi >= self.safety_thresholds["bmi_dangerous_high"]:
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

        # Detect calculate_bmi calls with numeric literals (e.g., weight=30, height=180)
        call_pattern = re.compile(
            r"calculate_bmi\s*\(\s*weight\s*=\s*([\d.]+)\s*,\s*height\s*=\s*([\d.]+)", re.IGNORECASE
        )
        for match in call_pattern.finditer(code):
            try:
                weight = float(match.group(1))
                height = float(match.group(2))
                # Convert cm to m if value looks like cm (> 3m is unrealistic)
                height_m = height / 100.0 if height > 3 else height
                if height_m <= 0 or height_m > 3 or height <= 0:
                    continue
                bmi = _compute_bmi(weight, height_m)
                if (
                    bmi < self.safety_thresholds["bmi_dangerous_low"]
                    or bmi >= self.safety_thresholds["bmi_dangerous_high"]
                ):
                    level: SafetyLevel = "dangerous"
                    message = (
                        f"Опасно низкий BMI: {bmi:.1f}"
                        if bmi < self.safety_thresholds["bmi_dangerous_low"]
                        else f"Опасно высокий BMI: {bmi:.1f}"
                    )
                    results.append(
                        NutritionTestResult(
                            test_name=test_name,
                            success=False,
                            nutrition_category=NutritionCategory.BMI_SAFETY,
                            error_type=NutritionErrorType.BMI_DANGEROUS,
                            error_message=message,
                            business_impact=(
                                "Риск ожирения и сопутствующих заболеваний"
                                if bmi >= self.safety_thresholds["bmi_dangerous_high"]
                                else "Риск анорексии и недоедания"
                            ),
                            safety_level=level,
                        )
                    )
            except ValueError:
                continue

        return results

    def _analyze_allergen_safety(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует безопасность аллергенов."""
        results = []

        # Поиск упоминаний аллергенов
        code_lower = code.lower()
        allergen_mentions = [
            allergen
            for allergen in self.nutrition_knowledge_base["allergens"]
            if allergen.lower() in code_lower
        ]

        # Проверка на отсутствие проверок аллергенов
        if allergen_mentions and not any(
            keyword in code_lower for keyword in ["allergen", "allergy", "check", "safe"]
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
        code_lower = code.lower()
        medical_mentions = [
            condition
            for condition in self.nutrition_knowledge_base["medical_conditions"]
            if condition.lower() in code_lower
        ]

        # Проверка на противоречия в медицинских рекомендациях
        if medical_mentions:
            # Проверка на диабет и высокое содержание сахара
            if (
                "diabetes" in medical_mentions
                and "sugar" in code_lower
                and "limit" not in code_lower
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
        results: List[NutritionTestResult] = []

        # Skip privacy checks if we're in a test/mock context to avoid false positives,
        # except when the test explicitly targets privacy behavior.
        if self._is_in_test_or_mock_context(code, test_name) and "privacy" not in test_name.lower():
            return results

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

    def _validate_macronutrients(
        self, test_name: str, protein_grams: float, fat_grams: float, carb_grams: float
    ) -> List[NutritionTestResult]:
        """Validate macronutrient values and balance.

        Extracted helper for testing macronutrient validation logic without regex coupling.

        Args:
            test_name: Test name for result identification
            protein_grams: Protein amount in grams (must be non-negative)
            fat_grams: Fat amount in grams (must be non-negative)
            carb_grams: Carbohydrate amount in grams (must be non-negative)

        Returns:
            List of NutritionTestResult for any validation errors found
        """
        results = []

        # Explicitly check for negative values before calculating calories
        # This prevents negative values from being masked by positive values in other macros
        negative_macros = []
        if protein_grams < 0:
            negative_macros.append(f"белок={protein_grams}г")
        if fat_grams < 0:
            negative_macros.append(f"жиры={fat_grams}г")
        if carb_grams < 0:
            negative_macros.append(f"углеводы={carb_grams}г")

        if negative_macros:
            results.append(
                NutritionTestResult(
                    test_name=test_name,
                    success=False,
                    nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                    error_type=NutritionErrorType.MACRONUTRIENT_SUM_INVALID,
                    error_message=(
                        f"Макронутриенты не могут быть отрицательными: {', '.join(negative_macros)}"
                    ),
                    business_impact=(
                        "Отрицательные значения макронутриентов указывают на ошибки в данных, "
                        "что может привести к неверным расчетам калорий и рекомендаций"
                    ),
                    safety_level="dangerous",
                )
            )
            # Skip further checks when negative values are present
            return results

        # Calculate calories for each macro (protein/carbs = 4 cal/g, fat = 9 cal/g)
        protein_cals = protein_grams * 4
        fat_cals = fat_grams * 9
        carb_cals = carb_grams * 4

        total_calories = protein_cals + fat_cals + carb_cals

        # Validate that total_calories is positive
        # Note: Percentages calculated from calories always sum to ~100% by definition,
        # so we skip redundant percentage sum validation and instead ensure calorie values are valid
        if total_calories <= 0:
            results.append(
                NutritionTestResult(
                    test_name=test_name,
                    success=False,
                    nutrition_category=NutritionCategory.MACRONUTRIENT_BALANCE,
                    error_type=NutritionErrorType.MACRONUTRIENT_SUM_INVALID,
                    error_message=(
                        f"Общая калорийность макронутриентов должна быть положительной: "
                        f"белок={protein_cals}ккал, жиры={fat_cals}ккал, "
                        f"углеводы={carb_cals}ккал, всего={total_calories}ккал"
                    ),
                    business_impact=(
                        "Некорректные данные о питании могут привести к "
                        "ошибкам в расчетах калорий и макронутриентов, "
                        "что влияет на доверие пользователей"
                    ),
                    safety_level="dangerous",
                )
            )
            # Skip further percentage-based checks if total_calories is invalid
            return results

        # Only proceed with percentage checks if total_calories is valid
        protein_pct = protein_cals / total_calories
        fat_pct = fat_cals / total_calories
        carb_pct = carb_cals / total_calories

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

    def _analyze_nutrition_standards(self, code: str, test_name: str) -> List[NutritionTestResult]:
        """Анализирует соответствие стандартам питания."""
        results = []

        # Поиск макронутриентов
        # Support decimal values and account for possible reassignments:
        # use re.findall and take the last occurrence for each macro.
        # Note: Patterns match only positive numbers (\d+). Negative macronutrient values
        # are not expected in valid nutritional data, so we validate positivity below.
        macro_patterns = {
            "protein": r"protein\s*[=:]\s*(\d+(?:\.\d+)?)",
            "fat": r"fat\s*[=:]\s*(\d+(?:\.\d+)?)",
            "carbs": r"carbs?\s*[=:]\s*(\d+(?:\.\d+)?)",
        }

        macro_values: Dict[str, float] = {}
        for macro, pattern in macro_patterns.items():
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                # Take the last occurrence to account for reassignments in the test
                # RU: Берем последнее вхождение для учета переприсвоений в тесте
                # EN: Last-match logic is robust for typical test patterns (setup -> assertions)
                #     but may miss edge cases with conditional branches or loops reassigning macros.
                #     Trade-off: simplicity vs. full control-flow analysis (CFG/SSA).
                #     Current approach is sufficient for 99% of test code patterns.
                macro_values[macro] = float(matches[-1])

        # Проверка баланса макронутриентов
        if len(macro_values) >= 2:
            # Use extracted validation helper for testability
            protein_grams = macro_values.get("protein", 0)
            fat_grams = macro_values.get("fat", 0)
            carb_grams = macro_values.get("carbs", 0)

            results.extend(
                self._validate_macronutrients(test_name, protein_grams, fat_grams, carb_grams)
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

        if (
            NutritionCategory.NUTRITION_STANDARDS in issues
            or NutritionCategory.MACRONUTRIENT_BALANCE in issues
        ):
            recommendations.append(
                "Проверять баланс макронутриентов согласно медицинским стандартам"
            )

        return recommendations

    def get_safety_score(self) -> float:
        """Вычисляет общий балл безопасности питания."""
        if self._total_analyses == 0:
            return 1.0

        base_score = (self._total_analyses - self._failed_analyses) / self._total_analyses

        # Compute total dangerous penalty by summing per-issue penalties
        total_dangerous_penalty = sum(
            self.DANGEROUS_PENALTY
            for result in self.test_results
            if not result.success and result.safety_level == "dangerous"
        )

        # Cap the cumulative penalty to prevent over-penalization
        # This ensures we never drive the score below zero even with many findings
        capped_penalty = min(total_dangerous_penalty, self.MAX_TOTAL_PENALTY)

        # Subtract capped penalty from base_score and clamp to [0, 1]
        return max(0.0, min(1.0, base_score - capped_penalty))

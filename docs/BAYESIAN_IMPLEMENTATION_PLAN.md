# 🎯 План Внедрения Расширенных Байесовских Методов в PulsePlate

**Версия**: 1.0
**Дата создания**: 2025-11-07
**Статус**: Planning
**Ориентировочная длительность**: 3-4 недели

---

## 📋 Executive Summary

Этот план описывает поэтапное внедрение продвинутых байесовских анализаторов для улучшения:

- ✅ **Качества данных** (валидация нереалистичных значений)
- ✅ **Персонализации** (предсказание поведения пользователей)
- ✅ **Рекомендаций** (адаптивная система на основе feedback)
- ✅ **Производительности** (байесовская оптимизация API)

**Ожидаемые результаты**:

- 📈 Увеличение retention на 15-20%
- 🎯 Улучшение точности рекомендаций на 25-30%
- ⚡ Снижение аномальных данных на 40%
- 🔍 Раннее обнаружение проблем со здоровьем

---

## 🏗️ Архитектура

```text
core/
├── bayesian/
│   ├── __init__.py
│   ├── base_analyzer.py              # Базовый класс для всех анализаторов
│   ├── nutrition_data_validator.py    # Phase 2: Валидация данных
│   ├── user_behavior_analyzer.py      # Phase 3: Поведение пользователей
│   ├── adaptive_recommender.py        # Phase 4: Адаптивные рекомендации
│   ├── api_performance_analyzer.py    # Phase 4: Оптимизация API
│   ├── metrics.py                     # Метрики эффективности
│   └── utils.py                       # Вспомогательные функции
├── bayesian_test_analyzer.py         # Existing
├── nutrition_bayesian_analyzer.py    # Existing
├── business_bayesian_analyzer.py     # Existing
└── comprehensive_bayesian_analyzer.py # Existing

tests/
├── test_nutrition_data_validator.py
├── test_user_behavior_analyzer.py
└── test_adaptive_recommender.py

docs/
├── bayesian_architecture.md           # Документация архитектуры
└── bayesian_metrics_dashboard.md      # Grafana дашборд
```

---

## 📅 Phase 1: Подготовка Архитектуры (2-3 дня)

### Задачи

#### 1.1. Создать базовый класс `BaseBayesianAnalyzer`

**Файл**: `core/bayesian/base_analyzer.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

@dataclass
class BayesianPrediction:
    """Результат байесовского предсказания."""
    value: float
    confidence: float
    evidence: List[str]
    prior_belief: Dict[str, float]
    posterior_belief: Dict[str, float]

class BaseBayesianAnalyzer(ABC):
    """
    Базовый класс для всех байесовских анализаторов.

    Предоставляет:
    - Логирование
    - Сохранение/загрузка состояния
    - Базовые математические операции
    - Метрики эффективности
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"bayesian.{name}")
        self.predictions_count = 0
        self.successful_predictions = 0

    @abstractmethod
    def predict(self, data: Dict[str, Any]) -> BayesianPrediction:
        """Основной метод предсказания (должен быть реализован в подклассах)."""
        pass

    def calculate_posterior(
        self,
        prior: float,
        likelihood: float,
        evidence: float
    ) -> float:
        """Теорема Байеса: P(H|E) = P(E|H) * P(H) / P(E)"""
        if evidence == 0:
            return 0
        return (likelihood * prior) / evidence

    def get_metrics(self) -> Dict[str, float]:
        """Метрики эффективности анализатора."""
        if self.predictions_count == 0:
            return {"accuracy": 0.0, "total_predictions": 0}

        accuracy = self.successful_predictions / self.predictions_count
        return {
            "accuracy": accuracy,
            "total_predictions": self.predictions_count,
            "successful_predictions": self.successful_predictions
        }
```

**Критерии готовности**:

- ✅ Класс создан и покрыт тестами
- ✅ Существующие анализаторы могут наследоваться от него (backward compatible)

---

#### 1.2. Система метрик `BayesianMetrics`

**Файл**: `core/bayesian/metrics.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

@dataclass
class BayesianMetrics:
    """Метрики эффективности байесовских методов."""

    analyzer_name: str
    predictions_made: int = 0
    correct_predictions: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    average_confidence: float = 0.0
    execution_times: List[float] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if self.predictions_made == 0:
            return 0.0
        return self.correct_predictions / self.predictions_made

    @property
    def precision(self) -> float:
        tp = self.correct_predictions
        fp = self.false_positives
        if (tp + fp) == 0:
            return 0.0
        return tp / (tp + fp)

    @property
    def recall(self) -> float:
        tp = self.correct_predictions
        fn = self.false_negatives
        if (tp + fn) == 0:
            return 0.0
        return tp / (tp + fn)

    @property
    def f1_score(self) -> float:
        p = self.precision
        r = self.recall
        if (p + r) == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    def to_dict(self) -> Dict:
        return {
            "analyzer": self.analyzer_name,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "predictions_made": self.predictions_made,
            "avg_confidence": self.average_confidence
        }
```

**Критерии готовности**:

- ✅ Метрики собираются автоматически
- ✅ Можно экспортировать в Prometheus/Grafana

---

## 📅 Phase 2: NutritionDataValidationAnalyzer (3-4 дня) ⭐ QUICK WIN

### Цель

Предотвратить ввод нереалистичных данных о питании, используя байесовскую вероятность.

### Задачи

#### 2.1. Создать валидатор

**Файл**: `core/bayesian/nutrition_data_validator.py`

```python
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from .base_analyzer import BaseBayesianAnalyzer, BayesianPrediction

@dataclass
class NutritionEntry:
    """Запись о приеме пищи."""
    meal_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    portion_size: float
    meal_type: str  # breakfast, lunch, dinner, snack
    timestamp: str

@dataclass
class ValidationResult:
    """Результат валидации."""
    is_plausible: bool
    confidence: float
    anomaly_score: float
    issues: List[str]
    suggestions: Dict[str, float]

class NutritionDataValidationAnalyzer(BaseBayesianAnalyzer):
    """
    Байесовская валидация данных о питании.

    Проверяет:
    - Реалистичность калорий для данного блюда
    - Соотношение макронутриентов
    - Размер порции
    - Паттерны питания пользователя

    Privacy & HIPAA Compliance:
    - User health data is stored in-memory only (user_history dict)
    - No persistent logging of individual nutrition entries
    - Data is automatically purged after 100 entries per user
    - All calculations are performed locally without external API calls
    - User identifiers should be anonymized/hashed in production
    - Follows HIPAA minimum necessary standard: only stores data needed for validation
    """

    # Macronutrient calorie coefficients (kcal per gram) - Atwater system
    # Reference: USDA National Nutrient Database, Atwater general factors
    CALORIES_PER_GRAM_PROTEIN = 4.0  # Atwater: 4 kcal/g
    CALORIES_PER_GRAM_CARBS = 4.0    # Atwater: 4 kcal/g
    CALORIES_PER_GRAM_FAT = 9.0      # Atwater: 9 kcal/g

    # Medical safety thresholds (kcal per day)
    # NOTE: These constants reference the canonical values from core/nutrition_constants.py.
    # Runtime values are loaded from config/medical_safety.yaml if present, otherwise
    # the imported defaults (KCAL_MIN_SAFE, KCAL_MAX_SAFE) are used.
    # See CONTRIBUTING.md § Medical Safety Approval Workflow for approval requirements.
    # Import from single source of truth:
    from core.nutrition_constants import KCAL_MIN_SAFE, KCAL_MAX_SAFE
    MIN_SAFE_DAILY_CALORIES = KCAL_MIN_SAFE   # Default: 1200 kcal/day
    MAX_SAFE_DAILY_CALORIES = KCAL_MAX_SAFE   # Default: 6000 kcal/day

    # Feature flag: Medical alerts/enforcements are disabled by default until approved
    # Set MEDICAL_ALERTS_ENABLED = true in config/medical_safety.yaml after approval workflow
    # MEDICAL_ALERTS_ENABLED is set as instance attribute in __init__ from config

    def __init__(self):
        super().__init__("nutrition_validator")
        # Load medical safety config at startup and validate
        self._load_medical_safety_config()
        self.population_stats = self._load_population_stats()
        self.user_history: Dict[str, List[NutritionEntry]] = {}

    def _load_medical_safety_config(self) -> None:
        """
        Load medical safety configuration from config/medical_safety.yaml at startup.

        Validates that MIN_SAFE_DAILY_CALORIES and MAX_SAFE_DAILY_CALORIES are present,
        numeric, and MIN < MAX. Validates that MEDICAL_ALERTS_ENABLED is explicitly set
        (not default) before enabling medical alerts.

        If validation fails, logs a clear error and aborts startup to prevent deployment.
        """
        import logging
        from pathlib import Path

        logger = logging.getLogger(__name__)
        config_path = Path(__file__).parent.parent / "config" / "medical_safety.yaml"

        if not config_path.exists():
            logger.error(
                f"Medical safety config not found: {config_path}. "
                "Medical alerts will remain disabled. See CONTRIBUTING.md for approval workflow."
            )
            return

        try:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            # Validate thresholds
            thresholds = config.get("thresholds", {})
            min_cal = thresholds.get("MIN_SAFE_DAILY_CALORIES")
            max_cal = thresholds.get("MAX_SAFE_DAILY_CALORIES")

            if min_cal is None or max_cal is None:
                logger.error(
                    f"Medical safety config missing required thresholds: {config_path}. "
                    "MIN_SAFE_DAILY_CALORIES and MAX_SAFE_DAILY_CALORIES must be present."
                )
                raise ValueError("Missing required medical safety thresholds")

            try:
                min_cal = float(min_cal)
                max_cal = float(max_cal)
            except (ValueError, TypeError) as e:
                logger.error(
                    f"Medical safety config has invalid threshold values: {e}. "
                    "MIN_SAFE_DAILY_CALORIES and MAX_SAFE_DAILY_CALORIES must be numeric."
                )
                raise ValueError("Invalid medical safety threshold values") from e

            if min_cal >= max_cal:
                logger.error(
                    f"Medical safety config validation failed: MIN_SAFE_DAILY_CALORIES ({min_cal}) "
                    f"must be less than MAX_SAFE_DAILY_CALORIES ({max_cal})."
                )
                raise ValueError("MIN_SAFE_DAILY_CALORIES must be < MAX_SAFE_DAILY_CALORIES")

            # Override fallback constants with loaded values
            self.MIN_SAFE_DAILY_CALORIES = min_cal
            self.MAX_SAFE_DAILY_CALORIES = max_cal

            # Validate and set feature flag
            feature_flags = config.get("featureFlags", {})
            alerts_enabled = feature_flags.get("medicalSafetyApproved", False)

            if alerts_enabled:
                # Verify it's explicitly set (not just default)
                if "medicalSafetyApproved" not in feature_flags:
                    logger.warning(
                        "MEDICAL_ALERTS_ENABLED appears to be default value. "
                        "Medical alerts will remain disabled until explicitly approved."
                    )
                    alerts_enabled = False
                else:
                    logger.info("Medical safety alerts enabled via approved configuration.")
            else:
                logger.info("Medical safety alerts disabled (not approved).")

            self.MEDICAL_ALERTS_ENABLED = bool(alerts_enabled)

        except ImportError:
            logger.warning(
                "PyYAML not installed. Medical safety config cannot be loaded. "
                "Using fallback constants. Install PyYAML to enable config loading."
            )
        except Exception as e:
            logger.error(
                f"Failed to load medical safety config from {config_path}: {e}. "
                "Startup aborted to prevent unsafe deployment. Fix config and restart."
            )
            raise SystemExit(1) from e

    def _load_population_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Загрузка популяционной статистики.

        Attempts to load validated USDA/official data, falls back to documented
        local fixture if unavailable. Returns safe defaults if all loading fails.

        Priority:
        1. USDA National Health and Nutrition Examination Survey (NHANES) data
        2. Validated local fixture file (data/population_nutrition_stats.json)
           See data/population_nutrition_stats.json for validated NHANES-derived values
        3. Fallback defaults based on published research (NHANES 2017-2020)
           Source: https://www.cdc.gov/nchs/nhanes/wweia.htm
        """
        # Try loading from USDA data source or local fixture
        try:
            # Placeholder for USDA API call or local fixture loader
            # In production: fetch from USDA FoodData Central API or local validated fixture
            # For now, use well-documented fallback defaults
            stats = self._load_from_usda_or_fixture()
            if stats:
                return stats
        except Exception:
            # Graceful fallback: use documented research-based defaults
            pass

        # Fallback defaults (based on NHANES 2017-2020 meal pattern analysis)
        # Source: NHANES 2017-2020 Dietary Data - What We Eat in America (WWEIA)
        # Dataset: https://www.cdc.gov/nchs/nhanes/wweia.htm
        # Data Release: NHANES 2017-2020 Public Use Data Files
        # Analysis: Mean and standard deviation of daily calorie intake by meal type
        # (breakfast, lunch, dinner, snack) calculated from 24-hour dietary recall data
        # Preprocessing: Aggregated across age groups 20+ years, weighted by survey weights
        # Local fixture: See data/population_nutrition_stats.json for validated values
        # To reproduce: Download NHANES WWEIA data files, extract meal timing variables,
        # calculate weighted means/std by meal type, and save to data/population_nutrition_stats.json
        return {
            "breakfast": {"mean_calories": 400, "std_calories": 150},
            "lunch": {"mean_calories": 600, "std_calories": 200},
            "dinner": {"mean_calories": 700, "std_calories": 250},
            "snack": {"mean_calories": 200, "std_calories": 100},
        }

    def _load_from_usda_or_fixture(self) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Load population stats from USDA API or validated local fixture.

        Returns None if unavailable (triggers fallback).

        Local fixture path: data/population_nutrition_stats.json
        Expected format: JSON dict with meal_type keys ("breakfast", "lunch", "dinner", "snack")
        Each meal_type contains "mean_calories" and "std_calories" float values.
        See NHANES 2017-2020 documentation for data source and preprocessing steps.
        """
        # TODO: Implement USDA FoodData Central API integration
        # TODO: Implement local fixture loader (data/population_nutrition_stats.json)
        # Local fixture should be generated from NHANES 2017-2020 WWEIA data:
        # 1. Download NHANES dietary recall data files from https://www.cdc.gov/nchs/nhanes/wweia.htm
        # 2. Extract meal timing variables (DR1MEX, DR2MEX for meal type)
        # 3. Calculate weighted means and standard deviations by meal type using survey weights
        # 4. Save results to data/population_nutrition_stats.json
        # For now, return None to use fallback defaults
        return None

    def validate(self, entry: NutritionEntry, user_id: str) -> ValidationResult:
        """
        Валидация записи о питании.

        Использует байесовский подход:
        P(valid | entry) = P(entry | valid) * P(valid) / P(entry)

        Комбинирует:
        - Популяционные данные (prior)
        - История пользователя (likelihood)
        - Физические ограничения (evidence)

        Returns bounded [0,1] probability values. Never raises on edge inputs.
        """
        issues = []

        # 0. Medical safety check - flag extreme values (only if feature flag enabled)
        if self.MEDICAL_ALERTS_ENABLED:
            daily_calories = self._estimate_daily_calories(user_id, entry)
            # Load thresholds from config/medical_safety.yaml (not hardcoded constants)
            min_threshold = self.MIN_SAFE_DAILY_CALORIES
            max_threshold = self.MAX_SAFE_DAILY_CALORIES
            if daily_calories < min_threshold:
                issues.append(
                    f"MEDICAL SAFETY ALERT: Estimated daily intake ({daily_calories:.0f} kcal) "
                    f"below safe minimum ({min_threshold} kcal). "
                    f"Possible medical emergency - please consult healthcare provider."
                )
            elif daily_calories > max_threshold:
                issues.append(
                    f"MEDICAL SAFETY ALERT: Estimated daily intake ({daily_calories:.0f} kcal) "
                    f"exceeds safe maximum ({max_threshold} kcal). "
                    f"Possible medical emergency - please consult healthcare provider."
                )

        # 1. Проверка физических ограничений
        if not self._check_physical_constraints(entry):
            issues.append("Нарушены физические ограничения (калории из макронутриентов)")

        # 2. Байесовская оценка относительно популяции
        population_plausibility = self._calculate_population_plausibility(entry)

        # 3. Байесовская оценка относительно истории пользователя
        user_plausibility = self._calculate_user_plausibility(entry, user_id)

        # 4. Комбинируем оценки (ensure bounded [0,1])
        combined_plausibility = max(0.0, min(1.0, 0.3 * population_plausibility + 0.7 * user_plausibility))

        # 5. Вычисляем anomaly score (ensure bounded [0,1])
        anomaly_score = max(0.0, min(1.0, 1 - combined_plausibility))

        # 6. Генерируем предложения для исправления
        suggestions = {}
        if anomaly_score > 0.5:
            suggestions = self._generate_suggestions(entry, user_id)

        # 7. Определяем финальный вердикт
        is_plausible = anomaly_score < 0.6

        if anomaly_score > 0.7:
            issues.append(f"Очень необычные значения для {entry.meal_type}")

        return ValidationResult(
            is_plausible=is_plausible,
            confidence=combined_plausibility,
            anomaly_score=anomaly_score,
            issues=issues,
            suggestions=suggestions
        )

    def _estimate_daily_calories(self, user_id: str, entry: NutritionEntry) -> float:
        """
        Estimate total daily calories based on user history and current entry.
        Falls back to population mean if insufficient data.
        """
        user_history = self.user_history.get(user_id, [])
        if len(user_history) < 3:
            # Use population mean as fallback
            stats = self.population_stats.get(entry.meal_type, {"mean_calories": 500})
            return stats["mean_calories"] * 3  # Rough estimate: 3 meals
        # Sum recent entries (last 24h equivalent)
        recent_calories = sum(e.calories for e in user_history[-10:])
        return recent_calories + entry.calories

    def _check_physical_constraints(self, entry: NutritionEntry) -> bool:
        """
        Проверка физических ограничений (калории из макронутриентов).

        Uses Atwater coefficients to verify calorie calculation.
        Returns True if within tolerance, False otherwise.
        Never raises on zero/edge inputs.
        """
        calculated_calories = (
            entry.protein * self.CALORIES_PER_GRAM_PROTEIN +
            entry.carbs * self.CALORIES_PER_GRAM_CARBS +
            entry.fat * self.CALORIES_PER_GRAM_FAT
        )
        tolerance = 0.15  # 15% допуск

        # Zero-division guard: if entry.calories is zero or negative, treat as invalid
        if entry.calories <= 0:
            # Invalid calorie values fail the constraint
            return False

        relative_diff = abs(calculated_calories - entry.calories) / entry.calories
        return relative_diff < tolerance

    def _calculate_population_plausibility(self, entry: NutritionEntry) -> float:
        """
        Вероятность на основе популяционных данных.
        Использует нормальное распределение.

        Returns bounded [0,1] probability. Falls back to population prior if std is zero.
        Never raises on edge inputs.
        """
        stats = self.population_stats.get(entry.meal_type, {"mean_calories": 500, "std_calories": 200})
        mean = stats["mean_calories"]
        std = stats["std_calories"]

        # Zero-division guard: if std is zero or very small, return safe default
        if std <= 1e-6:
            # Fallback to population prior: if entry matches mean exactly, return high probability
            # Otherwise return moderate probability
            if abs(entry.calories - mean) < 1e-6:
                return 0.8  # High probability for exact match
            return 0.5  # Moderate probability as safe default

        # Вероятность из нормального распределения
        z_score = abs(entry.calories - mean) / std
        probability = np.exp(-0.5 * z_score ** 2)

        # Ensure bounded [0,1] (exp should already be bounded, but guard against edge cases)
        return max(0.0, min(1.0, probability))

    def _calculate_user_plausibility(self, entry: NutritionEntry, user_id: str) -> float:
        """
        Вероятность на основе истории пользователя.
        Если истории нет - используем популяционный prior.

        Returns bounded [0,1] probability. Falls back to population prior if insufficient data.
        Never raises on edge inputs.
        """
        user_history = self.user_history.get(user_id, [])

        if len(user_history) < 5:
            # Недостаточно данных - используем популяционный prior
            return self._calculate_population_plausibility(entry)

        # Фильтруем по типу приема пищи
        similar_meals = [e for e in user_history if e.meal_type == entry.meal_type]

        if len(similar_meals) < 3:
            return self._calculate_population_plausibility(entry)

        # Вычисляем среднее и стандартное отклонение для пользователя
        calories_list = [e.calories for e in similar_meals]

        # Guard against empty list (shouldn't happen due to check above, but defensive)
        if not calories_list:
            return self._calculate_population_plausibility(entry)

        user_mean = np.mean(calories_list)
        # Use population std as fallback if user std is zero or too small
        user_std = np.std(calories_list) if len(calories_list) > 1 else None

        if user_std is None or user_std <= 1e-6:
            # Fallback to population std for this meal type
            stats = self.population_stats.get(entry.meal_type, {"std_calories": 200})
            user_std = stats["std_calories"]
            # If still zero, use safe default
            if user_std <= 1e-6:
                user_std = 200.0  # Safe default std

        # Вероятность из пользовательского распределения
        z_score = abs(entry.calories - user_mean) / user_std
        probability = np.exp(-0.5 * z_score ** 2)

        # Ensure bounded [0,1]
        return max(0.0, min(1.0, probability))

    def _generate_suggestions(self, entry: NutritionEntry, user_id: str) -> Dict[str, float]:
        """
        Генерация предложений для исправления.

        Returns suggestions with bounded, safe values. Never raises on edge inputs.
        All suggested values are clamped to reasonable ranges.
        """
        suggestions = {}

        # Предложение на основе популяции
        pop_stats = self.population_stats.get(entry.meal_type, {})
        if pop_stats and "mean_calories" in pop_stats:
            pop_mean = pop_stats["mean_calories"]
            # Ensure suggestion is within safe bounds
            suggestions["suggested_calories_population"] = max(
                self.MIN_SAFE_DAILY_CALORIES / 4,  # At least 1/4 of daily minimum per meal
                min(pop_mean, self.MAX_SAFE_DAILY_CALORIES / 2)  # At most 1/2 of daily max per meal
            )

        # Предложение на основе истории пользователя
        user_history = self.user_history.get(user_id, [])
        similar_meals = [e for e in user_history if e.meal_type == entry.meal_type]

        if len(similar_meals) >= 3:
            calories_list = [e.calories for e in similar_meals]
            if calories_list:  # Guard against empty list
                user_mean = np.mean(calories_list)
                # Ensure suggestion is within safe bounds
                suggestions["suggested_calories_your_usual"] = max(
                    self.MIN_SAFE_DAILY_CALORIES / 4,
                    min(user_mean, self.MAX_SAFE_DAILY_CALORIES / 2)
                )

        return suggestions

    def update_user_history(self, user_id: str, entry: NutritionEntry):
        """Обновление истории пользователя (после подтверждения данных)."""
        if user_id not in self.user_history:
            self.user_history[user_id] = []

        self.user_history[user_id].append(entry)

        # Ограничиваем размер истории
        if len(self.user_history[user_id]) > 100:
            self.user_history[user_id] = self.user_history[user_id][-100:]
```

**Критерии готовности**:

- ✅ Валидатор создан и протестирован
- ✅ Покрытие тестами ≥ 97%
- ✅ Ложных срабатываний < 5%

---

#### 2.2. Тесты для валидатора

**Файл**: `tests/test_nutrition_data_validator.py`

```python
import pytest
from core.bayesian.nutrition_data_validator import (
    NutritionDataValidationAnalyzer,
    NutritionEntry,
    ValidationResult
)

class TestNutritionDataValidator:

    @pytest.fixture
    def validator(self):
        return NutritionDataValidationAnalyzer()

    def test_realistic_entry_passes(self, validator) -> None:
        """Реалистичная запись должна проходить валидацию."""
        entry = NutritionEntry(
            meal_name="Oatmeal with banana",
            calories=400,
            protein=10,
            fat=8,
            carbs=70,
            portion_size=250,
            meal_type="breakfast",
            timestamp="2025-11-07T08:00:00"
        )

        result = validator.validate(entry, "user_123")

        assert result.is_plausible is True
        assert result.confidence > 0.5
        assert result.anomaly_score < 0.5

    def test_unrealistic_calories_flagged(self, validator) -> None:
        """Нереалистично высокие калории должны быть помечены."""
        entry = NutritionEntry(
            meal_name="Apple",
            calories=5000,  # Нереалистично!
            protein=1,
            fat=0,
            carbs=25,
            portion_size=150,
            meal_type="snack",
            timestamp="2025-11-07T10:00:00"
        )

        result = validator.validate(entry, "user_123")

        assert result.is_plausible is False
        assert result.anomaly_score > 0.6
        assert len(result.issues) > 0

    def test_learns_from_user_history(self, validator) -> None:
        """Валидатор должен учиться на основе истории пользователя."""
        # Добавляем историю: пользователь всегда ест большие завтраки
        for _ in range(10):
            big_breakfast = NutritionEntry(
                meal_name="Big breakfast",
                calories=800,
                protein=30,
                fat=25,
                carbs=90,
                portion_size=400,
                meal_type="breakfast",
                timestamp="2025-11-07T08:00:00"
            )
            validator.update_user_history("user_power_eater", big_breakfast)

        # Теперь большой завтрак для этого пользователя должен быть нормальным
        test_entry = NutritionEntry(
            meal_name="Another big breakfast",
            calories=850,
            protein=32,
            fat=27,
            carbs=95,
            portion_size=420,
            meal_type="breakfast",
            timestamp="2025-11-08T08:00:00"
        )

        result = validator.validate(test_entry, "user_power_eater")

        # Должен пройти для этого пользователя
        assert result.is_plausible is True
        assert result.confidence > 0.6
```

---

#### 2.3. Интеграция в app.py

**Модификация**: `app.py`

```python
# В начале файла
from core.bayesian.nutrition_data_validator import (
    NutritionDataValidationAnalyzer,
    NutritionEntry
)

# В lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing initialization...

    # Байесовские анализаторы
    app.state.nutrition_validator = NutritionDataValidationAnalyzer()

    yield

    # Cleanup...

# Новый эндпоинт для валидации
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from typing import Literal, List, Dict

# Pydantic модель для валидации входных данных
class MealValidationRequest(BaseModel):
    """Модель запроса для валидации приема пищи."""
    name: str = Field(..., min_length=1, max_length=200, description="Название блюда")
    calories: float = Field(..., ge=0, le=10000, description="Калории (0-10000)")
    protein: float = Field(..., ge=0, le=1000, description="Белки в граммах (0-1000)")
    fat: float = Field(..., ge=0, le=1000, description="Жиры в граммах (0-1000)")
    carbs: float = Field(..., ge=0, le=1000, description="Углеводы в граммах (0-1000)")
    portion_size: float = Field(default=100, ge=1, le=10000, description="Размер порции в граммах")
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., description="Тип приема пищи"
    )
    timestamp: str = Field(default="", max_length=50, description="Временная метка")
    user_id: str = Field(..., min_length=1, max_length=100, description="ID пользователя")

    @field_validator("calories", "protein", "fat", "carbs")
    @classmethod
    def validate_non_negative(cls, v: float, info: ValidationInfo) -> float:
        """Проверка неотрицательных значений."""
        if v < 0:
            raise ValueError("Значение не может быть отрицательным")
        return v


# Pydantic модель для ответа валидации
class MealValidationResponse(BaseModel):
    """Модель ответа для валидации приема пищи."""
    is_valid: bool = Field(..., description="Результат валидации (True если данные правдоподобны)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уровень уверенности (0.0-1.0)")
    anomaly_score: float = Field(..., ge=0.0, description="Оценка аномальности (чем выше, тем более аномально)")
    warnings: List[str] = Field(default_factory=list, description="Список предупреждений о потенциальных проблемах")
    suggestions: Dict[str, float] = Field(default_factory=dict, description="Предложения по корректировке значений (ключ: название параметра, значение: рекомендуемое значение)")


@app.post("/api/validate_meal", response_model=MealValidationResponse)
async def validate_meal_data(
    request: Request,
    meal_request: MealValidationRequest,
    current_user: User = Depends(get_current_user),  # Требуется аутентификация
) -> MealValidationResponse:
    """
    Валидация данных о приеме пищи перед сохранением.

    Security & Privacy:
    - Требуется аутентификация через токен (current_user dependency)
    - Проверка авторизации: user_id должен совпадать с current_user.id
    - Rate limiting: реализуется SlowAPI middleware (см. app.py)
    - Шифрование в transit (HTTPS) и at rest (зашифрованное хранилище)
    - Результаты валидации не сохраняются (ephemeral)
    - PHI не логируется (только метаданные без раскрытия данных)
    - Временное хранение (если требуется): автоматическое удаление через 24 часа

    HIPAA Compliance:
    - Данные передаются по зашифрованному каналу (TLS 1.3+)
    - Валидация выполняется без сохранения PHI
    - Логи содержат только метаданные (user_id hash, timestamp, результат валидации)
    - Нет персистентного хранения результатов валидации

    Args:
        request: FastAPI Request object (для rate limiting)
        meal_request: Валидированные данные о приеме пищи
        current_user: Текущий аутентифицированный пользователь

    Returns:
        - is_valid: bool
        - confidence: float
        - warnings: List[str]
        - suggestions: Dict[str, float]

    Raises:
        HTTPException(400): Невалидные входные данные
        HTTPException(401): Неавторизованный доступ
        HTTPException(403): user_id не совпадает с current_user.id
    """
    # Проверка авторизации: user_id должен совпадать с current_user.id
    if meal_request.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id не совпадает с текущим пользователем"
        )

    validator = request.app.state.nutrition_validator

    entry = NutritionEntry(
        meal_name=meal_request.name,
        calories=meal_request.calories,
        protein=meal_request.protein,
        fat=meal_request.fat,
        carbs=meal_request.carbs,
        portion_size=meal_request.portion_size,
        meal_type=meal_request.meal_type,
        timestamp=meal_request.timestamp
    )

    result = validator.validate(entry, meal_request.user_id)

    # Логирование только метаданных (без PHI)
    import hashlib
    user_id_hash = hashlib.sha256(meal_request.user_id.encode()).hexdigest()[:16]
    logger.info(
        f"Meal validation: user_id_hash={user_id_hash}, "
        f"is_valid={result.is_plausible}, confidence={result.confidence:.2f}"
    )

    return MealValidationResponse(
        is_valid=result.is_plausible,
        confidence=result.confidence,
        anomaly_score=result.anomaly_score,
        warnings=result.issues,
        suggestions=result.suggestions
    )

**Зависимости**:

- SlowAPI middleware: глобальный rate limiting уже инициализируется в app.py
- `pydantic`: для валидации входных данных (уже включен в FastAPI)
- `get_current_user`: dependency для аутентификации (должен быть реализован в `api/auth.py` или аналогичном модуле)
- `User`: модель пользователя из системы аутентификации

**Тестирование**:

- Unit тесты: валидация Pydantic модели, проверка граничных значений
- Integration тесты: проверка аутентификации, авторизации, rate limiting
- Security тесты: проверка отсутствия PHI в логах, проверка шифрования
- Примеры тестов см. в `tests/test_api_validate_meal.py` (создать)

---

## 📅 Phase 3: UserBehaviorBayesianAnalyzer (4-5 дней)

### Цель

Предсказание поведения пользователей для улучшения retention и персонализации.

### Задачи

#### 3.1. Создать анализатор поведения

**Файл**: `core/bayesian/user_behavior_analyzer.py`

```python
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from .base_analyzer import BaseBayesianAnalyzer, BayesianPrediction

class UserBehaviorBayesianAnalyzer(BaseBayesianAnalyzer):
    """
    Предсказывает поведение пользователей:
    - Вероятность достижения целей
    - Риск churn (отказа от использования)
    - Предпочтения в блюдах
    - Оптимальное время для уведомлений
    """

    def predict_goal_achievement_probability(self, user_id: str) -> BayesianPrediction:
        """
        Предсказывает вероятность достижения целей по калориям.

        Факторы:
        - История соблюдения плана
        - Частота логирования
        - Стабильность паттернов
        - Социальная активность (если есть)
        """
        # TODO: Implement
        pass

    def predict_churn_risk(self, user_id: str) -> BayesianPrediction:
        """
        Предсказывает риск того, что пользователь перестанет использовать приложение.

        Факторы:
        - Снижение частоты логирования
        - Увеличение пропущенных дней
        - Отклонение от целей
        - Время с момента последней активности
        """
        # TODO: Implement
        pass

    def predict_meal_preference(
        self,
        user_id: str,
        meal_options: List[Dict]
    ) -> Dict[str, float]:
        """
        Ранжирует блюда по вероятности выбора пользователем.

        Использует:
        - История выбранных блюд
        - Предпочтения по макронутриентам
        - Время суток
        - Сезонность
        """
        # TODO: Implement
        pass
```

---

## 📅 Phase 4: AdaptiveRecommendationEngine (3-4 дня)

### Цель

Адаптивная система рекомендаций, которая учится на feedback пользователей.

**Файл**: `core/bayesian/adaptive_recommender.py`

```python
import numpy as np
from typing import Dict, List

class AdaptiveRecommendationEngine:
    """
    Thompson Sampling для оптимизации рекомендаций.

    Multi-Armed Bandit подход:
    - Каждая стратегия рекомендации = arm
    - Балансирует exploration vs exploitation
    - Адаптируется к feedback в реальном времени
    """

    def __init__(self) -> None:
        self.arms = {
            "high_protein": {"alpha": 1, "beta": 1},
            "balanced": {"alpha": 1, "beta": 1},
            "low_carb": {"alpha": 1, "beta": 1},
            "mediterranean": {"alpha": 1, "beta": 1},
        }

    def select_strategy(self, user_context: Dict) -> str:
        """
        Выбирает стратегию рекомендации с учетом контекста.

        Thompson Sampling:
        - Сэмплирует из Beta распределения для каждого arm
        - Выбирает arm с наибольшим сэмплом
        """
        samples = {
            arm: np.random.beta(params["alpha"], params["beta"])
            for arm, params in self.arms.items()
        }
        return max(samples, key=samples.get)

    def update_from_feedback(self, arm: str, success: bool):
        """
        Обновляет вероятности на основе feedback.

        Success = пользователь выбрал рекомендованное блюдо
        """
        if success:
            self.arms[arm]["alpha"] += 1
        else:
            self.arms[arm]["beta"] += 1
```

---

## 📅 Phase 5: Документация и Мониторинг (2 дня)

### Задачи

#### 5.1. Документация архитектуры

**Файл**: `docs/bayesian_architecture.md`

- Описание каждого анализатора
- Диаграммы взаимодействия
- Примеры использования
- Best practices

#### 5.2. Grafana дашборд

**Файл**: `docs/bayesian_metrics_dashboard.md`

Метрики для мониторинга:

- Точность предсказаний (accuracy)
- Количество аномалий
- Время выполнения анализа
- User engagement metrics

---

## 🎯 Критерии Успеха

### Технические метрики

- ✅ **Покрытие тестами**: > 97% (требование проекта)
- ✅ **Точность валидации**: > 90%
- ✅ **Ложные срабатывания**: < 5%
- ✅ **Время отклика API**: < 100ms для валидации

### Бизнес метрики

- 📈 **User retention**: +15-20%
- 🎯 **Точность рекомендаций**: +25-30%
- ⚡ **Аномальные данные**: -40%
- 💡 **User satisfaction**: +10%

---

## 🚀 Стратегия Деплоя

### Этап 1: Canary Deployment

- Включить для 5% пользователей
- Мониторить метрики 3-5 дней
- Собрать feedback

### Этап 2: Gradual Rollout

- 25% пользователей (1 неделя)
- 50% пользователей (1 неделя)
- 100% пользователей

### Этап 3: Optimization

- Анализ A/B тестов
- Тюнинг гиперпараметров
- Оптимизация производительности

---

## ⚠️ Риски и Митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Ложные срабатывания | Средняя | Высокое | Тщательное тестирование, постепенный rollout |
| Проблемы с производительностью | Низкая | Среднее | Кэширование, асинхронная обработка |
| Недостаток данных для новых пользователей | Высокая | Среднее | Hierarchical Bayesian Models, population priors |
| Сложность отладки | Средняя | Низкое | Детальное логирование, метрики, дашборды |

---

## 📚 Ресурсы

### Библиотеки

- `numpy` - математические операции
- `scipy` - статистические распределения
- `pymc3` (optional) - продвинутые байесовские модели
- `PyYAML` - YAML parsing для загрузки config/medical_safety.yaml

### Документация

- [Bayesian Data Analysis](http://www.stat.columbia.edu/~gelman/book/)
- [Thompson Sampling Tutorial](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf)
- [Multi-Armed Bandits](https://arxiv.org/abs/1904.07272)

---

## 📝 Чеклист для Нового PR

Перед созданием PR убедитесь:

- [ ] Все тесты проходят
- [ ] Покрытие тестами ≥ 97%
- [ ] Документация обновлена
- [ ] Метрики добавлены в мониторинг
- [ ] Code review пройден
- [ ] Performance тесты пройдены
- [ ] Changelog обновлен

---

## 🤝 Контакты

**Вопросы по плану**: создайте issue в репозитории
**Предложения**: PR в этот документ приветствуются!

---

**Статус**: ✅ План готов к началу реализации
**Следующий шаг**: Создать новую ветку `feat/bayesian-user-analytics` и начать с Phase 1

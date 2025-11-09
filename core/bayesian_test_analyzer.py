"""
Байесовская система анализа тестов и диагностики для PulsePlate.

Использует теорему Байеса для:
- Предсказания вероятности ошибок
- Диагностики причин падающих тестов
- Оптимизации порядка выполнения тестов
- Анализа корреляций между ошибками
"""

import json
import os
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict, Counter
import math
from datetime import datetime, timezone

from core.bayesian_technical_utils import analyze_technical_aspects_common
from core.bayesian_recommendations import (
    get_recommendations,
    get_error_type_key,
    get_symptom_key,
    DEFAULT_LANGUAGE,
)

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Результат выполнения теста."""

    __test__ = False  # Tell pytest this is not a test class

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ErrorType(Enum):
    """Типы ошибок в тестах."""

    ASSERTION_ERROR = "assertion_error"
    IMPORT_ERROR = "import_error"
    TYPE_ERROR = "type_error"
    ATTRIBUTE_ERROR = "attribute_error"
    VALUE_ERROR = "value_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT_ERROR = "timeout_error"
    COVERAGE_ERROR = "coverage_error"
    MOCK_ERROR = "mock_error"
    ASYNC_ERROR = "async_error"


class TestCategory(Enum):
    """Категории тестов."""

    __test__ = False  # Tell pytest this is not a test class

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    COVERAGE = "coverage"
    MONTE_CARLO = "monte_carlo"
    BAYESIAN = "bayesian"


@dataclass
class TestRecord:
    """Запись о выполнении теста."""

    __test__ = False  # Tell pytest this is not a test class

    test_name: str
    category: TestCategory
    result: TestStatus
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    coverage_percentage: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dependencies: List[str] = field(default_factory=list)
    file_path: str = ""
    line_number: Optional[int] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class BayesianDiagnosis:
    """Байесовский диагноз проблемы."""

    most_likely_cause: str
    probability: float
    confidence: float
    evidence: List[str]
    recommendations: List[str]
    alternative_causes: List[Tuple[str, float]]


class BayesianTestAnalyzer:
    """
    Байесовский анализатор тестов для PulsePlate.

    Использует теорему Байеса для:
    P(причина|симптомы) = P(симптомы|причина) * P(причина) / P(симптомы)
    """

    def __init__(self, data_file: Optional[Path] = None, language: Optional[str] = None) -> None:
        """
        Инициализация анализатора.

        Args:
            data_file: Путь к файлу истории выполнения тестов.
            language: Код языка для рекомендаций (ru/en/es). По умолчанию используется DEFAULT_LANGUAGE.
        """
        # Управление персистентностью истории:
        # Если явно передан data_file в конструктор (как в тестах), считаем, что запись включена.
        truthy = {"1", "true", "yes", "on"}
        if data_file is not None:
            self.persist_enabled = True
            self.data_file = Path(data_file)
        else:
            self.persist_enabled = os.getenv("BAYESIAN_PERSIST", "0").strip().lower() in truthy
            history_path = os.getenv("BAYESIAN_HISTORY_PATH", "test_execution_history.json").strip()
            self.data_file = (
                Path(history_path) if history_path else Path("test_execution_history.json")
            )

        # Language configuration for recommendations
        self.language = language or os.getenv("BAYESIAN_LANGUAGE", DEFAULT_LANGUAGE).strip().lower()

        self.execution_history: List[TestRecord] = []
        self.error_patterns: Dict[ErrorType, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self.test_correlations: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self.coverage_patterns: Dict[str, List[float]] = defaultdict(list)

        # Априорные вероятности на основе опыта (могут быть адаптированы из истории)
        self.prior_probabilities = {
            ErrorType.ASSERTION_ERROR: 0.25,
            ErrorType.IMPORT_ERROR: 0.15,
            ErrorType.TYPE_ERROR: 0.20,
            ErrorType.ATTRIBUTE_ERROR: 0.15,
            ErrorType.VALUE_ERROR: 0.10,
            ErrorType.RUNTIME_ERROR: 0.10,
            ErrorType.TIMEOUT_ERROR: 0.03,
            ErrorType.COVERAGE_ERROR: 0.02,
            ErrorType.MOCK_ERROR: 0.15,
            ErrorType.ASYNC_ERROR: 0.10,
        }
        # Нормализуем вероятности, чтобы сумма была равна 1.0
        # Use epsilon to guard against very small sums that could produce extreme weights
        EPSILON = 1e-12
        prior_sum = sum(self.prior_probabilities.values())
        if prior_sum <= EPSILON:
            # Fallback to uniform distribution when sum is too small
            uniform_weight = 1.0 / len(ErrorType)
            self.prior_probabilities = {error_type: uniform_weight for error_type in ErrorType}
        else:
            self.prior_probabilities = {
                error_type: weight / prior_sum
                for error_type, weight in self.prior_probabilities.items()
            }

        self.load_history()

    def _calculate_recency_weight(
        self, timestamp: datetime, half_life_hours: float = 24 * 7
    ) -> float:
        """
        Calculate recency weight for a timestamp using exponential decay.

        Args:
            timestamp: The timestamp to calculate weight for
            half_life_hours: Half-life in hours (default: 1 week = 168 hours)

        Returns:
            Weight value between 0.0 and 1.0, with 1.0 for recent timestamps
            and exponential decay for older ones. Returns 1.0 on any exception.
        """
        try:
            now = datetime.now(timezone.utc)
            age_hours = max(0.0, (now - timestamp).total_seconds() / 3600.0)
            # Exponential decay: w = 0.5 ** (age / half_life)
            weight: float = 0.5 ** (age_hours / half_life_hours)
            return weight
        except Exception:
            return 1.0

    def load_history(self) -> None:
        """Загрузить историю выполнения тестов."""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.execution_history = [
                        TestRecord(
                            test_name=item["test_name"],
                            category=TestCategory(item["category"]),
                            result=TestStatus(item["result"]),
                            error_type=(
                                ErrorType(item["error_type"]) if item.get("error_type") else None
                            ),
                            error_message=item.get("error_message"),
                            execution_time=item.get("execution_time", 0.0),
                            coverage_percentage=item.get("coverage_percentage"),
                            timestamp=datetime.fromisoformat(item["timestamp"]),
                            dependencies=item.get("dependencies", []),
                            file_path=item.get("file_path", ""),
                            line_number=item.get("line_number"),
                        )
                        for item in data
                    ]
                logger.info(f"Загружено {len(self.execution_history)} записей истории тестов")
                # Адаптировать приоры на базе истории
                self._refresh_priors_from_history()
        except Exception as e:
            logger.warning(f"Не удалось загрузить историю тестов: {e}")

    def save_history(self) -> None:
        """Сохранить историю выполнения тестов."""
        # В CI по умолчанию отключаем запись истории, чтобы избежать нестабильных тестов и гонок
        if not self.persist_enabled:
            return
        try:
            data = []
            for execution in self.execution_history:
                item = asdict(execution)
                item["timestamp"] = execution.timestamp.isoformat()
                item["category"] = execution.category.value
                item["result"] = execution.result.value
                if execution.error_type:
                    item["error_type"] = execution.error_type.value
                data.append(item)

            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Сохранено {len(self.execution_history)} записей истории тестов")
        except Exception as e:
            logger.error(f"Ошибка сохранения истории тестов: {e}")

    def record_test_execution(self, execution: TestRecord) -> None:
        """Записать выполнение теста."""
        self.execution_history.append(execution)
        self._update_patterns(execution)
        # Адаптировать приоры после нового наблюдения
        self._refresh_priors_from_history()
        self.save_history()

    def _update_patterns(self, execution: TestRecord) -> None:
        """Обновить паттерны ошибок и корреляций."""
        if execution.result == TestStatus.FAILED and execution.error_type:
            # Обновить паттерны ошибок
            error_key = f"{execution.category.value}_{execution.file_path}"
            self.error_patterns[execution.error_type][error_key] += 1

            # Обновить корреляции между тестами
            for other_execution in self.execution_history[-10:]:  # Последние 10 тестов
                if (
                    other_execution.test_name != execution.test_name
                    and other_execution.result == TestStatus.FAILED
                ):
                    self.test_correlations[execution.test_name][other_execution.test_name] += 1

        # Обновить паттерны покрытия
        if execution.coverage_percentage is not None:
            self.coverage_patterns[execution.test_name].append(execution.coverage_percentage)

    def diagnose_test_failure(
        self, test_name: str, error_message: str, context: Optional[Dict[str, Any]] = None
    ) -> BayesianDiagnosis:
        """
        Диагностировать причину падения теста с использованием теоремы Байеса.

        P(причина|симптомы) = P(симптомы|причина) * P(причина) / P(симптомы)
        """
        if context is None:
            context = {}

        # Извлечь симптомы из сообщения об ошибке
        symptoms = self._extract_symptoms(error_message, context)

        # Найти исторические случаи с похожими симптомами
        similar_cases = self._find_similar_cases(symptoms)

        # Вычислить байесовские вероятности для каждой возможной причины
        cause_probabilities = {}

        for error_type in ErrorType:
            # P(причина) - априорная вероятность
            prior = self.prior_probabilities[error_type]

            # P(симптомы|причина) - вероятность симптомов при данной причине
            likelihood = self._calculate_likelihood(symptoms, error_type, similar_cases)

            # P(симптомы) - общая вероятность симптомов (нормализация Байеса)
            evidence = self._calculate_evidence(symptoms, similar_cases)

            # P(причина|симптомы) = P(симптомы|причина) * P(причина) / P(симптомы)
            if evidence > 0:
                posterior = (likelihood * prior) / evidence
                # Ограничить вероятность до 1.0
                cause_probabilities[error_type] = min(1.0, posterior)
        # Найти наиболее вероятную причину
        most_likely_cause = max(cause_probabilities.items(), key=lambda x: x[1])

        # Вычислить уверенность (энтропия распределения)
        confidence = self._calculate_confidence(cause_probabilities)

        # Собрать доказательства (список строк)
        evidence_list = self._gather_evidence(symptoms, most_likely_cause[0], similar_cases)

        # Сгенерировать рекомендации
        recommendations = self._generate_recommendations(most_likely_cause[0], symptoms, context)

        # Альтернативные причины
        alternative_causes = sorted(
            [
                (cause.value, prob)
                for cause, prob in cause_probabilities.items()
                if cause != most_likely_cause[0] and prob > 0.1
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        return BayesianDiagnosis(
            most_likely_cause=most_likely_cause[0].value,
            probability=most_likely_cause[1],
            confidence=confidence,
            evidence=evidence_list,
            recommendations=recommendations,
            alternative_causes=alternative_causes,
        )

    def _extract_symptoms(self, error_message: str, context: Dict[str, Any]) -> Set[str]:
        """Извлечь симптомы из сообщения об ошибке."""
        symptoms = set()

        # Ключевые слова для разных типов ошибок
        error_keywords = {
            "assertion": ["AssertionError", "assert", "expected", "actual"],
            "import": ["ImportError", "ModuleNotFoundError", "No module named"],
            "type": ["TypeError", "unexpected keyword argument", "missing required"],
            "attribute": ["AttributeError", "has no attribute", "object has no attribute"],
            "value": ["ValueError", "invalid value", "out of range"],
            "runtime": ["RuntimeError", "runtime error"],
            "timeout": ["TimeoutError", "timeout", "deadline exceeded"],
            "coverage": ["coverage", "below threshold", "insufficient coverage"],
            "mock": ["Mock", "MagicMock", "AsyncMock", "patch"],
            "async": ["asyncio", "await", "async", "coroutine"],
        }

        error_lower = error_message.lower()
        for error_type, keywords in error_keywords.items():
            if any(keyword.lower() in error_lower for keyword in keywords):
                symptoms.add(error_type)

        # Добавить контекстные симптомы
        if context.get("is_async", False):
            symptoms.add("async_context")
        if context.get("has_mocks", False):
            symptoms.add("mock_context")
        if context.get("coverage_below_threshold", False):
            symptoms.add("coverage_context")

        return symptoms

    def _find_similar_cases(self, symptoms: Set[str]) -> List[TestRecord]:
        """Найти похожие случаи в истории."""
        similar_cases = []

        for execution in self.execution_history:
            if execution.result == TestStatus.FAILED and execution.error_type:
                case_symptoms = self._extract_symptoms(execution.error_message or "", {})

                # Вычислить схожесть симптомов (Jaccard), безопасно обрабатывая пустое объединение
                union_size = len(symptoms.union(case_symptoms))
                if union_size == 0:
                    similarity = 0.0
                else:
                    similarity = len(symptoms.intersection(case_symptoms)) / union_size

                if similarity > 0.3:  # Порог схожести
                    similar_cases.append(execution)

        return similar_cases

    def _calculate_likelihood(
        self, symptoms: Set[str], error_type: ErrorType, similar_cases: List[TestRecord]
    ) -> float:
        """Вычислить P(симптомы|причина) с учетом сглаживания и давности."""
        # Если нет истории — возвращаем сглаженную базу
        if not self.execution_history:
            return 0.1

        # Параметры сглаживания и давности
        alpha = 1.0  # Laplace smoothing
        half_life_hours = 24 * 7  # полураспад 1 неделя

        # Все случаи данного типа
        type_all = [case for case in self.execution_history if case.error_type == error_type]
        if not type_all:
            return 0.1

        # Совпадение симптомов считаем близостью (Jaccard) > 0.3
        def symptoms_similarity(msg: str) -> float:
            case_sy = self._extract_symptoms(msg or "", {})
            if not case_sy and not symptoms:
                return 1.0
            inter = len(symptoms.intersection(case_sy))
            # Union is guaranteed to be non-zero here (both sets empty case handled above)
            union = len(symptoms.union(case_sy))
            return inter / union

        # Взвешенные суммы
        weighted_num = 0.0
        weighted_den = 0.0
        for case in type_all:
            w = self._calculate_recency_weight(case.timestamp, half_life_hours)
            sim = symptoms_similarity(case.error_message or "")
            weighted_num += w * (1.0 if sim >= 0.3 else 0.0)
            weighted_den += w

        # Laplace smoothing — избегаем крайностей 0/1
        prob = (weighted_num + alpha) / (weighted_den + 2 * alpha)
        return float(max(0.01, min(0.99, prob)))

    def _calculate_evidence(self, symptoms: Set[str], similar_cases: List[TestRecord]) -> float:
        """Вычислить P(симптомы) = Σ_e P(симптомы|e)·P(e)."""
        if not symptoms:
            return 1.0

        # Оценка нормализатора по формуле полной вероятности
        total = 0.0
        # Нормируем приоры на всякий случай
        prior_sum = sum(self.prior_probabilities.values()) or 1.0
        for error_type in ErrorType:
            prior = self.prior_probabilities.get(error_type, 0.0) / prior_sum
            like = self._calculate_likelihood(symptoms, error_type, similar_cases)
            total += like * prior

        # Минимальный нижний порог, чтобы избежать деления на ~0
        return max(1e-6, min(1.0, total))

    def _calculate_confidence(self, probabilities: Dict[ErrorType, float]) -> float:
        """Вычислить уверенность в диагнозе (обратная энтропия)."""
        if not probabilities:
            return 0.0

        # Нормализовать вероятности
        total = sum(probabilities.values())
        if total == 0:
            return 0.0

        normalized = {k: v / total for k, v in probabilities.items()}

        # Вычислить энтропию
        entropy = -sum(p * math.log2(p) if p > 0 else 0 for p in normalized.values())

        # Уверенность = 1 - нормализованная энтропия
        max_entropy = math.log2(len(normalized))
        if max_entropy == 0:
            return 1.0

        return 1.0 - (entropy / max_entropy)

    def _gather_evidence(
        self, symptoms: Set[str], error_type: ErrorType, similar_cases: List[TestRecord]
    ) -> List[str]:
        """Собрать доказательства для диагноза."""
        evidence = []

        # Статистика по типу ошибки
        type_cases = [case for case in self.execution_history if case.error_type == error_type]
        evidence.append(f"Найдено {len(type_cases)} случаев {error_type.value} в истории")

        # Похожие случаи
        evidence.append(f"Найдено {len(similar_cases)} похожих случаев")

        # Частые файлы с данным типом ошибки
        file_counts = Counter(case.file_path for case in type_cases)
        if file_counts:
            most_common_file = file_counts.most_common(1)[0]
            evidence.append(
                f"Чаще всего {error_type.value} встречается в {most_common_file[0]} ({most_common_file[1]} раз)"
            )

        # Симптомы
        evidence.append(f"Обнаружены симптомы: {', '.join(symptoms)}")

        return evidence

    def _generate_recommendations(
        self, error_type: ErrorType, symptoms: Set[str], context: Dict[str, Any]
    ) -> List[str]:
        """
        Сгенерировать рекомендации по исправлению.

        Использует централизованную конфигурацию рекомендаций из bayesian_recommendations
        с поддержкой интернационализации.

        Args:
            error_type: Тип ошибки.
            symptoms: Множество симптомов.
            context: Контекстная информация (не используется, но сохранен для совместимости).

        Returns:
            Список рекомендаций по исправлению.
        """
        recommendations = []

        # Получаем рекомендации для типа ошибки
        error_key = get_error_type_key(error_type)
        error_recommendations = get_recommendations(
            error_key, language=self.language, fallback=[f"Review {error_type.value}"]
        )
        recommendations.extend(error_recommendations)

        # Получаем контекстные рекомендации на основе симптомов
        for symptom in symptoms:
            symptom_key = get_symptom_key(symptom)
            symptom_recommendations = get_recommendations(
                symptom_key, language=self.language, fallback=[]
            )
            recommendations.extend(symptom_recommendations)

        return recommendations

    def _refresh_priors_from_history(self) -> None:
        """Адаптировать априорные вероятности по истории с учетом давности.

        Использует экспоненциальное взвешивание по времени и Laplace smoothing,
        затем смешивает с исходными приорами (50/50), чтобы избежать резких скачков.
        """
        if not self.execution_history:
            return

        # Взвешивание по давности
        half_life_hours = 24 * 7

        # Считаем только падения с указанным типом ошибки
        weighted_counts: Dict[ErrorType, float] = {et: 0.0 for et in ErrorType}
        total_weight = 0.0
        for exec in self.execution_history:
            if exec.result == TestStatus.FAILED and exec.error_type is not None:
                w = self._calculate_recency_weight(exec.timestamp, half_life_hours)
                weighted_counts[exec.error_type] = weighted_counts.get(exec.error_type, 0.0) + w
                total_weight += w

        if total_weight <= 0:
            return

        # Laplace smoothing
        alpha = 1.0
        k = len(ErrorType)
        hist_priors: Dict[ErrorType, float] = {}
        for et in ErrorType:
            count = weighted_counts.get(et, 0.0)
            hist_priors[et] = (count + alpha) / (total_weight + alpha * k)

        # Смешиваем с текущими приорами
        current_sum = sum(self.prior_probabilities.values()) or 1.0
        blended: Dict[ErrorType, float] = {}
        for et in ErrorType:
            base = self.prior_probabilities.get(et, 0.0) / current_sum
            blended[et] = 0.5 * base + 0.5 * hist_priors[et]

        # Денормализуем обратно к удобным относительным весам
        # (внутренние функции все равно нормализуют по сумме)
        for et in ErrorType:
            self.prior_probabilities[et] = blended[et]

    def predict_test_failure_probability(
        self, test_name: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Предсказать вероятность падения теста."""
        if context is None:
            context = {}

        # Найти исторические данные по тесту
        test_history = [exec for exec in self.execution_history if exec.test_name == test_name]

        if not test_history:
            return 0.1  # Базовая вероятность для новых тестов

        # Вычислить частоту падений
        failure_count = sum(exec.result == TestStatus.FAILED for exec in test_history)
        total_count = len(test_history)

        base_probability = failure_count / total_count

        # Корректировка на основе контекста
        context_factor = 1.0

        if context.get("recent_changes", False):
            context_factor *= 1.5  # Увеличить вероятность при недавних изменениях

        if context.get("complex_dependencies", False):
            context_factor *= 1.3  # Увеличить при сложных зависимостях

        if context.get("async_test", False):
            context_factor *= 1.2  # Асинхронные тесты более склонны к ошибкам

        return min(1.0, base_probability * context_factor)

    def optimize_test_order(self, test_list: List[str]) -> List[str]:
        """Оптимизировать порядок выполнения тестов для быстрого выявления проблем."""
        # Сортировать по вероятности падения (сначала наиболее вероятные)
        test_probabilities = [
            (test, self.predict_test_failure_probability(test)) for test in test_list
        ]

        # Сортировать по убыванию вероятности
        sorted_tests = sorted(test_probabilities, key=lambda x: x[1], reverse=True)

        return [test for test, _ in sorted_tests]

    def get_test_health_score(self, test_name: str) -> float:
        """Получить оценку здоровья теста (0-1, где 1 = идеально)."""
        test_history = [exec for exec in self.execution_history if exec.test_name == test_name]

        if not test_history:
            return 0.5  # Нейтральная оценка для новых тестов

        # Факторы здоровья
        success_rate = sum(exec.result == TestStatus.PASSED for exec in test_history) / len(
            test_history
        )

        # Стабильность покрытия
        coverage_scores = [
            exec.coverage_percentage
            for exec in test_history
            if exec.coverage_percentage is not None
        ]

        if coverage_scores:
            coverage_stability = 1.0 - (max(coverage_scores) - min(coverage_scores)) / 100.0
        else:
            coverage_stability = 1.0

        # Время выполнения (стабильность)
        execution_times = [exec.execution_time for exec in test_history if exec.execution_time > 0]

        if execution_times and len(execution_times) > 1:
            avg_time = sum(execution_times) / len(execution_times)
            # Guard against division by zero: only compute stability if avg_time > 0
            if avg_time > 0:
                time_variance = sum((t - avg_time) ** 2 for t in execution_times) / len(
                    execution_times
                )
                time_stability = 1.0 / (1.0 + time_variance / (avg_time**2))
            else:
                time_stability = 1.0  # Safe default for near-zero average time
        else:
            time_stability = 1.0

        # Взвешенная оценка
        health_score = success_rate * 0.5 + coverage_stability * 0.3 + time_stability * 0.2

        return max(0.0, min(1.0, health_score))

    def generate_test_report(self) -> Dict[str, Any]:
        """Сгенерировать отчет о состоянии тестов."""
        if not self.execution_history:
            return {"message": "Нет данных для анализа"}

        # Общая статистика
        total_tests = len(self.execution_history)
        passed_tests = sum(exec.result == TestStatus.PASSED for exec in self.execution_history)
        failed_tests = sum(exec.result == TestStatus.FAILED for exec in self.execution_history)

        # Статистика по типам ошибок
        error_stats = Counter(
            exec.error_type for exec in self.execution_history if exec.error_type is not None
        )

        # Самые проблемные тесты
        test_failures = Counter(
            exec.test_name for exec in self.execution_history if exec.result == TestStatus.FAILED
        )

        # Рекомендации по улучшению
        recommendations = []

        if failed_tests / total_tests > 0.1:
            recommendations.append(
                "Высокий процент падающих тестов - пересмотрите стратегию тестирования"
            )

        # Explicit handling of most common error to avoid confusion about None vs tuple
        most_common_error: tuple[ErrorType, int] | None = None
        if error_stats:
            most_common_list = error_stats.most_common(1)
            if most_common_list:
                most_common_error = most_common_list[0]  # Tuple[ErrorType, int]

        if most_common_error is not None:
            error, count = most_common_error
            if count > total_tests * 0.05:
                recommendations.append(f"Частая ошибка {error.value} - создайте общее решение")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "error_types": {error.value: count for error, count in error_stats.items()},
            "most_problematic_tests": test_failures.most_common(5),
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _analyze_technical_aspects(self, code: str, test_name: str) -> List[str]:
        """Анализирует технические аспекты теста."""
        return analyze_technical_aspects_common(code, test_name)

    def analyze_technical_aspects(self, code: str, test_name: str) -> List[str]:
        """Public wrapper for analyzing technical aspects of a test.

        Delegates to the internal implementation to preserve behavior.
        """
        return self._analyze_technical_aspects(code, test_name)


# Глобальный экземпляр анализатора
bayesian_analyzer = BayesianTestAnalyzer()


def diagnose_test_failure(
    test_name: str, error_message: str, context: Optional[Dict[str, Any]] = None
) -> BayesianDiagnosis:
    """Удобная функция для диагностики падения теста."""
    return bayesian_analyzer.diagnose_test_failure(test_name, error_message, context)


def record_test_execution(
    test_name: str,
    category: TestCategory,
    result: TestStatus,
    error_type: Optional[ErrorType] = None,
    error_message: Optional[str] = None,
    execution_time: float = 0.0,
    coverage_percentage: Optional[float] = None,
    file_path: str = "",
    line_number: Optional[int] = None,
) -> None:
    """Удобная функция для записи выполнения теста."""
    execution = TestRecord(
        test_name=test_name,
        category=category,
        result=result,
        error_type=error_type,
        error_message=error_message,
        execution_time=execution_time,
        coverage_percentage=coverage_percentage,
        file_path=file_path,
        line_number=line_number,
    )
    bayesian_analyzer.record_test_execution(execution)

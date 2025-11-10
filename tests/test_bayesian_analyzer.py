"""
Тесты для байесовской системы анализа тестов.
"""

import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from core.bayesian_recommendations import (
    get_all_error_type_keys,
    get_all_symptom_keys,
    get_error_type_key,
    get_recommendations,
    get_symptom_key,
)
from core.bayesian_test_analyzer import (
    BayesianDiagnosis,
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestRecord,
    TestStatus,
    diagnose_test_failure,
    record_test_execution,
)


class TestBayesianTestAnalyzer:
    """Тесты для BayesianTestAnalyzer."""

    @pytest.fixture
    def temp_data_file(self) -> Iterator[Path]:
        """Временный файл для данных."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)

    @pytest.fixture
    def analyzer(self, temp_data_file: Path) -> BayesianTestAnalyzer:
        """Создать анализатор с временным файлом данных."""
        return BayesianTestAnalyzer(data_file=temp_data_file)

    def test_init(self, analyzer) -> None:
        """Тест инициализации анализатора."""
        assert analyzer.data_file is not None
        assert len(analyzer.execution_history) == 0
        assert len(analyzer.prior_probabilities) > 0

    def test_record_test_execution(self, analyzer) -> None:
        """Тест записи выполнения теста."""
        execution = TestRecord(
            test_name="test_example",
            category=TestCategory.UNIT,
            result=TestStatus.PASSED,
            execution_time=1.5,
            coverage_percentage=95.0,
        )

        analyzer.record_test_execution(execution)

        assert len(analyzer.execution_history) == 1
        assert analyzer.execution_history[0].test_name == "test_example"
        assert analyzer.execution_history[0].result == TestStatus.PASSED

    def test_save_and_load_history(self, analyzer, temp_data_file) -> None:
        """Тест сохранения и загрузки истории."""
        # Добавить тестовые данные
        execution1 = TestRecord(
            test_name="test_1", category=TestCategory.UNIT, result=TestStatus.PASSED
        )
        execution2 = TestRecord(
            test_name="test_2",
            category=TestCategory.INTEGRATION,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            error_message="Assertion failed",
        )

        analyzer.record_test_execution(execution1)
        analyzer.record_test_execution(execution2)

        # Создать новый анализатор и загрузить данные
        new_analyzer = BayesianTestAnalyzer(data_file=temp_data_file)

        assert len(new_analyzer.execution_history) == 2
        assert new_analyzer.execution_history[0].test_name == "test_1"
        assert new_analyzer.execution_history[1].error_type == ErrorType.ASSERTION_ERROR

    def test_extract_symptoms(self, analyzer) -> None:
        """Тест извлечения симптомов из сообщения об ошибке."""
        error_message = "AssertionError: Expected 'hello' but got 'world'"
        context = {"is_async": True, "has_mocks": False}

        symptoms = analyzer._extract_symptoms(error_message, context)

        assert "assertion" in symptoms
        assert "async_context" in symptoms
        assert "mock_context" not in symptoms

    def test_calculate_likelihood(self, analyzer) -> None:
        """Тест вычисления правдоподобия."""
        # Добавить тестовые данные
        execution = TestRecord(
            test_name="test_example",
            category=TestCategory.UNIT,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            error_message="Assertion failed",
        )
        analyzer.record_test_execution(execution)

        symptoms = {"assertion"}
        similar_cases = [execution]

        likelihood = analyzer._calculate_likelihood(
            symptoms, ErrorType.ASSERTION_ERROR, similar_cases
        )

        assert 0 <= likelihood <= 1

    def test_calculate_confidence(self, analyzer) -> None:
        """Тест вычисления уверенности."""
        probabilities = {
            ErrorType.ASSERTION_ERROR: 0.8,
            ErrorType.TYPE_ERROR: 0.1,
            ErrorType.IMPORT_ERROR: 0.1,
        }

        confidence = analyzer._calculate_confidence(probabilities)

        assert 0 <= confidence <= 1
        # Уверенность должна быть разумной
        assert confidence > 0.3

    def test_diagnose_test_failure(self, analyzer) -> None:
        """Тест диагностики падения теста."""
        # Добавить исторические данные
        execution = TestRecord(
            test_name="test_similar",
            category=TestCategory.UNIT,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            error_message="AssertionError: Expected value",
        )
        analyzer.record_test_execution(execution)

        diagnosis = analyzer.diagnose_test_failure(
            "test_new", "AssertionError: Expected 'hello' but got 'world'", {"is_async": False}
        )

        assert isinstance(diagnosis, BayesianDiagnosis)
        assert diagnosis.most_likely_cause is not None
        assert 0 <= diagnosis.probability <= 1
        assert 0 <= diagnosis.confidence <= 1
        assert len(diagnosis.evidence) > 0
        assert len(diagnosis.recommendations) > 0

    def test_predict_test_failure_probability(self, analyzer) -> None:
        """Тест предсказания вероятности падения теста."""
        # Добавить исторические данные
        execution1 = TestRecord(
            test_name="test_example", category=TestCategory.UNIT, result=TestStatus.PASSED
        )
        execution2 = TestRecord(
            test_name="test_example",
            category=TestCategory.UNIT,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
        )
        analyzer.record_test_execution(execution1)
        analyzer.record_test_execution(execution2)

        probability = analyzer.predict_test_failure_probability("test_example")

        assert 0 <= probability <= 1
        # Вероятность должна быть около 0.5 (1 из 2 тестов упал)
        assert 0.4 <= probability <= 0.6

    def test_optimize_test_order(self, analyzer) -> None:
        """Тест оптимизации порядка тестов."""
        test_list = ["test_a", "test_b", "test_c"]

        # Добавить данные о падениях
        execution = TestRecord(
            test_name="test_b",
            category=TestCategory.UNIT,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
        )
        analyzer.record_test_execution(execution)

        optimized_order = analyzer.optimize_test_order(test_list)

        assert len(optimized_order) == len(test_list)
        assert set(optimized_order) == set(test_list)
        # test_b должен быть первым (наиболее вероятно упадет)
        assert optimized_order[0] == "test_b"

    def test_get_test_health_score(self, analyzer) -> None:
        """Тест получения оценки здоровья теста."""
        # Добавить успешные выполнения
        for i in range(5):
            execution = TestRecord(
                test_name="test_healthy",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
                execution_time=1.0,
                coverage_percentage=95.0,
            )
            analyzer.record_test_execution(execution)

        health_score = analyzer.get_test_health_score("test_healthy")

        assert 0 <= health_score <= 1
        # Здоровый тест должен иметь высокую оценку
        assert health_score > 0.8

    def test_generate_test_report(self, analyzer) -> None:
        """Тест генерации отчета о тестах."""
        # Добавить тестовые данные
        execution1 = TestRecord(
            test_name="test_1", category=TestCategory.UNIT, result=TestStatus.PASSED
        )
        execution2 = TestRecord(
            test_name="test_2",
            category=TestCategory.UNIT,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
        )
        analyzer.record_test_execution(execution1)
        analyzer.record_test_execution(execution2)

        report = analyzer.generate_test_report()

        assert "total_tests" in report
        assert "passed_tests" in report
        assert "failed_tests" in report
        assert "success_rate" in report
        assert "error_types" in report
        assert "recommendations" in report

        assert report["total_tests"] == 2
        assert report["passed_tests"] == 1
        assert report["failed_tests"] == 1
        assert report["success_rate"] == 0.5

    def test_predict_test_failure_probability_no_history(self, analyzer) -> None:
        """Test predict_test_failure_probability for a test with no history."""
        probability = analyzer.predict_test_failure_probability("test_no_history")
        # Default probability for new tests with no history is 0.1
        assert probability == 0.1

    def test_optimize_test_order_equal_probability(self, analyzer) -> None:
        """Тест оптимизации порядка тестов при равной вероятности падения."""
        test_list = ["test_x", "test_y", "test_z"]

        # Не добавляем данные о падениях — все тесты равны
        optimized_order = analyzer.optimize_test_order(test_list)

        assert len(optimized_order) == len(test_list)
        assert set(optimized_order) == set(test_list)
        # Порядок должен быть исходным, так как все вероятности равны
        assert optimized_order == test_list

    def test_generate_test_report_empty_history(self, analyzer) -> None:
        """Test generate_test_report with empty history returns default report."""
        report = analyzer.generate_test_report()
        # Default report when no executions are recorded
        assert report == {"message": "Нет данных для анализа"}

    def test_gather_evidence(self, analyzer) -> None:
        """Тест сбора доказательств."""
        # Добавить тестовые данные
        execution = TestRecord(
            test_name="test_example",
            category=TestCategory.UNIT,
            result=TestStatus.FAILED,
            error_type=ErrorType.ASSERTION_ERROR,
            error_message="Assertion failed",
            file_path="test_file.py",
        )
        analyzer.record_test_execution(execution)

        symptoms = {"assertion"}
        similar_cases = [execution]

        evidence = analyzer._gather_evidence(symptoms, ErrorType.ASSERTION_ERROR, similar_cases)

        assert len(evidence) > 0
        assert any("assertion_error" in item for item in evidence)
        assert any("test_file.py" in item for item in evidence)

    def test_generate_recommendations(self, analyzer) -> None:
        """Тест генерации рекомендаций."""
        symptoms = {"assertion", "async_context"}
        context = {"is_async": True}

        recommendations = analyzer._generate_recommendations(
            ErrorType.ASSERTION_ERROR, symptoms, context
        )

        assert len(recommendations) > 0
        assert any("assert" in rec.lower() for rec in recommendations)
        # Проверим, что есть рекомендации для асинхронного контекста
        assert any("асинхронную" in rec.lower() for rec in recommendations)


class TestBayesianDiagnosis:
    """Тесты для BayesianDiagnosis."""

    def test_init(self) -> None:
        """Тест инициализации диагноза."""
        diagnosis = BayesianDiagnosis(
            most_likely_cause="assertion_error",
            probability=0.8,
            confidence=0.9,
            evidence=["Test failed with assertion"],
            recommendations=["Check assertions"],
            alternative_causes=[("type_error", 0.1)],
        )

        assert diagnosis.most_likely_cause == "assertion_error"
        assert diagnosis.probability == 0.8
        assert diagnosis.confidence == 0.9
        assert len(diagnosis.evidence) == 1
        assert len(diagnosis.recommendations) == 1
        assert len(diagnosis.alternative_causes) == 1


class TestConvenienceFunctions:
    """Тесты для удобных функций."""

    @pytest.fixture
    def temp_data_file(self) -> Iterator[Path]:
        """Временный файл для данных."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)

    @pytest.fixture
    def analyzer(self, temp_data_file: Path) -> BayesianTestAnalyzer:
        """Создать анализатор с временным файлом данных."""
        return BayesianTestAnalyzer(data_file=temp_data_file)

    def test_diagnose_test_failure_function(self) -> None:
        """Тест функции diagnose_test_failure."""
        diagnosis = diagnose_test_failure(
            "test_example", "AssertionError: Expected value", {"is_async": False}
        )

        assert isinstance(diagnosis, BayesianDiagnosis)
        assert diagnosis.most_likely_cause is not None

    def test_record_test_execution_function(self, analyzer: BayesianTestAnalyzer) -> None:
        """Тест функции record_test_execution с использованием изолированного fixture."""
        # Очистить историю перед тестом для изоляции
        analyzer.execution_history.clear()

        # Мокаем глобальный bayesian_analyzer, чтобы использовать наш изолированный fixture
        from unittest.mock import patch

        from core import bayesian_test_analyzer

        with patch.object(bayesian_test_analyzer, "bayesian_analyzer", analyzer):
            # Вызываем функцию record_test_execution, которая теперь использует наш fixture
            record_test_execution(
                test_name="test_example",
                category=TestCategory.UNIT,
                result=TestStatus.PASSED,
            )

        # Проверить, что данные записались в изолированную фикстуру
        assert len(analyzer.execution_history) == 1
        assert analyzer.execution_history[0].test_name == "test_example"
        assert analyzer.execution_history[0].result == TestStatus.PASSED
        assert analyzer.execution_history[0].category == TestCategory.UNIT


class TestErrorTypeEnum:
    """Тесты для перечисления ErrorType."""

    def test_error_types(self) -> None:
        """Тест всех типов ошибок."""
        error_types = [
            ErrorType.ASSERTION_ERROR,
            ErrorType.IMPORT_ERROR,
            ErrorType.TYPE_ERROR,
            ErrorType.ATTRIBUTE_ERROR,
            ErrorType.VALUE_ERROR,
            ErrorType.RUNTIME_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.COVERAGE_ERROR,
            ErrorType.MOCK_ERROR,
            ErrorType.ASYNC_ERROR,
        ]

        assert len(error_types) == 10
        for error_type in error_types:
            assert error_type.value is not None
            assert isinstance(error_type.value, str)


class TestTestCategoryEnum:
    """Тесты для перечисления TestCategory."""

    def test_test_categories(self) -> None:
        """Тест всех категорий тестов."""
        categories = [
            TestCategory.UNIT,
            TestCategory.INTEGRATION,
            TestCategory.E2E,
            TestCategory.PERFORMANCE,
            TestCategory.COVERAGE,
            TestCategory.MONTE_CARLO,
            TestCategory.BAYESIAN,
        ]

        assert len(categories) == 7
        for category in categories:
            assert category.value is not None
            assert isinstance(category.value, str)


class TestTestStatusEnum:
    """Тесты для перечисления TestStatus."""

    def test_test_results(self) -> None:
        """Тест всех результатов тестов."""
        results = [TestStatus.PASSED, TestStatus.FAILED, TestStatus.SKIPPED, TestStatus.ERROR]

        assert len(results) == 4
        for result in results:
            assert result.value is not None
            assert isinstance(result.value, str)


class TestIntegration:
    """Интеграционные тесты."""

    def test_full_workflow(self) -> None:
        """Тест полного рабочего процесса."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            analyzer = BayesianTestAnalyzer(data_file=temp_path)

            # 1. Записать несколько выполнений тестов
            executions = [
                TestRecord("test_1", TestCategory.UNIT, TestStatus.PASSED),
                TestRecord(
                    "test_2",
                    TestCategory.UNIT,
                    TestStatus.FAILED,
                    ErrorType.ASSERTION_ERROR,
                    "Assertion failed",
                ),
                TestRecord("test_3", TestCategory.INTEGRATION, TestStatus.PASSED),
                TestRecord(
                    "test_2",
                    TestCategory.UNIT,
                    TestStatus.FAILED,
                    ErrorType.TYPE_ERROR,
                    "Type error",
                ),
            ]

            for execution in executions:
                analyzer.record_test_execution(execution)

            # 2. Диагностировать новую ошибку
            diagnosis = analyzer.diagnose_test_failure(
                "test_new", "AssertionError: Expected 'hello' but got 'world'"
            )

            assert diagnosis.most_likely_cause is not None

            # 3. Предсказать вероятность падения
            probability = analyzer.predict_test_failure_probability("test_2")
            assert 0 <= probability <= 1

            # 4. Оптимизировать порядок тестов
            test_list = ["test_1", "test_2", "test_3", "test_new"]
            optimized = analyzer.optimize_test_order(test_list)
            assert len(optimized) == len(test_list)

            # 5. Получить отчет
            report = analyzer.generate_test_report()
            assert report["total_tests"] == 4
            assert report["failed_tests"] == 2

        finally:
            # Очистить временный файл
            temp_path.unlink(missing_ok=True)


class TestRecommendationsCoverage:
    """Тесты для проверки покрытия рекомендаций всеми типами ошибок и симптомами."""

    @pytest.fixture
    def temp_data_file(self) -> Iterator[Path]:
        """Временный файл для данных."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_all_error_types_have_recommendations(self) -> None:
        """Проверка, что каждый ErrorType имеет хотя бы одну рекомендацию."""
        for error_type in ErrorType:
            error_key = get_error_type_key(error_type)
            recommendations = get_recommendations(error_key, language="ru")
            error_msg = (
                f"ErrorType {error_type.name} ({error_type.value}) "
                f"does not have any recommendations. Key: {error_key}"
            )
            assert len(recommendations) > 0, error_msg
            # Проверяем, что рекомендации не пустые строки
            empty_msg = f"ErrorType {error_type.name} has empty recommendation strings"
            assert all(rec.strip() for rec in recommendations), empty_msg

    def test_all_error_types_have_recommendations_all_languages(self) -> None:
        """Проверка, что каждый ErrorType имеет рекомендации на всех языках."""
        languages = ["ru", "en", "es"]
        for error_type in ErrorType:
            error_key = get_error_type_key(error_type)
            for language in languages:
                recommendations = get_recommendations(error_key, language=language)
                assert len(recommendations) > 0, (
                    f"ErrorType {error_type.name} ({error_type.value}) "
                    f"does not have recommendations in language '{language}'. Key: {error_key}"
                )

    def test_known_symptoms_have_recommendations(self) -> None:
        """Проверка, что известные симптомы имеют рекомендации."""
        known_symptoms = ["async_context", "mock_context", "coverage_context"]
        for symptom in known_symptoms:
            symptom_key = get_symptom_key(symptom)
            recommendations = get_recommendations(symptom_key, language="ru")
            assert (
                len(recommendations) > 0
            ), f"Symptom '{symptom}' does not have any recommendations. Key: {symptom_key}"

    def test_recommendations_fallback_mechanism(self) -> None:
        """Проверка механизма fallback для рекомендаций."""
        # Тест fallback на default language
        error_key = get_error_type_key(ErrorType.ASSERTION_ERROR)
        recommendations_en = get_recommendations(error_key, language="en")
        recommendations_ru = get_recommendations(error_key, language="ru")
        assert len(recommendations_en) > 0
        assert len(recommendations_ru) > 0

        # Тест fallback на переданный fallback список
        unknown_key = "error_type.unknown_error"
        fallback_recs = ["Default recommendation"]
        recommendations = get_recommendations(unknown_key, language="ru", fallback=fallback_recs)
        assert recommendations == fallback_recs

    def test_analyzer_uses_recommendations(self, temp_data_file: Path) -> None:
        """Проверка, что анализатор использует систему рекомендаций."""
        analyzer = BayesianTestAnalyzer(data_file=temp_data_file, language="ru")

        # Тестируем генерацию рекомендаций для каждого типа ошибки
        for error_type in ErrorType:
            symptoms = set()
            recommendations = analyzer._generate_recommendations(error_type, symptoms, {})
            assert (
                len(recommendations) > 0
            ), f"Analyzer did not generate recommendations for ErrorType {error_type.name}"

    def test_analyzer_recommendations_with_symptoms(self, temp_data_file: Path) -> None:
        """Проверка генерации рекомендаций с симптомами."""
        analyzer = BayesianTestAnalyzer(data_file=temp_data_file, language="ru")

        symptoms = {"async_context", "mock_context", "coverage_context"}
        recommendations = analyzer._generate_recommendations(
            ErrorType.ASSERTION_ERROR, symptoms, {}
        )

        # Должны быть рекомендации для типа ошибки и для симптомов
        assert (
            len(recommendations) > 3
        ), "Analyzer should generate recommendations for error type and symptoms"

    def test_analyzer_language_configuration(self, temp_data_file: Path) -> None:
        """Проверка конфигурации языка в анализаторе."""
        # Тест с явным указанием языка
        analyzer_en = BayesianTestAnalyzer(data_file=temp_data_file, language="en")
        assert analyzer_en.language == "en"

        analyzer_ru = BayesianTestAnalyzer(data_file=temp_data_file, language="ru")
        assert analyzer_ru.language == "ru"

        # Тест с дефолтным языком
        analyzer_default = BayesianTestAnalyzer(data_file=temp_data_file)
        assert analyzer_default.language in ["ru", "en", "es"]

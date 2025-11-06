"""
Pytest plugin для интеграции с байесовской системой диагностики.

Автоматически записывает результаты тестов и предоставляет диагностику ошибок.
"""

import asyncio
from typing import Dict, Any, Optional, Tuple
import time
import os

# Import modules via proper packaging/pytest configuration (no sys.path mutations)

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    TestResult,
    ErrorType,
    TestCategory,
    record_test_execution,
    diagnose_test_failure,
)


class BayesianPytestPlugin:
    """Pytest plugin для байесовской диагностики."""

    def __init__(self):
        self.analyzer = BayesianTestAnalyzer()
        self.test_start_times = {}
        self.test_contexts = {}

    def pytest_runtest_setup(self, item):
        """Вызывается перед выполнением теста."""
        test_name = item.nodeid
        self.test_start_times[test_name] = time.time()

        # Определить категорию теста
        category = self._determine_test_category(item)

        # Собрать контекст теста
        context = self._gather_test_context(item)
        self.test_contexts[test_name] = {"category": category, "context": context}

    def pytest_runtest_teardown(self, item, nextitem):
        """Вызывается после выполнения теста."""
        test_name = item.nodeid
        start_time = self.test_start_times.get(test_name, time.time())
        _ = time.time() - start_time

        # Очистить временные данные
        self.test_start_times.pop(test_name, None)
        self.test_contexts.pop(test_name, None)

    def pytest_runtest_logreport(self, report):
        """Вызывается при получении отчета о тесте."""
        if report.when != "call":  # Только для основного выполнения
            return

        test_name = report.nodeid
        context_data = self.test_contexts.get(test_name, {})
        category = context_data.get("category", TestCategory.UNIT)
        context = context_data.get("context", {})

        # Определить результат теста
        if report.outcome == "passed":
            result = TestResult.PASSED
            error_type = None
            error_message = None
        elif report.outcome == "failed":
            result = TestResult.FAILED
            error_type, error_message = self._analyze_failure(report)

            # Предоставить диагностику
            if error_message:
                diagnosis = diagnose_test_failure(test_name, error_message, context)
                self._print_diagnosis(diagnosis)
        else:  # skipped, error
            result = TestResult.SKIPPED if report.outcome == "skipped" else TestResult.ERROR
            error_type = None
            error_message = None

        # Записать выполнение теста
        record_test_execution(
            test_name=test_name,
            category=category,
            result=result,
            error_type=error_type,
            error_message=error_message,
            execution_time=getattr(report, "duration", 0.0),
            file_path=report.fspath.strpath if hasattr(report, "fspath") else "",
            line_number=getattr(report, "lineno", None),
        )

    def _determine_test_category(self, item) -> TestCategory:
        """Определить категорию теста. Сначала по маркерам, затем по пути/имени."""
        try:
            markers = {m.name for m in getattr(item, "iter_markers", lambda: [])()}
        except Exception:
            markers = set()

        # Приоритет по явным маркерам
        if "integration" in markers:
            return TestCategory.INTEGRATION
        if "e2e" in markers:
            return TestCategory.E2E
        if "performance" in markers:
            return TestCategory.PERFORMANCE
        if "coverage" in markers:
            return TestCategory.COVERAGE
        if "monte_carlo" in markers:
            return TestCategory.MONTE_CARLO
        if "bayesian" in markers:
            return TestCategory.BAYESIAN

        # Фоллбэк по имени/пути
        test_path = str(item.fspath).lower()
        test_name = item.name.lower()
        if "integration" in test_path or "integration" in test_name:
            return TestCategory.INTEGRATION
        if "e2e" in test_path or "e2e" in test_name:
            return TestCategory.E2E
        if "performance" in test_path or "performance" in test_name:
            return TestCategory.PERFORMANCE
        if "coverage" in test_path or "coverage" in test_name:
            return TestCategory.COVERAGE
        if "monte_carlo" in test_path or "monte_carlo" in test_name:
            return TestCategory.MONTE_CARLO
        if "bayesian" in test_path or "bayesian" in test_name:
            return TestCategory.BAYESIAN
        return TestCategory.UNIT

    def _gather_test_context(self, item) -> Dict[str, Any]:
        """Собрать контекст теста."""
        context = {}

        # Проверить, является ли тест асинхронным
        context["is_async"] = hasattr(item, "function") and asyncio.iscoroutinefunction(
            item.function
        )

        # Проверить наличие моков в коде теста
        test_code = self._get_test_code(item)
        context["has_mocks"] = any(
            keyword in test_code.lower() for keyword in ["mock", "patch", "magicmock", "asyncmock"]
        )

        # Проверить, связан ли тест с покрытием
        context["coverage_related"] = "coverage" in str(item.fspath).lower()

        # Проверить сложность зависимостей
        context["complex_dependencies"] = len(item.fixturenames) > 3

        return context

    def _get_test_code(self, item) -> str:
        """Получить код теста."""
        try:
            if hasattr(item, "function") and hasattr(item.function, "__code__"):
                import inspect

                return inspect.getsource(item.function)
        except (OSError, TypeError):
            pass
        return ""

    def _analyze_failure(self, report) -> Tuple[Optional[str], Optional[str]]:
        """Анализировать падение теста и определить тип ошибки и сообщение.

        Returns a tuple (error_type_str, error_message_str) where values may be None
        if they cannot be determined from the report.
        """
        if not hasattr(report, "longrepr") or not report.longrepr:
            return None, None

        error_text = str(report.longrepr)
        error_message = None

        # Extract a concise error message from pytest longrepr in a safe, stepwise manner
        lr = getattr(report, "longrepr", None)
        if lr is not None:
            reprtraceback = getattr(lr, "reprtraceback", None)
            if reprtraceback is not None:
                reprentries = getattr(reprtraceback, "reprentries", None)
                if isinstance(reprentries, list) and reprentries:
                    last_entry = reprentries[-1]
                    reprfileloc = getattr(last_entry, "reprfileloc", None)
                    message_attr = getattr(reprfileloc, "message", None) if reprfileloc else None
                    if message_attr is not None:
                        error_message = str(message_attr)
        if error_message is None:
            error_message = error_text

        error_type = None
        error_lower = error_text.lower()
        if "assertionerror" in error_lower or "assert" in error_lower:
            error_type = ErrorType.ASSERTION_ERROR
        elif "importerror" in error_lower or "modulenotfounderror" in error_lower:
            error_type = ErrorType.IMPORT_ERROR
        elif "typeerror" in error_lower:
            error_type = ErrorType.TYPE_ERROR
        elif "attributeerror" in error_lower:
            error_type = ErrorType.ATTRIBUTE_ERROR
        elif "valueerror" in error_lower or "unprocessable" in error_lower:
            error_type = ErrorType.VALUE_ERROR
        elif "runtimeerror" in error_lower:
            error_type = ErrorType.RUNTIME_ERROR
        elif "timeouterror" in error_lower or "timeout" in error_lower:
            error_type = ErrorType.TIMEOUT_ERROR
        elif "coverage" in error_lower and "below" in error_lower:
            error_type = ErrorType.COVERAGE_ERROR
        elif "mock" in error_lower or "patch" in error_lower:
            error_type = ErrorType.MOCK_ERROR
        elif "asyncio" in error_lower or "await" in error_lower or "async" in error_lower:
            error_type = ErrorType.ASYNC_ERROR

        return error_type, error_message

    def _print_diagnosis(self, diagnosis: Any) -> None:
        """Вывести диагностику в консоль.

        Controlled by env BAYESIAN_DIAG_VERBOSE. Accepted truthy values:
        "1", "true", "yes", "on" (case-insensitive). Any other value disables printing.
        """
        val = os.getenv("BAYESIAN_DIAG_VERBOSE", "").strip().lower()
        truthy = {"1", "true", "yes", "on"}
        if val not in truthy:
            return
        print("\n" + "=" * 60)
        print("🔍 БАЙЕСОВСКАЯ ДИАГНОСТИКА")
        print("=" * 60)
        print(f"Наиболее вероятная причина: {diagnosis.most_likely_cause}")
        print(f"Вероятность: {diagnosis.probability:.2%}")
        print(f"Уверенность: {diagnosis.confidence:.2%}")
        print("\n📋 Доказательства:")
        for evidence in diagnosis.evidence:
            print(f"  • {evidence}")
        print("\n💡 Рекомендации:")
        for recommendation in diagnosis.recommendations:
            print(f"  • {recommendation}")
        if diagnosis.alternative_causes:
            print("\n🔄 Альтернативные причины:")
            for cause, prob in diagnosis.alternative_causes:
                print(f"  • {cause}: {prob:.2%}")
        print("=" * 60 + "\n")


def pytest_configure(config):
    """Конфигурация pytest plugin."""
    if not hasattr(config, "bayesian_plugin"):
        config.bayesian_plugin = BayesianPytestPlugin()


def pytest_runtest_setup(item):
    """Хук для настройки теста."""
    if hasattr(item.config, "bayesian_plugin"):
        item.config.bayesian_plugin.pytest_runtest_setup(item)


def pytest_runtest_teardown(item, nextitem):
    """Хук для завершения теста."""
    if hasattr(item.config, "bayesian_plugin"):
        item.config.bayesian_plugin.pytest_runtest_teardown(item, nextitem)


def pytest_runtest_logreport(report):
    """Хук для отчета о тесте."""
    if hasattr(report.config, "bayesian_plugin"):
        report.config.bayesian_plugin.pytest_runtest_logreport(report)

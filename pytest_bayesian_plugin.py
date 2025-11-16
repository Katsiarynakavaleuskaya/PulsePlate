"""
Pytest plugin для интеграции с байесовской системой диагностики.

Автоматически записывает результаты тестов и предоставляет диагностику ошибок.

EN: Pytest plugin for integration with Bayesian diagnostic system.

Automatically records test results and provides error diagnosis.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.nodes import Item
    from _pytest.reports import TestReport
else:  # pragma: no cover - runtime fallback when pytest types unavailable
    Config = Any
    Item = Any
    TestReport = Any

from core.bayesian_test_analyzer import (
    BayesianDiagnosis,
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestStatus,
    diagnose_test_failure,
    record_test_execution,
)

# Import modules via proper packaging/pytest configuration (no sys.path mutations)

logger = logging.getLogger(__name__)


class BayesianPytestPlugin:
    """Pytest plugin для байесовской диагностики."""

    DEFAULT_CATEGORY_MARKERS: List[str] = ["smoke", "regression", "integration", "unit"]

    # Mapping of marker names (lowercase) to TestCategory
    MARKER_TO_CATEGORY: Dict[str, TestCategory] = {
        "integration": TestCategory.INTEGRATION,
        "e2e": TestCategory.E2E,
        "performance": TestCategory.PERFORMANCE,
        "coverage": TestCategory.COVERAGE,
        "monte_carlo": TestCategory.MONTE_CARLO,
        "bayesian": TestCategory.BAYESIAN,
    }

    # Error detection patterns: (ErrorType, keywords list, require_all flag)
    # COVERAGE_ERROR requires all keywords to be present, others use any()
    ERROR_PATTERNS = [
        (ErrorType.ASSERTION_ERROR, ["assertionerror", "assert"], False),
        (ErrorType.IMPORT_ERROR, ["importerror", "modulenotfounderror"], False),
        (ErrorType.TYPE_ERROR, ["typeerror"], False),
        (ErrorType.ATTRIBUTE_ERROR, ["attributeerror"], False),
        (ErrorType.VALUE_ERROR, ["valueerror", "unprocessable"], False),
        (ErrorType.RUNTIME_ERROR, ["runtimeerror"], False),
        (ErrorType.TIMEOUT_ERROR, ["timeouterror", "timeout"], False),
        (ErrorType.COVERAGE_ERROR, ["coverage", "below"], True),  # Requires all keywords
        (ErrorType.MOCK_ERROR, ["mock", "patch"], False),
        (ErrorType.ASYNC_ERROR, ["asyncio", "await", "async"], False),
    ]

    def __init__(self, category_markers: Optional[List[str]] = None) -> None:
        self.analyzer = BayesianTestAnalyzer()
        self.test_contexts: dict[str, dict[str, Any]] = {}
        self.test_start_times: dict[str, float] = {}
        # Allow custom markers, fallback to default
        self.category_markers = list(category_markers or self.DEFAULT_CATEGORY_MARKERS)

    def pytest_runtest_setup(self, item: Item) -> None:
        """Вызывается перед выполнением теста."""
        test_name = item.nodeid
        self.test_start_times[test_name] = time.time()

        # Определить категорию теста
        category = self._determine_test_category(item)

        # Собрать контекст теста
        context = self._gather_test_context(item)
        self.test_contexts[test_name] = {"category": category, "context": context}

    def pytest_runtest_teardown(self, item: Item, nextitem: Item | None) -> None:
        """Вызывается после выполнения теста."""
        test_name = item.nodeid

        # Очистить временные данные
        self.test_start_times.pop(test_name, None)
        self.test_contexts.pop(test_name, None)

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Вызывается при получении отчета о тесте."""
        if report.when != "call":  # Только для основного выполнения
            return

        test_name = report.nodeid
        context_data = self.test_contexts.get(test_name, {})
        category = context_data.get("category", TestCategory.UNIT)
        context = context_data.get("context", {})

        # Определить результат теста
        if report.outcome == "passed":
            result = TestStatus.PASSED
            error_type = None
            error_message = None
        elif report.outcome == "failed":
            result = TestStatus.FAILED
            error_type, error_message = self._analyze_failure(report)

            # Предоставить диагностику
            if error_message:
                diagnosis = diagnose_test_failure(test_name, error_message, context)
                self._print_diagnosis(diagnosis)
        elif report.outcome == "skipped":
            result = TestStatus.SKIPPED
            error_type = None
            error_message = None
        else:  # ERROR/other unexpected outcomes
            result = TestStatus.ERROR
            error_type, error_message = self._analyze_failure(report)
            if error_message:
                diagnosis = diagnose_test_failure(test_name, error_message, context)
                self._print_diagnosis(diagnosis)

        # Записать выполнение теста
        fspath = getattr(report, "fspath", None)
        if fspath is not None:
            # Support older py.path objects with .strpath and newer str/Path values
            file_path = getattr(fspath, "strpath", None) or str(fspath)
        else:
            file_path = ""

        record_test_execution(
            test_name=test_name,
            category=category,
            result=result,
            error_type=error_type,
            error_message=error_message,
            execution_time=getattr(report, "duration", 0.0),
            file_path=file_path,
            line_number=getattr(report, "lineno", None),
        )

    def _determine_test_category(self, item: Item) -> TestCategory:
        """Определяет категорию теста на основе маркеров с поддержкой настроек.

        Сначала проверяются настраиваемые маркеры, затем известные категории,
        затем фоллбэк по имени/пути.
        """
        try:
            all_markers = {m.name for m in getattr(item, "iter_markers", lambda: [])()}
        except Exception as exc:
            # Handle cases where item doesn't have iter_markers or raises at iteration time
            all_markers = set()
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Failed to get markers from item %s: %s",
                getattr(item, "nodeid", str(item)),
                exc,
            )

        # Настраиваемые маркеры
        for marker in self.category_markers:
            if marker in all_markers:
                # Map common strings to TestCategory when possible
                name = marker.lower()
                return self.MARKER_TO_CATEGORY.get(name, TestCategory.UNIT)

        # Известные маркеры - use MARKER_TO_CATEGORY mapping
        for marker_name, category in self.MARKER_TO_CATEGORY.items():
            if marker_name in all_markers:
                return category

        # Фоллбэк по имени/пути
        fspath = getattr(item, "fspath", None)
        test_path = (
            getattr(fspath, "strpath", None) or str(fspath) if fspath is not None else ""
        ).lower()
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

    def _gather_test_context(self, item: Item) -> dict[str, Any]:
        """Собрать контекст теста."""
        context = {}

        # Проверить, является ли тест асинхронным
        context["is_async"] = hasattr(item, "function") and asyncio.iscoroutinefunction(
            item.function
        )

        # Проверить наличие моков в коде теста
        test_code = self._get_test_code(item)
        context["has_mocks"] = self._detect_mocks_ast(test_code)

        # Проверить, связан ли тест с покрытием
        fspath = getattr(item, "fspath", None)
        path_str = getattr(fspath, "strpath", None) or (str(fspath) if fspath is not None else "")
        context["coverage_related"] = "coverage" in path_str.lower()

        # Проверить сложность зависимостей
        fixturenames = getattr(item, "fixturenames", ()) or ()
        context["complex_dependencies"] = len(fixturenames) > 3

        return context

    def _get_test_code(self, item: Item) -> str:
        """Получить код теста."""
        try:
            if hasattr(item, "function") and hasattr(item.function, "__code__"):
                import inspect

                return inspect.getsource(item.function)
        except (OSError, TypeError):
            # Source may be unavailable (e.g., dynamically generated functions or builtins).
            pass
        return ""

    def _detect_mocks_ast(self, test_code: str) -> bool:
        """Обнаружить использование моков через AST-анализ.

        Парсит код и ищет:
        - Импорты модулей/имен, содержащих "mock" или "unittest.mock"
        - Вызовы функций и атрибутов, содержащих "mock", "patch", "magicmock", "asyncmock"
        (регистронезависимо)

        Args:
            test_code: Исходный код теста

        Returns:
            True если найдены моки, False иначе
        """
        if not test_code:
            return False

        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            # Если код невалиден, возвращаем False
            return False

        mock_keywords = {"mock", "patch", "magicmock", "asyncmock"}

        class MockDetector(ast.NodeVisitor):
            """Visitor для обнаружения использования моков в AST."""

            def __init__(self, keywords: set) -> None:
                self.has_mocks = False
                self.mock_keywords = keywords

            def visit_Import(self, node: ast.Import) -> None:
                """Проверить импорты модулей."""
                for alias in node.names:
                    module_name = alias.name.lower()
                    if "mock" in module_name or "unittest.mock" in module_name:
                        self.has_mocks = True
                        return
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                """Проверить импорты из модулей."""
                if node.module:
                    module_name = node.module.lower()
                    if "mock" in module_name or "unittest.mock" in module_name:
                        self.has_mocks = True
                        return
                # Проверить импортируемые имена
                for alias in node.names:
                    name = alias.name.lower()
                    if any(keyword in name for keyword in self.mock_keywords):
                        self.has_mocks = True
                        return
                self.generic_visit(node)

            def _check_name_or_attr(self, node: ast.AST) -> bool:
                """Рекурсивно проверить имя или атрибут на наличие mock-ключевых слов."""
                if isinstance(node, ast.Name):
                    name = node.id.lower()
                    return any(keyword in name for keyword in self.mock_keywords)
                elif isinstance(node, ast.Attribute):
                    attr_name = node.attr.lower()
                    if any(keyword in attr_name for keyword in self.mock_keywords):
                        return True
                    # Рекурсивно проверить вложенные атрибуты (например, unittest.mock.patch)
                    return self._check_name_or_attr(node.value)
                return False

            def visit_Call(self, node: ast.Call) -> None:
                """Проверить вызовы функций."""
                if self._check_name_or_attr(node.func):
                    self.has_mocks = True
                    return
                self.generic_visit(node)

            def visit_Attribute(self, node: ast.Attribute) -> None:
                """Проверить использование атрибутов."""
                if self._check_name_or_attr(node):
                    self.has_mocks = True
                    return
                self.generic_visit(node)

        detector = MockDetector(mock_keywords)
        detector.visit(tree)
        return detector.has_mocks

    def _analyze_failure(self, report: TestReport) -> tuple[ErrorType | None, str | None]:
        """Анализировать падение теста и определить тип ошибки и сообщение.

        Returns a tuple (error_type, error_message) where values may be None
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

        error_type: ErrorType | None = None
        error_lower = error_text.lower()

        # Iterate over ERROR_PATTERNS to find matching error type
        for pattern_error_type, keywords, require_all in self.ERROR_PATTERNS:
            if require_all:
                # COVERAGE_ERROR requires all keywords to be present
                if all(keyword in error_lower for keyword in keywords):
                    error_type = pattern_error_type
                    break
            else:
                # Most error types match if any keyword is present
                if any(keyword in error_lower for keyword in keywords):
                    error_type = pattern_error_type
                    break

        return error_type, error_message

    def _print_diagnosis(self, diagnosis: BayesianDiagnosis) -> None:
        """Вывести диагностику в консоль.

        Controlled by env BAYESIAN_DIAG_VERBOSE. Accepted truthy values:
        "1", "true", "yes", "on" (case-insensitive). Any other value disables printing.
        """
        val = os.getenv("BAYESIAN_DIAG_VERBOSE", "").strip().lower()
        truthy = {"1", "true", "yes", "on"}
        if val not in truthy:
            return
        diag_logger = logging.getLogger("bayesian.diagnostics")
        lines = [
            "",
            "=" * 60,
            "🔍 БАЙЕСОВСКАЯ ДИАГНОСТИКА",
            "=" * 60,
            f"Наиболее вероятная причина: {diagnosis.most_likely_cause}",
            f"Вероятность: {diagnosis.probability:.2%}",
            f"Уверенность: {diagnosis.confidence:.2%}",
            "",
            "📋 Доказательства:",
        ]
        lines.extend(f"  • {evidence}" for evidence in diagnosis.evidence)
        lines.append("")
        lines.append("💡 Рекомендации:")
        lines.extend(f"  • {recommendation}" for recommendation in diagnosis.recommendations)
        if diagnosis.alternative_causes:
            lines.append("")
            lines.append("🔄 Альтернативные причины:")
            lines.extend(f"  • {cause}: {prob:.2%}" for cause, prob in diagnosis.alternative_causes)
        lines.append("=" * 60)
        lines.append("")

        for line in lines:
            diag_logger.info(line)
            print(line)


def pytest_configure(config: Config) -> None:
    """Конфигурация pytest plugin."""
    plugin = getattr(config, "bayesian_plugin", None)
    if plugin is None:
        plugin = BayesianPytestPlugin()
        setattr(config, "bayesian_plugin", plugin)
    if getattr(config, "_bayesian_plugin_registered", False):
        return
    try:
        config.pluginmanager.register(plugin, name="bayesian_pytest_plugin")
    except ValueError:
        # Already registered elsewhere - mark as registered to avoid duplicate hook calls
        setattr(config, "_bayesian_plugin_registered", True)
    except Exception:
        # Ignore other registration failures; fall back to module-level hooks
        return
    else:
        setattr(config, "_bayesian_plugin_registered", True)


def pytest_runtest_setup(item: Item) -> None:
    """Хук для настройки теста."""
    if hasattr(item.config, "bayesian_plugin") and not getattr(
        item.config, "_bayesian_plugin_registered", False
    ):
        item.config.bayesian_plugin.pytest_runtest_setup(item)


def pytest_runtest_teardown(item: Item, nextitem: Item | None) -> None:
    """Хук для завершения теста."""
    if hasattr(item.config, "bayesian_plugin") and not getattr(
        item.config, "_bayesian_plugin_registered", False
    ):
        item.config.bayesian_plugin.pytest_runtest_teardown(item, nextitem)


def pytest_runtest_logreport(report: Any) -> None:
    """Хук для отчета о тесте."""
    report_config = getattr(report, "config", None)
    if report_config is None:
        return
    if hasattr(report_config, "bayesian_plugin") and not getattr(
        report_config, "_bayesian_plugin_registered", False
    ):
        report_config.bayesian_plugin.pytest_runtest_logreport(report)

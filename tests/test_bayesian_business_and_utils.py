"""
Additional coverage-focused tests for Bayesian analyzers and utilities.

RU: Дополнительные тесты для повышения покрытия байесовских анализаторов и утилит.
EN: Additional tests to improve coverage for Bayesian analyzers and utilities.
"""

from __future__ import annotations

import ast
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.bayesian_recommendations import (
    DEFAULT_LANGUAGE,
    RECOMMENDATIONS,
    get_all_error_type_keys,
    get_all_symptom_keys,
    get_error_type_key,
    get_recommendations,
    get_symptom_key,
)
from core.bayesian_technical_utils import (
    _has_explicit_return_or_yield,
    analyze_technical_aspects_common,
)
from core.bayesian_test_analyzer import (
    BayesianDiagnosis,
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestRecord,
    TestStatus,
)
from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
    BusinessTestResult,
)
from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer
from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer
from pytest_bayesian_plugin import BayesianPytestPlugin
from pytest_bayesian_plugin import TestCategory as PluginCategory
from scripts import run_tests_bayesian

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyReport:
    """RU: Заглушка отчета Pytest. EN: Lightweight pytest report stub."""

    def __init__(self, nodeid: str, outcome: str) -> None:
        self.nodeid = nodeid
        self.when = "call"
        self.outcome = outcome
        self.duration = 0.05
        self.fspath = SimpleNamespace(strpath="tests/sample_test.py")
        self.longrepr = SimpleNamespace(
            reprtraceback=SimpleNamespace(
                reprentries=[
                    SimpleNamespace(
                        reprfileloc=SimpleNamespace(message="AssertionError: boom"),
                    )
                ]
            )
        )


class DummyItem:
    """RU: Заглушка Pytest item. EN: Minimal pytest item substitute."""

    def __init__(
        self,
        name: str,
        path: str,
        markers: list[str] | None = None,
        is_async: bool = False,
        fixturenames: list[str] | None = None,
        source: str = "",
    ) -> None:
        self.name = name
        self.fspath = Path(path)
        self._markers = markers or []
        self.fixturenames = fixturenames or []
        if is_async:

            async def _async_func():
                return None

            self.function = _async_func
        else:
            self.function = lambda: None
        self._source = source
        self.nodeid = f"{path}::{name}"

    def iter_markers(self):
        for marker in self._markers:
            yield SimpleNamespace(name=marker)

    def __getattr__(self, name):
        if name == "__code__":
            raise AttributeError
        raise AttributeError(name)


# ---------------------------------------------------------------------------
# Business analyzer tests
# ---------------------------------------------------------------------------


def _build_complex_business_code() -> str:
    """Generate a code snippet that triggers multiple analyzer branches."""

    return """
price = 0.5
expensive_package = 5000
payment = True
billing = "manual"
price_invalid = "not_a_number"
payment_processor.process()
register_user()
for user in users:
    for order in orders:
        database.save(order)
while True:
    request.execute()
sleep(10)
analytics.log_event("conversion")
user_personal_profile = True
notification_sender.send("reminder")
feedback_collector.collect()
SELECT * FROM revenue_table
"""


def test_business_analyzer_detects_multi_category_issues() -> None:
    """RU: Проверка обнаружения бизнес-проблем. EN: Ensure multi-category issues detected."""

    analyzer = BusinessBayesianAnalyzer(domain="generic")
    code = _build_complex_business_code()

    # Cover public analyze entry point
    public_results = analyzer.analyze(code, test_name="ScenarioPublic")
    results = analyzer.analyze_business_logic(code, test_name="ScenarioCase")
    assert public_results
    categories = {result.business_category for result in results}

    assert BusinessCategory.MONETIZATION in categories
    assert BusinessCategory.COST_OPTIMIZATION in categories
    assert BusinessCategory.REVENUE_GROWTH in categories
    assert BusinessCategory.USER_RETENTION in categories
    assert any("платежи без стратегии" in result.error_message.lower() for result in results)

    # Trigger tokenize fallback path
    bad_code = "def broken(:\n    pass"
    assert analyzer._remove_comments(bad_code)  # Should return gracefully

    # Generate recommendations and ROI based on accumulated issues
    analyzer.test_results.extend(
        [
            BusinessTestResult(
                test_name="efficiency_case",
                success=False,
                business_category=BusinessCategory.OPERATIONAL_EFFICIENCY,
                error_type=BusinessErrorType.OPERATIONAL_WASTE,
                error_message="Неэффективные процессы разработки",
            ),
            BusinessTestResult(
                test_name="data_case",
                success=False,
                business_category=BusinessCategory.DATA_MONETIZATION,
                error_type=BusinessErrorType.DATA_UNDERUTILIZED,
                error_message="Данные не монетизируются",
            ),
        ]
    )

    cost_recs = analyzer.generate_cost_savings_recommendations()
    revenue_recs = analyzer.generate_revenue_optimization_recommendations()
    assert cost_recs  # RU: Проверяем наличие рекомендаций по экономии / EN: Ensure cost recs exist
    assert revenue_recs

    roi_estimates = analyzer.calculate_roi_potential()
    assert {estimate.category for estimate in roi_estimates} >= {
        "cost_optimization",
        "monetization",
    }


def test_calculate_bayesian_roi_without_data() -> None:
    """RU/EN: ROI estimator should fall back to priors when no evidence provided."""

    analyzer = BusinessBayesianAnalyzer()
    roi_estimate = analyzer._calculate_bayesian_roi(
        category="test_category",
        prior_mean=0.2,
        prior_std=0.1,
        data=[],
        time_horizon_months=6,
        assumptions="no data available",
    )
    assert roi_estimate.expected_roi >= 0.0


def test_analyze_monetization_handles_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Gracefully skip prices that cannot be parsed."""

    analyzer = BusinessBayesianAnalyzer()
    call_count = {"seen": 0}
    real_float = float

    def fake_float(value: str) -> float:
        call_count["seen"] += 1
        if call_count["seen"] == 1:
            raise ValueError("boom")
        return real_float(value)

    monkeypatch.setattr("core.business_bayesian_analyzer.float", fake_float, raising=False)
    code = "price = 4\nprice = 4.5"
    results = analyzer._analyze_monetization(code, "suite::pricing")
    # First occurrence triggers ValueError branch; second is processed normally
    assert any("Слишком низкая цена" in res.error_message for res in results)


def test_analyze_customer_retention_feedback_branch() -> None:
    """RU/EN: Detect feedback collection without processing."""

    analyzer = BusinessBayesianAnalyzer()
    results = analyzer._analyze_customer_retention(
        "feedback = collect()\nresponse = queue_feedback(feedback)",
        "suite::retention",
    )
    assert any("обратной связи" in res.error_message.lower() for res in results)


# ---------------------------------------------------------------------------
# Bayesian recommendations tests
# ---------------------------------------------------------------------------


def test_recommendations_language_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU: Проверка фоллбэка рекомендаций. EN: Ensure fallback logic works."""

    # Language defaults to DEFAULT_LANGUAGE when None is supplied
    default_lookup = get_recommendations("error_type.assertion_error", language=None)
    assert default_lookup == RECOMMENDATIONS[DEFAULT_LANGUAGE]["error_type.assertion_error"]

    unknown_language_result = get_recommendations("error_type.assertion_error", language="de")
    default_result = RECOMMENDATIONS[DEFAULT_LANGUAGE]["error_type.assertion_error"]
    assert unknown_language_result == default_result

    custom_fallback = ["Default recommendation"]
    result_with_fallback = get_recommendations(
        "unknown_key", language="es", fallback=custom_fallback
    )
    assert result_with_fallback == custom_fallback

    assert get_error_type_key(ErrorType.ASSERTION_ERROR) == "error_type.assertion_error"
    assert get_symptom_key("async_context") == "symptom.async_context"
    assert all(key.startswith("error_type.") for key in get_all_error_type_keys())
    assert all(key.startswith("symptom.") for key in get_all_symptom_keys())


# ---------------------------------------------------------------------------
# Bayesian technical utils tests
# ---------------------------------------------------------------------------


def test_has_explicit_return_or_yield() -> None:
    """RU/EN: Ensure AST helper detects return/yield."""

    func_node = ast.parse("def helper():\n    yield from range(1)\n").body[0]
    assert _has_explicit_return_or_yield(func_node) is True


def test_has_explicit_return_or_yield_false() -> None:
    """RU/EN: Bare return should not require annotation."""

    func_node = ast.parse("def helper():\n    return\n").body[0]
    assert _has_explicit_return_or_yield(func_node) is False


def test_analyze_technical_aspects_ast() -> None:
    """RU/EN: Cover AST path of analyze_technical_aspects_common."""

    code = """
from unittest.mock import Mock
import unittest.mock

async def fetch_data():
    resource = Mock()
    return resource

def helper():
    return 42

raise RuntimeError("boom")
"""
    issues = analyze_technical_aspects_common(code, "_sample")
    assert "Async function without await usage" in issues
    assert "Using Mock instead of AsyncMock for async methods" in issues
    assert "Exception raised without handling" in issues
    assert "Missing return type annotations" in issues


def test_analyze_technical_aspects_regex() -> None:
    """RU/EN: Cover regex fallback when AST parsing fails."""

    broken_code = (
        "async def broken(:\n    result = Mock()\n    raise ValueError()\n    return value"
    )
    issues = analyze_technical_aspects_common(broken_code, "_sample")
    assert "Async function without await usage" in issues
    assert "Missing return type annotations" in issues
    assert "Exception raised without handling" in issues


# ---------------------------------------------------------------------------
# Bayesian test analyzer tests
# ---------------------------------------------------------------------------


def test_bayesian_test_analyzer_history_and_diagnosis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RU/EN: Ensure history load/save and diagnosis logic are covered."""

    history_path = tmp_path / "history.json"
    history_data = [
        {
            "test_name": "tests/sample_test.py::test_example",
            "category": TestCategory.UNIT.value,
            "result": TestStatus.FAILED.value,
            "error_type": ErrorType.ASSERTION_ERROR.value,
            "error_message": "AssertionError: values differ",
            "execution_time": 0.5,
            "coverage_percentage": 75.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dependencies": [],
            "file_path": "tests/sample_test.py",
            "line_number": 12,
        }
    ]
    history_path.write_text(json.dumps(history_data), encoding="utf-8")

    analyzer = BayesianTestAnalyzer(data_file=history_path)
    assert analyzer.execution_history, "History should be loaded"

    # Persist enabled path should trigger save_history
    record = TestRecord(
        test_name="tests/sample_test.py::test_new",
        category=TestCategory.UNIT,
        result=TestStatus.FAILED,
        error_type=ErrorType.ASSERTION_ERROR,
        error_message="AssertionError: boom",
        execution_time=1.2,
        coverage_percentage=80.0,
        file_path="tests/sample_test.py",
    )
    analyzer.record_test_execution(record)
    saved = json.loads(history_path.read_text(encoding="utf-8"))
    assert any(item["test_name"] == record.test_name for item in saved)

    # Recency weight: normal and fallback branch
    recent_weight = analyzer._calculate_recency_weight(
        datetime.now(timezone.utc) - timedelta(hours=12)
    )
    assert 0.0 < recent_weight <= 1.0
    assert analyzer._calculate_recency_weight("not-a-datetime") == 1.0

    diagnosis = analyzer.diagnose_test_failure(
        "tests/sample_test.py::test_new",
        "AssertionError: expected 1 got 2",
        {"is_async": True, "has_mocks": True, "coverage_below_threshold": True},
    )
    assert isinstance(diagnosis, BayesianDiagnosis)
    assert diagnosis.most_likely_cause

    # Environment-driven constructor branches
    monkeypatch.setenv("BAYESIAN_PERSIST", "1")
    monkeypatch.setenv("BAYESIAN_HISTORY_PATH", "")
    extra_analyzer = BayesianTestAnalyzer()
    assert extra_analyzer.persist_enabled is True


# ---------------------------------------------------------------------------
# Pytest plugin tests
# ---------------------------------------------------------------------------


def test_pytest_plugin_logreport(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """RU/EN: Cover logreport diagnostic and verbose output."""

    plugin = BayesianPytestPlugin(category_markers=["custom"])
    plugin.test_contexts["suite::test_item"] = {"category": PluginCategory.COVERAGE, "context": {}}
    plugin.test_start_times["suite::test_item"] = time.time()

    fake_diagnosis = SimpleNamespace(
        most_likely_cause="assertion_error",
        probability=0.42,
        confidence=0.73,
        evidence=["assert mismatch"],
        recommendations=["Check inputs"],
        alternative_causes=[],
    )

    monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "true")
    monkeypatch.setattr(
        "pytest_bayesian_plugin.diagnose_test_failure", lambda *args, **kwargs: fake_diagnosis
    )

    recorded = []

    def fake_record(*args, **kwargs):
        recorded.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr("pytest_bayesian_plugin.record_test_execution", fake_record)

    report = DummyReport("suite::test_item", "failed")
    plugin.pytest_runtest_logreport(report)

    output = capsys.readouterr().out
    assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in output
    assert recorded and recorded[0]["kwargs"]["test_name"] == "suite::test_item"


def test_pytest_plugin_category_detection() -> None:
    """RU/EN: Ensure category detection covers custom and fallback paths."""

    plugin = BayesianPytestPlugin(category_markers=["custom"])

    # Custom marker
    item_custom = DummyItem(
        name="test_custom",
        path="tests/test_sample.py",
        markers=["custom"],
    )
    assert plugin._determine_test_category(item_custom) == PluginCategory.UNIT

    # Known marker
    item_marker = DummyItem(
        name="test_integration",
        path="tests/test_integration_sample.py",
        markers=["integration"],
    )
    assert plugin._determine_test_category(item_marker) == PluginCategory.INTEGRATION

    # Fallback by path/name
    item_fallback = DummyItem(
        name="performance_case",
        path="tests/performance/test_perf.py",
    )
    assert plugin._determine_test_category(item_fallback) == PluginCategory.PERFORMANCE


def test_pytest_plugin_context_detection() -> None:
    """RU/EN: Ensure mock detection and context gathering."""

    plugin = BayesianPytestPlugin()
    source_code = (
        "from unittest.mock import patch\n\n@patch('x.y')\ndef test_sample(mock_patch):\n    pass\n"
    )
    item = DummyItem(
        name="test_sample",
        path="tests/test_sample.py",
        source=source_code,
        fixturenames=["a", "b", "c", "d"],
    )
    item.function = lambda: None
    with patch("inspect.getsource", return_value=source_code):
        context = plugin._gather_test_context(item)
    assert context["has_mocks"] is True
    assert context["complex_dependencies"] is True


def test_pytest_plugin_detect_mocks_syntax_error() -> None:
    """RU/EN: Ensure AST SyntaxError path returns False."""

    plugin = BayesianPytestPlugin()
    bad_code = "def broken(:\n    pass"
    assert plugin._detect_mocks_ast(bad_code) is False


def test_pytest_plugin_logreport_non_call_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Ensure non-call phases are ignored."""

    plugin = BayesianPytestPlugin()
    report = DummyReport("suite::test_non_call", "passed")
    report.when = "setup"
    plugin.pytest_runtest_logreport(report)

    # No entries recorded because branch returned early
    assert "suite::test_non_call" not in plugin.test_contexts
    assert "suite::test_non_call" not in plugin.test_start_times


def test_pytest_plugin_category_path_fallback() -> None:
    """RU/EN: Ensure path-based fallback categorization works."""

    plugin = BayesianPytestPlugin()
    item = DummyItem(
        name="test_integration_feature",
        path="tests/integration/test_feature.py",
    )
    assert plugin._determine_test_category(item) == PluginCategory.INTEGRATION


def test_pytest_plugin_setup_and_teardown(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Cover pytest_runtest_setup and teardown bookkeeping."""

    plugin = BayesianPytestPlugin()
    item = DummyItem(
        name="test_sample",
        path="tests/test_sample.py",
        markers=["unit"],
        source="from unittest.mock import Mock\nMock()\n",
    )
    with patch("inspect.getsource", return_value=item._source):
        plugin.pytest_runtest_setup(item)
    assert item.nodeid in plugin.test_contexts
    assert item.nodeid in plugin.test_start_times

    plugin.pytest_runtest_teardown(item, None)
    assert item.nodeid not in plugin.test_contexts
    assert item.nodeid not in plugin.test_start_times


def test_pytest_plugin_logreport_passed_and_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Ensure logreport handles passed and skipped outcomes."""

    plugin = BayesianPytestPlugin()
    plugin.test_contexts["suite::test_item_passed"] = {
        "category": PluginCategory.UNIT,
        "context": {},
    }
    plugin.test_contexts["suite::test_item_skipped"] = {
        "category": PluginCategory.E2E,
        "context": {},
    }

    recorded = []

    def fake_record(*args, **kwargs):
        recorded.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr("pytest_bayesian_plugin.record_test_execution", fake_record)

    passed_report = DummyReport("suite::test_item_passed", "passed")
    plugin.pytest_runtest_logreport(passed_report)
    skipped_report = DummyReport("suite::test_item_skipped", "skipped")
    skipped_report.when = "call"
    plugin.pytest_runtest_logreport(skipped_report)

    outcomes = [call["kwargs"]["result"] for call in recorded]
    assert TestStatus.PASSED in outcomes
    assert TestStatus.SKIPPED in outcomes


def test_pytest_plugin_analyze_failure_patterns() -> None:
    """RU/EN: Cover failure analysis edge cases (coverage error detection)."""

    plugin = BayesianPytestPlugin()
    report = DummyReport("suite::test_item", "failed")
    report.longrepr = SimpleNamespace(
        reprtraceback=None,
        reprcrash=SimpleNamespace(message="Coverage below threshold"),
    )
    error_type, message = plugin._analyze_failure(report)
    assert error_type == ErrorType.COVERAGE_ERROR
    assert "Coverage" in (message or "")


def test_pytest_plugin_analyze_failure_simple_string() -> None:
    """RU/EN: Simple string longrepr should still detect coverage errors."""

    plugin = BayesianPytestPlugin()
    report = DummyReport("suite::test_cov", "failed")
    report.longrepr = "Coverage below required threshold"
    error_type, message = plugin._analyze_failure(report)
    assert error_type == ErrorType.COVERAGE_ERROR
    assert "Coverage" in (message or "")


def test_detect_mocks_ast_import_variants() -> None:
    """RU/EN: Ensure MockDetector handles plain imports."""

    plugin = BayesianPytestPlugin()
    code_direct = """
import unittest.mock
def run():
    unittest.mock.patch("module.func")
"""
    code_from = """
from unittest.mock import AsyncMock
def run():
    AsyncMock()
"""
    assert plugin._detect_mocks_ast(code_direct) is True
    assert plugin._detect_mocks_ast(code_from) is True


# ---------------------------------------------------------------------------
# Scripts coverage improvements
# ---------------------------------------------------------------------------


def test_run_tests_fast_fallback_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Ensure fallback path when extracting failed tests triggers logging."""

    class BadLine(str):
        def split(self, sep=None):
            raise AttributeError("broken split")

    class BadString(str):
        def split(self, sep=None):
            return [
                BadLine("FAILED tests/test_demo.py::test_example - AttributeError"),
                "FAILED tests/test_demo.py::test_example - AssertionError",
            ]

    class BadOutput:
        def __init__(self, text: str) -> None:
            self.text = text

        def __add__(self, other: str) -> BadString:
            return BadString(self.text + str(other))

    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = ""

        def __init__(self):
            self.stdout = ""
            self.stderr = ""

    def fake_run(*args, **kwargs):
        res = FakeResult()
        res.stdout = BadOutput("FAILED tests/test_demo.py::test_example - AssertionError\n")
        res.stderr = ""
        return res

    warnings = []

    def fake_warning(msg, exc_info=False):
        warnings.append(msg)

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(run_tests_bayesian.logging, "warning", fake_warning)

    result = run_tests_bayesian.run_tests_fast()
    assert result["failed_tests"]
    assert any("Failed to extract test name" in msg for msg in warnings)


# ---------------------------------------------------------------------------
# Comprehensive and integrated analyzer coverage
# ---------------------------------------------------------------------------


def test_comprehensive_bayesian_analyzer_combines_scores() -> None:
    """RU/EN: Ensure comprehensive analyzer aggregates scores and risk."""

    analyzer = ComprehensiveBayesianAnalyzer()

    analyzer.technical_analyzer = SimpleNamespace(
        analyze_technical_aspects=lambda code, name: ["AsyncMock missing", "cache issue"]
    )
    analyzer.nutrition_analyzer = SimpleNamespace(
        analyze_nutrition_safety=lambda code, name: [
            SimpleNamespace(success=False, error_message="Опасно низкий калораж")
        ],
        get_safety_score=lambda: 0.2,
    )
    analyzer.business_analyzer = SimpleNamespace(
        analyze_business_logic=lambda code, name: [
            BusinessTestResult(
                test_name=name,
                success=False,
                business_category=BusinessCategory.MONETIZATION,
                error_type=BusinessErrorType.REVENUE_LEAK,
                error_message="Потеря дохода",
                revenue_impact="Снижение дохода",
                cost_impact="Рост расходов",
                customer_impact="Отток клиентов",
                optimization_potential="Оптимизировать цены",
            )
        ]
    )

    result = analyzer.analyze_comprehensively("code", "ScenarioCase", "tests/sample.py")
    assert result.overall_score <= 0.8
    assert result.critical_issues
    assert analyzer.comprehensive_results


def test_integrated_bayesian_analyzer_custom_assessment(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Ensure integrated analyzer processes safety and recommendations."""

    analyzer = IntegratedBayesianAnalyzer()

    # Patch analyzers to deterministic behaviours
    analyzer.technical_analyzer = SimpleNamespace(
        analyze_technical_aspects=lambda code, name: ["AsyncMock issue", "Cache miss"]
    )
    analyzer.nutrition_analyzer = SimpleNamespace(
        analyze_nutrition_safety=lambda code, name: [
            SimpleNamespace(success=False, error_message="Опасно высокий BMI")
        ],
    )

    def fake_analyze_safety(code: str, name: str) -> list[str]:
        return ["Logging sensitive data", "open without context"]

    monkeypatch.setattr(analyzer, "_analyze_safety_aspects", fake_analyze_safety)
    monkeypatch.setattr(
        analyzer,
        "_analyze_philosophy_compliance",
        lambda code, name: ["Нарушение философии"],
    )
    monkeypatch.setattr(
        analyzer,
        "_assess_business_impact",
        lambda *args: {"revenue": "risk", "cost": "increase"},
    )

    result = analyzer.analyze_test_comprehensively("code sample", "TestCase", "tests/sample.py")
    assert result.business_impact
    assert result.recommendations
    assert analyzer.integrated_results

"""
Unit tests to cover core logic of pytest_bayesian_plugin without relying on pytest runtime.
"""

import os
from typing import Any, List
from unittest.mock import MagicMock

from pytest_bayesian_plugin import BayesianPytestPlugin
from core.bayesian_test_analyzer import TestCategory, ErrorType


class _FakeMarker:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeItem:
    def __init__(
        self, markers: List[str], fspath: str = "tests/test_example.py", name: str = "test_x"
    ) -> None:
        self._markers = markers
        self.fspath = fspath
        self.name = name
        # Minimal attributes for context gathering
        self.fixturenames = []

    def iter_markers(self) -> List[Any]:
        return [_FakeMarker(m) for m in self._markers]


def test_determine_category_custom_marker_defaults_to_unit() -> None:
    plugin = BayesianPytestPlugin(
        category_markers=["regression"]
    )  # custom marker not mapped to enum
    item = _FakeItem(["regression"])  # will fall back to UNIT
    assert plugin._determine_test_category(item) == TestCategory.UNIT


def test_determine_category_known_marker_integration() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem(["integration"])  # known mapping
    assert plugin._determine_test_category(item) == TestCategory.INTEGRATION


def test_determine_category_custom_marker_integration() -> None:
    plugin = BayesianPytestPlugin(category_markers=["integration"])
    item = _FakeItem(["integration"])
    assert plugin._determine_test_category(item) == TestCategory.INTEGRATION


def test_determine_category_custom_marker_e2e() -> None:
    plugin = BayesianPytestPlugin(category_markers=["e2e"])
    item = _FakeItem(["e2e"])
    assert plugin._determine_test_category(item) == TestCategory.E2E


def test_determine_category_custom_marker_performance() -> None:
    plugin = BayesianPytestPlugin(category_markers=["performance"])
    item = _FakeItem(["performance"])
    assert plugin._determine_test_category(item) == TestCategory.PERFORMANCE


def test_determine_category_custom_marker_coverage() -> None:
    plugin = BayesianPytestPlugin(category_markers=["coverage"])
    item = _FakeItem(["coverage"])
    assert plugin._determine_test_category(item) == TestCategory.COVERAGE


def test_determine_category_custom_marker_monte_carlo() -> None:
    plugin = BayesianPytestPlugin(category_markers=["monte_carlo"])
    item = _FakeItem(["monte_carlo"])
    assert plugin._determine_test_category(item) == TestCategory.MONTE_CARLO


def test_determine_category_custom_marker_bayesian() -> None:
    plugin = BayesianPytestPlugin(category_markers=["bayesian"])
    item = _FakeItem(["bayesian"])
    assert plugin._determine_test_category(item) == TestCategory.BAYESIAN


def test_determine_category_fallback_path_name_e2e() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([], fspath="tests/e2e/test_flow.py", name="test_flow")
    assert plugin._determine_test_category(item) == TestCategory.E2E


def test_determine_category_fallback_path_performance() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([], fspath="tests/performance/test_speed.py", name="test_speed")
    assert plugin._determine_test_category(item) == TestCategory.PERFORMANCE


def test_determine_category_fallback_path_coverage() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([], fspath="tests/test_coverage.py", name="test_coverage")
    assert plugin._determine_test_category(item) == TestCategory.COVERAGE


def test_determine_category_fallback_path_monte_carlo() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([], fspath="tests/test_monte_carlo.py", name="test_mc")
    assert plugin._determine_test_category(item) == TestCategory.MONTE_CARLO


def test_determine_category_fallback_path_bayesian() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([], fspath="tests/test_bayesian.py", name="test_bayesian")
    assert plugin._determine_test_category(item) == TestCategory.BAYESIAN


def test_determine_category_exception_in_iter_markers() -> None:
    plugin = BayesianPytestPlugin()

    class _BrokenItem:
        def __init__(self) -> None:
            self.fspath = "tests/test_example.py"
            self.name = "test_x"

        def iter_markers(self) -> List[Any]:
            raise Exception("Marker iteration failed")

    item = _BrokenItem()
    # Should fallback to UNIT when marker iteration fails
    assert plugin._determine_test_category(item) == TestCategory.UNIT


def test_gather_test_context_flags_present() -> None:
    plugin = BayesianPytestPlugin()

    async def _afunc() -> None:  # async function to trigger is_async
        return None

    item = _FakeItem([])
    # Attach function attribute expected by the plugin
    item.function = _afunc  # type: ignore[attr-defined]
    ctx = plugin._gather_test_context(item)
    assert "is_async" in ctx and "has_mocks" in ctx and "coverage_related" in ctx


def test_gather_test_context_with_mocks() -> None:
    plugin = BayesianPytestPlugin()

    def _func_with_mock() -> None:
        from unittest.mock import Mock

        mock = Mock()

    item = _FakeItem([])
    item.function = _func_with_mock  # type: ignore[attr-defined]
    ctx = plugin._gather_test_context(item)
    assert ctx["has_mocks"] is True


def test_gather_test_context_coverage_related() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([], fspath="tests/test_coverage.py")
    ctx = plugin._gather_test_context(item)
    assert ctx["coverage_related"] is True


def test_gather_test_context_complex_dependencies() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([])
    item.fixturenames = ["fixture1", "fixture2", "fixture3", "fixture4"]  # > 3
    ctx = plugin._gather_test_context(item)
    assert ctx["complex_dependencies"] is True


def test_get_test_code_success() -> None:
    plugin = BayesianPytestPlugin()

    def _test_func() -> None:
        """Test function."""
        pass

    item = _FakeItem([])
    item.function = _test_func  # type: ignore[attr-defined]
    code = plugin._get_test_code(item)
    assert "def _test_func" in code or "_test_func" in code


def test_get_test_code_no_function() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([])
    code = plugin._get_test_code(item)
    assert code == ""


def test_get_test_code_exception(monkeypatch) -> None:
    plugin = BayesianPytestPlugin()

    def _func() -> None:
        pass

    # Make inspect.getsource raise OSError
    import inspect

    def _raise_oserror(*args, **kwargs) -> str:
        raise OSError("Could not get source")

    monkeypatch.setattr(inspect, "getsource", _raise_oserror)

    item = _FakeItem([])
    item.function = _func  # type: ignore[attr-defined]
    code = plugin._get_test_code(item)
    assert code == ""


class _FakeLongRepr:
    def __init__(self, message: str, reprtraceback: Any = None) -> None:
        self._msg = message
        self.reprtraceback = reprtraceback

    def __str__(self) -> str:  # fallback path parsing uses str()
        return self._msg


class _FakeReprTraceback:
    def __init__(self, reprentries: List[Any]) -> None:
        self.reprentries = reprentries


class _FakeReprEntry:
    def __init__(self, message: str) -> None:
        self.reprfileloc = _FakeReprFileLoc(message)


class _FakeReprFileLoc:
    def __init__(self, message: str) -> None:
        self.message = message


class _FakeReport:
    def __init__(self, msg: str, longrepr: Any = None) -> None:
        self.longrepr = longrepr or _FakeLongRepr(msg)


def test_analyze_failure_extracts_error_type() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("AssertionError: boom")
    err_type, msg = plugin._analyze_failure(report)
    assert err_type == ErrorType.ASSERTION_ERROR
    assert isinstance(msg, str) and "AssertionError" in msg


def test_analyze_failure_import_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("ImportError: No module named 'xyz'")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.IMPORT_ERROR


def test_analyze_failure_modulenotfound_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("ModuleNotFoundError: No module named 'xyz'")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.IMPORT_ERROR


def test_analyze_failure_type_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("TypeError: unsupported operand type")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.TYPE_ERROR


def test_analyze_failure_attribute_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("AttributeError: 'NoneType' object has no attribute 'x'")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.ATTRIBUTE_ERROR


def test_analyze_failure_value_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("ValueError: invalid value")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.VALUE_ERROR


def test_analyze_failure_unprocessable() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("Request is unprocessable")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.VALUE_ERROR


def test_analyze_failure_runtime_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("RuntimeError: something went wrong")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.RUNTIME_ERROR


def test_analyze_failure_timeout_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("TimeoutError: operation timed out")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.TIMEOUT_ERROR


def test_analyze_failure_generic_timeout() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("Operation timeout exceeded")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.TIMEOUT_ERROR


def test_analyze_failure_coverage_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("Coverage below threshold")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.COVERAGE_ERROR


def test_analyze_failure_mock_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("Mock was not called")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.MOCK_ERROR


def test_analyze_failure_patch_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("patch target not found")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.MOCK_ERROR


def test_analyze_failure_async_error() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("coroutine was never awaited")
    err_type, _ = plugin._analyze_failure(report)
    assert err_type == ErrorType.ASYNC_ERROR


def test_analyze_failure_no_longrepr() -> None:
    plugin = BayesianPytestPlugin()
    report = MagicMock()
    del report.longrepr  # type: ignore[attr-defined]
    err_type, msg = plugin._analyze_failure(report)
    assert err_type is None
    assert msg is None


def test_analyze_failure_with_reprtraceback() -> None:
    plugin = BayesianPytestPlugin()
    entry = _FakeReprEntry("AssertionError: test failed")
    traceback = _FakeReprTraceback([entry])
    # The longrepr string representation is used for error type detection
    longrepr = _FakeLongRepr("AssertionError: test failed", traceback)
    report = _FakeReport("", longrepr)
    err_type, msg = plugin._analyze_failure(report)
    assert err_type == ErrorType.ASSERTION_ERROR
    assert "AssertionError" in msg or "test failed" in msg


def test_print_diagnosis_disabled() -> None:
    plugin = BayesianPytestPlugin()
    diagnosis = MagicMock()
    diagnosis.most_likely_cause = "Test error"
    diagnosis.probability = 0.8
    diagnosis.confidence = 0.9
    diagnosis.evidence = ["Evidence 1"]
    diagnosis.recommendations = ["Fix 1"]
    diagnosis.alternative_causes = []

    # Should not print when env var is not set
    os.environ.pop("BAYESIAN_DIAG_VERBOSE", None)
    plugin._print_diagnosis(diagnosis)  # Should not raise


def test_print_diagnosis_enabled(monkeypatch) -> None:
    plugin = BayesianPytestPlugin()
    diagnosis = MagicMock()
    diagnosis.most_likely_cause = "Test error"
    diagnosis.probability = 0.8
    diagnosis.confidence = 0.9
    diagnosis.evidence = ["Evidence 1"]
    diagnosis.recommendations = ["Fix 1"]
    diagnosis.alternative_causes = [("Cause 2", 0.3)]

    monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "1")
    plugin._print_diagnosis(diagnosis)  # Should not raise

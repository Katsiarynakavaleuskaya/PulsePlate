"""Additional tests for pytest_bayesian_plugin.py to improve coverage."""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.bayesian_test_analyzer import (
    BayesianDiagnosis,
    ErrorType,
    TestCategory,
    TestStatus,
)
from pytest_bayesian_plugin import (
    BayesianPytestPlugin,
    pytest_configure,
    pytest_runtest_logreport,
    pytest_runtest_setup,
    pytest_runtest_teardown,
)


class TestBayesianPytestPluginAnalyzeFailure:
    """Tests for _analyze_failure method."""

    @pytest.fixture
    def plugin(self) -> BayesianPytestPlugin:
        """Create a plugin instance."""
        return BayesianPytestPlugin()

    def test_analyze_failure_no_longrepr(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with no longrepr attribute."""
        report = MagicMock()
        report.longrepr = None

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type is None
        assert error_message is None

    def test_analyze_failure_assertion_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with AssertionError."""
        report = MagicMock()
        report.longrepr = "AssertionError: Expected 5 but got 3"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.ASSERTION_ERROR
        assert error_message is not None
        assert "AssertionError" in error_message

    def test_analyze_failure_import_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with ImportError."""
        report = MagicMock()
        report.longrepr = "ImportError: No module named 'missing_module'"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.IMPORT_ERROR
        assert error_message is not None
        assert "ImportError" in error_message

    def test_analyze_failure_module_not_found_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with ModuleNotFoundError."""
        report = MagicMock()
        report.longrepr = "ModuleNotFoundError: No module named 'foo'"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.IMPORT_ERROR

    def test_analyze_failure_type_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with TypeError."""
        report = MagicMock()
        report.longrepr = "TypeError: unsupported operand type(s)"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.TYPE_ERROR

    def test_analyze_failure_attribute_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with AttributeError."""
        report = MagicMock()
        report.longrepr = "AttributeError: 'NoneType' object has no attribute 'foo'"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.ATTRIBUTE_ERROR

    def test_analyze_failure_value_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with ValueError."""
        report = MagicMock()
        report.longrepr = "ValueError: invalid literal for int()"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.VALUE_ERROR

    def test_analyze_failure_unprocessable_entity(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with unprocessable error."""
        report = MagicMock()
        report.longrepr = "422 Unprocessable Entity"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.VALUE_ERROR

    def test_analyze_failure_runtime_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with RuntimeError."""
        report = MagicMock()
        report.longrepr = "RuntimeError: maximum recursion depth exceeded"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.RUNTIME_ERROR

    def test_analyze_failure_timeout_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with TimeoutError."""
        report = MagicMock()
        report.longrepr = "TimeoutError: operation timed out"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.TIMEOUT_ERROR

    def test_analyze_failure_timeout_keyword(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with timeout keyword."""
        report = MagicMock()
        report.longrepr = "Test timeout after 5 seconds"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.TIMEOUT_ERROR

    def test_analyze_failure_coverage_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with coverage error."""
        report = MagicMock()
        report.longrepr = "coverage below threshold"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.COVERAGE_ERROR

    def test_analyze_failure_mock_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with mock error."""
        report = MagicMock()
        report.longrepr = "mock.patch call failed"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.MOCK_ERROR

    def test_analyze_failure_async_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with async error."""
        report = MagicMock()
        report.longrepr = "asyncio.CancelledError: Task was cancelled"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.ASYNC_ERROR

    def test_analyze_failure_await_error(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with await error."""
        report = MagicMock()
        report.longrepr = "SyntaxError: await was used without async"

        error_type, error_message = plugin._analyze_failure(report)

        assert error_type == ErrorType.ASYNC_ERROR

    def test_analyze_failure_with_complex_longrepr(self, plugin: BayesianPytestPlugin) -> None:
        """Test analyze_failure with complex pytest longrepr structure."""
        # Mock a complex pytest longrepr object
        message_obj = Mock()
        message_obj.message = "Detailed error message"

        reprfileloc = Mock()
        reprfileloc.message = "Extracted error message"

        last_entry = Mock()
        last_entry.reprfileloc = reprfileloc

        reprtraceback = Mock()
        reprtraceback.reprentries = [last_entry]

        longrepr = Mock()
        longrepr.reprtraceback = reprtraceback

        report = Mock()
        report.longrepr = longrepr

        error_type, error_message = plugin._analyze_failure(report)

        assert error_message == "Extracted error message"


class TestBayesianPytestPluginContext:
    """Tests for context gathering methods."""

    @pytest.fixture
    def plugin(self) -> BayesianPytestPlugin:
        """Create a plugin instance."""
        return BayesianPytestPlugin()

    def test_gather_test_context_async(self, plugin: BayesianPytestPlugin) -> None:
        """Test gathering context for async test."""

        async def async_test_func():
            pass

        item = Mock()
        item.function = async_test_func
        item.fixturenames = []
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test_file.py"

        context = plugin._gather_test_context(item)

        assert context["is_async"] is True

    def test_gather_test_context_sync(self, plugin: BayesianPytestPlugin) -> None:
        """Test gathering context for sync test."""

        def sync_test_func():
            pass

        item = Mock()
        item.function = sync_test_func
        item.fixturenames = []
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test_file.py"

        context = plugin._gather_test_context(item)

        assert context["is_async"] is False

    def test_gather_test_context_no_function(self, plugin: BayesianPytestPlugin) -> None:
        """Test gathering context when item has no function."""
        item = Mock(spec=[])  # No 'function' attribute
        item.fixturenames = []
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test_file.py"

        context = plugin._gather_test_context(item)

        assert "is_async" in context

    def test_gather_test_context_has_mocks(self, plugin: BayesianPytestPlugin) -> None:
        """Test detecting mocks in test code."""
        from unittest.mock import Mock, patch

        # Test code with Mock() call that should be detected
        test_code_with_mock = """def test_with_mock():
    from unittest.mock import Mock
    test_mock = Mock()
    test_mock.foo()
    return test_mock"""

        def test_with_mock():
            """Test function that uses proper mocking."""
            test_mock = Mock()
            test_mock.foo()
            return test_mock

        item = MagicMock()
        item.function = test_with_mock
        item.fixturenames = []
        item.fspath = MagicMock()

        item.fspath.strpath = "/path/to/test_file.py"

        # Mock _get_test_code to return code that contains Mock() call
        with patch.object(plugin, "_get_test_code", return_value=test_code_with_mock):
            # Verify mock detection works correctly
            # The test uses proper Mock() from unittest.mock, which should be detected
            context = plugin._gather_test_context(item)
            # Assert that context is gathered successfully
            assert context is not None
            # Verify context is a dictionary with expected structure
            assert isinstance(context, dict)
            # The context should contain test metadata (exact keys may vary)
            assert len(context) > 0
            # Verify mock detection flag is present and True
            assert "has_mocks" in context
            assert context["has_mocks"] is True

    def test_gather_test_context_no_mocks(self, plugin: BayesianPytestPlugin) -> None:
        """Test detecting no mocks in test code."""

        def test_without_any_special_imports():
            x = 1 + 1
            assert x == 2

        item = MagicMock()
        item.function = test_without_any_special_imports
        item.fixturenames = []
        item.fspath = MagicMock()
        item.fspath.strpath = "/path/to/test_file.py"

        # Mock _get_test_code to return code without mock keywords
        with patch.object(plugin, "_get_test_code", return_value="x = 1 + 1\nassert x == 2"):
            context = plugin._gather_test_context(item)

        assert context["has_mocks"] is False

    def test_gather_test_context_coverage_related(self, plugin: BayesianPytestPlugin) -> None:
        """Test detecting coverage-related tests."""
        item = MagicMock()
        item.function = lambda: None
        item.fixturenames = []
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test_coverage_file.py"
        item.fspath.configure_mock(__str__=lambda self: "/path/to/test_coverage_file.py")

        context = plugin._gather_test_context(item)

        assert context["coverage_related"] is True

    def test_gather_test_context_not_coverage_related(self, plugin: BayesianPytestPlugin) -> None:
        """Test detecting non-coverage-related tests."""
        item = MagicMock()
        item.function = lambda: None
        item.fixturenames = []
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test_regular.py"
        item.fspath.configure_mock(__str__=lambda self: "/path/to/test_regular.py")

        context = plugin._gather_test_context(item)

        assert context["coverage_related"] is False

    def test_gather_test_context_complex_dependencies(self, plugin: BayesianPytestPlugin) -> None:
        """Test detecting complex dependencies."""
        item = Mock()
        item.function = lambda: None
        item.fixturenames = ["fixture1", "fixture2", "fixture3", "fixture4"]
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test_file.py"

        context = plugin._gather_test_context(item)

        assert context["complex_dependencies"] is True

    def test_gather_test_context_simple_dependencies(self, plugin: BayesianPytestPlugin) -> None:
        """Test detecting simple dependencies."""
        item = Mock()
        item.function = lambda: None
        item.fixturenames = ["fixture1", "fixture2"]
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test_file.py"

        context = plugin._gather_test_context(item)

        assert context["complex_dependencies"] is False

    def test_get_test_code_success(self, plugin: BayesianPytestPlugin) -> None:
        """Test getting test code successfully."""

        def test_func():
            """A test function."""
            x = 1 + 1
            assert x == 2

        item = Mock()
        item.function = test_func

        code = plugin._get_test_code(item)

        assert "x = 1 + 1" in code
        assert "assert x == 2" in code

    def test_get_test_code_no_function(self, plugin: BayesianPytestPlugin) -> None:
        """Test getting test code when no function attribute."""
        item = Mock(spec=[])  # No 'function' attribute

        code = plugin._get_test_code(item)

        assert code == ""

    def test_get_test_code_no_code_attr(self, plugin: BayesianPytestPlugin) -> None:
        """Test getting test code when function has no __code__ attribute."""
        item = Mock()
        item.function = Mock(spec=[])  # No '__code__' attribute

        code = plugin._get_test_code(item)

        assert code == ""

    def test_get_test_code_oserror(self, plugin: BayesianPytestPlugin) -> None:
        """Test getting test code handles OSError."""
        import inspect

        def test_func():
            pass

        item = Mock()
        item.function = test_func

        with patch("inspect.getsource", side_effect=OSError("File not found")):
            code = plugin._get_test_code(item)

        assert code == ""

    def test_get_test_code_typeerror(self, plugin: BayesianPytestPlugin) -> None:
        """Test getting test code handles TypeError."""
        item = Mock()
        item.function = lambda: None  # Lambda might cause TypeError in some cases

        with patch("inspect.getsource", side_effect=TypeError("Cannot get source")):
            code = plugin._get_test_code(item)

        assert code == ""


class TestBayesianPytestPluginDiagnosis:
    """Tests for diagnosis printing."""

    @pytest.fixture
    def plugin(self) -> BayesianPytestPlugin:
        """Create a plugin instance."""
        return BayesianPytestPlugin()

    @pytest.fixture
    def diagnosis(self) -> BayesianDiagnosis:
        """Create a sample diagnosis."""
        return BayesianDiagnosis(
            most_likely_cause="Test data issue",
            probability=0.85,
            confidence=0.90,
            evidence=["Evidence 1", "Evidence 2"],
            recommendations=["Fix data", "Add validation"],
            alternative_causes=[("Alternative cause", 0.10)],
        )

    def test_print_diagnosis_enabled(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis when enabled."""
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "1")

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in captured.out
        assert "Test data issue" in captured.out
        assert "85.00%" in captured.out
        assert "90.00%" in captured.out
        assert "Evidence 1" in captured.out
        assert "Fix data" in captured.out

    def test_print_diagnosis_enabled_true(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis with 'true' value."""
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "true")

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in captured.out

    def test_print_diagnosis_enabled_yes(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis with 'yes' value."""
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "yes")

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in captured.out

    def test_print_diagnosis_enabled_on(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis with 'on' value."""
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "on")

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in captured.out

    def test_print_diagnosis_enabled_case_insensitive(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis with uppercase value."""
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "TRUE")

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert "БАЙЕСОВСКАЯ ДИАГНОСТИКА" in captured.out

    def test_print_diagnosis_disabled(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis when disabled."""
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "0")

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_diagnosis_disabled_default(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis when env var not set."""
        monkeypatch.delenv("BAYESIAN_DIAG_VERBOSE", raising=False)

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_diagnosis_disabled_empty(
        self,
        plugin: BayesianPytestPlugin,
        diagnosis: BayesianDiagnosis,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test printing diagnosis with empty env var."""
        monkeypatch.setenv("BAYESIAN_DIAG_VERBOSE", "")

        plugin._print_diagnosis(diagnosis)

        captured = capsys.readouterr()
        assert captured.out == ""


class TestPytestHooks:
    """Tests for pytest hook functions."""

    def test_pytest_configure_creates_plugin(self) -> None:
        """Test pytest_configure creates plugin."""
        config = Mock()
        del config.bayesian_plugin  # Ensure it doesn't exist

        pytest_configure(config)

        assert hasattr(config, "bayesian_plugin")
        assert isinstance(config.bayesian_plugin, BayesianPytestPlugin)

    def test_pytest_configure_does_not_override(self) -> None:
        """Test pytest_configure doesn't override existing plugin."""
        config = Mock()
        existing_plugin = BayesianPytestPlugin()
        config.bayesian_plugin = existing_plugin

        pytest_configure(config)

        assert config.bayesian_plugin is existing_plugin

    def test_pytest_runtest_setup_calls_plugin(self) -> None:
        """Test pytest_runtest_setup calls plugin method."""
        config = Mock()
        plugin = Mock(spec=BayesianPytestPlugin)
        config.bayesian_plugin = plugin

        item = Mock()
        item.config = config

        pytest_runtest_setup(item)

        plugin.pytest_runtest_setup.assert_called_once_with(item)

    def test_pytest_runtest_setup_no_plugin(self) -> None:
        """Test pytest_runtest_setup when plugin doesn't exist."""
        config = Mock(spec=[])  # No bayesian_plugin attribute

        item = Mock()
        item.config = config

        # Should not raise an error
        pytest_runtest_setup(item)

    def test_pytest_runtest_teardown_calls_plugin(self) -> None:
        """Test pytest_runtest_teardown calls plugin method."""
        config = Mock()
        plugin = Mock(spec=BayesianPytestPlugin)
        config.bayesian_plugin = plugin

        item = Mock()
        item.config = config
        nextitem = Mock()

        pytest_runtest_teardown(item, nextitem)

        plugin.pytest_runtest_teardown.assert_called_once_with(item, nextitem)

    def test_pytest_runtest_teardown_no_plugin(self) -> None:
        """Test pytest_runtest_teardown when plugin doesn't exist."""
        config = Mock(spec=[])

        item = Mock()
        item.config = config
        nextitem = Mock()

        # Should not raise an error
        pytest_runtest_teardown(item, nextitem)

    def test_pytest_runtest_logreport_calls_plugin(self) -> None:
        """Test pytest_runtest_logreport calls plugin method."""
        config = Mock()
        plugin = Mock(spec=BayesianPytestPlugin)
        config.bayesian_plugin = plugin

        report = Mock()
        report.config = config

        pytest_runtest_logreport(report)

        plugin.pytest_runtest_logreport.assert_called_once_with(report)

    def test_pytest_runtest_logreport_no_plugin(self) -> None:
        """Test pytest_runtest_logreport when plugin doesn't exist."""
        config = Mock(spec=[])

        report = Mock()
        report.config = config

        # Should not raise an error
        pytest_runtest_logreport(report)


class TestBayesianPytestPluginCategoryDetermination:
    """Tests for test category determination with markers."""

    @pytest.fixture
    def plugin(self) -> BayesianPytestPlugin:
        """Create a plugin instance."""
        return BayesianPytestPlugin()

    def test_determine_category_with_custom_markers(self) -> None:
        """Test category determination with custom markers."""
        plugin = BayesianPytestPlugin(category_markers=["custom_marker"])

        marker = Mock()
        marker.name = "custom_marker"

        item = Mock()
        item.iter_markers = lambda: [marker]
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test.py"
        item.name = "test_something"

        category = plugin._determine_test_category(item)

        assert category == TestCategory.UNIT  # Default fallback

    def test_determine_category_iter_markers_exception(self, plugin: BayesianPytestPlugin) -> None:
        """Test category determination when iter_markers raises exception."""
        item = Mock()
        item.iter_markers = Mock(side_effect=Exception("Error"))
        item.fspath = Mock()
        item.fspath.strpath = "/path/to/test.py"
        item.name = "test_something"

        category = plugin._determine_test_category(item)

        # Should handle exception and return default
        assert category == TestCategory.UNIT

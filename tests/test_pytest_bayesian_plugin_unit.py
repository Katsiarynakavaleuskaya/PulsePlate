"""
Unit tests to cover core logic of pytest_bayesian_plugin without relying on pytest runtime.
"""

from typing import Any, List

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


def test_determine_category_fallback_path_name_e2e() -> None:
    plugin = BayesianPytestPlugin()
    item = _FakeItem([], fspath="tests/e2e/test_flow.py", name="test_flow")
    assert plugin._determine_test_category(item) == TestCategory.E2E


def test_gather_test_context_flags_present() -> None:
    plugin = BayesianPytestPlugin()

    async def _afunc() -> None:  # async function to trigger is_async
        return None

    item = _FakeItem([])
    # Attach function attribute expected by the plugin
    item.function = _afunc  # type: ignore[attr-defined]
    ctx = plugin._gather_test_context(item)
    assert "is_async" in ctx and "has_mocks" in ctx and "coverage_related" in ctx


class _FakeLongRepr:
    def __init__(self, message: str) -> None:
        self._msg = message
        self.reprtraceback = None

    def __str__(self) -> str:  # fallback path parsing uses str()
        return self._msg


class _FakeReport:
    def __init__(self, msg: str) -> None:
        self.longrepr = _FakeLongRepr(msg)


def test_analyze_failure_extracts_error_type() -> None:
    plugin = BayesianPytestPlugin()
    report = _FakeReport("AssertionError: boom")
    err_type, msg = plugin._analyze_failure(report)
    assert err_type == ErrorType.ASSERTION_ERROR
    assert isinstance(msg, str) and "AssertionError" in msg

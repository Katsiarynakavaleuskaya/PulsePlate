from types import SimpleNamespace
from typing import Iterator

from pytest_bayesian_plugin import BayesianPytestPlugin
from core.bayesian_test_analyzer import TestCategory


class DummyMarker:
    def __init__(self, name: str) -> None:
        self.name = name


class DummyItem:
    def __init__(
        self, markers: list[str], path: str = "tests/test_sample.py", name: str = "test_x"
    ) -> None:
        self._markers = [DummyMarker(m) for m in markers]
        self.fspath = SimpleNamespace(**{"__str__": lambda self=self: path})
        self.name = name

    def iter_markers(self) -> Iterator[DummyMarker]:
        return iter(self._markers)


def test_determine_category_custom_marker_fallback() -> None:
    """Test that unmapped custom markers fallback to UNIT category."""
    plugin = BayesianPytestPlugin(category_markers=["regression", "integration"])
    item = DummyItem(["regression"])
    assert plugin._determine_test_category(item) == TestCategory.UNIT


def test_determine_category_custom_marker_known() -> None:
    """Test that known custom markers map to their correct category."""
    plugin = BayesianPytestPlugin(category_markers=["regression", "integration"])
    item2 = DummyItem(["integration"])
    assert plugin._determine_test_category(item2) == TestCategory.INTEGRATION

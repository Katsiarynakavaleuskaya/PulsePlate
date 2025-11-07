from types import SimpleNamespace

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

    def iter_markers(self):  # type: ignore[override]
        return iter(self._markers)


def test_determine_category_custom_marker() -> None:
    plugin = BayesianPytestPlugin(category_markers=["regression", "integration"])  # custom + known
    item = DummyItem(["regression"])  # not mapped, should fallback to UNIT
    assert plugin._determine_test_category(item) == TestCategory.UNIT

    item2 = DummyItem(["integration"])  # known -> INTEGRATION
    assert plugin._determine_test_category(item2) == TestCategory.INTEGRATION

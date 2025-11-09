from pytest_bayesian_plugin import BayesianPytestPlugin
from core.bayesian_test_analyzer import TestCategory
from tests.conftest import DummyItem


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

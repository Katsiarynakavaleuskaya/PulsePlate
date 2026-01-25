#!/usr/bin/env python3
"""
Targeted tests that close remaining diff-cover gaps across Bayesian modules.

These tests focus on rarely used branches (error handling, fallbacks, and
small helper functions) to keep coverage high without touching production
logic.
"""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.bayesian_recommendations import get_error_type_key
from core.bayesian_technical_utils import analyze_technical_aspects_common
from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    ErrorType,
    TestCategory,
    TestRecord,
    TestStatus,
)
from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessTestResult,
)
from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer, IntegratedTestResult

# --- bayesian_recommendations -------------------------------------------------


def test_get_error_type_key_type_error_for_non_enum() -> None:
    """Non-enum input should raise a clear TypeError."""
    with pytest.raises(TypeError):
        get_error_type_key("not-an-enum")  # type: ignore[arg-type]


# --- bayesian_technical_utils -------------------------------------------------


def test_analyze_technical_aspects_unhandled_raise() -> None:
    """Unhandled raise without try/raises markers should be reported."""
    code = "def bad():\n    raise ValueError('boom')\n"
    issues = analyze_technical_aspects_common(code)
    assert "Exception raised without handling" in issues


# --- bayesian_test_analyzer ---------------------------------------------------


def test_test_history_setter_keeps_alias() -> None:
    analyzer = BayesianTestAnalyzer()
    execution = TestRecord(
        test_name="t",
        category=TestCategory.UNIT,
        result=TestStatus.PASSED,
        error_type=None,
        error_message=None,
        execution_time=0.1,
        coverage_percentage=None,
        timestamp=datetime.now(timezone.utc),
    )
    analyzer.test_history = [execution]
    assert analyzer.execution_history == [execution]


def test_load_history_file_not_found(tmp_path: Path) -> None:
    """Missing history file should be handled quietly (FileNotFoundError branch)."""
    missing = tmp_path / "no_history.json"
    analyzer = BayesianTestAnalyzer(data_file=missing)
    assert analyzer.execution_history == []
    # Persist stays enabled because data_file was provided
    assert analyzer.persist_enabled is True


def test_load_history_generic_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Generic exception while opening history should be caught."""
    history_path = tmp_path / "history.json"
    history_path.write_text("[]", encoding="utf-8")

    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if Path(file) == history_path:
            raise RuntimeError("boom")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    analyzer = BayesianTestAnalyzer(data_file=history_path)
    # History load failed but analyzer should remain usable
    assert analyzer.execution_history == []


# --- business_bayesian_analyzer ----------------------------------------------


def _set_bba_module_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point business analyzer module paths to a temporary directory."""
    import core.business_bayesian_analyzer as bmod

    fake_file = tmp_path / "core" / "business_bayesian_analyzer.py"
    monkeypatch.setattr(bmod, "__file__", str(fake_file))
    return fake_file.parent.parent


def test_load_business_knowledge_without_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When PyYAML is missing, loader should log and fall back to defaults."""
    config_root = _set_bba_module_file(monkeypatch, tmp_path)
    config_path = config_root / "config"
    config_path.mkdir(parents=True, exist_ok=True)
    (config_path / "business_knowledge.yaml").write_text("key: value", encoding="utf-8")

    monkeypatch.setattr(BusinessBayesianAnalyzer, "_import_yaml_module", staticmethod(lambda: None))

    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_business_knowledge()
    assert "revenue_streams" in data


def test_load_monetization_strategies_import_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cover locale normalization fallback and YAML load failure branches."""
    import core.business_bayesian_analyzer as bmod
    import yaml

    config_root = _set_bba_module_file(monkeypatch, tmp_path)
    config_dir = config_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    target_yaml = config_dir / "monetization_strategies.en.yaml"
    target_yaml.write_text("pricing_models:\n  - bad", encoding="utf-8")

    # Mock core.i18n import to raise ImportError using sys.modules
    import sys

    # Remove module instead of setting to None (prevents sys.modules None poisoning)
    module_to_restore = None
    if "core.i18n" in sys.modules:
        module_to_restore = sys.modules["core.i18n"]
        del sys.modules["core.i18n"]

    try:
        monkeypatch.setattr(
            BusinessBayesianAnalyzer, "_import_yaml_module", staticmethod(lambda: yaml)
        )

        analyzer = BusinessBayesianAnalyzer()
        data = analyzer._load_monetization_strategies(locale=None)
        assert "pricing_models" in data
    finally:
        # Restore module
        if module_to_restore is not None:
            sys.modules["core.i18n"] = module_to_restore


def test_load_cost_rules_os_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Open errors while reading cost rules should fall back gracefully."""
    import core.business_bayesian_analyzer as bmod
    import yaml

    config_root = _set_bba_module_file(monkeypatch, tmp_path)
    config_dir = config_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    target_yaml = config_dir / "cost_optimization_rules.yaml"
    target_yaml.write_text("infrastructure: {}\n", encoding="utf-8")

    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if Path(file) == target_yaml:
            raise OSError("cannot read")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(BusinessBayesianAnalyzer, "_import_yaml_module", staticmethod(lambda: yaml))
    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_cost_optimization_rules()
    assert "infrastructure" in data


def test_analyze_monetization_valueerror_skip() -> None:
    """Unparseable price values should be skipped without raising."""
    analyzer = BusinessBayesianAnalyzer()
    code = "price = 'abc'\nbilling = True\n"
    results = analyzer._analyze_monetization(code, "test_bad_price")
    # Should not crash and return a list (may be empty)
    assert isinstance(results, list)


def test_cost_optimization_regex_fallback_for_broken_code() -> None:
    """Broken code triggers regex-based nested loop detection branch."""
    analyzer = BusinessBayesianAnalyzer()
    broken_code = "for i in range(3):\n for j in range(2):\n    query = j\n"
    issues = analyzer._analyze_cost_optimization(broken_code, "broken_nested_loop")
    assert any(res.business_category == BusinessCategory.COST_OPTIMIZATION for res in issues)


def test_cost_savings_recommendations_cover_all_categories() -> None:
    """Populate issues to trigger all recommendation blocks."""
    analyzer = BusinessBayesianAnalyzer()
    analyzer.test_results = [
        BusinessTestResult(
            test_name="cost",
            success=False,
            business_category=BusinessCategory.COST_OPTIMIZATION,
        ),
        BusinessTestResult(
            test_name="ops",
            success=False,
            business_category=BusinessCategory.OPERATIONAL_EFFICIENCY,
        ),
        BusinessTestResult(
            test_name="monet",
            success=False,
            business_category=BusinessCategory.MONETIZATION,
        ),
    ]
    recs = analyzer.generate_cost_savings_recommendations()
    # Check for recommendation categories instead of locale-dependent phrases
    # COST_OPTIMIZATION recommendations should mention pricing/infrastructure
    # OPERATIONAL_EFFICIENCY recommendations should mention automation/testing
    # MONETIZATION recommendations should mention pricing models/tiers
    has_cost_opt = any(
        any(
            keyword in r.lower()
            for keyword in ["pricing", "spot", "infrastructure", "инстанс", "ценообразован"]
        )
        for r in recs
    )
    has_ops_efficiency = any(
        any(
            keyword in r.lower()
            for keyword in ["automat", "testing", "тестирован", "автоматизиров"]
        )
        for r in recs
    )
    has_monetization = any(
        any(
            keyword in r.lower()
            for keyword in ["tier", "pricing model", "многоуровнев", "ценообразован"]
        )
        for r in recs
    )
    assert has_cost_opt, "Expected COST_OPTIMIZATION recommendation"
    assert has_ops_efficiency, "Expected OPERATIONAL_EFFICIENCY recommendation"
    assert has_monetization, "Expected MONETIZATION recommendation"


# --- integrated_bayesian_analyzer --------------------------------------------


def test_is_in_test_or_mock_context_importfrom_mock_and_testcase() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    code = """
from mock import patch
from unittest import TestCase

class MyTest(TestCase):
    @patch('mod.fn')
    def test_something(self):
        pass
"""
    assert analyzer._is_in_test_or_mock_context(code) is True


def test_check_unsafe_file_opens_contextlib_closing() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    code = """
from contextlib import closing

def use_file():
    with closing(open("x.txt")) as f:
        return f.read()
"""
    assert analyzer._check_unsafe_file_opens(code) is False


def test_sensitive_logging_detects_name_and_fstring() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    code = """
import logging
password_token = "secret"
logger.info(password_token)
logger.info(f"token={password_token}")
"""
    assert analyzer._check_sensitive_data_logging(code) is True
    issues = analyzer._analyze_safety_aspects(code, "prod")
    assert any("Logging sensitive data" in msg for msg in issues)


def test_philosophy_health_indicator_missing() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    violations = analyzer._analyze_philosophy_compliance("print('x')", "health_check")
    assert any("does not verify key metrics" in msg for msg in violations)


def test_generate_integrated_recommendations_all_sections() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    recs = analyzer._generate_integrated_recommendations(["t1"], ["n1"], ["s1"], ["p1"])
    assert any("technical issues" in r for r in recs)
    assert any("nutrition safety" in r for r in recs)
    assert any("data safety" in r for r in recs)
    assert any("system philosophy" in r for r in recs)


def test_generate_strategy_recommendations_thresholds() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    analyzer.integrated_results = [
        IntegratedTestResult(
            test_name="t1",
            success=False,
            technical_issues=["tech"],
            nutrition_issues=["nut"],
            safety_issues=["safe"],
            philosophy_violations=["phil"],
            business_impact="high",
            overall_risk_level="high",
            recommendations=[],
        ),
        IntegratedTestResult(
            test_name="t2",
            success=False,
            technical_issues=["tech"],
            nutrition_issues=["nut"],
            safety_issues=["safe"],
            philosophy_violations=["phil"],
            business_impact="high",
            overall_risk_level="high",
            recommendations=[],
        ),
    ]

    recs = analyzer._generate_system_recommendations()
    # Locale-agnostic assertions: check for both English and Russian keywords
    has_technical = any(
        any(
            keyword in r.lower()
            for keyword in ["technical refactor", "технический рефакторинг", "refactor"]
        )
        for r in recs
    )
    has_nutrition = any(
        any(keyword in r.lower() for keyword in ["nutrition safety", "nutrition", "питан"])
        for r in recs
    )
    has_security = any(
        any(keyword in r.lower() for keyword in ["security audit", "audit", "безопасн"])
        for r in recs
    )
    has_philosophy = any(
        any(keyword in r.lower() for keyword in ["philosophy", "философ"]) for r in recs
    )
    assert has_technical, "Expected technical refactoring recommendation"
    assert has_nutrition, "Expected nutrition safety recommendation"
    assert has_security, "Expected security audit recommendation"
    assert has_philosophy, "Expected philosophy recommendation"

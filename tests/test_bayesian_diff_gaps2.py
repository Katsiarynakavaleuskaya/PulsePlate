#!/usr/bin/env python3
"""
Additional gap-closing tests for Bayesian analyzers.
"""

import builtins
import io
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    TestRecord,
    TestStatus,
    ErrorType,
    TestCategory,
)
from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessTestResult,
)
from core.integrated_bayesian_analyzer import IntegratedBayesianAnalyzer


def test_bayesian_test_analyzer_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid history JSON should trigger JSONDecodeError path."""
    history = tmp_path / "history.json"
    history.write_text("{bad json", encoding="utf-8")
    analyzer = BayesianTestAnalyzer(data_file=history)
    assert analyzer.execution_history == []


def test_bayesian_test_analyzer_file_not_found(tmp_path: Path) -> None:
    """Missing history file should hit FileNotFoundError branch."""
    missing = tmp_path / "missing.json"
    analyzer = BayesianTestAnalyzer(data_file=missing)
    assert analyzer.execution_history == []


def test_bayesian_test_analyzer_health_score_zero_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Single execution with no time should still yield bounded health score."""
    analyzer = BayesianTestAnalyzer()
    rec = TestRecord(
        test_name="t1",
        category=TestCategory.UNIT,
        result=TestStatus.PASSED,
        error_type=None,
        error_message=None,
        execution_time=0.0,
        coverage_percentage=90.0,
        timestamp=(
            analyzer._current_timestamp()
            if hasattr(analyzer, "_current_timestamp")
            else datetime.now(timezone.utc)
        ),
    )
    analyzer.execution_history.append(rec)
    score = analyzer.get_test_health_score("t1")
    assert 0.0 <= score <= 1.0, "Health score should be in range [0, 1]"


def test_business_load_knowledge_unicode_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UnicodeDecodeError during knowledge load should fall back to defaults."""
    import core.business_bayesian_analyzer as bmod

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "business_knowledge.yaml"
    yaml_path.write_text("dummy: 1", encoding="utf-8")

    def fake_open(file, *args, **kwargs):
        if Path(file) == yaml_path:
            raise UnicodeDecodeError("utf-8", b"bad", 0, 1, "bad")
        return builtins.open(file, *args, **kwargs)

    monkeypatch.setattr(bmod, "__file__", str(tmp_path / "core" / "business_bayesian_analyzer.py"))
    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(
        BusinessBayesianAnalyzer, "_import_yaml_module", staticmethod(lambda: __import__("yaml"))
    )

    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_business_knowledge()
    assert "revenue_streams" in data


def test_business_monetization_oserror(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """OSError while loading monetization YAML should fall back to defaults."""
    import core.business_bayesian_analyzer as bmod
    import yaml

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "monetization_strategies.en.yaml"
    yaml_path.write_text("pricing_models:\n  basic: 1", encoding="utf-8")

    def fake_open(file, *args, **kwargs):
        if Path(file) == yaml_path:
            raise OSError("cannot read")
        return builtins.open(file, *args, **kwargs)

    monkeypatch.setattr(bmod, "__file__", str(tmp_path / "core" / "business_bayesian_analyzer.py"))
    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(BusinessBayesianAnalyzer, "_import_yaml_module", staticmethod(lambda: yaml))

    analyzer = BusinessBayesianAnalyzer()
    data = analyzer._load_monetization_strategies(locale="en")
    assert "pricing_models" in data


def test_business_remove_comments_triple_quotes() -> None:
    analyzer = BusinessBayesianAnalyzer()
    code = "'''\ncomment block\n'''\ncode = 1  # inline comment"
    cleaned = analyzer._remove_comments(code)
    assert "comment block" in cleaned
    assert "inline comment" not in cleaned


def test_business_valueerror_price_parsing_branch() -> None:
    analyzer = BusinessBayesianAnalyzer()
    code = "price = 12efoo\n"
    results = analyzer._analyze_monetization(code, "bad_price")
    assert isinstance(results, list)


def test_business_data_monetization_recommendations() -> None:
    """Trigger all recommendation buckets in revenue optimization."""
    analyzer = BusinessBayesianAnalyzer(locale="ru")  # Explicitly set Russian locale
    analyzer.test_results = [
        BusinessTestResult(
            test_name="acq",
            success=False,
            business_category=BusinessCategory.CUSTOMER_ACQUISITION,
        ),
        BusinessTestResult(
            test_name="ret",
            success=False,
            business_category=BusinessCategory.USER_RETENTION,
        ),
        BusinessTestResult(
            test_name="data",
            success=False,
            business_category=BusinessCategory.DATA_MONETIZATION,
        ),
    ]
    recs = analyzer.generate_revenue_optimization_recommendations()
    assert any("онбординга" in r for r in recs)
    assert any("лояльности" in r for r in recs)
    assert any("монет" in r.lower() for r in recs)


def test_integrated_testcase_and_mock_patch_detection() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    code = """
from unittest import TestCase
import mock

@mock.patch('x.y')
class MyTest(TestCase):
    def test_ok(self):
        pass
"""
    assert analyzer._is_in_test_or_mock_context(code) is True


def test_integrated_sensitive_logging_formatted_value_and_joined() -> None:
    analyzer = IntegratedBayesianAnalyzer()
    code = 'import logging\nlogger.info(f"pwd={password}")\nlogger.info("token=" f"{token}")\n'
    assert analyzer._check_sensitive_data_logging(code) is True


def test_bayesian_test_analyzer_uniform_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """When evidence is zero, cause_probabilities should fall back to uniform."""
    analyzer = BayesianTestAnalyzer()

    monkeypatch.setattr(analyzer, "_extract_symptoms", lambda msg, ctx: [])
    monkeypatch.setattr(analyzer, "_calculate_evidence", lambda symptoms, cases: 0.0)
    diagnosis = analyzer.diagnose_test_failure("t", "", {})
    assert diagnosis.most_likely_cause in [et.value for et in ErrorType]

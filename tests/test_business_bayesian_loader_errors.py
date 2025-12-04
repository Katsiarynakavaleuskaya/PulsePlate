from pathlib import Path

import pytest

from core.business_bayesian_analyzer import BusinessBayesianAnalyzer


def _write_invalid_yaml(path: Path) -> None:
    """Write an intentionally invalid YAML file at the provided Path for testing YAML parse errors.

    Args:
        path: Path where the invalid YAML file should be written

    Returns:
        None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(":\n  bad: [", encoding="utf-8")


@pytest.fixture
def patched_analyzer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BusinessBayesianAnalyzer:
    """Fixture that provides a BusinessBayesianAnalyzer with patched __file__ for testing YAML loading."""
    import core.business_bayesian_analyzer as bba_module

    monkeypatch.setattr(
        bba_module, "__file__", str(tmp_path / "core" / "business_bayesian_analyzer.py")
    )
    return BusinessBayesianAnalyzer()


def test_load_business_knowledge_invalid_yaml_fallback(
    tmp_path: Path, patched_analyzer: BusinessBayesianAnalyzer
) -> None:
    """Test fallback to defaults when business_knowledge.yaml is invalid."""
    config_dir = tmp_path / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "business_knowledge.yaml"
    _write_invalid_yaml(yaml_path)

    data = patched_analyzer._load_business_knowledge()
    assert "subscription" in data["revenue_streams"]


def test_load_monetization_strategies_invalid_yaml(
    tmp_path: Path, patched_analyzer: BusinessBayesianAnalyzer
) -> None:
    """Test fallback to defaults when monetization_strategies.{locale}.yaml is invalid."""
    config_dir = tmp_path / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "monetization_strategies.zz.yaml"
    _write_invalid_yaml(yaml_path)

    data = patched_analyzer._load_monetization_strategies("zz")
    assert "pricing_models" in data


def test_load_cost_optimization_rules_invalid_yaml(
    tmp_path: Path, patched_analyzer: BusinessBayesianAnalyzer
) -> None:
    """Test fallback to defaults when cost_optimization_rules.yaml is invalid."""
    config_dir = tmp_path / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = config_dir / "cost_optimization_rules.yaml"
    _write_invalid_yaml(yaml_path)

    data = patched_analyzer._load_cost_optimization_rules()
    assert "infrastructure" in data

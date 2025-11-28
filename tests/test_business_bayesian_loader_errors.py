import os
from pathlib import Path

import pytest

from core.business_bayesian_analyzer import BusinessBayesianAnalyzer


def _write_invalid_yaml(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(":\n  bad: [", encoding="utf-8")


def test_load_business_knowledge_invalid_yaml_fallback():
    config_dir = Path(__file__).resolve().parent.parent / "core" / "config"
    yaml_path = config_dir / "business_knowledge.yaml"
    _write_invalid_yaml(yaml_path)
    try:
        analyzer = BusinessBayesianAnalyzer()
        data = analyzer._load_business_knowledge()
        assert "subscription" in data["revenue_streams"]
    finally:
        if yaml_path.exists():
            yaml_path.unlink()


def test_load_monetization_strategies_invalid_yaml():
    config_dir = Path(__file__).resolve().parent.parent / "core" / "config"
    yaml_path = config_dir / "monetization_strategies.zz.yaml"
    _write_invalid_yaml(yaml_path)
    try:
        analyzer = BusinessBayesianAnalyzer()
        data = analyzer._load_monetization_strategies("zz")
        assert "pricing_models" in data
    finally:
        if yaml_path.exists():
            yaml_path.unlink()


def test_load_cost_optimization_rules_invalid_yaml():
    config_dir = Path(__file__).resolve().parent.parent / "core" / "config"
    yaml_path = config_dir / "cost_optimization_rules.yaml"
    _write_invalid_yaml(yaml_path)
    try:
        analyzer = BusinessBayesianAnalyzer()
        data = analyzer._load_cost_optimization_rules()
        assert "infrastructure" in data
    finally:
        if yaml_path.exists():
            yaml_path.unlink()

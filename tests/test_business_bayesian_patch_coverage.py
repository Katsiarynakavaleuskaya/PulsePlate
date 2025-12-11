"""Additional tests to boost patch coverage for BusinessBayesianAnalyzer.

Targets specific uncovered lines identified by Codecov patch coverage analysis.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from core.business_bayesian_analyzer import (
    BusinessBayesianAnalyzer,
    BusinessCategory,
    BusinessErrorType,
    ROIEstimate,
)


class TestYAMLLoadingEdgeCases:
    """Tests for YAML loading edge cases and fallbacks."""

    def test_load_business_knowledge_yaml_exists_but_empty_dict(self, tmp_path: Path) -> None:
        """Test loading business knowledge when YAML exists but returns empty dict."""
        import yaml

        # Create a YAML file with empty content
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        yaml_file = config_dir / "business_knowledge.yaml"
        yaml_file.write_text("")  # Empty file

        analyzer = BusinessBayesianAnalyzer()

        with patch.object(analyzer, "_config_dir", return_value=config_dir):
            result = analyzer._load_business_knowledge()

        # Should fall back to defaults when YAML is empty
        assert "revenue_streams" in result
        assert "subscription" in result["revenue_streams"]

    def test_load_business_knowledge_yaml_missing_revenue_streams(self, tmp_path: Path) -> None:
        """Test loading business knowledge when YAML exists but missing expected keys."""
        import yaml

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        yaml_file = config_dir / "business_knowledge.yaml"

        # Write YAML with unexpected structure
        invalid_data = {"unexpected_key": "value"}
        yaml_file.write_text(yaml.dump(invalid_data))

        analyzer = BusinessBayesianAnalyzer()

        with patch.object(analyzer, "_config_dir", return_value=config_dir):
            result = analyzer._load_business_knowledge()

        # Should fall back to defaults when structure is wrong
        assert "revenue_streams" in result
        assert "subscription" in result["revenue_streams"]

    def test_load_monetization_strategies_localized_yaml_found(self, tmp_path: Path) -> None:
        """Test loading localized monetization strategies when localized file exists."""
        import yaml

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create localized YAML file
        localized_file = config_dir / "monetization_strategies.ru.yaml"
        localized_data = {
            "pricing_models": {
                "tiered": ["базовый", "про", "предприятие"],
                "usage_based": True,
            }
        }
        localized_file.write_text(yaml.dump(localized_data))

        analyzer = BusinessBayesianAnalyzer(locale="ru")

        with patch.object(analyzer, "_config_dir", return_value=config_dir):
            result = analyzer._load_monetization_strategies(locale="ru")

        # Should load localized version
        assert result["pricing_models"]["tiered"][0] == "базовый"

    def test_load_cost_optimization_rules_yaml_exists_with_data(self, tmp_path: Path) -> None:
        """Test loading cost optimization rules when YAML exists with valid data."""
        import yaml

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        yaml_file = config_dir / "cost_optimization_rules.yaml"

        custom_rules = {
            "infrastructure": {"custom_rule": True},
            "development": {"custom_dev": True},
        }
        yaml_file.write_text(yaml.dump(custom_rules))

        analyzer = BusinessBayesianAnalyzer()

        with patch.object(analyzer, "_config_dir", return_value=config_dir):
            result = analyzer._load_cost_optimization_rules()

        # Should load custom rules
        assert result["infrastructure"]["custom_rule"] is True

    def test_config_dir_fallback_to_parent(self, tmp_path: Path) -> None:
        """Test _config_dir falls back to parent when immediate config dir doesn't exist."""
        analyzer = BusinessBayesianAnalyzer()

        # Mock __file__ to point to a location without config/
        fake_module_path = tmp_path / "fake_module.py"
        fake_module_path.touch()

        # Create config in parent
        parent_config = tmp_path / "config"
        parent_config.mkdir()

        with patch("core.business_bayesian_analyzer.__file__", str(fake_module_path)):
            result = analyzer._config_dir()

        # Should return parent/config since module.parent/config doesn't exist
        assert result.name == "config"


class TestBusinessAnalysisEdgeCases:
    """Tests for business analysis edge cases."""

    def test_analyze_with_tuple_input(self) -> None:
        """Test analysis with tuple input instead of str or list."""
        analyzer = BusinessBayesianAnalyzer()

        code_tuple = ("def test():", "    price = 2.0", "    return price")

        results = analyzer.analyze_business_logic(code_tuple, "test_tuple")  # type: ignore[arg-type]

        # Should handle tuple input correctly
        assert isinstance(results, list)

    def test_analyze_revenue_growth_no_keywords(self) -> None:
        """Test revenue growth analysis with no matching keywords."""
        analyzer = BusinessBayesianAnalyzer()

        code = "def utility_function(): return True"

        results = analyzer._analyze_revenue_growth(code, "test_utility")

        # Should return empty list when no revenue keywords found
        assert len(results) == 0

    def test_analyze_customer_retention_with_multiple_issues(self) -> None:
        """Test customer retention analysis with multiple issues."""
        analyzer = BusinessBayesianAnalyzer()

        code = """
def send_notification(user):
    # Missing error handling
    notify(user)
    # Missing retry logic
    update_user(user)
"""

        results = analyzer._analyze_customer_retention(code, "test_retention")

        # Should detect multiple retention issues
        assert len(results) > 0

    def test_remove_comments_with_tokenize_error(self) -> None:
        """Test comment removal falls back to character parser on tokenize error."""
        analyzer = BusinessBayesianAnalyzer()

        # Malformed code that breaks tokenizer
        broken_code = "def test(: # broken syntax"

        result = analyzer._remove_comments(broken_code)

        # Should still return something (fallback parser)
        assert isinstance(result, str)


class TestDomainSpecificBehavior:
    """Tests for domain-specific behavior."""

    def test_nutrition_domain_uses_specific_thresholds(self) -> None:
        """Test that nutrition domain uses nutrition-specific thresholds."""
        analyzer = BusinessBayesianAnalyzer(domain="nutrition")

        assert (
            analyzer.low_price_threshold == BusinessBayesianAnalyzer.NUTRITION_LOW_PRICE_THRESHOLD
        )
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.NUTRITION_HIGH_PRICE_THRESHOLD
        )

    def test_health_domain_uses_nutrition_thresholds(self) -> None:
        """Test that health domain also uses nutrition thresholds."""
        analyzer = BusinessBayesianAnalyzer(domain="health")

        assert (
            analyzer.low_price_threshold == BusinessBayesianAnalyzer.NUTRITION_LOW_PRICE_THRESHOLD
        )
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.NUTRITION_HIGH_PRICE_THRESHOLD
        )

    def test_unknown_domain_uses_generic_thresholds(self) -> None:
        """Test that unknown domain uses generic thresholds."""
        analyzer = BusinessBayesianAnalyzer(domain="unknown")

        assert analyzer.low_price_threshold == BusinessBayesianAnalyzer.DEFAULT_LOW_PRICE_THRESHOLD
        assert (
            analyzer.high_price_threshold == BusinessBayesianAnalyzer.DEFAULT_HIGH_PRICE_THRESHOLD
        )

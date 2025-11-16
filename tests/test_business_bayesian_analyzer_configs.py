"""Targeted coverage for configuration fallbacks in business analyzer."""

from __future__ import annotations

import builtins
from io import StringIO
from pathlib import Path

import pytest

import core.business_bayesian_analyzer
from core.business_bayesian_analyzer import BusinessBayesianAnalyzer


def test_load_monetization_strategies_importerror(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback to locale heuristic when core.i18n import fails."""
    analyzer = BusinessBayesianAnalyzer()
    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "core.i18n":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = analyzer._load_monetization_strategies(locale="ru")
    assert "pricing_models" in result


def test_load_monetization_strategies_without_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handle missing PyYAML gracefully by returning defaults."""
    analyzer = BusinessBayesianAnalyzer()
    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "yaml":
            raise ImportError("no yaml")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if self.name.startswith("monetization_strategies"):
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    result = analyzer._load_monetization_strategies(locale="en")
    assert "retention_strategies" in result


def test_load_monetization_strategies_logs_read_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Errors while reading config should fall back to defaults and continue."""
    analyzer = BusinessBayesianAnalyzer()
    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if self.name.startswith("monetization_strategies"):
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    real_open = builtins.open

    def fake_open(*args, **kwargs):
        file = args[0] if args else kwargs.get("file")
        if isinstance(file, (str, Path)) and str(file).endswith(".yaml"):
            raise OSError("cannot open")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    result = analyzer._load_monetization_strategies(locale="en")
    assert "conversion_tactics" in result


def test_load_business_knowledge_yaml_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """YAML parse errors should log warning and fall back to defaults."""

    analyzer = BusinessBayesianAnalyzer()
    target_path = Path(__file__).parent.parent / "config" / "business_knowledge.yaml"

    class FakeYAML:
        class YAMLError(Exception):
            pass

        @staticmethod
        def safe_load(_fh):
            raise FakeYAML.YAMLError("boom")

    monkeypatch.setattr(analyzer, "_import_yaml_module", lambda: FakeYAML())

    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:  # noqa: D401
        if self == target_path:
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(
        core.business_bayesian_analyzer,
        "open",
        lambda *_args, **_kwargs: StringIO("invalid: [yaml"),
        raising=False,
    )

    data = analyzer._load_business_knowledge()
    assert "revenue_streams" in data

"""Tests for the evaluation item statistics baseline.

RU: Тесты для описательной статистики eval-элементов.
EN: Deterministic, offline tests that validate the item statistics
    baseline covers all registry items, has no orphan items, produces
    deterministic output, and contains no forbidden imports.

This test file does NOT implement IRT, psychometric scoring, or
adaptive item selection.  It validates descriptive statistics only.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.evals.eval_item_registry import load_eval_item_registry
from scripts.evals.eval_item_statistics import (
    EvalItemStatisticsRecord,
    build_item_statistics,
    build_item_statistics_report,
    load_fixture_outcomes,
)
from scripts.evals.eval_validity_contract import EvalOutcomeRecord

# ---------------------------------------------------------------------------
# Paths (relative to repo root, resolved from this file)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _REPO_ROOT / "data" / "evals" / "eval_item_metadata_registry.jsonl"
_JUDGMENT_FIXTURE = (
    _REPO_ROOT / "data" / "evals" / "pulseplate_judgment_eval_validity_variants.jsonl"
)
_RAG_FIXTURE = _REPO_ROOT / "data" / "evals" / "pulseplate_rag_release_gate_validity_variants.jsonl"
_STATISTICS_MODULE = _REPO_ROOT / "scripts" / "evals" / "eval_item_statistics.py"
_CLI_MODULE = _REPO_ROOT / "scripts" / "evals" / "run_eval_item_statistics.py"
_CLI_SCRIPT = _CLI_MODULE  # alias for subprocess tests

# Both source files must be guarded by AST scans (FM-1, FM-4, FM-6)
_GUARDED_MODULES = [_STATISTICS_MODULE, _CLI_MODULE]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_all_outcomes() -> list[EvalOutcomeRecord]:
    """Load outcomes from both judgment and RAG fixtures."""
    outcomes: list[EvalOutcomeRecord] = []
    outcomes.extend(load_fixture_outcomes(_JUDGMENT_FIXTURE))
    outcomes.extend(load_fixture_outcomes(_RAG_FIXTURE))
    return outcomes


def _build_full_stats() -> list[EvalItemStatisticsRecord]:
    """Build item statistics from real registry + fixtures."""
    registry = load_eval_item_registry(_REGISTRY_PATH)
    outcomes = _load_all_outcomes()
    return build_item_statistics(outcomes, registry)


def _build_full_report() -> dict[str, Any]:
    """Build the full item statistics report from real data."""
    items = _build_full_stats()
    return build_item_statistics_report(items)


# ---------------------------------------------------------------------------
# 1. No network imports
# ---------------------------------------------------------------------------

_NETWORK_MODULES = frozenset(
    {
        "requests",
        "httpx",
        "aiohttp",
        "urllib3",
        "urllib.request",
        "socket",
        "http.client",
    }
)


def _is_forbidden_module(module_name: str) -> bool:
    """Check if a module name matches or is a submodule of a forbidden network lib."""
    return any(
        module_name == forbidden or module_name.startswith(f"{forbidden}.")
        for forbidden in _NETWORK_MODULES
    )


class TestNoNetworkImports:
    @pytest.mark.parametrize("module_path", _GUARDED_MODULES, ids=lambda p: p.name)
    def test_guarded_modules_have_no_network_imports(self, module_path: Path) -> None:
        """FM-6: Neither the stats module nor the CLI runner may import network libs."""
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _is_forbidden_module(
                        alias.name
                    ), f"{module_path.name} imports network lib: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    assert not _is_forbidden_module(
                        node.module
                    ), f"{module_path.name} imports from network lib: {node.module}"
                    for alias in node.names:
                        qualified = f"{node.module}.{alias.name}"
                        assert not _is_forbidden_module(
                            qualified
                        ), f"{module_path.name} imports from network lib: {qualified}"


# ---------------------------------------------------------------------------
# 2. No IRT imports
# ---------------------------------------------------------------------------

_IRT_PATTERNS = frozenset(
    {
        "item_response_theory",
        "irt_difficulty",
        "irt_discrimination",
        "irt_information",
        "rasch_model",
        "2pl_model",
        "3pl_model",
        "theta_estimate",
        "item_information_function",
        "test_information_function",
        "scipy.optimize",
        "scipy.stats",
        "numpy",
        "pandas",
        "sklearn",
    }
)


class TestNoIrtImports:
    @pytest.mark.parametrize("module_path", _GUARDED_MODULES, ids=lambda p: p.name)
    def test_guarded_modules_have_no_irt_patterns(self, module_path: Path) -> None:
        """FM-1: Neither the stats module nor the CLI runner may contain IRT vocabulary."""
        source = module_path.read_text(encoding="utf-8")
        source_lower = source.lower()
        for pattern in _IRT_PATTERNS:
            assert (
                pattern.lower() not in source_lower
            ), f"{module_path.name} contains IRT/forbidden pattern: {pattern!r}"


# ---------------------------------------------------------------------------
# 3. Loads registry and fixtures
# ---------------------------------------------------------------------------


class TestLoadsRegistryAndFixtures:
    def test_item_statistics_loads_registry_and_fixtures(self) -> None:
        items = _build_full_stats()
        assert len(items) > 0, "Item statistics list must not be empty"
        for item in items:
            assert isinstance(item["canonical_id"], str)
            assert isinstance(item["variant_count"], int)
            assert item["variant_count"] > 0


# ---------------------------------------------------------------------------
# 4. Covers all registry items
# ---------------------------------------------------------------------------


class TestCoversAllRegistryItems:
    def test_item_statistics_covers_all_registry_items(self) -> None:
        registry = load_eval_item_registry(_REGISTRY_PATH)
        items = _build_full_stats()
        stats_ids = {item["canonical_id"] for item in items}
        registry_ids = {rec["canonical_id"] for rec in registry}
        missing = registry_ids - stats_ids
        assert not missing, f"Registry items missing from statistics: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 5. No orphan items
# ---------------------------------------------------------------------------


class TestNoOrphanItems:
    def test_item_statistics_has_no_orphan_items(self) -> None:
        registry = load_eval_item_registry(_REGISTRY_PATH)
        items = _build_full_stats()
        stats_ids = {item["canonical_id"] for item in items}
        registry_ids = {rec["canonical_id"] for rec in registry}
        orphans = stats_ids - registry_ids
        assert not orphans, f"Orphan statistics items not in registry: {sorted(orphans)}"


# ---------------------------------------------------------------------------
# 6. Deterministic report
# ---------------------------------------------------------------------------


class TestDeterministicReport:
    def test_item_statistics_report_is_deterministic(self) -> None:
        report_1 = _build_full_report()
        report_2 = _build_full_report()
        json_1 = json.dumps(report_1, sort_keys=True, ensure_ascii=False)
        json_2 = json.dumps(report_2, sort_keys=True, ensure_ascii=False)
        assert json_1 == json_2, "Item statistics report is not deterministic"


# ---------------------------------------------------------------------------
# 7. Lane counts include rag and judgment
# ---------------------------------------------------------------------------


class TestLaneCounts:
    def test_item_statistics_lane_counts_include_rag_and_judgment(self) -> None:
        report = _build_full_report()
        lane_counts = report["lane_counts"]
        assert "rag" in lane_counts, "lane_counts missing 'rag'"
        assert "judgment" in lane_counts, "lane_counts missing 'judgment'"
        assert lane_counts["rag"] > 0, "rag lane_count must be > 0"
        assert lane_counts["judgment"] > 0, "judgment lane_count must be > 0"


# ---------------------------------------------------------------------------
# 8. Anchor item count is nonzero
# ---------------------------------------------------------------------------


class TestAnchorItemCount:
    def test_item_statistics_anchor_item_count_is_nonzero(self) -> None:
        report = _build_full_report()
        assert report["anchor_item_count"] > 0, "anchor_item_count must be > 0"


# ---------------------------------------------------------------------------
# 9. Invariance counts are nonzero
# ---------------------------------------------------------------------------


class TestInvarianceCounts:
    def test_item_statistics_invariance_counts_are_nonzero(self) -> None:
        items = _build_full_stats()
        total_invariance = sum(item["invariance_count"] for item in items)
        assert total_invariance > 0, "Total invariance_count across all items must be > 0"

        total_agreement = sum(item["invariance_agreement_count"] for item in items)
        assert total_agreement > 0, "Total invariance_agreement_count must be > 0"


# ---------------------------------------------------------------------------
# 10. Mutation counts are nonzero
# ---------------------------------------------------------------------------


class TestMutationCounts:
    def test_item_statistics_mutation_counts_are_nonzero(self) -> None:
        items = _build_full_stats()
        total_mutation = sum(item["mutation_count"] for item in items)
        assert total_mutation > 0, "Total mutation_count across all items must be > 0"


# ---------------------------------------------------------------------------
# 11. Expected decision matches registry
# ---------------------------------------------------------------------------


class TestExpectedDecisionMatchesRegistry:
    def test_item_statistics_expected_decision_matches_registry(self) -> None:
        registry = load_eval_item_registry(_REGISTRY_PATH)
        items = _build_full_stats()
        registry_index = {rec["canonical_id"]: rec for rec in registry}

        for item in items:
            cid = item["canonical_id"]
            reg = registry_index.get(cid)
            assert reg is not None, f"Item {cid!r} has no registry entry"
            assert item["expected_decision"] == reg["expected_decision"], (
                f"Item {cid!r} expected_decision mismatch: "
                f"stats={item['expected_decision']!r} vs "
                f"registry={reg['expected_decision']!r}"
            )
            assert item["expected_score_band"] == reg["expected_score_band"], (
                f"Item {cid!r} expected_score_band mismatch: "
                f"stats={item['expected_score_band']!r} vs "
                f"registry={reg['expected_score_band']!r}"
            )


# ---------------------------------------------------------------------------
# 12. Does not change RAG threshold or decision logic
# ---------------------------------------------------------------------------


_FORBIDDEN_RAG_MODULES = frozenset(
    {
        "scripts.evals.run_rag_release_gates",
        "scripts.evals.rag_release_gate_validity",
    }
)


class TestNoRagDecisionImports:
    @pytest.mark.parametrize("module_path", _GUARDED_MODULES, ids=lambda p: p.name)
    def test_guarded_modules_do_not_import_rag_gate_modules(
        self,
        module_path: Path,
    ) -> None:
        """FM-4: Neither the stats module nor the CLI may import RAG gate modules."""
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert (
                        alias.name not in _FORBIDDEN_RAG_MODULES
                    ), f"{module_path.name} must not import RAG gate module: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    assert (
                        node.module not in _FORBIDDEN_RAG_MODULES
                    ), f"{module_path.name} must not import from RAG gate module: {node.module}"


# ---------------------------------------------------------------------------
# 13. Does not change judgment decision logic
# ---------------------------------------------------------------------------


_FORBIDDEN_JUDGMENT_MODULES = frozenset(
    {
        "scripts.evals.judgment_validity",
        "scripts.orchestration.judgment_eval",
    }
)


class TestNoJudgmentDecisionImports:
    @pytest.mark.parametrize("module_path", _GUARDED_MODULES, ids=lambda p: p.name)
    def test_guarded_modules_do_not_import_judgment_modules(
        self,
        module_path: Path,
    ) -> None:
        """FM-4: Neither the stats module nor the CLI may import judgment modules."""
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert (
                        alias.name not in _FORBIDDEN_JUDGMENT_MODULES
                    ), f"{module_path.name} must not import judgment module: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    assert (
                        node.module not in _FORBIDDEN_JUDGMENT_MODULES
                    ), f"{module_path.name} must not import from judgment module: {node.module}"


# ---------------------------------------------------------------------------
# 14. No decision-function vocabulary in source (FM-4 reinforcement)
# ---------------------------------------------------------------------------

_DECISION_FUNCTION_PATTERNS = frozenset(
    {
        "pass_no_go",
        "evaluate_pass",
        "evaluate_no_go",
        "promote_item",
        "defer_item",
        "discard_item",
        "gate_decision",
        "release_decision",
    }
)


class TestNoDecisionFunctionVocabulary:
    @pytest.mark.parametrize("module_path", _GUARDED_MODULES, ids=lambda p: p.name)
    def test_guarded_modules_have_no_decision_function_vocabulary(
        self,
        module_path: Path,
    ) -> None:
        """FM-4: Stats modules must not define or call decision functions."""
        source = module_path.read_text(encoding="utf-8")
        source_lower = source.lower()
        for pattern in _DECISION_FUNCTION_PATTERNS:
            assert (
                pattern not in source_lower
            ), f"{module_path.name} contains decision-function vocabulary: {pattern!r}"


# ---------------------------------------------------------------------------
# 15. Report output has no IRT-claiming keys (FM-1 reinforcement)
# ---------------------------------------------------------------------------

_IRT_REPORT_KEYS = frozenset(
    {
        "irt_difficulty",
        "irt_discrimination",
        "irt_information",
        "theta_estimate",
        "item_information",
        "test_information",
        "rasch_difficulty",
        "reliability_coefficient",
        "calibrated_difficulty",
    }
)


class TestReportHasNoIrtKeys:
    def test_item_statistics_report_has_no_irt_keys(self) -> None:
        """FM-1: Report output must not contain IRT-claiming field names."""
        report = _build_full_report()
        for item in report["items"]:
            item_keys = set(item.keys())
            irt_found = item_keys & _IRT_REPORT_KEYS
            assert (
                not irt_found
            ), f"Item {item.get('canonical_id', '?')!r} has IRT-claiming keys: {irt_found}"
        top_keys = set(report.keys())
        irt_top = top_keys & _IRT_REPORT_KEYS
        assert not irt_top, f"Report envelope has IRT-claiming keys: {irt_top}"


# ---------------------------------------------------------------------------
# 16. CLI writes report
# ---------------------------------------------------------------------------


class TestCliWritesReport:
    def test_item_statistics_cli_writes_report(self, tmp_path: Path) -> None:
        output_file = tmp_path / "test_report.json"
        result = subprocess.run(
            [
                sys.executable,
                str(_CLI_SCRIPT),
                "--registry",
                str(_REGISTRY_PATH),
                "--fixture",
                str(_JUDGMENT_FIXTURE),
                "--fixture",
                str(_RAG_FIXTURE),
                "--output",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert (
            result.returncode == 0
        ), f"CLI failed with:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert output_file.exists(), "CLI did not create output file"

        report = json.loads(output_file.read_text(encoding="utf-8"))
        assert report["schema_version"] == "1.0"
        assert report["item_count"] > 0
        assert "lane_counts" in report
        assert "items" in report
        assert isinstance(report["items"], list)
        assert len(report["items"]) == report["item_count"]


# ---------------------------------------------------------------------------
# 17. CLI output has no timestamp
# ---------------------------------------------------------------------------


class TestCliOutputHasNoTimestamp:
    def test_item_statistics_cli_output_has_no_timestamp(self, tmp_path: Path) -> None:
        output_file = tmp_path / "test_report_ts.json"
        subprocess.run(
            [
                sys.executable,
                str(_CLI_SCRIPT),
                "--registry",
                str(_REGISTRY_PATH),
                "--fixture",
                str(_JUDGMENT_FIXTURE),
                "--fixture",
                str(_RAG_FIXTURE),
                "--output",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        content = output_file.read_text(encoding="utf-8")

        # Check no timestamp-like keys in JSON
        report = json.loads(content)
        _timestamp_keys = {"timestamp", "created_at", "updated_at", "generated_at", "date"}
        found = _timestamp_keys & set(report.keys())
        assert not found, f"Report contains timestamp key(s): {found}"

        # Also verify no ISO-format timestamps in raw content
        iso_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        assert not iso_pattern.search(content), "Report contains ISO timestamp string"

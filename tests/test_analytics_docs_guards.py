"""Documentation policy guards for vendor-agnostic analytics artifacts.

These guards intentionally avoid:
- time-based checks (no `datetime.now()` / overdue logic)
- snapshot writes or any file system mutation

They enforce that canonical analytics doc surfaces exist and keep a minimum structure,
so future PRs don't silently delete or hollow out the contracts.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def test_analytics_docs_exist() -> None:
    required = [
        "docs/analytics/README.md",
        "docs/analytics/ANALYTICS_INDEX.md",
        "docs/analytics/METRICS_CATALOG.md",
        "docs/analytics/DATA_CATALOG.md",
        "docs/analytics/EXPERIMENT_REGISTRY.md",
    ]

    missing = [p for p in required if not (REPO_ROOT / p).exists()]
    assert not missing, (
        "Missing analytics canonical docs.\n"
        f"- missing: {missing}\n"
        "Fix: add vendor-agnostic templates under docs/analytics/ (see plan)."
    )


def test_metrics_catalog_contains_required_sections() -> None:
    content = _read("docs/analytics/METRICS_CATALOG.md")

    required_markers = [
        "#### Definition",
        "#### Formula",
        "#### Owner",
        "#### Update frequency",
        "#### Change history",
    ]
    missing = [m for m in required_markers if m not in content]
    assert not missing, (
        "docs/analytics/METRICS_CATALOG.md missing required template sections.\n"
        f"- missing_markers: {missing}\n"
        "Fix: restore the metric template sections so definitions stay reviewable."
    )


def test_experiment_registry_contains_active_and_completed_sections() -> None:
    content = _read("docs/analytics/EXPERIMENT_REGISTRY.md")
    required_markers = ["## Active Experiments", "## Completed Experiments"]
    missing = [m for m in required_markers if m not in content]
    assert not missing, (
        "docs/analytics/EXPERIMENT_REGISTRY.md missing required sections.\n"
        f"- missing_markers: {missing}\n"
        "Fix: keep both Active and Completed sections for end-to-end tracking."
    )


def test_analytics_index_contains_metrics_and_sources_sections() -> None:
    content = _read("docs/analytics/ANALYTICS_INDEX.md")
    required_markers = ["## Tracked Metrics", "## Data Sources"]
    missing = [m for m in required_markers if m not in content]
    assert not missing, (
        "docs/analytics/ANALYTICS_INDEX.md missing required sections.\n"
        f"- missing_markers: {missing}\n"
        "Fix: keep metrics and data sources catalog sections."
    )

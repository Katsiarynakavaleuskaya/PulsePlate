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

ANALYTICS_DOCS_REQUIRED_MARKERS: dict[str, list[str]] = {
    "docs/analytics/README.md": [
        "## Files (canonical surfaces)",
        "## Ownership (recommended)",
    ],
    "docs/analytics/ANALYTICS_INDEX.md": [
        "## Tracked Metrics",
        "## Data Sources",
    ],
    "docs/analytics/METRICS_CATALOG.md": [
        "#### Definition",
        "#### Formula",
        "#### Owner",
        "#### Update frequency",
        "#### Change history",
    ],
    "docs/analytics/DATA_CATALOG.md": [
        # Enforce semantic skeleton to prevent hollow placeholders.
        "## Data sources (high-level)",
        "## Tables / entities (example templates)",
        "### users",
        "## Events (vendor-agnostic)",
        "### event: <event_name>",
    ],
    "docs/analytics/EXPERIMENT_REGISTRY.md": [
        "## Active Experiments",
        "## Completed Experiments",
    ],
}


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _assert_required_markers(path: str, content: str, markers: list[str]) -> None:
    missing = [marker for marker in markers if marker not in content]
    assert not missing, (
        f"{path} missing required structure markers.\n"
        f"- missing_markers: {missing}\n"
        "Fix: restore canonical headings/sections required by analytics docs guards."
    )


def test_analytics_docs_exist() -> None:
    missing = [p for p in ANALYTICS_DOCS_REQUIRED_MARKERS if not (REPO_ROOT / p).exists()]
    assert not missing, (
        "Missing analytics canonical docs.\n"
        f"- missing: {missing}\n"
        "Fix: add vendor-agnostic templates under docs/analytics/ (see plan)."
    )


def test_analytics_docs_keep_required_structure_markers() -> None:
    for path, markers in ANALYTICS_DOCS_REQUIRED_MARKERS.items():
        _assert_required_markers(path=path, content=_read(path), markers=markers)

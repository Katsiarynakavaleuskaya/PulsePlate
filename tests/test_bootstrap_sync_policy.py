"""Tests for canonical bootstrap sync-policy helpers."""

from __future__ import annotations

from scripts.orchestration.bootstrap_sync_policy import (
    AGENT_CONTRACT_PATH_MARKERS,
    AGENTS_CONTRACT_FILE,
    AGENTS_CURSOR_PREFIX,
    BACKLOG_SIGNAL_TERMS,
    IMPLEMENTATION_PATH_PREFIXES,
    PRIVILEGED_REVIEW_PREFIXES,
    SKILL_CONTRACT_FILE,
    matches_any_prefix,
    needs_agents_sync,
    needs_backlog_update,
    needs_docs_sync,
    requires_security_review,
)


def test_bootstrap_sync_policy_freezes_backlog_signal_terms() -> None:
    """Backlog markers should stay deterministic across follow-on automation slices."""

    assert BACKLOG_SIGNAL_TERMS == (
        "backlog",
        "ledger",
        "roadmap",
        "defer",
        "deferred",
        "follow-up",
        "follow up",
    )


def test_bootstrap_sync_policy_freezes_implementation_roots() -> None:
    """Implementation roots must remain explicit until widened in a dedicated PR."""

    assert IMPLEMENTATION_PATH_PREFIXES == (
        "app/",
        "core/",
        "scripts/",
        "frontend/",
        "ios/",
    )


def test_bootstrap_sync_policy_freezes_privileged_review_prefixes() -> None:
    """Privileged review prefixes must remain canonical and reviewable."""

    assert PRIVILEGED_REVIEW_PREFIXES == (
        ".github/workflows/",
        "ios/fastlane/",
        "scripts/orchestration/",
        "scripts/ci/",
        "docs/orchestration/",
        "docs/review/",
    )


def test_bootstrap_sync_policy_matches_prefixes_for_root_and_nested_paths() -> None:
    """Prefix matching should work for both exact roots and nested paths."""

    prefixes = ("scripts/", "docs/orchestration/")

    assert matches_any_prefix("scripts", prefixes) is True
    assert matches_any_prefix("scripts/orchestration/task_bootstrap.py", prefixes) is True
    assert matches_any_prefix("docs/orchestration/workflow.md", prefixes) is True
    assert matches_any_prefix("tests/test_bootstrap_sync_policy.py", prefixes) is False


def test_bootstrap_sync_policy_detects_backlog_update_markers() -> None:
    """Backlog update signals should fire for both text markers and ledger paths."""

    assert (
        needs_backlog_update(
            goal="Track deferred roadmap follow-up",
            task_class="Documentation",
            candidate_paths=["docs/orchestration/workflow.md"],
        )
        is True
    )
    assert (
        needs_backlog_update(
            goal="Refresh docs",
            task_class="Documentation",
            candidate_paths=["docs/roadmap/BACKLOG_LEDGER.md"],
        )
        is True
    )
    assert (
        needs_backlog_update(
            goal="Implement feature X in core service",
            task_class="Engineering",
            candidate_paths=["src/core/service.py"],
        )
        is False
    )


def test_bootstrap_sync_policy_detects_docs_and_agents_sync_signals() -> None:
    """Docs and agent sync signals should remain narrowly scoped and deterministic."""

    assert AGENT_CONTRACT_PATH_MARKERS == (
        AGENTS_CONTRACT_FILE,
        AGENTS_CURSOR_PREFIX,
        SKILL_CONTRACT_FILE,
    )
    assert needs_docs_sync(["app/security/auth.py"]) is True
    assert needs_docs_sync(["app/security/auth.py", "docs/security/AUTH.md"]) is False
    assert needs_agents_sync([AGENTS_CONTRACT_FILE]) is True
    assert needs_agents_sync([AGENTS_CURSOR_PREFIX]) is True
    assert needs_agents_sync(["frontend/AGENTS.md"]) is True
    assert needs_agents_sync([f"skills/bootstrap/{SKILL_CONTRACT_FILE}"]) is True
    assert needs_agents_sync(["docs/orchestration/workflow.md"]) is False


def test_bootstrap_sync_policy_detects_privileged_review_surfaces() -> None:
    """Privileged review detection should stay aligned with the canonical prefix set."""

    assert requires_security_review([".github/workflows"]) is True
    assert requires_security_review(["scripts/ci"]) is True
    assert requires_security_review(["scripts/orchestration/task_bootstrap.py"]) is True
    assert requires_security_review(["docs/review/PR_1325_FIXED_MAPPING.md"]) is True
    assert requires_security_review(["script/orchestration/config.yml"]) is False
    assert requires_security_review(["tests/test_task_bootstrap.py"]) is False

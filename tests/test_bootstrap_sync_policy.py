"""Tests for canonical bootstrap sync-policy helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration.bootstrap_sync_policy import (
    AGENT_CONTRACT_PATH_MARKERS,
    AGENTS_CONTRACT_FILE,
    AGENTS_CURSOR_PREFIX,
    ANALYSIS_ENVELOPE_MODE,
    BACKLOG_SIGNAL_TERMS,
    DOCS_ONLY_ENVELOPE_MODE,
    DOCS_ONLY_ROOT_FILES,
    IMPLEMENTATION_PATH_PREFIXES,
    PRIVILEGED_REVIEW_PREFIXES,
    PRIVILEGED_REVIEW_SURFACES,
    SKILL_CONTRACT_FILE,
    is_docs_only_contract_path,
    matches_any_prefix,
    needs_agents_sync,
    needs_backlog_update,
    needs_docs_sync,
    privileged_review_surface_matches,
    requires_security_review,
    resolve_analysis_envelope_mode,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "orchestration"


def _privileged_surface_cases() -> list[dict[str, object]]:
    fixture = json.loads((FIXTURE_DIR / "privileged_review_surfaces.json").read_text())
    return list(fixture["cases"])


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
        ".github/actions/",
        "ios/fastlane/",
        "scripts/orchestration/",
        "scripts/ci/",
        "docs/orchestration/",
        "docs/review/",
        "deploy/",
        ".devcontainer/",
    )
    assert tuple(surface.surface_class for surface in PRIVILEGED_REVIEW_SURFACES) == (
        "github_workflows",
        "github_actions",
        "ios_fastlane",
        "orchestration_scripts",
        "merge_governance_scripts",
        "orchestration_governance_docs",
        "review_governance_docs",
        "deploy_and_image_config",
        "dependency_and_hook_config",
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


def test_bootstrap_sync_policy_freezes_docs_only_roots() -> None:
    """Docs-only roots must remain explicit until widened in a dedicated PR."""

    assert DOCS_ONLY_ROOT_FILES == (
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "README.md",
        "CLAUDE.md",
        "DEPLOYMENT.md",
    )


def test_bootstrap_sync_policy_detects_docs_only_contract_paths() -> None:
    """Docs-only detection should stay limited to canonical markdown/contract files."""

    assert is_docs_only_contract_path("CONTRIBUTING.md") is True
    assert is_docs_only_contract_path("DEPLOYMENT.md") is True
    assert is_docs_only_contract_path("docs/orchestration/AGENT_MESSAGE_PROTOCOL.md") is True
    assert is_docs_only_contract_path(".github/PULL_REQUEST_TEMPLATE.md") is True
    assert is_docs_only_contract_path("frontend/AGENTS.md") is True
    assert is_docs_only_contract_path("skills/bootstrap/SKILL.md") is True
    assert is_docs_only_contract_path("docs/orchestration/schema.json") is False
    assert is_docs_only_contract_path("scripts/orchestration/task_bootstrap.py") is False
    assert is_docs_only_contract_path("app/internal_notes.md") is False
    assert is_docs_only_contract_path("core/README.md") is False


def test_bootstrap_sync_policy_fails_closed_for_implementation_tree_markdown() -> None:
    """Markdown under implementation roots must not alone justify docs-only envelope."""

    assert resolve_analysis_envelope_mode(["app/internal_notes.md"]) == ANALYSIS_ENVELOPE_MODE
    assert resolve_analysis_envelope_mode(["core/README.md"]) == ANALYSIS_ENVELOPE_MODE


def test_bootstrap_sync_policy_derives_docs_only_envelope_mode_for_contract_scope() -> None:
    """Pure docs/contract scopes may downshift to docs-only envelope mode."""

    assert (
        resolve_analysis_envelope_mode(
            [
                "CONTRIBUTING.md",
                "DEPLOYMENT.md",
            ]
        )
        == DOCS_ONLY_ENVELOPE_MODE
    )


def test_bootstrap_sync_policy_normalizes_whitespace_padded_docs_only_paths() -> None:
    """Whitespace-only padding must not change docs-only envelope derivation."""

    assert (
        resolve_analysis_envelope_mode(
            [
                " CONTRIBUTING.md ",
                "\tDEPLOYMENT.md\n",
            ]
        )
        == DOCS_ONLY_ENVELOPE_MODE
    )


def test_bootstrap_sync_policy_fails_closed_to_analysis_for_mixed_scope() -> None:
    """Mixed or runtime scopes must resolve to analysis mode."""

    assert resolve_analysis_envelope_mode([]) == ANALYSIS_ENVELOPE_MODE
    assert (
        resolve_analysis_envelope_mode(
            [
                "docs/orchestration/AGENT_MESSAGE_PROTOCOL.md",
                "scripts/orchestration/task_bootstrap.py",
            ]
        )
        == ANALYSIS_ENVELOPE_MODE
    )


def test_bootstrap_sync_policy_detects_privileged_review_surfaces() -> None:
    """Privileged review detection should stay aligned with the canonical prefix set."""

    assert requires_security_review([".github/workflows"]) is True
    assert requires_security_review(["scripts/ci"]) is True
    assert requires_security_review(["scripts/orchestration/task_bootstrap.py"]) is True
    assert requires_security_review(["docs/review/PR_1325_FIXED_MAPPING.md"]) is True
    assert requires_security_review(["Dockerfile"]) is True
    assert requires_security_review(["requirements.txt"]) is True
    assert requires_security_review(["script/orchestration/config.yml"]) is False
    assert requires_security_review(["tests/test_task_bootstrap.py"]) is False


@pytest.mark.parametrize("case", _privileged_surface_cases(), ids=lambda case: case["case_id"])
def test_bootstrap_sync_policy_uses_reviewed_privileged_surface_matrix(
    case: dict[str, object],
) -> None:
    """Shared matrix must drive exact, suffix, prefix, and negative matching."""

    path = str(case["path"])
    is_privileged = bool(case["privileged"])
    assert requires_security_review([path]) is is_privileged

    matches = privileged_review_surface_matches([f"  {path}  "])
    if is_privileged:
        assert case["reason"] in matches
    else:
        assert matches == ()


def test_bootstrap_sync_policy_fails_closed_to_analysis_for_privileged_docs() -> None:
    """Privileged orchestration docs must stay in analysis mode."""

    candidate_paths = ["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"]

    assert resolve_analysis_envelope_mode(candidate_paths) == ANALYSIS_ENVELOPE_MODE
    assert requires_security_review(candidate_paths) is True


def test_bootstrap_sync_policy_fails_closed_for_whitespace_padded_privileged_docs() -> None:
    """Privileged docs must stay in analysis mode even when input paths contain padding."""

    candidate_paths = ["  docs/orchestration/AGENT_MESSAGE_PROTOCOL.md  "]

    assert resolve_analysis_envelope_mode(candidate_paths) == ANALYSIS_ENVELOPE_MODE
    assert requires_security_review(candidate_paths) is True

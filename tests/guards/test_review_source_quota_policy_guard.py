"""Anti-drift guard for terminal Codex review-source quota evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.orchestration import pr_review_closeout
from scripts.orchestration.pr_review_evidence import (
    REVIEW_SOURCE_UNAVAILABILITY_AUTHORITY,
    REVIEW_SOURCE_UNAVAILABILITY_SCHEMA_VERSION,
    ReviewEvidenceError,
    build_review_source_unavailability_receipt,
    validate_review_credit_outage_scope,
)
from scripts.orchestration.review_source_status import (
    build_review_source_status,
    classify_codex_review_source_unavailability_body,
    review_source_policy_projection,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_AUTHORING_OPTIONS = {
    "--prior-codex-review-ref",
    "--review-credit-outage-ref",
    "--review-credit-quota-ref",
}
POLICY_SURFACE_FILES = {
    "AGENTS.md",
    "RUNBOOK_AGENT.md",
    "docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md",
    "docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    "scripts/ci/check_pr_merge_readiness.py",
    "scripts/orchestration/pr_commit_identity.py",
    "scripts/orchestration/pr_review_closeout.py",
    "scripts/orchestration/pr_review_evidence.py",
    "scripts/orchestration/review_source_status.py",
    "scripts/run-backend-tests-pre-commit.sh",
    "tests/guards/test_review_source_quota_policy_guard.py",
}


def _seal_option_strings() -> set[str]:
    parser = pr_review_closeout._parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action.choices, dict)
    )
    seal_parser = subparsers_action.choices["seal"]
    return {option for action in seal_parser._actions for option in action.option_strings}


def test_terminal_quota_policy_projection_is_exact() -> None:
    assert review_source_policy_projection() == {
        "blocking_statuses": [
            "actionable_bot_comments",
            "failed_required_check",
            "fallback_finding",
            "unresolved_threads",
        ],
        "policy_version": "pulseplate.review-source-policy/v1",
        "terminal_nonblocking_statuses": [
            "rate_limited",
            "usage_limit_reached",
        ],
        "terminal_unavailability": {
            "blocking": False,
            "fallback_required": False,
            "operator_override_required": False,
            "prior_review_required": False,
            "retry_required": False,
            "review_claim": "none",
            "source_degraded": True,
            "substitute_review_required": False,
            "ttl_required": False,
        },
    }


@pytest.mark.parametrize("status", ["rate_limited", "usage_limit_reached"])
def test_terminal_quota_policy_cannot_be_overridden_to_blocking(status: str) -> None:
    with pytest.raises(
        ValueError,
        match="terminal review-source unavailability cannot be marked blocking",
    ):
        build_review_source_status(
            source="codex_review",
            status=status,
            blocking=True,
        )


def test_legacy_credit_override_is_live_valid_only_for_bootstrap_pr() -> None:
    validate_review_credit_outage_scope(
        repository="Katsiarynakavaleuskaya/PulsePlate",
        pr_number=2142,
        material_paths=("scripts/ci/check_pr_merge_readiness.py",),
    )
    for repository, pr_number, paths in (
        (
            "Katsiarynakavaleuskaya/PulsePlate",
            2143,
            ("requirements-test.txt",),
        ),
        ("owner/repo", 42, ()),
    ):
        with pytest.raises(ReviewEvidenceError, match="live-valid only.*PR #2142"):
            validate_review_credit_outage_scope(
                repository=repository,
                pr_number=pr_number,
                material_paths=paths,
            )


def test_known_codex_quota_bodies_remain_exact_terminal_evidence() -> None:
    bodies = (
        (
            "Codex usage limits have been reached for code reviews. "
            "Please check with the admins of this repo to increase the limits "
            "by adding credits."
        ),
        (
            "Codex usage limits have been reached for code reviews. "
            "Please check with the admins of this repo to increase the limits "
            "by adding credits.\n"
            "Credits must be used to enable repository wide code reviews."
        ),
        (
            "You have reached your Codex usage limits for code reviews. "
            "You can see your limits in the "
            "[Codex usage dashboard](https://chatgpt.com/codex/cloud/settings/usage)."
        ),
    )
    assert {classify_codex_review_source_unavailability_body(body) for body in bodies} == {
        "usage_limit_reached"
    }


def test_closeout_exposes_only_current_review_authoring_modes() -> None:
    options = _seal_option_strings()
    assert {"--review-ref", "--review-source-unavailable-ref"} <= options
    assert not options.intersection(LEGACY_AUTHORING_OPTIONS)
    closeout_source = (REPO_ROOT / "scripts/orchestration/pr_review_closeout.py").read_text(
        encoding="utf-8"
    )
    assert all(option not in closeout_source for option in LEGACY_AUTHORING_OPTIONS)


def test_quota_receipt_authority_never_claims_review_or_blocking() -> None:
    receipt = build_review_source_unavailability_receipt(
        material_digest="sha256:" + "a" * 64,
        material_head_sha="b" * 40,
        quota_reference="https://github.com/owner/repo/pull/42#issuecomment-1",
        quota_created_at="2020-01-01T00:00:00Z",
        quota_body_sha256="sha256:" + "c" * 64,
        source_status="usage_limit_reached",
    )
    assert receipt["schema_version"] == REVIEW_SOURCE_UNAVAILABILITY_SCHEMA_VERSION
    assert receipt["authority"] == REVIEW_SOURCE_UNAVAILABILITY_AUTHORITY
    assert receipt["binding_kind"] == "seal_context_only"
    assert receipt["review_claim"] == "none"
    assert receipt["source_degraded"] is True
    assert receipt["fallback_required"] is False
    assert receipt["blocking"] is False
    assert "review_reference" not in receipt
    assert "review_commit_ref" not in receipt


def test_authoritative_docs_keep_terminal_warning_only_contract() -> None:
    paths = (
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md",
        "docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
    )
    documents = {path: (REPO_ROOT / path).read_text(encoding="utf-8") for path in paths}
    joined = "\n".join(documents.values())
    normalized = " ".join(joined.split())
    assert all(option not in joined for option in LEGACY_AUTHORING_OPTIONS)
    assert all(
        phrase not in normalized
        for phrase in (
            "requires a prior trusted Codex review",
            "must name a subsequent exact-head",
            "quota response must be current",
            "All evidence must remain within its TTL",
        )
    )
    assert "No retry, substitute review, prior review, operator override, or TTL" in normalized
    assert "`review_claim=none`" in joined
    assert "Historical PR `#2142`" in joined
    assert "not an active authoring" in joined
    runbook = documents["RUNBOOK_AGENT.md"]
    normalized_runbook = " ".join(runbook.split())
    assert "do not trigger or retrigger it manually" in normalized_runbook
    assert "Do not post manual bot-review commands" in normalized_runbook
    assert "first disable automatic" not in normalized_runbook
    assert "@codex review" not in runbook


def test_every_policy_surface_selects_this_guard_in_diff_validation() -> None:
    runner = (REPO_ROOT / "scripts/run-backend-tests-pre-commit.sh").read_text(encoding="utf-8")
    assert "declare -a REVIEW_SOURCE_QUOTA_POLICY_SURFACE_FILES=(" in runner
    assert 'EXTRA_TEST_FILES+=("tests/guards/test_review_source_quota_policy_guard.py")' in runner
    for path in POLICY_SURFACE_FILES:
        assert f'"{path}"' in runner

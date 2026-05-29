"""Tests for deterministic Slack Block Kit KPP renderer."""

from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.orchestration.experiment_contract import FAILURE_CLASSES
import scripts.orchestration.experiment_notify as experiment_notify
from scripts.orchestration.experiment_slack_redaction import safe_artifact_ref
from scripts.orchestration.experiment_slack_kpp_renderer import (
    ACTION_REQUIRED_COPY,
    ARTIFACT_REFERENCE_COPY,
    KPP_DEFER,
    KPP_DISCARD,
    KPP_FAIL,
    KPP_ORACLE_VIOLATION,
    KPP_PROMOTE,
    KPP_SURFACE_BREACH,
    KPP_OUTCOMES,
    KPPRenderError,
    NO_MERGE_ACTION_COPY,
    NO_SENSITIVE_DATA_COPY,
    REDACTION_NOTICE,
    SECURITY_SENSITIVE_OUTCOMES,
    _slack_text,
    _validate_experiment_id,
    _validate_kpp_outcome,
    render_kpp_block_message,
    route_kpp_outcome_from_result,
)

# ============================================================================
# Redaction
# ============================================================================


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Hello world", "Hello world"),
        ("xoxb-1234567890-abcdef", "[redacted-secret]"),
        ("ghp_abcdefghijklmnopqrstuvwxyz1234", "[redacted-secret]"),  # pragma: allowlist secret
        (
            "https://hooks.slack.com/services/T123/B456/xxx",
            "[redacted-secret]",
        ),  # pragma: allowlist secret
        ("sk-abcdefghijklmnopqrstuvwxyz12", "[redacted-secret]"),  # pragma: allowlist secret
        ("<@U12345678>", "[redacted-slack-id]"),
        ("<#C12345678|channel>", "[redacted-slack-id]"),
        ("U12345678", "[redacted-slack-id]"),
        ("/Users/alice/project", "[redacted-path]"),
        ("/home/alice/project", "[redacted-path]"),
        ("/var/log/pulseplate/runner.log", "[redacted-path]"),
        ("diff --git a/file b/file", "[redacted-log] a/file b/file"),
        ("@@ -1,3 +1,5 @@", "[redacted-log]-1,3 +1,5 @@"),
        ("@here please review", "@[redacted-mention] please review"),
        ("@channel attention", "@[redacted-mention] attention"),
        ("<script>alert(1)</script>", "<script>alert(1)</script>"),
        ("`code`", "'code'"),
        ("", "none"),
        ("   ", "none"),
        ("x\x00y\x01z", "x y z"),
    ],
)
def test_slack_text_redaction(raw: str, expected: str) -> None:
    assert _slack_text(raw) == expected


def test_slack_text_truncation() -> None:
    long_text = "a" * 300
    result = _slack_text(long_text, limit=100)
    assert result.endswith(" [truncated=true]")
    assert len(result) <= 100


@pytest.mark.parametrize(
    "raw",
    [
        "/Users/alice/project/artifact.json",
        "/home/alice/project/artifact.json",
        "/var/log/pulseplate/runner.log",
        "/etc/passwd",
        "../outside.json",
        "docs/audit/../secret.json",
        "C:\\Users\\alice\\secret.txt",
        "\\\\server\\share\\secret.txt",
        "docs/audit/xoxb-secret-secret-secret",
        "unknown/path.json",
    ],
)
def test_safe_artifact_ref_rejects_unsafe_refs(raw: str) -> None:
    assert safe_artifact_ref(raw) == "[redacted-ref]"


def test_safe_artifact_ref_allows_known_repo_refs_and_hashes() -> None:
    assert safe_artifact_ref("docs/audit/EXPERIMENT_EXP_NOTIFY.md") == (
        "docs/audit/EXPERIMENT_EXP_NOTIFY.md"
    )
    assert safe_artifact_ref("artifacts/orchestration/experiments/results/exp-042.json") == (
        "artifacts/orchestration/experiments/results/exp-042.json"
    )
    assert safe_artifact_ref("11111111222222223333333344444444") == "1111111122222222"


# ============================================================================
# Validation
# ============================================================================


def test_validate_kpp_outcome_success() -> None:
    for outcome in KPP_OUTCOMES:
        assert _validate_kpp_outcome(outcome) == outcome
        assert _validate_kpp_outcome(outcome.lower()) == outcome


@pytest.mark.parametrize(
    "bad",
    ["", "  ", "unknown", "PROMOTE_EXTRA", 123],
)
def test_validate_kpp_outcome_failure(bad: Any) -> None:
    with pytest.raises(KPPRenderError, match=r"KPP outcome must be one of"):
        _validate_kpp_outcome(bad)


@pytest.mark.parametrize(
    "good",
    ["exp-001", "experiment_123", "A1", "test_runner_v2"],
)
def test_validate_experiment_id_success(good: str) -> None:
    assert _validate_experiment_id(good) == good


@pytest.mark.parametrize(
    "bad",
    ["", "  ", "/tmp/exp", "../../../etc", "exp with space", 'exp"quote'],
)
def test_validate_experiment_id_failure(bad: str) -> None:
    with pytest.raises(KPPRenderError):
        _validate_experiment_id(bad)


def test_validate_experiment_id_too_long() -> None:
    with pytest.raises(KPPRenderError, match=r"at most 64 characters"):
        _validate_experiment_id("a" * 65)


# ============================================================================
# Rendering
# ============================================================================


@pytest.mark.parametrize(
    "outcome",
    KPP_OUTCOMES,
)
def test_render_all_outcomes(outcome: str) -> None:
    message = render_kpp_block_message(
        kpp_outcome=outcome,
        experiment_id="test-001",
    )
    assert message.kpp_outcome == outcome
    json_payload = message.as_blocks_json()
    parsed = json.loads(json_payload)
    assert "blocks" in parsed
    assert isinstance(parsed["blocks"], list)
    assert len(parsed["blocks"]) >= 4


@pytest.mark.parametrize(
    "outcome, expected_class",
    [
        (KPP_PROMOTE, "promotion_candidate"),
        (KPP_DEFER, "deferred_candidate"),
        (KPP_DISCARD, "discarded_candidate"),
        (KPP_FAIL, "failed_candidate"),
        (KPP_ORACLE_VIOLATION, "security_oracle_violation"),
        (KPP_SURFACE_BREACH, "security_surface_breach"),
    ],
)
def test_kpp_class_values(outcome: str, expected_class: str) -> None:
    message = render_kpp_block_message(
        kpp_outcome=outcome,
        experiment_id="test-001",
    )
    assert message.kpp_class == expected_class


@pytest.mark.parametrize(
    "outcome",
    SECURITY_SENSITIVE_OUTCOMES,
)
def test_security_sensitive_headers(outcome: str) -> None:
    message = render_kpp_block_message(
        kpp_outcome=outcome,
        experiment_id="test-001",
    )
    assert "SECURITY ALERT" in message.header


def test_render_with_failure_class() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_FAIL,
        experiment_id="test-001",
        failure_class="timeout",
    )
    assert message.failure_class == "timeout"
    json_payload = message.as_blocks_json()
    parsed = json.loads(json_payload)
    section_texts = []
    for block in parsed["blocks"]:
        if block.get("type") == "section":
            if "text" in block:
                section_texts.append(block["text"].get("text", ""))
            if "fields" in block:
                for field in block["fields"]:
                    section_texts.append(field.get("text", ""))
    assert any("timeout" in text for text in section_texts)


def test_render_with_artifacts() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
        artifact_refs=("artifacts/exp/test-001.json", "docs/review/PR_1848.md"),
    )
    json_payload = message.as_blocks_json()
    parsed = json.loads(json_payload)
    artifact_block_text = " ".join(
        block.get("text", {}).get("text", "")
        for block in parsed["blocks"]
        if block.get("type") == "section"
        and "Artifact/reference" in block.get("text", {}).get("text", "")
    )
    assert "artifacts/exp/test-001.json" in artifact_block_text
    assert "docs/review/PR_1848.md" in artifact_block_text


def test_render_custom_action_required() -> None:
    custom_action = "Custom operator action"
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
        action_required=custom_action,
    )
    assert message.action_required == custom_action


def test_render_default_scope() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
    )
    assert "Experiment Runner KPP outcome" in message.scope


def test_render_custom_scope() -> None:
    custom_scope = "Custom scope description"
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
        scope=custom_scope,
    )
    assert message.scope == custom_scope


def test_render_evidence_summary() -> None:
    evidence = ("Line one", "Line two")
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
        evidence_summary=evidence,
    )
    assert message.evidence_summary == evidence
    json_payload = message.as_blocks_json()
    parsed = json.loads(json_payload)
    evidence_text = " ".join(
        block.get("text", {}).get("text", "")
        for block in parsed["blocks"]
        if block.get("type") == "section"
        and "Evidence summary" in block.get("text", {}).get("text", "")
    )
    assert "Line one" in evidence_text
    assert "Line two" in evidence_text


# ============================================================================
# Deterministic JSON
# ============================================================================


def test_deterministic_json() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
    )
    run1 = message.as_blocks_json()
    run2 = message.as_blocks_json()
    assert run1 == run2


def test_json_no_raw_secrets() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_FAIL,
        experiment_id="test-001",
        evidence_summary=(
            "xoxb-1234567890-secret-token",
            "/Users/alice/local/path",
        ),
    )
    json_payload = message.as_blocks_json()
    assert "xoxb-1234567890-secret-token" not in json_payload
    assert "/Users/alice/local/path" not in json_payload
    assert "[redacted-secret]" in json_payload
    assert "[redacted-path]" in json_payload


# ============================================================================
# Routing
# ============================================================================


def test_route_promote() -> None:
    result = {"status": "accepted"}
    assert route_kpp_outcome_from_result(result) == KPP_PROMOTE


def test_route_discard_unchanged() -> None:
    result = {"status": "rejected", "failure_class": "unchanged_result"}
    assert route_kpp_outcome_from_result(result) == KPP_DISCARD


def test_route_discard_regression() -> None:
    result = {"status": "rejected", "failure_class": "metric_regression"}
    assert route_kpp_outcome_from_result(result) == KPP_DISCARD


def test_route_fail_timeout() -> None:
    result = {"status": "rejected", "failure_class": "timeout"}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


def test_route_fail_oom() -> None:
    result = {"status": "rejected", "failure_class": "oom"}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


def test_route_fail_guard() -> None:
    result = {"status": "rejected", "failure_class": "guard_failure"}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


def test_route_defer_from_promotion_disposition() -> None:
    result = {"status": "rejected", "failure_class": "guard_failure"}
    promotion = {"disposition": "deferred"}
    assert route_kpp_outcome_from_result(result, promotion) == KPP_DEFER


def test_route_fail_infra_flake() -> None:
    result = {"status": "rejected", "failure_class": "infra_flake"}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


def test_route_oracle_violation() -> None:
    result = {
        "status": "rejected",
        "failure_class": "policy_violation",
        "runner_mode": "oracle_only_governance_reviewer",
    }
    assert route_kpp_outcome_from_result(result) == KPP_ORACLE_VIOLATION


def test_route_surface_breach() -> None:
    result = {
        "status": "rejected",
        "failure_class": "policy_violation",
        "mutated_paths": ["some/file.py"],
    }
    assert route_kpp_outcome_from_result(result) == KPP_SURFACE_BREACH


def test_route_surface_breach_with_empty_mutated_paths() -> None:
    result = {
        "status": "rejected",
        "failure_class": "policy_violation",
        "mutated_paths": [],
    }
    assert route_kpp_outcome_from_result(result) == KPP_SURFACE_BREACH


def test_route_surface_breach_overrides_deferred_for_policy_violation() -> None:
    result = {
        "status": "rejected",
        "failure_class": "policy_violation",
        "mutated_paths": [],
    }
    promotion = {"disposition": "deferred"}
    assert route_kpp_outcome_from_result(result, promotion) == KPP_SURFACE_BREACH


def test_route_default_fail_for_unknown_status() -> None:
    result = {"status": "unknown"}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


def test_route_default_fail_for_rejected_no_failure_class() -> None:
    result = {"status": "rejected"}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


def test_route_default_fail_for_empty_dict() -> None:
    result: dict[str, Any] = {}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


def test_route_default_fail_for_none_failure_class() -> None:
    result = {"status": "rejected", "failure_class": None}
    assert route_kpp_outcome_from_result(result) == KPP_FAIL


# ============================================================================
# Contract coverage
# ============================================================================


def test_kpp_routing_covers_all_failure_classes() -> None:
    """Every FAILURE_CLASSES value must route deterministically."""

    for fc in FAILURE_CLASSES:
        result = {"status": "rejected", "failure_class": fc}
        outcome = route_kpp_outcome_from_result(result)
        assert outcome in KPP_OUTCOMES, (
            f"Failure class {fc!r} routed to unexpected outcome {outcome!r}. "
            f"Expected one of {KPP_OUTCOMES}."
        )


# ============================================================================
# Block Kit structure
# ============================================================================


def test_block_kit_has_required_copy_snippets() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
    )
    json_payload = message.as_blocks_json()
    assert NO_MERGE_ACTION_COPY in json_payload
    assert NO_SENSITIVE_DATA_COPY in json_payload
    assert ARTIFACT_REFERENCE_COPY in json_payload
    assert REDACTION_NOTICE in json_payload
    assert ACTION_REQUIRED_COPY in json_payload or "Action required" in json_payload


def test_block_kit_header_plain_text() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
    )
    parsed = json.loads(message.as_blocks_json())
    header = parsed["blocks"][0]
    assert header["type"] == "header"
    assert header["text"]["type"] == "plain_text"
    assert header["text"]["emoji"] is False


def test_block_kit_no_untrusted_formatting_in_header() -> None:
    message = render_kpp_block_message(
        kpp_outcome=KPP_PROMOTE,
        experiment_id="test-001",
    )
    parsed = json.loads(message.as_blocks_json())
    header_text = parsed["blocks"][0]["text"]["text"]
    assert "`" not in header_text
    assert "<" not in header_text
    assert "&" not in header_text or "&amp;" in header_text


# ============================================================================
# Security
# ============================================================================


def test_no_slack_sdk_import() -> None:
    import scripts.orchestration.experiment_slack_kpp_renderer as renderer_module
    import types

    for name, obj in vars(renderer_module).items():
        if isinstance(obj, types.ModuleType):
            assert "slack" not in obj.__name__, (
                f"Module {obj.__name__!r} leaked into renderer. "
                "Renderer must be pure with no Slack SDK dependencies."
            )


def test_security_sensitive_outcomes_frozen() -> None:
    assert isinstance(SECURITY_SENSITIVE_OUTCOMES, frozenset)
    assert KPP_ORACLE_VIOLATION in SECURITY_SENSITIVE_OUTCOMES
    assert KPP_SURFACE_BREACH in SECURITY_SENSITIVE_OUTCOMES
    assert KPP_PROMOTE not in SECURITY_SENSITIVE_OUTCOMES


# ============================================================================
# Module sanity
# ============================================================================


def test_kpp_outcomes_tuple() -> None:
    assert isinstance(KPP_OUTCOMES, tuple)
    assert len(KPP_OUTCOMES) == 6
    assert KPP_PROMOTE in KPP_OUTCOMES
    assert KPP_SURFACE_BREACH in KPP_OUTCOMES


def test_render_fail_on_invalid_outcome() -> None:
    with pytest.raises(KPPRenderError):
        render_kpp_block_message(
            kpp_outcome="INVALID",
            experiment_id="test-001",
        )


def test_render_fail_on_empty_experiment_id() -> None:
    with pytest.raises(KPPRenderError):
        render_kpp_block_message(
            kpp_outcome=KPP_PROMOTE,
            experiment_id="",
        )


# ============================================================================
# Oracle-audit regression guards (PR #1849)
# ============================================================================


def test_render_kpp_slack_blocks_oracle_violation_redacts_sensitive_output() -> None:
    """Oracle-only governance reviewer with policy violation must render
    ORACLE_VIOLATION / SECURITY ALERT and must not leak raw stdout/stderr,
    local paths, tokens, or patch markers."""
    packet = {
        "experiment_id": "exp-oracle-audit",
        "runner_mode": "oracle_only_governance_reviewer",
    }
    result = {
        "status": "rejected",
        "failure_class": "policy_violation",
        "runner_mode": "oracle_only_governance_reviewer",
        "mutated_paths": [],
        "oracle_results": [
            {
                "command": 'python3 -c "import sys; sys.exit(1)"',
                "returncode": 1,
                "timed_out": False,
                "truncated": False,
                "stdout": "Leak: /Users/alice/.ssh/id_rsa and xoxb-secret-token",
                "stderr": "diff --git a/secret b/secret\nraw patch text",
                "cwd": "/Users/alice/local/repo",
            }
        ],
    }
    blocks_json = experiment_notify.render_kpp_slack_blocks(packet, result)
    assert "ORACLE_VIOLATION" in blocks_json
    assert "SECURITY ALERT" in blocks_json
    assert "/Users/alice" not in blocks_json
    assert "xoxb-secret-token" not in blocks_json
    assert "diff --git" not in blocks_json
    assert "raw patch" not in blocks_json


def test_render_kpp_slack_blocks_surface_breach_for_candidate_patch() -> None:
    """Candidate patch with policy violation and mutated_paths must render
    SURFACE_BREACH, not ORACLE_VIOLATION."""
    packet = {
        "experiment_id": "exp-surface-audit",
        "runner_mode": "candidate_patch",
    }
    result = {
        "status": "rejected",
        "failure_class": "policy_violation",
        "runner_mode": "candidate_patch",
        "mutated_paths": ["core/rag/allowed.py"],
        "oracle_results": [],
    }
    blocks_json = experiment_notify.render_kpp_slack_blocks(packet, result)
    assert "SURFACE_BREACH" in blocks_json
    assert "ORACLE_VIOLATION" not in blocks_json

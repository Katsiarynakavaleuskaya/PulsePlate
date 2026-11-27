"""Tests for deterministic experiment bootstrap packets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import scripts.orchestration.experiment_bootstrap as experiment_bootstrap
from scripts.orchestration.experiment_contract import (
    is_cv_experiment,
    validate_creative_research_origin,
    validate_cv_context,
    validate_experiment_packet,
)
from scripts.orchestration.experiment_bootstrap import (
    _resolve_output_path,
    build_experiment_packet,
    compute_experiment_id,
    main,
    validate_mutable_candidate_surface,
)


def _cv_context() -> dict[str, Any]:
    """Return a deterministic CV packet payload for offline photo->food eval."""

    return {
        "dataset": {
            "id": "food-101",
            "version": "1.0",
            "source": "ethz-food-101",
            "license": "research-only",
            "split_strategy": "official-train-test",
            "label_provenance": "dataset-labels-v1",
        },
        "sensor_conditions": ["blur", "low_light"],
        "uncertainty_band_policy": {
            "mode": "qualitative_only",
            "bands": ["high", "medium", "low", "unknown"],
        },
        "degrade_state_matrix": {
            "high": "show_ranked_candidates",
            "medium": "confirm_top_candidate",
            "low": "manual_entry_required",
            "unknown": "reject_unusable_image",
        },
        "privacy_packet": {
            "raw_image_retention": "none",
            "logging_policy": "no_raw_images",
            "consent_policy": "explicit_opt_in",
            "deletion_policy": "delete_on_request",
        },
    }


def _origin() -> dict[str, str]:
    return {
        "bundle_id": "creative-research-valid",
        "candidate_id": "hyp-batch",
        "promotion_decision": "promote",
    }


def test_build_experiment_packet_is_deterministic() -> None:
    """Identical inputs should produce identical packets and ids."""

    kwargs = {
        "decision_question": "Benchmark RAG reliability for contradiction reduction",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/vector_rag.py", "core/insight/pipeline.py"],
        "oracle_commands": ["pytest -q tests/test_philosophical_runtime.py"],
        "metrics": ["val_bpb", "latency_p95_ms"],
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
    }

    first = build_experiment_packet(**kwargs)
    second = build_experiment_packet(**kwargs)

    assert first == second
    assert first["experiment_id"].startswith("exp-")
    assert first["domain"] == "ml"
    assert "data-scientist-agent" in first["recommended_agents"]
    assert "ml-engineer-agent" in first["recommended_agents"]
    assert "pulseplate-workflow" in first["recommended_skills"]
    assert "pulseplate-gates" in first["recommended_skills"]
    assert "docs-sync" in first["recommended_skills"]
    assert first["metrics"]["baseline_reference"] == "current-main"
    assert first["metrics"]["acceptance_threshold"] == "strict_improvement"


def test_build_experiment_packet_adds_cv_agent_for_cv_intent() -> None:
    """CV-oriented experiment text should add cv-agent to the advisory stack."""

    packet = build_experiment_packet(
        decision_question="Evaluate CV photo pipeline confidence on food image reliability",
        task_class="Experimentation",
        mutable_paths=["docs/prompts/cv/program.md"],
        oracle_commands=[
            "pytest -q tests/test_skill_router.py -k experimentation_lane_skills_for_cv_eval"
        ],
        metrics=["confidence_error"],
        negative_controls=["oracle file unchanged", "no hidden memory"],
        promotion_target="audit_artifact",
        cv_context=_cv_context(),
    )

    assert "cv-agent" in packet["recommended_agents"]
    assert packet["domain"] == "ml"
    assert "ml-engineer-agent" in packet["recommended_agents"]
    assert packet["cv_context"]["dataset"]["id"] == "food-101"
    assert packet["cv_context"]["privacy_packet"]["raw_image_retention"] == "none"


def test_build_experiment_packet_does_not_match_cv_hint_on_substrings() -> None:
    """Substring noise like 'cve' must not force the cv advisory path."""

    packet = build_experiment_packet(
        decision_question="Evaluate drag coefficient with cve notes",
        task_class="Experimentation",
        mutable_paths=["core/rag/vector_rag.py"],
        oracle_commands=["pytest -q tests/test_skill_router.py -k experimentation_lane_skills"],
        metrics=["reliability_score"],
        negative_controls=["oracle file unchanged", "no hidden memory"],
        promotion_target="audit_artifact",
    )

    assert "cv-agent" not in packet["recommended_agents"]


def test_resolve_experiment_domain_avoids_ml_substring_false_positive() -> None:
    """ML text hints should not trigger on larger words without token boundaries."""

    domain = experiment_bootstrap._resolve_experiment_domain(
        decision_question="Prepare prebenchmarking notes for docs",
        task_class="Documentation",
        mutable_paths=["docs/research/example.md"],
    )

    assert domain == "docs"


def test_build_experiment_packet_detects_cv_hint_through_separator_normalization() -> None:
    """Separator-heavy CV terms should still trigger the governed CV lane."""

    packet = build_experiment_packet(
        decision_question="Evaluate photo_recognition reliability on food images",
        task_class="Experimentation",
        mutable_paths=["docs/prompts/cv/program.md"],
        oracle_commands=[
            "pytest -q tests/test_skill_router.py -k experimentation_lane_skills_for_cv_eval"
        ],
        metrics=["confidence_error"],
        negative_controls=["non-food image", "blurred image"],
        promotion_target="audit_artifact",
        cv_context=_cv_context(),
    )

    assert "cv-agent" in packet["recommended_agents"]


def test_build_experiment_packet_requires_cv_context_for_cv_intent() -> None:
    """CV-oriented packets must fail closed without the CV metadata block."""

    with pytest.raises(ValueError, match="must include cv_context"):
        build_experiment_packet(
            decision_question="Evaluate CV photo pipeline confidence on food image reliability",
            task_class="Experimentation",
            mutable_paths=["docs/prompts/cv/program.md"],
            oracle_commands=[
                "pytest -q tests/test_skill_router.py -k experimentation_lane_skills_for_cv_eval"
            ],
            metrics=["confidence_error"],
            negative_controls=["oracle file unchanged", "no hidden memory"],
            promotion_target="audit_artifact",
        )


def test_build_experiment_packet_keeps_non_cv_packets_backward_compatible() -> None:
    """Non-CV packets must not require cv_context or emit it."""

    packet = build_experiment_packet(
        decision_question="Benchmark RAG reliability for contradiction reduction",
        task_class="Experimentation",
        mutable_paths=["core/rag/vector_rag.py"],
        oracle_commands=["pytest -q tests/test_philosophical_runtime.py"],
        metrics=["val_bpb"],
        negative_controls=["oracle file unchanged", "no forbidden path mutation"],
        promotion_target="pr_packet",
    )

    assert "cv_context" not in packet
    assert "creative_research_origin" not in packet
    assert packet["runner_mode"] == "candidate_patch"


def test_build_experiment_packet_adds_normalized_creative_research_origin() -> None:
    """Bootstrap should accept valid optional origin metadata and normalize it."""

    packet = build_experiment_packet(
        decision_question="Bootstrap creative research provenance for promotion",
        task_class="Experimentation",
        mutable_paths=["core/rag/vector_rag.py"],
        oracle_commands=["pytest -q tests/test_philosophical_runtime.py"],
        metrics=["val_bpb"],
        negative_controls=["oracle file unchanged", "no forbidden path mutation"],
        promotion_target="pr_packet",
        creative_research_origin={
            "bundle_id": " creative-research-valid ",
            "candidate_id": " hyp-batch ",
            "promotion_decision": " Promote ",
        },
    )

    assert packet["creative_research_origin"] == _origin()
    assert validate_experiment_packet(packet)["creative_research_origin"] == _origin()


def test_build_experiment_packet_rejects_partial_creative_research_origin() -> None:
    """Function input for origin metadata is all-or-none via exact key validation."""

    with pytest.raises(ValueError, match="unsupported fields"):
        build_experiment_packet(
            decision_question="Bootstrap creative research provenance for promotion",
            task_class="Experimentation",
            mutable_paths=["core/rag/vector_rag.py"],
            oracle_commands=["pytest -q tests/test_philosophical_runtime.py"],
            metrics=["val_bpb"],
            negative_controls=["oracle file unchanged", "no forbidden path mutation"],
            promotion_target="pr_packet",
            creative_research_origin={
                "bundle_id": "creative-research-valid",
                "candidate_id": "hyp-batch",
            },
        )


def test_build_experiment_packet_emits_oracle_only_runner_mode() -> None:
    """Bootstrap must expose oracle-only mode through the canonical packet surface."""

    packet = build_experiment_packet(
        decision_question="Run governance validators for PR evidence",
        task_class="Experimentation",
        runner_mode="oracle_only_governance_reviewer",
        mutable_paths=[
            "scripts/orchestration/experiment_runner.py",
            "docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md",
        ],
        oracle_commands=["python3 scripts/orchestration/check_agent_consistency.py"],
        metrics=["governance_validator_pass"],
        negative_controls=["no candidate patch", "no governance mutation"],
        promotion_target="audit_artifact",
    )

    assert packet["runner_mode"] == "oracle_only_governance_reviewer"
    assert packet["mutable_candidate_surface"] == [
        "docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md",
        "scripts/orchestration/experiment_runner.py",
    ]
    assert validate_experiment_packet(packet)["runner_mode"] == "oracle_only_governance_reviewer"


def test_build_experiment_packet_rejects_governance_surface_in_candidate_mode() -> None:
    """Bootstrap must not mint candidate packets that rewrite governance oracles."""

    with pytest.raises(ValueError, match="must not include governance"):
        build_experiment_packet(
            decision_question="Run governance validators for PR evidence",
            task_class="Experimentation",
            mutable_paths=["docs/orchestration/prompts/governance.program.md"],
            oracle_commands=["python3 scripts/orchestration/check_agent_consistency.py"],
            metrics=["governance_validator_pass"],
            negative_controls=["no candidate patch", "no governance mutation"],
            promotion_target="audit_artifact",
        )


def test_build_experiment_packet_rejects_local_artifact_context_in_oracle_only_mode() -> None:
    """Oracle-only context must point at repo surfaces, not local artifact paths."""

    with pytest.raises(ValueError, match="repo-relative tracked surfaces"):
        build_experiment_packet(
            decision_question="Run governance validators for PR evidence",
            task_class="Experimentation",
            runner_mode="oracle_only_governance_reviewer",
            mutable_paths=["artifacts/orchestration/experiments/results/latest.json"],
            oracle_commands=["python3 scripts/orchestration/check_agent_consistency.py"],
            metrics=["governance_validator_pass"],
            negative_controls=["no candidate patch", "no governance mutation"],
            promotion_target="audit_artifact",
        )


def test_build_experiment_packet_is_deterministic_for_cv_lane() -> None:
    """CV packets should also remain byte-stable for identical inputs."""

    kwargs = {
        "decision_question": "Evaluate photo recognition uncertainty on food images",
        "task_class": "Experimentation",
        "mutable_paths": ["docs/prompts/cv/program.md"],
        "oracle_commands": ["pytest -q tests/test_experiment_bootstrap.py -k cv_context"],
        "metrics": ["top1_accuracy"],
        "negative_controls": ["non-food image", "blurred image"],
        "promotion_target": "audit_artifact",
        "cv_context": _cv_context(),
    }

    first = build_experiment_packet(**kwargs)
    second = build_experiment_packet(**kwargs)

    assert first == second
    assert first["cv_context"]["dataset"]["id"] == "food-101"
    assert first["cv_context"]["degrade_state_matrix"]["unknown"] == "reject_unusable_image"


def test_build_experiment_packet_normalizes_cv_context_deterministically() -> None:
    """CV packet fields should normalize order-sensitive inputs into stable JSON."""

    packet = build_experiment_packet(
        decision_question="Evaluate photo recognition uncertainty on food images",
        task_class="Experimentation",
        mutable_paths=["docs/prompts/cv/program.md"],
        oracle_commands=["pytest -q tests/test_experiment_bootstrap.py -k cv_context"],
        metrics=["top1_accuracy"],
        negative_controls=["non-food image", "blurred image"],
        promotion_target="audit_artifact",
        cv_context={
            **_cv_context(),
            "sensor_conditions": ["low_light", "blur", "blur"],
        },
    )

    assert packet["cv_context"]["sensor_conditions"] == ["blur", "low_light"]
    assert packet["cv_context"]["uncertainty_band_policy"]["bands"] == [
        "high",
        "medium",
        "low",
        "unknown",
    ]
    assert packet["cv_context"]["degrade_state_matrix"] == {
        "high": "show_ranked_candidates",
        "medium": "confirm_top_candidate",
        "low": "manual_entry_required",
        "unknown": "reject_unusable_image",
    }


def test_main_writes_cv_context_when_metadata_is_complete(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """CLI should emit cv_context for valid offline CV packets."""

    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    exit_code = main(
        [
            "--decision-question",
            "Evaluate CV photo pipeline confidence on food image reliability",
            "--mutable-path",
            "docs/prompts/cv/program.md",
            "--oracle-command",
            "pytest -q tests/test_skill_router.py -k experimentation_lane_skills_for_cv_eval",
            "--metric",
            "confidence_error",
            "--negative-control",
            "non-food image",
            "--negative-control",
            "blurred image",
            "--promotion-target",
            "audit_artifact",
            "--cv-mode",
            "--cv-dataset-id",
            "food-101",
            "--cv-dataset-version",
            "1.0",
            "--cv-dataset-source",
            "ethz-food-101",
            "--cv-dataset-license",
            "research-only",
            "--cv-split-strategy",
            "official-train-test",
            "--cv-label-provenance",
            "dataset-labels-v1",
            "--cv-sensor-condition",
            "blur",
            "--cv-sensor-condition",
            "low_light",
            "--cv-degrade-high",
            "show_ranked_candidates",
            "--cv-degrade-medium",
            "confirm_top_candidate",
            "--cv-degrade-low",
            "manual_entry_required",
            "--cv-degrade-unknown",
            "reject_unusable_image",
            "--cv-privacy-retention",
            "none",
            "--cv-privacy-logging",
            "no_raw_images",
            "--cv-privacy-consent",
            "explicit_opt_in",
            "--cv-privacy-deletion",
            "delete_on_request",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    output = json.loads(captured.out)
    packet_path = repo_root / output["output"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["cv_context"]["dataset"]["id"] == "food-101"
    assert packet["cv_context"]["privacy_packet"]["consent_policy"] == "explicit_opt_in"


def test_main_writes_oracle_only_runner_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    exit_code = main(
        [
            "--decision-question",
            "Run governance validators for PR evidence",
            "--runner-mode",
            "oracle_only_governance_reviewer",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--oracle-command",
            "python3 scripts/orchestration/check_agent_consistency.py",
            "--metric",
            "governance_validator_pass",
            "--negative-control",
            "no candidate patch",
            "--negative-control",
            "no governance mutation",
            "--promotion-target",
            "audit_artifact",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    output = json.loads(captured.out)
    packet = json.loads((repo_root / output["output"]).read_text(encoding="utf-8"))
    assert output["runner_mode"] == "oracle_only_governance_reviewer"
    assert "creative_research_origin" not in output
    assert packet["runner_mode"] == "oracle_only_governance_reviewer"


def test_main_writes_creative_research_origin_metadata(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """CLI should emit valid optional creative_research_origin metadata."""

    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    exit_code = main(
        [
            "--decision-question",
            "Bootstrap creative research provenance for promotion",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--oracle-command",
            "pytest -q tests/test_philosophical_runtime.py",
            "--metric",
            "val_bpb",
            "--negative-control",
            "oracle file unchanged",
            "--negative-control",
            "no forbidden path mutation",
            "--promotion-target",
            "pr_packet",
            "--creative-research-bundle-id",
            "creative-research-valid",
            "--creative-research-candidate-id",
            "hyp-batch",
            "--creative-research-promotion-decision",
            "promote",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    output = json.loads(captured.out)
    packet = json.loads((repo_root / output["output"]).read_text(encoding="utf-8"))
    assert output["creative_research_origin"] == _origin()
    assert packet["creative_research_origin"] == _origin()


def test_main_rejects_partial_creative_research_origin_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI origin flags should fail cleanly unless all three are present."""

    exit_code = main(
        [
            "--decision-question",
            "Bootstrap creative research provenance for promotion",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--oracle-command",
            "pytest -q tests/test_philosophical_runtime.py",
            "--metric",
            "val_bpb",
            "--negative-control",
            "oracle file unchanged",
            "--negative-control",
            "no forbidden path mutation",
            "--promotion-target",
            "pr_packet",
            "--creative-research-bundle-id",
            "creative-research-valid",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "creative research origin flags are all-or-none" in captured.out


def test_main_rejects_invalid_creative_research_origin_before_packet_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """CLI should reject unsafe all-flag origin metadata before writing packets."""

    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    exit_code = main(
        [
            "--decision-question",
            "Bootstrap creative research provenance for promotion",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--oracle-command",
            "pytest -q tests/test_philosophical_runtime.py",
            "--metric",
            "val_bpb",
            "--negative-control",
            "oracle file unchanged",
            "--negative-control",
            "no forbidden path mutation",
            "--promotion-target",
            "pr_packet",
            "--creative-research-bundle-id",
            "../escape",
            "--creative-research-candidate-id",
            "hyp-batch",
            "--creative-research-promotion-decision",
            "promote",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "safe local identifier" in captured.out
    assert not experiment_dir.exists()


def test_validate_experiment_packet_requires_cv_context_for_cv_lane() -> None:
    """Validation should reject CV packets that arrive without cv_context."""

    packet = build_experiment_packet(
        decision_question="Benchmark RAG reliability for contradiction reduction",
        task_class="Experimentation",
        mutable_paths=["core/rag/vector_rag.py"],
        oracle_commands=["pytest -q tests/test_philosophical_runtime.py"],
        metrics=["val_bpb"],
        negative_controls=["oracle file unchanged", "no forbidden path mutation"],
        promotion_target="pr_packet",
    )
    packet["decision_question"] = "Evaluate CV photo pipeline confidence on food image reliability"
    packet["mutable_candidate_surface"] = ["docs/prompts/cv/program.md"]

    with pytest.raises(
        ValueError,
        match="CV-oriented experiment packets must include cv_context",
    ):
        validate_experiment_packet(packet)


def test_main_rejects_incomplete_cv_context(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI should fail cleanly when CV mode is enabled without the required metadata."""

    exit_code = main(
        [
            "--decision-question",
            "Evaluate CV photo pipeline confidence on food image reliability",
            "--mutable-path",
            "docs/prompts/cv/program.md",
            "--oracle-command",
            "pytest -q tests/test_skill_router.py -k experimentation_lane_skills_for_cv_eval",
            "--metric",
            "confidence_error",
            "--negative-control",
            "non-food image",
            "--negative-control",
            "blurred image",
            "--promotion-target",
            "audit_artifact",
            "--cv-mode",
            "--cv-dataset-id",
            "food-101",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: Experiment packet cv_context" in captured.out


def test_validate_mutable_candidate_surface_rejects_forbidden_path() -> None:
    """Forbidden mutable surfaces should fail closed."""

    with pytest.raises(ValueError, match="Invalid paths"):
        validate_mutable_candidate_surface(["docs/orchestration/workflow.md"])


def test_validate_mutable_candidate_surface_rejects_traversal_escape() -> None:
    """Traversal segments must not bypass the mutable-surface allowlist."""

    with pytest.raises(ValueError, match="docs/orchestration/workflow.md"):
        validate_mutable_candidate_surface(["core/rag/../../docs/orchestration/workflow.md"])


def test_validate_mutable_candidate_surface_normalizes_safe_relative_paths() -> None:
    """Benign traversal inside an allowed root should normalize to the allowed file."""

    normalized = validate_mutable_candidate_surface(["core/rag/../rag/vector_rag.py"])

    assert normalized == ["core/rag/vector_rag.py"]


def test_main_rejects_missing_oracles(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI should fail cleanly when no immutable oracle command is provided."""

    exit_code = main(
        [
            "--decision-question",
            "Benchmark RAG reliability",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--metric",
            "val_bpb",
            "--negative-control",
            "oracle file unchanged",
            "--negative-control",
            "no forbidden path mutation",
            "--promotion-target",
            "pr_packet",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: At least one --oracle-command is required." in captured.out


def test_main_writes_relative_output_inside_repo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """CLI should write output under the experiment artifact directory."""

    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    relative_output = Path("tmp/experiment-packet.json")
    repo_output = (experiment_bootstrap.EXPERIMENT_PACKET_DIR / relative_output).resolve()

    packet = {
        "schema_version": "1.0",
        "experiment_id": "exp-testpacket",
        "runner_mode": "candidate_patch",
        "decision_question": "Test experiment bootstrap write",
        "task_class": "Experimentation",
        "domain": "ml",
        "mutable_candidate_surface": ["core/rag/vector_rag.py"],
        "immutable_oracles": [
            {
                "command": "pytest -q tests/test_skill_router.py -k experimentation_lane_skills",
                "expected_signal": "must pass",
            }
        ],
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
            "stop_condition": "stop",
        },
        "metrics": {
            "primary": "val_bpb",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
        "primary_agent": "agent-coordinator",
        "reviewer": "architecture-specialist",
        "recommended_agents": ["agent-coordinator", "data-scientist-agent"],
        "recommended_skills": ["pulseplate-workflow", "pulseplate-gates"],
        "skill_routing": {
            "policy_version": "2026-03-27",
            "selection_mode": "deterministic-weighted",
            "requested_agents": [],
            "task_classification": {
                "label": "experiment",
                "score": 6,
                "reasons": ["lexeme:experiment(+2)", "lexeme:benchmark(+2)"],
            },
            "required": [
                {
                    "skill": "pulseplate-workflow",
                    "rationale": "Mandatory entry skill for all PulsePlate tasks.",
                    "reasons": ["always-on"],
                }
            ],
            "recommended": [{"skill": "pulseplate-gates", "score": 4}],
            "conditional": [],
            "blocked": [],
        },
        "routing_context": {
            "cluster": "ml",
            "domain": "ml",
            "task_type": "Experimentation",
            "primary": "ai-innovation-specialist",
            "secondary": "rag-systems-agent",
            "reviewer": "architecture-specialist",
        },
    }
    monkeypatch.setattr(
        "scripts.orchestration.experiment_bootstrap.build_experiment_packet",
        lambda **_: packet,
    )

    exit_code = main(
        [
            "--decision-question",
            "ignored",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--oracle-command",
            "pytest -q tests/test_skill_router.py -k experimentation_lane_skills",
            "--metric",
            "val_bpb",
            "--negative-control",
            "oracle file unchanged",
            "--negative-control",
            "no forbidden path mutation",
            "--promotion-target",
            "pr_packet",
            "--output",
            str(relative_output),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    written = json.loads(repo_output.read_text(encoding="utf-8"))
    assert written["experiment_id"] == "exp-testpacket"
    assert (
        json.loads(captured.out)["output"]
        == (Path("artifacts/orchestration/experiments") / relative_output).as_posix()
    )


def test_resolve_output_path_rejects_outside_repo(tmp_path: Path) -> None:
    """Output path must remain inside the experiment artifact directory."""

    outside = tmp_path / "experiment-packet.json"
    with pytest.raises(
        ValueError,
        match="--output must stay within artifacts/orchestration/experiments",
    ):
        _resolve_output_path(str(outside), "exp-ignored")


def test_build_experiment_packet_rejects_budget_overrides_above_hard_caps() -> None:
    """Budget overrides above protocol caps must fail closed."""

    with pytest.raises(ValueError, match="wall_clock_seconds must be <= 600"):
        build_experiment_packet(
            decision_question="Benchmark RAG reliability for contradiction reduction",
            task_class="Experimentation",
            mutable_paths=["core/rag/vector_rag.py"],
            oracle_commands=["pytest -q tests/test_philosophical_runtime.py"],
            metrics=["val_bpb"],
            negative_controls=["oracle file unchanged", "no forbidden path mutation"],
            promotion_target="pr_packet",
            budgets={"wall_clock_seconds": 601},
        )


def test_build_experiment_packet_rejects_unsupported_budget_keys() -> None:
    """Unknown budget override keys must fail closed before packet generation."""

    with pytest.raises(ValueError, match="Unsupported budget keys: gpu_budget"):
        build_experiment_packet(
            decision_question="Benchmark RAG reliability for contradiction reduction",
            task_class="Experimentation",
            mutable_paths=["core/rag/vector_rag.py"],
            oracle_commands=["pytest -q tests/test_philosophical_runtime.py"],
            metrics=["val_bpb"],
            negative_controls=["oracle file unchanged", "no forbidden path mutation"],
            promotion_target="pr_packet",
            budgets={"gpu_budget": 1},
        )


def test_compute_experiment_id_changes_with_budgets_and_stop_condition() -> None:
    """Execution constraints must participate in deterministic experiment ids."""

    base_kwargs = {
        "decision_question": "Benchmark RAG reliability for contradiction reduction",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/vector_rag.py"],
        "immutable_oracles": [
            {
                "command": "pytest -q tests/test_philosophical_runtime.py",
                "expected_signal": "must pass",
            }
        ],
        "metrics": {
            "primary": "val_bpb",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
    }

    default_id = compute_experiment_id(
        budgets={
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        stop_condition="Stop on timeout.",
        **base_kwargs,
    )
    budget_variant_id = compute_experiment_id(
        budgets={
            "wall_clock_seconds": 301,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        stop_condition="Stop on timeout.",
        **base_kwargs,
    )
    stop_variant_id = compute_experiment_id(
        budgets={
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        stop_condition="Stop on unchanged result.",
        **base_kwargs,
    )

    assert default_id != budget_variant_id
    assert default_id != stop_variant_id


def test_compute_experiment_id_changes_with_cv_context() -> None:
    """CV packet metadata must participate in deterministic ids."""

    base_kwargs = {
        "decision_question": "Evaluate photo recognition uncertainty on food images",
        "task_class": "Experimentation",
        "mutable_paths": ["docs/prompts/cv/program.md"],
        "immutable_oracles": [
            {
                "command": "pytest -q tests/test_experiment_bootstrap.py -k cv_context",
                "expected_signal": "must pass",
            }
        ],
        "metrics": {
            "primary": "top1_accuracy",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["non-food image", "blurred image"],
        "promotion_target": "audit_artifact",
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        "stop_condition": "Stop on timeout.",
    }

    base_id = compute_experiment_id(
        cv_context=_cv_context(),
        **base_kwargs,
    )
    variant_id = compute_experiment_id(
        cv_context={
            **_cv_context(),
            "privacy_packet": {
                **_cv_context()["privacy_packet"],
                "deletion_policy": "delete_after_eval",
            },
        },
        **base_kwargs,
    )

    assert base_id != variant_id


def test_compute_experiment_id_keeps_legacy_non_cv_shape() -> None:
    """Non-CV ids must remain backward compatible with the pre-PR5 payload shape."""

    base_kwargs = {
        "decision_question": "Benchmark RAG reliability for contradiction reduction",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/vector_rag.py"],
        "immutable_oracles": [
            {
                "command": "pytest -q tests/test_philosophical_runtime.py",
                "expected_signal": "must pass",
            }
        ],
        "metrics": {
            "primary": "val_bpb",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        "stop_condition": "Stop on timeout.",
    }
    legacy_payload = json.dumps(
        {
            "decision_question": base_kwargs["decision_question"],
            "task_class": base_kwargs["task_class"],
            "mutable_paths": base_kwargs["mutable_paths"],
            "immutable_oracles": base_kwargs["immutable_oracles"],
            "metrics": base_kwargs["metrics"],
            "negative_controls": base_kwargs["negative_controls"],
            "promotion_target": base_kwargs["promotion_target"],
            "budgets": base_kwargs["budgets"],
            "stop_condition": base_kwargs["stop_condition"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    legacy_id = f"exp-{hashlib.sha256(legacy_payload.encode('utf-8')).hexdigest()[:12]}"

    assert compute_experiment_id(cv_context=None, **base_kwargs) == legacy_id


def test_compute_experiment_id_binds_candidate_patch_and_base() -> None:
    """Different candidate bytes or base commits must produce distinct ids."""

    base_kwargs = {
        "decision_question": "Evaluate a bounded candidate patch",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/orchestration.py"],
        "immutable_oracles": [
            {
                "command": "pytest -q tests/test_rag_orchestration.py",
                "expected_signal": "must pass",
            }
        ],
        "metrics": {
            "primary": "oracle_pass",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "audit_artifact",
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 1,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 1,
        },
        "stop_condition": "Stop on timeout.",
    }

    first = compute_experiment_id(
        candidate_patch_fingerprint="sha256:" + ("a" * 64),
        base_commit_sha="1" * 40,
        **base_kwargs,
    )
    patch_variant = compute_experiment_id(
        candidate_patch_fingerprint="sha256:" + ("b" * 64),
        base_commit_sha="1" * 40,
        **base_kwargs,
    )
    base_variant = compute_experiment_id(
        candidate_patch_fingerprint="sha256:" + ("a" * 64),
        base_commit_sha="2" * 40,
        **base_kwargs,
    )

    assert first != patch_variant
    assert first != base_variant


def test_compute_experiment_id_changes_with_oracle_only_runner_mode() -> None:
    """Non-default runner behavior must participate in deterministic ids."""

    base_kwargs = {
        "decision_question": "Run governance validators for PR evidence",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/vector_rag.py"],
        "immutable_oracles": [
            {
                "command": "python3 scripts/orchestration/check_agent_consistency.py",
                "expected_signal": "must pass",
            }
        ],
        "metrics": {
            "primary": "governance_validator_pass",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["no candidate patch", "no governance mutation"],
        "promotion_target": "audit_artifact",
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        "stop_condition": "Stop on timeout.",
    }

    candidate_id = compute_experiment_id(**base_kwargs)
    oracle_only_id = compute_experiment_id(
        runner_mode="oracle_only_governance_reviewer",
        **base_kwargs,
    )

    assert candidate_id != oracle_only_id


def test_compute_experiment_id_changes_with_creative_research_origin() -> None:
    """Origin metadata must affect ids only when the optional block is present."""

    base_kwargs = {
        "decision_question": "Bootstrap creative research provenance for promotion",
        "task_class": "Experimentation",
        "mutable_paths": ["core/rag/vector_rag.py"],
        "immutable_oracles": [
            {
                "command": "pytest -q tests/test_philosophical_runtime.py",
                "expected_signal": "must pass",
            }
        ],
        "metrics": {
            "primary": "val_bpb",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": ["oracle file unchanged", "no forbidden path mutation"],
        "promotion_target": "pr_packet",
        "budgets": {
            "wall_clock_seconds": 300,
            "retry_budget": 1,
            "max_changed_files": 3,
            "network_budget": 0,
            "benchmark_budget": 1,
            "test_budget": 2,
        },
        "stop_condition": "Stop on timeout.",
    }

    no_origin_id = compute_experiment_id(**base_kwargs)
    with_origin_id = compute_experiment_id(
        creative_research_origin=_origin(),
        **base_kwargs,
    )
    with_raw_origin_id = compute_experiment_id(
        creative_research_origin={
            "bundle_id": " creative-research-valid ",
            "candidate_id": " hyp-batch ",
            "promotion_decision": " PROMOTE ",
        },
        **base_kwargs,
    )
    variant_origin_id = compute_experiment_id(
        creative_research_origin={**_origin(), "promotion_decision": "defer"},
        **base_kwargs,
    )

    assert no_origin_id != with_origin_id
    assert with_origin_id == with_raw_origin_id
    assert with_origin_id != variant_origin_id


def test_validate_creative_research_origin_normalizes_values() -> None:
    """Shared origin validation should strip IDs and normalize decisions."""

    assert (
        validate_creative_research_origin(
            {
                "bundle_id": " creative-research-valid ",
                "candidate_id": " hyp-batch ",
                "promotion_decision": " PROMOTE ",
            }
        )
        == _origin()
    )


def test_validate_experiment_packet_rejects_invalid_creative_research_origin() -> None:
    """Packet validation should fail closed before promotion sees unsafe origin IDs."""

    packet = build_experiment_packet(
        decision_question="Bootstrap creative research provenance for promotion",
        task_class="Experimentation",
        mutable_paths=["core/rag/vector_rag.py"],
        oracle_commands=["pytest -q tests/test_philosophical_runtime.py"],
        metrics=["val_bpb"],
        negative_controls=["oracle file unchanged", "no forbidden path mutation"],
        promotion_target="pr_packet",
    )
    packet["creative_research_origin"] = {
        "bundle_id": "../escape",
        "candidate_id": "hyp-batch",
        "promotion_decision": "promote",
    }

    with pytest.raises(ValueError, match="safe local identifier"):
        validate_experiment_packet(packet)


def test_validate_cv_context_rejects_missing_dataset() -> None:
    """CV context must fail closed when dataset provenance is missing."""

    invalid = _cv_context()
    invalid.pop("dataset")

    with pytest.raises(ValueError, match="cv_context.dataset must be an object"):
        validate_cv_context(invalid)


def test_validate_cv_context_rejects_non_canonical_band_order() -> None:
    """Confidence buckets must stay canonical and deterministic."""

    invalid = _cv_context()
    invalid["uncertainty_band_policy"]["bands"] = ["medium", "high", "low", "unknown"]

    with pytest.raises(ValueError, match="uncertainty_band_policy.bands must equal"):
        validate_cv_context(invalid)


def test_validate_cv_context_rejects_missing_degrade_mapping() -> None:
    """Each qualitative bucket must map to a deterministic degrade state."""

    invalid = _cv_context()
    invalid["degrade_state_matrix"].pop("unknown")

    with pytest.raises(ValueError, match="degrade_state_matrix entries must be one of"):
        validate_cv_context(invalid)


def test_validate_cv_context_rejects_missing_privacy_field() -> None:
    """Privacy packet omissions must fail closed for CV packets."""

    invalid = _cv_context()
    invalid["privacy_packet"].pop("consent_policy")

    with pytest.raises(ValueError, match="privacy_packet must include a non-empty consent_policy"):
        validate_cv_context(invalid)


def test_main_fails_cleanly_on_output_write_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Write failures inside the artifact tree must respect the FAIL/exit=1 contract."""

    repo_root = tmp_path.resolve()
    experiment_dir = (repo_root / "artifacts" / "orchestration" / "experiments").resolve()
    experiment_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(experiment_bootstrap, "REPO_ROOT", repo_root)
    monkeypatch.setattr(experiment_bootstrap, "EXPERIMENT_PACKET_DIR", experiment_dir)

    output_dir = experiment_dir / "occupied"
    output_dir.mkdir()

    exit_code = main(
        [
            "--decision-question",
            "ignored",
            "--mutable-path",
            "core/rag/vector_rag.py",
            "--oracle-command",
            "pytest -q tests/test_skill_router.py -k experimentation_lane_skills",
            "--metric",
            "val_bpb",
            "--negative-control",
            "oracle file unchanged",
            "--negative-control",
            "no forbidden path mutation",
            "--promotion-target",
            "pr_packet",
            "--output",
            "occupied",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL: unable to write experiment packet:" in captured.out


# A fixed source-governance counterexample, not optical data or a live evidence receipt.
_CV_ORACLE_REVIEW_PATHS = (
    ".github/workflows/cd.yml",
    ".github/workflows/ci.yml",
    ".secrets.baseline",
    "docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md",
    "docs/roadmap/BACKLOG_LEDGER.md",
    "scripts/AGENTS.md",
    "scripts/QUICK_FIX_PRODUCTION.sh",
    "scripts/ci/prometheus_source_image.py",
    "scripts/deploy.sh",
    "scripts/deploy_production.sh",
    "scripts/orchestration/experiment_bootstrap.py",
    "scripts/orchestration/experiment_contract.py",
    "tests/AGENTS.md",
    "tests/test_caddy_deploy_provenance.py",
    "tests/test_cd_workflow_production_deploy_gate.py",
    "tests/test_ci_workflow_pr_size_governance_contract.py",
    "tests/test_deploy_contract_scripts.py",
    "tests/test_experiment_bootstrap.py",
    "tests/test_legacy_growth_guard.py",
    "tests/test_prometheus_source_image.py",
)
_CV_ORACLE_REVIEW_QUESTION = (
    "For PR2493 actual post-sync committed head "
    "29f5bf2a0333352a2590dc5a5fa335e0f268c826, "
    "current base/merge-base "
    "13556deaf2ddcbff733b7c4ff1a4f0516494770b, "
    "genuine merge parents "
    "a546b95a1a17f346669d4a85daa9364f20d7d544/"
    "13556deaf2ddcbff733b7c4ff1a4f0516494770b, "
    "net diff sha256:"
    "7e3634ebb2432dd60d69b31851a6eb44715a135b2c97a6b3664791118098cd57, "
    "do the complete baseline and historical Prometheus admission preserve original18 criteria, "
    "exact native/source/credential boundaries and all negative controls? "
    "Synthetic oracles do not prove actual image publication, successor-main B7/DK2 or D8."
)


def _cv_applicability_inputs() -> dict[str, Any]:
    """Supply valid existing paths and oracles without optical intent or metadata."""
    return {
        "decision_question": "Check deterministic source controls",
        "task_class": "bugfix",
        "mutable_paths": ["core/rag/vector_rag.py"],
        "oracle_commands": ["pytest -q tests/test_experiment_bootstrap.py"],
        "metrics": ["required_controls_pass"],
        "negative_controls": ["no candidate mutation", "all source paths retained"],
        "promotion_target": "audit_artifact",
    }


def test_cv_oracle_constructor_retains_complete_source_review_context() -> None:
    """Keep all twenty real review paths without fabricating an optical overlay."""
    kwargs = _cv_applicability_inputs()
    kwargs.update(
        decision_question=_CV_ORACLE_REVIEW_QUESTION,
        mutable_paths=list(_CV_ORACLE_REVIEW_PATHS),
        runner_mode="oracle_only_governance_reviewer",
    )
    packet = build_experiment_packet(**kwargs)
    assert packet["runner_mode"] == "oracle_only_governance_reviewer"
    assert packet["mutable_candidate_surface"] == sorted(_CV_ORACLE_REVIEW_PATHS)
    assert "cv_context" not in packet
    assert "cv-agent" not in packet["recommended_agents"]
    validated = validate_experiment_packet(packet)
    assert validated["mutable_candidate_surface"] == sorted(_CV_ORACLE_REVIEW_PATHS)
    assert "cv_context" not in validated
    assert validated["runner_mode"] == packet["runner_mode"]
    assert validated["immutable_oracles"] == packet["immutable_oracles"]
    kwargs["mutable_paths"] = list(reversed(_CV_ORACLE_REVIEW_PATHS))
    assert build_experiment_packet(**kwargs)["experiment_id"] == packet["experiment_id"]
    kwargs["mutable_paths"] = [
        path
        for path in _CV_ORACLE_REVIEW_PATHS
        if path != "scripts/orchestration/experiment_bootstrap.py"
    ]
    assert build_experiment_packet(**kwargs)["experiment_id"] != packet["experiment_id"]


def test_cv_oracle_constructor_preserves_canonical_context_domain() -> None:
    """Propagate Oracle mode so a CV context path reaches canonical domain routing."""
    kwargs = _cv_applicability_inputs()
    kwargs.update(
        mutable_paths=["docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md"],
        runner_mode="oracle_only_governance_reviewer",
    )
    packet = build_experiment_packet(**kwargs)
    assert "cv_context" not in packet
    assert packet["domain"] == "cv"


def test_cv_oracle_downstream_independently_accepts_complete_review_context() -> None:
    """Reach downstream validation even while the full-context constructor is broken."""
    kwargs = _cv_applicability_inputs()
    kwargs["runner_mode"] = "oracle_only_governance_reviewer"
    packet = build_experiment_packet(**kwargs)
    assert (
        validate_experiment_packet(packet)["mutable_candidate_surface"] == kwargs["mutable_paths"]
    )
    packet["decision_question"] = _CV_ORACLE_REVIEW_QUESTION
    packet["mutable_candidate_surface"] = list(_CV_ORACLE_REVIEW_PATHS)
    validated = validate_experiment_packet(packet)
    assert validated["mutable_candidate_surface"] == sorted(_CV_ORACLE_REVIEW_PATHS)
    assert validated["runner_mode"] == "oracle_only_governance_reviewer"
    assert "cv_context" not in validated


@pytest.mark.parametrize("runner_mode", ["candidate_patch", "oracle_only_governance_reviewer"])
@pytest.mark.parametrize("field", ["decision_question", "task_class"])
@pytest.mark.parametrize(
    "cue",
    [
        "cv",
        "photo",
        "vision",
        "multimodal",
        "image recognition",
        "image classification",
        "image segmentation",
    ],
)
def test_cv_explicit_intent_requires_overlay_in_both_modes(
    runner_mode: str, field: str, cue: str
) -> None:
    """Retain every finite intent cue in both input fields and both execution modes."""
    kwargs = _cv_applicability_inputs()
    kwargs.update(runner_mode=runner_mode, cv_context=_cv_context())
    kwargs[field] = "Container image work with " + cue
    packet = build_experiment_packet(**kwargs)
    assert validate_experiment_packet(packet)["cv_context"] == packet["cv_context"]
    kwargs["cv_context"] = None
    with pytest.raises(ValueError, match="CV-oriented experiment packets must include cv_context"):
        build_experiment_packet(**kwargs)
    packet.pop("cv_context")
    with pytest.raises(ValueError, match="CV-oriented experiment packets must include cv_context"):
        validate_experiment_packet(packet)


@pytest.mark.parametrize(
    "runner_mode,expected_mode,requires_overlay",
    [
        (None, "candidate_patch", True),
        ("candidate_patch", "candidate_patch", True),
        (" CANDIDATE_PATCH ", "candidate_patch", True),
        ("oracle_only_governance_reviewer", "oracle_only_governance_reviewer", False),
        (" ORACLE_ONLY_GOVERNANCE_REVIEWER ", "oracle_only_governance_reviewer", False),
    ],
)
def test_cv_mode_distinguishes_candidate_paths_from_oracle_context(
    runner_mode: str | None, expected_mode: str, requires_overlay: bool
) -> None:
    """The same admitted CV path has different input roles, with legacy mode normalization."""
    kwargs = _cv_applicability_inputs()
    kwargs.update(
        mutable_paths=["docs/prompts/cv/program.md"],
        runner_mode=runner_mode,
        cv_context=_cv_context(),
    )
    packet = build_experiment_packet(**kwargs)
    assert validate_experiment_packet(packet)["runner_mode"] == expected_mode
    assert (
        is_cv_experiment(
            kwargs["decision_question"],
            runner_mode=runner_mode,
            surface_paths=kwargs["mutable_paths"],
        )
        is requires_overlay
    )
    kwargs["cv_context"] = None
    packet.pop("cv_context")
    if requires_overlay:
        with pytest.raises(ValueError, match="must include cv_context"):
            build_experiment_packet(**kwargs)
        with pytest.raises(ValueError, match="must include cv_context"):
            validate_experiment_packet(packet)
    else:
        assert "cv_context" not in build_experiment_packet(**kwargs)
        assert "cv_context" not in validate_experiment_packet(packet)


def test_cv_legacy_positional_and_omitted_mode_keep_candidate_intent() -> None:
    """Existing creative-style positional calls and omitted mode retain CV path intent."""
    assert is_cv_experiment("Check controls", "Experimentation", "docs/prompts/cv/program.md")
    assert is_cv_experiment("Check controls", surface_paths=["docs/prompts/cv/program.md"])
    kwargs = _cv_applicability_inputs()
    kwargs["mutable_paths"] = ["docs/prompts/cv/program.md"]
    with pytest.raises(ValueError, match="must include cv_context"):
        build_experiment_packet(**kwargs)


@pytest.mark.parametrize("runner_mode", ["", "  ", "unknown", 7, False])
def test_cv_invalid_mode_cannot_bypass_overlay_admission(runner_mode: object) -> None:
    """Invalid modes fail through the existing mode owner, never an oracle fallback."""
    kwargs = _cv_applicability_inputs()
    packet = build_experiment_packet(**kwargs)
    assert validate_experiment_packet(packet)["runner_mode"] == "candidate_patch"
    with pytest.raises(ValueError, match="runner_mode must be one of"):
        is_cv_experiment("Check controls", runner_mode=runner_mode, surface_paths=[])
    kwargs["runner_mode"] = runner_mode
    with pytest.raises(ValueError, match="runner_mode must be one of"):
        build_experiment_packet(**kwargs)
    packet["runner_mode"] = runner_mode
    with pytest.raises(ValueError, match="runner_mode must be one of"):
        validate_experiment_packet(packet)


@pytest.mark.parametrize(
    "section,key,diagnostic",
    [
        ("dataset", "id", "dataset must include a non-empty id"),
        (
            "privacy_packet",
            "consent_policy",
            "privacy_packet must include a non-empty consent_policy",
        ),
        ("degrade_state_matrix", "unknown", "degrade_state_matrix entries must be one of"),
        ("uncertainty_band_policy", "bands", "uncertainty_band_policy.bands must be a list"),
    ],
)
def test_cv_negative_oracle_intent_still_validates_supplied_metadata(
    section: str, key: str, diagnostic: str
) -> None:
    """A cue-negative oracle cannot bypass malformed non-None metadata validation."""
    kwargs = _cv_applicability_inputs()
    kwargs["runner_mode"] = "oracle_only_governance_reviewer"
    packet = build_experiment_packet(**kwargs)
    assert "cv_context" not in validate_experiment_packet(packet)
    invalid = _cv_context()
    invalid[section].pop(key)
    kwargs["cv_context"] = invalid
    with pytest.raises(ValueError, match=diagnostic):
        build_experiment_packet(**kwargs)
    packet["cv_context"] = invalid
    with pytest.raises(ValueError, match=diagnostic):
        validate_experiment_packet(packet)


@pytest.mark.parametrize(
    "parts,expected",
    [
        (("container image publication",), False),
        (("scripts/ci/prometheus_source_image.py",), False),
        (("visionary cve photograph",), False),
        (("preimage classification",), False),
        (("image classificationish",), False),
        (("image", "classification"), False),
        (("image", "recognition"), False),
        (("image classification",), True),
        (("image_classification",), True),
        (("image-recognition",), True),
        (("image/segmentation",), True),
        (("cv",), True),
        (("photo",), True),
        (("vision",), True),
        (("multimodal",), True),
        (("container image", "photo"), True),
    ],
)
def test_cv_cues_are_bounded_and_do_not_join_independent_parts(
    parts: tuple[str, ...], expected: bool
) -> None:
    """Require same-part optical compounds and preserve finite token boundaries."""
    assert is_cv_experiment(*parts) is expected


def test_cv_advisor_preserves_task_class_input_asymmetry() -> None:
    """Task-class-only admission stays mandatory without adding that input to the advisor."""
    kwargs = _cv_applicability_inputs()
    kwargs.update(
        task_class="CV",
        runner_mode="oracle_only_governance_reviewer",
        mutable_paths=list(_CV_ORACLE_REVIEW_PATHS),
        cv_context=_cv_context(),
    )
    packet = build_experiment_packet(**kwargs)
    assert packet["domain"] == "ml"
    assert "cv-agent" not in packet["recommended_agents"]
    assert validate_experiment_packet(packet)["cv_context"] == packet["cv_context"]
    kwargs["decision_question"] = "Evaluate photo recognition"
    assert "cv-agent" in build_experiment_packet(**kwargs)["recommended_agents"]

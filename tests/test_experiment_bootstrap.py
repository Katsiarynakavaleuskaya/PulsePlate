"""Tests for deterministic experiment bootstrap packets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import scripts.orchestration.experiment_bootstrap as experiment_bootstrap
from scripts.orchestration.experiment_contract import (
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
            "policy_version": "2026-03-08",
            "selection_mode": "deterministic-weighted",
            "recommended": [{"skill": "pulseplate-workflow", "score": 100}],
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

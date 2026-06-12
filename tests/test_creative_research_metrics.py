"""Tests for local-only creative research adoption metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.orchestration.context_pack as context_pack
import scripts.orchestration.creative_research_metrics as metrics


def _configure_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path]:
    repo = tmp_path / "repo"
    artifact_root = repo / "artifacts" / "orchestration"
    evals_dir = artifact_root / "creative_research" / "evals"
    promotions_dir = artifact_root / "experiments" / "promotions"
    metrics_dir = artifact_root / "creative_research" / "metrics"
    evals_dir.mkdir(parents=True)
    promotions_dir.mkdir(parents=True)
    metrics_dir.mkdir(parents=True)

    monkeypatch.setattr(context_pack, "REPO_ROOT", repo)
    monkeypatch.setattr(metrics, "REPO_ROOT", repo)
    monkeypatch.setattr(metrics, "ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(metrics, "EVALS_DIR", evals_dir)
    monkeypatch.setattr(metrics, "PROMOTIONS_DIR", promotions_dir)
    monkeypatch.setattr(metrics, "METRICS_DIR", metrics_dir)
    monkeypatch.setattr(metrics, "DEFAULT_OUTPUT_JSON", metrics_dir / "latest.json")
    monkeypatch.setattr(metrics, "DEFAULT_OUTPUT_MD", metrics_dir / "latest.md")
    return {
        "repo": repo,
        "artifact_root": artifact_root,
        "evals_dir": evals_dir,
        "promotions_dir": promotions_dir,
        "metrics_dir": metrics_dir,
    }


def _candidate(
    candidate_id: str,
    *,
    decision: str = "promote",
    output_class: str = "mechanistic_hypothesis",
    negative_controls: list[str] | None = None,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "claim": "RAW CLAIM THAT MUST NOT LEAK",
        "mechanism": "RAW MECHANISM THAT MUST NOT LEAK",
        "evidence_needed": "RAW EVIDENCE THAT MUST NOT LEAK",
        "falsifier": "RAW FALSIFIER THAT MUST NOT LEAK",
        "confidence": "medium",
        "known_risks": ["RAW RISK THAT MUST NOT LEAK"],
        "wellness_boundary": "wellness only",
        "alternative_explanations": [],
        "counterevidence": [],
        "stopping_rule": "stop",
        "decision_rule": "decide",
        "minimum_observation": "observe",
        "output_class": output_class,
        "reference_overlap": 0.2,
        "peer_overlap": 0.1,
        "negative_controls_triggered": negative_controls or [],
        "scorecard": {
            "originality": 4,
            "flexibility": 4,
            "mechanism_specificity": 4,
            "groundedness": 4,
            "falsifiability": 4,
            "wellness_safety": 5,
            "hallucination_risk": 1,
        },
        "promotion_decision": decision,
        "presentation_label": None,
    }


def _eval_result(
    bundle_id: str,
    candidates: list[dict[str, object]],
    *,
    phase: str = "divergence",
    summary_override: dict[str, int] | None = None,
) -> dict[str, object]:
    counts = {"promote": 0, "defer": 0, "discard": 0}
    for candidate in candidates:
        counts[str(candidate["promotion_decision"])] += 1
    summary = {
        "candidate_count": len(candidates),
        "promote": counts["promote"],
        "defer": counts["defer"],
        "discard": counts["discard"],
    }
    if summary_override is not None:
        summary = summary_override
    return {
        "schema_version": "1.0",
        "bundle_id": bundle_id,
        "task_class": "creative_research",
        "phase": phase,
        "prompt_seed": "RAW PROMPT SEED THAT MUST NOT LEAK",
        "reference_corpus_size": 1,
        "summary": summary,
        "candidates": candidates,
    }


def _promotion(
    *,
    bundle_id: str | None = None,
    candidate_id: str | None = None,
    decision: str = "promote",
    target: str = "pr_packet",
    durable_artifact_path: str | None = None,
) -> dict[str, object]:
    if durable_artifact_path is None:
        durable_artifact_path = {
            "pr_packet": "docs/orchestration/experiment_pr_packets/exp-promote.md",
            "audit_artifact": "docs/audit/EXPERIMENT_EXP_PROMOTE.md",
            "guard_test_proposal": ("docs/orchestration/experiment_guard_proposals/exp-promote.md"),
            "backlog_entry": "docs/roadmap/BACKLOG_LEDGER.md",
            "memory_capsule": "docs/memory/exp-promote_capsule.md",
        }.get(target, "docs/orchestration/experiment_pr_packets/exp-promote.md")
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "experiment_id": "exp-promote",
        "result_status": "accepted",
        "failure_class": None,
        "promotion_target": target,
        "disposition": "promoted",
        "durable_artifact_path": durable_artifact_path,
        "shared_tree_untouched": True,
        "domain": "orchestration",
        "evidence": {"oracle_commands": [], "mutated_paths": [], "oracle_count": 0},
    }
    if bundle_id is not None and candidate_id is not None:
        payload["creative_research_origin"] = {
            "bundle_id": bundle_id,
            "candidate_id": candidate_id,
            "promotion_decision": decision,
        }
    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def test_empty_dirs_report_zero_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    assert report["schema_version"] == "creative-research-metrics-v1"
    assert report["status"] == "empty"
    assert report["candidate_totals"]["bundle_count"] == 0
    assert report["candidate_totals"]["candidate_count"] == 0
    assert report["conversion"]["missing_conversion_link_count"] == 0


def test_eval_aggregation_recomputes_counts_and_negative_controls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(
        paths["evals_dir"] / "bundle-a.json",
        _eval_result(
            "bundle-a",
            [
                _candidate(
                    "candidate-promote",
                    negative_controls=["shallow_corpus_overlap", "shallow_corpus_overlap"],
                ),
                _candidate(
                    "candidate-defer",
                    decision="defer",
                    output_class="experimental_proposal",
                    negative_controls=["missing_scientific_research_fields"],
                ),
                _candidate(
                    "candidate-discard",
                    decision="discard",
                    output_class="creative_ideation",
                ),
            ],
        ),
    )

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    assert report["candidate_totals"]["bundle_count"] == 1
    assert report["candidate_totals"]["candidate_count"] == 3
    assert report["candidate_totals"]["by_decision"] == {
        "promote": 1,
        "defer": 1,
        "discard": 1,
    }
    assert report["negative_controls"]["candidate_count"] == 2
    assert report["negative_controls"]["counts"] == {
        "missing_scientific_research_fields": 1,
        "shallow_corpus_overlap": 1,
    }


def test_conversion_links_and_missing_promoted_candidates_are_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(
        paths["evals_dir"] / "bundle-a.json",
        _eval_result(
            "bundle-a",
            [
                _candidate("candidate-linked"),
                _candidate("candidate-missing"),
                _candidate("candidate-discard", decision="discard"),
            ],
        ),
    )
    _write_json(
        paths["promotions_dir"] / "linked.json",
        _promotion(bundle_id="bundle-a", candidate_id="candidate-linked"),
    )
    _write_json(paths["promotions_dir"] / "plain.json", _promotion(target="audit_artifact"))

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    assert report["conversion"]["promoted_candidate_count"] == 2
    assert report["conversion"]["linked_promotion_count"] == 1
    assert report["conversion"]["linked_candidate_count"] == 1
    assert report["conversion"]["missing_conversion_links"] == [
        {"bundle_id": "bundle-a", "candidate_id": "candidate-missing"}
    ]
    assert report["conversion"]["destination_counts"] == {
        "audit_artifact": 1,
        "pr_packet": 1,
    }
    assert report["conversion"]["origin_destination_counts"] == {"pr_packet": 1}
    assert report["conversion"]["destination_ref_counts"] == {
        "audit_artifact:docs/audit/EXPERIMENT_EXP_PROMOTE.md": 1,
        "pr_packet:docs/orchestration/experiment_pr_packets/exp-promote.md": 1,
    }
    assert report["conversion"]["origin_destination_ref_counts"] == {
        "pr_packet:docs/orchestration/experiment_pr_packets/exp-promote.md": 1
    }


def test_duplicate_origin_links_and_mismatches_are_accounted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(
        paths["evals_dir"] / "bundle-a.json",
        _eval_result(
            "bundle-a",
            [
                _candidate("candidate-linked"),
                _candidate("candidate-missing"),
                _candidate("candidate-defer", decision="defer"),
            ],
        ),
    )
    _write_json(
        paths["promotions_dir"] / "linked-a.json",
        _promotion(bundle_id="bundle-a", candidate_id="candidate-linked"),
    )
    _write_json(
        paths["promotions_dir"] / "linked-b.json",
        _promotion(bundle_id="bundle-a", candidate_id="candidate-linked"),
    )
    _write_json(
        paths["promotions_dir"] / "mismatch-missing.json",
        _promotion(bundle_id="bundle-a", candidate_id="candidate-unknown"),
    )
    _write_json(
        paths["promotions_dir"] / "mismatch-decision.json",
        _promotion(bundle_id="bundle-a", candidate_id="candidate-defer", decision="promote"),
    )

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    assert report["conversion"]["linked_promotion_count"] == 2
    assert report["conversion"]["linked_candidate_count"] == 1
    assert report["conversion"]["duplicate_origin_link_count"] == 1
    assert report["conversion"]["origin_mismatch_count"] == 2
    assert report["conversion"]["missing_conversion_links"] == [
        {"bundle_id": "bundle-a", "candidate_id": "candidate-missing"}
    ]


def test_malformed_duplicates_and_summary_mismatch_are_accounted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(
        paths["evals_dir"] / "00-good.json",
        _eval_result(
            "bundle-a",
            [_candidate("candidate-a")],
            summary_override={"candidate_count": 9, "promote": 9, "defer": 0, "discard": 0},
        ),
    )
    _write_json(
        paths["evals_dir"] / "duplicate-bundle.json",
        _eval_result("bundle-a", [_candidate("candidate-b")]),
    )
    _write_json(
        paths["evals_dir"] / "duplicate-candidate.json",
        _eval_result("bundle-b", [_candidate("dup"), _candidate("dup")]),
    )
    (paths["evals_dir"] / "bad.json").write_text("{not-json", encoding="utf-8")
    (paths["evals_dir"] / "array.json").write_text("[]\n", encoding="utf-8")

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    reasons = [item["reason"] for item in report["sources"]["skipped_artifacts"]]
    assert report["sources"]["summary_mismatch_count"] == 1
    assert "duplicate_bundle_id" in reasons
    assert "duplicate candidate_id in eval artifact." in reasons
    assert "malformed_json" in reasons
    assert "non_object_json" in reasons


def test_invalid_eval_phase_empty_candidates_and_promotion_refs_are_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(
        paths["evals_dir"] / "invalid-phase.json",
        _eval_result("bundle-phase", [_candidate("candidate-a")], phase="runtime"),
    )
    _write_json(paths["evals_dir"] / "empty.json", _eval_result("bundle-empty", []))
    _write_json(
        paths["promotions_dir"] / "invalid-target.json",
        _promotion(target="runtime_cache"),
    )
    _write_json(
        paths["promotions_dir"] / "invalid-ref.json",
        _promotion(durable_artifact_path="/tmp/raw-secret-path.md"),
    )

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    reasons = {item["reason"] for item in report["sources"]["skipped_artifacts"]}
    assert "phase is not recognized." in reasons
    assert "candidates must not be empty." in reasons
    assert "promotion_target is not recognized." in reasons
    assert "durable_artifact_path must be repo-relative." in reasons
    assert report["sources"]["eval_artifacts_loaded"] == 0
    assert report["sources"]["promotion_artifacts_loaded"] == 0


def test_report_outputs_do_not_leak_raw_text_or_absolute_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(paths["evals_dir"] / "bundle-a.json", _eval_result("bundle-a", [_candidate("c1")]))

    exit_code = metrics.main(
        [
            "--output-json",
            "artifacts/orchestration/creative_research/metrics/latest.json",
            "--output-md",
            "artifacts/orchestration/creative_research/metrics/latest.md",
        ]
    )

    assert exit_code == 0
    json_text = (paths["metrics_dir"] / "latest.json").read_text(encoding="utf-8")
    markdown_text = (paths["metrics_dir"] / "latest.md").read_text(encoding="utf-8")
    combined = json_text + markdown_text
    assert "RAW PROMPT SEED THAT MUST NOT LEAK" not in combined
    assert "RAW CLAIM THAT MUST NOT LEAK" not in combined
    assert "RAW MECHANISM THAT MUST NOT LEAK" not in combined
    assert "RAW EVIDENCE THAT MUST NOT LEAK" not in combined
    assert "RAW FALSIFIER THAT MUST NOT LEAK" not in combined
    assert "RAW RISK THAT MUST NOT LEAK" not in combined
    assert str(tmp_path) not in combined
    assert "bundle-a" in combined
    assert "c1" in combined


def test_metrics_outputs_are_byte_stable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(
        paths["evals_dir"] / "b.json",
        _eval_result("bundle-b", [_candidate("candidate-b", decision="discard")]),
    )
    _write_json(
        paths["evals_dir"] / "a.json",
        _eval_result("bundle-a", [_candidate("candidate-a")]),
    )
    first_json = paths["metrics_dir"] / "first.json"
    first_md = paths["metrics_dir"] / "first.md"
    second_json = paths["metrics_dir"] / "second.json"
    second_md = paths["metrics_dir"] / "second.md"

    first_exit = metrics.main(["--output-json", str(first_json), "--output-md", str(first_md)])
    second_exit = metrics.main(["--output-json", str(second_json), "--output-md", str(second_md)])

    assert first_exit == 0
    assert second_exit == 0
    assert first_json.read_bytes() == second_json.read_bytes()
    assert first_md.read_bytes() == second_md.read_bytes()


def test_output_escape_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_repo(monkeypatch, tmp_path)

    exit_code = metrics.main(["--output-json", "../escape.json"])

    assert exit_code == 1
    assert "--output-json must stay within artifacts/orchestration/creative_research/metrics" in (
        capsys.readouterr().err
    )


def test_symlinked_eval_artifact_is_skipped_without_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_payload = outside / "payload.json"
    _write_json(outside_payload, _eval_result("bundle-outside", [_candidate("candidate-a")]))
    (paths["evals_dir"] / "escape.json").symlink_to(outside_payload)

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    assert report["status"] == "no_valid_eval_artifacts"
    assert report["sources"]["skipped_artifacts"] == [
        {"category": "eval", "file": "escape.json", "reason": "symlink_path"}
    ]


def test_invalid_origin_artifact_is_skipped_and_counted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _configure_repo(monkeypatch, tmp_path)
    _write_json(paths["evals_dir"] / "bundle-a.json", _eval_result("bundle-a", [_candidate("c1")]))
    invalid = _promotion(bundle_id="bundle-a", candidate_id="c1")
    invalid["creative_research_origin"] = {
        "bundle_id": "bundle-a",
        "candidate_id": "c1",
        "promotion_decision": "promote",
        "raw_prompt": "RAW PROMPT THAT MUST NOT LEAK",
    }
    _write_json(paths["promotions_dir"] / "invalid.json", invalid)

    report = metrics.build_metrics_report(paths["evals_dir"], paths["promotions_dir"])

    assert report["sources"]["promotion_artifacts_skipped"] == 1
    assert report["sources"]["skipped_artifacts"] == [
        {
            "category": "promotion",
            "file": "invalid.json",
            "reason": "creative_research_origin has unsupported fields.",
        }
    ]
    rendered = json.dumps(report, ensure_ascii=True, sort_keys=True)
    assert "RAW PROMPT THAT MUST NOT LEAK" not in rendered

from __future__ import annotations

import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/design/design_scorecard.py"
WEB_SAMPLE = REPO_ROOT / "docs/design/screen_evidence/examples/web_marketing.sample.json"
IOS_SAMPLE = REPO_ROOT / "docs/design/screen_evidence/examples/ios_home.sample.json"


def load_scorecard_module() -> SimpleNamespace:
    script_dir = str(MODULE_PATH.parent)
    sys.path.insert(0, script_dir)
    try:
        return SimpleNamespace(**runpy.run_path(str(MODULE_PATH)))
    finally:
        sys.path.remove(script_dir)


def make_temp_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    design_dir = repo_root / "docs/design"
    design_dir.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "docs/design/ui_component_vocabulary.json",
        design_dir / "ui_component_vocabulary.json",
    )
    return repo_root


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def valid_web_manifest(**overrides):
    manifest = read_json(WEB_SAMPLE)
    manifest.update(overrides)
    return manifest


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MODULE_PATH), *args],
        check=False,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_valid_web_screen_evidence_scores_deterministically():
    module = load_scorecard_module()

    first = module.score_path(WEB_SAMPLE, repo_root=REPO_ROOT)
    second = module.score_path(WEB_SAMPLE, repo_root=REPO_ROOT)

    assert first == second
    assert first["scorecard_id"] == "design-scorecard::web-marketing-sample"
    assert first["status"] == "pass"
    assert first["recommendation"] == "usable_for_pr5_pr6_brief"


def test_valid_ios_screen_evidence_scores_deterministically():
    module = load_scorecard_module()

    scorecard = module.score_path(IOS_SAMPLE, repo_root=REPO_ROOT)

    assert scorecard["scorecard_id"] == "design-scorecard::ios-home-sample"
    assert scorecard["platform"] == "ios"
    assert scorecard["status"] == "pass"


def test_invalid_evidence_manifest_fails_before_scoring(tmp_path: Path):
    manifest_path = tmp_path / "invalid.json"
    manifest = valid_web_manifest(component_ids=["invented_component"])
    write_json(manifest_path, manifest)

    result = run_cli("score", str(manifest_path))

    assert result.returncode == 1
    assert "cannot score invalid screen evidence" in result.stderr
    assert "unknown PulsePlate component id: invented_component" in result.stderr
    assert result.stdout == ""


def test_source_of_truth_violation_fails_before_scoring(tmp_path: Path):
    manifest_path = tmp_path / "sot.json"
    manifest = valid_web_manifest(
        source_of_truth_note="Screen evidence is the source of truth for runtime UI."
    )
    write_json(manifest_path, manifest)

    result = run_cli("score", str(manifest_path))

    assert result.returncode == 1
    assert "screen evidence must not become a source of truth" in result.stderr


def test_unknown_component_ids_fail_before_scoring(tmp_path: Path):
    manifest_path = tmp_path / "unknown-component.json"
    write_json(manifest_path, valid_web_manifest(component_ids=["button", "unknown"]))

    result = run_cli("score", str(manifest_path))

    assert result.returncode == 1
    assert "unknown PulsePlate component id: unknown" in result.stderr


def test_unsafe_artifact_paths_fail_before_scoring(tmp_path: Path):
    manifest_path = tmp_path / "unsafe-path.json"
    write_json(
        manifest_path,
        valid_web_manifest(
            artifact_policy="local_only",
            screenshot_artifact_path=(
                "artifacts/design/screen_evidence/run/DerivedData/evidence.txt"
            ),
        ),
    )

    result = run_cli("score", str(manifest_path))

    assert result.returncode == 1
    assert "disallowed local artifact path segment" in result.stderr


def test_copy_safety_violation_fails_before_scoring(tmp_path: Path):
    manifest_path = tmp_path / "copy-safety.json"
    write_json(
        manifest_path,
        valid_web_manifest(
            copy_safety_evidence={"claim": "This screen guarantees treatment outcomes."}
        ),
    )

    result = run_cli("score", str(manifest_path))

    assert result.returncode == 1
    assert "copy_safety_evidence must not promote" in result.stderr


def test_rejected_evidence_status_becomes_blocking_failure(tmp_path: Path):
    module = load_scorecard_module()
    repo_root = make_temp_repo(tmp_path)
    manifest_path = repo_root / "evidence.json"
    write_json(manifest_path, valid_web_manifest(status="rejected"))

    scorecard = module.score_path(manifest_path, repo_root=repo_root)

    assert scorecard["status"] == "fail"
    assert scorecard["recommendation"] == "rejected"
    assert scorecard["blocking_failures"] == ["evidence status is rejected"]


def test_missing_accessibility_evidence_lowers_score_without_wcag_claim(tmp_path: Path):
    module = load_scorecard_module()
    repo_root = make_temp_repo(tmp_path)
    manifest_path = repo_root / "evidence.json"
    write_json(manifest_path, valid_web_manifest(accessibility_evidence={}))

    scorecard = module.score_path(manifest_path, repo_root=repo_root)
    accessibility = next(
        item for item in scorecard["dimensions"] if item["id"] == "accessibility_evidence"
    )

    assert accessibility["status"] == "warn"
    assert accessibility["score"] == 0
    assert "Accessibility evidence metadata is missing." in scorecard["warnings"]
    assert "wcag_pass" not in json.dumps(scorecard)


def test_missing_responsive_overflow_and_motion_evidence_lowers_score(tmp_path: Path):
    module = load_scorecard_module()
    repo_root = make_temp_repo(tmp_path)
    manifest_path = repo_root / "evidence.json"
    write_json(
        manifest_path,
        valid_web_manifest(
            motion_evidence={},
            overflow_evidence={},
            responsive_evidence={},
        ),
    )

    scorecard = module.score_path(manifest_path, repo_root=repo_root)
    dimensions = {item["id"]: item for item in scorecard["dimensions"]}

    assert dimensions["responsive_evidence"]["score"] == 0
    assert dimensions["overflow_evidence"]["score"] == 0
    assert dimensions["motion_evidence"]["score"] == 0
    assert scorecard["status"] == "warn"


def test_score_dir_scores_all_sample_evidence_manifests():
    module = load_scorecard_module()

    result = module.score_dir("docs/design/screen_evidence/examples", repo_root=REPO_ROOT)

    assert [item["path"] for item in result["scorecards"]] == [
        "docs/design/screen_evidence/examples/ios_home.sample.json",
        "docs/design/screen_evidence/examples/web_marketing.sample.json",
    ]


def test_validate_score_validates_generated_scorecard():
    module = load_scorecard_module()
    scorecard = module.score_path(WEB_SAMPLE, repo_root=REPO_ROOT)

    assert module.validate_scorecard_record(scorecard) == []


def test_validate_score_rejects_subjective_fields():
    module = load_scorecard_module()
    scorecard = module.score_path(WEB_SAMPLE, repo_root=REPO_ROOT)
    scorecard["premium_score"] = 10

    errors = module.validate_scorecard_record(scorecard)

    assert "subjective scorecard field is forbidden: premium_score" in errors


def test_validate_score_requires_canonical_dimension_order():
    module = load_scorecard_module()
    scorecard = module.score_path(WEB_SAMPLE, repo_root=REPO_ROOT)
    scorecard["dimensions"] = list(reversed(scorecard["dimensions"]))

    errors = module.validate_scorecard_record(scorecard)

    assert "dimensions must use the canonical deterministic dimension order" in errors


def test_summarize_output_is_deterministic(tmp_path: Path):
    module = load_scorecard_module()
    scorecard_path = tmp_path / "scorecard.json"
    write_json(scorecard_path, module.score_path(WEB_SAMPLE, repo_root=REPO_ROOT))

    first = module.summarize_path(scorecard_path, repo_root=REPO_ROOT)
    second = module.summarize_path(scorecard_path, repo_root=REPO_ROOT)

    assert first == second
    assert first["scorecard_id"] == "design-scorecard::web-marketing-sample"


def test_cli_validate_score_validates_sample_scorecard_fixture():
    result = run_cli(
        "validate-score",
        "docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json",
    )

    assert result.returncode == 0
    assert "OK:" in result.stdout


def test_no_subjective_visual_scoring_terms_in_generated_output():
    module = load_scorecard_module()
    scorecard = module.score_path(WEB_SAMPLE, repo_root=REPO_ROOT)
    payload = json.dumps(scorecard, sort_keys=True)

    for forbidden in ["beautiful", "premium_score", "luxury_score", "taste_score"]:
        assert forbidden not in payload


def test_cli_does_not_require_network_access():
    result = run_cli("score", str(WEB_SAMPLE))

    assert result.returncode == 0
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout

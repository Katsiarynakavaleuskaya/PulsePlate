from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/design/screen_evidence_pack.py"


def load_evidence_module() -> SimpleNamespace:
    return SimpleNamespace(**runpy.run_path(str(MODULE_PATH)))


def make_temp_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    design_dir = repo_root / "docs/design"
    design_dir.mkdir(parents=True)
    shutil.copyfile(
        REPO_ROOT / "docs/design/ui_component_vocabulary.json",
        design_dir / "ui_component_vocabulary.json",
    )
    return repo_root


def valid_manifest(**overrides):
    manifest = {
        "a11y_artifact_path": "",
        "accessibility_evidence": {"focus": "Visible focus evidence captured."},
        "artifact_policy": "committed_sample_metadata",
        "capture_mode": "sample",
        "component_ids": ["button", "card"],
        "copy_safety_evidence": {
            "wellness_boundary": "Review evidence only; avoid diagnosis, treatment, therapy, crisis, medical, and guaranteed outcome claims."
        },
        "dom_artifact_path": "",
        "evidence_id": "web-marketing-sample",
        "generated_at_policy": "omitted",
        "generated_by": "test fixture",
        "ios_simulator_artifact_path": "",
        "locale": "en-US",
        "motion_evidence": {"reduced_motion": "Reduced-motion behavior reviewed."},
        "overflow_evidence": {"horizontal": "No horizontal overflow evidence captured."},
        "platform": "web",
        "responsive_evidence": {"desktop": "Desktop viewport evidence captured."},
        "route_or_screen": "/marketing",
        "screenshot_artifact_path": "",
        "source_of_truth_note": "Screen evidence is review evidence only, non-canonical, and not source of truth; repo tokens, UI vocabulary, backend/OpenAPI contracts, tests, and runtime code win.",
        "status": "sample",
        "storybook_artifact_path": "",
        "surface_id": "web:/marketing",
        "surface_name": "Marketing launch shell",
        "tabbar_or_navigation_evidence": {"navigation": "Navigation evidence captured."},
        "theme": "repo-default",
        "token_mirror_paths_checked": [
            "frontend/src/styles/tokens.css",
            "frontend/src/styles/tokens.ts",
        ],
        "viewport": "desktop-1440x1100",
        "warnings": ["sample metadata only"],
    }
    manifest.update(overrides)
    return manifest


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_valid_web_sample_manifest_passes():
    module = load_evidence_module()

    assert module.validate_record(valid_manifest(), repo_root=REPO_ROOT) == []


def test_valid_ios_sample_manifest_passes():
    module = load_evidence_module()
    manifest = valid_manifest(
        artifact_policy="committed_sample_metadata",
        component_ids=["button", "card", "navigation_tab_bar"],
        platform="ios",
        route_or_screen="Home",
        surface_id="ios:home",
        token_mirror_paths_checked=[
            "ios/PulsePlate/DesignSystem/DesignTokens.generated.swift",
        ],
        viewport="iPhone-template",
    )

    assert module.validate_record(manifest, repo_root=REPO_ROOT) == []


def test_missing_required_field_fails():
    module = load_evidence_module()
    manifest = valid_manifest()
    del manifest["surface_id"]

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "missing required field: surface_id" in errors


def test_invalid_enum_values_fail():
    module = load_evidence_module()
    manifest = valid_manifest(platform="android", status="approved")

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "platform must be one of: ios, web" in errors
    assert "status must be one of: captured, rejected, sample, validated" in errors


def test_source_of_truth_wording_fails():
    module = load_evidence_module()
    manifest = valid_manifest(
        source_of_truth_note="Screen evidence is the source of truth for runtime UI."
    )

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "source_of_truth_note must state this is review evidence" in errors
    assert "screen evidence must not become a source of truth" in errors


def test_source_of_truth_but_overrides_wording_fails():
    module = load_evidence_module()
    manifest = valid_manifest(
        source_of_truth_note=(
            "Screen evidence is review evidence only and not source of truth, "
            "but overrides repo runtime UI."
        )
    )

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "screen evidence must not become a source of truth" in errors


def test_negated_source_of_truth_wording_passes():
    module = load_evidence_module()
    manifest = valid_manifest(
        source_of_truth_note=(
            "Screen evidence is review evidence only and is not source of truth; "
            "repo runtime code wins."
        )
    )

    assert module.validate_record(manifest, repo_root=REPO_ROOT) == []


def test_unknown_component_ids_fail():
    module = load_evidence_module()
    manifest = valid_manifest(component_ids=["button", "invented_component"])

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "unknown PulsePlate component id: invented_component" in errors


def test_malformed_component_ids_return_validation_errors():
    module = load_evidence_module()
    manifest = valid_manifest(component_ids=["button", {}])

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "component_ids must contain only non-empty strings" in errors


def test_committed_binary_artifact_paths_fail():
    module = load_evidence_module()
    manifest = valid_manifest(
        screenshot_artifact_path="artifacts/design/screen_evidence/run/screen.png"
    )

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "screenshot_artifact_path must be empty for committed_sample_metadata" in errors
    assert "screenshot_artifact_path must not reference committed binary artifacts" in errors


def test_disallowed_paths_fail():
    module = load_evidence_module()
    manifest = valid_manifest(
        artifact_policy="local_only",
        screenshot_artifact_path="artifacts/design/screen_evidence/run/DerivedData/screen.txt",
        dom_artifact_path="artifacts/design/screen_evidence/run/storybook-static/dom.json",
        a11y_artifact_path="artifacts/design/screen_evidence/run/node_modules/a11y.json",
        storybook_artifact_path="artifacts/design/screen_evidence/run/.venv/storybook.json",
        ios_simulator_artifact_path="artifacts/design/screen_evidence/run/worktrees/ios.json",
    )

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert (
        errors.count("screenshot_artifact_path contains a disallowed local artifact path segment")
        == 1
    )
    assert errors.count("dom_artifact_path contains a disallowed local artifact path segment") == 1
    assert errors.count("a11y_artifact_path contains a disallowed local artifact path segment") == 1
    assert (
        errors.count("storybook_artifact_path contains a disallowed local artifact path segment")
        == 1
    )
    assert (
        errors.count(
            "ios_simulator_artifact_path contains a disallowed local artifact path segment"
        )
        == 1
    )


def test_copy_safety_medical_claim_fails():
    module = load_evidence_module()
    manifest = valid_manifest(
        copy_safety_evidence={"claim": "This screen supports treatment and guaranteed outcomes."}
    )

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert any("copy_safety_evidence must not promote" in error for error in errors)


def test_validated_status_requires_non_empty_evidence():
    module = load_evidence_module()
    manifest = valid_manifest(
        accessibility_evidence={},
        status="validated",
        token_mirror_paths_checked=[],
    )

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "status=validated requires non-empty accessibility_evidence" in errors
    assert "status=validated requires token_mirror_paths_checked" in errors


def test_validated_status_rejects_placeholder_scalar_evidence():
    module = load_evidence_module()
    manifest = valid_manifest(
        accessibility_evidence={"placeholder": None},
        copy_safety_evidence={"placeholder": False},
        motion_evidence={"placeholder": 0},
        overflow_evidence={"nested": {"placeholder": None}},
        responsive_evidence={"items": [False, 0, None]},
        status="validated",
        tabbar_or_navigation_evidence={"placeholder": 0},
    )

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "status=validated requires non-empty accessibility_evidence" in errors
    assert "status=validated requires non-empty copy_safety_evidence" in errors
    assert "status=validated requires non-empty motion_evidence" in errors
    assert "status=validated requires non-empty overflow_evidence" in errors
    assert "status=validated requires non-empty responsive_evidence" in errors
    assert "status=validated requires non-empty tabbar_or_navigation_evidence" in errors


def test_ios_automated_capture_requires_ios_artifact_path():
    module = load_evidence_module()
    manifest = valid_manifest(platform="ios", capture_mode="automated", route_or_screen="Home")

    errors = module.validate_record(manifest, repo_root=REPO_ROOT)

    assert "platform=ios automated capture requires ios_simulator_artifact_path" in errors


def test_validate_dir_validates_examples():
    module = load_evidence_module()

    results = module.validate_dir("docs/design/screen_evidence/examples", repo_root=REPO_ROOT)

    assert results
    assert all(errors == [] for errors in results.values())


def test_summarize_output_is_deterministic(tmp_path, capsys):
    module = load_evidence_module()
    repo_root = make_temp_repo(tmp_path)
    manifest_path = repo_root / "manifest.json"
    write_manifest(manifest_path, valid_manifest(warnings=["z warning", "a warning"]))

    first = module.run(["summarize", str(manifest_path)], repo_root=repo_root)
    first_output = capsys.readouterr().out
    second = module.run(["summarize", str(manifest_path)], repo_root=repo_root)
    second_output = capsys.readouterr().out

    assert first == 0
    assert second == 0
    assert first_output == second_output
    assert json.loads(first_output)["warnings"] == ["a warning", "z warning"]


def test_web_plan_output_is_deterministic(tmp_path):
    module = load_evidence_module()
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first = module.web_plan(["/", "/marketing"], first_dir)
    second = module.web_plan(["/", "/marketing"], second_dir)

    first_manifests = sorted(path.read_text(encoding="utf-8") for path in first_dir.glob("*.json"))
    second_manifests = sorted(
        path.read_text(encoding="utf-8") for path in second_dir.glob("*.json")
    )

    assert first["routes"] == second["routes"] == ["/", "/marketing"]
    assert len(first_manifests) == len(second_manifests) == 2
    assert [json.loads(text)["evidence_id"] for text in first_manifests] == [
        json.loads(text)["evidence_id"] for text in second_manifests
    ]


def test_web_plan_requires_no_network(monkeypatch, tmp_path):
    module = load_evidence_module()

    def fail_network(*_args, **_kwargs):  # pragma: no cover - defensive sentinel
        raise AssertionError("network access is not allowed")

    monkeypatch.setattr("socket.create_connection", fail_network)

    summary = module.web_plan(["/marketing"], tmp_path / "plan")

    assert summary["routes"] == ["/marketing"]

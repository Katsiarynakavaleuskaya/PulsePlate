from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/design/reference_manifest.py"


def load_manifest_module() -> SimpleNamespace:
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


def valid_record(**overrides):
    record = {
        "reference_id": "synthetic-reference-001",
        "source_name": "Synthetic Reference",
        "source_url": "https://example.invalid/synthetic-reference",
        "license_status": "restricted",
        "attribution_required": False,
        "product_category": "wellness",
        "platform": ["web", "ios"],
        "surface_type": ["dashboard"],
        "visual_archetype": "calm premium planning surface",
        "palette_archetype": "derived dark foundation with restrained accent",
        "typography_archetype": "clear hierarchy with compact labels",
        "spacing_density": "balanced",
        "radius_profile": "medium",
        "component_patterns": ["card", "button"],
        "layout_patterns": ["summary plus detail"],
        "motion_notes": "Subtle motion only; reduced-motion fallback remains required.",
        "accessibility_notes": "Derived notes cover contrast, focus, keyboard, and touch targets.",
        "wellness_safety_notes": "Read-only non-canonical evidence; avoid diagnostic, treatment, crisis, medical, and guaranteed outcome claims.",
        "monetization_notes": "Read-only non-canonical evidence for value framing; pricing truth remains repo-owned.",
        "legal_copy_risks": ["brand-specific wording must be avoided"],
        "adopt_adapt_reject_decision": "adapt",
        "normalization_notes": "Read-only non-canonical evidence mapped into PulsePlate vocabulary.",
        "mapped_pulseplate_components": ["card", "button"],
        "forbidden_copy_elements": [
            "screenshot",
            "external brand",
            "exact layout",
            "marketing copy",
        ],
        "icon-silhouette-check": "not_applicable",
        "design-guard": "required",
        "status": "normalized",
    }
    record.update(overrides)
    return record


def write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_valid_read_only_reference_passes():
    module = load_manifest_module()
    record = valid_record(
        license_status="unknown",
        adopt_adapt_reject_decision="adapt",
        status="read_only",
    )

    assert module.validate_record(record, repo_root=REPO_ROOT) == []


def test_valid_normalized_reference_passes():
    module = load_manifest_module()

    assert module.validate_record(valid_record(), repo_root=REPO_ROOT) == []


def test_valid_candidate_for_brief_requires_resolved_fields():
    module = load_manifest_module()
    record = valid_record(
        license_status="restricted",
        status="candidate_for_brief",
        adopt_adapt_reject_decision="adapt",
    )

    assert module.validate_record(record, repo_root=REPO_ROOT) == []


def test_missing_required_field_fails():
    module = load_manifest_module()
    record = valid_record()
    del record["source_name"]

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "missing required field: source_name" in errors


def test_candidate_for_brief_requires_normalization_notes_and_components():
    module = load_manifest_module()
    record = valid_record(
        status="candidate_for_brief",
        normalization_notes="",
        mapped_pulseplate_components=[],
    )

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "candidate_for_brief requires non-empty normalization_notes" in errors
    assert "candidate_for_brief requires non-empty mapped_pulseplate_components" in errors


def test_rejected_reference_requires_rejected_status():
    module = load_manifest_module()
    record = valid_record(adopt_adapt_reject_decision="reject", status="normalized")

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "adopt_adapt_reject_decision=reject requires status=rejected" in errors


def test_rejected_status_requires_reject_decision():
    module = load_manifest_module()
    record = valid_record(adopt_adapt_reject_decision="adapt", status="rejected")

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "status=rejected requires adopt_adapt_reject_decision=reject" in errors


def test_unknown_license_cannot_be_candidate_for_brief():
    module = load_manifest_module()
    record = valid_record(license_status="unknown", status="candidate_for_brief")

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "license_status=unknown cannot be candidate_for_brief" in errors


def test_unknown_pulseplate_component_mapping_fails():
    module = load_manifest_module()
    record = valid_record(mapped_pulseplate_components=["card", "invented_component"])

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "unknown PulsePlate component mapping: invented_component" in errors


def test_unknown_component_pattern_fails():
    module = load_manifest_module()
    record = valid_record(component_patterns=["card", "invented_component"])

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "unknown PulsePlate component pattern: invented_component" in errors


def test_component_patterns_accept_canonical_vocabulary_aliases():
    module = load_manifest_module()
    record = valid_record(component_patterns=["card", "segmented-control"])

    assert module.validate_record(record, repo_root=REPO_ROOT) == []


def test_missing_forbidden_copy_elements_fails_for_non_rejected_reference():
    module = load_manifest_module()
    record = valid_record(forbidden_copy_elements=[])

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "non-rejected references require forbidden_copy_elements" in errors


def test_direct_copy_risk_fails_closed():
    module = load_manifest_module()
    record = valid_record(
        normalization_notes="Read-only evidence, but copy screenshot layout exactly."
    )

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "direct-copy intent is forbidden" in errors


@pytest.mark.parametrize(
    "normalization_notes",
    [
        "Read-only evidence says the screenshot should be copied into PulsePlate.",
        "Read-only evidence says use the exact screenshot as implementation reference.",
        "Read-only evidence says duplicate the vendor layout and brand style.",
    ],
)
def test_direct_copy_variants_fail_closed(normalization_notes: str):
    module = load_manifest_module()
    record = valid_record(normalization_notes=normalization_notes)

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "direct-copy intent is forbidden" in errors


def test_medical_treatment_claim_wording_fails_when_promoted():
    module = load_manifest_module()
    record = valid_record(
        wellness_safety_notes="This reference supports treatment and guaranteed outcomes."
    )

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert any("wellness_safety_notes must not promote" in error for error in errors)


def test_external_reference_source_of_truth_wording_fails():
    module = load_manifest_module()
    record = valid_record(normalization_notes="This external reference is the source of truth.")

    errors = module.validate_record(record, repo_root=REPO_ROOT)

    assert "external references must not become a source of truth" in errors


def test_malformed_json_reports_deterministic_error(tmp_path, capsys):
    module = load_manifest_module()
    repo_root = make_temp_repo(tmp_path)
    path = repo_root / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    result = module.run(["validate", str(path)], repo_root=repo_root)
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR:" in captured.err
    assert "invalid JSON" in captured.err
    assert "Traceback" not in captured.err


def test_malformed_component_vocabulary_reports_validation_error(tmp_path, capsys):
    module = load_manifest_module()
    repo_root = make_temp_repo(tmp_path)
    vocabulary_path = repo_root / "docs/design/ui_component_vocabulary.json"
    vocabulary_path.write_text("{not json", encoding="utf-8")
    manifest_path = repo_root / "manifest.json"
    write_record(manifest_path, valid_record())

    result = module.run(["validate", str(manifest_path)], repo_root=repo_root)
    captured = capsys.readouterr()

    assert result == 1
    assert "ERROR:" in captured.err
    assert "ui_component_vocabulary.json: invalid JSON" in captured.err
    assert "Traceback" not in captured.err


def test_validate_dir_validates_every_json_file(tmp_path, capsys):
    module = load_manifest_module()
    repo_root = make_temp_repo(tmp_path)
    examples_dir = repo_root / "docs/design/reference_manifest/examples"
    write_record(examples_dir / "one.json", valid_record(reference_id="one"))
    write_record(examples_dir / "two.json", valid_record(reference_id="two", status="read_only"))

    result = module.run(
        ["validate-dir", "docs/design/reference_manifest/examples"],
        repo_root=repo_root,
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "OK: docs/design/reference_manifest/examples manifests are valid." in captured.out


def test_normalize_output_is_deterministic(tmp_path, capsys):
    module = load_manifest_module()
    repo_root = make_temp_repo(tmp_path)
    path = repo_root / "manifest.json"
    write_record(path, valid_record())

    assert module.run(["normalize", str(path)], repo_root=repo_root) == 0
    first = capsys.readouterr().out
    assert module.run(["normalize", str(path)], repo_root=repo_root) == 0
    second = capsys.readouterr().out

    assert first == second
    summary = json.loads(first)
    assert summary["reference_id"] == "synthetic-reference-001"
    assert summary["recommendation"] == "read_only"
    assert summary["mapped_pulseplate_component_ids"] == ["button", "card"]


def test_no_network_access_is_required_for_validation(tmp_path, monkeypatch):
    module = load_manifest_module()
    repo_root = make_temp_repo(tmp_path)
    path = repo_root / "manifest.json"
    write_record(path, valid_record(source_url="https://network.invalid/reference"))

    def fail_network(*_args, **_kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr("socket.create_connection", fail_network)

    assert module.run(["validate", str(path)], repo_root=repo_root) == 0


def test_committed_examples_are_synthetic_and_valid():
    module = load_manifest_module()

    examples_dir = REPO_ROOT / "docs/design/reference_manifest/examples"
    result = module.validate_dir(examples_dir, repo_root=REPO_ROOT)

    assert result == []
    for path in examples_dir.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        serialized = json.dumps(record).lower()
        assert "synthetic" in serialized
        assert "copy screenshot" not in serialized
        assert "exact layout" in record["forbidden_copy_elements"]

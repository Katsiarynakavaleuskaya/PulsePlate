from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.design import design_component_registry as registry_module

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docs/orchestration/contracts/design_component_registry.v1.json"
VOCABULARY_PATH = REPO_ROOT / "docs/design/ui_component_vocabulary.json"


def _load_registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write_registry(tmp_path: Path, registry: dict[str, object]) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return path


def test_design_component_registry_seed_is_valid_and_matches_vocabulary() -> None:
    registry = _load_registry()
    vocabulary = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))

    assert registry_module.validate_registry(REGISTRY_PATH) == []

    component_ids = {component["component_id"] for component in registry["components"]}
    vocabulary_ids = {component["id"] for component in vocabulary}
    assert component_ids == vocabulary_ids


def test_design_component_registry_summarize_is_deterministic() -> None:
    summary = registry_module.summarize_registry(REGISTRY_PATH)

    assert summary == {
        "schema_version": "design_component_registry.v1",
        "component_count": 24,
        "status_counts": {"missing": 8, "partial": 16},
    }


def test_design_component_registry_rejects_missing_required_field(tmp_path: Path) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    del broken["components"][0]["visual_regression_contract"]

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any("missing required fields: visual_regression_contract" in error for error in errors)


def test_design_component_registry_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text("{", encoding="utf-8")

    errors = registry_module.validate_registry(path)

    assert any("invalid JSON" in error for error in errors)


def test_design_component_registry_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text("[]", encoding="utf-8")

    errors = registry_module.validate_registry(path)

    assert any("expected JSON object" in error for error in errors)


def test_design_component_registry_rejects_unknown_component_id(tmp_path: Path) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["components"][0]["component_id"] = "vendor_magic_card"

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any("unknown vocabulary id 'vendor_magic_card'" in error for error in errors)


def test_design_component_registry_rejects_duplicate_component_id(tmp_path: Path) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["components"][1]["component_id"] = broken["components"][0]["component_id"]

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any("duplicate id 'button'" in error for error in errors)


def test_design_component_registry_rejects_duplicate_vocabulary_ids(
    tmp_path: Path,
) -> None:
    vocabulary_dir = tmp_path / "docs/design"
    vocabulary_dir.mkdir(parents=True)
    (vocabulary_dir / "ui_component_vocabulary.json").write_text(
        json.dumps(
            [
                {"id": "button", "canonical_name": "Button"},
                {"id": "button", "canonical_name": "Button duplicate"},
            ]
        ),
        encoding="utf-8",
    )
    registry = {
        "schema_version": "design_component_registry.v1",
        "source_of_truth": "repo",
        "authority": {
            "canonical": ["repo code/docs/tests"],
            "reference_only": [
                "Kimi",
                "Figma",
                "Canva",
                "Penpot",
                "Storybook",
                "Code Connect",
            ],
        },
        "components": [
            {
                "component_id": "button",
                "canonical_name": "Button",
                "repo_vocabulary_anchor": "docs/design/ui_component_vocabulary.json#button",
                "web_runtime_anchor": "unspecified",
                "ios_runtime_anchor": "unspecified",
                "token_dependencies": ["unspecified"],
                "storybook_review_anchor": "unspecified",
                "figma_reference_anchor": "unspecified",
                "penpot_reference_anchor": "unspecified",
                "code_connect_anchor": "unspecified",
                "states": ["unspecified"],
                "variants": ["unspecified"],
                "accessibility_contract": "unspecified",
                "visual_regression_contract": "unspecified",
                "owner": "design-system",
                "status": "unspecified",
            }
        ],
    }

    errors = registry_module.validate_registry(
        _write_registry(tmp_path, registry), repo_root=tmp_path
    )

    assert any("duplicate component id 'button'" in error for error in errors)


def test_design_component_registry_rejects_invalid_status(tmp_path: Path) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["components"][0]["status"] = "ready"

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any("invalid status 'ready'" in error for error in errors)


def test_design_component_registry_rejects_empty_strings(tmp_path: Path) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["components"][0]["ios_runtime_anchor"] = ""

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any("empty string is forbidden; use 'unspecified'" in error for error in errors)


def test_design_component_registry_rejects_external_authority_promotion(
    tmp_path: Path,
) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["authority"]["canonical"].append("Figma source of truth")

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any("external evidence tools must not be canonical: figma" in error for error in errors)


def test_design_component_registry_rejects_kimi_adjacent_authority_promotion(
    tmp_path: Path,
) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["authority"]["canonical"].append("Google Drive prototype folder")
    broken["authority"]["canonical"].append("generated code bundles")

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any("google drive" in error for error in errors)
    assert any("generated code" in error for error in errors)


def test_design_component_registry_rejects_wrong_vocabulary_anchor(
    tmp_path: Path,
) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["components"][0][
        "repo_vocabulary_anchor"
    ] = "docs/design/ui_component_vocabulary.json:input"

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any(
        "repo_vocabulary_anchor: expected 'docs/design/ui_component_vocabulary.json:button'"
        in error
        for error in errors
    )


def test_design_component_registry_rejects_wrong_web_runtime_anchor(
    tmp_path: Path,
) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["components"][0]["web_runtime_anchor"] = "frontend/src/components/ui/DoesNotExist.tsx"

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any(
        "web_runtime_anchor: expected repo-backed anchor "
        "'frontend/src/components/ui/Button.tsx'" in error
        for error in errors
    )


def test_design_component_registry_rejects_invented_unconfirmed_anchors(
    tmp_path: Path,
) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    broken["components"][0]["figma_reference_anchor"] = "figma://invented-node"
    broken["components"][0]["token_dependencies"] = ["--color-invented"]

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any(
        "unconfirmed seed fields must be 'unspecified'" in error
        and "figma_reference_anchor" in error
        and "token_dependencies" in error
        for error in errors
    )


def test_design_component_registry_rejects_covered_status_without_bridge_evidence(
    tmp_path: Path,
) -> None:
    registry = _load_registry()
    broken = copy.deepcopy(registry)
    missing_component = next(
        component for component in broken["components"] if component["component_id"] == "select"
    )
    missing_component["status"] = "covered"

    errors = registry_module.validate_registry(_write_registry(tmp_path, broken))

    assert any(
        "covered requires bridge evidence" in error and "web_runtime_anchor" in error
        for error in errors
    )


def test_design_component_registry_rejects_deleted_web_runtime_anchor(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    vocabulary_dir = repo_root / "docs/design"
    vocabulary_dir.mkdir(parents=True)
    (vocabulary_dir / "ui_component_vocabulary.json").write_text(
        json.dumps(
            [
                {
                    "id": "button",
                    "canonical_name": "Button",
                    "existing_repo_component": "frontend/src/components/ui/Button.tsx",
                }
            ]
        ),
        encoding="utf-8",
    )
    registry = {
        "schema_version": "design_component_registry.v1",
        "source_of_truth": "repo",
        "authority": {
            "canonical": ["repo code/docs/tests"],
            "reference_only": [
                "Kimi",
                "Figma",
                "Canva",
                "Penpot",
                "Storybook",
                "Code Connect",
            ],
        },
        "components": [
            {
                "component_id": "button",
                "canonical_name": "Button",
                "repo_vocabulary_anchor": "docs/design/ui_component_vocabulary.json:button",
                "web_runtime_anchor": "frontend/src/components/ui/Button.tsx",
                "ios_runtime_anchor": "unspecified",
                "token_dependencies": ["unspecified"],
                "storybook_review_anchor": "unspecified",
                "figma_reference_anchor": "unspecified",
                "penpot_reference_anchor": "unspecified",
                "code_connect_anchor": "unspecified",
                "states": ["unspecified"],
                "variants": ["unspecified"],
                "accessibility_contract": "unspecified",
                "visual_regression_contract": "unspecified",
                "owner": "design-system",
                "status": "partial",
            }
        ],
    }

    errors = registry_module.validate_registry(
        _write_registry(tmp_path, registry), repo_root=repo_root
    )

    assert any("repo-backed anchor does not exist" in error for error in errors)


def test_design_component_registry_cli_validate_and_summarize(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert registry_module.main(["validate", str(REGISTRY_PATH)]) == 0
    assert "PASS: design component registry valid" in capsys.readouterr().out

    assert registry_module.main(["summarize", str(REGISTRY_PATH)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["component_count"] == 24

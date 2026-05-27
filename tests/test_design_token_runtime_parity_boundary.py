from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from scripts.design import design_token_runtime_parity_boundary as boundary_module

REPO_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = (
    REPO_ROOT / "docs/orchestration/contracts/design_token_runtime_parity_boundary.v1.json"
)
REGISTRY_PATH = REPO_ROOT / "docs/orchestration/contracts/design_component_registry.v1.json"
BRIDGE_PATH = REPO_ROOT / "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json"
VISUAL_PATH = REPO_ROOT / "docs/orchestration/contracts/design_visual_regression_decisions.v1.json"
ACCESSIBILITY_PATH = (
    REPO_ROOT / "docs/orchestration/contracts/design_accessibility_regression_decisions.v1.json"
)
BoundaryMutator = Callable[[dict[str, Any]], object]


def _load_boundary() -> dict[str, Any]:
    return json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))


def _write_boundary(tmp_path: Path, boundary: object) -> Path:
    path = tmp_path / "boundary.json"
    path.write_text(json.dumps(boundary), encoding="utf-8")
    return path


def _write_repo_inputs(
    tmp_path: Path,
    boundary: dict[str, Any],
    *,
    visual: dict[str, Any] | None = None,
    accessibility: dict[str, Any] | None = None,
) -> Path:
    boundary_path = tmp_path / "boundary.json"
    boundary_path.write_text(json.dumps(boundary), encoding="utf-8")
    for source in (REGISTRY_PATH, BRIDGE_PATH, VISUAL_PATH, ACCESSIBILITY_PATH):
        target = tmp_path / source.relative_to(REPO_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source == VISUAL_PATH and visual is not None:
            target.write_text(json.dumps(visual), encoding="utf-8")
        elif source == ACCESSIBILITY_PATH and accessibility is not None:
            target.write_text(json.dumps(accessibility), encoding="utf-8")
        else:
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    for record in boundary.get("records", []):
        if not isinstance(record, dict):
            continue
        for anchor in record.get("evidence_anchors", []):
            if not isinstance(anchor, str):
                continue
            if not anchor.startswith(
                ("docs/", "scripts/", "tests/", "frontend/", "ios/", "tokens/")
            ):
                continue
            file_path = tmp_path / anchor.split(":", 1)[0]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch(exist_ok=True)
    return boundary_path


def _errors(tmp_path: Path, boundary: object) -> list[str]:
    return boundary_module.validate_boundary(_write_boundary(tmp_path, boundary))


def test_current_boundary_validates_and_covers_registry_once() -> None:
    boundary = _load_boundary()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE_PATH.read_text(encoding="utf-8"))

    assert boundary_module.validate_boundary(BOUNDARY_PATH) == []
    assert [record["component_id"] for record in boundary["records"]] == [
        record["component_id"] for record in registry["components"]
    ]
    assert [record["component_id"] for record in boundary["records"]] == [
        record["component_id"] for record in bridge["records"]
    ]
    assert len({record["component_id"] for record in boundary["records"]}) == 24


def test_summarize_output_is_deterministic() -> None:
    assert boundary_module.summarize_boundary(BOUNDARY_PATH) == {
        "schema_version": "design_token_runtime_parity_boundary.v1",
        "record_count": 24,
        "status_counts": {
            "generated_mirror_status": {"blocked": 24},
            "implementation_readiness": {"blocked": 24},
            "ios_runtime_status": {"blocked": 24},
            "token_authoring_status": {"blocked": 24},
            "web_runtime_status": {"blocked": 24},
        },
        "blocked_for_implementation": 24,
        "next_required_gate_counts": {"first bounded frontend MVP product slice": 24},
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("{", "invalid JSON"),
        ([], "expected JSON object"),
    ],
)
def test_boundary_rejects_malformed_or_non_object_json(
    tmp_path: Path, payload: object, expected: str
) -> None:
    path = tmp_path / "boundary.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")

    assert any(expected in error for error in boundary_module.validate_boundary(path))


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda d: d.pop("records"), "missing required fields: records"),
        (lambda d: d.update({"extra": True}), "unexpected fields: extra"),
        (lambda d: d.update({"schema_version": "wrong"}), "schema_version"),
        (lambda d: d.update({"source_of_truth": "figma"}), "source_of_truth"),
        (lambda d: d.update({"records": []}), "records: expected non-empty list"),
        (
            lambda d: d.update({"next_required_gate": "another design governance layer"}),
            "next_required_gate",
        ),
    ],
)
def test_boundary_rejects_top_level_contract_errors(
    tmp_path: Path, mutator: BoundaryMutator, expected: str
) -> None:
    boundary = _load_boundary()
    mutator(boundary)

    assert any(expected in error for error in _errors(tmp_path, boundary))


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda d: d["records"][1].update({"component_id": "button"}), "duplicate id"),
        (lambda d: d["records"].pop(), "missing registry components"),
        (
            lambda d: d["records"][0].update({"component_id": "vendor_magic"}),
            "expected registry id",
        ),
        (lambda d: d["records"][0].update({"canonical_name": "wrong"}), "canonical_name"),
        (lambda d: d["records"][0].pop("evidence_anchors"), "missing required fields"),
        (lambda d: d["records"][0].update({"unexpected": "x"}), "unexpected fields"),
        (lambda d: d["records"][0].update({"token_authoring_status": "unknown"}), "invalid value"),
        (lambda d: d["records"][0].update({"token_dependencies": None}), "null is forbidden"),
        (lambda d: d["records"][0].update({"canonical_name": ""}), "empty string"),
    ],
)
def test_boundary_rejects_record_contract_errors(
    tmp_path: Path, mutator: BoundaryMutator, expected: str
) -> None:
    boundary = _load_boundary()
    mutator(boundary)

    assert any(expected in error for error in _errors(tmp_path, boundary))


def test_boundary_rejects_unknown_component_id_with_extra_record(tmp_path: Path) -> None:
    boundary = _load_boundary()
    extra = copy.deepcopy(boundary["records"][0])
    extra["component_id"] = "vendor_magic"
    boundary["records"].append(extra)

    errors = _errors(tmp_path, boundary)

    assert any("component not in registry" in error for error in errors)
    assert any("components not in registry: vendor_magic" in error for error in errors)


def test_boundary_rejects_wrong_component_order(tmp_path: Path) -> None:
    boundary = _load_boundary()
    boundary["records"][0], boundary["records"][1] = (
        boundary["records"][1],
        boundary["records"][0],
    )

    assert any("expected registry id" in error for error in _errors(tmp_path, boundary))


@pytest.mark.parametrize(
    "tool",
    ["Figma", "Canva", "Penpot", "Kimi", "Storybook", "Code Connect", "screenshots"],
)
def test_boundary_rejects_reference_only_authority_promotion(tmp_path: Path, tool: str) -> None:
    boundary = _load_boundary()
    boundary["authority"]["canonical"].append(tool)

    assert any(
        "reference artifacts must not be canonical" in error or "authority.canonical" in error
        for error in _errors(tmp_path, boundary)
    )


def test_boundary_rejects_generated_mirrors_as_authoring_truth(tmp_path: Path) -> None:
    boundary = _load_boundary()
    boundary["records"][0][
        "implementation_blocked_reason"
    ] = "Generated mirrors are the authoring truth for implementation."

    assert any(
        "generated mirrors must not be treated as authoring truth" in error
        for error in _errors(tmp_path, boundary)
    )


def test_boundary_rejects_token_value_mutation_claim(tmp_path: Path) -> None:
    boundary = _load_boundary()
    boundary["records"][0]["implementation_blocked_reason"] = "This gate may edit token values."

    assert any("must not mutate token values" in error for error in _errors(tmp_path, boundary))


def test_boundary_rejects_implementation_ready_before_visual_gate(tmp_path: Path) -> None:
    boundary = _load_boundary()
    boundary["records"][0]["implementation_readiness"] = "ready"

    errors = _errors(tmp_path, boundary)

    assert any("ready requires visual gate" in error for error in errors)


def test_boundary_rejects_implementation_ready_before_accessibility_gate(tmp_path: Path) -> None:
    boundary = _load_boundary()
    boundary["records"][0]["implementation_readiness"] = "ready"
    visual = json.loads(VISUAL_PATH.read_text(encoding="utf-8"))
    visual["records"][0]["visual_regression_decision"] = "ready"
    visual["records"][0]["baseline_policy"] = "existing_repo_baseline"
    visual["records"][0]["threshold_policy"] = "existing_repo_threshold"
    visual["records"][0]["tooling_policy"] = "existing_repo_tooling"
    decision_path = _write_repo_inputs(tmp_path, boundary, visual=visual)

    errors = boundary_module.validate_boundary(decision_path, repo_root=tmp_path)

    assert any("ready requires accessibility gate" in error for error in errors)


def test_boundary_rejects_wrong_next_gate(tmp_path: Path) -> None:
    boundary = _load_boundary()
    boundary["records"][0]["next_required_gate"] = "another design governance layer"

    assert any("next_required_gate" in error for error in _errors(tmp_path, boundary))


def test_validator_has_no_runtime_network_or_subprocess_imports() -> None:
    source = (REPO_ROOT / "scripts/design/design_token_runtime_parity_boundary.py").read_text(
        encoding="utf-8"
    )

    forbidden = [
        "import requests",
        "import httpx",
        "import socket",
        "import subprocess",
        "import app",
        "from app",
        "import frontend",
        "import ios",
    ]
    for token in forbidden:
        assert token not in source

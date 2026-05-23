from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.design import design_bridge_coverage_inventory as inventory_module

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO_ROOT / "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json"
REGISTRY_PATH = REPO_ROOT / "docs/orchestration/contracts/design_component_registry.v1.json"
VOCABULARY_PATH = REPO_ROOT / "docs/design/ui_component_vocabulary.json"


def _load_inventory() -> dict[str, object]:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _write_inventory(tmp_path: Path, inventory: object) -> Path:
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(inventory), encoding="utf-8")
    return path


def _errors(tmp_path: Path, inventory: object) -> list[str]:
    return inventory_module.validate_inventory(_write_inventory(tmp_path, inventory))


def test_valid_inventory_passes_and_covers_registry_once() -> None:
    inventory = _load_inventory()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    vocabulary = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))

    assert inventory_module.validate_inventory(INVENTORY_PATH) == []
    assert [r["component_id"] for r in inventory["records"]] == [
        c["component_id"] for c in registry["components"]
    ]
    assert {r["component_id"] for r in inventory["records"]} == {v["id"] for v in vocabulary}


def test_summarize_output_is_deterministic() -> None:
    assert inventory_module.summarize_inventory(INVENTORY_PATH) == {
        "schema_version": "design_bridge_coverage_inventory.v1",
        "record_count": 24,
        "coverage_counts": {
            "code_connect_coverage": {"unspecified": 24},
            "figma_reference_coverage": {"unspecified": 24},
            "ios_runtime_coverage": {"unspecified": 24},
            "penpot_reference_coverage": {"unspecified": 24},
            "repo_vocabulary_coverage": {"covered": 24},
            "storybook_review_coverage": {"unspecified": 24},
            "web_runtime_coverage": {"missing": 8, "partial": 16},
        },
        "blocked_for_implementation": 24,
        "next_required_gate_counts": {"visual regression decision gate": 24},
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("{", "invalid JSON"),
        ([], "expected JSON object"),
    ],
)
def test_inventory_rejects_malformed_or_non_object_json(
    tmp_path: Path, payload: object, expected: str
) -> None:
    path = tmp_path / "inventory.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")

    assert any(expected in error for error in inventory_module.validate_inventory(path))


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda d: d.pop("records"), "missing required fields: records"),
        (lambda d: d.update({"extra": True}), "unexpected fields: extra"),
        (lambda d: d.update({"schema_version": "wrong"}), "schema_version"),
        (lambda d: d.update({"source_of_truth": "figma"}), "source_of_truth"),
        (lambda d: d.update({"records": []}), "records: expected non-empty list"),
        (lambda d: d.update({"records": {}}), "records: expected non-empty list"),
    ],
)
def test_inventory_rejects_top_level_contract_errors(
    tmp_path: Path, mutator, expected: str
) -> None:
    inventory = _load_inventory()
    mutator(inventory)

    assert any(expected in error for error in _errors(tmp_path, inventory))


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda d: d["records"][1].update({"component_id": "button"}), "duplicate id"),
        (
            lambda d: d["records"][0].update({"component_id": "vendor_magic"}),
            "expected registry order id",
        ),
        (lambda d: d["records"].pop(), "missing registry components"),
        (lambda d: d["records"][0].update({"canonical_name": "wrong"}), "canonical_name"),
        (lambda d: d["records"][0].pop("evidence_anchors"), "missing required fields"),
        (lambda d: d["records"][0].update({"unexpected": "x"}), "unexpected fields"),
        (lambda d: d["records"][0].update({"canonical_name": ""}), "empty string"),
        (lambda d: d["records"][0].update({"ios_runtime_coverage": "unknown"}), "invalid coverage"),
        (lambda d: d["records"][0].update({"ios_runtime_coverage": None}), "null is forbidden"),
    ],
)
def test_inventory_rejects_record_contract_errors(tmp_path: Path, mutator, expected: str) -> None:
    inventory = _load_inventory()
    mutator(inventory)

    assert any(expected in error for error in _errors(tmp_path, inventory))


@pytest.mark.parametrize("tool", ["Kimi", "Figma", "Canva", "Penpot", "Storybook", "Code Connect"])
def test_inventory_rejects_reference_tools_as_canonical_authority(
    tmp_path: Path, tool: str
) -> None:
    inventory = _load_inventory()
    inventory["authority"]["canonical"].append(tool)

    assert any(
        "reference tools must not be canonical" in error for error in _errors(tmp_path, inventory)
    )


def test_inventory_rejects_missing_coverage_as_implementation_permission(tmp_path: Path) -> None:
    inventory = _load_inventory()
    inventory["records"][2]["implementation_blocked_reason"] = "Ready for runtime implementation."

    assert any("must block implementation" in error for error in _errors(tmp_path, inventory))


@pytest.mark.parametrize(
    "field", ["visual_regression_decision", "accessibility_regression_decision"]
)
def test_inventory_rejects_ready_regression_decisions(tmp_path: Path, field: str) -> None:
    inventory = _load_inventory()
    inventory["records"][0][field] = "covered"

    assert any(field in error and "fail-closed" in error for error in _errors(tmp_path, inventory))


def test_inventory_rejects_next_gate_skipping_to_runtime(tmp_path: Path) -> None:
    inventory = _load_inventory()
    inventory["records"][0]["next_required_gate"] = "web implementation"

    assert any("next_required_gate" in error for error in _errors(tmp_path, inventory))


def test_inventory_rejects_wrong_record_order(tmp_path: Path) -> None:
    inventory = _load_inventory()
    inventory["records"][0], inventory["records"][1] = (
        inventory["records"][1],
        inventory["records"][0],
    )

    assert any("expected registry order id" in error for error in _errors(tmp_path, inventory))


def test_inventory_rejects_reference_tool_evidence_as_canonical_proof(tmp_path: Path) -> None:
    inventory = _load_inventory()
    inventory["records"][0]["evidence_anchors"] = ["Figma:node-123"]

    errors = _errors(tmp_path, inventory)

    assert any("reference-tool evidence" in error for error in errors)
    assert any("repo evidence anchor" in error for error in errors)


def test_validator_has_no_runtime_network_or_subprocess_imports() -> None:
    source = (REPO_ROOT / "scripts/design/design_bridge_coverage_inventory.py").read_text(
        encoding="utf-8"
    )

    forbidden = [
        "import requests",
        "import httpx",
        "import socket",
        "import subprocess",
        "import app",
        "from app",
    ]
    for token in forbidden:
        assert token not in source

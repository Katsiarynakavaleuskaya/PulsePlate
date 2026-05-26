from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable, cast

import pytest

from scripts.design import design_accessibility_regression_decisions as decisions_module

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS_PATH = (
    REPO_ROOT / "docs/orchestration/contracts/design_accessibility_regression_decisions.v1.json"
)
BRIDGE_PATH = REPO_ROOT / "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json"
REGISTRY_PATH = REPO_ROOT / "docs/orchestration/contracts/design_component_registry.v1.json"
VISUAL_PATH = REPO_ROOT / "docs/orchestration/contracts/design_visual_regression_decisions.v1.json"
DecisionMutator = Callable[[dict[str, Any]], object]


def _load_decisions() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(DECISIONS_PATH.read_text(encoding="utf-8")))


def _write_decisions(tmp_path: Path, decisions: object) -> Path:
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps(decisions), encoding="utf-8")
    return path


def _write_repo_inputs(
    tmp_path: Path,
    decisions: dict[str, Any],
    *,
    bridge: dict[str, Any] | None = None,
    visual: dict[str, Any] | None = None,
) -> Path:
    decision_path = tmp_path / "decisions.json"
    decision_path.write_text(json.dumps(decisions), encoding="utf-8")
    bridge_path = tmp_path / "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json"
    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text(
        json.dumps(bridge or json.loads(BRIDGE_PATH.read_text(encoding="utf-8"))),
        encoding="utf-8",
    )
    registry_path = tmp_path / "docs/orchestration/contracts/design_component_registry.v1.json"
    registry_path.write_text(REGISTRY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    visual_path = (
        tmp_path / "docs/orchestration/contracts/design_visual_regression_decisions.v1.json"
    )
    visual_path.write_text(
        json.dumps(visual or json.loads(VISUAL_PATH.read_text(encoding="utf-8"))),
        encoding="utf-8",
    )
    for record in decisions.get("records", []):
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
    return decision_path


def _errors(tmp_path: Path, decisions: object) -> list[str]:
    return decisions_module.validate_decisions(_write_decisions(tmp_path, decisions))


def test_valid_decisions_pass_and_cover_bridge_inventory_once() -> None:
    decisions = _load_decisions()
    bridge = json.loads(BRIDGE_PATH.read_text(encoding="utf-8"))

    assert decisions_module.validate_decisions(DECISIONS_PATH) == []
    assert [record["component_id"] for record in decisions["records"]] == [
        record["component_id"] for record in bridge["records"]
    ]
    assert len({record["component_id"] for record in decisions["records"]}) == 24


def test_summarize_output_is_deterministic() -> None:
    expected_policy_counts = {"repo_evidence_required_before_runtime": 24}

    assert decisions_module.summarize_decisions(DECISIONS_PATH) == {
        "schema_version": "design_accessibility_regression_decisions.v1",
        "record_count": 24,
        "decision_counts": {
            "accessibility_regression_decision": {"blocked": 24},
            "aria_status_live_region_policy": expected_policy_counts,
            "ios_voiceover_dynamic_type_policy": expected_policy_counts,
            "keyboard_focus_policy": expected_policy_counts,
            "non_color_only_semantics_policy": expected_policy_counts,
            "reduced_motion_policy": expected_policy_counts,
            "semantic_role_name_value_policy": expected_policy_counts,
            "state_accessibility_policy": expected_policy_counts,
            "touch_target_policy": expected_policy_counts,
            "web_screen_reader_policy": expected_policy_counts,
            "implementation_readiness": {"blocked": 24},
        },
        "blocked_for_implementation": 24,
        "next_required_gate_counts": {"token/runtime parity boundary": 24},
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("{", "invalid JSON"),
        ([], "expected JSON object"),
    ],
)
def test_decisions_reject_malformed_or_non_object_json(
    tmp_path: Path, payload: object, expected: str
) -> None:
    path = tmp_path / "decisions.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")

    assert any(expected in error for error in decisions_module.validate_decisions(path))


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda d: d.pop("records"), "missing required fields: records"),
        (lambda d: d.update({"extra": True}), "unexpected fields: extra"),
        (lambda d: d.update({"schema_version": "wrong"}), "schema_version"),
        (lambda d: d.update({"source_of_truth": "figma"}), "source_of_truth"),
        (
            lambda d: d.update({"source_visual_decisions": "docs/wrong.json"}),
            "source_visual_decisions",
        ),
        (lambda d: d.update({"records": []}), "records: expected non-empty list"),
        (lambda d: d.update({"records": {}}), "records: expected non-empty list"),
    ],
)
def test_decisions_reject_top_level_contract_errors(
    tmp_path: Path, mutator: DecisionMutator, expected: str
) -> None:
    decisions = _load_decisions()
    mutator(decisions)

    assert any(expected in error for error in _errors(tmp_path, decisions))


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda d: d["records"][1].update({"component_id": "button"}), "duplicate id"),
        (
            lambda d: d["records"][0].update({"component_id": "vendor_magic"}),
            "expected bridge inventory id",
        ),
        (lambda d: d["records"].pop(), "missing bridge inventory components"),
        (lambda d: d["records"][0].update({"canonical_name": "wrong"}), "canonical_name"),
        (
            lambda d: d["records"][0].update({"bridge_inventory_anchor": "docs/wrong.md"}),
            "bridge_inventory_anchor",
        ),
        (
            lambda d: d["records"][0].update({"visual_decision_anchor": "docs/wrong.md"}),
            "visual_decision_anchor",
        ),
        (lambda d: d["records"][0].pop("evidence_anchors"), "missing required fields"),
        (lambda d: d["records"][0].update({"unexpected": "x"}), "unexpected fields"),
        (lambda d: d["records"][0].update({"canonical_name": ""}), "empty string"),
        (lambda d: d["records"][0].update({"keyboard_focus_policy": None}), "null is forbidden"),
        (
            lambda d: d["records"][0].update({"accessibility_regression_decision": "unknown"}),
            "invalid value 'unknown'",
        ),
    ],
)
def test_decisions_reject_record_contract_errors(
    tmp_path: Path, mutator: DecisionMutator, expected: str
) -> None:
    decisions = _load_decisions()
    mutator(decisions)

    assert any(expected in error for error in _errors(tmp_path, decisions))


def test_decisions_reject_unknown_component_id_with_extra_record(tmp_path: Path) -> None:
    decisions = _load_decisions()
    extra = copy.deepcopy(decisions["records"][0])
    extra["component_id"] = "vendor_magic"
    extra["bridge_inventory_anchor"] = (
        "docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json:vendor_magic"
    )
    extra["visual_decision_anchor"] = (
        "docs/orchestration/contracts/design_visual_regression_decisions.v1.json:vendor_magic"
    )
    decisions["records"].append(extra)

    errors = _errors(tmp_path, decisions)

    assert any("component not in bridge inventory" in error for error in errors)
    assert any("components not in bridge inventory: vendor_magic" in error for error in errors)


def test_decisions_reject_wrong_component_order(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0], decisions["records"][1] = (
        decisions["records"][1],
        decisions["records"][0],
    )

    assert any("expected bridge inventory id" in error for error in _errors(tmp_path, decisions))


def test_decisions_reject_visual_decision_order_mismatch(tmp_path: Path) -> None:
    decisions = _load_decisions()
    visual = json.loads(VISUAL_PATH.read_text(encoding="utf-8"))
    visual["records"][0], visual["records"][1] = visual["records"][1], visual["records"][0]
    decision_path = _write_repo_inputs(tmp_path, decisions, visual=visual)

    errors = decisions_module.validate_decisions(decision_path, repo_root=tmp_path)

    assert any("mismatch with visual decision order" in error for error in errors)


def test_decisions_reject_ready_accessibility_without_repo_evidence(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0]["accessibility_regression_decision"] = "ready"

    errors = _errors(tmp_path, decisions)

    assert any("ready requires repo evidence" in error for error in errors)
    assert any("ready requires ready visual decision" in error for error in errors)


def test_decisions_reject_visual_approval_as_accessibility_approval(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0][
        "implementation_blocked_reason"
    ] = "Visual approval is complete, so accessibility can be treated as approved."

    assert any(
        "visual decision must not substitute for accessibility approval" in error
        for error in _errors(tmp_path, decisions)
    )


def test_decisions_reject_implementation_ready_before_later_gates(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0]["implementation_readiness"] = "ready"

    assert any(
        "ready requires accessibility and token/runtime parity gates" in error
        for error in _errors(tmp_path, decisions)
    )


def test_decisions_reject_next_gate_runtime_implementation(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0]["next_required_gate"] = "runtime implementation"

    errors = _errors(tmp_path, decisions)

    assert any("next_required_gate" in error for error in errors)
    assert any("must not skip token/runtime parity boundary" in error for error in errors)


@pytest.mark.parametrize("tool", ["Kimi", "Figma", "Canva", "Penpot", "Storybook", "Code Connect"])
def test_decisions_reject_external_authority_promotion(tmp_path: Path, tool: str) -> None:
    decisions = _load_decisions()
    decisions["authority"]["canonical"].append(tool)

    assert any(
        "reference artifacts must not be canonical" in error
        for error in _errors(tmp_path, decisions)
    )


@pytest.mark.parametrize("artifact", ["screenshots", "generated design exports", "prompt outputs"])
def test_decisions_reject_reference_artifact_canonical_authority(
    tmp_path: Path, artifact: str
) -> None:
    decisions = _load_decisions()
    decisions["authority"]["canonical"].append(artifact)

    assert any(
        "reference artifacts must not be canonical" in error
        for error in _errors(tmp_path, decisions)
    )


def test_decisions_reject_nonexistent_repo_evidence_anchor(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0]["evidence_anchors"] = ["docs/not_real.md:123"]

    assert any(
        "repo evidence file does not exist" in error for error in _errors(tmp_path, decisions)
    )


def test_decisions_reject_non_repo_evidence_anchor(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0]["evidence_anchors"] = ["https://figma.example/node"]

    errors = _errors(tmp_path, decisions)

    assert any("reference-tool evidence" in error for error in errors)
    assert any("expected repo evidence anchor" in error for error in errors)


def test_decisions_reject_runtime_permission_wording(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decisions["records"][0][
        "implementation_blocked_reason"
    ] = "Runtime implementation is allowed after this accessibility gate."

    assert any(
        "must not grant runtime implementation permission" in error
        for error in _errors(tmp_path, decisions)
    )


def test_decisions_reject_missing_source_visual_decisions_file(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decision_path = _write_repo_inputs(tmp_path, decisions)
    visual_path = (
        tmp_path / "docs/orchestration/contracts/design_visual_regression_decisions.v1.json"
    )
    visual_path.unlink()

    errors = decisions_module.validate_decisions(decision_path, repo_root=tmp_path)

    assert any("source_visual_decisions: file not found" in error for error in errors)


def test_decisions_reject_missing_source_registry_file(tmp_path: Path) -> None:
    decisions = _load_decisions()
    decision_path = _write_repo_inputs(tmp_path, decisions)
    registry_path = tmp_path / "docs/orchestration/contracts/design_component_registry.v1.json"
    registry_path.unlink()

    errors = decisions_module.validate_decisions(decision_path, repo_root=tmp_path)

    assert any("source_registry: file not found" in error for error in errors)


def test_validator_has_no_runtime_network_or_subprocess_imports() -> None:
    source = (REPO_ROOT / "scripts/design/design_accessibility_regression_decisions.py").read_text(
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
        "from frontend",
        "import ios",
        "from ios",
    ]
    for token in forbidden:
        assert token not in source

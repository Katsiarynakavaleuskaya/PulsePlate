from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.design import execute_design, generate_figma_instructions, verify_design


def test_generated_instruction_includes_code_first_contract_fields() -> None:
    instruction = generate_figma_instructions.generate_screen_instruction("ios.home")
    payload = generate_figma_instructions.instruction_to_dict(instruction)

    assert payload["surface"] == "ios_home_screen"
    assert payload["layout_pattern"] == "hero-plus-quick-actions"
    assert payload["primary_components"] == ["hero", "button"]
    assert payload["supporting_components"] == [
        "stats-card",
        "navigation/tab-bar",
        "badge",
    ]
    assert "token_constraints" in payload
    assert payload["context_version"] == "code-first-ui-v1"
    assert payload["instructions"][0]["type"] == "create_frame"
    assert payload["instructions"][1]["canonical_component"] == "button"


def test_validate_governance_rejects_missing_contract_fields() -> None:
    instruction = {
        "screen_id": "ios.home",
        "page": "10_iOS_Home",
        "platform": "IOS",
        "dimensions": {"width": 390, "height": 844},
        "background_token": "Color.navy",
        "governance_checks": ["verify_instruction_contract"],
        "context_version": "code-first-ui-v1",
        "instructions": [],
    }

    errors = execute_design.validate_governance(instruction)

    assert any("Missing required instruction field" in error for error in errors)


def test_update_manifest_records_surface_and_layout_pattern(tmp_path: Path) -> None:
    manifest_path = tmp_path / "docs" / "design" / "figma-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"manifest_version": "1.0", "exports": []}),
        encoding="utf-8",
    )

    original_root = execute_design.PROJECT_ROOT
    execute_design.PROJECT_ROOT = tmp_path
    try:
        execute_design.update_manifest(
            "ios.home",
            {
                "screen_id": "ios.home",
                "executed_at": "2026-03-11T00:00:00Z",
                "status": "simulated",
                "surface": "ios_home_screen",
                "layout_pattern": "hero-plus-quick-actions",
                "simulation_mode": "deterministic_contract_stub",
                "created_nodes": [{"name": "Node", "type": "create_button"}],
            },
        )
    finally:
        execute_design.PROJECT_ROOT = original_root

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    export = manifest["exports"][0]
    assert export["surface"] == "ios_home_screen"
    assert export["layout_pattern"] == "hero-plus-quick-actions"
    assert export["simulation_mode"] == "deterministic_contract_stub"


def test_verify_screen_distinguishes_not_executed(tmp_path: Path) -> None:
    instruction_path = tmp_path / "scripts" / "design" / "instructions" / "ios_home.json"
    instruction_path.parent.mkdir(parents=True)
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.home")
    )
    instruction_path.write_text(json.dumps(payload), encoding="utf-8")

    original_root = verify_design.PROJECT_ROOT
    verify_design.PROJECT_ROOT = tmp_path
    try:
        result = verify_design.verify_screen(
            "ios.home",
            {"exports": []},
        )
    finally:
        verify_design.PROJECT_ROOT = original_root

    assert result["status"] == "not_executed"
    assert any(check["check"] == "manifest_entry" for check in result["checks"])


def test_verify_screen_detects_manifest_mismatch(tmp_path: Path) -> None:
    instruction_path = tmp_path / "scripts" / "design" / "instructions" / "ios_home.json"
    instruction_path.parent.mkdir(parents=True)
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.home")
    )
    instruction_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest = {
        "exports": [
            {
                "screen_id": "ios.home",
                "status": "simulated",
                "surface": "wrong_surface",
                "layout_pattern": "wrong_layout",
                "node_count": len(payload["instructions"]) - 1,
                "nodes": [],
            }
        ]
    }

    original_root = verify_design.PROJECT_ROOT
    verify_design.PROJECT_ROOT = tmp_path
    try:
        result = verify_design.verify_screen("ios.home", manifest)
    finally:
        verify_design.PROJECT_ROOT = original_root

    assert result["status"] == "fail"
    assert any("surface mismatch" in error.lower() for error in result["errors"])
    assert any("layout_pattern mismatch" in error.lower() for error in result["errors"])
    assert any("Node count mismatch" in error for error in result["errors"])

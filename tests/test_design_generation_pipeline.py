from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.design import execute_design, generate_figma_instructions, verify_design
from scripts.design.layout_templates import build_reusable_layout_template


def test_generated_instruction_includes_code_first_contract_fields() -> None:
    instruction = generate_figma_instructions.generate_screen_instruction("ios.home")
    payload = generate_figma_instructions.instruction_to_dict(instruction)

    assert payload["platform"] == "iOS"
    assert payload["surface"] == "ios_home_screen"
    assert payload["layout_archetype"] == "hero_shell"
    assert payload["layout_pattern"] == "hero-plus-quick-actions"
    assert payload["primary_components"] == ["hero", "button", "card"]
    assert payload["supporting_components"] == [
        "stats-card",
        "navigation/tab-bar",
        "badge",
    ]
    assert payload["sections"][0]["section_id"] == "hero-band"
    assert payload["component_hierarchy"][0]["component_id"] == "ios-home-shell"
    assert payload["component_hierarchy"][0]["hierarchy_level"] == 0
    assert "token_constraints" in payload
    assert payload["context_version"] == "code-first-ui-v1"
    assert payload["instructions"][0]["type"] == "create_frame"
    assert any(
        item["type"] == "create_frame" and item["component_id"] == "ios-home-actions"
        for item in payload["instructions"]
    )
    assert any(
        item["canonical_component"] == "button"
        and item["component_id"].startswith("node:ios.home.")
        and item["hierarchy_level"] == 2
        for item in payload["instructions"]
    )
    flagged_button = next(
        item
        for item in payload["instructions"]
        if item.get("component_id") == "node:ios.home.weekly_plan_reader"
    )
    primary_button = next(
        item
        for item in payload["instructions"]
        if item.get("component_id") == "node:ios.home.bmi_calculator"
    )
    assert "feature-flagged" in flagged_button["states"]
    assert "hover" not in primary_button["states"]
    assert payload["instructions"][0]["name"] == "iOS Home Screen"


def test_generated_web_progress_export_cta_uses_header_container() -> None:
    instruction = generate_figma_instructions.generate_screen_instruction("web.progress")
    payload = generate_figma_instructions.instruction_to_dict(instruction)

    export_button = next(
        item
        for item in payload["instructions"]
        if item.get("component_id") == "node:web.progress.export_pdf"
    )

    assert export_button["section_id"] == "progress-header"
    assert export_button["parent_component_id"] == "web-progress-header-utilities"
    assert any(
        section["section_id"] == "progress-header"
        and "node:web.progress.export_pdf" in section["component_ids"]
        for section in payload["sections"]
    )


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


def test_update_manifest_records_surface_and_layout_pattern(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "docs" / "design" / "figma-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"manifest_version": "1.0", "exports": []}),
        encoding="utf-8",
    )

    monkeypatch.setattr(execute_design, "PROJECT_ROOT", tmp_path)
    execute_design.update_manifest(
        "ios.home",
        {
            "screen_id": "ios.home",
            "executed_at": "2026-03-11T00:00:00Z",
            "status": "simulated",
            "surface": "ios_home_screen",
            "layout_archetype": "hero_shell",
            "layout_pattern": "hero-plus-quick-actions",
            "section_count": 3,
            "adapter_name": "deterministic_stub",
            "adapter_mode": "simulated",
            "simulation_mode": "deterministic_contract_stub",
            "created_nodes": [{"name": "Node", "type": "create_button"}],
        },
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    export = manifest["exports"][0]
    assert export["surface"] == "ios_home_screen"
    assert export["layout_archetype"] == "hero_shell"
    assert export["layout_pattern"] == "hero-plus-quick-actions"
    assert export["section_count"] == 3
    assert export["adapter_name"] == "deterministic_stub"
    assert export["adapter_mode"] == "simulated"
    assert export["simulation_mode"] == "deterministic_contract_stub"


def test_execute_instruction_uses_deterministic_adapter_metadata() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )

    result = execute_design.execute_instruction(payload, "deterministic_stub")

    assert result["status"] == "simulated"
    assert result["adapter_name"] == "deterministic_stub"
    assert result["adapter_mode"] == "simulated"
    assert result["executed_at"] == "2026-01-01T00:00:00Z"
    assert result["layout_archetype"] == "dashboard_shell"
    assert any(
        node["component_id"] == "node:web.progress.export_pdf" for node in result["created_nodes"]
    )


def test_platform_specific_button_states_and_platform_labels() -> None:
    ios_payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.progress")
    )
    web_payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )

    ios_button = next(
        item for item in ios_payload["instructions"] if item["type"] == "create_button"
    )
    web_button = next(
        item for item in web_payload["instructions"] if item["type"] == "create_button"
    )

    assert ios_payload["platform"] == "iOS"
    assert web_payload["platform"] == "Web"
    assert "hover" not in ios_button["states"]
    assert "hover" in web_button["states"]


def test_execute_instruction_supports_code_native_canvas_adapter() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.home")
    )

    result = execute_design.execute_instruction(payload, "code_native_canvas")

    assert result["status"] == "simulated"
    assert result["adapter_name"] == "code_native_canvas"
    assert result["adapter_mode"] == "render_plan"
    assert result["simulation_mode"] == "code_native_render_plan_stub"
    assert result["mcp_calls"][0]["tool"] == "code_native.render_plan"
    assert len(result["render_plan"]) == len(payload["instructions"])


def test_reusable_layout_template_registry_reuses_hero_shell() -> None:
    template = build_reusable_layout_template("hero_actions", "ios.home")

    assert template["layout_sections"][0]["id"] == "hero-band"
    assert template["static_component_tree"][0]["id"] == "ios-home-shell"
    assert template["static_component_tree"][1]["canonical_component"] == "hero"


def test_verify_screen_distinguishes_not_executed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instruction_path = tmp_path / "scripts" / "design" / "instructions" / "ios_home.json"
    instruction_path.parent.mkdir(parents=True)
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.home")
    )
    instruction_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(verify_design, "PROJECT_ROOT", tmp_path)
    result = verify_design.verify_screen(
        "ios.home",
        {"exports": []},
    )

    assert result["status"] == "not_executed"
    assert any(check["check"] == "manifest_entry" for check in result["checks"])


def test_verify_screen_detects_manifest_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                "layout_archetype": "wrong_archetype",
                "layout_pattern": "wrong_layout",
                "adapter_name": "deterministic_stub",
                "adapter_mode": "simulated",
                "node_count": len(payload["instructions"]) - 1,
                "nodes": [],
            }
        ]
    }

    monkeypatch.setattr(verify_design, "PROJECT_ROOT", tmp_path)
    result = verify_design.verify_screen("ios.home", manifest)

    assert result["status"] == "fail"
    assert any("surface mismatch" in error.lower() for error in result["errors"])
    assert any("layout_archetype mismatch" in error.lower() for error in result["errors"])
    assert any("layout_pattern mismatch" in error.lower() for error in result["errors"])
    assert any("Node count mismatch" in error for error in result["errors"])


def test_validate_governance_rejects_invalid_hierarchy_payload() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.home")
    )
    payload["component_hierarchy"][1]["parent_component_id"] = "missing-parent"
    payload["instructions"][1]["hierarchy_level"] = -1

    errors = execute_design.validate_governance(payload)

    assert any("Unknown parent_component_id" in error for error in errors)
    assert any("must define hierarchy_level >= 0" in error for error in errors)


def test_validate_governance_rejects_instruction_hierarchy_mismatch() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.home")
    )
    target_index = next(
        index
        for index, item in enumerate(payload["instructions"])
        if item["component_id"] == "node:ios.home.bmi_calculator"
    )
    payload["instructions"][target_index]["section_id"] = "hero-band"

    errors = execute_design.validate_governance(payload)

    assert any("section_id does not match component_hierarchy" in error for error in errors)


def test_validate_governance_requires_frame_instruction_for_static_nodes() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.home")
    )
    payload["instructions"] = [
        item for item in payload["instructions"] if item["component_id"] != "ios-home-actions"
    ]

    errors = execute_design.validate_governance(payload)

    assert any("Missing create_frame instructions" in error for error in errors)


def test_validate_governance_requires_button_instruction_for_button_nodes() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("ios.home")
    )
    payload["instructions"] = [
        item
        for item in payload["instructions"]
        if item["component_id"] != "node:ios.home.bmi_calculator"
    ]

    errors = execute_design.validate_governance(payload)

    assert any("Missing create_button instructions" in error for error in errors)


def test_validate_governance_rejects_duplicate_and_mismatched_instruction_metadata() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    payload["sections"][0]["component_ids"] = [
        component_id
        for component_id in payload["sections"][0]["component_ids"]
        if component_id != "web-progress-header-utilities"
    ]
    duplicated_frame = next(
        item for item in payload["instructions"] if item["component_id"] == "web-progress-shell"
    ).copy()
    payload["instructions"].append(duplicated_frame)

    target_index = next(
        index
        for index, item in enumerate(payload["instructions"])
        if item["component_id"] == "web-progress-header-utilities"
    )
    payload["instructions"][target_index]["canonical_component"] = "alert"
    payload["instructions"][target_index]["semantic_role"] = "recovery_message"

    errors = execute_design.validate_governance(payload)

    assert any("missing from sections.component_ids" in error for error in errors)
    assert any("Duplicate create_frame instruction" in error for error in errors)
    assert any("canonical_component does not match" in error for error in errors)
    assert any("semantic_role does not match" in error for error in errors)

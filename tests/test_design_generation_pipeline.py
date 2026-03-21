from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.design.canvas_artifact import CANVAS_ARTIFACT_VERSION, build_canvas_artifact
from scripts.design.contracts import validate_canvas_artifact_contract
from scripts.design import execute_design, generate_figma_instructions, html_preview, verify_design
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
    assert payload["interaction_contract"]["interaction_mode"] == "delegate_with_checkpoints"
    assert payload["interaction_contract"]["checkpoint_policy"] == "critical_actions_only"
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


def test_generated_web_plate_semantic_roles_match_hierarchy() -> None:
    instruction = generate_figma_instructions.generate_screen_instruction("web.plate")
    payload = generate_figma_instructions.instruction_to_dict(instruction)

    hierarchy_roles = {
        item["component_id"]: item["semantic_role"] for item in payload["component_hierarchy"]
    }
    instruction_roles = {
        item["component_id"]: item["semantic_role"]
        for item in payload["instructions"]
        if item["component_id"] in {"web-plate-badge", "web-plate-dialog"}
    }

    assert instruction_roles["web-plate-badge"] == hierarchy_roles["web-plate-badge"]
    assert instruction_roles["web-plate-dialog"] == hierarchy_roles["web-plate-dialog"]


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


def test_checked_in_instruction_inventory_passes_governance() -> None:
    for screen_id in sorted(generate_figma_instructions.PAGE_MAPPING):
        errors = execute_design.validate_governance(execute_design.load_instruction(screen_id))
        assert not errors, f"{screen_id}: {errors}"


def test_execute_design_main_validate_only_accepts_checked_in_inventory(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["execute_design.py", "--screen", "ios.home", "--validate-only"],
    )

    exit_code = execute_design.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Governance validation: PASSED" in captured.out
    assert captured.err == ""


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
    assert result["adapter_mode"] == "artifact_emit"
    assert result["simulation_mode"] == "code_native_canvas_artifact"
    assert result["artifact_type"] == CANVAS_ARTIFACT_VERSION
    assert result["artifact_version"] == CANVAS_ARTIFACT_VERSION
    assert result["component_count"] == len(result["render_plan"])
    assert result["component_count"] == len(result["canvas_artifact"]["nodes"])
    assert result["mcp_calls"][0]["tool"] == "code_native.emit_canvas_artifact"
    assert len(result["render_plan"]) == len(payload["instructions"])
    assert len(result["canvas_artifact"]["render_ops"]) == len(payload["instructions"])


def test_reusable_layout_template_registry_reuses_hero_shell() -> None:
    ios_template = build_reusable_layout_template("hero_actions", "ios.home")
    web_template = build_reusable_layout_template("hero_actions", "web.home")

    assert ios_template["layout_sections"][0]["id"] == "hero-band"
    assert web_template["layout_sections"][0]["id"] == "hero-band"
    assert ios_template["static_component_tree"][0]["id"] == "ios-home-shell"
    assert web_template["static_component_tree"][0]["id"] == "web-home-shell"
    assert ios_template["static_component_tree"][1]["canonical_component"] == "hero"
    assert web_template["static_component_tree"][1]["canonical_component"] == "hero"


def test_reusable_layout_template_registry_rejects_unknown_key() -> None:
    with pytest.raises(
        ValueError,
        match="Supported templates: content_actions, dashboard_recovery, form_stack, hero_actions, navigation_overlay",
    ):
        build_reusable_layout_template("unknown_template", "web.home")


def test_screen_content_model_keeps_metadata_only_authoring_path() -> None:
    content_model = generate_figma_instructions.SCREEN_CONTENT_MODEL["web.progress"]

    assert "layout_sections" not in content_model
    assert "static_component_tree" not in content_model
    assert content_model["layout_template_key"] == "dashboard_recovery"
    assert content_model["cta_parent_id"] == "web-progress-header-utilities"
    assert content_model["interaction_contract"]["interaction_mode"] == "review_and_inspect"


def test_canvas_artifact_matches_instruction_contract() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.plate")
    )

    canvas_artifact = build_canvas_artifact(payload)
    errors = validate_canvas_artifact_contract(canvas_artifact, payload)

    assert canvas_artifact["canvas_version"] == CANVAS_ARTIFACT_VERSION
    assert canvas_artifact["interaction_contract"] == payload["interaction_contract"]
    assert len(canvas_artifact["nodes"]) == len(payload["component_hierarchy"])
    assert len(canvas_artifact["render_ops"]) == len(payload["instructions"])
    assert not errors


def test_validate_governance_rejects_unknown_interaction_contract_value() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.home")
    )
    payload["interaction_contract"]["interaction_mode"] = "live_mutation"

    errors = execute_design.validate_governance(payload)

    assert any(
        "interaction_contract.interaction_mode unsupported value" in error for error in errors
    )


def test_build_canvas_artifact_does_not_split_string_token_constraints() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.plate")
    )
    payload["token_constraints"] = "Color.surface.canvas"

    canvas_artifact = build_canvas_artifact(payload)

    assert canvas_artifact["token_constraints"] == []


def test_execute_instruction_rejects_non_object_canvas_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InvalidCanvasAdapter:
        adapter_name = "code_native_canvas"
        adapter_mode = "artifact_emit"

        def execute(self, instruction: dict[str, Any]) -> dict[str, Any]:
            return {
                "screen_id": instruction["screen_id"],
                "status": "simulated",
                "canvas_artifact": [],
            }

    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.home")
    )

    monkeypatch.setattr(
        execute_design, "resolve_execution_adapter", lambda _: InvalidCanvasAdapter()
    )

    with pytest.raises(ValueError, match="expected object, got list"):
        execute_design.execute_instruction(payload, "code_native_canvas")


def test_code_native_canvas_created_nodes_preserve_hierarchy_metadata() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )

    result = execute_design.execute_instruction(payload, "code_native_canvas")
    export_node = next(
        node
        for node in result["created_nodes"]
        if node["component_id"] == "node:web.progress.export_pdf"
    )

    assert export_node["type"] == "create_button"
    assert export_node["parent_component_id"] == "web-progress-header-utilities"
    assert export_node["hierarchy_level"] == 2


def test_validate_canvas_artifact_requires_render_op_name() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.plate")
    )
    canvas_artifact = build_canvas_artifact(payload)
    del canvas_artifact["render_ops"][0]["name"]

    errors = validate_canvas_artifact_contract(canvas_artifact, payload)

    assert any("missing field(s): name" in error for error in errors)


def test_validate_canvas_artifact_returns_structural_errors_before_alignment_crash() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    canvas_artifact = build_canvas_artifact(payload)
    del canvas_artifact["nodes"][0]["source_ref"]

    errors = validate_canvas_artifact_contract(canvas_artifact, payload)

    assert any("canvas nodes[0] missing field(s): source_ref" in error for error in errors)


def test_validate_canvas_artifact_rejects_duplicate_render_op_component_ids() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.home")
    )
    canvas_artifact = build_canvas_artifact(payload)
    canvas_artifact["render_ops"][1]["component_id"] = canvas_artifact["render_ops"][0][
        "component_id"
    ]

    errors = validate_canvas_artifact_contract(canvas_artifact, payload)

    assert any("Duplicate canvas render_op component_id" in error for error in errors)


def test_validate_canvas_artifact_rejects_render_op_name_drift() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    canvas_artifact = build_canvas_artifact(payload)
    canvas_artifact["render_ops"][0]["name"] = "Drifted Name"

    errors = validate_canvas_artifact_contract(canvas_artifact, payload)

    assert "canvas render_ops do not match instruction operations" in errors


def test_validate_canvas_artifact_rejects_interaction_contract_drift() -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    canvas_artifact = build_canvas_artifact(payload)
    canvas_artifact["interaction_contract"]["checkpoint_policy"] = "critical_actions_only"

    errors = validate_canvas_artifact_contract(canvas_artifact, payload)

    assert any("canvas interaction_contract mismatch" in error for error in errors)


@pytest.mark.parametrize(
    ("screen_id", "expected_interaction_mode"),
    [
        ("ios.home", "delegate_with_checkpoints"),
        ("web.plate", "guided_adjustment"),
        ("web.progress", "review_and_inspect"),
    ],
)
def test_render_html_preview_is_deterministic_for_representative_surfaces(
    screen_id: str,
    expected_interaction_mode: str,
) -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction(screen_id)
    )
    canvas_artifact = build_canvas_artifact(payload)

    first_preview = html_preview.render_html_preview(canvas_artifact)
    second_preview = html_preview.render_html_preview(canvas_artifact)

    assert first_preview == second_preview
    assert 'data-preview-version="pulseplate_html_preview_v1"' in first_preview
    assert screen_id in first_preview
    assert payload["layout_pattern"] in first_preview
    assert payload["component_hierarchy"][0]["component_id"] in first_preview
    assert expected_interaction_mode in first_preview


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


def test_update_manifest_records_canvas_artifact_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "docs" / "design" / "figma-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"manifest_version": "1.0", "exports": []}),
        encoding="utf-8",
    )

    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    result = execute_design.execute_instruction(payload, "code_native_canvas")

    monkeypatch.setattr(execute_design, "PROJECT_ROOT", tmp_path)
    execute_design.update_manifest("web.progress", result)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    export = manifest["exports"][0]
    assert export["artifact_type"] == CANVAS_ARTIFACT_VERSION
    assert export["artifact_version"] == CANVAS_ARTIFACT_VERSION
    assert export["component_count"] == len(payload["component_hierarchy"])
    assert export["canvas_artifact"]["canvas_version"] == CANVAS_ARTIFACT_VERSION
    assert export["interaction_contract"]["interaction_mode"] == "review_and_inspect"


def test_verify_screen_accepts_code_native_canvas_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instruction_path = tmp_path / "scripts" / "design" / "instructions" / "web_progress.json"
    instruction_path.parent.mkdir(parents=True)
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    instruction_path.write_text(json.dumps(payload), encoding="utf-8")

    result = execute_design.execute_instruction(payload, "code_native_canvas")
    manifest = {
        "exports": [
            {
                "screen_id": "web.progress",
                "status": result["status"],
                "surface": result["surface"],
                "layout_archetype": result["layout_archetype"],
                "layout_pattern": result["layout_pattern"],
                "section_count": result["section_count"],
                "adapter_name": result["adapter_name"],
                "adapter_mode": result["adapter_mode"],
                "artifact_type": result["artifact_type"],
                "artifact_version": result["artifact_version"],
                "node_count": len(result["created_nodes"]),
                "component_count": result["component_count"],
                "nodes": result["created_nodes"],
                "canvas_artifact": result["canvas_artifact"],
            }
        ]
    }

    monkeypatch.setattr(verify_design, "PROJECT_ROOT", tmp_path)
    verification = verify_design.verify_screen("web.progress", manifest)

    assert verification["status"] == "warn"
    assert any(
        check["check"] == "canvas_artifact" and check["status"] == "pass"
        for check in verification["checks"]
    )


def test_generate_preview_artifact_updates_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "docs" / "design" / "figma-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"manifest_version": "1.0", "exports": []}),
        encoding="utf-8",
    )

    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    result = execute_design.execute_instruction(payload, "code_native_canvas")
    preview_output = tmp_path / "artifacts" / "design_previews" / "web_progress.html"

    monkeypatch.setattr(html_preview, "PROJECT_ROOT", tmp_path)
    execute_design.generate_preview_artifact(
        "web.progress",
        result,
        output_path=preview_output,
    )

    monkeypatch.setattr(execute_design, "PROJECT_ROOT", tmp_path)
    execute_design.update_manifest("web.progress", result)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    export = manifest["exports"][0]
    assert export["preview_artifact"]["preview_version"] == "pulseplate_html_preview_v1"
    assert (
        export["preview_artifact"]["output_path"] == "artifacts/design_previews/web_progress.html"
    )
    assert preview_output.exists()


def test_verify_screen_accepts_preview_artifact_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instruction_path = tmp_path / "scripts" / "design" / "instructions" / "web_progress.json"
    instruction_path.parent.mkdir(parents=True)
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    instruction_path.write_text(json.dumps(payload), encoding="utf-8")

    result = execute_design.execute_instruction(payload, "code_native_canvas")
    preview_output = tmp_path / "artifacts" / "design_previews" / "web_progress.html"
    monkeypatch.setattr(html_preview, "PROJECT_ROOT", tmp_path)
    execute_design.generate_preview_artifact(
        "web.progress",
        result,
        output_path=preview_output,
    )

    manifest = {
        "exports": [
            {
                "screen_id": "web.progress",
                "status": result["status"],
                "surface": result["surface"],
                "layout_archetype": result["layout_archetype"],
                "layout_pattern": result["layout_pattern"],
                "interaction_contract": result["interaction_contract"],
                "section_count": result["section_count"],
                "adapter_name": result["adapter_name"],
                "adapter_mode": result["adapter_mode"],
                "artifact_type": result["artifact_type"],
                "artifact_version": result["artifact_version"],
                "node_count": len(result["created_nodes"]),
                "component_count": result["component_count"],
                "nodes": result["created_nodes"],
                "canvas_artifact": result["canvas_artifact"],
                "preview_artifact": result["preview_artifact"],
            }
        ]
    }

    monkeypatch.setattr(verify_design, "PROJECT_ROOT", tmp_path)
    verification = verify_design.verify_screen("web.progress", manifest)

    assert verification["status"] == "warn"
    assert any(
        check["check"] == "preview_artifact" and check["status"] == "pass"
        for check in verification["checks"]
    )


def test_verify_screen_rejects_absolute_preview_artifact_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instruction_path = tmp_path / "scripts" / "design" / "instructions" / "web_progress.json"
    instruction_path.parent.mkdir(parents=True)
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )
    instruction_path.write_text(json.dumps(payload), encoding="utf-8")

    result = execute_design.execute_instruction(payload, "code_native_canvas")
    preview_artifact = {
        "preview_version": "pulseplate_html_preview_v1",
        "screen_id": "web.progress",
        "output_path": str(tmp_path / "artifacts" / "design_previews" / "web_progress.html"),
        "section_count": len(payload["sections"]),
        "node_count": len(payload["component_hierarchy"]),
        "render_op_count": len(payload["instructions"]),
        "interaction_mode": payload["interaction_contract"]["interaction_mode"],
    }
    manifest = {
        "exports": [
            {
                "screen_id": "web.progress",
                "status": result["status"],
                "surface": result["surface"],
                "layout_archetype": result["layout_archetype"],
                "layout_pattern": result["layout_pattern"],
                "interaction_contract": result["interaction_contract"],
                "section_count": result["section_count"],
                "adapter_name": result["adapter_name"],
                "adapter_mode": result["adapter_mode"],
                "artifact_type": result["artifact_type"],
                "artifact_version": result["artifact_version"],
                "node_count": len(result["created_nodes"]),
                "component_count": result["component_count"],
                "nodes": result["created_nodes"],
                "canvas_artifact": result["canvas_artifact"],
                "preview_artifact": preview_artifact,
            }
        ]
    }

    monkeypatch.setattr(verify_design, "PROJECT_ROOT", tmp_path)
    verification = verify_design.verify_screen("web.progress", manifest)

    assert any(
        check["check"] == "preview_artifact" and check["status"] == "fail"
        for check in verification["checks"]
    )
    assert "preview output_path must be repo-relative" in verification["errors"]


def test_execute_design_main_emit_preview_auto_selects_code_native_canvas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = generate_figma_instructions.instruction_to_dict(
        generate_figma_instructions.generate_screen_instruction("web.progress")
    )

    monkeypatch.setattr(execute_design, "load_instruction", lambda _screen_id: payload)
    monkeypatch.setattr(execute_design, "log_execution", lambda _screen_id, _results: None)
    monkeypatch.setattr(execute_design, "update_manifest", lambda _screen_id, _results: None)
    monkeypatch.setattr(html_preview, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["execute_design.py", "--screen", "web.progress", "--execute", "--emit-preview"],
    )

    exit_code = execute_design.main()
    captured = capsys.readouterr()
    preview_path = tmp_path / "artifacts" / "design_previews" / "web_progress.html"

    assert exit_code == 0
    assert "auto-selecting code_native_canvas" in captured.out
    assert "Adapter: code_native_canvas (artifact_emit)" in captured.out
    assert "HTML preview: artifacts/design_previews/web_progress.html" in captured.out
    assert preview_path.exists()


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

#!/usr/bin/env python3
"""
Figma Design Verification Script for PulsePlate.

Verifies created Figma designs against instruction specifications.

Usage:
    python scripts/design/verify_design.py --screen ios.home
    python scripts/design/verify_design.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.design.contracts import (
    SUPPORTED_SCREENS,
    validate_canvas_artifact_contract,
    validate_instruction_contract,
)
from scripts.design.html_preview import HTML_PREVIEW_VERSION

# Project root for resolving paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

AVAILABLE_SCREENS = list(SUPPORTED_SCREENS)


def load_manifest() -> dict[str, Any]:
    """Load figma-manifest.json."""
    manifest_path = PROJECT_ROOT / "docs" / "design" / "figma-manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path) as f:
        return cast(dict[str, Any], json.load(f))


def load_instruction(screen_id: str) -> dict[str, Any]:
    """Load instruction JSON for a screen."""
    instruction_path = (
        PROJECT_ROOT / "scripts" / "design" / "instructions" / f"{screen_id.replace('.', '_')}.json"
    )

    if not instruction_path.exists():
        raise FileNotFoundError(f"Instruction file not found: {instruction_path}")

    with open(instruction_path) as f:
        return cast(dict[str, Any], json.load(f))


def verify_screen(screen_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify a screen's design against its instruction."""
    result: dict[str, Any] = {
        "screen_id": screen_id,
        "status": "unknown",
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    # Load instruction
    try:
        instruction = load_instruction(screen_id)
    except FileNotFoundError as e:
        result["status"] = "error"
        result["errors"].append(f"Instruction not found: {e}")
        return result

    contract_errors = validate_instruction_contract(instruction)
    if contract_errors:
        result["status"] = "error"
        result["errors"].extend(contract_errors)
        result["checks"].append({"check": "instruction_contract", "status": "fail"})
        return result

    result["checks"].append({"check": "instruction_contract", "status": "pass"})

    # Check if screen exists in manifest exports
    exports = manifest.get("exports", [])
    screen_export = next((e for e in exports if e.get("screen_id") == screen_id), None)

    if not screen_export:
        result["status"] = "not_executed"
        result["warnings"].append("Screen not found in manifest exports (not yet executed)")
        result["checks"].append({"check": "manifest_entry", "status": "missing"})
        return result

    result["checks"].append({"check": "manifest_entry", "status": "present"})

    if screen_export.get("surface") == instruction.get("surface"):
        result["checks"].append({"check": "surface", "status": "pass"})
    else:
        result["checks"].append({"check": "surface", "status": "fail"})
        result["errors"].append(
            "Manifest surface mismatch: "
            f"expected {instruction.get('surface')}, got {screen_export.get('surface')}"
        )

    if screen_export.get("layout_pattern") == instruction.get("layout_pattern"):
        result["checks"].append({"check": "layout_pattern", "status": "pass"})
    else:
        result["checks"].append({"check": "layout_pattern", "status": "fail"})
        result["errors"].append(
            "Manifest layout_pattern mismatch: "
            f"expected {instruction.get('layout_pattern')}, got {screen_export.get('layout_pattern')}"
        )

    if screen_export.get("layout_archetype") == instruction.get("layout_archetype"):
        result["checks"].append({"check": "layout_archetype", "status": "pass"})
    else:
        result["checks"].append({"check": "layout_archetype", "status": "fail"})
        result["errors"].append(
            "Manifest layout_archetype mismatch: "
            f"expected {instruction.get('layout_archetype')}, got {screen_export.get('layout_archetype')}"
        )

    expected_section_count = len(instruction.get("sections", []))
    actual_section_count = screen_export.get("section_count")
    if expected_section_count == actual_section_count:
        result["checks"].append(
            {
                "check": "section_count",
                "status": "pass",
                "expected": expected_section_count,
                "actual": actual_section_count,
            }
        )
    else:
        result["checks"].append(
            {
                "check": "section_count",
                "status": "fail",
                "expected": expected_section_count,
                "actual": actual_section_count,
            }
        )
        result["errors"].append(
            "Manifest section_count mismatch: "
            f"expected {expected_section_count}, got {actual_section_count}"
        )

    # Verify instruction count matches
    expected_count = len(instruction.get("instructions", []))
    actual_count = screen_export.get("node_count", 0)

    if expected_count == actual_count:
        result["checks"].append(
            {
                "check": "node_count",
                "status": "pass",
                "expected": expected_count,
                "actual": actual_count,
            }
        )
    else:
        result["checks"].append(
            {
                "check": "node_count",
                "status": "fail",
                "expected": expected_count,
                "actual": actual_count,
            }
        )
        result["errors"].append(
            f"Node count mismatch: expected {expected_count}, got {actual_count}"
        )

    # Check execution status
    exec_status = screen_export.get("status", "unknown")
    adapter_name = screen_export.get("adapter_name")
    adapter_mode = screen_export.get("adapter_mode")
    if adapter_name:
        result["checks"].append(
            {"check": "execution_adapter", "status": "pass", "value": adapter_name}
        )
    else:
        result["warnings"].append("Execution adapter metadata missing in manifest export")
        result["checks"].append({"check": "execution_adapter", "status": "missing"})

    if exec_status == "simulated":
        result["warnings"].append("Design was simulated, not actually created in Figma")
        result["checks"].append(
            {
                "check": "execution_status",
                "status": "simulated",
                "adapter_mode": adapter_mode,
            }
        )
    elif exec_status == "completed":
        result["checks"].append({"check": "execution_status", "status": "pass"})
    else:
        result["checks"].append(
            {
                "check": "execution_status",
                "status": "unknown",
                "value": exec_status,
            }
        )

    if adapter_name == "code_native_canvas":
        expected_component_count = len(instruction.get("component_hierarchy", []))
        actual_component_count = screen_export.get("component_count")
        if expected_component_count == actual_component_count:
            result["checks"].append(
                {
                    "check": "component_count",
                    "status": "pass",
                    "expected": expected_component_count,
                    "actual": actual_component_count,
                }
            )
        else:
            result["checks"].append(
                {
                    "check": "component_count",
                    "status": "fail",
                    "expected": expected_component_count,
                    "actual": actual_component_count,
                }
            )
            result["errors"].append(
                "Component count mismatch: "
                f"expected {expected_component_count}, got {actual_component_count}"
            )

        artifact_type = screen_export.get("artifact_type")
        artifact_version = screen_export.get("artifact_version")
        if artifact_type == "pulseplate_canvas_v1":
            result["checks"].append({"check": "artifact_type", "status": "pass"})
        else:
            result["checks"].append({"check": "artifact_type", "status": "fail"})
            result["errors"].append(
                "Manifest artifact_type mismatch: "
                f"expected pulseplate_canvas_v1, got {artifact_type}"
            )

        if artifact_version == "pulseplate_canvas_v1":
            result["checks"].append({"check": "artifact_version", "status": "pass"})
        else:
            result["checks"].append({"check": "artifact_version", "status": "fail"})
            result["errors"].append(
                "Manifest artifact_version mismatch: "
                f"expected pulseplate_canvas_v1, got {artifact_version}"
            )

        canvas_artifact = screen_export.get("canvas_artifact")
        if isinstance(canvas_artifact, dict):
            canvas_errors = validate_canvas_artifact_contract(canvas_artifact, instruction)
            if canvas_errors:
                result["checks"].append({"check": "canvas_artifact", "status": "fail"})
                result["errors"].extend(canvas_errors)
            else:
                result["checks"].append({"check": "canvas_artifact", "status": "pass"})
        else:
            result["checks"].append({"check": "canvas_artifact", "status": "missing"})
            result["errors"].append("code_native_canvas export missing canvas_artifact payload")

        preview_artifact = screen_export.get("preview_artifact")
        if preview_artifact is not None:
            if not isinstance(preview_artifact, dict):
                result["checks"].append({"check": "preview_artifact", "status": "fail"})
                result["errors"].append("preview_artifact must be an object when present")
            else:
                preview_errors: list[str] = []
                if preview_artifact.get("preview_version") != HTML_PREVIEW_VERSION:
                    preview_errors.append(
                        "preview_version mismatch: expected "
                        f"{HTML_PREVIEW_VERSION}, got {preview_artifact.get('preview_version')}"
                    )
                if preview_artifact.get("screen_id") != screen_id:
                    preview_errors.append(
                        f"preview screen_id mismatch: expected {screen_id}, "
                        f"got {preview_artifact.get('screen_id')}"
                    )
                output_path = str(preview_artifact.get("output_path", "")).strip()
                if not output_path:
                    preview_errors.append("preview output_path must be non-empty")
                elif Path(output_path).is_absolute():
                    preview_errors.append("preview output_path must be repo-relative")

                expected_preview_counts = {
                    "section_count": len(instruction.get("sections", [])),
                    "node_count": len(instruction.get("component_hierarchy", [])),
                    "render_op_count": len(instruction.get("instructions", [])),
                }
                for field_name, expected_value in expected_preview_counts.items():
                    if preview_artifact.get(field_name) != expected_value:
                        preview_errors.append(
                            f"preview {field_name} mismatch: expected {expected_value}, "
                            f"got {preview_artifact.get(field_name)}"
                        )

                interaction_contract = screen_export.get("interaction_contract")
                if isinstance(interaction_contract, dict):
                    expected_interaction_mode = interaction_contract.get("interaction_mode")
                    if preview_artifact.get("interaction_mode") != expected_interaction_mode:
                        preview_errors.append(
                            "preview interaction_mode mismatch: expected "
                            f"{expected_interaction_mode}, got "
                            f"{preview_artifact.get('interaction_mode')}"
                        )

                if preview_errors:
                    result["checks"].append({"check": "preview_artifact", "status": "fail"})
                    result["errors"].extend(preview_errors)
                else:
                    result["checks"].append({"check": "preview_artifact", "status": "pass"})

    # Verify each CTA exists
    instruction_ctas = [
        inst for inst in instruction.get("instructions", []) if inst.get("type") == "create_button"
    ]
    export_nodes = screen_export.get("nodes", [])
    canvas_payload = screen_export.get("canvas_artifact")
    canvas_render_ops = (
        canvas_payload.get("render_ops", []) if isinstance(canvas_payload, dict) else []
    )

    for cta in instruction_ctas:
        cta_name = cta.get("name", "Unknown")
        cta_key = cta.get("cta_key", "")
        cta_component_id = cta.get("component_id", "")

        # Check if CTA exists in export nodes
        matching_node = next((n for n in export_nodes if n.get("name") == cta_name), None)
        matching_render_op = next(
            (item for item in canvas_render_ops if item.get("component_id") == cta_component_id),
            None,
        )

        if matching_node:
            result["checks"].append(
                {
                    "check": f"cta:{cta_key}",
                    "status": "present",
                    "name": cta_name,
                }
            )
        else:
            result["checks"].append(
                {
                    "check": f"cta:{cta_key}",
                    "status": "missing",
                    "name": cta_name,
                }
            )
            result["errors"].append(f"CTA not found in export: {cta_name} ({cta_key})")

        if adapter_name == "code_native_canvas":
            if matching_render_op:
                result["checks"].append(
                    {
                        "check": f"canvas_cta:{cta_key}",
                        "status": "present",
                        "component_id": cta_component_id,
                    }
                )
            else:
                result["checks"].append(
                    {
                        "check": f"canvas_cta:{cta_key}",
                        "status": "missing",
                        "component_id": cta_component_id,
                    }
                )
                result["errors"].append(
                    f"CTA render op not found in canvas artifact: {cta_name} ({cta_key})"
                )

    # Determine overall status
    if result["errors"]:
        result["status"] = "fail"
    elif result["warnings"]:
        result["status"] = "warn"
    else:
        result["status"] = "pass"

    return result


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify Figma designs against instruction specifications"
    )
    parser.add_argument(
        "--screen",
        help="Screen ID to verify (e.g., ios.home)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all screens",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    if not args.screen and not args.all:
        print("Error: Specify --screen <id> or --all", file=sys.stderr)
        return 1

    # Load manifest
    try:
        manifest = load_manifest()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Determine screens to verify
    screens = AVAILABLE_SCREENS if args.all else [args.screen]
    results = []

    for screen_id in screens:
        result = verify_screen(screen_id, manifest)
        results.append(result)

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("\n" + "=" * 60)
        print("FIGMA DESIGN VERIFICATION REPORT")
        print("=" * 60)

        all_pass = True
        for result in results:
            status_icon = {
                "pass": "✓",
                "warn": "⚠",
                "fail": "✗",
                "not_executed": "○",
                "error": "✗",
            }.get(result["status"], "?")

            print(f"\n{status_icon} {result['screen_id']}: {result['status'].upper()}")

            for check in result["checks"]:
                check_status = check.get("status", "unknown")
                check_icon = "✓" if check_status in ["pass", "present"] else "○"
                print(f"  {check_icon} {check.get('check')}: {check_status}")

            for warning in result["warnings"]:
                print(f"  ⚠ Warning: {warning}")

            for error in result["errors"]:
                print(f"  ✗ Error: {error}")
                all_pass = False

        print("\n" + "=" * 60)
        if all_pass:
            print("OVERALL: All verifications passed")
        else:
            print("OVERALL: Some verifications failed")
        print("=" * 60)

    # Return non-zero if any failures
    return 0 if all(r["status"] in ["pass", "warn", "not_executed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

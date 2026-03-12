#!/usr/bin/env python3
"""
Design Execution Pipeline for PulsePlate.

Executes code-first design instructions through runtime adapters and tracks results.

Usage:
    python scripts/design/execute_design.py --screen ios.home --validate-only
    python scripts/design/execute_design.py --screen ios.home --execute --adapter code_native_canvas
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.design.contracts import (
    SUPPORTED_SCREENS,
    validate_canvas_artifact_contract,
    validate_instruction_contract,
)
from scripts.design.execution_adapters import (
    available_adapter_names,
    resolve_execution_adapter,
)

# Project root for resolving paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_instruction(screen_id: str) -> dict[str, Any]:
    """Load instruction JSON for a screen."""
    instruction_path = (
        PROJECT_ROOT / "scripts" / "design" / "instructions" / f"{screen_id.replace('.', '_')}.json"
    )

    if not instruction_path.exists():
        raise FileNotFoundError(f"Instruction file not found: {instruction_path}")

    with open(instruction_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def validate_governance(instruction: dict[str, Any]) -> list[str]:
    """Validate instruction against governance rules."""
    errors: list[str] = list(validate_instruction_contract(instruction))
    checks = instruction.get("governance_checks", [])

    # Token usage check
    if "verify_token_usage" in checks:
        bg_token = instruction.get("background_token", "")
        if not bg_token:
            errors.append("Missing background_token")
        elif bg_token.startswith("#"):
            errors.append(f"Raw hex color used: {bg_token} (use design token)")

    # HPP compliance check
    if "verify_hpp_compliance" in checks:
        screen_id = instruction.get("screen_id", "")
        if screen_id not in SUPPORTED_SCREENS:
            errors.append(f"Screen {screen_id} not in H+P+Pr scope")

    # CTA registry check
    if "verify_cta_registry_match" in checks:
        instructions_list = instruction.get("instructions", [])
        for inst in instructions_list:
            if not isinstance(inst, dict):
                continue
            if inst.get("type") == "create_button":
                cta_key = inst.get("cta_key", "")
                if not cta_key:
                    errors.append(f"Button {inst.get('name')} missing cta_key")

    return errors


def execute_instruction(instruction: dict[str, Any], adapter_name: str) -> dict[str, Any]:
    """Execute one instruction payload through the configured adapter seam."""

    adapter = resolve_execution_adapter(adapter_name)
    results = cast(dict[str, Any], adapter.execute(instruction))

    canvas_artifact = results.get("canvas_artifact")
    if canvas_artifact is not None and not isinstance(canvas_artifact, dict):
        raise ValueError(
            f"Invalid canvas artifact emitted by {adapter_name}: expected object, "
            f"got {type(canvas_artifact).__name__}"
        )
    if adapter_name == "code_native_canvas" and not isinstance(canvas_artifact, dict):
        raise ValueError(
            f"Invalid canvas artifact emitted by {adapter_name}: missing artifact payload"
        )
    if isinstance(canvas_artifact, dict):
        canvas_errors = validate_canvas_artifact_contract(canvas_artifact, instruction)
        if canvas_errors:
            joined_errors = "; ".join(canvas_errors)
            raise ValueError(f"Invalid canvas artifact emitted by {adapter_name}: {joined_errors}")

    return results


def update_manifest(screen_id: str, results: dict[str, Any]) -> None:
    """Update figma-manifest.json with execution results."""
    manifest_path = PROJECT_ROOT / "docs" / "design" / "figma-manifest.json"

    if not manifest_path.exists():
        print(f"Warning: Manifest not found at {manifest_path}")
        return

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    # Add execution results to exports
    if "exports" not in manifest:
        manifest["exports"] = []

    # Check if screen already exists in exports
    existing = next((e for e in manifest["exports"] if e.get("screen_id") == screen_id), None)

    export_entry = {
        "screen_id": screen_id,
        "executed_at": results.get("executed_at"),
        "status": results.get("status"),
        "surface": results.get("surface"),
        "layout_archetype": results.get("layout_archetype"),
        "layout_pattern": results.get("layout_pattern"),
        "section_count": results.get("section_count"),
        "adapter_name": results.get("adapter_name"),
        "adapter_mode": results.get("adapter_mode"),
        "simulation_mode": results.get("simulation_mode"),
        "artifact_type": results.get("artifact_type"),
        "artifact_version": results.get("artifact_version"),
        "node_count": len(results.get("created_nodes", [])),
        "component_count": results.get("component_count"),
        "nodes": results.get("created_nodes", []),
        "canvas_artifact": results.get("canvas_artifact"),
    }

    if existing:
        # Update existing entry
        idx = manifest["exports"].index(existing)
        manifest["exports"][idx] = export_entry
    else:
        # Add new entry
        manifest["exports"].append(export_entry)

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Updated manifest: {manifest_path}")


def log_execution(screen_id: str, results: dict[str, Any]) -> None:
    """Log execution results to audit file."""
    logs_dir = PROJECT_ROOT / "docs" / "figma" / "execution_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = logs_dir / f"{timestamp}_{screen_id.replace('.', '_')}.json"

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Execution log: {log_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Execute design instructions via runtime adapters")
    parser.add_argument(
        "--screen",
        required=True,
        help="Screen ID (e.g., ios.home, web.plate)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate instruction only, do not execute",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute instruction via the selected adapter (currently simulated)",
    )
    parser.add_argument(
        "--adapter",
        choices=available_adapter_names(),
        default="deterministic_stub",
        help="Execution adapter seam to use",
    )
    parser.add_argument(
        "--update-manifest",
        action="store_true",
        default=True,
        help="Update figma-manifest.json after execution",
    )

    args = parser.parse_args()

    # Load instruction
    try:
        instruction = load_instruction(args.screen)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Loaded instruction for: {args.screen}")
    print(f"  Page: {instruction.get('page')}")
    print(f"  Platform: {instruction.get('platform')}")
    print(f"  Instructions: {len(instruction.get('instructions', []))}")

    # Validate
    errors = validate_governance(instruction)
    if errors:
        print("\nGovernance validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("\nGovernance validation: PASSED")

    if args.validate_only:
        return 0

    if not args.execute:
        print("\nUse --execute to run via the selected adapter (currently simulated)")
        return 0

    # Execute (currently simulated)
    print("\nExecuting design instructions...")
    results = execute_instruction(instruction, args.adapter)

    print("\nExecution results:")
    print(f"  Status: {results.get('status')}")
    print(f"  Adapter: {results.get('adapter_name')} ({results.get('adapter_mode')})")
    print(f"  Nodes created: {len(results.get('created_nodes', []))}")
    print(f"  MCP calls: {len(results.get('mcp_calls', []))}")

    # Log execution
    log_execution(args.screen, results)

    # Update manifest
    if args.update_manifest:
        update_manifest(args.screen, results)

    print("\nNote: live external design tools are intentionally optional.")
    print("Current execution uses local runtime adapter seams.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Figma Design Execution Pipeline for PulsePlate.

Executes Figma design instructions via MCP and tracks results.

Usage:
    python scripts/design/execute_design.py --screen ios.home --validate-only
    python scripts/design/execute_design.py --screen ios.home --execute
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Project root for resolving paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_instruction(screen_id: str) -> dict[str, Any]:
    """Load instruction JSON for a screen."""
    instruction_path = (
        PROJECT_ROOT / "scripts" / "design" / "instructions" / f"{screen_id.replace('.', '_')}.json"
    )

    if not instruction_path.exists():
        raise FileNotFoundError(f"Instruction file not found: {instruction_path}")

    with open(instruction_path) as f:
        return json.load(f)


def validate_governance(instruction: dict[str, Any]) -> list[str]:
    """Validate instruction against governance rules."""
    errors = []
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
        valid_screens = [
            "ios.home",
            "ios.plate",
            "ios.progress",
            "web.home",
            "web.plate",
            "web.progress",
        ]
        if screen_id not in valid_screens:
            errors.append(f"Screen {screen_id} not in H+P+Pr scope")

    # CTA registry check
    if "verify_cta_registry_match" in checks:
        instructions_list = instruction.get("instructions", [])
        for inst in instructions_list:
            if inst.get("type") == "create_button":
                cta_key = inst.get("cta_key", "")
                if not cta_key:
                    errors.append(f"Button {inst.get('name')} missing cta_key")

    return errors


def simulate_mcp_execution(instruction: dict[str, Any]) -> dict[str, Any]:
    """Simulate MCP execution (placeholder for actual MCP calls).

    In production, this would invoke actual Figma MCP tools:
    - figma.create_frame
    - figma.create_components
    - figma.apply_styles

    For now, it returns a simulated result structure.
    """
    screen_id = instruction.get("screen_id", "unknown")
    instructions_list = instruction.get("instructions", [])

    # Simulate node ID generation
    results = {
        "screen_id": screen_id,
        "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "simulated",
        "created_nodes": [],
        "mcp_calls": [],
    }

    for i, inst in enumerate(instructions_list):
        inst_type = inst.get("type", "unknown")
        inst_name = inst.get("name", f"Node_{i}")

        # Simulate MCP call
        results["mcp_calls"].append(
            {"tool": f"figma.{inst_type}", "params": {"name": inst_name}, "status": "simulated"}
        )

        # Simulate created node
        results["created_nodes"].append(
            {
                "type": inst_type,
                "name": inst_name,
                "node_id": f"simulated:{screen_id}:{i}",
                "status": "pending_real_execution",
            }
        )

    return results


def update_manifest(screen_id: str, results: dict[str, Any]) -> None:
    """Update figma-manifest.json with execution results."""
    manifest_path = PROJECT_ROOT / "docs" / "design" / "figma-manifest.json"

    if not manifest_path.exists():
        print(f"Warning: Manifest not found at {manifest_path}")
        return

    with open(manifest_path) as f:
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
        "node_count": len(results.get("created_nodes", [])),
        "nodes": results.get("created_nodes", []),
    }

    if existing:
        # Update existing entry
        idx = manifest["exports"].index(existing)
        manifest["exports"][idx] = export_entry
    else:
        # Add new entry
        manifest["exports"].append(export_entry)

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Updated manifest: {manifest_path}")


def log_execution(screen_id: str, results: dict[str, Any]) -> None:
    """Log execution results to audit file."""
    logs_dir = PROJECT_ROOT / "docs" / "figma" / "execution_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = logs_dir / f"{timestamp}_{screen_id.replace('.', '_')}.json"

    with open(log_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Execution log: {log_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Execute Figma design instructions via MCP")
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
        help="Execute instruction via MCP (currently simulated)",
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
        print("\nUse --execute to run MCP execution (currently simulated)")
        return 0

    # Execute (currently simulated)
    print("\nExecuting design instructions...")
    results = simulate_mcp_execution(instruction)

    print("\nExecution results:")
    print(f"  Status: {results.get('status')}")
    print(f"  Nodes created: {len(results.get('created_nodes', []))}")
    print(f"  MCP calls: {len(results.get('mcp_calls', []))}")

    # Log execution
    log_execution(args.screen, results)

    # Update manifest
    if args.update_manifest:
        update_manifest(args.screen, results)

    print("\nNote: Actual MCP execution requires Figma MCP connection.")
    print("Current execution is simulated. Connect MCP to create real designs.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

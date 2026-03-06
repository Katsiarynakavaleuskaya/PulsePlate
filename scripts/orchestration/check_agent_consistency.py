#!/usr/bin/env python3
"""CLI to verify agent docs consistency across all canonical layers.

Exit 0 = PASS, 1 = FAIL. Run before merge readiness.
Usage:
    python scripts/orchestration/check_agent_consistency.py [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.agent_consistency_loader import load_agent_sets


def _diff(a: set[str], b: set[str]) -> List[str]:
    return sorted(a - b)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="check_agent_consistency",
        description="Verify agent docs and files stay aligned across canonical layers.",
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON report")
    args = ap.parse_args()

    sets_ = load_agent_sets()
    files = sets_.files
    index = sets_.index
    inventory = sets_.inventory
    capability = sets_.capability
    context = sets_.context
    routing = sets_.routing
    allowlist = sets_.non_routable

    inventory_file_backed = inventory - sets_.system_exceptions
    repo_backed_expected = routing | allowlist

    files_not_in_index = _diff(files, index)
    index_not_in_files = _diff(index, files)
    routing_not_in_inventory = _diff(routing, inventory)
    routing_missing_in_files = _diff(repo_backed_expected, files)
    routing_missing_in_index = _diff(repo_backed_expected, index)
    inventory_not_in_capability = _diff(inventory, capability)
    inventory_not_in_context = _diff(inventory_file_backed, context)
    allowlist_not_in_inventory = _diff(allowlist, inventory)

    report: Dict[str, Any] = {
        "counts": {
            "files": len(files),
            "index": len(index),
            "inventory": len(inventory),
            "capability": len(capability),
            "context": len(context),
            "routing": len(routing),
            "non_routable": len(allowlist),
        },
        "system_exceptions": sorted(sets_.system_exceptions),
        "files_not_in_index": files_not_in_index,
        "index_not_in_files": index_not_in_files,
        "routing_missing_in_inventory": routing_not_in_inventory,
        "routing_missing_in_files": routing_missing_in_files,
        "routing_missing_in_index": routing_missing_in_index,
        "inventory_missing_in_capability": inventory_not_in_capability,
        "inventory_missing_in_context": inventory_not_in_context,
        "allowlisted_missing_in_inventory": allowlist_not_in_inventory,
        "ok": not any(
            (
                files_not_in_index,
                index_not_in_files,
                routing_not_in_inventory,
                routing_missing_in_files,
                routing_missing_in_index,
                inventory_not_in_capability,
                inventory_not_in_context,
                allowlist_not_in_inventory,
            )
        ),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if report["ok"]:
            print("OK: agent docs and files are consistent.")
        else:
            print("FAIL: agent consistency violations detected.")
            for key in (
                "files_not_in_index",
                "index_not_in_files",
                "routing_missing_in_inventory",
                "routing_missing_in_files",
                "routing_missing_in_index",
                "inventory_missing_in_capability",
                "inventory_missing_in_context",
                "allowlisted_missing_in_inventory",
            ):
                if report[key]:
                    print(f"- {key} ({len(report[key])}):")
                    for item in report[key]:
                        print(f"  - {item}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

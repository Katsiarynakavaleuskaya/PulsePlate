#!/usr/bin/env python3
"""CLI to verify agent docs consistency: routing ⊆ inventory ⊆ capability.

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
        description="Verify agent docs: routing ⊆ inventory ⊆ capability.",
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON report")
    args = ap.parse_args()

    sets_ = load_agent_sets()
    inv = sets_.inventory
    cap = sets_.capability
    rt = sets_.routing

    routing_not_in_inventory = _diff(rt, inv)
    inventory_not_in_capability = _diff(inv, cap)

    # Required: routing ⊆ inventory. Advisory: inventory ⊆ capability (warn only until matrix updated).
    report: Dict[str, Any] = {
        "counts": {"inventory": len(inv), "capability": len(cap), "routing": len(rt)},
        "routing_missing_in_inventory": routing_not_in_inventory,
        "inventory_missing_in_capability": inventory_not_in_capability,
        "ok": not routing_not_in_inventory,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if report["ok"]:
            print("OK: routing ⊆ inventory.")
            if report["inventory_missing_in_capability"]:
                print(
                    f"WARN: {len(report['inventory_missing_in_capability'])} inventory agents not in capability matrix (advisory)."
                )
        else:
            print("FAIL: routing ⊆ inventory violated.")
            if report["routing_missing_in_inventory"]:
                print(
                    f"- routing_missing_in_inventory ({len(report['routing_missing_in_inventory'])}):"
                )
                for item in report["routing_missing_in_inventory"]:
                    print(f"  - {item}")
        if report["inventory_missing_in_capability"] and not report["ok"]:
            print(
                f"WARN: inventory_missing_in_capability ({len(report['inventory_missing_in_capability'])})."
            )

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

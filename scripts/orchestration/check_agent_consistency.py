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

from scripts.orchestration.agent_consistency_loader import (
    SYSTEM_AGENT_EXCEPTIONS,
    load_agent_file_slugs,
    load_agent_sets,
    load_capability_agents,
    load_context_agents,
    load_declared_routing_clusters,
    load_index_agents,
    load_inventory_agents,
    load_non_routable_agents,
    load_routing_agents,
)
from scripts.orchestration.routing_graph_loader import load_routing_clusters_raw


def _diff(a: set[str], b: set[str]) -> List[str]:
    return sorted(a - b)


def _safe_load_set(loader_name: str, loader: Any, loader_errors: List[str]) -> set[str]:
    """Best-effort set loader used for structured CLI output on loader failures."""

    try:
        return loader()
    except (FileNotFoundError, ValueError) as exc:
        loader_errors.append(f"{loader_name}: {exc}")
        return set()


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="check_agent_consistency",
        description="Verify agent docs and files stay aligned across canonical layers.",
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON report")
    args = ap.parse_args()

    loader_errors: List[str] = []

    try:
        sets_ = load_agent_sets()
        files = sets_.files
        index = sets_.index
        inventory = sets_.inventory
        capability = sets_.capability
        context = sets_.context
        routing = sets_.routing
        routing_clusters = sets_.routing_clusters
        declared_clusters = sets_.declared_clusters
        allowlist = sets_.non_routable
        system_exceptions = sets_.system_exceptions
    except (FileNotFoundError, ValueError) as exc:
        loader_errors.append(f"agent_sets: {exc}")
        files = _safe_load_set("agent_files", load_agent_file_slugs, loader_errors)
        index = _safe_load_set("agent_index", load_index_agents, loader_errors)
        inventory = _safe_load_set("agent_inventory", load_inventory_agents, loader_errors)
        capability = _safe_load_set("capability_matrix", load_capability_agents, loader_errors)
        context = _safe_load_set("context_map", load_context_agents, loader_errors)
        routing = _safe_load_set("routing_agents", load_routing_agents, loader_errors)
        routing_clusters = _safe_load_set(
            "routing_clusters_raw", load_routing_clusters_raw, loader_errors
        )
        declared_clusters = _safe_load_set(
            "declared_routing_clusters", load_declared_routing_clusters, loader_errors
        )
        allowlist = _safe_load_set(
            "non_routable_allowlist", load_non_routable_agents, loader_errors
        )
        system_exceptions = set(SYSTEM_AGENT_EXCEPTIONS)

    inventory_file_backed = inventory - system_exceptions
    files_file_backed = files - system_exceptions
    index_file_backed = index - system_exceptions
    repo_backed_expected = routing | allowlist

    files_not_in_index = _diff(files, index)
    index_not_in_files = _diff(index, files)
    routing_not_in_inventory = _diff(routing, inventory)
    routing_missing_in_files = _diff(repo_backed_expected, files)
    routing_missing_in_index = _diff(repo_backed_expected, index)
    files_not_in_context = _diff(files_file_backed, context)
    index_not_in_context = _diff(index_file_backed, context)
    inventory_not_in_capability = _diff(inventory, capability)
    inventory_not_in_context = _diff(inventory_file_backed, context)
    allowlist_not_in_inventory = _diff(allowlist, inventory)
    routing_clusters_undefined = _diff(routing_clusters, declared_clusters)
    declared_clusters_unused = _diff(declared_clusters, routing_clusters)

    report: Dict[str, Any] = {
        "counts": {
            "files": len(files),
            "index": len(index),
            "inventory": len(inventory),
            "capability": len(capability),
            "context": len(context),
            "routing": len(routing),
            "routing_clusters": len(routing_clusters),
            "declared_clusters": len(declared_clusters),
            "non_routable": len(allowlist),
        },
        "routing_clusters": sorted(routing_clusters),
        "declared_clusters": sorted(declared_clusters),
        "loader_errors": loader_errors,
        "system_exceptions": sorted(system_exceptions),
        "files_not_in_index": files_not_in_index,
        "index_not_in_files": index_not_in_files,
        "routing_missing_in_inventory": routing_not_in_inventory,
        "routing_missing_in_files": routing_missing_in_files,
        "routing_missing_in_index": routing_missing_in_index,
        "files_missing_in_context": files_not_in_context,
        "index_missing_in_context": index_not_in_context,
        "inventory_missing_in_capability": inventory_not_in_capability,
        "inventory_missing_in_context": inventory_not_in_context,
        "allowlisted_missing_in_inventory": allowlist_not_in_inventory,
        "routing_clusters_undefined": routing_clusters_undefined,
        "declared_clusters_unused": declared_clusters_unused,
        "ok": not any(
            (
                files_not_in_index,
                index_not_in_files,
                routing_not_in_inventory,
                routing_missing_in_files,
                routing_missing_in_index,
                files_not_in_context,
                index_not_in_context,
                inventory_not_in_capability,
                inventory_not_in_context,
                allowlist_not_in_inventory,
                routing_clusters_undefined,
                declared_clusters_unused,
                loader_errors,
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
            if report["loader_errors"]:
                print(f"- loader_errors ({len(report['loader_errors'])}):")
                for item in report["loader_errors"]:
                    print(f"  - {item}")
            for key in (
                "files_not_in_index",
                "index_not_in_files",
                "routing_missing_in_inventory",
                "routing_missing_in_files",
                "routing_missing_in_index",
                "files_missing_in_context",
                "index_missing_in_context",
                "inventory_missing_in_capability",
                "inventory_missing_in_context",
                "allowlisted_missing_in_inventory",
                "routing_clusters_undefined",
                "declared_clusters_unused",
            ):
                if report[key]:
                    print(f"- {key} ({len(report[key])}):")
                    for item in report[key]:
                        print(f"  - {item}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

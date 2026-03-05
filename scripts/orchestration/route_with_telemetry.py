#!/usr/bin/env python3
"""Self-optimizing routing helper: telemetry + canonical graph → RoutingDecision.

Reads artifacts/orchestration/telemetry_rollup.json (advisory) and
docs/orchestration/AGENT_ROUTING_GRAPH.md (canonical baseline).
Outputs JSON with primary/secondary/reviewer. No network calls, no auto-commits.

Usage:
    python scripts/orchestration/route_with_telemetry.py --domain safety --task-type "Safety / Philosophy / Logic"
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.routing_graph_loader import (
    DomainRoute,
    load_routing_graph,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TELEMETRY_PATH = REPO_ROOT / "artifacts" / "orchestration" / "telemetry_rollup.json"


@dataclass(frozen=True)
class RoutingDecision:
    """Routing decision: primary, optional secondary, reviewer, rationale."""

    domain: str
    task_type: str
    primary: str
    secondary: Optional[str]
    reviewer: str
    rationale: Dict[str, Any]


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_agent_stats(telemetry: Dict[str, Any], agent: str) -> Dict[str, Any]:
    agents = telemetry.get("agents", {})
    if not isinstance(agents, dict):
        return {}
    stats = agents.get(agent, {})
    return stats if isinstance(stats, dict) else {}


def _is_stable(stats: Dict[str, Any]) -> bool:
    return stats.get("stability") == "STABLE"


def _avg_score(stats: Dict[str, Any]) -> float:
    try:
        return float(stats.get("avg_score", 0.0))
    except Exception:
        return 0.0


def _rewrite_rate(stats: Dict[str, Any]) -> float:
    meta = stats.get("meta", {})
    if not isinstance(meta, dict):
        return 0.0
    try:
        runs = int(meta.get("runs", 0) or 0)
        rewrites = int(meta.get("decision_REWRITE_REQUIRED", 0) or 0)
    except (ValueError, TypeError):
        return 0.0
    if runs <= 0:
        return 0.0
    return rewrites / runs


def _canonical_fallback(
    domain: str, routing: Dict[str, DomainRoute]
) -> Tuple[str, Optional[str], str]:
    """Get primary/secondary/reviewer from canonical routing graph."""
    dr = routing.get(domain)
    if dr:
        return (dr.primary, dr.secondary, dr.reviewer)
    return ("agent-coordinator", None, "agent-coordinator")


def route(
    domain: str,
    task_type: str,
    *,
    telemetry: Optional[Dict[str, Any]],
    routing: Dict[str, DomainRoute],
) -> RoutingDecision:
    """Compute routing decision from telemetry (advisory) + canonical graph."""
    domain = domain.strip().lower()
    canon_primary, canon_secondary, canon_reviewer = _canonical_fallback(domain, routing)

    rationale: Dict[str, Any] = {"source": "canonical_only"}
    primary = canon_primary
    secondary = canon_secondary
    reviewer = canon_reviewer

    if not telemetry:
        return RoutingDecision(domain, task_type, primary, secondary, reviewer, rationale)

    domains = telemetry.get("domains", {})
    if not isinstance(domains, dict):
        return RoutingDecision(domain, task_type, primary, secondary, reviewer, rationale)

    dom = domains.get(domain, {})
    if not isinstance(dom, dict):
        return RoutingDecision(domain, task_type, primary, secondary, reviewer, rationale)

    suggested_primary = dom.get("primary_suggested")
    suggested_secondary = dom.get("secondary_suggested")

    rationale = {
        "source": "telemetry+canonical",
        "suggested_primary": suggested_primary,
        "suggested_secondary": suggested_secondary,
    }

    if isinstance(suggested_primary, str) and suggested_primary:
        sp_stats = _get_agent_stats(telemetry, suggested_primary)
        if _is_stable(sp_stats):
            primary = suggested_primary
            rationale["primary_reason"] = "telemetry_primary_stable"
        else:
            rationale["primary_reason"] = "telemetry_primary_low_data_fallback_canonical"
    else:
        rationale["primary_reason"] = "no_telemetry_primary_fallback_canonical"

    if isinstance(suggested_secondary, str) and suggested_secondary:
        ss_stats = _get_agent_stats(telemetry, suggested_secondary)
        if _is_stable(ss_stats):
            secondary = suggested_secondary
            rationale["secondary_reason"] = "telemetry_secondary_stable"
        else:
            rationale["secondary_reason"] = "telemetry_secondary_low_data_fallback_canonical"
    else:
        rationale["secondary_reason"] = "fallback_canonical"

    p_stats = _get_agent_stats(telemetry, primary)
    p_avg = _avg_score(p_stats)
    p_rewrite = _rewrite_rate(p_stats)
    p_stable = _is_stable(p_stats)

    rationale["primary_stats"] = {
        "avg_score": p_avg,
        "rewrite_rate": round(p_rewrite, 4),
        "stability": p_stats.get("stability"),
    }

    escalate = False
    if domain == "safety":
        escalate = True
        reviewer = "philosophy-agent"
        rationale["reviewer_reason"] = "domain_safety_forced_philosophy_review"
    elif p_stable and p_avg < 0.70:
        escalate = True
        rationale["reviewer_reason"] = "primary_avg_score_low"
    elif p_stable and p_rewrite > 0.25:
        escalate = True
        rationale["reviewer_reason"] = "primary_rewrite_rate_high"
    else:
        rationale["reviewer_reason"] = "canonical_reviewer"

    if escalate and domain != "safety":
        if domain == "backend":
            reviewer = "architecture-specialist"
        elif domain in ("ai", "ml"):
            reviewer = "rag-systems-agent"
        else:
            reviewer = "agent-coordinator"

    return RoutingDecision(domain, task_type, primary, secondary, reviewer, rationale)


def main() -> int:
    ap = argparse.ArgumentParser(prog="route_with_telemetry")
    ap.add_argument("--domain", required=True)
    ap.add_argument("--task-type", required=True)
    ap.add_argument("--telemetry", default=str(TELEMETRY_PATH))
    args = ap.parse_args()

    routing = load_routing_graph()
    telemetry = _read_json(Path(args.telemetry))
    decision = route(args.domain, args.task_type, telemetry=telemetry, routing=routing)

    print(
        json.dumps(
            {
                "domain": decision.domain,
                "task_type": decision.task_type,
                "primary": decision.primary,
                "secondary": decision.secondary,
                "reviewer": decision.reviewer,
                "rationale": decision.rationale,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

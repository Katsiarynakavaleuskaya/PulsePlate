#!/usr/bin/env python3
"""Aggregate agent_run_summary artifacts into orchestration reliability scores.

Advisory only: no auto-routing writes, no CI blocking.
Output: artifacts/orchestration/telemetry_rollup.json (gitignored).

Usage:
    python scripts/orchestration/telemetry_rollup.py [--runs-dir DIR] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "artifacts" / "agent_runs"
OUT_DIR = REPO_ROOT / "artifacts" / "orchestration"
OUT_PATH = OUT_DIR / "telemetry_rollup.json"

SEVERITY_PENALTY = {"LOW": 0.05, "MEDIUM": 0.15, "HIGH": 0.35, "BLOCKER": 1.0}
DECISION_PENALTY = {"PASS": 0.0, "REWRITE_REQUIRED": 0.4}
MIN_RUNS_FOR_STABLE = 5


@dataclass(frozen=True)
class RunSignal:
    """Extracted signal from one agent run summary JSON."""

    schema_version: str
    agent: str
    domain: str
    cluster: str
    task_type: str
    run_phase: str
    decision: str
    max_severity: str
    blocker_count: int
    issues_count: int
    static_fail: bool
    handoff_count: int
    sync_points: int
    duration_ms: int
    gate_status: str
    retries: int
    outcome: str


def _iter_json_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.json") if p.is_file())


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _max_severity(issues: list[dict[str, Any]]) -> str:
    order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "BLOCKER": 4}
    max_sev = "LOW"
    for it in issues:
        sev = str(it.get("severity", "LOW"))
        if sev in order and order[sev] > order[max_sev]:
            max_sev = sev
    return max_sev


def _extract_signal(payload: dict[str, Any]) -> RunSignal | None:
    agent = str(payload.get("agent", "")).strip()
    domain = str(payload.get("domain", "")).strip()
    task_type = str(payload.get("task_type", "")).strip()
    cluster = str(payload.get("cluster", "ops")).strip() or "ops"
    run_phase = str(payload.get("run_phase", "execute")).strip() or "execute"
    decision = str(payload.get("decision", {}).get("action", "")).strip()

    if not agent or not domain or not task_type or decision not in DECISION_PENALTY:
        return None

    pv = payload.get("philosophy_validator", {}) or {}
    issues = pv.get("issues", []) or []
    if not isinstance(issues, list):
        issues = []

    max_sev = _max_severity([i for i in issues if isinstance(i, dict)])
    blocker_count = sum(1 for i in issues if isinstance(i, dict) and i.get("severity") == "BLOCKER")
    issues_count = sum(1 for i in issues if isinstance(i, dict))

    static_scans = payload.get("static_scans", {}) or {}
    static_fail = False
    for scan in static_scans.values():
        if isinstance(scan, dict) and scan.get("ok") is False:
            static_fail = True
            break

    return RunSignal(
        agent=agent,
        schema_version=str(payload.get("schema_version", "1.0")).strip() or "1.0",
        domain=domain,
        cluster=cluster,
        task_type=task_type,
        run_phase=run_phase,
        decision=decision,
        max_severity=max_sev,
        blocker_count=blocker_count,
        issues_count=issues_count,
        static_fail=static_fail,
        handoff_count=int(payload.get("handoff_count", 0) or 0),
        sync_points=int(payload.get("sync_points", 0) or 0),
        duration_ms=int(payload.get("duration_ms", 0) or 0),
        gate_status=str(payload.get("gate_status", "not_run")).strip() or "not_run",
        retries=int(payload.get("retries", 0) or 0),
        outcome=str(payload.get("outcome", "pass")).strip() or "pass",
    )


def _score_run(sig: RunSignal) -> float:
    """Return score in [0, 1] where 1 is best."""
    penalty = 0.0
    penalty += DECISION_PENALTY.get(sig.decision, 0.0)
    penalty += SEVERITY_PENALTY.get(sig.max_severity, 0.2)
    if sig.static_fail:
        penalty += 0.25
    if sig.blocker_count >= 2:
        penalty += 0.15
    if sig.outcome not in {"pass", "partial"}:
        penalty += 0.25
    if sig.gate_status not in {"pass", "not_run"}:
        penalty += 0.2
    penalty += min(sig.retries * 0.05, 0.2)
    penalty += min(sig.handoff_count * 0.02, 0.1)
    if sig.duration_ms > 0:
        penalty += min(sig.duration_ms / 600000.0, 0.1)
    penalty = min(1.0, penalty)
    return max(0.0, 1.0 - penalty)


def _aggregate(signals: list[RunSignal]) -> dict[str, Any]:
    per_agent_scores: dict[str, list[float]] = defaultdict(list)
    per_agent_meta: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_domain_agent_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    per_cluster_agent_scores: dict[tuple[str, str], list[float]] = defaultdict(list)

    for s in signals:
        sc = _score_run(s)
        per_agent_scores[s.agent].append(sc)
        per_domain_agent_scores[(s.domain, s.agent)].append(sc)
        per_cluster_agent_scores[(s.cluster, s.agent)].append(sc)

        per_agent_meta[s.agent]["runs"] += 1
        per_agent_meta[s.agent][f"decision_{s.decision}"] += 1
        per_agent_meta[s.agent][f"maxsev_{s.max_severity}"] += 1
        per_agent_meta[s.agent][f"phase_{s.run_phase}"] += 1
        per_agent_meta[s.agent][f"outcome_{s.outcome}"] += 1
        per_agent_meta[s.agent][f"gate_{s.gate_status}"] += 1
        per_agent_meta[s.agent]["handoff_total"] += s.handoff_count
        per_agent_meta[s.agent]["sync_points_total"] += s.sync_points
        per_agent_meta[s.agent]["duration_ms_total"] += s.duration_ms
        per_agent_meta[s.agent]["retries_total"] += s.retries
        if s.static_fail:
            per_agent_meta[s.agent]["static_fail"] += 1
        if s.blocker_count:
            per_agent_meta[s.agent]["blocker_runs"] += 1

    def mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 4) if xs else 0.0

    agent_table: dict[str, Any] = {}
    for agent, scores in per_agent_scores.items():
        avg = mean(scores)
        runs = per_agent_meta[agent]["runs"]
        stability = "STABLE" if runs >= MIN_RUNS_FOR_STABLE else "LOW_DATA"
        weight = 0.5 + avg
        weight = round(max(0.5, min(1.5, weight)), 3)

        agent_table[agent] = {
            "avg_score": avg,
            "weight": weight,
            "stability": stability,
            "avg_duration_ms": (
                round(per_agent_meta[agent]["duration_ms_total"] / runs, 2) if runs else 0.0
            ),
            "avg_handoffs": (
                round(per_agent_meta[agent]["handoff_total"] / runs, 2) if runs else 0.0
            ),
            "meta": dict(per_agent_meta[agent]),
        }

    domain_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (domain, agent), scores in per_domain_agent_scores.items():
        domain_map[domain].append({"agent": agent, "avg_score": mean(scores), "runs": len(scores)})

    for rows in domain_map.values():
        rows.sort(key=lambda r: (r["avg_score"], r["runs"]), reverse=True)

    recommendations: dict[str, Any] = {}
    for domain, rows in domain_map.items():
        stable = [r for r in rows if r["runs"] >= MIN_RUNS_FOR_STABLE]
        pool = stable if stable else rows

        primary = pool[0]["agent"] if pool else None
        secondary = pool[1]["agent"] if len(pool) >= 2 else None

        recommendations[domain] = {
            "primary_suggested": primary,
            "secondary_suggested": secondary,
            "ranked": rows[:5],
        }

    cluster_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (cluster, agent), scores in per_cluster_agent_scores.items():
        cluster_map[cluster].append(
            {"agent": agent, "avg_score": mean(scores), "runs": len(scores)}
        )
    for rows in cluster_map.values():
        rows.sort(key=lambda r: (r["avg_score"], r["runs"]), reverse=True)

    return {
        "schema_version": "2.0",
        "signals_count": len(signals),
        "agents": agent_table,
        "domains": recommendations,
        "clusters": dict(cluster_map),
    }


def build_rollup(runs_dir: Path) -> dict[str, Any]:
    signals: list[RunSignal] = []
    for p in _iter_json_files(runs_dir):
        payload = _safe_read_json(p)
        if not payload:
            continue
        sig = _extract_signal(payload)
        if sig:
            signals.append(sig)

    rollup = _aggregate(signals)
    try:
        rel = runs_dir.resolve().relative_to(REPO_ROOT)
        rollup["runs_dir"] = rel.as_posix()
    except ValueError:
        rollup["runs_dir"] = str(runs_dir)
    return rollup


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="telemetry_rollup",
        description="Aggregate agent_run_summary artifacts into reliability scores and routing recommendations.",
    )
    ap.add_argument(
        "--runs-dir",
        type=str,
        default=str(RUNS_DIR),
        help="Directory containing agent run summary JSON artifacts.",
    )
    ap.add_argument(
        "--output",
        type=str,
        default=str(OUT_PATH),
        help="Output JSON path.",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    runs_dir = Path(args.runs_dir)
    out_path = Path(args.output)

    rollup = build_rollup(runs_dir)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(rollup, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

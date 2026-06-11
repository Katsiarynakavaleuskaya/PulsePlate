#!/usr/bin/env python3
"""Aggregate local creative research adoption metrics.

Manual local-only eval -> promotion metrics with no runtime side effects.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any

RUNNER_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(RUNNER_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNNER_REPO_ROOT))

from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
from scripts.orchestration.creative_research_eval_contract import (
    OUTPUT_CLASSES,
    PROMOTION_DECISIONS,
    SCHEMA_VERSION as CREATIVE_RESEARCH_SCHEMA_VERSION,
    TASK_CLASS,
    VALID_PHASES,
)
from scripts.orchestration.experiment_contract import PROMOTION_TARGETS

REPORT_SCHEMA_VERSION = "creative-research-metrics-v1"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "orchestration"
EVALS_DIR = ARTIFACT_ROOT / "creative_research" / "evals"
PROMOTIONS_DIR = ARTIFACT_ROOT / "experiments" / "promotions"
METRICS_DIR = ARTIFACT_ROOT / "creative_research" / "metrics"
DEFAULT_OUTPUT_JSON = METRICS_DIR / "latest.json"
DEFAULT_OUTPUT_MD = METRICS_DIR / "latest.md"

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_CONTROL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_DESTINATION_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,255}$")
DESTINATION_REF_PREFIX_BY_TARGET = {
    "pr_packet": ("docs/orchestration/experiment_pr_packets/",),
    "audit_artifact": ("docs/audit/",),
    "guard_test_proposal": ("docs/orchestration/experiment_guard_proposals/",),
    "memory_capsule": ("docs/memory/",),
}
DESTINATION_REF_EXACT_BY_TARGET = {"backlog_entry": frozenset({"docs/roadmap/BACKLOG_LEDGER.md"})}
CREATIVE_RESEARCH_ORIGIN_KEYS = frozenset({"bundle_id", "candidate_id", "promotion_decision"})


class CreativeResearchMetricsError(RuntimeError):
    """Raised when local metrics inputs or paths violate the report contract."""


@dataclass(frozen=True)
class EvalCandidateSignal:
    """Sanitized candidate-level signal from one evaluated bundle."""

    bundle_id: str
    candidate_id: str
    phase: str
    output_class: str
    promotion_decision: str
    negative_controls: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str]:
        return (self.bundle_id, self.candidate_id)


@dataclass(frozen=True)
class PromotionOriginSignal:
    """Sanitized optional creative-research origin from a promotion artifact."""

    bundle_id: str
    candidate_id: str
    promotion_decision: str
    promotion_target: str
    durable_artifact_path: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.bundle_id, self.candidate_id)


def _artifact_root() -> Path:
    return Path(ARTIFACT_ROOT).resolve()


def _path_label(path: Path) -> str:
    try:
        return str(normalize_repo_path(path))
    except ValueError:
        return path.name


def _reject_symlinked_path(candidate: Path, *, anchor: Path, label: str) -> Path:
    """Fail closed if candidate or an ancestor under anchor is a symlink."""

    resolved_anchor = Path(anchor).resolve()
    absolute_candidate = candidate if candidate.is_absolute() else Path(REPO_ROOT) / candidate
    for part in [absolute_candidate, *absolute_candidate.parents]:
        if part == resolved_anchor or part == anchor:
            break
        if part.is_symlink():
            raise CreativeResearchMetricsError(f"{label} must not traverse symlinks.")
    resolved_candidate = Path(absolute_candidate).resolve()
    try:
        resolved_candidate.relative_to(resolved_anchor)
    except ValueError as exc:
        raise CreativeResearchMetricsError(
            f"{label} must stay within {_path_label(resolved_anchor)}."
        ) from exc
    return Path(resolved_candidate)


def _resolve_input_dir(raw_path: str | None, *, default: Path, label: str) -> Path:
    if raw_path is None:
        candidate = default
    else:
        raw_candidate = Path(raw_path).expanduser()
        if raw_candidate.is_absolute():
            candidate = raw_candidate
        else:
            repo_candidate = REPO_ROOT / raw_candidate
            try:
                repo_candidate.resolve().relative_to(_artifact_root())
                candidate = repo_candidate
            except ValueError:
                candidate = default / raw_candidate
    return _reject_symlinked_path(candidate, anchor=_artifact_root(), label=label)


def _resolve_output_path(raw_path: str | None, *, default: Path, label: str) -> Path:
    if raw_path is None:
        candidate = default
    else:
        raw_candidate = Path(raw_path).expanduser()
        if raw_candidate.is_absolute():
            candidate = raw_candidate
        else:
            repo_candidate = REPO_ROOT / raw_candidate
            try:
                repo_candidate.resolve().relative_to(METRICS_DIR.resolve())
                candidate = repo_candidate
            except ValueError:
                candidate = METRICS_DIR / raw_candidate
    return _reject_symlinked_path(candidate, anchor=METRICS_DIR.resolve(), label=label)


def _iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def _relative_artifact_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _read_json_artifact(
    path: Path,
    *,
    root: Path,
    category: str,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    file_ref = _relative_artifact_path(path, root)
    try:
        _reject_symlinked_path(path, anchor=_artifact_root(), label=f"{category} artifact")
    except CreativeResearchMetricsError:
        return None, {"category": category, "file": file_ref, "reason": "symlink_path"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, {"category": category, "file": file_ref, "reason": "malformed_json"}
    except (OSError, UnicodeDecodeError):
        return None, {"category": category, "file": file_ref, "reason": "unreadable_json"}
    if not isinstance(payload, dict):
        return None, {"category": category, "file": file_ref, "reason": "non_object_json"}
    return payload, None


def _safe_identifier(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise CreativeResearchMetricsError(f"{field} must be a string.")
    normalized = value.strip()
    if not SAFE_ID_RE.fullmatch(normalized):
        raise CreativeResearchMetricsError(f"{field} must be a safe local identifier.")
    return normalized


def _safe_count(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise CreativeResearchMetricsError(f"{field} must be a non-negative integer.")
    return value


def _safe_controls(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CreativeResearchMetricsError("negative_controls_triggered must be a list.")
    controls: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise CreativeResearchMetricsError(
                "negative_controls_triggered entries must be strings."
            )
        normalized = item.strip()
        if not normalized:
            continue
        if not SAFE_CONTROL_RE.fullmatch(normalized):
            raise CreativeResearchMetricsError(
                "negative_controls_triggered entries must be safe identifiers."
            )
        controls.add(normalized)
    return tuple(sorted(controls))


def _safe_phase(value: object) -> str:
    phase = _safe_identifier(value, field="phase")
    if phase not in VALID_PHASES:
        raise CreativeResearchMetricsError("phase is not recognized.")
    return phase


def _safe_promotion_target(value: object) -> str:
    if not isinstance(value, str):
        raise CreativeResearchMetricsError("promotion_target must be a string.")
    target = value.strip()
    if target not in PROMOTION_TARGETS:
        raise CreativeResearchMetricsError("promotion_target is not recognized.")
    return target


def _safe_destination_ref(value: object, *, target: str) -> str:
    if not isinstance(value, str):
        raise CreativeResearchMetricsError("durable_artifact_path must be a string.")
    ref = value.strip()
    if not ref or Path(ref).is_absolute() or ".." in Path(ref).parts:
        raise CreativeResearchMetricsError("durable_artifact_path must be repo-relative.")
    if not SAFE_DESTINATION_REF_RE.fullmatch(ref):
        raise CreativeResearchMetricsError("durable_artifact_path must be a safe repo ref.")
    exact_refs = DESTINATION_REF_EXACT_BY_TARGET.get(target, frozenset())
    allowed_prefixes = DESTINATION_REF_PREFIX_BY_TARGET.get(target, ())
    if ref not in exact_refs and not ref.startswith(allowed_prefixes):
        raise CreativeResearchMetricsError("durable_artifact_path uses an unsupported repo ref.")
    return ref


def _extract_eval_candidates(
    payload: dict[str, Any],
) -> tuple[list[EvalCandidateSignal], bool]:
    if (
        payload.get("schema_version") != CREATIVE_RESEARCH_SCHEMA_VERSION
        or payload.get("task_class") != TASK_CLASS
    ):
        raise CreativeResearchMetricsError("artifact is not a creative research eval result.")
    bundle_id = _safe_identifier(payload.get("bundle_id"), field="bundle_id")
    phase = _safe_phase(payload.get("phase"))
    candidates_raw = payload.get("candidates")
    if not isinstance(candidates_raw, list):
        raise CreativeResearchMetricsError("candidates must be a list.")
    if not candidates_raw:
        raise CreativeResearchMetricsError("candidates must not be empty.")

    summary_raw = payload.get("summary")
    if not isinstance(summary_raw, dict):
        raise CreativeResearchMetricsError("summary must be an object.")
    summary = {
        "candidate_count": _safe_count(
            summary_raw.get("candidate_count"), field="summary.candidate_count"
        ),
        "promote": _safe_count(summary_raw.get("promote"), field="summary.promote"),
        "defer": _safe_count(summary_raw.get("defer"), field="summary.defer"),
        "discard": _safe_count(summary_raw.get("discard"), field="summary.discard"),
    }

    candidate_ids: set[str] = set()
    candidates: list[EvalCandidateSignal] = []
    decision_counts = {decision: 0 for decision in PROMOTION_DECISIONS}
    for candidate_raw in candidates_raw:
        if not isinstance(candidate_raw, dict):
            raise CreativeResearchMetricsError("candidate entries must be objects.")
        candidate_id = _safe_identifier(candidate_raw.get("candidate_id"), field="candidate_id")
        if candidate_id in candidate_ids:
            raise CreativeResearchMetricsError("duplicate candidate_id in eval artifact.")
        candidate_ids.add(candidate_id)
        output_class = _safe_identifier(candidate_raw.get("output_class"), field="output_class")
        if output_class not in OUTPUT_CLASSES:
            raise CreativeResearchMetricsError("output_class is not recognized.")
        promotion_decision = _safe_identifier(
            candidate_raw.get("promotion_decision"), field="promotion_decision"
        )
        if promotion_decision not in PROMOTION_DECISIONS:
            raise CreativeResearchMetricsError("promotion_decision is not recognized.")
        decision_counts[promotion_decision] += 1
        candidates.append(
            EvalCandidateSignal(
                bundle_id=bundle_id,
                candidate_id=candidate_id,
                phase=phase,
                output_class=output_class,
                promotion_decision=promotion_decision,
                negative_controls=_safe_controls(
                    candidate_raw.get("negative_controls_triggered", [])
                ),
            )
        )

    summary_mismatch = (
        summary["candidate_count"] != len(candidates)
        or summary["promote"] != decision_counts["promote"]
        or summary["defer"] != decision_counts["defer"]
        or summary["discard"] != decision_counts["discard"]
    )
    return candidates, summary_mismatch


def _extract_origin_signal(payload: dict[str, Any]) -> PromotionOriginSignal | None:
    target = _safe_promotion_target(payload.get("promotion_target"))
    destination_ref = _safe_destination_ref(payload.get("durable_artifact_path"), target=target)
    origin = payload.get("creative_research_origin")
    if origin is None:
        return None
    if not isinstance(origin, dict):
        raise CreativeResearchMetricsError("creative_research_origin must be an object.")
    if set(origin) != CREATIVE_RESEARCH_ORIGIN_KEYS:
        raise CreativeResearchMetricsError("creative_research_origin has unsupported fields.")
    promotion_decision = _safe_identifier(
        origin.get("promotion_decision"), field="creative_research_origin.promotion_decision"
    )
    if promotion_decision not in PROMOTION_DECISIONS:
        raise CreativeResearchMetricsError(
            "creative_research_origin.promotion_decision is not recognized."
        )
    return PromotionOriginSignal(
        bundle_id=_safe_identifier(
            origin.get("bundle_id"), field="creative_research_origin.bundle_id"
        ),
        candidate_id=_safe_identifier(
            origin.get("candidate_id"), field="creative_research_origin.candidate_id"
        ),
        promotion_decision=promotion_decision,
        promotion_target=target,
        durable_artifact_path=destination_ref,
    )


def build_metrics_report(
    evals_dir: Path = EVALS_DIR, promotions_dir: Path = PROMOTIONS_DIR
) -> dict[str, Any]:
    """Build a sanitized metrics report from local eval and promotion artifacts."""

    skipped: list[dict[str, str]] = []
    candidate_signals: dict[tuple[str, str], EvalCandidateSignal] = {}
    loaded_bundle_ids: set[str] = set()
    eval_seen = 0
    eval_loaded = 0
    summary_mismatch_count = 0

    for path in _iter_json_files(evals_dir):
        eval_seen += 1
        payload, skip = _read_json_artifact(path, root=evals_dir, category="eval")
        if skip is not None:
            skipped.append(skip)
            continue
        if payload is None:
            continue
        try:
            candidates, summary_mismatch = _extract_eval_candidates(payload)
        except CreativeResearchMetricsError as exc:
            skipped.append(
                {
                    "category": "eval",
                    "file": _relative_artifact_path(path, evals_dir),
                    "reason": str(exc),
                }
            )
            continue
        bundle_id = candidates[0].bundle_id if candidates else ""
        if bundle_id in loaded_bundle_ids:
            skipped.append(
                {
                    "category": "eval",
                    "file": _relative_artifact_path(path, evals_dir),
                    "reason": "duplicate_bundle_id",
                }
            )
            continue
        loaded_bundle_ids.add(bundle_id)
        eval_loaded += 1
        if summary_mismatch:
            summary_mismatch_count += 1
        for signal in candidates:
            candidate_signals[signal.key] = signal

    promotion_seen = 0
    promotion_loaded = 0
    destination_counts: Counter[str] = Counter()
    destination_ref_counts: Counter[str] = Counter()
    origin_destination_counts: Counter[str] = Counter()
    origin_destination_ref_counts: Counter[str] = Counter()
    linked_promotion_count = 0
    origin_mismatch_count = 0
    duplicate_origin_link_count = 0
    linked_candidate_keys: set[tuple[str, str]] = set()

    for path in _iter_json_files(promotions_dir):
        promotion_seen += 1
        payload, skip = _read_json_artifact(path, root=promotions_dir, category="promotion")
        if skip is not None:
            skipped.append(skip)
            continue
        if payload is None:
            continue
        try:
            origin = _extract_origin_signal(payload)
            target = _safe_promotion_target(payload.get("promotion_target"))
            destination_ref = _safe_destination_ref(
                payload.get("durable_artifact_path"), target=target
            )
        except CreativeResearchMetricsError as exc:
            skipped.append(
                {
                    "category": "promotion",
                    "file": _relative_artifact_path(path, promotions_dir),
                    "reason": str(exc),
                }
            )
            continue
        promotion_loaded += 1
        destination_counts[target] += 1
        destination_ref_counts[f"{target}:{destination_ref}"] += 1
        if origin is None:
            continue
        candidate = candidate_signals.get(origin.key)
        if candidate is None or candidate.promotion_decision != origin.promotion_decision:
            origin_mismatch_count += 1
            continue
        linked_promotion_count += 1
        origin_destination_counts[origin.promotion_target] += 1
        origin_destination_ref_counts[
            f"{origin.promotion_target}:{origin.durable_artifact_path}"
        ] += 1
        if origin.key in linked_candidate_keys:
            duplicate_origin_link_count += 1
        linked_candidate_keys.add(origin.key)

    decision_counts: Counter[str] = Counter()
    output_class_counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    negative_control_counts: Counter[str] = Counter()
    negative_control_candidate_count = 0
    for signal in candidate_signals.values():
        decision_counts[signal.promotion_decision] += 1
        output_class_counts[signal.output_class] += 1
        phase_counts[signal.phase] += 1
        if signal.negative_controls:
            negative_control_candidate_count += 1
        for control in signal.negative_controls:
            negative_control_counts[control] += 1

    promoted_keys = {
        key for key, signal in candidate_signals.items() if signal.promotion_decision == "promote"
    }
    missing_conversion_links = [
        {"bundle_id": bundle_id, "candidate_id": candidate_id}
        for bundle_id, candidate_id in sorted(promoted_keys - linked_candidate_keys)
    ]

    status = "empty" if eval_seen == 0 and promotion_seen == 0 else "ok"
    if eval_seen > 0 and not candidate_signals:
        status = "no_valid_eval_artifacts"

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": status,
        "sources": {
            "eval_artifacts_seen": eval_seen,
            "eval_artifacts_loaded": eval_loaded,
            "eval_artifacts_skipped": eval_seen - eval_loaded,
            "promotion_artifacts_seen": promotion_seen,
            "promotion_artifacts_loaded": promotion_loaded,
            "promotion_artifacts_skipped": promotion_seen - promotion_loaded,
            "summary_mismatch_count": summary_mismatch_count,
            "skipped_artifacts": sorted(
                skipped,
                key=lambda item: (item["category"], item["file"], item["reason"]),
            ),
        },
        "candidate_totals": {
            "bundle_count": len(loaded_bundle_ids),
            "candidate_count": len(candidate_signals),
            "by_decision": {
                decision: decision_counts.get(decision, 0) for decision in PROMOTION_DECISIONS
            },
            "by_output_class": {
                output_class: output_class_counts.get(output_class, 0)
                for output_class in OUTPUT_CLASSES
            },
            "by_phase": dict(sorted(phase_counts.items())),
        },
        "negative_controls": {
            "candidate_count": negative_control_candidate_count,
            "counts": dict(sorted(negative_control_counts.items())),
        },
        "conversion": {
            "promoted_candidate_count": len(promoted_keys),
            "linked_promotion_count": linked_promotion_count,
            "linked_candidate_count": len(linked_candidate_keys),
            "missing_conversion_link_count": len(missing_conversion_links),
            "missing_conversion_links": missing_conversion_links,
            "origin_mismatch_count": origin_mismatch_count,
            "duplicate_origin_link_count": duplicate_origin_link_count,
            "destination_counts": dict(sorted(destination_counts.items())),
            "destination_ref_counts": dict(sorted(destination_ref_counts.items())),
            "origin_destination_counts": dict(sorted(origin_destination_counts.items())),
            "origin_destination_ref_counts": dict(sorted(origin_destination_ref_counts.items())),
        },
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    """Render a compact operator-readable Markdown report from sanitized metrics."""

    sources = report["sources"]
    totals = report["candidate_totals"]
    conversion = report["conversion"]
    negative_controls = report["negative_controls"]
    lines = [
        "# Creative Research Adoption Metrics",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Status: `{report['status']}`",
        f"- Eval artifacts loaded: `{sources['eval_artifacts_loaded']}` of `{sources['eval_artifacts_seen']}`",
        f"- Promotion artifacts loaded: `{sources['promotion_artifacts_loaded']}` of `{sources['promotion_artifacts_seen']}`",
        f"- Bundles: `{totals['bundle_count']}`",
        f"- Candidates: `{totals['candidate_count']}`",
        f"- Promoted candidates: `{conversion['promoted_candidate_count']}`",
        f"- Linked promotions: `{conversion['linked_promotion_count']}`",
        f"- Missing conversion links: `{conversion['missing_conversion_link_count']}`",
        "",
        "## Decision Counts",
        "",
    ]
    for decision, count in totals["by_decision"].items():
        lines.append(f"- `{decision}`: `{count}`")
    lines.extend(["", "## Output Classes", ""])
    for output_class, count in totals["by_output_class"].items():
        lines.append(f"- `{output_class}`: `{count}`")
    lines.extend(["", "## Negative Controls", ""])
    lines.append(f"- Candidates with negative controls: `{negative_controls['candidate_count']}`")
    if negative_controls["counts"]:
        for control, count in negative_controls["counts"].items():
            lines.append(f"- `{control}`: `{count}`")
    else:
        lines.append("- None observed.")
    lines.extend(["", "## Destination Counts", ""])
    if conversion["destination_counts"]:
        for destination, count in conversion["destination_counts"].items():
            lines.append(f"- `{destination}`: `{count}`")
    else:
        lines.append("- None observed.")
    lines.extend(["", "## Destination Refs", ""])
    if conversion["destination_ref_counts"]:
        for destination, count in conversion["destination_ref_counts"].items():
            lines.append(f"- `{destination}`: `{count}`")
    else:
        lines.append("- None observed.")
    lines.extend(["", "## Missing Conversion Links", ""])
    if conversion["missing_conversion_links"]:
        for row in conversion["missing_conversion_links"]:
            lines.append(f"- `{row['bundle_id']}` / `{row['candidate_id']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Skipped Artifacts", ""])
    if sources["skipped_artifacts"]:
        for item in sources["skipped_artifacts"]:
            lines.append(f"- `{item['category']}` `{item['file']}`: `{item['reason']}`")
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def _write_report(output_json: Path, output_md: Path, report: dict[str, Any]) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(render_markdown_report(report), encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate local creative_research eval and promotion adoption metrics."
    )
    parser.add_argument(
        "--evals-dir",
        default=None,
        help="Eval artifact directory under artifacts/orchestration/creative_research/evals/.",
    )
    parser.add_argument(
        "--promotions-dir",
        default=None,
        help="Promotion artifact directory under artifacts/orchestration/experiments/promotions/.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Output JSON path under artifacts/orchestration/creative_research/metrics/.",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Output Markdown path under artifacts/orchestration/creative_research/metrics/.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        evals_dir = _resolve_input_dir(args.evals_dir, default=EVALS_DIR, label="--evals-dir")
        promotions_dir = _resolve_input_dir(
            args.promotions_dir,
            default=PROMOTIONS_DIR,
            label="--promotions-dir",
        )
        output_json = _resolve_output_path(
            args.output_json,
            default=DEFAULT_OUTPUT_JSON,
            label="--output-json",
        )
        output_md = _resolve_output_path(
            args.output_md,
            default=DEFAULT_OUTPUT_MD,
            label="--output-md",
        )
        report = build_metrics_report(evals_dir=evals_dir, promotions_dir=promotions_dir)
        _write_report(output_json, output_md, report)
    except (CreativeResearchMetricsError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "schema_version": report["schema_version"],
                "status": report["status"],
                "output_json": normalize_repo_path(output_json),
                "output_md": normalize_repo_path(output_md),
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

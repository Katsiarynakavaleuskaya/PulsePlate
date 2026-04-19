#!/usr/bin/env python3
"""Deterministic offline eval runner for FitChef judgment replay packs.

RU: Читает replay pack, считает deterministic decision artifact и пишет результат.
EN: Reads a replay pack, computes deterministic decision artifacts, and writes the result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

RUNNER_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(RUNNER_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNNER_REPO_ROOT))

from scripts.orchestration.context_pack import REPO_ROOT
from scripts.orchestration.judgment_eval_contract import (
    evaluate_fitchef_replay_pack,
    validate_fitchef_replay_pack,
)

RESULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "orchestration" / "judgment" / "evals"
PROMOTION_DECISIONS = frozenset({"promote", "defer", "discard"})


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load FitChef judgment replay JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("FitChef judgment replay pack must be a JSON object.")
    return payload


def _resolve_output_path(raw_output: str | None, bundle_id: str) -> Path:
    """Keep offline-eval artifacts scoped under the dedicated artifacts tree."""

    if raw_output:
        candidate = Path(raw_output)
        if not candidate.is_absolute():
            candidate = RESULT_ARTIFACT_DIR / candidate
    else:
        candidate = RESULT_ARTIFACT_DIR / f"{bundle_id}.json"
    candidate = candidate.resolve()
    try:
        candidate.relative_to(RESULT_ARTIFACT_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "--output must stay within artifacts/orchestration/judgment/evals"
        ) from exc
    return candidate


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic FitChef judgment replay bundles."
    )
    parser.add_argument("--input", required=True, help="Path to the replay-pack JSON.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional artifact path under artifacts/orchestration/judgment/evals/.",
    )
    return parser


def _build_summary(results: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"promote": 0, "defer": 0, "discard": 0, "hard_fail": 0}
    for result in results:
        decision = str(result.get("decision", "")).strip().lower()
        if decision not in PROMOTION_DECISIONS:
            raise ValueError(f"Unexpected decision in replay result: {decision!r}")
        summary[decision] += 1
        if result.get("hard_fail_reasons"):
            summary["hard_fail"] += 1
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        raw_pack = _read_json_object(Path(args.input))
        pack = validate_fitchef_replay_pack(raw_pack)
        results = evaluate_fitchef_replay_pack(raw_pack)
        artifact = {
            "bundle_id": pack["bundle_id"],
            "schema_version": pack["schema_version"],
            "mode": pack["mode"],
            "task_class": pack["task_class"],
            "scenario_family": pack["scenario_family"],
            "summary": _build_summary(results),
            "results": results,
        }
        output_path = _resolve_output_path(args.output, pack["bundle_id"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

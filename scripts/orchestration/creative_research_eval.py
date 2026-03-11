#!/usr/bin/env python3
"""Deterministic offline eval runner for creative research candidate bundles.

RU: Читает creative_research bundle, считает deterministic scorecard и пишет artifact.
EN: Reads a creative_research bundle, computes a deterministic scorecard, and writes an artifact.
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
from scripts.orchestration.creative_research_eval_contract import (
    evaluate_bundle,
    validate_bundle,
)

RESULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "orchestration" / "creative_research" / "evals"


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load creative research bundle JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Creative research bundle must be a JSON object.")
    return payload


def _resolve_output_path(raw_output: str | None, bundle_id: str) -> Path:
    """RU: Ограничивает output artifacts/ директориями. EN: Keep outputs under artifacts/."""

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
            "--output must stay within artifacts/orchestration/creative_research/evals"
        ) from exc
    return candidate


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic creative research offline bundles."
    )
    parser.add_argument("--input", required=True, help="Path to the creative research bundle JSON.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional artifact path under artifacts/orchestration/creative_research/evals/.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        raw_bundle = _read_json_object(Path(args.input))
        bundle = validate_bundle(raw_bundle)
        result = evaluate_bundle(bundle)
        output_path = _resolve_output_path(args.output, bundle["bundle_id"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

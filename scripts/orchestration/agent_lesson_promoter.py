#!/usr/bin/env python3
"""Render non-mutating promotion proposals for agent learning records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.agent_learning_loop import build_learning_promotion_proposal

REQUIRED_RECORD_FIELDS = {
    "lesson_id",
    "source",
    "pattern",
    "severity",
    "affected_surfaces",
    "root_cause",
    "required_oracle",
    "promotion_target",
    "dedupe_fingerprint",
    "redaction_status",
    "human_review_required",
}


def _load_record(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("Invalid learning record: expected JSON object.")
    missing = sorted(REQUIRED_RECORD_FIELDS.difference(payload))
    if missing:
        raise SystemExit(f"Invalid learning record: missing fields {', '.join(missing)}.")
    return payload


def promote_agent_lesson_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a proposal object; never mutate repository policy by itself."""

    proposal: dict[str, Any] = build_learning_promotion_proposal(record)
    return proposal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a repo-review promotion proposal for one agent learning record."
    )
    parser.add_argument("--record", help="Path to an agent_learning_record.v1 JSON object.")
    args = parser.parse_args(argv)
    print(
        json.dumps(promote_agent_lesson_record(_load_record(args.record)), indent=2, sort_keys=True)
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by py_compile/CLI smoke gates.
    raise SystemExit(main())

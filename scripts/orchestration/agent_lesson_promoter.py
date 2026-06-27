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

from scripts.orchestration.agent_learning_loop import (
    build_learning_promotion_proposal,
    validate_agent_learning_record,
)


def _load_record(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object.")
    return validate_agent_learning_record(payload)


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
    try:
        proposal = promote_agent_lesson_record(_load_record(args.record))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Invalid learning record input: {exc}") from exc
    print(json.dumps(proposal, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by py_compile/CLI smoke gates.
    raise SystemExit(main())

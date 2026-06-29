#!/usr/bin/env python3
"""Extract proposal-only PulsePlate agent learning records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.agent_learning_loop import build_agent_learning_record


def extract_agent_lesson_record(
    *,
    source: str,
    pattern: str,
    severity: str,
    affected_surfaces: list[str],
    root_cause: str,
    required_oracle: str,
    promotion_target: str,
) -> dict[str, object]:
    """Return one redacted learning record without writing or promotion."""

    return cast(
        dict[str, object],
        build_agent_learning_record(
            source=source,
            pattern=pattern,
            severity=severity,
            affected_surfaces=affected_surfaces,
            root_cause=root_cause,
            required_oracle=required_oracle,
            promotion_target=promotion_target,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit one repo-governed agent learning record without side effects."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--severity", default="medium")
    parser.add_argument("--affected-surface", action="append", default=[])
    parser.add_argument("--root-cause", required=True)
    parser.add_argument("--required-oracle", required=True)
    parser.add_argument("--promotion-target", required=True)
    args = parser.parse_args(argv)
    try:
        payload = extract_agent_lesson_record(
            source=args.source,
            pattern=args.pattern,
            severity=args.severity,
            affected_surfaces=args.affected_surface,
            root_cause=args.root_cause,
            required_oracle=args.required_oracle,
            promotion_target=args.promotion_target,
        )
    except ValueError as exc:
        raise SystemExit(f"Invalid learning record input: {exc}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by py_compile/CLI smoke gates.
    raise SystemExit(main())

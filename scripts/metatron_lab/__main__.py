"""CLI: `python3 -m scripts.metatron_lab validate|checklist`."""

from __future__ import annotations

import argparse
import sys
from typing import cast

from scripts.metatron_lab.compose_guard import operator_checklist_lines, validate_all_profiles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m scripts.metatron_lab",
        description="METATRON out-of-band lab helpers (no product surface).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="Run `docker compose config -q` for all lab profiles.")
    sub.add_parser("checklist", help="Print operator checklist to stdout.")

    args = parser.parse_args(argv)
    if args.command == "validate":
        return cast(int, validate_all_profiles())
    if args.command == "checklist":
        for line in operator_checklist_lines():
            print(line)
        return 0
    raise RuntimeError(f"unhandled command: {args.command!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Compatibility wrapper for the legacy Python 3.12 main shard runner path."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.run_main_test_shards import main as run_main_test_shards


def main(argv: Sequence[str] | None = None) -> int:
    """Delegate to the shared main-suite shard runner with a py312 default."""

    args = list(sys.argv[1:] if argv is None else argv)
    if "--python-version" not in args and "--artifact-label" not in args:
        args = ["--python-version", "3.12", *args]
    return int(run_main_test_shards(args))


if __name__ == "__main__":
    raise SystemExit(main())

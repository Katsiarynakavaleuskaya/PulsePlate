#!/usr/bin/env python3
"""Runtime-agnostic PulsePlate role dispatch manifest CLI.

The implementation currently lives in ``qoder_dispatch_bridge.py`` for backward
compatibility with older packets and scripts. New task packets should use this
neutral entrypoint so the bridge is understood as a custom-role dispatch bridge,
not a Qoder-only adapter.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.qoder_dispatch_bridge import main

if __name__ == "__main__":
    raise SystemExit(main())

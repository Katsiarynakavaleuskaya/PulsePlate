"""Legacy quick quick-check shim.

This file restores the historical path `test_quick_check.py` that some CI / pre-commit
steps still invoke directly (pytest test_quick_check.py). The real quick tests now
live in `tests/quick/test_llm_quick_check.py`.

Keep this extremely fast and side‑effect free.
"""

from __future__ import annotations

import os


def test_quick_placeholder() -> None:
    """Always-pass placeholder so CI invocation succeeds instantly."""
    # Guarantee deterministic env for any downstream imports if added later.
    os.environ["LLM_PROVIDER"] = "none"


def test_quick_llm_import_smoke() -> None:
    """Lightweight import smoke for `llm.get_provider()` when provider=none.

    Avoids any network calls; just ensures module reload path works.
    """
    os.environ["LLM_PROVIDER"] = "none"
    import importlib  # local import to keep global import time minimal

    import llm

    m = importlib.reload(llm)
    # Placeholder assertion for shim module; expected None when provider=none
    assert m.get_provider() is None  # nosec B101

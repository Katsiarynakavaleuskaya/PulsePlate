from __future__ import annotations

import re
from pathlib import Path

from tests.feature_manifest import FEATURE_TODO_KEYS


def test_feature_manifest_keys_are_used_in_tests() -> None:
    """Ensure each feature-manifest key is referenced by require_feature in tests."""
    tests_root = Path(__file__).parent
    content_parts: list[str] = []
    for path in tests_root.rglob("*.py"):
        content_parts.append(path.read_text(encoding="utf-8"))
    content = "\n".join(content_parts)

    missing: list[str] = []
    for key in sorted(FEATURE_TODO_KEYS):
        direct_pattern = rf"require_feature\(\s*['\"]{re.escape(key)}['\"]"
        gated_pattern = rf"require_feature_or_raise\([^)]*['\"]{re.escape(key)}['\"]"
        if re.search(direct_pattern, content) is None and re.search(gated_pattern, content) is None:
            missing.append(key)

    assert not missing, f"Unused feature keys in feature_manifest: {missing}"

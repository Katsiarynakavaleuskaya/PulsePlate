from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.feature_manifest import (
    FEATURE_TODO_KEYS,
    FeatureManifest,
    require_feature,
    require_feature_or_raise,
)

SKIP_REASON_RE = re.compile(r"^feature_disabled:[a-z0-9_]+(?:\s.*)?$")


def test_feature_manifest_keys_are_used_in_tests() -> None:
    """Ensure each feature-manifest key is referenced by require_feature in tests."""
    tests_root = Path(__file__).parent
    content_parts = [path.read_text(encoding="utf-8") for path in tests_root.rglob("*.py")]
    content = "\n".join(content_parts)

    missing: list[str] = []
    for key in sorted(FEATURE_TODO_KEYS):
        direct_pattern = rf"require_feature\(\s*['\"]{re.escape(key)}['\"]"
        gated_pattern = rf"require_feature_or_raise\([^)]*['\"]{re.escape(key)}['\"]"
        if re.search(direct_pattern, content) is None and re.search(gated_pattern, content) is None:
            missing.append(key)

    assert not missing, f"Unused feature keys in feature_manifest: {missing}"


def test_require_feature_skip_reason_uses_canonical_prefix() -> None:
    """Require canonical feature_disabled:<key> skip reason prefix."""
    manifest = FeatureManifest(enabled=frozenset())
    with pytest.raises(pytest.skip.Exception, match=SKIP_REASON_RE.pattern) as exc_info:
        require_feature("planner_engines", reason="CP3 guard check", manifest=manifest)

    assert str(exc_info.value).startswith("feature_disabled:planner_engines")


def test_require_feature_or_raise_reraises_when_feature_enabled() -> None:
    """Enabled feature must re-raise ImportError (never skip silently)."""
    manifest = FeatureManifest(enabled=frozenset({"planner_engines"}))
    sentinel = ImportError("planner_engines import failed")

    with pytest.raises(ImportError, match="planner_engines import failed"):
        require_feature_or_raise(
            sentinel, "planner_engines", reason="CP3 guard check", manifest=manifest
        )


def test_require_feature_or_raise_skips_when_feature_disabled() -> None:
    """Disabled feature may skip with canonical reason."""
    manifest = FeatureManifest(enabled=frozenset())
    sentinel = ImportError("planner_engines import failed")

    with pytest.raises(pytest.skip.Exception, match=SKIP_REASON_RE.pattern) as exc_info:
        require_feature_or_raise(
            sentinel, "planner_engines", reason="CP3 guard check", manifest=manifest
        )

    assert str(exc_info.value).startswith("feature_disabled:planner_engines")

from __future__ import annotations

import re
from pathlib import Path

from tests.feature_manifest import FEATURE_TODO_KEYS

CP3_TARGET_FILES: tuple[str, ...] = (
    "test_zero_coverage_modules.py",
    "test_remaining_modules.py",
    "test_final_core_coverage.py",
    "test_direct_core_functions.py",
    "test_quick_coverage_boost.py",
)


def _read_target(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cp3_target_files_use_canonical_skip_protocol() -> None:
    """CP3 target suites must use feature-manifest skip protocol only."""
    tests_root = Path(__file__).parent
    missing_files: list[str] = []
    invalid_keys: list[str] = []

    key_pattern = re.compile(
        r"require_feature_or_raise\(\s*exc,\s*['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )

    for filename in CP3_TARGET_FILES:
        path = tests_root / filename
        if not path.exists():
            missing_files.append(filename)
            continue

        content = _read_target(path)
        assert (
            "from tests.feature_manifest import FEATURE_REASON, require_feature_or_raise" in content
        )
        assert "pytest.skip(" not in content
        assert "feature_disabled:" not in content
        assert "require_feature_or_raise(" in content

        for key in key_pattern.findall(content):
            if key not in FEATURE_TODO_KEYS:
                invalid_keys.append(f"{filename}:{key}")

    assert not missing_files, f"Missing CP3 target files: {missing_files}"
    assert not invalid_keys, f"Unknown feature-manifest keys in CP3 targets: {invalid_keys}"

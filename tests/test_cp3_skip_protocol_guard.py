"""CP3 guard: block newly added free-form skip/xfail patterns in tests."""

from __future__ import annotations

import os
import re
import subprocess

import pytest

FREE_FORM_SKIP_PATTERNS = (
    re.compile(r"\bpytest\.skip\("),
    re.compile(r"\bpytest\.xfail\("),
    re.compile(r"@pytest\.mark\.(?:skip|skipif|xfail)\b"),
)

ALLOWLIST_FILES = {
    "tests/feature_manifest.py",
    "tests/test_cp3_skip_protocol_guard.py",
}


def _diff_added_test_lines() -> list[tuple[str, int, str]]:
    """Return (file, line_no, content) for newly added lines in tests diff."""
    base_ref = os.getenv("CP3_GIT_BASE_REF", "origin/main")
    diff_args_candidates = [
        ["git", "diff", "--unified=0", "--no-color", f"{base_ref}...HEAD", "--", "tests"],
        ["git", "diff", "--unified=0", "--no-color", "HEAD~1..HEAD", "--", "tests"],
    ]
    diff: str | None = None
    last_error: Exception | None = None
    for args in diff_args_candidates:
        try:
            diff = subprocess.check_output(
                args,
                text=True,
                stderr=subprocess.STDOUT,
            )
            break
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            last_error = exc
    if diff is None:
        pytest.fail(f"CP3 skip guard failed: cannot read git diff ({last_error})")

    current_file: str | None = None
    current_new_line = 0
    added: list[tuple[str, int, str]] = []

    hunk_re = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

    for raw_line in diff.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            continue

        hunk_match = hunk_re.match(raw_line)
        if hunk_match:
            current_new_line = int(hunk_match.group(1))
            continue

        if current_file is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added.append((current_file, current_new_line, raw_line[1:]))
            current_new_line += 1
            continue

        if raw_line.startswith("-") and not raw_line.startswith("---"):
            continue

        if raw_line.startswith(" "):
            current_new_line += 1

    return added


def test_no_new_free_form_skip_or_xfail_in_tests_diff() -> None:
    """Newly added test lines must not introduce raw pytest skip/xfail calls."""
    violations: list[str] = []
    for file_path, line_no, line in _diff_added_test_lines():
        if file_path in ALLOWLIST_FILES:
            continue
        if any(pattern.search(line) for pattern in FREE_FORM_SKIP_PATTERNS):
            violations.append(f"{file_path}:{line_no}: {line.strip()}")

    assert not violations, (
        "CP3 policy violation: newly added free-form skip/xfail found. "
        "Use require_feature(...) / require_feature_or_raise(...) helpers instead.\n"
        + "\n".join(violations)
    )

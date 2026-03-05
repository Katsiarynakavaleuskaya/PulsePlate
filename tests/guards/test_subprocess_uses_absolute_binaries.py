"""Guard: subprocess must not use short-name binaries (B607-class).

Policy: gh, git, curl, wget, ssh etc. only via shutil.which() or absolute path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = (
    REPO_ROOT / "app",
    REPO_ROOT / "core",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
)

DISALLOWED_SHORT_BINARIES: frozenset[str] = frozenset({"gh", "git", "curl", "wget", "ssh"})

# First argument to run/Popen as string literal: ["gh", ...] or ['gh', ...]
SUBPROCESS_CALL_RE = re.compile(
    r"subprocess\.(run|Popen)\s*\(\s*(?P<argv>\[[^\]]{1,500}\])",
    re.VERBOSE,
)
FIRST_ARG_STR_RE = re.compile(r"""\[\s*["'](?P<bin>[^"']+)["']\s*(,|\])""")
WHICH_ASSIGN_RE = re.compile(
    r'(?P<var>\w+)\s*=\s*shutil\.which\s*\(\s*["\'](?P<bin>[^"\']+)["\']\s*\)'
)


@dataclass(frozen=True)
class SubprocessViolation:
    relpath: str
    lineno: int
    line: str
    reason: str


def _iter_files() -> list[Path]:
    exclude = {".venv", "venv", "node_modules", "__pycache__", ".git", "disabled_hypothesis"}
    out: list[Path] = []
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(part in p.parts for part in exclude):
                continue
            try:
                p.relative_to(REPO_ROOT)
            except ValueError:
                continue
            out.append(p)
    return sorted(out)


def _find_recent_which_var(lines: list[str], upto_idx: int, bin_name: str) -> Optional[str]:
    """Find variable assigned from shutil.which(bin_name) within 80 lines above."""
    start = max(0, upto_idx - 80)
    for j in range(upto_idx - 1, start - 1, -1):
        m = WHICH_ASSIGN_RE.search(lines[j])
        if m and m.group("bin") == bin_name:
            return m.group("var")
    return None


def test_subprocess_requires_absolute_or_which_resolved_binary() -> None:
    """subprocess.run/Popen must not use short-name binaries; use shutil.which or abs path."""
    violations: list[SubprocessViolation] = []

    for path in _iter_files():
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(lines, start=1):
            if "subprocess." not in line:
                continue
            m = SUBPROCESS_CALL_RE.search(line)
            if not m:
                continue
            argv = m.group("argv")
            first = FIRST_ARG_STR_RE.search(argv.strip())
            if not first:
                continue
            bin_token = first.group("bin").strip()
            if bin_token.startswith("/"):
                continue
            if bin_token not in DISALLOWED_SHORT_BINARIES:
                continue
            which_var = _find_recent_which_var(lines, idx, bin_token)
            if which_var:
                reason = (
                    f"calls '{bin_token}' by short name; use [{which_var}, ...] "
                    f"from shutil.which('{bin_token}')"
                )
            else:
                reason = (
                    f"calls '{bin_token}' by short name; resolve with shutil.which('{bin_token}') "
                    "or use an absolute path"
                )
            violations.append(
                SubprocessViolation(relpath=rel, lineno=idx, line=line.strip(), reason=reason)
            )

    if violations:
        msg_lines = [
            "Subprocess short-name binary violations (B607-class).",
            "Fix: use shutil.which('<bin>') and pass the resolved path as first arg.",
            "",
        ]
        for v in violations:
            msg_lines.append(f"- {v.relpath}:{v.lineno}: {v.reason}")
            msg_lines.append(f"  {v.line[:100]}{'...' if len(v.line) > 100 else ''}")
        raise AssertionError("\n".join(msg_lines))

"""Guard: no blind Bandit suppressions; every # nosec must be justified and dated.

Policy (AGENTS.md): # nosec forbidden by default. Allowed only as:
  # nosec BXXX: <why> (remove-by: YYYY-MM-DD, ref: <issue/pr>)
remove-by and ref MUST NOT be 'N/A'. Enforced so auto/weak modes cannot bypass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = (
    REPO_ROOT / "app",
    REPO_ROOT / "core",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
)

ALLOWLIST_PATH = Path(__file__).resolve().parent / "fixtures" / "nosec_policy_allowlist.txt"

BANDIT_CODE_RE = re.compile(r"\b(B\d{3})\b")
REMOVE_BY_RE = re.compile(r"\bremove-by:\s*([^\s,\)]+)\b", re.IGNORECASE)
REF_RE = re.compile(r"\bref:\s*([^\s\)]+)\b", re.IGNORECASE)

# N/A is forbidden (policy enforcement)
NA_PATTERN = re.compile(r"\bN/A\b", re.IGNORECASE)


@dataclass(frozen=True)
class NoSecViolation:
    relpath: str
    lineno: int
    line: str
    reason: str


# Optional per-line TTL: "path:line remove-by=YYYY-MM-DD ref=PR-XXX"
ALLOWLIST_REMOVE_BY_RE = re.compile(r"\bremove-by=(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)


def _load_allowlist() -> tuple[set[tuple[str, int]], list[tuple[str, int, str]]]:
    """(allowed_set, expired_list). allowed_set = (path, line_no); expired_list = (path, line_no, remove_by_str)."""
    if not ALLOWLIST_PATH.exists():
        return set(), []
    allowed: set[tuple[str, int]] = set()
    expired: list[tuple[str, int, str]] = []
    today = date.today()
    for raw in ALLOWLIST_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Parse "path:line" and optional "remove-by=YYYY-MM-DD ref=..."
        if ":" not in line:
            continue
        path_part, rest = line.split(":", 1)
        path_rel = path_part.strip()
        rest = rest.strip()
        # line_no is the first token (may be followed by remove-by=...)
        parts = rest.split()
        if not parts:
            continue
        try:
            line_no = int(parts[0])
        except ValueError:
            continue
        remove_by_m = ALLOWLIST_REMOVE_BY_RE.search(line)
        if remove_by_m:
            try:
                remove_by_date = date.fromisoformat(remove_by_m.group(1))
                if remove_by_date < today:
                    expired.append((path_rel, line_no, remove_by_m.group(1)))
                    continue
            except ValueError:
                pass
        else:
            # No remove-by on line → treat as expired (require TTL)
            expired.append((path_rel, line_no, "(missing remove-by=)"))
            continue
        allowed.add((path_rel, line_no))
    return allowed, expired


def _iter_files() -> list[Path]:
    """Python files under SCAN_DIRS."""
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


def _validate_nosec_line(line: str) -> tuple[bool, str]:
    """(ok, reason). ok=True -> line is valid or not a suppression; ok=False -> violation."""
    if "# nosec" not in line.lower() and "#nosec" not in line.lower():
        return True, ""
    # Only validate lines that are actual suppressions (contain Bandit code), not docstrings
    code_m = BANDIT_CODE_RE.search(line)
    if not code_m:
        return True, ""  # prose mention of nosec, skip

    code = code_m.group(1)
    # 2) must have Bxxx: (explanation marker)
    if f"{code}:" not in line:
        return False, f"missing explanation marker '{code}:'"

    # 3) must have remove-by: YYYY-MM-DD (and not N/A)
    remove_m = REMOVE_BY_RE.search(line)
    if not remove_m:
        return False, "missing 'remove-by: YYYY-MM-DD'"
    val = remove_m.group(1).strip()
    if NA_PATTERN.search(val):
        return False, "remove-by MUST NOT be 'N/A' (use a real date or fix the code)"
    if not re.match(r"\d{4}-\d{2}-\d{2}", val):
        return False, "remove-by must be date YYYY-MM-DD"

    # 4) must have ref: <issue/pr> (and not N/A)
    ref_m = REF_RE.search(line)
    if not ref_m:
        return False, "missing 'ref: <issue/pr>'"
    ref_val = ref_m.group(1).strip()
    if NA_PATTERN.search(ref_val):
        return False, "ref MUST NOT be 'N/A' (use PR-XXX or issue number)"

    return True, ""


def test_nosec_policy_guard() -> None:
    """Every # nosec must have Bxxx:, remove-by: date, ref: non-N/A; else FAIL. Allowlist entries must have TTL."""
    allowlist, expired = _load_allowlist()
    if expired:
        msg = [
            "Allowlist has expired or missing-TTL entries. Migrate to full nosec format or fix; do not extend allowlist.",
            "Format per line: path:line remove-by=YYYY-MM-DD ref=PR-XXX",
            "",
        ]
        for path_rel, line_no, remove_by_str in expired:
            msg.append(f"  {path_rel}:{line_no} {remove_by_str}")
        raise AssertionError("\n".join(msg))
    violations: list[NoSecViolation] = []

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
            if (rel, idx) in allowlist:
                continue
            ok, reason = _validate_nosec_line(line)
            if not ok:
                violations.append(
                    NoSecViolation(relpath=rel, lineno=idx, line=line.strip(), reason=reason)
                )

    if violations:
        msg_lines = [
            "NOSEC policy violations. Fix the code or use format:",
            "# nosec BXXX: <why> (remove-by: YYYY-MM-DD, ref: PR-XXX)",
            "remove-by and ref MUST NOT be 'N/A'.",
            "",
        ]
        for v in violations:
            msg_lines.append(f"- {v.relpath}:{v.lineno}: {v.reason}")
            msg_lines.append(f"  {v.line[:100]}{'...' if len(v.line) > 100 else ''}")
        raise AssertionError("\n".join(msg_lines))

"""Wellness language BLOCKER guard: blocks medical/diagnostic claims in docs and public copy.

Scans docs/ (and optionally other dirs) for BLOCKER patterns (RU+EN).
Allowlist: tests/guards/wellness_language_allowlist.txt (path-anchored regex).
In-file marker: pulseplate-allow:blocker-example (skips only line with marker).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Pattern, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = [
    REPO_ROOT / "docs",
]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "worktrees",
}

TEXT_EXTS = {
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".py",
    ".ts",
    ".tsx",
}

IN_FILE_ALLOW_MARKER = "pulseplate-allow:blocker-example"

# Narrow patterns: only phrases that are almost always medical claims.
# Excluded: "treat" / "treatment" (too many false positives: "treat as", "do not treat", code).
BLOCKER_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "WELLNESS_MEDICAL_CLAIM_RU",
        re.compile(
            r"\b(лечит|вылечит|вылечим|исцелит|диагноз|диагностирую|диагностирует)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "WELLNESS_MEDICAL_CLAIM_EN",
        re.compile(
            r"\b(we\s+cure|we\s+diagnose|will\s+cure|will\s+diagnose"
            r"|I\s+cure|I\s+diagnose|cures?\s+your|cures?\s+the"
            r"|diagnoses?\s+your|diagnoses?\s+the)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass(frozen=True)
class Finding:
    code: str
    path: Path
    line_no: int
    line: str


def _iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        yield p


def _load_allowlist() -> List[Pattern[str]]:
    """Load and compile allowlist regexes once (avoids recompilation per line)."""
    allow_path = REPO_ROOT / "tests" / "guards" / "wellness_language_allowlist.txt"
    if not allow_path.exists():
        return []
    patterns: List[Pattern[str]] = []
    for raw in allow_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        try:
            patterns.append(re.compile(s, re.IGNORECASE))
        except re.error:
            continue
    return patterns


def _is_allowlisted(path: Path, line: str, allow_patterns: List[Pattern[str]]) -> bool:
    try:
        rel = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = path.as_posix()
    composite = f"{rel}::{line}"
    for pat in allow_patterns:
        if pat.search(composite):
            return True
    return False


def test_wellness_language_blockers_guard() -> None:
    """Fail if docs/ contains medical claims (wellness-only posture)."""
    allow_patterns = _load_allowlist()
    findings: List[Finding] = []

    for root in SCAN_DIRS:
        if not root.exists():
            continue

        for file_path in _iter_files(root):
            if not file_path.exists():
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, FileNotFoundError, OSError):
                continue

            for idx, line in enumerate(text.splitlines(), start=1):
                if IN_FILE_ALLOW_MARKER in line:
                    continue

                for code, pattern in BLOCKER_PATTERNS:
                    if pattern.search(line):
                        if _is_allowlisted(file_path, line, allow_patterns):
                            continue
                        findings.append(
                            Finding(
                                code=code,
                                path=file_path,
                                line_no=idx,
                                line=line.strip()[:240],
                            )
                        )

    if findings:
        _raise_findings(findings)


def _raise_findings(findings: List[Finding]) -> None:
    pretty = "\n".join(
        f"- {f.code}: {f.path.relative_to(REPO_ROOT)}:{f.line_no}: {f.line}" for f in findings[:50]
    )
    raise AssertionError(
        "Wellness language BLOCKER guard failed. "
        "Remove/rewrite medical claims (wellness-only posture), or allowlist specific examples.\n"
        f"Findings (first 50):\n{pretty}\n"
        "Allowlist: tests/guards/wellness_language_allowlist.txt\n"
        f"In-file marker: {IN_FILE_ALLOW_MARKER}"
    )


def test_wellness_guard_blocks_medical_claim_ru() -> None:
    """Guard must fail when RU medical claim appears (negative test)."""
    for code, pattern in BLOCKER_PATTERNS:
        if code == "WELLNESS_MEDICAL_CLAIM_RU":
            assert pattern.search("Мы вылечим тревожность за 2 недели.")
            assert pattern.search("FFMI лечит недостаток мышц.")
            break
    else:
        raise AssertionError("WELLNESS_MEDICAL_CLAIM_RU pattern not found in BLOCKER_PATTERNS")


def test_wellness_guard_blocks_medical_claim_en() -> None:
    """Guard must fail when EN medical claim appears (negative test)."""
    for code, pattern in BLOCKER_PATTERNS:
        if code == "WELLNESS_MEDICAL_CLAIM_EN":
            assert pattern.search("We cure anxiety quickly.")
            assert pattern.search("This cures your condition.")
            assert pattern.search("I diagnose your condition.")
            assert pattern.search("This diagnoses the disease.")
            break
    else:
        raise AssertionError("WELLNESS_MEDICAL_CLAIM_EN pattern not found in BLOCKER_PATTERNS")
